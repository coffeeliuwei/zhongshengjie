#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
世界观API - 苍澜专用统一接口
=============================

整合技法库检索 + 世界观适配 + 案例检索
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加core目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from world_config_loader import (
    get_current_world,
    get_world_info,
    get_power_systems,
    get_power_system,
    get_factions,
    get_faction,
    get_eras,
    get_era,
    get_core_principles,
    query_by_power,
    query_by_faction,
    list_available_worlds,
    set_current_world,
    validate_world_config,
)

try:
    from technique_search import TechniqueSearcher
    from case_search import CaseSearcher

    TECHNIQUE_AVAILABLE = True
    CASE_AVAILABLE = True
except ImportError:
    TECHNIQUE_AVAILABLE = False
    CASE_AVAILABLE = False


class WorldviewAPI:
    """世界观架构统一API"""

    def __init__(self, world_name: str = None):
        """初始化

        Args:
            world_name: 世界观名称（默认当前）
        """
        if world_name:
            set_current_world(world_name)

        self._technique_searcher = None
        self._case_searcher = None

    def _get_technique_searcher(self):
        """获取技法检索器"""
        if self._technique_searcher is None and TECHNIQUE_AVAILABLE:
            self._technique_searcher = TechniqueSearcher()
        return self._technique_searcher

    def _get_case_searcher(self):
        """获取案例检索器"""
        if self._case_searcher is None and CASE_AVAILABLE:
            self._case_searcher = CaseSearcher()
        return self._case_searcher

    # ============================================================
    # 世界观管理
    # ============================================================

    def list_worlds(self) -> List[str]:
        """列出所有可用世界观"""
        return list_available_worlds()

    def switch_world(self, world_name: str) -> bool:
        """切换世界观

        Args:
            world_name: 世界观名称

        Returns:
            是否成功
        """
        return set_current_world(world_name)

    def get_world_summary(self) -> Dict[str, Any]:
        """获取当前世界观摘要"""
        return get_world_info()

    def validate_world(self) -> List[str]:
        """验证当前世界观配置"""
        return validate_world_config(get_current_world())

    # ============================================================
    # 世界观核心查询
    # ============================================================

    def get_power_systems_overview(self) -> Dict[str, Any]:
        """获取力量体系总览

        Returns:
            力量体系摘要
        """
        power_systems = get_power_systems()
        summary = {}

        for name, config in power_systems.items():
            summary[name] = {
                "source": config.get("source"),
                "combat_style": config.get("combat_style"),
                "costs": config.get("costs"),
                "subtypes_count": len(config.get("subtypes", {})),
            }

        return {"total": len(summary), "systems": summary}

    def get_factions_overview(self) -> Dict[str, Any]:
        """获取势力总览

        Returns:
            势力摘要
        """
        factions = get_factions()
        summary = {}

        for name, config in factions.items():
            summary[name] = {
                "structure": config.get("structure"),
                "architecture": config.get("architecture"),
                "culture": config.get("culture"),
            }

        return {"total": len(summary), "factions": summary}

    def get_eras_overview(self) -> Dict[str, Any]:
        """获取时代总览

        Returns:
            时代摘要
        """
        eras = get_eras()
        summary = {}

        for name, config in eras.items():
            summary[name] = {
                "mood": config.get("mood"),
                "color": config.get("color"),
                "symbols": config.get("symbols"),
            }

        return {"total": len(summary), "eras": summary}

    def get_world_principles(self) -> Dict[str, Any]:
        """获取世界观核心原则

        Returns:
            核心原则
        """
        return get_core_principles()

    # ============================================================
    # 详细查询
    # ============================================================

    def get_power_detail(self, power_name: str) -> Dict[str, Any]:
        """获取力量体系完整详情

        Args:
            power_name: 力量体系

        Returns:
            完整详情
        """
        return query_by_power(power_name)

    def get_faction_detail(self, faction_name: str) -> Dict[str, Any]:
        """获取势力完整详情

        Args:
            faction_name: 势力名称

        Returns:
            完整详情
        """
        return query_by_faction(faction_name)

    def get_era_detail(self, era_name: str) -> Dict[str, Any]:
        """获取时代完整详情

        Args:
            era_name: 时代名称

        Returns:
            完整详情
        """
        from world_config_loader import query_by_era

        return query_by_era(era_name)

    # ============================================================
    # 技法库检索层
    # ============================================================

    def search_worldview_techniques(
        self, query: str, dimension: str = "世界观", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """检索世界观相关技法

        Args:
            query: 查询文本
            dimension: 技法维度
            limit: 返回数量

        Returns:
            技法列表
        """
        searcher = self._get_technique_searcher()
        if searcher is None:
            return []

        results = searcher.search(query=query, dimension=dimension, limit=limit)
        return results

    def search_by_keywords(
        self, keywords: List[str], dimension: str = "世界观", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """按关键词检索技法

        Args:
            keywords: 关键词列表
            dimension: 技法维度
            limit: 返回数量

        Returns:
            技法列表
        """
        query = " ".join(keywords)
        return self.search_worldview_techniques(query, dimension=dimension, limit=limit)

    # ============================================================
    # 案例库检索层
    # ============================================================

    def search_worldview_cases(
        self, query: str, scene_type: str = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """检索世界观相关案例

        Args:
            query: 查询文本
            scene_type: 场景类型
            limit: 返回数量

        Returns:
            案例列表
        """
        searcher = self._get_case_searcher()
        if searcher is None:
            return []

        results = searcher.search(query=query, scene_type=scene_type, limit=limit)
        return results

    # ============================================================
    # 综合创作API
    # ============================================================

    def compose_worldview_scene(
        self, scope: str = None, keywords: List[str] = None, scene_type: str = None
    ) -> Dict[str, Any]:
        """综合生成世界观场景创作素材

        Args:
            scope: 范围（势力/力量/时代）
            keywords: 关键词列表
            scene_type: 场景类型

        Returns:
            综合创作素材
        """
        result = {
            "world_summary": self.get_world_summary(),
            "power_overview": self.get_power_systems_overview(),
            "faction_overview": self.get_factions_overview(),
            "era_overview": self.get_eras_overview(),
            "principles": self.get_world_principles(),
            "techniques": [],
            "cases": [],
        }

        # 构建查询
        query_parts = []
        if scope:
            query_parts.append(scope)
        if keywords:
            query_parts.extend(keywords)

        query = " ".join(query_parts) if query_parts else "世界观架构"

        # 技法检索
        result["techniques"] = self.search_worldview_techniques(
            query=query, dimension="世界观", limit=10
        )

        # 案例检索
        result["cases"] = self.search_worldview_cases(
            query=query, scene_type=scene_type, limit=5
        )

        return result

    def get_worldview_expert_techniques(self) -> List[str]:
        """获取世界观专家级技法列表

        苍澜专长于宏大设定、权力体系、世界规则构建
        """
        # 苍澜核心技法
        expert_techniques = [
            "世界观构建技法",
            "力量体系设计",
            "势力结构设计",
            "权力体系构建",
            "世界规则设计",
            "时代划分技法",
            "代价系统设计",
            "关系网络设计",
            "核心原则设定",
            "AI入侵机制",
        ]

        # 从技法库补充
        techniques = self.search_by_keywords(
            keywords=["世界观", "力量体系", "势力", "规则"],
            dimension="世界观",
            limit=10,
        )

        # 合并
        all_techniques = expert_techniques.copy()
        for t in techniques:
            technique_name = t.get("name", t.get("title"))
            if technique_name and technique_name not in all_techniques:
                all_techniques.append(technique_name)

        return all_techniques


# 全局API实例
_worldview_api: Optional[WorldviewAPI] = None


def get_worldview_api(world_name: str = None) -> WorldviewAPI:
    """获取世界观API实例

    Args:
        world_name: 世界观名称（可选）

    Returns:
        WorldviewAPI实例
    """
    global _worldview_api
    if _worldview_api is None:
        _worldview_api = WorldviewAPI(world_name)
    return _worldview_api


if __name__ == "__main__":
    print("=" * 60)
    print("世界观API测试")
    print("=" * 60)

    api = get_worldview_api()

    # 测试世界观列表
    print("\n1. 可用世界观:")
    worlds = api.list_worlds()
    print(f"   {worlds}")

    # 测试世界观摘要
    print("\n2. 当前世界观摘要:")
    summary = api.get_world_summary()
    print(f"   名称: {summary['name']}")
    print(f"   类型: {summary['type']}")

    # 测试力量体系
    print("\n3. 力量体系总览:")
    powers = api.get_power_systems_overview()
    print(f"   总数: {powers['total']}")
    for name, info in list(powers["systems"].items())[:3]:
        print(f"   - {name}: {info['source']}")

    # 测试势力
    print("\n4. 势力总览:")
    factions = api.get_factions_overview()
    print(f"   总数: {factions['total']}")
    for name, info in list(factions["factions"].items())[:3]:
        print(f"   - {name}: {info['structure']}")

    # 测试核心原则
    print("\n5. 核心原则:")
    principles = api.get_world_principles()
    print(f"   道德观: {principles['moral_view']}")
    print(f"   核心主题: {principles['core_theme']}")

    # ============================================================
    # 世界观元素命名规律检索（新增）
    # ============================================================

    def search_naming_patterns(
        self,
        element_type: str = None,
        query: str = None,
        min_frequency: int = 3,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        检索世界观元素命名规律

        从 worldview_element_v1 Collection 检索命名模式，
        用于创作新地名/组织名时参考。

        Args:
            element_type: 元素类型（地点/组织/势力）
            query: 查询文本（如"城"、"宗"、"门"）
            min_frequency: 最小出现频次
            limit: 返回数量

        Returns:
            命名规律列表：
            [
                {
                    "element_name": "玄武城",
                    "element_type": "地点",
                    "total_frequency": 156,
                    "novel_count": 12,
                    "naming_pattern": "形容词+城",
                    "is_cross_novel": True
                },
                ...
            ]

        Example:
            # 获取城类命名规律
            patterns = api.search_naming_patterns(element_type="地点", query="城")

            # 获取宗门类命名规律
            patterns = api.search_naming_patterns(element_type="组织", query="宗")
        """
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url="http://localhost:6333")

            # 构建 filter
            filter_conditions = []
            if element_type:
                filter_conditions.append(
                    models.Filter(
                        must=[
                            models.FieldCondition(
                                key="element_type",
                                match=models.MatchValue(value=element_type),
                            )
                        ]
                    )
                )

            filter_obj = (
                models.Filter(must=filter_conditions) if filter_conditions else None
            )

            # scroll 获取数据
            results = client.scroll(
                collection_name="worldview_element_v1",
                with_payload=True,
                with_vectors=False,
                limit=limit * 5,  # 扩大召回范围
                query_filter=filter_obj,
            )[0]

            # 过滤低频元素
            filtered = []
            for point in results:
                payload = point.payload
                freq = payload.get("total_frequency", 0)
                if freq >= min_frequency:
                    # 如果有query，检查是否匹配
                    if query:
                        element_name = payload.get("element_name", "")
                        if query in element_name:
                            filtered.append(payload)
                    else:
                        filtered.append(payload)

            # 按频次排序
            filtered.sort(key=lambda x: x.get("total_frequency", 0), reverse=True)

            return filtered[:limit]

        except Exception as e:
            print(f"[警告] 世界观元素检索失败: {e}")
            return []

    def get_element_statistics(self) -> Dict[str, Any]:
        """
        获取世界观元素统计信息

        Returns:
            {
                "total_elements": 209223,
                "by_type": {"地点": 85600, "组织": 72400, "势力": 51223},
                "cross_novel_count": 156,
                "top_elements": [...]
            }
        """
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url="http://localhost:6333")

            # 获取 Collection 信息
            info = client.get_collection("worldview_element_v1")

            stats = {
                "total_elements": info.points_count,
                "collection_status": info.status.value,
            }

            return stats

        except Exception as e:
            print(f"[警告] 统计信息获取失败: {e}")
            return {"total_elements": 0}
