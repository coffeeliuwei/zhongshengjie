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
        """列出所有场景类型"""
        results = self.client.scroll(
            collection_name=CASE_COLLECTION,
            with_payload=True,
            with_vectors=False,
            limit=10000,
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
        self.graph = KnowledgeGraphReader()
        self.scene_mapping = SceneWriterMapping()

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
                "场景类型": self.cases.list_scene_types(),
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


if __name__ == "__main__":
    main()
