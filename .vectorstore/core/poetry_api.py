#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诗词意境API - 云溪专用统一接口
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
    get_eras,
    get_era,
    get_technique_mapping,
    query_by_era,
)

try:
    from technique_search import TechniqueSearcher
    from case_search import CaseSearcher

    TECHNIQUE_AVAILABLE = True
    CASE_AVAILABLE = True
except ImportError:
    TECHNIQUE_AVAILABLE = False
    CASE_AVAILABLE = False


class PoetryAPI:
    """诗词意境统一API"""

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

    def get_world_poetry_context(self) -> Dict[str, Any]:
        """获取当前世界观的意境上下文

        Returns:
            世界观意境配置
        """
        eras = get_eras()
        era_techniques = get_technique_mapping("意境")

        return {
            "world": get_current_world(),
            "eras": eras,
            "era_techniques": era_techniques.get("era_specific", {})
            if era_techniques
            else {},
        }

    def get_era_poetry_guide(self, era_name: str) -> Dict[str, Any]:
        """获取指定时代的意境创作指南

        Args:
            era_name: 时代名称

        Returns:
            时代意境指南
        """
        era_info = query_by_era(era_name)
        return {
            "era_name": era_name,
            "mood": era_info.get("era_config", {}).get("mood"),
            "color": era_info.get("era_config", {}).get("color"),
            "symbols": era_info.get("era_config", {}).get("symbols"),
            "techniques": era_info.get("era_techniques"),
        }

    # ============================================================
    # 技法库检索层
    # ============================================================

    def search_poetry_techniques(
        self, query: str, dimension: str = "意境", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """检索意境相关技法

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

    def search_poetry_by_keywords(
        self, keywords: List[str], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """按关键词检索意境技法

        Args:
            keywords: 关键词列表（如["诗意", "氛围", "意境"]）
            limit: 返回数量

        Returns:
            技法列表
        """
        query = " ".join(keywords)
        return self.search_poetry_techniques(query, dimension="意境", limit=limit)

    # ============================================================
    # 案例库检索层
    # ============================================================

    def search_poetry_cases(
        self, query: str, scene_type: str = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """检索意境相关案例

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

    def compose_poetry_scene(
        self,
        era: str = None,
        mood: str = None,
        keywords: List[str] = None,
        scene_type: str = "意境营造",
    ) -> Dict[str, Any]:
        """综合生成意境场景创作素材

        Args:
            era: 时代（可选）
            mood: 情绪/氛围（可选）
            keywords: 关键词列表（可选）
            scene_type: 场景类型

        Returns:
            综合创作素材
        """
        result = {
            "world_context": self.get_world_poetry_context(),
            "era_guide": None,
            "techniques": [],
            "cases": [],
        }

        # 时代适配
        if era:
            result["era_guide"] = self.get_era_poetry_guide(era)

        # 构建查询
        query_parts = []
        if mood:
            query_parts.append(mood)
        if keywords:
            query_parts.extend(keywords)

        query = " ".join(query_parts) if query_parts else "意境营造"

        # 技法检索
        result["techniques"] = self.search_poetry_techniques(
            query=query, dimension="意境", limit=10
        )

        # 案例检索
        result["cases"] = self.search_poetry_cases(
            query=query, scene_type=scene_type, limit=5
        )

        return result

    def get_poetry_expert_techniques(self) -> List[str]:
        """获取诗词专家级技法列表

        云溪在诗词方面已达到专家级，此方法返回核心技法
        """
        # 云溪专家级技法（从技法库预定义）
        expert_techniques = [
            "古典诗词引用技法",
            "诗意意象构建",
            "氛围渲染技法",
            "意境营造技法",
            "诗意语言运用",
            "诗词场景融合",
            "诗意结尾技法",
            "诗词隐喻技法",
        ]

        # 从技法库补充检索
        techniques = self.search_poetry_by_keywords(
            keywords=["诗意", "诗词", "意境", "氛围"], limit=10
        )

        # 合并
        all_techniques = expert_techniques.copy()
        for t in techniques:
            technique_name = t.get("name", t.get("title"))
            if technique_name and technique_name not in all_techniques:
                all_techniques.append(technique_name)

        return all_techniques


# 全局API实例
_poetry_api: Optional[PoetryAPI] = None


def get_poetry_api(world_name: str = None) -> PoetryAPI:
    """获取诗词API实例

    Args:
        world_name: 世界观名称（可选）

    Returns:
        PoetryAPI实例
    """
    global _poetry_api
    if _poetry_api is None:
        _poetry_api = PoetryAPI(world_name)
    return _poetry_api


if __name__ == "__main__":
    print("=" * 60)
    print("诗词意境API测试")
    print("=" * 60)

    api = get_poetry_api()

    # 测试世界观适配
    print("\n1. 世界观意境上下文:")
    context = api.get_world_poetry_context()
    print(f"   世界: {context['world']}")
    print(f"   时代数量: {len(context['eras'])}")

    # 测试时代意境
    print("\n2. 时代意境指南:")
    era_guide = api.get_era_poetry_guide("觉醒时代")
    print(f"   情绪: {era_guide['mood']}")
    print(f"   色调: {era_guide['color']}")

    # 测试技法检索
    print("\n3. 技法检索:")
    techniques = api.search_poetry_by_keywords(["诗意", "氛围"])
    print(f"   找到 {len(techniques)} 条技法")

    # 测试专家技法
    print("\n4. 专家级技法:")
    expert = api.get_poetry_expert_techniques()
    for t in expert[:5]:
        print(f"   - {t}")
