#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作者风格API - 风格模仿统一接口
==============================

整合技法库检索 + 作者风格特征检索
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加core目录到路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from technique_search import TechniqueSearcher
    from case_search import CaseSearcher

    TECHNIQUE_AVAILABLE = True
    CASE_AVAILABLE = True
except ImportError:
    TECHNIQUE_AVAILABLE = False
    CASE_AVAILABLE = False


class AuthorStyleAPI:
    """作者风格统一API"""

    def __init__(self, world_name: str = None):
        """初始化

        Args:
            world_name: 世界观名称（默认当前）
        """
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
    # 作者风格检索层
    # ============================================================

    def search_author_styles(
        self,
        style_pattern: str = None,
        author_name: str = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        检索作者风格特征

        从 author_style_v1 Collection 检索作者风格指纹，
        用于模仿特定作者风格时参考。

        Args:
            style_pattern: 风格模式（简洁/华丽/幽默等）
            author_name: 作者名称
            limit: 返回数量

        Returns:
            风格特征列表：
            [
                {
                    "style_pattern": "简洁有力",
                    "avg_sentence_length": 15.6,
                    "rhetoric_usage": {"比喻": 12, "排比": 8},
                    "novel_count": 5,
                    "description": "句子短促有力，节奏感强"
                },
                ...
            ]

        Example:
            # 获取简洁风格特征
            styles = api.search_author_styles(style_pattern="简洁")

            # 获取特定作者风格
            styles = api.search_author_styles(author_name="猫腻")
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            client = QdrantClient(url="http://localhost:6333")

            # 构建 filter
            filter_conditions = []
            if style_pattern:
                filter_conditions.append(
                    models.FieldCondition(
                        key="style_pattern",
                        match=models.MatchValue(value=style_pattern),
                    )
                )

            filter_obj = (
                models.Filter(must=filter_conditions) if filter_conditions else None
            )

            # scroll 获取数据
            results = client.scroll(
                collection_name="author_style_v1",
                with_payload=True,
                with_vectors=False,
                limit=limit,
                query_filter=filter_obj,
            )[0]

            return [point.payload for point in results]

        except Exception as e:
            print(f"[警告] 作者风格检索失败: {e}")
            return []

    def get_style_statistics(self) -> Dict[str, Any]:
        """
        获取作者风格统计信息

        Returns:
            {
                "total_styles": 2803,
                "collection_status": "green"
            }
        """
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url="http://localhost:6333")

            info = client.get_collection("author_style_v1")

            return {
                "total_styles": info.points_count,
                "collection_status": info.status.value,
            }

        except Exception as e:
            print(f"[警告] 统计信息获取失败: {e}")
            return {"total_styles": 0}

    # ============================================================
    # 综合创作 API
    # ============================================================

    def compose_style_guide(
        self,
        target_style: str = "简洁",
        reference_authors: List[str] = None,
    ) -> Dict[str, Any]:
        """
        综合生成风格创作指南

        Args:
            target_style: 目标风格
            reference_authors: 参考作者列表

        Returns:
            {
                "target_style": "简洁",
                "style_features": {...},
                "techniques": [...],
                "cases": [...]
            }
        """
        result = {
            "target_style": target_style,
            "style_features": [],
            "techniques": [],
            "cases": [],
        }

        # 检索风格特征
        result["style_features"] = self.search_author_styles(
            style_pattern=target_style, limit=5
        )

        # 检索技法
        searcher = self._get_technique_searcher()
        if searcher:
            result["techniques"] = searcher.search(
                query=f"{target_style} 风格 写作", dimension="叙事维度", limit=5
            )

        # 检索案例
        case_searcher = self._get_case_searcher()
        if case_searcher:
            result["cases"] = case_searcher.search(
                query=f"{target_style} 文风", scene_type="开篇", limit=3
            )

        return result


# 全局API实例
_author_api: Optional[AuthorStyleAPI] = None


def get_author_api() -> AuthorStyleAPI:
    """获取作者风格API实例

    Returns:
        AuthorStyleAPI实例
    """
    global _author_api
    if _author_api is None:
        _author_api = AuthorStyleAPI()
    return _author_api


if __name__ == "__main__":
    print("=" * 60)
    print("作者风格API测试")
    print("=" * 60)

    api = get_author_api()

    # 测试风格检索
    print("\n1. 简洁风格特征:")
    styles = api.search_author_styles(style_pattern="简洁")
    for s in styles[:3]:
        print(f"   - {s.get('style_pattern')}: {s.get('description')}")

    # 测试统计
    print("\n2. 统计信息:")
    stats = api.get_style_statistics()
    print(f"   总数: {stats['total_styles']}")

    # 测试综合创作
    print("\n3. 风格创作指南:")
    guide = api.compose_style_guide(target_style="华丽")
    print(f"   风格特征数: {len(guide['style_features'])}")
    print(f"   技法数: {len(guide['techniques'])}")
