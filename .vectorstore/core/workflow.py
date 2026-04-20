#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
众生界小说工作流系统 v3.0 (Qdrant)
=====================================

三大数据库：
- novel_settings_v2：小说设定（196条）- 势力、角色、力量体系
- writing_techniques_v2：创作技法（1,124条）- 11维度技法
- case_library_v2：标杆案例（256,083条）- 跨题材案例

使用方法：
    from workflow import NovelWorkflow

    workflow = NovelWorkflow()

    # 检索小说设定
    character = workflow.get_character("林夕")
    faction = workflow.get_faction("东方修仙")

    # 检索创作技法
    techniques = workflow.search_techniques("战斗代价", dimension="战斗")

    # 检索案例
    cases = workflow.search_cases("部落战斗 血脉燃烧", scene_type="战斗场景")

    # 获取知识图谱
    graph = workflow.get_knowledge_graph()
"""

import sys
import io

# Windows PowerShell 编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.config_loader import (
    get_qdrant_url,
    get_project_root,
    get_model_path,
    get_vectorstore_dir,
    get_path,
)

# 导入经验写入器（用于增强检索）
_experience_writer_available = True
try:
    from core.feedback.experience_writer import ExperienceWriter
except ImportError:
    _experience_writer_available = False
    ExperienceWriter = None  # type: ignore

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
except ImportError:
    print("请安装 qdrant-client: pip install qdrant-client")
    exit(1)


# ============================================================
# 配置
# ============================================================

PROJECT_DIR = get_project_root()
VECTORSTORE_DIR = get_vectorstore_dir()
QDRANT_DIR = VECTORSTORE_DIR / "qdrant"

# Docker Qdrant 配置（优先使用）
QDRANT_DOCKER_URL = get_qdrant_url()

# 集合名称 (v2版本)
NOVEL_COLLECTION = "novel_settings_v2"
TECHNIQUE_COLLECTION = "writing_techniques_v2"
CASE_COLLECTION = "case_library_v2"

# 向量维度 (BGE-M3)
VECTOR_SIZE = 1024

# BGE-M3 模型路径
BGE_M3_MODEL_PATH = get_model_path()

# 图谱文件
GRAPH_FILE = VECTORSTORE_DIR / "knowledge_graph.json"

# 场景-作家映射文件
SCENE_WRITER_MAPPING_FILE = VECTORSTORE_DIR / "scene_writer_mapping.json"


def get_qdrant_client():
    """获取Qdrant客户端，优先使用Docker"""
    try:
        # 连接Docker Qdrant（必须启动Docker）
        client = QdrantClient(url=QDRANT_DOCKER_URL)
        client.get_collections()  # 测试连接
        return client, "docker"
    except Exception as e:
        print(f"连接Docker Qdrant失败: {e}")
        raise


# 场景-作家映射读取器
# ============================================================


class SceneWriterMapping:
    """
    场景-作家协作映射读取器

    用于读取scene_writer_mapping.json配置，支持：
    - 获取场景的作家协作结构
    - 获取主责作家
    - 获取执行顺序
    - 获取案例库过滤配置
    """

    def __init__(self):
        self._data = None
        self._load()

    def _load(self):
        """加载映射配置"""
        if SCENE_WRITER_MAPPING_FILE.exists():
            with open(SCENE_WRITER_MAPPING_FILE, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {"scene_writer_mapping": {}, "inactive_scenes": {}}

    def get_scene_collaboration(self, scene_type: str) -> Optional[Dict]:
        """
        获取场景的协作结构

        Args:
            scene_type: 场景类型名称

        Returns:
            协作结构字典，包含collaboration, workflow_order, primary_writer等
        """
        mapping = self._data.get("scene_writer_mapping", {})
        return mapping.get(scene_type)

    def get_primary_writer(self, scene_type: str) -> Optional[str]:
        """获取场景的主责作家"""
        scene = self.get_scene_collaboration(scene_type)
        if scene:
            return scene.get("primary_writer")
        return None

    def get_workflow_order(self, scene_type: str) -> List[str]:
        """获取场景的作家执行顺序"""
        scene = self.get_scene_collaboration(scene_type)
        if scene:
            return scene.get("workflow_order", [])
        return []

    def get_writer_contributions(self, scene_type: str, writer: str) -> List[str]:
        """获取指定作家在该场景中的贡献项"""
        scene = self.get_scene_collaboration(scene_type)
        if not scene:
            return []

        for collab in scene.get("collaboration", []):
            if collab.get("writer") == writer:
                return collab.get("contribution", [])
        return []

    def get_case_library_filter(self, scene_type: str) -> Optional[Dict]:
        """获取场景的案例库过滤配置"""
        scene = self.get_scene_collaboration(scene_type)
        if scene:
            return scene.get("case_library_filter")
        return None

    def list_active_scenes(self) -> List[str]:
        """列出所有已激活的场景"""
        mapping = self._data.get("scene_writer_mapping", {})
        return [s for s, c in mapping.items() if c.get("status") is None]

    def list_can_activate_scenes(self) -> List[str]:
        """列出所有可激活的场景"""
        mapping = self._data.get("scene_writer_mapping", {})
        return [s for s, c in mapping.items() if c.get("status") == "can_activate"]

    def list_pending_scenes(self) -> List[str]:
        """列出所有待激活的场景"""
        mapping = self._data.get("scene_writer_mapping", {})
        return [
            s for s, c in mapping.items() if c.get("status") == "pending_activation"
        ]

    def list_inactive_scenes(self) -> List[str]:
        """列出所有不激活的场景"""
        inactive = self._data.get("inactive_scenes", {})
        return list(inactive.keys())

    def get_scene_stats(self) -> Dict:
        """获取场景统计信息"""
        return self._data.get("scene_count", {})

    def get_writer_role(self, writer: str) -> Optional[Dict]:
        """获取作家的角色定义"""
        writers = self._data.get("writer_definitions", {})
        return writers.get(writer)

    def get_all_writers(self) -> List[str]:
        """获取所有作家列表"""
        writers = self._data.get("writer_definitions", {})
        return list(writers.keys())

    def get_scenes_by_writer(self, writer: str) -> List[str]:
        """获取指定作家参与的所有场景"""
        mapping = self._data.get("scene_writer_mapping", {})
        scenes = []
        for scene_type, config in mapping.items():
            for collab in config.get("collaboration", []):
                if collab.get("writer") == writer:
                    scenes.append(scene_type)
                    break
        return scenes


# ============================================================
# 小说设定检索器
# ============================================================


class NovelSettingsSearcher:
    """小说设定检索器 (BGE-M3 + Qdrant版)"""

    def __init__(self, client: QdrantClient):
        self.client = client
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel

                self._model = BGEM3FlagModel(
                    BGE_M3_MODEL_PATH, use_fp16=True, device="cpu"
                )
            except ImportError:
                print("请安装 FlagEmbedding: pip install FlagEmbedding")
            except Exception as e:
                print(f"加载BGE-M3模型失败: {e}")
        return self._model

    def _get_embedding(self, text: str) -> List[float]:
        model = self._load_model()
        if model is None:
            return [0.0] * VECTOR_SIZE
        try:
            out = model.encode([text], return_dense=True)
            return out["dense_vecs"][0].tolist()
        except Exception as e:
            return [0.0] * VECTOR_SIZE

    def search(
        self, query: str, entity_type: Optional[str] = None, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """语义检索小说设定"""
        query_vector = self._get_embedding(query)

        query_filter = None
        if entity_type:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="type", match=models.MatchValue(value=entity_type)
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=NOVEL_COLLECTION,
            query=query_vector,
            using="dense",  # 使用dense向量
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        formatted = []
        for p in results.points:
            formatted.append(
                {
                    "id": p.id,
                    "name": p.payload.get("name", "未知"),
                    "type": p.payload.get("type", "未知"),
                    "description": p.payload.get("description", ""),
                    "properties": p.payload.get("properties", "{}"),
                    "score": p.score,
                }
            )
        return formatted

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """按名称精确获取"""
        results = self.client.scroll(
            collection_name=NOVEL_COLLECTION,
            with_payload=True,
            with_vectors=False,
            limit=1000,
        )[0]

        for p in results:
            if p.payload.get("name") == name:
                return {
                    "id": p.id,
                    "name": p.payload.get("name"),
                    "type": p.payload.get("type"),
                    "description": p.payload.get("description", ""),
                    "properties": p.payload.get("properties", "{}"),
                }
        return None

    def get_character(self, name: str) -> Optional[Dict[str, Any]]:
        """获取角色设定 - 优先精确匹配"""
        # 先尝试精确匹配
        exact = self.get_by_name(name)
        if exact and exact.get("type") == "角色":
            return exact

        # 再用语义检索
        results = self.search(name, entity_type="角色", top_k=10)
        for r in results:
            if name in r.get("name", "") or r.get("name", "") in name:
                return r
        return None

    def get_faction(self, name: str) -> Optional[Dict[str, Any]]:
        """获取势力设定 - 优先精确匹配"""
        # 先尝试精确匹配
        exact = self.get_by_name(name)
        if exact and exact.get("type") == "势力":
            return exact

        # 再用语义检索
        results = self.search(name, entity_type="势力", top_k=10)
        for r in results:
            if name in r.get("name", "") or r.get("name", "") in name:
                return r
        return None

    def get_power_branch(self, name: str) -> Optional[Dict[str, Any]]:
        """获取力量派别"""
        results = self.search(name, entity_type="力量派别", top_k=10)
        for r in results:
            if name in r.get("name", ""):
                return r
        return None

    def list_all(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有实体"""
        results = self.client.scroll(
            collection_name=NOVEL_COLLECTION,
            with_payload=True,
            with_vectors=False,
            limit=1000,
        )[0]

        items = []
        for p in results:
            if entity_type is None or p.payload.get("type") == entity_type:
                items.append(
                    {
                        "id": p.id,
                        "name": p.payload.get("name", "未知"),
                        "type": p.payload.get("type", "未知"),
                    }
                )
        return items

    def count(self) -> int:
        """获取总数量"""
        info = self.client.get_collection(NOVEL_COLLECTION)
        return info.points_count


# ============================================================
# 创作技法检索器
# ============================================================


class TechniqueSearcher:
    """创作技法检索器 (BGE-M3 + Qdrant版)"""

    def __init__(self, client: QdrantClient):
        self.client = client
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel

                self._model = BGEM3FlagModel(
                    BGE_M3_MODEL_PATH, use_fp16=True, device="cpu"
                )
            except ImportError:
                print("请安装 FlagEmbedding: pip install FlagEmbedding")
            except Exception as e:
                print(f"加载BGE-M3模型失败: {e}")
        return self._model

    def _get_embedding(self, text: str) -> List[float]:
        model = self._load_model()
        if model is None:
            return [0.0] * VECTOR_SIZE
        try:
            out = model.encode([text], return_dense=True)
            return out["dense_vecs"][0].tolist()
        except Exception as e:
            return [0.0] * VECTOR_SIZE

    def search(
        self, query: str, dimension: Optional[str] = None, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """语义检索创作技法"""
        query_vector = self._get_embedding(query)

        query_filter = None
        if dimension:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="dimension", match=models.MatchValue(value=dimension)
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=TECHNIQUE_COLLECTION,
            query=query_vector,
            using="dense",  # 使用dense向量
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        formatted = []
        for p in results.points:
            formatted.append(
                {
                    "id": p.id,
                    "name": p.payload.get("name", "未知"),
                    "dimension": p.payload.get("dimension", "未知"),
                    "writer": p.payload.get("writer", "未知"),
                    "source_file": p.payload.get("source_file", ""),
                    "source_title": p.payload.get("source_title", ""),
                    "content": p.payload.get("content", ""),
                    "word_count": p.payload.get("word_count", 0),
                    "score": p.score,
                }
            )
        return formatted

    def get_by_dimension(self, dimension: str) -> List[Dict[str, Any]]:
        """按维度获取所有技法"""
        results = self.client.scroll(
            collection_name=TECHNIQUE_COLLECTION,
            with_payload=True,
            with_vectors=False,
            limit=1000,
        )[0]

        items = []
        for p in results:
            if p.payload.get("dimension") == dimension:
                items.append(
                    {
                        "id": p.id,
                        "name": p.payload.get("name", "未知"),
                        "dimension": p.payload.get("dimension"),
                        "writer": p.payload.get("writer", "未知"),
                        "content": p.payload.get("content", ""),
                        "file": p.payload.get("file", ""),
                    }
                )
        return items

    def list_dimensions(self) -> List[str]:
        """列出所有维度"""
        results = self.client.scroll(
            collection_name=TECHNIQUE_COLLECTION,
            with_payload=True,
            with_vectors=False,
            limit=1000,
        )[0]

        dimensions = set()
        for p in results:
            dim = p.payload.get("dimension", "")
            if dim:
                dimensions.add(dim)
        return sorted(list(dimensions))

    def count(self) -> int:
        """获取总数量"""
        info = self.client.get_collection(TECHNIQUE_COLLECTION)
        return info.points_count


# ============================================================
# 案例检索器
# ============================================================


class CaseSearcher:
    """案例检索器 (BGE-M3 + Qdrant版)"""

    def __init__(self, client: QdrantClient):
        self.client = client
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel

                self._model = BGEM3FlagModel(
                    BGE_M3_MODEL_PATH, use_fp16=True, device="cpu"
                )
            except ImportError:
                print("请安装 FlagEmbedding: pip install FlagEmbedding")
            except Exception as e:
                print(f"加载BGE-M3模型失败: {e}")
        return self._model

    def _get_embedding(self, text: str) -> List[float]:
        model = self._load_model()
        if model is None:
            return [0.0] * VECTOR_SIZE
        try:
            out = model.encode([text], return_dense=True)
            return out["dense_vecs"][0].tolist()
        except Exception as e:
            return [0.0] * VECTOR_SIZE

    def search(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """语义检索案例"""
        query_vector = self._get_embedding(query)

        filter_conditions = []
        if scene_type:
            filter_conditions.append(
                models.FieldCondition(
                    key="scene_type", match=models.MatchValue(value=scene_type)
                )
            )
        if genre:
            filter_conditions.append(
                models.FieldCondition(key="genre", match=models.MatchValue(value=genre))
            )

        query_filter = (
            models.Filter(must=filter_conditions) if filter_conditions else None
        )

        results = self.client.query_points(
            collection_name=CASE_COLLECTION,
            query=query_vector,
            using="dense",  # 使用dense向量
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        formatted = []
        for p in results.points:
            formatted.append(
                {
                    "id": p.id,
                    "novel_name": p.payload.get("novel_name", "未知"),
                    "scene_type": p.payload.get("scene_type", "未知"),
                    "genre": p.payload.get("genre", "未知"),
                    "quality_score": p.payload.get("quality_score", 0),
                    "content": p.payload.get("content", ""),
                    "score": p.score,
                }
            )
        return formatted

    def list_scene_types(self) -> List[str]:
        """列出所有场景类型（从配置文件读取，避免扫描38万条数据库）"""
        # 优先从 scene_writer_mapping.json 配置文件读取
        # 这比 scroll 38万条数据快得多
        try:
            mapping_file = PROJECT_DIR / ".vectorstore" / "scene_writer_mapping.json"
            if mapping_file.exists():
                with open(mapping_file, "r", encoding="utf-8") as f:
                    mapping = json.load(f)
                scene_mapping = mapping.get("scene_writer_mapping", {})
                scenes = list(scene_mapping.keys())
                if scenes:
                    return sorted(scenes)
        except Exception:
            pass

        # 回退：从数据库扫描（仅作为备选）
        results = self.client.scroll(
            collection_name=CASE_COLLECTION,
            with_payload=True,
            with_vectors=False,
            limit=1000,  # 减少扫描数量
        )[0]

        scenes = set()
        for p in results:
            scene = p.payload.get("scene_type", "")
            if scene:
                scenes.add(scene)
        return sorted(list(scenes))

    def count(self) -> int:
        """获取总数量"""
        info = self.client.get_collection(CASE_COLLECTION)
        return info.points_count


# ============================================================
# 诗词意象检索器
# ============================================================

IMAGERY_COLLECTION = "poetry_imagery_v2"


class ImagerySearcher:
    """诗词意象检索器 (BGE-M3 + Qdrant版)"""

    def __init__(self, client: QdrantClient):
        self.client = client
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel

                self._model = BGEM3FlagModel(
                    BGE_M3_MODEL_PATH, use_fp16=True, device="cpu"
                )
            except ImportError:
                print("请安装 FlagEmbedding: pip install FlagEmbedding")
            except Exception as e:
                print(f"加载BGE-M3模型失败: {e}")
        return self._model

    def _get_embedding(self, text: str) -> List[float]:
        model = self._load_model()
        if model is None:
            return [0.0] * VECTOR_SIZE
        try:
            out = model.encode([text], return_dense=True)
            return out["dense_vecs"][0].tolist()
        except Exception as e:
            return [0.0] * VECTOR_SIZE

    def search(
        self,
        query: str,
        world_context: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        语义检索意象

        Args:
            query: 查询文本（如"虚无感、战争后"）
            world_context: 世界观上下文（"众生界" / None）
            top_k: 返回数量

        Returns:
            意象列表
        """
        query_vector = self._get_embedding(query)

        # 构建过滤条件
        query_filter = None
        if world_context:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="world_context",
                        match=models.MatchValue(value=world_context),
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=IMAGERY_COLLECTION,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        formatted = []
        for p in results.points:
            formatted.append(
                {
                    "id": p.id,
                    "name": p.payload.get("name", "未知"),
                    "category": p.payload.get("category", "未知"),
                    "emotion_core": p.payload.get("emotion_core", ""),
                    "emotion_tags": p.payload.get("emotion_tags", []),
                    "description": p.payload.get("description", ""),
                    "usage_examples": p.payload.get("usage_examples", []),
                    "world_context": p.payload.get("world_context"),
                    "philosophy_link": p.payload.get("philosophy_link"),
                    "score": p.score,
                }
            )
        return formatted

    def list_all(self, world_context: Optional[str] = None) -> List[str]:
        """列出所有意象名称"""
        query_filter = None
        if world_context:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="world_context",
                        match=models.MatchValue(value=world_context),
                    )
                ]
            )

        results = self.client.scroll(
            collection_name=IMAGERY_COLLECTION,
            scroll_filter=query_filter,
            with_payload=True,
            with_vectors=False,
            limit=1000,
        )[0]

        names = [p.payload.get("name", "") for p in results if p.payload.get("name")]
        return sorted(names)

    def count(self) -> int:
        """获取总数量"""
        try:
            info = self.client.get_collection(IMAGERY_COLLECTION)
            return info.points_count
        except Exception:
            return 0


# ============================================================
# 知识图谱读取器
# ============================================================


class KnowledgeGraphReader:
    """知识图谱读取器"""

    def __init__(self):
        self.data = None
        self._load()

    def _load(self):
        if GRAPH_FILE.exists():
            with open(GRAPH_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)

    def get_all_entities(self) -> Dict[str, Dict]:
        return self.data.get("实体", {}) if self.data else {}

    def get_all_relations(self) -> List[Dict]:
        return self.data.get("关系", []) if self.data else []

    def get_entity(self, name: str) -> Optional[Dict]:
        entities = self.get_all_entities()
        return entities.get(name)

    def get_entity_relations(self, name: str) -> List[Dict]:
        relations = self.get_all_relations()
        result = []
        for rel in relations:
            if rel.get("源实体") == name or rel.get("目标实体") == name:
                result.append(rel)
        return result

    def get_stats(self) -> Dict[str, Any]:
        if not self.data:
            return {}

        entities = self.data.get("实体", {})
        relations = self.data.get("关系", [])

        type_counts = {}
        for entity in entities.values():
            t = entity.get("类型", "未知")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "总实体数": len(entities),
            "总关系数": len(relations),
            "实体类型分布": type_counts,
        }


# ============================================================
# 行为预判生成器
# ============================================================

# 行为预判数据文件
BEHAVIOR_DATA_FILE = PROJECT_DIR / "设定" / "角色过往经历与情绪触发.md"
PHILOSOPHY_DATA_FILE = PROJECT_DIR / "设定" / "主角哲学心理基调.md"


class BehaviorPredictor:
    """
    行为预判生成器

    根据角色设定生成在特定场景下的行为预测。

    数据来源：
    - 核心维度（哲学流派、心理特征等）：从知识图谱读取（已入库）
    - 扩展维度（过往经历、情绪触发等）：从MD文件运行时读取（不入库）

    使用方法：
        predictor = BehaviorPredictor()
        result = predictor.predict("林夕", "战斗", stage="小我期", emotion="愤怒")
    """

    def __init__(self, graph_reader: Optional[KnowledgeGraphReader] = None):
        self.graph_reader = graph_reader or KnowledgeGraphReader()
        self._extended_data = None  # 扩展维度缓存

    # ============================================================
    # 数据加载
    # ============================================================

    def _load_extended_data(self) -> Dict[str, Dict]:
        """从MD文件加载扩展维度（过往经历、情绪触发）"""
        if self._extended_data is not None:
            return self._extended_data

        if not BEHAVIOR_DATA_FILE.exists():
            return {}

        with open(BEHAVIOR_DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # 简单解析MD文件中的角色数据
        # 实际使用时可以用更复杂的解析逻辑
        self._extended_data = self._parse_behavior_md(content)
        return self._extended_data

    def _parse_behavior_md(self, content: str) -> Dict[str, Dict]:
        """
        解析行为数据MD文件

        文件格式：
        #### 1. 林夕（东方修仙·道家）

        **过往经历**：
        | 维度 | 内容 | 对行为的影响 |

        **情绪触发**：
        | 情绪 | 触发条件 | 行为变化 |

        **行为烙印**：
        | 触发情境 | 行为反应 | 依据 |
        """
        import re

        result = {}
        lines = content.split("\n")

        current_role = None
        current_section = None
        in_table = False
        table_rows = []

        for i, line in enumerate(lines):
            # 检测角色名 - 支持多种格式
            # 格式1: #### 1. 林夕（东方修仙·道家）
            # 格式2: #### 1. 林夕
            role_match = re.match(r"####\s+(\d+)\.\s*([^\s（(（]+)", line)
            if role_match:
                # 保存上一个角色的数据
                if current_role and current_section and table_rows:
                    self._save_table_data(
                        result, current_role, current_section, table_rows
                    )

                current_role = role_match.group(2).strip()
                result[current_role] = {"过往经历": {}, "情绪触发": {}, "行为烙印": []}
                current_section = None
                in_table = False
                table_rows = []
                continue

            if not current_role:
                continue

            # 检测章节标题
            if "**过往经历**" in line:
                # 保存上一节的数据
                if current_section and table_rows:
                    self._save_table_data(
                        result, current_role, current_section, table_rows
                    )
                current_section = "过往经历"
                in_table = False
                table_rows = []
            elif "**情绪触发**" in line:
                if current_section and table_rows:
                    self._save_table_data(
                        result, current_role, current_section, table_rows
                    )
                current_section = "情绪触发"
                in_table = False
                table_rows = []
            elif "**行为烙印**" in line:
                if current_section and table_rows:
                    self._save_table_data(
                        result, current_role, current_section, table_rows
                    )
                current_section = "行为烙印"
                in_table = False
                table_rows = []

            # 检测表格行
            elif current_section and line.strip().startswith("|"):
                # 跳过分隔行 (|---|---|)
                if re.match(r"^\|[\s\-:]+\|", line):
                    in_table = True
                    continue

                if in_table:
                    # 解析表格行
                    cells = [cell.strip() for cell in line.split("|")[1:-1]]
                    if cells:
                        table_rows.append(cells)

        # 保存最后一组数据
        if current_role and current_section and table_rows:
            self._save_table_data(result, current_role, current_section, table_rows)

        return result

    def _save_table_data(
        self, result: Dict, role: str, section: str, rows: List[List[str]]
    ):
        """将表格数据保存到结果中"""
        if not rows or role not in result:
            return

        if section == "过往经历":
            # 过往经历表格：| 维度 | 内容 | 对行为的影响 |
            for row in rows:
                if len(row) >= 2:
                    dimension = row[0].replace("**", "").strip()
                    content = row[1].strip() if len(row) > 1 else ""
                    impact = row[2].strip() if len(row) > 2 else ""
                    result[role]["过往经历"][dimension] = {
                        "内容": content,
                        "影响": impact,
                    }

        elif section == "情绪触发":
            # 情绪触发表格：| 情绪 | 触发条件 | 行为变化 |
            for row in rows:
                if len(row) >= 2:
                    emotion = row[0].replace("**", "").strip()
                    trigger = row[1].strip() if len(row) > 1 else ""
                    behavior = row[2].strip() if len(row) > 2 else ""
                    result[role]["情绪触发"][emotion] = {
                        "触发条件": trigger,
                        "行为变化": behavior,
                    }

        elif section == "行为烙印":
            # 行为烙印表格：| 触发情境 | 行为反应 | 依据 |
            for row in rows:
                if len(row) >= 2:
                    situation = row[0].replace("**", "").strip()
                    reaction = row[1].strip() if len(row) > 1 else ""
                    basis = row[2].strip() if len(row) > 2 else ""
                    result[role]["行为烙印"].append(
                        {"触发情境": situation, "行为反应": reaction, "依据": basis}
                    )

    def _get_core_data(self, role_name: str) -> Dict:
        """从知识图谱获取核心维度数据"""
        # 从知识图谱获取角色实体
        # 角色实体ID格式：char_linxi
        char_id = f"char_{role_name}"
        entity = self.graph_reader.get_entity(char_id)

        if not entity:
            # 尝试直接用名字查找
            entities = self.graph_reader.get_all_entities()
            for eid, e in entities.items():
                if e.get("名称") == role_name or e.get("名称") == role_name:
                    entity = e
                    break

        if not entity:
            return {}

        props = entity.get("属性", {})
        if isinstance(props, str):
            try:
                props = json.loads(props)
            except:
                props = {}

        return {
            "哲学设定": props.get("哲学设定", {}),
            "心理特征": props.get("心理特征", ""),
            "核心矛盾": props.get("核心矛盾", ""),
            "行为模式": props.get("行为模式", ""),
            "成长弧光": props.get("成长弧光", ""),
        }

    # ============================================================
    # 行为预判生成
    # ============================================================

    def predict(
        self,
        role_name: str,
        scene_type: str,
        stage: Optional[str] = None,
        emotion: str = "平静",
    ) -> Dict[str, Any]:
        """
        生成行为预判

        Args:
            role_name: 角色名（如"林夕"）
            scene_type: 场景类型（战斗/情感/悬念/社交/冲突等）
            stage: 成长阶段（可选，如"小我期"、"大我期"）
            emotion: 情绪状态（平静/愤怒/悲伤/焦虑/恐惧/兴奋）

        Returns:
            {
                "第一反应": "...",
                "后续行动": [...],
                "内心独白": "...",
                "推导依据": "...",
                "当前阶段": "...",
                "当前情绪": "..."
            }
        """
        # 加载数据
        core = self._get_core_data(role_name)
        extended = self._load_extended_data().get(role_name, {})

        # 检查是否有行为预判覆盖
        override = self._check_override(extended, scene_type, stage, emotion)
        if override:
            return override

        # 推导行为预判
        return self._derive_behavior(core, extended, scene_type, stage, emotion)

    def _check_override(
        self, extended: Dict, scene_type: str, stage: Optional[str], emotion: str
    ) -> Optional[Dict]:
        """检查是否有行为预判覆盖"""
        # 如果MD文件中定义了特定场景的行为预判，直接使用
        # 暂未实现，返回None
        return None

    def _derive_behavior(
        self,
        core: Dict,
        extended: Dict,
        scene_type: str,
        stage: Optional[str],
        emotion: str,
    ) -> Dict[str, Any]:
        """推导行为预判"""

        # 获取核心维度
        philosophy = core.get("哲学设定", {})
        psychological = core.get("心理特征", "")
        contradiction = core.get("核心矛盾", "")
        behavior_pattern = core.get("行为模式", "")

        # 根据情绪状态调整行为
        emotion_factor = self._get_emotion_factor(emotion)

        # 根据场景类型生成行为
        scene_template = self._get_scene_template(scene_type)

        # 推导第一反应
        first_reaction = self._derive_first_reaction(
            philosophy, psychological, emotion_factor, scene_type
        )

        # 推导后续行动
        actions = self._derive_actions(
            behavior_pattern, emotion_factor, scene_type, contradiction
        )

        # 推导内心独白
        inner_monologue = self._derive_inner_monologue(
            philosophy, contradiction, stage, emotion
        )

        # 生成推导依据
        evidence = self._generate_evidence(
            philosophy, psychological, contradiction, emotion
        )

        return {
            "第一反应": first_reaction,
            "后续行动": actions,
            "内心独白": inner_monologue,
            "推导依据": evidence,
            "当前阶段": stage or "默认阶段",
            "当前情绪": emotion,
        }

    def _get_emotion_factor(self, emotion: str) -> str:
        """获取情绪因子"""
        factors = {
            "平静": "按常规行为模式",
            "愤怒": "突破常规，冲动行动",
            "悲伤": "被动退缩，行动力下降",
            "焦虑": "犹豫拖延，可能留下破绽",
            "恐惧": "保守防御，逃避风险",
            "兴奋": "冒险冲动，过度自信",
        }
        return factors.get(emotion, "按常规行为模式")

    def _get_scene_template(self, scene_type: str) -> Dict:
        """获取场景模板"""
        templates = {
            "战斗": {"核心": "生死、代价、保护", "关注": "战斗风格、不畏死程度"},
            "情感": {"核心": "表达、羁绊、牺牲", "关注": "是否主动、付出程度"},
            "悬念": {"核心": "真相、隐瞒、揭示", "关注": "如何处理信息"},
            "社交": {"核心": "关系、利益、立场", "关注": "利益vs情感优先"},
            "冲突": {"核心": "立场、代价、选择", "关注": "如何站队、是否妥协"},
        }
        return templates.get(scene_type, {"核心": "未知", "关注": "未知"})

    def _derive_first_reaction(
        self, philosophy: Dict, psychological: str, emotion_factor: str, scene_type: str
    ) -> str:
        """推导第一反应"""
        # 简化逻辑：根据心理特征和情绪因子生成
        if "内敛" in psychological:
            base = "冷静观察，不主动"
        elif "高傲" in psychological:
            base = "自信展现，不容质疑"
        elif "暴躁" in psychological:
            base = "直接反应，不掩饰情绪"
        else:
            base = "按常规反应"

        if emotion_factor != "按常规行为模式":
            return f"{base}，但因{emotion_factor}"
        return base

    def _derive_actions(
        self,
        behavior_pattern: str,
        emotion_factor: str,
        scene_type: str,
        contradiction: str,
    ) -> List[str]:
        """推导后续行动"""
        actions = []

        # 根据行为模式提取关键动作
        if "默默" in behavior_pattern:
            actions.append("默默观察，积蓄力量")
        if "爆发" in behavior_pattern:
            actions.append("关键时刻一击必杀")
        if "拒绝" in behavior_pattern:
            actions.append("拒绝他人帮助，独自行动")
        if "独行" in behavior_pattern:
            actions.append("独自处理，不依赖他人")

        if not actions:
            actions.append("按常规方式行动")

        return actions[:3]  # 最多返回3个行动

    def _derive_inner_monologue(
        self, philosophy: Dict, contradiction: str, stage: Optional[str], emotion: str
    ) -> str:
        """推导内心独白"""
        concern = philosophy.get("核心关切", "")
        if concern:
            return f"思考：{concern}"
        if contradiction:
            return f"挣扎于：{contradiction}"
        return "保持冷静，观察局势"

    def _generate_evidence(
        self, philosophy: Dict, psychological: str, contradiction: str, emotion: str
    ) -> str:
        """生成推导依据"""
        parts = []
        if psychological:
            parts.append(f"心理特征({psychological})")
        if contradiction:
            parts.append(f"核心矛盾({contradiction})")
        if emotion != "平静":
            parts.append(f"情绪触发({emotion})")
        return " + ".join(parts) if parts else "基础设定"

    # ============================================================
    # 辅助方法
    # ============================================================

    def list_roles(self) -> List[str]:
        """列出所有有行为数据的角色"""
        extended = self._load_extended_data()
        return list(extended.keys())

    def get_role_history(self, role_name: str) -> Dict:
        """获取角色过往经历"""
        extended = self._load_extended_data()
        return extended.get(role_name, {}).get("过往经历", {})

    def get_role_emotion_triggers(self, role_name: str) -> Dict:
        """获取角色情绪触发"""
        extended = self._load_extended_data()
        return extended.get(role_name, {}).get("情绪触发", {})


# ============================================================
# 统一工作流
# ============================================================


class NovelWorkflow:
    """
    众生界小说工作流 v3.0 (Qdrant)

    提供统一的接口访问：
    - 小说设定库（势力、角色、力量体系）
    - 创作技法库（11维度技法）
    - 案例库（跨题材标杆案例）
    - 知识图谱（实体关系网络）
    """

    def __init__(self):
        # 初始化Qdrant客户端（优先Docker）
        self.client, self.client_type = get_qdrant_client()

        # 初始化各检索器
        self.settings = NovelSettingsSearcher(self.client)
        self.techniques = TechniqueSearcher(self.client)
        self.cases = CaseSearcher(self.client)
        self.imagery = ImagerySearcher(self.client)  # 诗词意象检索器
        self.graph = KnowledgeGraphReader()
        self.scene_mapping = SceneWriterMapping()

        # 初始化经验写入器（增强检索功能）
        self.experience_writer = None
        if _experience_writer_available:
            try:
                self.experience_writer = ExperienceWriter(
                    log_dir=str(PROJECT_DIR / "章节经验日志")
                )
            except Exception:
                pass

    # ==================== 小说设定接口 ====================

    def search_novel(
        self, query: str, entity_type: Optional[str] = None, top_k: int = 5
    ) -> List[Dict]:
        return self.settings.search(query, entity_type, top_k)

    def get_character(self, name: str) -> Optional[Dict]:
        return self.settings.get_character(name)

    def get_faction(self, name: str) -> Optional[Dict]:
        return self.settings.get_faction(name)

    def get_power_branch(self, name: str) -> Optional[Dict]:
        return self.settings.get_power_branch(name)

    def list_characters(self) -> List[Dict]:
        return self.settings.list_all("角色")

    def list_factions(self) -> List[Dict]:
        return self.settings.list_all("势力")

    def list_power_branches(self) -> List[Dict]:
        return self.settings.list_all("力量派别")

    # ==================== 创作技法接口 ====================

    def search_techniques(
        self, query: str, dimension: Optional[str] = None, top_k: int = 5
    ) -> List[Dict]:
        return self.techniques.search(query, dimension, top_k)

    def get_techniques_by_dimension(self, dimension: str) -> List[Dict]:
        return self.techniques.get_by_dimension(dimension)

    def list_technique_dimensions(self) -> List[str]:
        return self.techniques.list_dimensions()

    # ==================== 案例库接口 ====================

    def search_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        return self.cases.search(query, scene_type, genre, top_k)

    def list_case_scenes(self) -> List[str]:
        return self.cases.list_scene_types()

    # ==================== 诗词意象接口 ====================

    def search_imagery(
        self,
        query: str,
        world_context: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        检索诗词意象

        Args:
            query: 查询文本（如"虚无感、战争后"）
            world_context: 世界观上下文（"众生界" / None）
            top_k: 返回数量

        Returns:
            意象列表，包含name、emotion_core、usage_examples等
        """
        return self.imagery.search(query, world_context, top_k)

    def list_imagery(self, world_context: Optional[str] = None) -> List[str]:
        """列出所有意象名称"""
        return self.imagery.list_all(world_context)

    def create_poetry(
        self,
        scene: str,
        emotion: Optional[str] = None,
        world_context: Optional[str] = None,
        character: Optional[str] = None,
        poetry_type: str = "七言诗",
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        诗词创作接口（返回意象和情感分析，由LLM生成最终诗句）

        Args:
            scene: 场景描述
            emotion: 情感方向（可选，自动分析）
            world_context: 世界观上下文（"众生界" / None）
            character: 角色名（众生界模式）
            poetry_type: 诗词类型
            top_k: 检索意象数量

        Returns:
            {
                "imagery": [...],  # 契合的意象列表
                "emotion_core": "...",  # 情感内核
                "world_context": "...",  # 世界观上下文
                "character_style": {...}  # 角色诗风（可选）
            }
        """
        # 检索意象
        query = f"{scene} {emotion or ''}".strip()
        imagery = self.search_imagery(query, world_context, top_k)

        # 提取情感内核
        emotion_core = None
        if imagery:
            emotion_core = imagery[0].get("emotion_core", "")

        result = {
            "imagery": imagery,
            "emotion_core": emotion_core,
            "world_context": world_context,
            "poetry_type": poetry_type,
        }

        # 众生界模式：添加角色诗风
        if world_context == "众生界" and character:
            # 从知识图谱获取角色信息
            char_entity = self.graph.get_entity(character)
            if char_entity:
                result["character_style"] = {
                    "name": character,
                    "philosophy": char_entity.get("属性", {}).get("哲学设定", ""),
                }

        return result

    # ==================== 知识图谱接口 ====================

    def get_knowledge_graph(self) -> Dict:
        return {
            "实体": self.graph.get_all_entities(),
            "关系": self.graph.get_all_relations(),
        }

    def get_entity_relations(self, name: str) -> List[Dict]:
        return self.graph.get_entity_relations(name)

    def get_graph_stats(self) -> Dict:
        return self.graph.get_stats()

    # ==================== 角色深度设定接口 ====================

    def get_character_backstory(self, name: str) -> Dict:
        """
        获取角色过往经历

        Args:
            name: 角色名（如"林夕"）

        Returns:
            {
                "童年": {"内容": "...", "影响": "..."},
                "成长期": {...},
                "关键事件": {...},
                ...
            }
        """
        # 查找角色实体
        entities = self.graph.get_all_entities()
        char_entity = None

        for eid, entity in entities.items():
            if entity.get("类型") == "角色" and entity.get("名称") == name:
                char_entity = entity
                break

        if not char_entity:
            return {}

        props = char_entity.get("属性", {})
        if isinstance(props, str):
            try:
                props = json.loads(props)
            except:
                props = {}

        return props.get("过往经历", {})

    def get_character_emotion_triggers(self, name: str) -> Dict:
        """
        获取角色情绪触发

        Args:
            name: 角色名（如"林夕"）

        Returns:
            {
                "平静": {"触发条件": "...", "行为变化": "..."},
                "愤怒": {...},
                ...
            }
        """
        entities = self.graph.get_all_entities()
        char_entity = None

        for eid, entity in entities.items():
            if entity.get("类型") == "角色" and entity.get("名称") == name:
                char_entity = entity
                break

        if not char_entity:
            return {}

        props = char_entity.get("属性", {})
        if isinstance(props, str):
            try:
                props = json.loads(props)
            except:
                props = {}

        return props.get("情绪触发", {})

    def get_character_behavior_imprints(self, name: str) -> List[Dict]:
        """
        获取角色行为烙印

        Args:
            name: 角色名（如"林夕"）

        Returns:
            [
                {"触发情境": "...", "行为反应": "...", "依据": "..."},
                ...
            ]
        """
        entities = self.graph.get_all_entities()
        char_entity = None

        for eid, entity in entities.items():
            if entity.get("类型") == "角色" and entity.get("名称") == name:
                char_entity = entity
                break

        if not char_entity:
            return []

        props = char_entity.get("属性", {})
        if isinstance(props, str):
            try:
                props = json.loads(props)
            except:
                props = {}

        return props.get("行为烙印", [])

    def get_character_full_profile(self, name: str) -> Dict:
        """
        获取角色完整档案（包含基础设定和深度设定）

        Args:
            name: 角色名

        Returns:
            {
                "名称": "...",
                "类型": "角色",
                "基础设定": {...},  # 势力、血脉等
                "哲学设定": {...},  # 哲学流派、核心关切等
                "过往经历": {...},  # 童年、成长期、关键事件等
                "情绪触发": {...},  # 平静、愤怒、悲伤等
                "行为烙印": [...],  # 触发情境-行为反应-依据
            }
        """
        entities = self.graph.get_all_entities()
        char_entity = None
        char_id = None

        for eid, entity in entities.items():
            if entity.get("类型") == "角色" and entity.get("名称") == name:
                char_entity = entity
                char_id = eid
                break

        if not char_entity:
            return {}

        props = char_entity.get("属性", {})
        if isinstance(props, str):
            try:
                props = json.loads(props)
            except:
                props = {}

        return {
            "名称": char_entity.get("名称"),
            "类型": char_entity.get("类型"),
            "实体ID": char_id,
            "基础设定": {
                k: v
                for k, v in props.items()
                if k not in ["哲学设定", "过往经历", "情绪触发", "行为烙印"]
            },
            "哲学设定": props.get("哲学设定", {}),
            "过往经历": props.get("过往经历", {}),
            "情绪触发": props.get("情绪触发", {}),
            "行为烙印": props.get("行为烙印", []),
        }

    # ==================== 场景预判模板接口 ====================

    def get_scene_behavior_template(self, scene_type: str) -> Optional[Dict]:
        """
        获取场景行为预判模板

        Args:
            scene_type: 场景类型（如"战斗"、"情感"、"悬念"）

        Returns:
            {
                "场景类型": "战斗",
                "核心要素": "生死、代价、保护",
                "常见行为关注点": "...",
                "情绪影响": {...}
            }
        """
        entities = self.graph.get_all_entities()
        template_id = f"template_{scene_type}"

        if template_id in entities:
            return entities[template_id]
        return None

    def list_scene_templates(self) -> List[str]:
        """列出所有场景预判模板"""
        entities = self.graph.get_all_entities()
        templates = []
        for eid, entity in entities.items():
            if entity.get("类型") == "预判模板":
                templates.append(entity.get("名称", eid))
        return templates

    def get_emotion_states_reference(self) -> Dict:
        """
        获取情绪状态对照表

        Returns:
            {
                "平静": {"认知影响": "...", "行为倾向": "...", "典型表现": "..."},
                "愤怒": {...},
                ...
            }
        """
        entities = self.graph.get_all_entities()
        if "emotion_states_reference" in entities:
            return entities["emotion_states_reference"].get("属性", {})
        return {}

    # ==================== 文明技术基础接口 ====================

    def get_civilization_tech(
        self, civilization: str, tech_domain: Optional[str] = None
    ) -> List[Dict]:
        """
        获取文明技术基础设定

        Args:
            civilization: 文明类型（"科技文明"/"AI文明"/"异化人文明"）
            tech_domain: 技术领域（可选，如"量子计算"/"时空理论"）

        Returns:
            技术设定列表

        示例：
            workflow.get_civilization_tech("科技文明", "量子计算")
        """
        entities = self.graph.get_all_entities()
        results = []

        for eid, entity in entities.items():
            if entity.get("类型") != "技术基础":
                continue

            props = entity.get("属性", {})
            if isinstance(props, str):
                try:
                    props = json.loads(props)
                except:
                    props = {}

            # 过滤文明类型
            if props.get("文明") != civilization:
                continue

            # 过滤技术领域（如果指定）
            if tech_domain and props.get("技术领域") != tech_domain:
                continue

            results.append(
                {
                    "id": eid,
                    "名称": entity.get("名称"),
                    "文明": props.get("文明"),
                    "技术领域": props.get("技术领域"),
                    "来源": props.get("来源"),
                    "关键技术": props.get("关键技术", []),
                    "情节应用": props.get("情节应用", []),
                }
            )

        return results

    def list_civilization_types(self) -> List[str]:
        """列出所有文明类型"""
        return ["科技文明", "AI文明", "异化人文明"]

    def list_tech_domains(self, civilization: Optional[str] = None) -> List[str]:
        """列出所有技术领域（可按文明过滤）"""
        entities = self.graph.get_all_entities()
        domains = set()

        for eid, entity in entities.items():
            if entity.get("类型") != "技术基础":
                continue

            props = entity.get("属性", {})
            if isinstance(props, str):
                try:
                    props = json.loads(props)
                except:
                    props = {}

            if civilization and props.get("文明") != civilization:
                continue

            domain = props.get("技术领域")
            if domain:
                domains.add(domain)

        return sorted(list(domains))

    # ==================== 行为预判综合接口 ====================

    def predict_character_behavior(
        self,
        character_name: str,
        scene_type: str,
        emotion_state: str = "平静",
        stage: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        预测角色在特定场景下的行为

        Args:
            character_name: 角色名（如"林夕"）
            scene_type: 场景类型（如"战斗"、"情感"、"悬念"）
            emotion_state: 情绪状态（默认"平静"）
            stage: 成长阶段（可选）

        Returns:
            {
                "角色": "林夕",
                "场景类型": "战斗",
                "情绪状态": "平静",
                "第一反应": "...",
                "后续行动": [...],
                "内心独白": "...",
                "行为烙印": [...],
                "情绪触发": {...},
                "推导依据": "..."
            }
        """
        # 获取角色完整档案
        profile = self.get_character_full_profile(character_name)
        if not profile:
            return {"错误": f"未找到角色: {character_name}"}

        # 获取场景模板
        template = self.get_scene_behavior_template(scene_type)

        # 获取情绪状态对照
        emotion_ref = self.get_emotion_states_reference()
        emotion_factor = emotion_ref.get(emotion_state, {})

        # 从行为烙印中查找匹配的触发情境
        imprints = profile.get("行为烙印", [])
        matched_imprint = None
        for imp in imprints:
            if isinstance(imp, dict):
                trigger = imp.get("触发情境", "")
                # 简单匹配：如果场景类型出现在触发情境中
                if scene_type in trigger or trigger in scene_type:
                    matched_imprint = imp
                    break

        # 从情绪触发中获取当前情绪的行为变化
        emotion_triggers = profile.get("情绪触发", {})
        current_emotion_trigger = emotion_triggers.get(emotion_state, {})

        # 构建行为预判
        philosophy = profile.get("哲学设定", {})
        core_concern = (
            philosophy.get("核心关切", "") if isinstance(philosophy, dict) else ""
        )

        # 生成第一反应
        if matched_imprint:
            first_reaction = matched_imprint.get("行为反应", "按常规反应")
        elif current_emotion_trigger:
            first_reaction = current_emotion_trigger.get("行为变化", "按常规反应")
        else:
            first_reaction = (
                f"基于{profile.get('基础设定', {}).get('心理特征', '设定')}的反应"
            )

        # 生成后续行动
        actions = []
        if matched_imprint:
            actions.append(f"依据{matched_imprint.get('依据', '过往经历')}")
        for imp in imprints[:2]:
            if isinstance(imp, dict) and imp != matched_imprint:
                actions.append(f"{imp.get('触发情境', '')}: {imp.get('行为反应', '')}")

        # 生成内心独白
        inner_monologue = ""
        if core_concern:
            inner_monologue = f"思考：{core_concern}"
        elif current_emotion_trigger:
            inner_monologue = (
                f"情绪：{current_emotion_trigger.get('触发条件', '默认状态')}"
            )

        return {
            "角色": character_name,
            "场景类型": scene_type,
            "情绪状态": emotion_state,
            "成长阶段": stage or "默认阶段",
            "第一反应": first_reaction,
            "后续行动": actions[:3],
            "内心独白": inner_monologue,
            "行为烙印": imprints,
            "情绪触发": current_emotion_trigger,
            "推导依据": {
                "哲学关切": core_concern,
                "情绪影响": emotion_factor.get("行为倾向", ""),
                "场景核心": template.get("属性", {}).get("核心要素", "")
                if template
                else "",
            },
        }

    # ==================== 统计信息 ====================

    def get_stats(self) -> Dict[str, Any]:
        return {
            "小说设定库": {
                "总数": self.settings.count(),
            },
            "创作技法库": {
                "总数": self.techniques.count(),
                "维度": self.techniques.list_dimensions(),
            },
            "案例库": {
                "总数": self.cases.count(),
            },
            "诗词意象库": {
                "总数": self.imagery.count(),
                "众生界特色意象": self.imagery.list_all("众生界"),
            },
            "知识图谱": self.graph.get_stats(),
            "场景-作家映射": self.scene_mapping.get_scene_stats(),
        }

    # ==================== 场景-作家映射接口 ====================

    def get_scene_collaboration(self, scene_type: str) -> Optional[Dict]:
        """获取场景的作家协作结构"""
        return self.scene_mapping.get_scene_collaboration(scene_type)

    def get_scene_primary_writer(self, scene_type: str) -> Optional[str]:
        """获取场景的主责作家"""
        return self.scene_mapping.get_primary_writer(scene_type)

    def get_scene_workflow_order(self, scene_type: str) -> List[str]:
        """获取场景的作家执行顺序"""
        return self.scene_mapping.get_workflow_order(scene_type)

    def get_writer_contributions(self, scene_type: str, writer: str) -> List[str]:
        """获取指定作家在该场景中的贡献项"""
        return self.scene_mapping.get_writer_contributions(scene_type, writer)

    def get_scene_case_filter(self, scene_type: str) -> Optional[Dict]:
        """获取场景的案例库过滤配置"""
        return self.scene_mapping.get_case_library_filter(scene_type)

    def list_active_scenes(self) -> List[str]:
        """列出所有已激活的场景"""
        return self.scene_mapping.list_active_scenes()

    def list_can_activate_scenes(self) -> List[str]:
        """列出所有可激活的场景"""
        return self.scene_mapping.list_can_activate_scenes()

    def list_pending_scenes(self) -> List[str]:
        """列出所有待激活的场景"""
        return self.scene_mapping.list_pending_scenes()

    def list_inactive_scenes(self) -> List[str]:
        """列出所有不激活的场景"""
        return self.scene_mapping.list_inactive_scenes()

    def get_writer_role(self, writer: str) -> Optional[Dict]:
        """获取作家的角色定义"""
        return self.scene_mapping.get_writer_role(writer)

    def get_all_writers(self) -> List[str]:
        """获取所有作家列表"""
        return self.scene_mapping.get_all_writers()

    def get_scenes_by_writer(self, writer: str) -> List[str]:
        """获取指定作家参与的所有场景"""
        return self.scene_mapping.get_scenes_by_writer(writer)

    # ==================== 章节经验检索接口 ====================

    def retrieve_chapter_experience(
        self, current_chapter: int, scene_types: List[str], writer_name: str = "all"
    ) -> Dict[str, List]:
        """
        检索前几章的经验日志 + 用户修改要求

        Args:
            current_chapter: 当前章节号
            scene_types: 当前章节涉及的场景类型列表
            writer_name: 当前创作的作家名（如"墨言"），默认"all"表示不过滤

        Returns:
            经验上下文字典
        """
        log_dir = PROJECT_DIR / "章节经验日志"

        experiences = {
            "what_worked": [],
            "what_didnt_work": [],
            "insights": [],
            "for_next_chapter": [],
            "user_modification_requests": [],
        }

        # Step 1: 检索前3章日志
        if log_dir.exists():
            for chapter in range(current_chapter - 1, max(0, current_chapter - 4), -1):
                log_file = log_dir / f"第{chapter}章_log.json"
                if not log_file.exists():
                    continue
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        log = json.load(f)
                    experiences["what_worked"].extend(log.get("what_worked", []))
                    experiences["what_didnt_work"].extend(
                        log.get("what_didnt_work", [])
                    )
                    experiences["for_next_chapter"].extend(
                        log.get("for_next_chapter", [])
                    )
                    for insight in log.get("insights", []):
                        if self._is_insight_relevant(insight, scene_types):
                            experiences["insights"].append(insight)
                except Exception as e:
                    print(f"[经验检索] 读取日志失败 {log_file}: {e}")

        # Step 2: 检索用户修改要求
        standards_file = PROJECT_DIR / "写作标准积累" / "用户修改要求记录.md"
        pending_requests = self._extract_pending_requests(standards_file)

        # Step 2.1: 按作家过滤
        filtered_requests = []
        for req in pending_requests:
            applies_to = req.get("适用作家", ["all"])
            if writer_name == "all" or "all" in applies_to or writer_name in applies_to:
                filtered_requests.append(req)

        # Step 2.2: 按优先级排序
        priority_order = {"L1": 0, "L2": 1, "L3": 2, "L4": 3}
        filtered_requests.sort(
            key=lambda r: priority_order.get(r.get("标准层级", "L3"), 2)
        )

        # Step 2.3: 限制数量
        filtered_requests = filtered_requests[:5]

        experiences["user_modification_requests"] = filtered_requests
        return experiences

    def _is_insight_relevant(self, insight: Dict, scene_types: List[str]) -> bool:
        """判断洞察是否与当前场景相关"""
        scene_condition = insight.get("scene_condition", "")

        # 场景关键词映射
        scene_keywords = {
            "战斗": ["战斗", "代价", "胜利", "牺牲", "群体"],
            "人物": ["人物", "角色", "情感", "成长", "出场"],
            "世界观": ["世界观", "势力", "设定", "背景"],
            "剧情": ["剧情", "伏笔", "悬念", "反转"],
            "氛围": ["氛围", "意境", "描写", "环境"],
        }

        for scene_type in scene_types:
            keywords = scene_keywords.get(scene_type, [])
            for keyword in keywords:
                if keyword in scene_condition or keyword in insight.get("content", ""):
                    return True

        return False

    def _extract_pending_requests(self, standards_file: Path) -> List[Dict]:
        """从用户修改要求记录.md中提取未应用的修改要求"""
        import re

        pending = []
        if not standards_file.exists():
            return pending

        with open(standards_file, "r", encoding="utf-8") as f:
            content = f.read()

        request_blocks = re.findall(
            r"### (REQ-\d+).*?(?=### REQ-\d+|## |$)", content, re.DOTALL
        )

        for block in request_blocks:
            req_id = re.search(r"REQ-(\d+)", block)
            level = re.search(r"标准层级:\s*(L[1-4])", block)
            status = re.search(r"状态:\s*(\w+)", block)
            applies_to = re.search(r"适用作家:\s*\[([^\]]+)\]", block)
            standard = re.search(r"精炼标准:\s*(.+?)(?=\n|状态)", block, re.DOTALL)

            if status and status.group(1) == "pending":
                pending.append(
                    {
                        "id": req_id.group(0) if req_id else "REQ-???",
                        "标准层级": level.group(1) if level else "L3",
                        "适用作家": applies_to.group(1)
                        .replace('"', "")
                        .replace("'", "")
                        .split(",")
                        if applies_to
                        else ["all"],
                        "精炼标准": standard.group(1).strip() if standard else "",
                        "状态": "pending",
                    }
                )

        return pending

    def format_experience_context(self, experiences: Dict) -> str:
        """格式化经验上下文"""
        if not any(experiences.values()):
            return ""

        context = "【前章经验参考】\n\n"

        if experiences["what_worked"]:
            context += "有效做法（可参考）：\n"
            for item in experiences["what_worked"][:5]:
                context += f"  - {item}\n"
            context += "\n"

        if experiences["what_didnt_work"]:
            context += "避免重复错误：\n"
            for item in experiences["what_didnt_work"][:5]:
                context += f"  - {item}\n"
            context += "\n"

        if experiences["insights"]:
            context += "可复用洞察：\n"
            for insight in experiences["insights"][:3]:
                context += f"  - {insight.get('content', '')}\n"
                context += f"    适用：{insight.get('scene_condition', '')}\n"
            context += "\n"

        if experiences["for_next_chapter"]:
            context += "前章建议：\n"
            for item in experiences["for_next_chapter"][:5]:
                context += f"  - {item}\n"

        if experiences["user_modification_requests"]:
            context += "\n用户修改要求（待应用）：\n"
            for req in experiences["user_modification_requests"]:
                context += (
                    f"  [{req.get('标准层级', 'L3')}] {req.get('精炼标准', '')}\n"
                )

        return context

    def write_chapter_log(
        self, chapter_name: str, evaluation_result: Dict, techniques_used: List[Dict]
    ) -> Path:
        """
        将评估结果写入章节经验日志

        Args:
            chapter_name: 章节名称
            evaluation_result: Evaluator输出的评估结果
            techniques_used: 使用的技法列表

        Returns:
            日志文件路径
        """
        from datetime import datetime
        import re

        log_dir = PROJECT_DIR / "章节经验日志"
        log_dir.mkdir(parents=True, exist_ok=True)

        # 提取章节号
        match = re.search(r"第(\d+)章", chapter_name)
        chapter_num = match.group(1) if match else "0"

        log_file = log_dir / f"第{chapter_num}章_log.json"

        # 提取洞察
        insight_data = evaluation_result.get("反馈", {}).get("洞察提取", {})

        # 构建日志内容
        log_content = {
            "chapter": chapter_name,
            "created_at": datetime.now().isoformat(),
            "techniques_used": techniques_used,
            "what_worked": insight_data.get("有效做法", []),
            "what_didnt_work": insight_data.get("无效做法", []),
            "insights": [
                {
                    "content": i.get("content", ""),
                    "scene_condition": i.get("scene_condition", ""),
                    "reusable": i.get("可复用", True),
                }
                for i in insight_data.get("可复用洞察", [])
            ],
            "for_next_chapter": insight_data.get("给下一章建议", []),
            "user_modification_requests": insight_data.get("用户修改要求", []),
        }

        # 写入文件
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_content, f, ensure_ascii=False, indent=2)

        print(f"[经验写入] 已写入: {log_file}")
        return log_file

    # ==================== 增强版经验检索接口 ====================

    def retrieve_scene_experience_enhanced(self, scene_type: str) -> Dict[str, Any]:
        """
        按场景类型检索经验（增强版）

        使用ExperienceWriter的新检索API，提供更完整的经验汇总。

        Args:
            scene_type: 场景类型（如"战斗"、"情感"、"开篇"等）

        Returns:
            {
                "what_worked": 该场景成功做法列表,
                "what_didnt_work": 该场景失败做法列表,
                "recommended_techniques": 推荐技法列表,
                "forbidden_reminders": 禁止项提醒列表
            }
        """
        if self.experience_writer:
            return self.experience_writer.retrieve_scene_experience(scene_type)

        # 回退：返回空结果
        return {
            "what_worked": [],
            "what_didnt_work": [],
            "recommended_techniques": [],
            "forbidden_reminders": [],
        }

    def retrieve_technique_effectiveness(self, technique_name: str) -> Dict[str, Any]:
        """
        检索技法效果统计

        Args:
            technique_name: 技法名称

        Returns:
            {
                "average_score": 平均效果评分,
                "success_count": 成功使用次数（评分>=7）,
                "fail_count": 失败使用次数（评分<7）,
                "chapters_used": 使用过的章节列表,
                "best_scenes": 最佳场景类型列表,
                "worst_scenes": 最不适合场景列表
            }
        """
        if self.experience_writer:
            return self.experience_writer.retrieve_technique_effectiveness(
                technique_name
            )

        # 回退：返回默认统计
        return {
            "average_score": 0,
            "success_count": 0,
            "fail_count": 0,
            "chapters_used": [],
            "best_scenes": [],
            "worst_scenes": [],
            "total_uses": 0,
        }

    def get_recent_forbidden_candidates(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取最近的禁止项候选

        Args:
            days: 回溯天数（默认30天）

        Returns:
            禁止项候选列表
        """
        if self.experience_writer:
            return self.experience_writer.get_recent_forbidden_candidates(days)

        # 回退：返回空列表
        return []

    def get_phase1_writers(self, scene_type: str) -> List[str]:
        """
        获取场景的Phase 1前置作家列表

        根据scene_writer_mapping.json中的配置返回前置作家，
        而非固定返回苍澜、玄一、墨言三人。

        Args:
            scene_type: 场景类型

        Returns:
            前置作家列表
        """
        collab = self.scene_mapping.get_scene_collaboration(scene_type)
        if not collab:
            # 默认返回三人
            return ["苍澜", "玄一", "墨言"]

        # 从collaboration中提取phase为"前置"的作家
        phase1_writers = []
        for c in collab.get("collaboration", []):
            if c.get("phase") == "前置":
                phase1_writers.append(c.get("writer"))

        # 如果没有前置作家，返回默认三人
        if not phase1_writers:
            return ["苍澜", "玄一", "墨言"]

        return phase1_writers

    def get_phase1_dispatch(self, scene_type: str, scene_context: dict) -> dict:
        """
        Stage 4 Phase 1 灵感引擎分发

        根据配置决定走原流程或灵感引擎。
        返回 dict 含 mode + 对应字段。

        Args:
            scene_type: 场景类型
            scene_context: 场景上下文（大纲、角色、设定等）

        Returns:
            {
                "mode": "original" | "variants",
                "writers": List[str] (mode=original时),
                "variant_specs": List[dict] (mode=variants时)
            }

        设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §11
        """
        from core.inspiration.workflow_bridge import phase1_dispatch
        from core.config_loader import get_config

        original_writers = self.get_phase1_writers(scene_type)
        config = get_config()

        return phase1_dispatch(
            scene_type=scene_type,
            scene_context=scene_context,
            original_writers=original_writers,
            config=config,
        )

    def run_stage4_inspiration(
        self,
        scene_type: str,
        scene_context: dict,
        writer_caller,
        appraisal_raw: str,
    ) -> dict:
        """Stage 4 灵感引擎完整编排

        调用约定（两阶段）
        ------------------
        本方法需要外部进行两次调用，中间插入鉴赏师 Skill 执行：

        阶段 A — 获取鉴赏师 prompt：
            winner_spec = workflow.run_stage4_inspiration(
                scene_type, scene_context, writer_caller,
                appraisal_raw=None          # 第一次调用，不传 appraisal_raw
            )
            # winner_spec["skill_name"] 是鉴赏师 Skill 名
            # winner_spec["prompt"] 是需要发给鉴赏师的完整 prompt

        阶段 B — 提交鉴赏师结果，获取最终赢家：
            final_result = workflow.run_stage4_inspiration(
                scene_type, scene_context, writer_caller,
                appraisal_raw=appraisal_raw  # 第二次调用，传入鉴赏师响应
            )
            # final_result["winner_text"] 是最终选定的段落文本

        注意：两次调用之间变体列表由调用方负责缓存（candidates 字段在阶段 A
        的返回值中）。阶段 B 的 candidates 参数应传入阶段 A 返回的 candidates。
        详见架构文档：docs/superpowers/plans/2026-04-15-inspiration-orchestration.md

        Args:
            scene_type: 场景类型
            scene_context: 场景上下文
            writer_caller: 可调用，接收 spec dict，返回生成文本 str
            appraisal_raw: novelist-connoisseur Skill 返回的 JSON 字符串

        Returns:
            {
                "mode": str,
                "candidates": List[dict],      # 带文本的候选列表
                "winner_spec": dict | None,    # 鉴赏师调用规格
                "appraisal": AppraisalResult | None,
                "memory_point_id": str | None,
            }
        """
        from core.inspiration.workflow_bridge import (
            phase1_dispatch,
            execute_variants,
            select_winner_spec,
            record_winner,
        )
        from core.inspiration.appraisal_agent import (
            parse_appraisal_response,
            AppraisalParseError,
        )
        from core.config_loader import get_config

        config = get_config()
        original_writers = self.get_phase1_writers(scene_type)

        # Phase 1：分发（original / variants）
        dispatch = phase1_dispatch(
            scene_type=scene_type,
            scene_context=scene_context,
            original_writers=original_writers,
            config=config,
        )

        if dispatch["mode"] == "original":
            return {
                "mode": "original",
                "writers": dispatch["writers"],
                "candidates": [],
                "winner_spec": None,
                "appraisal": None,
                "memory_point_id": None,
            }

        specs = dispatch["variant_specs"]

        # Phase 2：执行变体生成
        candidates = execute_variants(specs=specs, writer_caller=writer_caller)

        # Phase 3：构造鉴赏师规格（供 Claude 调用 Skill）
        winner_spec = select_winner_spec(
            candidates=candidates,
            scene_context=scene_context,
        )

        # Phase 4：解析鉴赏师返回（由调用方传入 raw）
        appraisal = None
        memory_point_id = None
        if appraisal_raw:
            try:
                appraisal = parse_appraisal_response(appraisal_raw)
                memory_point_id = record_winner(
                    appraisal=appraisal,
                    candidates=candidates,
                    scene_context=scene_context,
                )
            except AppraisalParseError:
                pass  # 解析失败，不写记忆点

        return {
            "mode": "variants",
            "candidates": candidates,
            "winner_spec": winner_spec,
            "appraisal": appraisal,
            "memory_point_id": memory_point_id,
        }

    def run_stage5_5_negotiation(
        self,
        chapter_text: str,
        chapter_ref: str,
        scene_type: Optional[str] = None,
        connoisseur_raw: Optional[str] = None,
        accepted_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Stage 5.5 三方协商三段式编排。

        调用约定（三阶段）
        -----------------
        Phase A — 获取鉴赏师 prompt（connoisseur_raw=None, accepted_ids=None）:
            spec = workflow.run_stage5_5_negotiation(chapter_text, chapter_ref)
            # spec["status"] == "pending_connoisseur"
            # spec["skill_name"] / spec["prompt"] → 发给 novelist-connoisseur Skill

        Phase B — 提交鉴赏师 JSON，获取建议列表（connoisseur_raw=<json>, accepted_ids=None）:
            result = workflow.run_stage5_5_negotiation(
                chapter_text, chapter_ref, connoisseur_raw=raw
            )
            # result["status"] == "pending_author"          → 有建议，展示 display_text 给作者
            # result["status"] == "pending_author_skip_confirm" → 0条建议，Q1询问作者确认跳过

        Phase C — 提交作者决策，生成契约（connoisseur_raw=<json>, accepted_ids=[...]）:
            final = workflow.run_stage5_5_negotiation(
                chapter_text, chapter_ref,
                connoisseur_raw=raw, accepted_ids=["#1", "#2"]
            )
            # final["status"] == "contract_ready"
            # final["contract"] → CreativeContract 实例

        Q1 贯彻：accepted_ids=[] 时（全部驳回）→ contract.skipped_by_author=True

        Args:
            chapter_text:     整章文本（云溪润色后版本）
            chapter_ref:      章节标识（例 "第3章")
            scene_type:       场景类型，用于约束菜单筛选（None=全部）
            connoisseur_raw:  鉴赏师返回的 JSON 字符串（Phase B/C）
            accepted_ids:     作者采纳的建议 item_id 列表（Phase C）

        Returns:
            Phase A: {"status": "pending_connoisseur", "skill_name": str, "prompt": str}
            Phase B: {"status": "pending_author", "suggestions": [...], "display_text": str, ...}
                  or {"status": "pending_author_skip_confirm", "abstain_reason": str, ...}
            Phase C: {"status": "contract_ready", "contract": CreativeContract}
        """
        from core.inspiration.stage5_5 import (
            build_connoisseur_prompt,
            parse_connoisseur_response,
            suggestions_to_preserve_candidates,
            build_creative_contract,
        )
        from core.inspiration.constraint_library import ConstraintLibrary
        from core.inspiration.memory_point_sync import MemoryPointSync
        from core.inspiration.creative_contract import RejectedItem

        # ── Phase A：构造 prompt ──────────────────────────────────────────────
        if connoisseur_raw is None and accepted_ids is None:
            lib = ConstraintLibrary()
            menu = lib.as_menu(scene_type)

            try:
                mp_sync = MemoryPointSync()
                positive = mp_sync.list_recent("+", top_k=5)
                negative = mp_sync.list_recent("-", top_k=5)
            except Exception:
                positive, negative = [], []

            spec = build_connoisseur_prompt(
                chapter_text=chapter_text,
                chapter_ref=chapter_ref,
                menu_items=menu,
                positive_samples=positive,
                negative_samples=negative,
            )
            return {**spec, "status": "pending_connoisseur"}

        # ── Phase B：解析 connoisseur 返回 ────────────────────────────────────
        if connoisseur_raw is not None and accepted_ids is None:
            response = parse_connoisseur_response(connoisseur_raw)

            if not response.suggestions:
                # Q1：0条建议 → 不自动跳过，询问作者
                return {
                    "status": "pending_author_skip_confirm",
                    "abstain_reason": response.abstain_reason,
                    "menu_gap": response.menu_gap,
                    "overall_judgment": response.overall_judgment,
                }

            candidates = suggestions_to_preserve_candidates(response.suggestions)
            display_lines = [f"鉴赏师发现 {len(candidates)} 条创意建议："]
            for c in candidates:
                display_lines.append(
                    f"\n  {c.item_id} [段落 {c.scope.paragraph_index}]"
                    f" {c.applied_constraint_id}: {c.rationale}"
                )
            display_lines.append(
                "\n请回复采纳的 item_id 列表（例：['#1', '#2']），或 [] 全部驳回。"
            )

            return {
                "status": "pending_author",
                "suggestions": [
                    {
                        "item_id": s.item_id,
                        "paragraph": s.scope_paragraph_index,
                        "constraint": s.applied_constraint_id,
                        "rationale": s.rationale,
                        "confidence": s.confidence,
                    }
                    for s in response.suggestions
                ],
                "overall_judgment": response.overall_judgment,
                "display_text": "\n".join(display_lines),
            }

        # ── Phase C：生成契约 ─────────────────────────────────────────────────
        if connoisseur_raw is not None and accepted_ids is not None:
            response = parse_connoisseur_response(connoisseur_raw)
            all_candidates = suggestions_to_preserve_candidates(response.suggestions)

            accepted_set = set(accepted_ids)
            accepted = [c for c in all_candidates if c.item_id in accepted_set]
            rejected = [
                RejectedItem(item_id=c.item_id, reason="作者驳回")
                for c in all_candidates
                if c.item_id not in accepted_set
            ]

            skipped = not accepted and bool(response.suggestions)
            contract = build_creative_contract(
                accepted_items=accepted,
                rejected_items=rejected,
                chapter_ref=chapter_ref,
                skipped_by_author=skipped,
            )
            return {"status": "contract_ready", "contract": contract}

        # 参数组合不合法（只有 accepted_ids 但没有 connoisseur_raw）
        raise ValueError(
            "run_stage5_5_negotiation: accepted_ids 必须配合 connoisseur_raw 使用"
        )


# ============================================================
# 独立函数（可独立调用）
# ============================================================


def retrieve_chapter_experience(
    current_chapter: int, scene_types: List[str], writer_name: str = "all"
) -> Dict[str, List]:
    """
    检索前几章的经验日志（独立函数版本）

    可直接调用，无需实例化NovelWorkflow。

    Args:
        current_chapter: 当前章节号
        scene_types: 当前章节涉及的场景类型列表
        writer_name: 当前创作的作家名

    Returns:
        经验上下文字典
    """
    workflow = NovelWorkflow()
    return workflow.retrieve_chapter_experience(
        current_chapter, scene_types, writer_name
    )


def write_chapter_log(
    chapter_name: str, evaluation_result: Dict, techniques_used: List[Dict]
) -> Path:
    """
    写入章节经验日志（独立函数版本）

    可直接调用，无需实例化NovelWorkflow。
    """
    workflow = NovelWorkflow()
    return workflow.write_chapter_log(chapter_name, evaluation_result, techniques_used)


# ============================================================
# 命令行接口
# ============================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(description="众生界小说工作流 v3.0 (Qdrant)")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--search-novel", "-sn", type=str, help="检索小说设定")
    parser.add_argument("--search-technique", "-st", type=str, help="检索创作技法")
    parser.add_argument("--search-case", "-sc", type=str, help="检索案例")
    parser.add_argument("--dimension", "-d", type=str, help="技法维度过滤")
    parser.add_argument("--scene", "-s", type=str, help="场景类型过滤")
    parser.add_argument("--entity-type", "-t", type=str, help="实体类型过滤")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="返回数量")
    parser.add_argument("--scene-mapping", "-sm", type=str, help="查询场景-作家映射")
    parser.add_argument("--list-scenes", action="store_true", help="列出所有场景")
    parser.add_argument("--list-writers", action="store_true", help="列出所有作家")

    args = parser.parse_args()

    workflow = NovelWorkflow()

    if args.stats:
        stats = workflow.get_stats()
        print("=" * 60)
        print("众生界小说工作流 v3.0 (Qdrant)")
        print("=" * 60)

        print("\n【小说设定库】")
        print(f"  总数: {stats['小说设定库']['总数']}")

        print("\n【创作技法库】")
        print(f"  总数: {stats['创作技法库']['总数']}")
        print(f"  维度: {', '.join(stats['创作技法库']['维度'])}")

        print("\n【案例库】")
        print(f"  总数: {stats['案例库']['总数']}")
        print(f"  场景: {', '.join(stats['案例库']['场景类型'])}")

        print("\n【知识图谱】")
        graph_stats = stats["知识图谱"]
        print(f"  总实体: {graph_stats['总实体数']}")
        print(f"  总关系: {graph_stats['总关系数']}")

        print("\n【场景-作家映射】")
        scene_stats = stats.get("场景-作家映射", {})
        if scene_stats:
            print(f"  已激活: {scene_stats.get('active', 0)}")
            print(f"  可激活: {scene_stats.get('can_activate', 0)}")
            print(f"  待激活: {scene_stats.get('pending_activation', 0)}")
            print(f"  不激活: {scene_stats.get('inactive', 0)}")
            print(f"  总计: {scene_stats.get('total', 0)}")

        return

    if args.list_scenes:
        print("\n【已激活场景】")
        for scene in workflow.list_active_scenes():
            primary = workflow.get_scene_primary_writer(scene)
            print(f"  - {scene} (主责: {primary})")

        print("\n【可激活场景】")
        for scene in workflow.list_can_activate_scenes():
            primary = workflow.get_scene_primary_writer(scene)
            print(f"  - {scene} (主责: {primary})")

        print("\n【待激活场景】")
        for scene in workflow.list_pending_scenes():
            print(f"  - {scene}")

        print("\n【不激活场景】")
        for scene in workflow.list_inactive_scenes():
            print(f"  - {scene}")
        return

    if args.list_writers:
        print("\n【作家列表】")
        for writer in workflow.get_all_writers():
            role = workflow.get_writer_role(writer)
            if role:
                print(f"\n  {writer} - {role.get('role', '未知')}")
                print(f"    专长: {', '.join(role.get('specialty', []))}")
                print(f"    主责维度: {role.get('primary_dimension', '未知')}")
                scenes = workflow.get_scenes_by_writer(writer)
                print(f"    参与场景: {len(scenes)}个")
        return

    if args.scene_mapping:
        scene = args.scene_mapping
        collab = workflow.get_scene_collaboration(scene)
        if collab:
            print(f"\n【{scene} - 作家协作结构】")
            print(f"描述: {collab.get('description', '无')}")
            print(f"主责作家: {collab.get('primary_writer', '未知')}")
            print(f"执行顺序: {' → '.join(collab.get('workflow_order', []))}")
            print("\n【协作分工】")
            for c in collab.get("collaboration", []):
                print(f"\n  {c.get('writer', '未知')} ({c.get('phase', '未知')})")
                print(f"    角色: {c.get('role', '未知')}")
                print(f"    权重: {c.get('weight', 0):.0%}")
                print(f"    贡献: {', '.join(c.get('contribution', []))}")
        else:
            print(f"\n未找到场景: {scene}")
        return

    if args.search_novel:
        results = workflow.search_novel(args.search_novel, args.entity_type)
        print(f"\n检索小说设定: {args.search_novel}")
        print("=" * 60)
        for i, r in enumerate(results[: args.top_k], 1):
            print(f"\n[{i}] {r['name']} ({r['type']}) - {r['score']:.0%}")
            desc = r.get("description", "")[:200]
            if desc:
                print(f"    {desc}...")
        return

    if args.search_technique:
        results = workflow.search_techniques(args.search_technique, args.dimension)
        print(f"\n检索创作技法: {args.search_technique}")
        if args.dimension:
            print(f"维度过滤: {args.dimension}")
        print("=" * 60)
        for i, r in enumerate(results[: args.top_k], 1):
            print(f"\n[{i}] {r['name']} ({r['dimension']}) - {r['score']:.0%}")
            content = r.get("content", "")[:200]
            if content:
                print(f"    {content}...")
        return

    if args.search_case:
        results = workflow.search_cases(args.search_case, args.scene)
        print(f"\n检索案例: {args.search_case}")
        if args.scene:
            print(f"场景过滤: {args.scene}")
        print("=" * 60)
        for i, r in enumerate(results[: args.top_k], 1):
            print(f"\n[{i}] {r['novel_name']} ({r['scene_type']}) - {r['score']:.0%}")
            content = r.get("content", "")[:200]
            if content:
                print(f"    {content}...")
        return

    parser.print_help()


# ============================================================
# 场景契约系统接口
# ============================================================


def create_scene_contract(
    scene_id: str, chapter_id: str, scene_outline: Optional[Dict] = None
) -> "SceneContract":
    """
    创建场景契约

    Args:
        scene_id: 场景ID
        chapter_id: 章节ID
        scene_outline: 场景大纲（可选）

    Returns:
        场景契约对象
    """
    from core.scene_contract import SceneContract, create_contract_from_outline

    if scene_outline:
        return create_contract_from_outline(scene_outline, chapter_id)

    return SceneContract(scene_id=scene_id, chapter_id=chapter_id)


def load_scene_contract(chapter_id: str, scene_id: str) -> Optional["SceneContract"]:
    """
    加载场景契约

    Args:
        chapter_id: 章节ID
        scene_id: 场景ID

    Returns:
        场景契约对象，如果不存在返回None
    """
    from core.scene_contract import SceneContractStore

    store = SceneContractStore(chapter_id)
    return store.load_contract(scene_id)


def save_scene_contract(contract: "SceneContract") -> Path:
    """
    保存场景契约

    Args:
        contract: 场景契约对象

    Returns:
        契约文件路径
    """
    from core.scene_contract import SceneContractStore

    store = SceneContractStore(contract.chapter_id)
    return store.save_contract(contract)


def validate_scene_contracts(chapter_id: str) -> Dict:
    """
    校验章节的所有场景契约

    Args:
        chapter_id: 章节ID

    Returns:
        校验结果
    """
    from core.contract_sync import validate_chapter_contracts

    return validate_chapter_contracts(chapter_id)


def get_contract_dependency_graph(chapter_id: str) -> Dict:
    """
    获取章节的场景依赖图

    Args:
        chapter_id: 章节ID

    Returns:
        依赖图
    """
    from core.scene_contract import SceneContractStore

    store = SceneContractStore(chapter_id)
    return store.get_dependency_graph()


def get_scene_execution_plan(chapter_id: str) -> Dict:
    """
    获取场景执行计划（包括并行分组）

    Args:
        chapter_id: 章节ID

    Returns:
        执行计划
    """
    from core.contract_sync import ContractSyncManager

    manager = ContractSyncManager(chapter_id)
    return manager.get_execution_plan()


def register_scene_start(chapter_id: str, scene_id: str, timeout: int = 300) -> Dict:
    """
    注册场景开始（用于并行创作协调）

    Args:
        chapter_id: 章节ID
        scene_id: 场景ID
        timeout: 等待依赖的超时时间（秒）

    Returns:
        注册结果
    """
    from core.contract_sync import ContractSyncManager

    manager = ContractSyncManager(chapter_id)
    return manager.register_scene_start(scene_id, timeout)


def register_scene_complete(
    chapter_id: str, scene_id: str, updated_contract: Optional["SceneContract"] = None
) -> Dict:
    """
    注册场景完成

    Args:
        chapter_id: 章节ID
        scene_id: 场景ID
        updated_contract: 更新后的契约（可选）

    Returns:
        完成结果
    """
    from core.contract_sync import ContractSyncManager

    manager = ContractSyncManager(chapter_id)
    return manager.register_scene_complete(scene_id, updated_contract)


if __name__ == "__main__":
    main()
