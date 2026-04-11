#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人物刻画API - 墨言专用统一接口
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
    get_characters,
    get_character,
    get_factions,
    query_by_faction,
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


class CharacterAPI:
    """人物刻画统一API"""

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

    def get_world_character_context(self) -> Dict[str, Any]:
        """获取当前世界观的人物上下文

        Returns:
            世界观人物配置
        """
        return {
            "world": get_current_world(),
            "characters": get_characters(),
            "factions": get_factions(),
            "character_techniques": get_technique_mapping("人物"),
        }

    def get_character_profile(self, character_name: str) -> Dict[str, Any]:
        """获取角色完整档案

        Args:
            character_name: 角色名称

        Returns:
            角色档案
        """
        char_config = get_character(character_name)
        if not char_config:
            return {}

        return {
            "name": character_name,
            "faction": char_config.get("faction"),
            "power": char_config.get("power"),
            "subtype": char_config.get("subtype"),
            "abilities": char_config.get("abilities"),
            "invasion_status": char_config.get("invasion_status"),
        }

    def get_faction_character_guide(self, faction_name: str) -> Dict[str, Any]:
        """获取势力人物刻画指南

        Args:
            faction_name: 势力名称

        Returns:
            势力人物刻画指南
        """
        faction_info = query_by_faction(faction_name)
        faction_config = faction_info.get("faction_config", {})

        return {
            "faction_name": faction_name,
            "structure": faction_config.get("structure"),
            "culture": faction_config.get("culture"),
            "architecture": faction_config.get("architecture"),
            "style_features": faction_config.get("style_features"),
            "characters": faction_info.get("related_characters"),
            "techniques": faction_info.get("techniques"),
        }

    def get_character_behavior_patterns(self, faction_name: str) -> List[str]:
        """获取势力角色行为模式

        Args:
            faction_name: 势力名称

        Returns:
            行为模式列表
        """
        techniques = get_technique_mapping("人物")
        if not techniques:
            return []

        faction_specific = techniques.get("faction_specific", {})
        return faction_specific.get(faction_name, [])

    # ============================================================
    # 技法库检索层
    # ============================================================

    def search_character_techniques(
        self, query: str, dimension: str = "人物", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """检索人物刻画技法

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

    def search_character_by_keywords(
        self, keywords: List[str], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """按关键词检索人物技法

        Args:
            keywords: 关键词列表（如["心理", "情感", "成长"]）
            limit: 返回数量

        Returns:
            技法列表
        """
        query = " ".join(keywords)
        return self.search_character_techniques(query, dimension="人物", limit=limit)

    def search_emotion_techniques(self, limit: int = 10) -> List[Dict[str, Any]]:
        """检索情感描写技法

        Args:
            limit: 返回数量

        Returns:
            情感技法列表
        """
        return self.search_character_by_keywords(["情感", "情绪", "心理"], limit=limit)

    def search_growth_techniques(self, limit: int = 10) -> List[Dict[str, Any]]:
        """检索成长描写技法

        Args:
            limit: 返回数量

        Returns:
            成长技法列表
        """
        return self.search_character_by_keywords(["成长", "变化", "蜕变"], limit=limit)

    # ============================================================
    # 案例库检索层
    # ============================================================

    def search_character_cases(
        self, query: str, scene_type: str = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """检索人物刻画案例

        Args:
            query: 查询文本
            scene_type: 场景类型（可选）
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

    def compose_character_scene(
        self,
        character_name: str = None,
        faction_name: str = None,
        emotion_type: str = None,
        keywords: List[str] = None,
        scene_type: str = None,
    ) -> Dict[str, Any]:
        """综合生成人物场景创作素材

        Args:
            character_name: 角色名称（可选）
            faction_name: 势力名称（可选）
            emotion_type: 情绪类型（可选）
            keywords: 关键词列表（可选）
            scene_type: 场景类型

        Returns:
            综合创作素材
        """
        result = {
            "world_context": self.get_world_character_context(),
            "character_profile": None,
            "faction_guide": None,
            "behavior_patterns": None,
            "techniques": [],
            "cases": [],
        }

        # 角色适配
        if character_name:
            result["character_profile"] = self.get_character_profile(character_name)
            char = get_character(character_name)
            if char:
                faction_name = char.get("faction")

        # 势力适配
        if faction_name:
            result["faction_guide"] = self.get_faction_character_guide(faction_name)
            result["behavior_patterns"] = self.get_character_behavior_patterns(
                faction_name
            )

        # 构建查询
        query_parts = []
        if character_name:
            query_parts.append(character_name)
        if emotion_type:
            query_parts.append(emotion_type)
        if keywords:
            query_parts.extend(keywords)

        query = " ".join(query_parts) if query_parts else "人物刻画"

        # 技法检索
        if emotion_type:
            result["techniques"] = self.search_emotion_techniques(limit=10)
        else:
            result["techniques"] = self.search_character_techniques(
                query=query, dimension="人物", limit=10
            )

        # 案例检索
        result["cases"] = self.search_character_cases(
            query=query, scene_type=scene_type, limit=5
        )

        return result

    def get_character_expert_techniques(self) -> List[str]:
        """获取人物刻画专家级技法列表

        墨言专长于情感细腻、心理描写、人物成长
        """
        # 墨言核心技法
        expert_techniques = [
            "情感细腻描写",
            "心理状态刻画",
            "人物成长弧光",
            "情绪触发设计",
            "内心独白技法",
            "情感转折设计",
            "性格矛盾刻画",
            "人物动机揭示",
            "行为预判模板",
            "角色过往塑造",
        ]

        # 从技法库补充
        techniques = self.search_character_by_keywords(
            keywords=["情感", "心理", "人物", "成长"], limit=10
        )

        # 合并
        all_techniques = expert_techniques.copy()
        for t in techniques:
            technique_name = t.get("name", t.get("title"))
            if technique_name and technique_name not in all_techniques:
                all_techniques.append(technique_name)

        return all_techniques

    # ============================================================
    # 人物关系图谱检索（新增）
    # ============================================================

    def search_relation_patterns(
        self,
        relation_type: str = None,
        character_name: str = None,
        min_cooccurrence: int = 3,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        检索人物关系模式

        从 character_relation_v1 Collection 检索人物共现关系，
        用于创作人物关系描写时参考。

        Args:
            relation_type: 关系类型（师徒/同门/敌对/爱慕等）
            character_name: 角色名称（用于查找该角色的关系）
            min_cooccurrence: 最小共现次数
            limit: 返回数量

        Returns:
            关系模式列表：
            [
                {
                    "character1": "林雷",
                    "character2": "迪莉娅",
                    "cooccurrence_count": 156,
                    "relation_type": "爱慕",
                    "novel_count": 12
                },
                ...
            ]

        Example:
            # 获取师徒关系模式
            patterns = api.search_relation_patterns(min_cooccurrence=10)

            # 获取特定角色的关系
            patterns = api.search_relation_patterns(character_name="林雷")
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            client = QdrantClient(url="http://localhost:6333")

            # 构建 filter
            filter_conditions = []
            if character_name:
                # 搜索包含该角色的关系
                filter_conditions.append(
                    models.Filter(
                        should=[
                            models.FieldCondition(
                                key="character1",
                                match=models.MatchValue(value=character_name),
                            ),
                            models.FieldCondition(
                                key="character2",
                                match=models.MatchValue(value=character_name),
                            ),
                        ]
                    )
                )

            filter_obj = (
                models.Filter(must=filter_conditions) if filter_conditions else None
            )

            # scroll 获取数据
            results = client.scroll(
                collection_name="character_relation_v1",
                with_payload=True,
                with_vectors=False,
                limit=limit * 5,
                query_filter=filter_obj,
            )[0]

            # 过滤低频关系
            filtered = []
            for point in results:
                payload = point.payload
                count = payload.get("cooccurrence_count", 0)
                if count >= min_cooccurrence:
                    filtered.append(payload)

            # 按共现次数排序
            filtered.sort(key=lambda x: x.get("cooccurrence_count", 0), reverse=True)

            return filtered[:limit]

        except Exception as e:
            print(f"[警告] 人物关系检索失败: {e}")
            return []

    def get_relation_statistics(self) -> Dict[str, Any]:
        """
        获取人物关系统计信息

        Returns:
            {
                "total_relations": 198500,
                "top_pairs": [...],
                "collection_status": "green"
            }
        """
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url="http://localhost:6333")

            info = client.get_collection("character_relation_v1")

            return {
                "total_relations": info.points_count,
                "collection_status": info.status.value,
            }

        except Exception as e:
            print(f"[警告] 统计信息获取失败: {e}")
            return {"total_relations": 0}


# 全局API实例
_character_api: Optional[CharacterAPI] = None


def get_character_api(world_name: str = None) -> CharacterAPI:
    """获取人物API实例

    Args:
        world_name: 世界观名称（可选）

    Returns:
        CharacterAPI实例
    """
    global _character_api
    if _character_api is None:
        _character_api = CharacterAPI(world_name)
    return _character_api


if __name__ == "__main__":
    print("=" * 60)
    print("人物刻画API测试")
    print("=" * 60)

    api = get_character_api()

    # 测试世界观适配
    print("\n1. 世界观人物上下文:")
    context = api.get_world_character_context()
    print(f"   世界: {context['world']}")
    print(f"   角色数量: {len(context['characters'])}")

    # 测试角色档案
    print("\n2. 角色档案:")
    profile = api.get_character_profile("血牙")
    print(f"   势力: {profile['faction']}")
    print(f"   力量: {profile['power']}")
    print(f"   能力: {profile['abilities']}")

    # 测试势力指南
    print("\n3. 势力人物刻画:")
    guide = api.get_faction_character_guide("兽族文明")
    print(f"   文化: {guide['culture']}")
    print(f"   行为模式: {guide.get('techniques')}")

    # 测试情感技法
    print("\n4. 情感技法检索:")
    techniques = api.search_emotion_techniques()
    print(f"   找到 {len(techniques)} 条技法")
