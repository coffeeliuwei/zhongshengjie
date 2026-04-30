"""
同步管理器 - 数据同步到向量库
整合 sync_to_vectorstore_v3.py、rebuild_qdrant_docker.py 的核心逻辑
"""

import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

# 从配置加载器导入路径获取函数
# [N8 2026-04-18] 修复：原 sys.path 计算 .parent.parent 指到 modules/ 而非项目根，
# 且 config_loader 在 core/ 下而非项目根；改用与 __init__.py:25、
# hybrid_search_manager.py:21 一致的 `from core.config_loader import (...)`。
try:
    from core.config_loader import (
        get_project_root,
        get_qdrant_url,
        get_vectorstore_dir,
        get_qdrant_storage_dir,
        get_knowledge_graph_path,
        get_techniques_dir,
        get_case_library_dir,
    )

    HAS_CONFIG_LOADER = True
except Exception:
    # 如果无法加载配置加载器，后续逻辑将回退到默认路径
    HAS_CONFIG_LOADER = False

    # 仍保留名称以免后续代码引用出错
    def get_project_root():
        raise ImportError

    def get_vectorstore_dir():
        raise ImportError

    def get_qdrant_storage_dir():
        raise ImportError

    def get_qdrant_url():
        raise ImportError

    def get_knowledge_graph_path():
        raise ImportError

    def get_techniques_dir():
        raise ImportError

    def get_case_library_dir():
        raise ImportError


try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
except ImportError:
    raise ImportError("请安装 qdrant-client: pip install qdrant-client")


class SyncManager:
    """
    数据同步管理器

    支持同步三大数据源到Qdrant向量库：
    - novel_settings: 小说设定（从knowledge_graph.json）
    - writing_techniques: 创作技法（从创作技法目录）
    - case_library: 标杆案例（从案例库目录）
    """

    # 集合名称常量
    # [N11 2026-04-18] 三集合统一加 _v2 后缀，与 core/config_loader.py 中
    # qdrant.collections 配置完全对齐；修复前 CLI `kb --stats` 显示 0/0/0
    # 因为查的是无 _v2 的旧集合名（Qdrant 中不存在）
    NOVEL_COLLECTION = "novel_settings_v2"
    TECHNIQUE_COLLECTION = "writing_techniques_v2"
    CASE_COLLECTION = "case_library_v2"

    # 向量维度
    VECTOR_SIZE = 1024  # BGE-M3 dense 向量维度

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
        初始化同步管理器

        Args:
            project_dir: 项目根目录（默认从配置加载）
            use_docker: 是否使用Docker Qdrant
            docker_url: Docker Qdrant URL（默认从配置加载）
        """
        self.project_dir = project_dir or get_project_root()
        self.vectorstore_dir = get_vectorstore_dir()
        self.qdrant_dir = get_qdrant_storage_dir()

        # 数据源路径（从配置加载）
        self.knowledge_graph_file = get_knowledge_graph_path()
        self.techniques_dir = get_techniques_dir()
        self.case_library_dir = get_case_library_dir()

        # Qdrant客户端
        self._client = None
        self._model = None
        self.use_docker = use_docker
        self.docker_url = docker_url or get_qdrant_url()

    def _get_client(self) -> QdrantClient:
        """获取Qdrant客户端"""
        if self._client is None:
            if self.use_docker:
                try:
                    self._client = QdrantClient(url=self.docker_url)
                    self._client.get_collections()  # 测试连接
                except Exception:
                    # 回退到本地
                    self._client = QdrantClient(path=str(self.qdrant_dir))
            else:
                self._client = QdrantClient(path=str(self.qdrant_dir))
        return self._client

    def _load_model(self):
        """加载嵌入模型（BGE-M3，1024 维 dense vector）"""
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel
            except ImportError:
                raise ImportError("请安装 FlagEmbedding: pip install -U FlagEmbedding")

            # 复用 core/inspiration/embedder.py 的路径配置
            from core.config_loader import get_model_path

            model_path = get_model_path()
            if not model_path:
                raise RuntimeError(
                    "BGE-M3 模型路径未配置，请检查 config.json 或环境变量 BGE_M3_MODEL_PATH"
                )
            self._model = BGEM3FlagModel(model_path, use_fp16=True)
        return self._model

    def sync(self, target: str = "all", rebuild: bool = False) -> Dict[str, Any]:
        """
        同步数据到向量库

        Args:
            target: 同步目标 - "novel", "technique", "case", "all"
            rebuild: 是否重建数据库

        Returns:
            同步结果统计
        """
        results = {}

        model = self._load_model()
        client = self._get_client()

        if target == "novel" or target == "all":
            results["novel"] = self.sync_novel_settings(rebuild=rebuild)

        if target == "technique" or target == "all":
            results["technique"] = self.sync_techniques(rebuild=rebuild)

        if target == "case" or target == "all":
            results["case"] = self.sync_cases(rebuild=rebuild)

        return results

    def sync_novel_settings(self, rebuild: bool = False) -> int:
        """
        同步小说设定

        Args:
            rebuild: 是否重建数据库

        Returns:
            同步数量
        """
        print("\n[同步小说设定]")

        client = self._get_client()
        model = self._load_model()

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

        # 重建集合
        if rebuild:
            collections = [c.name for c in client.get_collections().collections]
            if self.NOVEL_COLLECTION in collections:
                print(f"  [删除] 旧集合 {self.NOVEL_COLLECTION}")
                client.delete_collection(collection_name=self.NOVEL_COLLECTION)

        # 创建集合
        client.create_collection(
            collection_name=self.NOVEL_COLLECTION,
            vectors_config=VectorParams(
                size=self.VECTOR_SIZE, distance=Distance.COSINE
            ),
        )

        # 准备数据
        points = []
        texts = []
        entity_list = list(entities.items())

        for name, props in entity_list:
            # 构建文本内容
            content_parts = [f"【{name}】"]
            content_parts.append(f"类型: {props.get('类型', '未知')}")

            desc = props.get("描述", "")
            if desc:
                content_parts.append(f"描述: {desc}")

            # 处理属性
            attrs = props.get("属性", {})
            if attrs:
                for key, value in attrs.items():
                    if value:
                        if isinstance(value, str) and len(value) > 500:
                            value = value[:500]
                        elif isinstance(value, (dict, list)):
                            value = json.dumps(value, ensure_ascii=False)[:500]
                        content_parts.append(f"{key}: {value}")

            # 处理其他顶层属性
            for key, value in props.items():
                if key not in ["类型", "描述", "属性", "id", "名称"] and value:
                    if isinstance(value, str) and len(value) > 500:
                        value = value[:500]
                    elif isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)[:500]
                    content_parts.append(f"{key}: {value}")

            text = "\n".join(content_parts)
            texts.append(text)

        # 批量生成嵌入（BGE-M3）
        print("  [生成] 正在生成嵌入向量...")
        _output = model.encode(
            texts,
            batch_size=32,
            max_length=512,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        vectors = _output["dense_vecs"]

        # 创建点
        for i, ((name, props), vector) in enumerate(zip(entity_list, vectors)):
            props_json = json.dumps(props, ensure_ascii=False)
            if len(props_json) > 8000:
                props_json = props_json[:8000]

            point = PointStruct(
                id=i,
                vector=vector.tolist(),
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

        # 上传
        batch_size = 100
        for j in range(0, len(points), batch_size):
            batch = points[j : j + batch_size]
            client.upsert(collection_name=self.NOVEL_COLLECTION, points=batch)
            print(f"    上传: {min(j + batch_size, len(points))}/{len(points)}")

        print(f"  [完成] 已同步 {len(points)} 条小说设定")
        return len(points)

    def sync_techniques(self, rebuild: bool = False) -> int:
        """
        同步创作技法

        ⚠️ 已停用：writing_techniques_v2 使用 BGE-M3 混合向量（dense+sparse+colbert），
        本方法创建的是无名单向量集合，与 HybridSearchManager.search_technique() 不兼容。

        请改用：
            python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild

        Returns:
            0（始终跳过）
        """
        print(
            "\n[sync_techniques] ⚠️ 已停用。\n"
            "  writing_techniques_v2 需要 BGE-M3 混合向量（dense+sparse+colbert）。\n"
            "  请改用：python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild\n"
            "  本次跳过技法同步，其余目标继续执行。"
        )
        return 0

    def sync_cases(self, rebuild: bool = False) -> int:
        """[M3-β] 委托给 tools/case_builder.py --sync 完成案例向量化同步

        Args:
            rebuild: True 时先删除集合再全量同步
        Returns:
            成功同步的案例数量（subprocess 返回码，0=成功）
        """
        import subprocess
        import sys

        # rebuild=True 时先删除集合
        if rebuild:
            try:
                client = self._get_client()
                collections = [c.name for c in client.get_collections().collections]
                if self.CASE_COLLECTION in collections:
                    print(f"  [rebuild] 删除旧集合 {self.CASE_COLLECTION}")
                    client.delete_collection(collection_name=self.CASE_COLLECTION)
            except Exception as e:
                print(f"  [警告] rebuild 删除集合失败: {e}")

        case_builder = self.project_dir / "tools" / "case_builder.py"
        if not case_builder.exists():
            print(f"  [错误] case_builder.py 不存在: {case_builder}")
            return 0

        cmd = [sys.executable, str(case_builder), "--sync"]
        print(f"  [M3-β] 执行: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(self.project_dir))
        if result.returncode != 0:
            print(f"  [警告] case_builder --sync 退出码 {result.returncode}")
        return 0 if result.returncode == 0 else result.returncode

    def _extract_technique_sections(self, content: str) -> List[Dict[str, str]]:
        """
        从技法文件中提取章节/技法单元

        Args:
            content: 文件内容

        Returns:
            章节/技法单元列表
        """
        sections = []

        # 方法1：按中文数字章节分割
        pattern1 = r"\n(?=## [一二三四五六七八九十]+、)"
        parts = re.split(pattern1, content)

        for part in parts:
            if not part.strip():
                continue

            # 提取技法名称
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
                # 方法2：按 ### 标题分割
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

    def get_sync_status(self) -> Dict[str, Any]:
        """
        获取同步状态

        Returns:
            各集合的统计信息
        """
        client = self._get_client()
        status = {}

        collections = [c.name for c in client.get_collections().collections]

        for collection_name in [
            self.NOVEL_COLLECTION,
            self.TECHNIQUE_COLLECTION,
            self.CASE_COLLECTION,
        ]:
            if collection_name in collections:
                info = client.get_collection(collection_name)
                status[collection_name] = {
                    "exists": True,
                    "count": info.points_count,
                    "status": info.status.value,
                }
            else:
                status[collection_name] = {
                    "exists": False,
                    "count": 0,
                    "status": "not_created",
                }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="同步数据到 Qdrant 向量库")
    parser.add_argument(
        "--target",
        choices=["novel", "technique", "case", "all"],
        required=True,
        help="同步目标: novel(设定) / technique(技法) / case(案例) / all(全部)",
    )
    parser.add_argument("--rebuild", action="store_true", help="先删除集合再全量重建")
    args = parser.parse_args()

    sm = SyncManager()
    if args.target in ("novel", "all"):
        n = sm.sync_novel_settings(rebuild=args.rebuild)
        print(f"[novel] 同步完成: {n} 条")
    if args.target in ("technique", "all"):
        n = sm.sync_techniques(rebuild=args.rebuild)
        print(f"[technique] 同步完成: {n} 条")
    if args.target in ("case", "all"):
        sm.sync_cases(rebuild=args.rebuild)
        print("[case] 同步完成（委托 case_builder --sync）")
