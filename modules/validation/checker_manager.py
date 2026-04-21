#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查管理器 - 整合检查功能
合并 check_sources.py、check_missing.py、check_relations.py、check_entity.py、check_bloodline.py

功能：
1. 检查案例库来源分布
2. 检查知识图谱缺失实体
3. 检查关系格式
4. 检查实体结构
5. 检查血脉格式

使用方法：
    from modules.validation import CheckerManager

    checker = CheckerManager()
    checker.check_sources()      # 检查案例库来源
    checker.check_missing()      # 检查缺失实体
    checker.check_all()          # 运行所有检查
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# [N14 2026-04-18] 改为 core 包内的 config_loader
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from core.config_loader import (
        get_project_root,
        get_vectorstore_dir,
        get_knowledge_graph_path,
    )

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False

# Windows 编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class CheckerManager:
    """
    检查管理器

    整合检查功能：
    1. check_sources.py - 案例库来源检查
    2. check_missing.py - 缺失实体检查
    3. check_relations.py - 关系格式检查
    4. check_entity.py - 实体结构检查
    5. check_bloodline.py - 血脉格式检查
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化检查管理器

        Args:
            project_root: 项目根目录
        """
        if HAS_CONFIG_LOADER:
            self.project_root = project_root or get_project_root()
            self.vectorstore_dir = get_vectorstore_dir()
            self.knowledge_graph_path = get_knowledge_graph_path()
        else:
            self.project_root = project_root or Path.cwd()
            self.vectorstore_dir = self.project_root / ".vectorstore"
            self.knowledge_graph_path = self.vectorstore_dir / "knowledge_graph.json"
        self.qdrant_dir = self.vectorstore_dir / "qdrant"

    def _load_knowledge_graph(self) -> Optional[Dict]:
        """加载知识图谱"""
        if not self.knowledge_graph_path.exists():
            return None
        try:
            with open(self.knowledge_graph_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[错误] 加载知识图谱失败: {e}")
            return None

    def check_sources(self) -> Dict[str, Any]:
        """
        检查案例库来源

        整合 check_sources.py 功能

        Returns:
            {
                "total_cases": int,
                "genres": Dict[str, int],
                "novels_count": int,
                "novels_sample": List[str]
            }
        """
        results = {
            "total_cases": 0,
            "genres": {},
            "novels_count": 0,
            "novels_sample": [],
            "error": None,
        }

        if not self.qdrant_dir.exists():
            results["error"] = "Qdrant 数据目录不存在"
            return results

        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(path=str(self.qdrant_dir))
            result = client.scroll(
                collection_name="case_library",
                limit=6000,
                with_payload=True,
                with_vectors=False,
            )

            cases = result[0]
            novels = set()

            for p in cases:
                payload = p.payload
                genre = payload.get("genre", "未知")
                results["genres"][genre] = results["genres"].get(genre, 0) + 1
                novels.add(payload.get("novel_name", "未知"))

            results["total_cases"] = len(cases)
            results["novels_count"] = len(novels)
            results["novels_sample"] = list(novels)[:20]

        except ImportError:
            results["error"] = "qdrant_client 未安装"
        except Exception as e:
            results["error"] = str(e)

        return results

    def check_missing(self) -> Dict[str, Any]:
        """
        检查知识图谱中缺失的实体

        整合 check_missing.py 功能

        Returns:
            {
                "name_mapping_count": int,
                "source_entity_count": int,
                "target_entity_count": int,
                "missing_sources": List[str],
                "missing_targets": List[str]
            }
        """
        data = self._load_knowledge_graph()
        if not data:
            return {"error": "无法加载知识图谱"}

        entities = data.get("实体", {})
        relations = data.get("关系", [])

        # 构建 name_to_id 映射
        name_to_id = {}
        for eid, e in entities.items():
            name = e.get("名称") or e.get("属性", {}).get("名称", "")
            if name:
                name_to_id[name] = eid

        # 收集关系中的实体名称
        source_names = set()
        target_names = set()
        for rel in relations:
            source = rel.get("源实体", "")
            target = rel.get("目标实体", "")
            if source:
                source_names.add(source)
            if target:
                target_names.add(target)

        # 找出缺失的名称
        missing_sources = list(source_names - set(name_to_id.keys()))[:20]
        missing_targets = list(target_names - set(name_to_id.keys()))[:20]

        return {
            "name_mapping_count": len(name_to_id),
            "source_entity_count": len(source_names),
            "target_entity_count": len(target_names),
            "missing_sources": missing_sources,
            "missing_targets": missing_targets,
        }

    def check_relations(self) -> Dict[str, Any]:
        """
        检查关系格式

        整合 check_relations.py 功能

        Returns:
            {
                "total_relations": int,
                "sample_relations": List[Dict],
                "char_prefix_count": int,
                "name_relations_count": int
            }
        """
        data = self._load_knowledge_graph()
        if not data:
            return {"error": "无法加载知识图谱"}

        relations = data.get("关系", [])

        # 检查格式
        char_relations = [
            r for r in relations if r.get("源实体", "").startswith("char_")
        ]
        name_relations = [
            r
            for r in relations
            if not r.get("源实体", "").startswith("char_")
            and not r.get("源实体", "").startswith("faction_")
        ]

        return {
            "total_relations": len(relations),
            "sample_relations": relations[:5],
            "char_prefix_count": len(char_relations),
            "name_relations_count": len(name_relations),
        }

    def check_entity(self) -> Dict[str, Any]:
        """
        检查实体结构

        整合 check_entity.py 功能

        Returns:
            {
                "power_entities": Dict,
                "era_entities": Dict,
                "character_entities": Dict
            }
        """
        data = self._load_knowledge_graph()
        if not data:
            return {"error": "无法加载知识图谱"}

        entities = data.get("实体", {})

        results = {
            "power_entities": {},
            "era_entities": {},
            "character_entities": {},
        }

        # 检查力量体系实体
        power = entities.get("power_cultivation", {})
        if power:
            results["power_entities"] = {
                "type": power.get("类型"),
                "name": power.get("属性", {}).get("名称"),
            }

        # 检查时代实体
        era = entities.get("era_awakening", {})
        if era:
            results["era_entities"] = {
                "type": era.get("类型"),
                "name": era.get("属性", {}).get("名称"),
            }

        # 检查角色实体
        char = entities.get("char_xueya", {})
        if char:
            results["character_entities"] = {
                "type": char.get("类型"),
                "name": char.get("名称"),
            }

        return results

    def check_bloodline(self) -> Dict[str, Any]:
        """
        检查血脉格式

        整合 check_bloodline.py 功能

        Returns:
            {
                "old_format_count": int,
                "new_format_count": int,
                "old_format_entities": List[str],
                "new_format_entities": List[str]
            }
        """
        data = self._load_knowledge_graph()
        if not data:
            return {"error": "无法加载知识图谱"}

        old_format = []
        new_format = []

        for entity_id in data.get("实体", {}).keys():
            if "血脉" in entity_id:
                old_format.append(entity_id)
            elif entity_id.startswith("bloodline_"):
                new_format.append(entity_id)

        return {
            "old_format_count": len(old_format),
            "new_format_count": len(new_format),
            "old_format_entities": old_format[:10],
            "new_format_entities": new_format[:10],
        }

    def check_all(self) -> Dict[str, Any]:
        """
        运行所有检查

        Returns:
            所有检查结果的汇总
        """
        print("=" * 60)
        print("检查管理器 - 运行所有检查")
        print("=" * 60)

        checks = {
            "sources": self.check_sources,
            "missing": self.check_missing,
            "relations": self.check_relations,
            "entity": self.check_entity,
            "bloodline": self.check_bloodline,
        }

        results = {}
        for check_id, check_func in checks.items():
            print(f"\n[检查] {check_id}...")
            result = check_func()
            results[check_id] = result

            if "error" in result:
                print(f"  ✗ 错误: {result['error']}")
            else:
                print(f"  ✓ 完成")
                # 打印简要信息
                for key, value in result.items():
                    if isinstance(value, (int, str)):
                        print(f"    - {key}: {value}")

        print("\n" + "=" * 60)
        print("检查完成")
        print("=" * 60)

        return results

    def get_report(self) -> str:
        """生成检查报告文本"""
        results = self.check_all()

        lines = [
            "=" * 60,
            "检查管理器报告",
            "=" * 60,
        ]

        for check_id, result in results.items():
            lines.append(f"\n## {check_id}")
            if "error" in result:
                lines.append(f"  错误: {result['error']}")
            else:
                for key, value in result.items():
                    if isinstance(value, dict):
                        lines.append(f"  {key}:")
                        for k, v in value.items():
                            lines.append(f"    - {k}: {v}")
                    elif isinstance(value, list):
                        lines.append(f"  {key}: {len(value)} 项")
                        for v in value[:5]:
                            lines.append(f"    - {v}")
                    else:
                        lines.append(f"  {key}: {value}")

        return "\n".join(lines)
