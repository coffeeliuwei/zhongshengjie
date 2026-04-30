"""
BGE-M3 混合同步管理器
支持 Dense + Sparse + ColBERT 三种向量同步到 Qdrant

使用方法：
    from .hybrid_sync_manager import HybridSyncManager

    sync = HybridSyncManager()
    sync.sync_all(rebuild=True)
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from tqdm import tqdm

# 从配置加载器导入路径获取函数
try:
    from core.config_loader import (
        get_project_root,
        get_qdrant_url,
        get_model_path,
        get_vectorstore_dir,
        get_qdrant_storage_dir,
        get_knowledge_graph_path,
        get_techniques_dir,
        get_case_library_dir,
    )

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False

try:
    from qdrant_client import QdrantClient
    from qdrant_client import models
    from qdrant_client.http.models import PointStruct, SparseVector
except ImportError:
    raise ImportError("请安装 qdrant-client: pip install qdrant-client")

# 导入配置
import sys

config_dir = Path(__file__).parent
if str(config_dir) not in sys.path:
    sys.path.insert(0, str(config_dir))
from bge_m3_config import (
    BGE_M3_MODEL_NAME,
    BGE_M3_CACHE_DIR,
    DENSE_VECTOR_SIZE,
    BATCH_SIZE,
    USE_FP16,
    COLLECTION_NAMES,
    MIGRATION_CONFIG,
    get_collection_config,
)


class HybridSyncManager:
    """
    BGE-M3 混合同步管理器

    支持同步三大数据源到 Qdrant 混合向量库：
    - novel_settings_v2: 小说设定（Dense + Sparse + ColBERT）
    - writing_techniques_v2: 创作技法（Dense + Sparse + ColBERT）
    - case_library_v2: 标杆案例（Dense + Sparse + ColBERT）
    """

    # 维度映射
    DIMENSION_MAP = {
        "01-世界观维度": "世界观维度",
        "02-剧情维度": "剧情维度",
        "03-人物维度": "人物维度",
        "04-战斗冲突维度": "战斗冲突维度",
        "05-氛围意境维度": "氛围意境维度",
        "06-叙事维度": "叙事维度",
        "07-主题维度": "主题维度",
        "08-情感维度": "情感维度",
        "09-读者体验维度": "读者体验维度",
        "10-元维度": "元维度",
        "11-节奏维度": "节奏维度",
        "99-外部资源": "外部资源",
        "99-实战案例": "实战案例",
        "99-创作模板": "创作模板",
        "99-速查表": "速查表",
    }

    # 作家映射
    WRITER_MAP = {
        "世界观维度": "苍澜",
        "剧情维度": "玄一",
        "人物维度": "墨言",
        "战斗冲突维度": "剑尘",
        "氛围意境维度": "云溪",
        "叙事维度": "玄一",
        "主题维度": "玄一",
        "情感维度": "墨言",
        "读者体验维度": "云溪",
        "元维度": "全部",
        "节奏维度": "玄一",
        "外部资源": "玄一",
        "实战案例": "玄一",
        "创作模板": "玄一",
        "速查表": "玄一",
    }

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        use_docker: bool = True,
        docker_url: str = None,
    ):
        """
        初始化混合同步管理器

        Args:
            project_dir: 项目根目录（默认从配置加载）
            use_docker: 是否使用 Docker Qdrant
            docker_url: Docker Qdrant URL（默认从配置加载）
        """
        if HAS_CONFIG_LOADER:
            self.project_dir = project_dir or get_project_root()
            self.vectorstore_dir = get_vectorstore_dir()
            self.qdrant_dir = get_qdrant_storage_dir()
            self.knowledge_graph_file = get_knowledge_graph_path()
            self.techniques_dir = get_techniques_dir()
            self.case_library_dir = get_case_library_dir()
        else:
            self.project_dir = project_dir or Path.cwd()
            self.vectorstore_dir = self.project_dir / ".vectorstore"
            self.qdrant_dir = self.vectorstore_dir / "qdrant"
            self.knowledge_graph_file = self.vectorstore_dir / "knowledge_graph.json"
            self.techniques_dir = self.project_dir / "创作技法"
            self.case_library_dir = self.project_dir / ".case-library"

        # Qdrant 客户端
        self._client = None
        self._model = None
        self.use_docker = use_docker
        self.docker_url = docker_url or get_qdrant_url()

        # 设置 HuggingFace 缓存
        os.environ["HF_HOME"] = BGE_M3_CACHE_DIR
        model_path = get_model_path()
        if model_path is not None:
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    def _get_client(self) -> QdrantClient:
        """获取 Qdrant 客户端"""
        if self._client is None:
            if self.use_docker:
                try:
                    self._client = QdrantClient(url=self.docker_url)
                    self._client.get_collections()  # 测试连接
                    print(f"✅ 已连接 Docker Qdrant: {self.docker_url}")
                except Exception as e:
                    print(f"⚠️ Docker Qdrant 连接失败: {e}")
                    print(f"   使用本地存储: {self.qdrant_dir}")
                    self._client = QdrantClient(path=str(self.qdrant_dir))
            else:
                self._client = QdrantClient(path=str(self.qdrant_dir))
        return self._client

    def _load_model(self):
        """加载 BGE-M3 模型"""
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel

                print(f"[~] 加载 BGE-M3 模型: {BGE_M3_MODEL_NAME}")
                print(f"    缓存目录: {BGE_M3_CACHE_DIR}")

                self._model = BGEM3FlagModel(
                    BGE_M3_MODEL_NAME,
                    use_fp16=USE_FP16,
                    device="cpu",  # 可改为 'cuda' 如果有 GPU
                )
                print("[OK] BGE-M3 模型加载完成")
            except ImportError as e:
                raise ImportError(
                    f"请安装 FlagEmbedding: pip install FlagEmbedding ({e})"
                )
        return self._model

    def _encode_batch(
        self, texts: List[str], show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        批量编码文本，生成三种向量

        Args:
            texts: 文本列表
            show_progress: 是否显示进度

        Returns:
            包含三种向量的字典
        """
        model = self._load_model()

        print(f"🔄 编码 {len(texts)} 条文本 (Dense + Sparse + ColBERT)...")

        output = model.encode(
            texts,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=True,
            batch_size=BATCH_SIZE,
            max_length=8192,
        )

        return output

    def _create_hybrid_collection(self, collection_name: str) -> bool:
        """
        创建支持混合检索的 Collection

        Args:
            collection_name: Collection 名称

        Returns:
            是否成功创建
        """
        client = self._get_client()
        config = get_collection_config()

        try:
            # 检查是否已存在
            collections = [c.name for c in client.get_collections().collections]
            if collection_name in collections:
                print(f"  [删除] 旧 Collection: {collection_name}")
                client.delete_collection(collection_name=collection_name)

            # 创建新 Collection
            client.create_collection(
                collection_name=collection_name,
                vectors_config=config["vectors_config"],
                sparse_vectors_config=config["sparse_vectors_config"],
            )
            print(f"  [创建] Collection: {collection_name}")
            return True
        except Exception as e:
            print(f"  [错误] 创建 Collection 失败: {e}")
            return False

    def sync_all(self, rebuild: bool = True) -> Dict[str, int]:
        """
        同步所有数据

        Args:
            rebuild: 是否重建 Collection

        Returns:
            各数据源同步数量
        """
        results = {}

        results["novel"] = self.sync_novel_settings(rebuild=rebuild)
        results["technique"] = self.sync_techniques(rebuild=rebuild)
        results["case"] = self.sync_cases(rebuild=rebuild)

        # 打印汇总
        print("\n" + "=" * 60)
        print("📊 同步汇总")
        print("=" * 60)
        total = 0
        for name, count in results.items():
            print(f"  {name}: {count} 条")
            total += count
        print(f"\n  总计: {total} 条")
        print("=" * 60)

        return results

    def sync_novel_settings(self, rebuild: bool = True) -> int:
        """同步小说设定"""
        print("\n" + "=" * 60)
        print("[同步小说设定] BGE-M3 混合检索模式")
        print("=" * 60)

        client = self._get_client()

        # 读取知识图谱
        if not self.knowledge_graph_file.exists():
            print(f"  [错误] 知识图谱不存在: {self.knowledge_graph_file}")
            return 0

        with open(self.knowledge_graph_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        entities = data.get("实体", {})
        if not entities:
            print("  [错误] 没有实体数据")
            return 0

        print(f"  发现 {len(entities)} 个实体")

        # 创建 Collection
        collection_name = COLLECTION_NAMES["novel_settings"]
        if not self._create_hybrid_collection(collection_name):
            return 0

        # 准备数据
        texts = []
        entity_list = list(entities.items())

        for name, props in entity_list:
            text = self._build_entity_text(name, props)
            texts.append(text)

        # 批量编码
        embeddings = self._encode_batch(texts)

        # 构建 Points
        points = []
        for i, ((name, props), idx) in enumerate(
            zip(entity_list, range(len(entity_list)))
        ):
            # 获取三种向量
            dense_vec = embeddings["dense_vecs"][i].tolist()
            sparse_dict = embeddings["lexical_weights"][i]
            colbert_vecs = embeddings["colbert_vecs"][i]

            # 构建 Sparse 向量
            sparse_indices = list(sparse_dict.keys())
            sparse_values = list(sparse_dict.values())

            # 处理 ColBERT 向量
            if isinstance(colbert_vecs, list):
                colbert_list = [
                    v.tolist() if hasattr(v, "tolist") else v for v in colbert_vecs
                ]
            else:
                colbert_list = (
                    colbert_vecs.tolist()
                    if hasattr(colbert_vecs, "tolist")
                    else colbert_vecs
                )

            # 构建 payload
            props_json = json.dumps(props, ensure_ascii=False)
            if len(props_json) > 8000:
                props_json = props_json[:8000]

            point = PointStruct(
                id=i,
                vector={
                    "dense": dense_vec,
                    "colbert": colbert_list,
                    "sparse": SparseVector(
                        indices=sparse_indices, values=sparse_values
                    ),
                },
                payload={
                    "name": name,
                    "type": props.get("类型", "未知"),
                    "description": props.get("描述", "")[:2000]
                    if props.get("描述")
                    else "",
                    "properties": props_json,
                    "source": "knowledge_graph.json",
                },
            )
            points.append(point)

        # 批量上传
        self._upload_points(collection_name, points)

        print(f"  ✅ 已同步 {len(points)} 条小说设定")
        return len(points)

    def sync_techniques(self, rebuild: bool = True) -> int:
        """同步创作技法"""
        print("\n" + "=" * 60)
        print("[同步创作技法] BGE-M3 混合检索模式")
        print("=" * 60)

        client = self._get_client()

        if not self.techniques_dir.exists():
            print(f"  [错误] 技法目录不存在: {self.techniques_dir}")
            return 0

        # 收集技法文件
        skip_files = [
            "README.md",
            "01-创作检查清单.md",
            "00-学习路径规划.md",
            "创作技法速查表.md",
        ]
        md_files = [
            f for f in self.techniques_dir.rglob("*.md") if f.name not in skip_files
        ]
        print(f"  发现 {len(md_files)} 个技法文件")

        # 创建 Collection
        collection_name = COLLECTION_NAMES["writing_techniques"]
        if not self._create_hybrid_collection(collection_name):
            return 0

        # 提取技法
        techniques = []
        for md_file in md_files:
            try:
                parent_dir = md_file.parent.name
                if parent_dir == "99-从小说提取":
                    dimension = md_file.stem
                else:
                    dimension = self.DIMENSION_MAP.get(parent_dir, "未知")
                writer = self.WRITER_MAP.get(dimension, "未知")

                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()

                file_title = md_file.stem
                for line in content.split("\n")[:5]:
                    if line.startswith("# "):
                        file_title = line[2:].strip()
                        break

                sections = self._extract_technique_sections(content)

                for section in sections:
                    tech_content = section["content"]
                    if len(tech_content) < 100:
                        continue

                    techniques.append(
                        {
                            "name": section["name"],
                            "dimension": dimension,
                            "writer": writer,
                            "source_file": md_file.name,
                            "source_title": file_title,
                            "content": tech_content[:500],
                            "full_content": tech_content[:5000],
                        }
                    )

            except Exception as e:
                print(f"  [跳过] {md_file}: {e}")

        print(f"  提取技法条目: {len(techniques)} 条")

        if not techniques:
            return 0

        # 批量编码
        texts = [t["content"] for t in techniques]
        embeddings = self._encode_batch(texts)

        # 构建 Points
        points = []
        for i, tech in enumerate(techniques):
            dense_vec = embeddings["dense_vecs"][i].tolist()
            sparse_dict = embeddings["lexical_weights"][i]
            colbert_vecs = embeddings["colbert_vecs"][i]

            sparse_indices = list(sparse_dict.keys())
            sparse_values = list(sparse_dict.values())

            if isinstance(colbert_vecs, list):
                colbert_list = [
                    v.tolist() if hasattr(v, "tolist") else v for v in colbert_vecs
                ]
            else:
                colbert_list = (
                    colbert_vecs.tolist()
                    if hasattr(colbert_vecs, "tolist")
                    else colbert_vecs
                )

            point = PointStruct(
                id=i,
                vector={
                    "dense": dense_vec,
                    "colbert": colbert_list,
                    "sparse": SparseVector(
                        indices=sparse_indices, values=sparse_values
                    ),
                },
                payload={
                    "name": tech["name"],
                    "dimension": tech["dimension"],
                    "writer": tech["writer"],
                    "source_file": tech["source_file"],
                    "source_title": tech["source_title"],
                    "content": tech["full_content"],
                    "word_count": len(tech["full_content"]),
                },
            )
            points.append(point)

        # 批量上传
        self._upload_points(collection_name, points)

        print(f"  ✅ 已同步 {len(points)} 条创作技法")
        return len(points)

    def sync_cases(self, rebuild: bool = True) -> int:
        """同步案例库"""
        print("\n" + "=" * 60)
        print("[同步案例库] BGE-M3 混合检索模式")
        print("=" * 60)

        client = self._get_client()

        cases_dir = self.case_library_dir / "cases"
        if not cases_dir.exists():
            print(f"  [错误] 案例目录不存在: {cases_dir}")
            return 0

        # 创建 Collection
        collection_name = COLLECTION_NAMES["case_library"]
        if not self._create_hybrid_collection(collection_name):
            return 0

        # 收集案例
        all_cases = []
        for scene_dir in cases_dir.iterdir():
            if not scene_dir.is_dir():
                continue

            scene_type = scene_dir.name
            for json_file in scene_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        case_data = json.load(f)

                    filename = json_file.stem
                    parts = filename.split("_")

                    if len(parts) >= 3:
                        genre = parts[1]
                        novel_name = "_".join(parts[2:])
                    else:
                        genre = case_data.get("genre", "未知")
                        novel_name = case_data.get("novel_name", "未知")

                    case_data["scene_type"] = case_data.get("scene_type", scene_type)
                    case_data["genre"] = case_data.get("genre", genre)
                    case_data["novel_name"] = case_data.get("novel_name", novel_name)

                    all_cases.append(case_data)
                except Exception:
                    pass

        print(f"  发现 {len(all_cases)} 个案例")

        # 过滤有效内容
        valid_cases = [c for c in all_cases if len(c.get("content", "")) >= 50]
        print(f"  有效案例: {len(valid_cases)} 个")

        if not valid_cases:
            return 0

        # 分批处理（案例数量大）
        batch_size = 1000
        total_synced = 0

        for batch_start in range(0, len(valid_cases), batch_size):
            batch_cases = valid_cases[batch_start : batch_start + batch_size]

            # 批量编码
            texts = [c.get("content", "")[:1000] for c in batch_cases]
            print(f"\n  处理批次 {batch_start // batch_size + 1} ({len(texts)} 条)")
            embeddings = self._encode_batch(texts)

            # 构建 Points
            points = []
            for i, case in enumerate(batch_cases):
                idx = batch_start + i
                dense_vec = embeddings["dense_vecs"][i].tolist()
                sparse_dict = embeddings["lexical_weights"][i]
                colbert_vecs = embeddings["colbert_vecs"][i]

                sparse_indices = list(sparse_dict.keys())
                sparse_values = list(sparse_dict.values())

                if isinstance(colbert_vecs, list):
                    colbert_list = [
                        v.tolist() if hasattr(v, "tolist") else v for v in colbert_vecs
                    ]
                else:
                    colbert_list = (
                        colbert_vecs.tolist()
                        if hasattr(colbert_vecs, "tolist")
                        else colbert_vecs
                    )

                content = case.get("content", "")
                point = PointStruct(
                    id=idx,
                    vector={
                        "dense": dense_vec,
                        "colbert": colbert_list,
                        "sparse": SparseVector(
                            indices=sparse_indices, values=sparse_values
                        ),
                    },
                    payload={
                        "novel_name": case.get("novel_name", "未知"),
                        "scene_type": case.get("scene_type", "未知"),
                        "genre": case.get("genre", "未知"),
                        "quality_score": case.get(
                            "quality_score", case.get("confidence", 0) * 10
                        ),
                        "word_count": case.get("word_count", len(content)),
                        "content": content[:2000],
                        "cross_genre_value": case.get("cross_genre_value", ""),
                    },
                )
                points.append(point)

            # 批量上传
            self._upload_points(collection_name, points)
            total_synced += len(points)

        print(f"  ✅ 已同步 {total_synced} 条案例")
        return total_synced

    def sync_technique_json(
        self,
        json_path: Optional[str] = None,
        rebuild: bool = True,
    ) -> int:
        """
        直接从 technique_all.json 同步 138,968 条批量提炼技法到 writing_techniques_v2。

        JSON 字段：technique_name, dimension, description, keywords,
                   example_count, examples, source_novels, _novel_id

        Args:
            json_path: technique_all.json 路径，None 时从 config.json 自动推断
            rebuild:   是否重建 Collection（默认 True）
        """
        print("\n" + "=" * 60)
        print("[同步批量技法 JSON] BGE-M3 混合检索模式")
        print("=" * 60)

        # 解析 JSON 路径
        if json_path is None:
            try:
                cfg_file = Path(get_project_root()) / "config.json"
                with open(cfg_file, "r", encoding="utf-8") as _f:
                    _cfg = json.load(_f)
                output_dir = _cfg.get("extractor", {}).get(
                    "output_dir", "E:/novel_extracted"
                )
            except Exception:
                output_dir = "E:/novel_extracted"
            resolved_path = Path(output_dir) / "technique" / "technique_all.json"
        else:
            resolved_path = Path(json_path)

        if not resolved_path.exists():
            print(f"  [错误] 文件不存在: {resolved_path}")
            return 0

        # 读取 JSON
        print(f"  读取: {resolved_path}")
        with open(resolved_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        print(f"  原始条数: {len(raw_data):,}")

        # 过滤：description 不为空，长度 >= 20
        valid_data = [
            t
            for t in raw_data
            if t.get("description") and len(t.get("description", "")) >= 20
        ]
        print(f"  有效条数（description >= 20字）: {len(valid_data):,}")

        if not valid_data:
            return 0

        # 创建 Collection（重建）
        collection_name = COLLECTION_NAMES["writing_techniques_batch"]
        if rebuild:
            client = self._get_client()
            existing = [c.name for c in client.get_collections().collections]
            if collection_name in existing:
                client.delete_collection(collection_name)
                print(f"  [删除] 旧 collection: {collection_name}")
        if not self._create_hybrid_collection(collection_name):
            return 0

        # 分批处理（138k 条，每批 1000）
        batch_size = 1000
        total_synced = 0

        for batch_start in range(0, len(valid_data), batch_size):
            batch = valid_data[batch_start : batch_start + batch_size]

            # 组合嵌入文本：技法名 + 描述 + 第一条示例（截断）
            texts = []
            for t in batch:
                parts = [t["technique_name"]]
                if t.get("description"):
                    parts.append(t["description"])
                if t.get("examples") and t["examples"]:
                    parts.append("示例：" + str(t["examples"][0])[:300])
                texts.append("\n".join(parts)[:500])

            batch_num = batch_start // batch_size + 1
            total_batches = (len(valid_data) + batch_size - 1) // batch_size
            print(f"\n  批次 {batch_num}/{total_batches}（{len(texts)} 条）")

            embeddings = self._encode_batch(texts)

            # 构建 Points（payload 与 sync_techniques 保持一致）
            points = []
            for i, tech in enumerate(batch):
                idx = batch_start + i
                dense_vec = embeddings["dense_vecs"][i].tolist()
                sparse_dict = embeddings["lexical_weights"][i]
                colbert_vecs = embeddings["colbert_vecs"][i]

                sparse_indices = list(sparse_dict.keys())
                sparse_values = list(sparse_dict.values())

                if isinstance(colbert_vecs, list):
                    colbert_list = [
                        v.tolist() if hasattr(v, "tolist") else v for v in colbert_vecs
                    ]
                else:
                    colbert_list = (
                        colbert_vecs.tolist()
                        if hasattr(colbert_vecs, "tolist")
                        else colbert_vecs
                    )

                dimension = tech.get("dimension", "未知")
                writer = self.WRITER_MAP.get(dimension, "未知")
                source_novels = tech.get("source_novels", [])
                source_file = (
                    source_novels[0] if source_novels else tech.get("_novel_id", "")
                )
                full_content = texts[i]

                point = PointStruct(
                    id=idx,
                    vector={
                        "dense": dense_vec,
                        "colbert": colbert_list,
                        "sparse": SparseVector(
                            indices=sparse_indices, values=sparse_values
                        ),
                    },
                    payload={
                        "name": tech["technique_name"],
                        "dimension": dimension,
                        "writer": writer,
                        "source_file": str(source_file),
                        "source_title": tech["technique_name"],
                        "content": full_content,
                        "word_count": len(full_content),
                        "keywords": tech.get("keywords", []),
                        "occurrence_count": tech.get("occurrence_count", 0),
                    },
                )
                points.append(point)

            self._upload_points(collection_name, points)
            total_synced += len(points)

        print(f"\n  ✅ 已同步 {total_synced:,} 条批量提炼技法")
        return total_synced

    def _upload_points(self, collection_name: str, points: List[PointStruct]):
        """批量上传 Points"""
        client = self._get_client()
        batch_size = 100

        for j in range(0, len(points), batch_size):
            batch = points[j : j + batch_size]
            client.upsert(collection_name=collection_name, points=batch)
            print(f"    上传: {min(j + batch_size, len(points))}/{len(points)}")

    def _build_entity_text(self, name: str, props: Dict) -> str:
        """构建实体文本用于编码"""
        content_parts = [f"【{name}】"]
        content_parts.append(f"类型: {props.get('类型', '未知')}")

        desc = props.get("描述", "")
        if desc:
            content_parts.append(f"描述: {desc}")

        attrs = props.get("属性", {})
        if attrs:
            for key, value in attrs.items():
                if value:
                    if isinstance(value, str) and len(value) > 500:
                        value = value[:500]
                    elif isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)[:500]
                    content_parts.append(f"{key}: {value}")

        for key, value in props.items():
            if key not in ["类型", "描述", "属性", "id", "名称"] and value:
                if isinstance(value, str) and len(value) > 500:
                    value = value[:500]
                elif isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)[:500]
                content_parts.append(f"{key}: {value}")

        return "\n".join(content_parts)

    def _extract_technique_sections(self, content: str) -> List[Dict[str, str]]:
        """从技法文件中提取章节"""
        sections = []

        pattern1 = r"\n(?=## [一二三四五六七八九十]+、)"
        parts = re.split(pattern1, content)

        for part in parts:
            if not part.strip():
                continue

            name_match = re.search(
                r"^## [一二三四五六七八九十]+、[^：]*：?(.+)$",
                part,
                re.MULTILINE,
            )

            if name_match:
                tech_name = name_match.group(1).strip()
                sections.append(
                    {
                        "name": tech_name,
                        "content": part,
                    }
                )
            else:
                sub_pattern = r"\n(?=### )"
                sub_parts = re.split(sub_pattern, part)

                for sub_part in sub_parts:
                    if not sub_part.strip():
                        continue

                    sub_match = re.search(r"^### (.+)$", sub_part, re.MULTILINE)
                    if sub_match:
                        sub_name = sub_match.group(1).strip()
                        sections.append(
                            {
                                "name": sub_name,
                                "content": sub_part,
                            }
                        )

        return sections


# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BGE-M3 混合同步管理器")
    parser.add_argument(
        "--sync",
        choices=["novel", "technique", "case", "all", "technique-json"],
        default="all",
        help="同步目标（technique-json: 直接从 technique_all.json 同步）",
    )
    parser.add_argument("--rebuild", action="store_true", help="重建 Collection")
    parser.add_argument(
        "--json-path",
        default=None,
        help="technique_all.json 路径（仅 --sync technique-json 时使用，默认从 config.json 自动推断）",
    )

    args = parser.parse_args()

    sync = HybridSyncManager()

    if args.sync == "all":
        sync.sync_all(rebuild=args.rebuild)
    elif args.sync == "novel":
        sync.sync_novel_settings(rebuild=args.rebuild)
    elif args.sync == "technique":
        sync.sync_techniques(rebuild=args.rebuild)
    elif args.sync == "case":
        sync.sync_cases(rebuild=args.rebuild)
    elif args.sync == "technique-json":
        sync.sync_technique_json(json_path=args.json_path, rebuild=args.rebuild)
