#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剧情编织API - 玄一专用统一接口
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
    get_core_principles,
    get_relationships,
    get_eras,
)

try:
    from technique_search import TechniqueSearcher
    from case_search import CaseSearcher

    TECHNIQUE_AVAILABLE = True
    CASE_AVAILABLE = True
except ImportError:
    TECHNIQUE_AVAILABLE = False
    CASE_AVAILABLE = False


class PlotAPI:
    """剧情编织统一API"""

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

    def get_world_plot_context(self) -> Dict[str, Any]:
        """获取当前世界观的剧情上下文

        Returns:
            世界观剧情配置
        """
        return {
            "world": get_current_world(),
            "core_principles": get_core_principles(),
            "relationships": get_relationships(),
            "eras": get_eras(),
        }

    def get_plot_principles(self) -> Dict[str, Any]:
        """获取剧情核心原则

        Returns:
            核心原则
        """
        principles = get_core_principles()
        return {
            "moral_view": principles.get("moral_view"),
            "core_theme": principles.get("core_theme"),
            "romance_rule": principles.get("romance_rule"),
        }

    def get_relationship_conflicts(self) -> List[Dict[str, Any]]:
        """获取关系冲突素材

        Returns:
            关系冲突列表
        """
        relationships = get_relationships()
        conflicts = []

        # 爱慕关系中的冲突
        for rel in relationships.get("love", []):
            conflicts.append(
                {
                    "type": "love",
                    "from": rel.get("from"),
                    "to": rel.get("to"),
                    "conflict": rel.get("conflict"),
                    "ending": rel.get("ending"),
                }
            )

        # 敌对关系
        for rel in relationships.get("enemy", []):
            conflicts.append(
                {
                    "type": "enemy",
                    "from": rel.get("from"),
                    "to": rel.get("to"),
                    "nature": rel.get("nature"),
                }
            )

        return conflicts

    # ============================================================
    # 技法库检索层
    # ============================================================

    def search_plot_techniques(
        self, query: str, dimension: str = "剧情", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """检索剧情相关技法

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

    def search_plot_by_keywords(
        self, keywords: List[str], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """按关键词检索剧情技法

        Args:
            keywords: 关键词列表（如["伏笔", "悬念", "反转"]）
            limit: 返回数量

        Returns:
            技法列表
        """
        query = " ".join(keywords)
        return self.search_plot_techniques(query, dimension="剧情", limit=limit)

    def search_foreshadowing_techniques(self, limit: int = 10) -> List[Dict[str, Any]]:
        """检索伏笔技法

        Args:
            limit: 返回数量

        Returns:
            伏笔技法列表
        """
        return self.search_plot_by_keywords(["伏笔", "伏笔设计", "铺垫"], limit=limit)

    def search_suspense_techniques(self, limit: int = 10) -> List[Dict[str, Any]]:
        """检索悬念技法

        Args:
            limit: 返回数量

        Returns:
            悬念技法列表
        """
        return self.search_plot_by_keywords(["悬念", "悬念布局", "疑问"], limit=limit)

    def search_reversal_techniques(self, limit: int = 10) -> List[Dict[str, Any]]:
        """检索反转技法

        Args:
            limit: 返回数量

        Returns:
            反转技法列表
        """
        return self.search_plot_by_keywords(["反转", "反转策划", "意外"], limit=limit)

    # ============================================================
    # 案例库检索层
    # ============================================================

    def search_plot_cases(
        self, query: str, scene_type: str = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """检索剧情相关案例

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

    def compose_plot_scene(
        self, plot_type: str = None, keywords: List[str] = None, scene_type: str = None
    ) -> Dict[str, Any]:
        """综合生成剧情场景创作素材

        Args:
            plot_type: 剧情类型（伏笔/悬念/反转）
            keywords: 关键词列表（可选）
            scene_type: 场景类型

        Returns:
            综合创作素材
        """
        result = {
            "world_context": self.get_world_plot_context(),
            "principles": self.get_plot_principles(),
            "conflicts": self.get_relationship_conflicts(),
            "techniques": [],
            "cases": [],
        }

        # 构建查询
        query_parts = []
        if plot_type:
            query_parts.append(plot_type)
        if keywords:
            query_parts.extend(keywords)

        query = " ".join(query_parts) if query_parts else "剧情编织"

        # 技法检索
        if plot_type == "伏笔":
            result["techniques"] = self.search_foreshadowing_techniques(limit=10)
        elif plot_type == "悬念":
            result["techniques"] = self.search_suspense_techniques(limit=10)
        elif plot_type == "反转":
            result["techniques"] = self.search_reversal_techniques(limit=10)
        else:
            result["techniques"] = self.search_plot_techniques(
                query=query, dimension="剧情", limit=10
            )

        # 案例检索
        result["cases"] = self.search_plot_cases(
            query=query, scene_type=scene_type, limit=5
        )

        return result

    def get_plot_expert_techniques(self) -> List[str]:
        """获取剧情专家级技法列表

        玄一专长于伏笔设计、悬念布局、反转策划
        """
        # 玄一核心技法
        expert_techniques = [
            "伏笔埋设技法",
            "伏笔推进技法",
            "伏笔回收技法",
            "悬念布局技法",
            "悬念节奏控制",
            "反转策划技法",
            "预期违背技法",
            "信息隐藏技法",
            "时间线编织",
            "因果链条设计",
        ]

        # 从技法库补充
        techniques = self.search_plot_by_keywords(
            keywords=["伏笔", "悬念", "反转"], limit=10
        )

        # 合并
        all_techniques = expert_techniques.copy()
        for t in techniques:
            technique_name = t.get("name", t.get("title"))
            if technique_name and technique_name not in all_techniques:
                all_techniques.append(technique_name)

        return all_techniques

    # ============================================================
    # 伏笔配对检索（新增）
    # ============================================================

    def search_foreshadow_pairs(
        self,
        relation_type: str = None,
        min_distance: int = 5,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        检索伏笔配对模式

        从 foreshadow_pair_v1 Collection 检索伏笔-回收配对，
        用于伏笔设计和回收时参考。

        Args:
            relation_type: 配对类型（悬念伏笔/情感伏笔/剧情伏笔）
            min_distance: 最小章节距离
            limit: 返回数量

        Returns:
            伏笔配对列表：
            [
                {
                    "relation_type": "悬念伏笔",
                    "pair_count": 156,
                    "avg_distance": 12.5,
                    "description": "悬念设置与回收模式"
                },
                ...
            ]

        Example:
            # 获取悬念伏笔配对
            pairs = api.search_foreshadow_pairs(relation_type="悬念伏笔")

            # 获取所有伏笔配对
            pairs = api.search_foreshadow_pairs()
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            client = QdrantClient(url="http://localhost:6333")

            # 构建 filter
            filter_conditions = []
            if relation_type:
                filter_conditions.append(
                    models.FieldCondition(
                        key="relation_type",
                        match=models.MatchValue(value=relation_type),
                    )
                )

            filter_obj = (
                models.Filter(must=filter_conditions) if filter_conditions else None
            )

            # scroll 获取数据
            results = client.scroll(
                collection_name="foreshadow_pair_v1",
                with_payload=True,
                with_vectors=False,
                limit=limit,
                query_filter=filter_obj,
            )[0]

            # 过滤距离过小的配对
            filtered = []
            for point in results:
                payload = point.payload
                avg_dist = payload.get("avg_distance", 0)
                if avg_dist >= min_distance:
                    filtered.append(payload)

            return filtered

        except Exception as e:
            print(f"[警告] 伏笔配对检索失败: {e}")
            return []


# 全局API实例
_plot_api: Optional[PlotAPI] = None


def get_plot_api(world_name: str = None) -> PlotAPI:
    """获取剧情API实例

    Args:
        world_name: 世界观名称（可选）

    Returns:
        PlotAPI实例
    """
    global _plot_api
    if _plot_api is None:
        _plot_api = PlotAPI(world_name)
    return _plot_api


if __name__ == "__main__":
    print("=" * 60)
    print("剧情编织API测试")
    print("=" * 60)

    api = get_plot_api()

    # 测试世界观适配
    print("\n1. 世界观剧情上下文:")
    context = api.get_world_plot_context()
    print(f"   世界: {context['world']}")
    print(f"   核心主题: {context['core_principles']['core_theme']}")

    # 测试关系冲突
    print("\n2. 关系冲突素材:")
    conflicts = api.get_relationship_conflicts()
    print(f"   冲突数量: {len(conflicts)}")
    for c in conflicts[:3]:
        print(f"   - {c['from']} vs {c['to']}: {c.get('conflict', c.get('nature'))}")

    # 测试伏笔技法
    print("\n3. 伏笔技法检索:")
    techniques = api.search_foreshadowing_techniques()
    print(f"   找到 {len(techniques)} 条技法")

    # 测试专家技法
    print("\n4. 专家级技法:")
    expert = api.get_plot_expert_techniques()
    for t in expert[:5]:
        print(f"   - {t}")
