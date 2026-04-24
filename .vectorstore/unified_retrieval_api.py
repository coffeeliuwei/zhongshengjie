#!/usr/bin/env python
"""
统一检索API - 单一入口，多源检索，自动融合

为创作系统提供统一检索接口，支持：
- 技法检索 (writing_techniques_v2)
- 案例检索 (case_library_v2)
- 设定检索 (novel_settings_v2)
- 扩展维度检索 (worldview/power/character等)

使用方法:
    from unified_retrieval_api import UnifiedRetrievalAPI

    api = UnifiedRetrievalAPI()

    # 多源检索
    results = api.retrieve("修仙突破", sources=["technique", "case"])

    # 维度过滤
    techniques = api.search_techniques("战斗胜利", dimension="战斗维度")

    # 场景类型检索
    cases = api.search_cases("开篇场景", scene_type="开篇")
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

try:
    from hybrid_retriever import (
        HybridRetriever,
        SearchResult,
        RetrievalCache,
        POPULAR_QUERIES,
    )
except ImportError:
    raise ImportError("请先创建 hybrid_retriever.py")


class RetrievalSource(Enum):
    """检索源"""

    TECHNIQUE = "writing_techniques_v2"  # 技法库
    CASE = "case_library_v2"  # 案例库
    SETTING = "novel_settings_v2"  # 设定库
    WORLDVIEW = "worldview_element_v1"  # 世界观元素
    POWER = "power_vocabulary_v1"  # 力量词汇
    CHARACTER = "character_relation_v1"  # 人物关系
    EMOTION = "emotion_arc_v1"  # 情感弧线
    DIALOGUE = "dialogue_style_v1"  # 对话风格
    FORESHADOW = "foreshadow_pair_v1"  # 伏笔配对
    COST = "power_cost_v1"  # 力量代价
    AUTHOR = "author_style_v1"  # 作者风格


# Source映射
SOURCE_TO_COLLECTION = {
    "technique": "writing_techniques_v2",
    "case": "case_library_v2",
    "setting": "novel_settings_v2",
    "worldview": "worldview_element_v1",
    "power": "power_vocabulary_v1",
    "character": "character_relation_v1",
    "emotion": "emotion_arc_v1",
    "dialogue": "dialogue_style_v1",
    "foreshadow": "foreshadow_pair_v1",
    "cost": "power_cost_v1",
    "author": "author_style_v1",
}

COLLECTION_TO_SOURCE = {v: k for k, v in SOURCE_TO_COLLECTION.items()}


@dataclass
class UnifiedResult:
    """统一检索结果"""

    source: str  # technique/case/setting等
    collection: str
    rank: int
    score: float
    text: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any]  # 额外元数据


class UnifiedRetrievalAPI:
    """统一检索API"""

    # 维度映射（技法库）
    DIMENSION_MAPPING = {
        "世界观维度": ["世界观构建", "世界观设定", "世界观呈现"],
        "人物维度": ["人物刻画", "人物出场", "人物成长", "人物心理"],
        "剧情维度": ["剧情编织", "伏笔设置", "悬念营造", "转折设计"],
        "战斗维度": ["战斗描写", "战斗胜利", "战斗代价", "功法体系"],
        "情感维度": ["情感描写", "情感冲突", "情感弧线"],
        "意境维度": ["意境营造", "诗意语言", "氛围描写"],
        "对话维度": ["对话技巧", "对话风格", "势力对话"],
        "开篇维度": ["开篇场景", "开篇技巧", "世界观铺垫"],
        "结尾维度": ["结尾场景", "结尾技巧", "情感收束"],
        "叙事维度": ["叙事技巧", "叙事节奏", "叙事张力"],
        "修辞维度": ["修辞手法", "比喻运用", "意象构建"],
    }

    # 场景类型映射（案例库）
    SCENE_TYPE_MAPPING = {
        "开篇": ["01-开篇场景"],
        "人物出场": ["02-人物出场"],
        "战斗": ["03-战斗场景"],
        "对话": ["04-对话场景"],
        "情感": ["05-情感场景"],
        "悬念": ["06-悬念场景"],
        "转折": ["07-转折场景"],
        "结尾": ["08-结尾场景"],
        "环境": ["09-环境场景"],
        "心理": ["10-心理场景"],
        "打脸": ["打脸场景"],
        "高潮": ["高潮场景"],
        "修炼突破": ["修炼突破"],
        "势力登场": ["势力登场"],
        "成长蜕变": ["成长蜕变"],
        "伏笔设置": ["伏笔设置"],
        "伏笔回收": ["伏笔回收"],
        "危机降临": ["危机降临"],
        "资源获取": ["资源获取"],
        "探索发现": ["探索发现"],
        "情报揭示": ["情报揭示"],
        "社交场景": ["社交场景"],
        "阴谋揭露": ["阴谋揭露"],
        "冲突升级": ["冲突升级"],
        "团队组建": ["团队组建"],
        "反派出场": ["反派出场"],
        "恢复休养": ["恢复休养"],
        "回忆场景": ["回忆场景"],
    }

    def __init__(self, use_cache: bool = True, warm_up: bool = False):
        """初始化API"""
        self.retriever = HybridRetriever()
        self.cache = RetrievalCache() if use_cache else None

        if warm_up and self.cache:
            self._warm_up_cache()

    def _warm_up_cache(self):
        """预热缓存"""
        collections = [
            SOURCE_TO_COLLECTION["technique"],
            SOURCE_TO_COLLECTION["case"],
            SOURCE_TO_COLLECTION["worldview"],
            SOURCE_TO_COLLECTION["power"],
        ]
        self.cache.warm_up(self.retriever, POPULAR_QUERIES, collections)

    def _format_result(self, sr: SearchResult, source: str, rank: int) -> UnifiedResult:
        """格式化检索结果"""
        collection = sr.payload.get("_collection", "")

        # 提取文本（兼容不同payload字段名）
        text = str(
            sr.payload.get(
                "content",
                sr.payload.get(
                    "text", sr.payload.get("name", sr.payload.get("技法名称", ""))
                ),
            )
        )

        # 提取元数据（兼容中英文字段名）
        metadata = {}
        if source == "technique":
            metadata = {
                "技法名称": sr.payload.get("name", sr.payload.get("技法名称", "")),
                "维度": sr.payload.get("dimension", sr.payload.get("维度", "")),
                "作家": sr.payload.get("writer", sr.payload.get("作家", "")),
                "标签": sr.payload.get("tags", sr.payload.get("标签", [])),
            }
        elif source == "case":
            metadata = {
                "scene_type": sr.payload.get("scene_type", ""),
                "genre": sr.payload.get("genre", ""),
                "novel_name": sr.payload.get("novel_name", ""),
                "quality_score": sr.payload.get("quality_score", 0),
            }
        elif source == "worldview":
            metadata = {
                "element_type": sr.payload.get("element_type", ""),
                "total_frequency": sr.payload.get("total_frequency", 0),
            }
        elif source == "power":
            metadata = {
                "category": sr.payload.get("category", ""),
                "power_type": sr.payload.get("power_type", ""),
            }
        elif source == "character":
            metadata = {
                "character1": sr.payload.get("character1", ""),
                "character2": sr.payload.get("character2", ""),
            }

        return UnifiedResult(
            source=source,
            collection=collection,
            rank=rank,
            score=sr.score,
            text=text,
            payload=sr.payload,
            metadata=metadata,
        )

    def retrieve(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        top_k: int = 10,
        top_k_per_source: int = 5,
        fusion_strategy: str = "concat",  # concat/rrf/score_weighted
        verbose: bool = False,
    ) -> List[UnifiedResult]:
        """
        多源检索

        Args:
            query: 查询文本
            sources: 检索源列表 ["technique", "case", "worldview"]等，默认全部核心源
            top_k: 最终返回数量
            top_k_per_source: 每个源返回数量
            fusion_strategy: 融合策略
                - concat: 直接拼接
                - rrf: RRF融合（需要所有结果有rank信息）
                - score_weighted: 按score加权排序
            verbose: 详细输出

        Returns:
            List[UnifiedResult]: 统一格式结果
        """
        if sources is None:
            sources = ["technique", "case", "worldview", "power"]

        start_time = time.time()
        all_results = []

        for source in sources:
            collection = SOURCE_TO_COLLECTION.get(source)
            if not collection:
                continue

            # 检查缓存
            cache_key = f"{query}|{collection}|{top_k_per_source}"
            if self.cache:
                cached = self.cache.get(cache_key)
                if cached:
                    for i, sr in enumerate(cached):
                        all_results.append(self._format_result(sr, source, i + 1))
                    if verbose:
                        print(f"  [{source}] 缓存命中")
                    continue

            # 检索
            results = self.retriever.retrieve(
                query, collection, top_k=top_k_per_source, verbose=verbose
            )

            # 缓存
            if self.cache:
                self.cache.set(cache_key, results)

            # 格式化
            for i, sr in enumerate(results):
                all_results.append(self._format_result(sr, source, i + 1))

        # 融合
        if fusion_strategy == "concat":
            # 直接拼接，按源优先级排序
            priority = {s: i for i, s in enumerate(sources)}
            all_results.sort(key=lambda r: (priority.get(r.source, 99), -r.score))
            final_results = all_results[:top_k]

        elif fusion_strategy == "score_weighted":
            # 按score排序
            all_results.sort(key=lambda r: -r.score)
            final_results = all_results[:top_k]

        else:
            # 默认concat
            final_results = all_results[:top_k]

        elapsed = time.time() - start_time
        if verbose:
            print(f"\n[总结] 检索耗时: {elapsed:.3f}s")
            print(f"  总结果: {len(all_results)}条 -> 返回: {len(final_results)}条")

        return final_results

    def search_techniques(
        self,
        query: str,
        dimension: Optional[str] = None,
        writer: Optional[str] = None,
        top_k: int = 5,
        verbose: bool = False,
    ) -> List[UnifiedResult]:
        """
        技法检索

        Args:
            query: 查询文本
            dimension: 维度过滤 "战斗维度"/"人物维度"等
            writer: 作家过滤 "剑尘"/"墨言"等
            top_k: 返回数量
            verbose: 详细输出

        Returns:
            List[UnifiedResult]: 技法结果
        """
        results = self.retrieve(
            query,
            sources=["technique"],
            top_k=top_k * 2,  # 多取一些用于过滤
            verbose=verbose,
        )

        # 维度过滤
        if dimension:
            dimension_keywords = self.DIMENSION_MAPPING.get(dimension, [dimension])
            results = [
                r
                for r in results
                if any(kw in r.metadata.get("维度", "") for kw in dimension_keywords)
            ]

        # 作家过滤
        if writer:
            results = [r for r in results if r.metadata.get("作家", "") == writer]

        return results[:top_k]

    def search_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 5,
        verbose: bool = False,
    ) -> List[UnifiedResult]:
        """
        案例检索

        Args:
            query: 查询文本
            scene_type: 场景类型过滤 "战斗"/"开篇"等
            genre: 题材过滤 "玄幻"/"都市"等
            top_k: 返回数量
            verbose: 详细输出

        Returns:
            List[UnifiedResult]: 案例结果
        """
        results = self.retrieve(
            query,
            sources=["case"],
            top_k=top_k * 2,
            verbose=verbose,
        )

        # 场景类型过滤
        if scene_type:
            scene_keywords = self.SCENE_TYPE_MAPPING.get(scene_type, [scene_type])
            results = [
                r
                for r in results
                if any(kw in r.metadata.get("scene_type", "") for kw in scene_keywords)
            ]

        # 题材过滤
        if genre:
            results = [r for r in results if genre in r.metadata.get("genre", "")]

        return results[:top_k]

    def search_worldview(
        self,
        query: str,
        element_type: Optional[str] = None,
        top_k: int = 5,
        verbose: bool = False,
    ) -> List[UnifiedResult]:
        """
        世界观元素检索

        Args:
            query: 查询文本
            element_type: 元素类型过滤 "地点"/"组织"/"势力"
            top_k: 返回数量
            verbose: 详细输出

        Returns:
            List[UnifiedResult]: 世界观结果
        """
        results = self.retrieve(
            query,
            sources=["worldview"],
            top_k=top_k,
            verbose=verbose,
        )

        # 元素类型过滤
        if element_type:
            results = [
                r for r in results if r.metadata.get("element_type", "") == element_type
            ]

        return results

    def search_power_vocabulary(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 10,
        verbose: bool = False,
    ) -> List[UnifiedResult]:
        """
        力量词汇检索

        Args:
            query: 查询文本
            category: 类别过滤 "境界"/"功法"/"物品"
            top_k: 返回数量
            verbose: 详细输出

        Returns:
            List[UnifiedResult]: 力量词汇结果
        """
        results = self.retrieve(
            query,
            sources=["power"],
            top_k=top_k,
            verbose=verbose,
        )

        # 类别过滤
        if category:
            results = [r for r in results if category in r.metadata.get("category", "")]

        return results

    def search_character_relations(
        self,
        query: str,
        character: Optional[str] = None,
        top_k: int = 5,
        verbose: bool = False,
    ) -> List[UnifiedResult]:
        """
        人物关系检索

        Args:
            query: 查询文本
            character: 人物名称过滤
            top_k: 返回数量
            verbose: 详细输出

        Returns:
            List[UnifiedResult]: 人物关系结果
        """
        results = self.retrieve(
            query,
            sources=["character"],
            top_k=top_k,
            verbose=verbose,
        )

        # 人物过滤
        if character:
            results = [
                r
                for r in results
                if character in r.metadata.get("character1", "")
                or character in r.metadata.get("character2", "")
            ]

        return results

    def retrieve_for_scene(
        self,
        scene_type: str,
        context: Optional[str] = None,
        top_k: int = 3,
        verbose: bool = False,
    ) -> Dict[str, List[UnifiedResult]]:
        """
        场景创作素材检索

        根据场景类型自动选择合适的检索源，
        返回技法+案例+词汇的完整素材包

        Args:
            scene_type: 场景类型 "战斗"/"开篇"/"情感"等
            context: 额外上下文（用于精确匹配）
            top_k: 每类返回数量
            verbose: 详细输出

        Returns:
            Dict[str, List[UnifiedResult]]: 按类型分组的素材
        """
        query = f"{scene_type}场景"
        if context:
            query = f"{context} {scene_type}场景"

        # 根据场景类型选择检索源
        source_map = {
            "战斗": ["technique", "case", "power"],
            "开篇": ["technique", "case", "worldview"],
            "情感": ["technique", "case", "emotion"],
            "对话": ["technique", "dialogue"],
            "悬念": ["technique", "case"],
            "转折": ["technique", "case"],
            "心理": ["technique", "case"],
            "环境": ["technique", "worldview"],
        }

        sources = source_map.get(scene_type, ["technique", "case"])

        results = self.retrieve(
            query, sources=sources, top_k=top_k * len(sources), verbose=verbose
        )

        # 分组
        grouped = defaultdict(list)
        for r in results:
            grouped[r.source].append(r)

        return dict(grouped)

    def get_stats(self) -> Dict[str, Any]:
        """获取检索统计"""
        return {
            "collections": self.retriever.COLLECTION_VECTOR_CONFIG,
            "cache_size": len(self.cache.cache) if self.cache else 0,
            "sources": list(SOURCE_TO_COLLECTION.keys()),
        }


def get_unified_api(warm_up: bool = False) -> UnifiedRetrievalAPI:
    """获取统一检索API（单例模式）"""
    global _UNIFIED_API
    if "_UNIFIED_API" not in globals() or globals().get("_UNIFIED_API") is None:
        globals()["_UNIFIED_API"] = UnifiedRetrievalAPI(warm_up=warm_up)
    return globals()["_UNIFIED_API"]


# 全局API实例
_UNIFIED_API = None


if __name__ == "__main__":
    print("=" * 60)
    print("统一检索API测试")
    print("=" * 60)

    api = UnifiedRetrievalAPI(warm_up=False)

    # 测试1: 多源检索
    print("\n[测试] 多源检索: '修仙突破'")
    results = api.retrieve(
        "修仙突破", sources=["technique", "case", "power"], top_k=3, verbose=True
    )
    for r in results:
        print(f"\n  [{r.source}] rank={r.rank} score={r.score:.4f}")
        print(f"    text: {r.text[:80]}...")
        print(f"    metadata: {r.metadata}")

    # 测试2: 技法检索
    print("\n[测试] 技法检索: '战斗胜利' (dimension='战斗维度')")
    techniques = api.search_techniques("战斗胜利", dimension="战斗维度", top_k=3)
    for t in techniques:
        print(f"\n  [{t.metadata.get('技法名称', '')}] score={t.score:.4f}")
        print(f"    维度: {t.metadata.get('维度', '')}")
        print(f"    作家: {t.metadata.get('作家', '')}")

    # 测试3: 场景素材检索
    print("\n[测试] 场景素材检索: '战斗'")
    materials = api.retrieve_for_scene("战斗", context="主角突破", top_k=2)
    for source, items in materials.items():
        print(f"\n  [{source}] {len(items)}条:")
        for item in items:
            print(f"    - {item.text[:60]}...")

    # 测试4: 统计
    print("\n[统计]")
    stats = api.get_stats()
    print(f"  Collection配置数: {len(stats['collections'])}")
    print(f"  支持源: {stats['sources']}")
