#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
战斗设计API - 剑尘专用统一接口
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
    get_power_systems,
    get_power_system,
    query_by_power,
    get_technique_mapping,
)

try:
    from technique_search import TechniqueSearcher
    from case_search import CaseSearcher

    TECHNIQUE_AVAILABLE = True
    CASE_AVAILABLE = True
except ImportError:
    TECHNIQUE_AVAILABLE = False
    CASE_AVAILABLE = False


class BattleAPI:
    """战斗设计统一API"""

    def __init__(self, world_name: str = None):
        """初始化

        Args:
            world_name: 世界观名称（默认当前）
        """
        if world_name:
            from world_config_loader import set_current_world

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
    # 世界观适配层
    # ============================================================

    def get_world_battle_context(self) -> Dict[str, Any]:
        """获取当前世界观的战斗上下文

        Returns:
            世界观战斗配置
        """
        power_systems = get_power_systems()
        battle_techniques = get_technique_mapping("战斗")

        return {
            "world": get_current_world(),
            "power_systems": list(power_systems.keys()),
            "battle_techniques": battle_techniques.get("power_specific", {})
            if battle_techniques
            else {},
        }

    def get_power_battle_guide(self, power_name: str) -> Dict[str, Any]:
        """获取指定力量体系的战斗创作指南

        Args:
            power_name: 力量体系名称

        Returns:
            力量体系战斗指南
        """
        power_info = query_by_power(power_name)
        power_config = power_info.get("power_config", {})

        return {
            "power_name": power_name,
            "source": power_config.get("source"),
            "cultivation": power_config.get("cultivation"),
            "combat_style": power_config.get("combat_style"),
            "costs": power_config.get("costs"),
            "subtypes": power_config.get("subtypes"),
            "techniques": power_info.get("techniques"),
            "related_characters": power_info.get("related_characters"),
        }

    def get_battle_cost_rules(self, power_name: str) -> Dict[str, Any]:
        """获取力量体系的代价规则

        Args:
            power_name: 力量体系

        Returns:
            代价规则
        """
        power_config = get_power_system(power_name)
        if not power_config:
            return {}

        return {
            "general_costs": power_config.get("costs", []),
            "subtype_costs": {
                subtype: config.get("cost")
                for subtype, config in power_config.get("subtypes", {}).items()
                if "cost" in config
            },
        }

    # ============================================================
    # 技法库检索层
    # ============================================================

    def search_battle_techniques(
        self, query: str, dimension: str = "战斗", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """检索战斗相关技法

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

    def search_battle_by_power(
        self, power_name: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """按力量体系检索战斗技法

        Args:
            power_name: 力量体系名称
            limit: 返回数量

        Returns:
            技法列表
        """
        # 从世界观获取力量关键词
        power_config = get_power_system(power_name)
        if not power_config:
            return []

        keywords = [power_name, power_config.get("combat_style", "")]
        query = " ".join(keywords)

        return self.search_battle_techniques(query, dimension="战斗", limit=limit)

    def search_battle_by_keywords(
        self, keywords: List[str], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """按关键词检索战斗技法

        Args:
            keywords: 关键词列表
            limit: 返回数量

        Returns:
            技法列表
        """
        query = " ".join(keywords)
        return self.search_battle_techniques(query, dimension="战斗", limit=limit)

    # ============================================================
    # 案例库检索层
    # ============================================================

    def search_battle_cases(
        self, query: str, scene_type: str = "战斗", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """检索战斗相关案例

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

    def compose_battle_scene(
        self,
        power_name: str = None,
        combat_type: str = None,
        keywords: List[str] = None,
        scene_type: str = "战斗",
    ) -> Dict[str, Any]:
        """综合生成战斗场景创作素材

        Args:
            power_name: 力量体系（可选）
            combat_type: 战斗类型（可选）
            keywords: 关键词列表（可选）
            scene_type: 场景类型

        Returns:
            综合创作素材
        """
        result = {
            "world_context": self.get_world_battle_context(),
            "power_guide": None,
            "cost_rules": None,
            "techniques": [],
            "cases": [],
        }

        # 力量适配
        if power_name:
            result["power_guide"] = self.get_power_battle_guide(power_name)
            result["cost_rules"] = self.get_battle_cost_rules(power_name)

        # 构建查询
        query_parts = []
        if power_name:
            query_parts.append(power_name)
        if combat_type:
            query_parts.append(combat_type)
        if keywords:
            query_parts.extend(keywords)

        query = " ".join(query_parts) if query_parts else "战斗设计"

        # 技法检索
        result["techniques"] = self.search_battle_techniques(
            query=query, dimension="战斗", limit=10
        )

        # 案例检索
        result["cases"] = self.search_battle_cases(
            query=query, scene_type=scene_type, limit=5
        )

        return result

    def get_battle_expert_techniques(self, power_name: str = None) -> List[str]:
        """获取战斗专家级技法列表

        Args:
            power_name: 力量体系（可选）

        Returns:
            专家级技法列表
        """
        # 剑尘核心技法（战斗设计专家）
        expert_techniques = [
            "战斗节奏控制",
            "力量代价设计",
            "战斗场景描写",
            "功法体系运用",
            "冲突张力构建",
            "战斗高潮设计",
            "弱者战胜强者技法",
            "群体战斗设计",
        ]

        # 从技法库补充检索
        if power_name:
            techniques = self.search_battle_by_power(power_name, limit=10)
        else:
            techniques = self.search_battle_by_keywords(
                keywords=["战斗", "战斗设计", "功法"], limit=10
            )

        # 合并
        all_techniques = expert_techniques.copy()
        for t in techniques:
            technique_name = t.get("name", t.get("title"))
            if technique_name and technique_name not in all_techniques:
                all_techniques.append(technique_name)

        return all_techniques

    # ============================================================
    # 力量代价检索（新增）
    # ============================================================

    def search_power_cost_patterns(
        self,
        power_type: str = None,
        cost_category: str = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        检索力量代价模式

        从 power_cost_v1 Collection 检索代价描写模板，
        用于战斗场景中代价描写参考。

        Args:
            power_type: 力量类型（修仙/魔法/科技等）
            cost_category: 代价类别（体力/精神/寿命/资源等）
            limit: 返回数量

        Returns:
            代价模式列表：
            [
                {
                    "power_type": "修仙",
                    "cost_categories": ["体力", "精神", "寿命"],
                    "total_expressions": 156,
                    "examples": [...]
                },
                ...
            ]

        Example:
            # 获取修仙代价模式
            patterns = api.search_power_cost_patterns(power_type="修仙")

            # 获取体力代价模式
            patterns = api.search_power_cost_patterns(cost_category="体力")
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            client = QdrantClient(url="http://localhost:6333")

            # 构建 filter
            filter_conditions = []
            if power_type:
                filter_conditions.append(
                    models.FieldCondition(
                        key="power_type",
                        match=models.MatchValue(value=power_type),
                    )
                )

            filter_obj = (
                models.Filter(must=filter_conditions) if filter_conditions else None
            )

            # scroll 获取数据
            results = client.scroll(
                collection_name="power_cost_v1",
                with_payload=True,
                with_vectors=False,
                limit=limit,
                query_filter=filter_obj,
            )[0]

            return [point.payload for point in results]

        except Exception as e:
            print(f"[警告] 力量代价检索失败: {e}")
            return []


# 全局API实例
_battle_api: Optional[BattleAPI] = None


def get_battle_api(world_name: str = None) -> BattleAPI:
    """获取战斗API实例

    Args:
        world_name: 世界观名称（可选）

    Returns:
        BattleAPI实例
    """
    global _battle_api
    if _battle_api is None:
        _battle_api = BattleAPI(world_name)
    return _battle_api


if __name__ == "__main__":
    print("=" * 60)
    print("战斗设计API测试")
    print("=" * 60)

    api = get_battle_api()

    # 测试世界观适配
    print("\n1. 世界观战斗上下文:")
    context = api.get_world_battle_context()
    print(f"   世界: {context['world']}")
    print(f"   力量体系: {context['power_systems'][:3]}...")

    # 测试力量体系战斗
    print("\n2. 修仙战斗指南:")
    guide = api.get_power_battle_guide("修仙")
    print(f"   力量来源: {guide['source']}")
    print(f"   代价: {guide['costs']}")

    # 测试代价规则
    print("\n3. 代价规则:")
    costs = api.get_battle_cost_rules("修仙")
    print(f"   一般代价: {costs['general_costs']}")

    # 测试技法检索
    print("\n4. 战斗技法检索:")
    techniques = api.search_battle_by_keywords(["战斗", "剑诀"])
    print(f"   找到 {len(techniques)} 条技法")
