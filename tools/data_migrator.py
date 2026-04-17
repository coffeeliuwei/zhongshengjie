#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据迁移工具 - Phase 6
======================

将现有JSON数据迁移到Qdrant向量库，创建扩展维度Collection。

支持的Collection:
- case_library_v2 - 案例库
- writing_techniques_v2 - 技法库
- novel_settings_v2 - 小说设定
- dialogue_style_v1 - 对话风格
- power_cost_v1 - 力量代价
- emotion_arc_v1 - 情感弧线
- power_vocabulary_v1 - 力量词汇
- foreshadow_pair_v1 - 伏笔对

使用方法:
    python tools/data_migrator.py --all          # 迁移所有数据
    python tools/data_migrator.py --status       # 查看迁移状态
    python tools/data_migrator.py --collection case_library_v2  # 迁移特定Collection
"""

import json
import argparse
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# 导入配置加载器
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import (
    get_project_root,
    get_qdrant_url,
    get_model_path,
    get_config,
    get_collection_name,
    get_vectorstore_dir,
    get_qdrant_storage_dir,
    get_case_library_dir,
    get_knowledge_graph_path,
)

# 导入现有模块（复用代码）
from modules.knowledge_base.sync_manager import SyncManager
from modules.knowledge_base.hybrid_search_manager import HybridSearchManager

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        Distance,
        VectorParams,
        PointStruct,
        SparseVector,
    )
except ImportError:
    raise ImportError("请安装 qdrant-client: pip install qdrant-client")


class DataMigrator:
    """
    数据迁移管理器

    负责将JSON数据迁移到Qdrant向量库，支持增量迁移和状态追踪。
    """

    # Collection定义
    COLLECTIONS = {
        # 核心Collection (v2 - BGE-M3混合检索)
        "case_library_v2": {
            "name": "案例库",
            "source": ".case-library/unified_index.json",
            "vector_size": 1024,
            "description": "标杆案例检索库，支持Dense+Sparse+ColBERT混合检索",
        },
        "writing_techniques_v2": {
            "name": "技法库",
            "source": "创作技法/",
            "vector_size": 1024,
            "description": "创作技法检索库，支持维度过滤",
        },
        "novel_settings_v2": {
            "name": "小说设定",
            "source": ".vectorstore/knowledge_graph.json",
            "vector_size": 1024,
            "description": "小说设定检索库，包含角色/势力/力量体系等",
        },
        # 大纲/剧情Collection (M3修复)
        "novel_plot_v1": {
            "name": "剧情大纲",
            "source": "总大纲.md",
            "vector_size": 1024,
            "description": "总大纲剧情检索库",
            "optional": True,
        },
        "chapter_outlines": {
            "name": "章节大纲",
            "source": "章节大纲/",
            "vector_size": 1024,
            "description": "章节大纲检索库",
            "optional": True,
        },
        # 扩展维度Collection (v1 - 单向量检索) - M3修复新增
        "worldview_element_v1": {
            "name": "世界观元素",
            "source": ".vectorstore/data/worldview_element.json",
            "vector_size": 1024,
            "description": "世界观元素检索库",
            "optional": True,
        },
        "character_relation_v1": {
            "name": "角色关系",
            "source": ".vectorstore/data/character_relation.json",
            "vector_size": 1024,
            "description": "角色关系检索库",
            "optional": True,
        },
        "author_style_v1": {
            "name": "作者风格",
            "source": ".vectorstore/data/author_style.json",
            "vector_size": 1024,
            "description": "风格检索库",
            "optional": True,
        },
        "evaluation_criteria_v1": {
            "name": "评审标准",
            "source": ".vectorstore/data/evaluation_criteria.json",
            "vector_size": 1024,
            "description": "评审标准检索库",
            "optional": True,
        },
        # 原有扩展维度Collection
        "dialogue_style_v1": {
            "name": "对话风格",
            "source": ".vectorstore/data/dialogue_style.json",
            "vector_size": 1024,
            "description": "对话风格模式库，用于对话场景参考",
            "optional": True,
        },
        "power_cost_v1": {
            "name": "力量代价",
            "source": ".vectorstore/data/power_cost.json",
            "vector_size": 1024,
            "description": "力量代价体系库，战斗场景参考",
            "optional": True,
        },
        "emotion_arc_v1": {
            "name": "情感弧线",
            "source": ".vectorstore/data/emotion_arc.json",
            "vector_size": 1024,
            "description": "情感弧线模板库，情感场景参考",
            "optional": True,
        },
        "power_vocabulary_v1": {
            "name": "力量词汇",
            "source": ".vectorstore/data/power_vocabulary.json",
            "vector_size": 1024,
            "description": "力量体系词汇库，战斗描写参考",
            "optional": True,
        },
        "foreshadow_pair_v1": {
            "name": "伏笔对",
            "source": ".vectorstore/data/foreshadow_pair.json",
            "vector_size": 1024,
            "description": "伏笔设置-回收配对库，伏笔场景参考",
            "optional": True,
        },
    }

    # 迁移进度文件
    MIGRATION_PROGRESS_FILE = ".vectorstore/migration_progress.json"

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        use_docker: bool = True,
        docker_url: str = None,
    ):
        """
        初始化数据迁移器

        Args:
            project_dir: 项目根目录
            use_docker: 是否使用Docker Qdrant
            docker_url: Docker Qdrant URL
        """
        self.project_dir = project_dir or get_project_root()
        self.vectorstore_dir = get_vectorstore_dir()
        self.case_library_dir = get_case_library_dir()

        # 复用现有管理器
        self.sync_manager = SyncManager(
            project_dir=self.project_dir,
            use_docker=use_docker,
            docker_url=docker_url,
        )

        self.search_manager = HybridSearchManager(
            project_dir=self.project_dir,
            use_docker=use_docker,
            docker_url=docker_url,
        )

        # Qdrant客户端
        self._client = None
        self._model = None
        self.use_docker = use_docker
        self.docker_url = docker_url or get_qdrant_url()

        # 加载迁移进度
        self.progress = self._load_progress()

    def _get_client(self) -> QdrantClient:
        """获取Qdrant客户端（复用现有逻辑）"""
        if self._client is None:
            if self.use_docker:
                try:
                    self._client = QdrantClient(url=self.docker_url)
                    self._client.get_collections()
                except Exception:
                    self._client = QdrantClient(path=str(get_qdrant_storage_dir()))
            else:
                self._client = QdrantClient(path=str(get_qdrant_storage_dir()))
        return self._client

    def _load_model(self):
        """加载嵌入模型（复用现有逻辑）"""
        if self._model is None:
            self._model = self.search_manager._load_model()
        return self._model

    def _load_progress(self) -> Dict[str, Any]:
        """加载迁移进度"""
        progress_file = self.vectorstore_dir / "migration_progress.json"
        if progress_file.exists():
            try:
                with open(progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_progress(self):
        """保存迁移进度"""
        progress_file = self.vectorstore_dir / "migration_progress.json"
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(self.progress, f, indent=2, ensure_ascii=False)

    def migrate_json_to_qdrant(
        self,
        collection_name: str,
        json_file: Path,
        batch_size: int = 100,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        迁移JSON数据到Qdrant

        Args:
            collection_name: Collection名称
            json_file: JSON文件路径
            batch_size: 批处理大小
            force: 是否强制重建

        Returns:
            迁移结果统计
        """
        print(f"\n[迁移] {collection_name} <- {json_file}")

        # 检查文件是否存在
        if not json_file.exists():
            print(f"  [错误] 文件不存在: {json_file}")
            return {"success": False, "error": "文件不存在", "count": 0}

        # 获取Collection配置
        collection_config = self.COLLECTIONS.get(collection_name)
        if not collection_config:
            print(f"  [错误] 未知的Collection: {collection_name}")
            return {"success": False, "error": "未知Collection", "count": 0}

        vector_size = collection_config["vector_size"]

        # 检查增量迁移
        file_hash = self._calculate_file_hash(json_file)
        last_hash = self.progress.get(collection_name, {}).get("file_hash")

        if not force and last_hash == file_hash:
            print(f"  [跳过] 文件未变化（增量迁移）")
            return {
                "success": True,
                "skipped": True,
                "count": self.progress[collection_name].get("count", 0),
            }

        # 加载JSON数据
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [错误] 读取JSON失败: {e}")
            return {"success": False, "error": str(e), "count": 0}

        # 处理数据格式
        records = self._extract_records(data, json_file, collection_name)

        if not records:
            print(f"  [警告] 没有有效数据")
            return {"success": True, "count": 0}

        print(f"  提取数据: {len(records)} 条")

        # 创建/重建Collection
        client = self._get_client()
        collections = [c.name for c in client.get_collections().collections]

        if collection_name in collections:
            if force:
                print(f"  [删除] 旧Collection")
                client.delete_collection(collection_name)
            else:
                print(f"  [已存在] Collection已存在，追加数据")

        # 创建Collection（根据类型使用不同配置）
        if collection_name.endswith("_v2"):
            # V2 Collection - 使用BGE-M3混合检索
            self._create_hybrid_collection(client, collection_name, vector_size)
        else:
            # V1 Collection - 使用单向量检索
            self._create_simple_collection(client, collection_name, vector_size)

        # 加载模型
        model = self._load_model()

        # 批量处理
        total_migrated = 0
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            migrated = self._migrate_batch(
                client, collection_name, model, batch, i, len(records)
            )
            total_migrated += migrated

        # 更新进度
        self.progress[collection_name] = {
            "file_hash": file_hash,
            "count": total_migrated,
            "last_migration": datetime.now().isoformat(),
            "source": str(json_file),
        }
        self._save_progress()

        print(f"  [完成] 已迁移 {total_migrated} 条数据")
        return {"success": True, "count": total_migrated}

    def _create_hybrid_collection(
        self, client: QdrantClient, collection_name: str, vector_size: int
    ):
        """创建混合检索Collection（V2）"""
        print(f"  [创建] 混合检索Collection: {collection_name}")

        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(size=vector_size, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": {},
            },
        )

    def _create_simple_collection(
        self, client: QdrantClient, collection_name: str, vector_size: int
    ):
        """创建单向量检索Collection（V1）"""
        print(f"  [创建] 单向量检索Collection: {collection_name}")

        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def _extract_records(
        self, data: Any, json_file: Path, collection_name: str
    ) -> List[Dict[str, Any]]:
        """
        从JSON数据提取记录

        Args:
            data: JSON数据
            json_file: JSON文件路径
            collection_name: Collection名称

        Returns:
            记录列表
        """
        records = []

        # 根据文件类型处理
        if collection_name == "case_library_v2":
            # 案例库 - 从unified_index.json提取
            novels = data.get("novels", {})
            for novel_path, novel_info in novels.items():
                if not novel_info.get("is_novel"):
                    continue

                # 查找对应的案例文件
                novel_name = novel_info.get("novel_name", "未知")
                genre = novel_info.get("genre", "未知")

                # 从案例目录提取
                cases_dir = self.case_library_dir
                for scene_dir in cases_dir.iterdir():
                    if not scene_dir.is_dir():
                        continue

                    scene_type = (
                        scene_dir.name.split("-")[1]
                        if "-" in scene_dir.name
                        else scene_dir.name
                    )

                    for case_file in scene_dir.rglob("*.json"):
                        try:
                            with open(case_file, "r", encoding="utf-8") as f:
                                case_data = json.load(f)

                            if case_data.get("novel_name") == novel_name:
                                records.append(
                                    {
                                        "id": hashlib.md5(
                                            str(case_file).encode()
                                        ).hexdigest()[:16],
                                        "content": case_data.get("content", "")[:2000],
                                        "payload": {
                                            "novel_name": novel_name,
                                            "scene_type": scene_type,
                                            "genre": genre,
                                            "word_count": case_data.get(
                                                "word_count", 0
                                            ),
                                            "quality_score": case_data.get(
                                                "quality_score", 0
                                            ),
                                            "source_file": str(case_file),
                                        },
                                    }
                                )
                        except Exception:
                            pass

        elif collection_name == "novel_settings_v2":
            # 小说设定 - 从knowledge_graph.json提取
            entities = data.get("实体", {})
            for name, props in entities.items():
                content_parts = [f"【{name}】"]
                content_parts.append(f"类型: {props.get('类型', '未知')}")

                desc = props.get("描述", "")
                if desc:
                    content_parts.append(f"描述: {desc}")

                attrs = props.get("属性", {})
                if attrs:
                    for key, value in attrs.items():
                        if value:
                            content_parts.append(f"{key}: {value}")

                records.append(
                    {
                        "id": hashlib.md5(name.encode()).hexdigest()[:16],
                        "content": "\n".join(content_parts),
                        "payload": {
                            "name": name,
                            "type": props.get("类型", "未知"),
                            "description": desc[:500],
                            "source": "knowledge_graph.json",
                        },
                    }
                )

        elif collection_name.endswith("_v1"):
            # 扩展维度Collection - 通用JSON处理
            if isinstance(data, dict):
                if "items" in data:
                    items = data["items"]
                elif "records" in data:
                    items = data["records"]
                elif "data" in data:
                    items = data["data"]
                else:
                    items = [data]
            elif isinstance(data, list):
                items = data
            else:
                items = [data]

            for i, item in enumerate(items):
                if isinstance(item, dict):
                    content = json.dumps(item, ensure_ascii=False)
                    records.append(
                        {
                            "id": hashlib.md5(content.encode()).hexdigest()[:16],
                            "content": content[:1000],
                            "payload": item,
                        }
                    )

        else:
            # 默认处理 - 直接提取
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = [data]
            else:
                items = [{"content": str(data)}]

            for i, item in enumerate(items):
                if isinstance(item, dict):
                    content = item.get("content", json.dumps(item, ensure_ascii=False))
                else:
                    content = str(item)

                records.append(
                    {
                        "id": hashlib.md5(content.encode()).hexdigest()[:16],
                        "content": content[:1000],
                        "payload": item
                        if isinstance(item, dict)
                        else {"content": content},
                    }
                )

        return records

    def _migrate_batch(
        self,
        client: QdrantClient,
        collection_name: str,
        model: Any,
        batch: List[Dict[str, Any]],
        batch_start: int,
        total: int,
    ) -> int:
        """
        迁移一批数据

        Args:
            client: Qdrant客户端
            collection_name: Collection名称
            model: 嵌入模型
            batch: 数据批次
            batch_start: 批次起始索引
            total: 总数据量

        Returns:
            迁移数量
        """
        # 提取文本内容
        texts = [r["content"] for r in batch]

        # 生成嵌入
        if collection_name.endswith("_v2"):
            # V2 - 使用BGE-M3生成三种向量
            output = model.encode(
                texts,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False,  # ColBERT不存储，检索时动态编码
            )

            vectors = output["dense_vecs"]
            sparse_vectors = output["lexical_weights"]
        else:
            # V1 - 使用单向量
            vectors = model.encode(texts)
            sparse_vectors = None

        # 创建点
        points = []
        for i, record in enumerate(batch):
            if collection_name.endswith("_v2"):
                # V2 - 混合向量点
                sparse_indices = list(sparse_vectors[i].keys())
                sparse_values = list(sparse_vectors[i].values())

                point = PointStruct(
                    id=record["id"],
                    vector={
                        "dense": vectors[i].tolist(),
                        "sparse": SparseVector(
                            indices=sparse_indices, values=sparse_values
                        ),
                    },
                    payload=record["payload"],
                )
            else:
                # V1 - 单向量点
                point = PointStruct(
                    id=record["id"],
                    vector=vectors[i].tolist(),
                    payload=record["payload"],
                )

            points.append(point)

        # 上传
        client.upsert(collection_name=collection_name, points=points)

        # 打印进度
        current = batch_start + len(batch)
        print(f"    进度: {current}/{total} ({current / total * 100:.1f}%)")

        return len(points)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希（用于增量迁移检测）"""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def create_extended_collections(self) -> Dict[str, Any]:
        """
        创建扩展维度Collection

        Returns:
            创建结果统计
        """
        print("\n[创建扩展维度Collection]")

        client = self._get_client()
        collections = [c.name for c in client.get_collections().collections]

        results = {}

        for collection_name, config in self.COLLECTIONS.items():
            if not config.get("optional", False):
                continue

            if collection_name in collections:
                print(f"  [已存在] {collection_name} - {config['name']}")
                results[collection_name] = {"exists": True, "created": False}
            else:
                print(f"  [创建] {collection_name} - {config['name']}")

                vector_size = config["vector_size"]
                self._create_simple_collection(client, collection_name, vector_size)

                results[collection_name] = {"exists": False, "created": True}

        return results

    def migrate_all(self, force: bool = False) -> Dict[str, Any]:
        """
        迁移所有数据

        Args:
            force: 是否强制重建

        Returns:
            迁移结果统计
        """
        print("\n" + "=" * 60)
        print("开始迁移所有数据")
        print("=" * 60)

        results = {}

        # 1. 迁移核心Collection（复用现有SyncManager）
        print("\n[迁移核心Collection]")

        # 案例库
        results["case_library_v2"] = self.sync_manager.sync_cases(rebuild=force)

        # 技法库
        results["writing_techniques_v2"] = self.sync_manager.sync_techniques(
            rebuild=force
        )

        # 小说设定
        results["novel_settings_v2"] = self.sync_manager.sync_novel_settings(
            rebuild=force
        )

        # 2. 迁移扩展维度Collection
        print("\n[迁移扩展维度Collection]")

        for collection_name, config in self.COLLECTIONS.items():
            if not config.get("optional", False):
                continue

            source_file = self.project_dir / config["source"]

            if source_file.exists():
                results[collection_name] = self.migrate_json_to_qdrant(
                    collection_name, source_file, force=force
                )
            else:
                print(f"  [跳过] {collection_name} - 数据文件不存在")
                results[collection_name] = {"success": False, "reason": "文件不存在"}

        # 3. 创建未迁移的扩展Collection
        self.create_extended_collections()

        # 打印总结
        print("\n" + "=" * 60)
        print("迁移完成")
        print("=" * 60)

        total_count = 0
        for collection_name, result in results.items():
            count = result.get("count", 0)
            total_count += count
            status = "成功" if result.get("success", False) else "失败"
            print(f"{collection_name}: {status} ({count} 条)")

        print(f"\n总计迁移: {total_count} 条数据")

        return results

    def get_migration_status(self) -> Dict[str, Any]:
        """
        获取迁移状态

        Returns:
            迁移状态详情
        """
        client = self._get_client()
        collections = [c.name for c in client.get_collections().collections]

        status = {
            "collections": {},
            "progress": self.progress,
            "timestamp": datetime.now().isoformat(),
        }

        for collection_name, config in self.COLLECTIONS.items():
            if collection_name in collections:
                info = client.get_collection(collection_name)
                status["collections"][collection_name] = {
                    "exists": True,
                    "name": config["name"],
                    "count": info.points_count,
                    "status": info.status.value,
                    "description": config["description"],
                    "optional": config.get("optional", False),
                }
            else:
                status["collections"][collection_name] = {
                    "exists": False,
                    "name": config["name"],
                    "count": 0,
                    "status": "not_created",
                    "description": config["description"],
                    "optional": config.get("optional", False),
                }

        return status

    def print_status(self):
        """打印迁移状态（CLI显示）"""
        status = self.get_migration_status()

        print("\n" + "=" * 60)
        print("数据迁移状态")
        print("=" * 60)

        print("\n[Collection状态]")

        for collection_name, info in status["collections"].items():
            optional_tag = " [可选]" if info.get("optional") else ""
            if info["exists"]:
                print(f"\n[OK] {collection_name}{optional_tag}")
                print(f"   名称: {info['name']}")
                print(f"   数量: {info['count']}")
                print(f"   状态: {info['status']}")
                print(f"   描述: {info['description']}")
            else:
                print(f"\n[--] {collection_name}{optional_tag}")
                print(f"   名称: {info['name']}")
                print(f"   状态: {info['status']}")
                print(f"   描述: {info['description']}")

        print("\n[迁移进度]")

        for collection_name, progress in status["progress"].items():
            if isinstance(progress, dict):
                last_time = progress.get("last_migration", "未迁移")
                count = progress.get("count", 0)
                print(f"{collection_name}: {count} 条 ({last_time})")
            else:
                print(f"{collection_name}: 已记录")

        print("\n" + "=" * 60)


def main():
    """CLI入口"""
    parser = argparse.ArgumentParser(
        description="数据迁移工具 - 将JSON数据迁移到Qdrant向量库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python tools/data_migrator.py --all          # 迁移所有数据
    python tools/data_migrator.py --status       # 查看迁移状态
    python tools/data_migrator.py --collection case_library_v2  # 迁移特定Collection
    python tools/data_migrator.py --create       # 创建扩展维度Collection
        """,
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="迁移所有数据",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="查看迁移状态",
    )

    parser.add_argument(
        "--collection",
        type=str,
        help="迁移特定Collection",
    )

    parser.add_argument(
        "--create",
        action="store_true",
        help="创建扩展维度Collection",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重建（删除旧数据）",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="批处理大小（默认100）",
    )

    args = parser.parse_args()

    migrator = DataMigrator()

    if args.status:
        migrator.print_status()

    elif args.all:
        migrator.migrate_all(force=args.force)

    elif args.collection:
        collection_name = args.collection

        if collection_name not in migrator.COLLECTIONS:
            print(f"错误: 未知的Collection '{collection_name}'")
            print(f"可用Collection: {list(migrator.COLLECTIONS.keys())}")
            return

        config = migrator.COLLECTIONS[collection_name]
        source_file = migrator.project_dir / config["source"]

        # 特殊处理核心Collection
        if collection_name == "case_library_v2":
            migrator.sync_manager.sync_cases(rebuild=args.force)
        elif collection_name == "writing_techniques_v2":
            migrator.sync_manager.sync_techniques(rebuild=args.force)
        elif collection_name == "novel_settings_v2":
            migrator.sync_manager.sync_novel_settings(rebuild=args.force)
        else:
            migrator.migrate_json_to_qdrant(
                collection_name,
                source_file,
                batch_size=args.batch_size,
                force=args.force,
            )

    elif args.create:
        migrator.create_extended_collections()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
