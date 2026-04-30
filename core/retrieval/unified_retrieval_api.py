#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一检索API
===========

兼容所有现有调用方式，提供统一的多数据源检索接口。

核心功能：
1. 统一入口：retrieve() - 同时检索多个数据源
2. 兼容现有接口：search_techniques、search_cases、search_novel
3. 新增扩展维度检索：力量词汇、对话风格、情感弧线
4. 支持缓存管理

使用方法：
    from core.retrieval import UnifiedRetrievalAPI

    api = UnifiedRetrievalAPI()

    # 统一检索
    results = api.retrieve("战斗场景", sources=["technique", "case"], top_k=5)

    # 技法检索
    techniques = api.search_techniques("战斗描写", dimension="战斗冲突维度")

    # 案例检索
    cases = api.search_cases("战斗", scene_type="战斗", genre="玄幻")

    # 小说设定检索
    characters = api.search_novel("主角", entity_type="角色")
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from functools import lru_cache

# 导入现有检索器
from modules.knowledge_base.hybrid_search_manager import HybridSearchManager

# 导入配置
from core.config_loader import (
    get_project_root,
    get_qdrant_url,
    get_model_path,
    get_collection_name,
)

# 导入日志工具
from core.logging_utils import get_logger

# 导入 metrics（可选依赖，prometheus 未安装时 record_retrieval 为 no-op）
try:
    from core.metrics import record_retrieval
except ImportError:

    def record_retrieval(source, dimension=None, latency_seconds=0.0, results_count=0):
        pass


class UnifiedRetrievalAPI:
    """
    统一检索API

    兼容所有现有调用方式，提供统一的多数据源检索接口。

    复用 HybridSearchManager（BGE-M3混合检索）作为底层检索引擎。

    数据源：
    - novel: 小说设定库（novel_settings_v2）
    - technique: 创作技法库（writing_techniques_v2）
    - case: 标杆案例库（case_library_v2）

    扩展维度：
    - power_vocabulary: 力量词汇检索
    - dialogue_style: 对话风格检索
    - emotion_arc: 情感弧线检索
    """

    # 支持的数据源（扩展版：支持8个JSON库）
    SOURCE_TYPES = [
        "novel",
        "technique",
        "case",
        # 8个扩展维度（JSON库）
        "worldview_element",
        "character_relation",
        "power_vocabulary",
        "dialogue_style",
        "emotion_arc",
        "author_style",
        "foreshadow_pair",
        "power_cost",
    ]

    # 技法维度列表（与 HybridSearchManager 保持一致）
    TECHNIQUE_DIMENSIONS = [
        "世界观维度",
        "剧情维度",
        "人物维度",
        "战斗冲突维度",
        "氛围意境维度",
        "叙事维度",
        "主题维度",
        "情感维度",
        "读者体验维度",
        "元维度",
        "节奏维度",
    ]

    # 实体类型列表（与 HybridSearchManager 保持一致）
    ENTITY_TYPES = ["势力", "派系", "角色", "力量体系", "力量派别", "时代", "事件"]

    # 力量类型列表
    POWER_TYPES = [
        "剑道",
        "刀法",
        "拳法",
        "掌法",
        "指法",
        "内功",
        "外功",
        "轻功",
        "暗器",
        "神术",
        "法术",
        "符篆",
        "阵法",
        "异能",
        "血脉",
        "兽魂",
    ]

    # 派系类型列表
    FACTION_TYPES = [
        "宗门",
        "世家",
        "朝廷",
        "军队",
        "商会",
        "江湖",
        "隐门",
        "邪派",
    ]

    # 情感弧线类型列表
    ARC_TYPES = [
        "开局",
        "发展",
        "高潮",
        "转折",
        "结局",
        "低谷",
        "复苏",
        "蜕变",
    ]

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        use_docker: bool = True,
        weight_preset: str = "general",
        use_cache: bool = True,
        cache_ttl: int = 300,
    ):
        """
        初始化统一检索API

        Args:
            project_dir: 项目根目录（默认从配置加载）
            use_docker: 是否使用 Docker Qdrant
            weight_preset: 权重预设 (general/semantic/exact/dense_only)
            use_cache: 是否启用缓存
            cache_ttl: 缓存有效期（秒）
        """
        # 从配置加载路径
        if project_dir is None:
            self.project_dir = get_project_root()
        else:
            self.project_dir = Path(project_dir)

        # 初始化底层检索器
        self._search_manager = HybridSearchManager(
            project_dir=self.project_dir,
            use_docker=use_docker,
            weight_preset=weight_preset,
        )

        # 缓存配置
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}

        # 权重预设
        self.weight_preset = weight_preset

        # 检索延迟日志器
        self._logger = get_logger("retrieval")

    def _get_cache_key(
        self,
        query: str,
        source: str,
        filters: Optional[Dict] = None,
        top_k: int = 10,
    ) -> str:
        """生成缓存键"""
        filter_str = str(filters) if filters else ""
        return f"{source}:{query}:{filter_str}:{top_k}"

    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """获取缓存结果"""
        if not self.use_cache:
            return None

        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self.cache_ttl:
                return self._cache[cache_key]

        return None

    def _set_cache(self, cache_key: str, result: Any):
        """设置缓存"""
        if self.use_cache:
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()

    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        self._cache_timestamps.clear()

    # ==================== 统一入口 ====================

    def retrieve(
        self,
        query: str,
        sources: List[str] = ["novel", "technique", "case"],
        filters: Optional[Dict] = None,
        top_k: int = 5,
        use_rerank: bool = True,
    ) -> Dict[str, List[Dict]]:
        """
        统一入口 - 同时检索多个数据源

        Args:
            query: 查询文本
            sources: 数据源列表 ["novel", "technique", "case", ...]
            filters: 过滤条件字典
                - novel: {"entity_type": "角色"}
                - technique: {"dimension": "战斗冲突维度"}
                - case: {"scene_type": "战斗", "genre": "玄幻"}
            top_k: 每个数据源返回数量
            use_rerank: 是否使用 ColBERT 重排

        Returns:
            Dict[str, List[Dict]]: 各数据源的检索结果
            {
                "novel": [...],
                "technique": [...],
                "case": [...],
                ...
            }
        """
        results = {}
        start_time = time.time()

        try:
            for source in sources:
                if source not in self.SOURCE_TYPES:
                    continue

                # 检查缓存
                cache_key = self._get_cache_key(query, source, filters, top_k)
                cached_result = self._get_cached(cache_key)
                if cached_result is not None:
                    results[source] = cached_result
                    continue

                # 根据数据源调用对应方法
                source_filters = filters.get(source, {}) if filters else {}

                if source == "novel":
                    result = self._search_manager.search_novel(
                        query=query,
                        entity_type=source_filters.get("entity_type"),
                        top_k=top_k,
                        use_rerank=use_rerank,
                    )
                elif source == "technique":
                    result = self._search_manager.search_technique(
                        query=query,
                        dimension=source_filters.get("dimension"),
                        top_k=top_k,
                        use_rerank=use_rerank,
                    )
                elif source == "case":
                    result = self._search_manager.search_case(
                        query=query,
                        scene_type=source_filters.get("scene_type"),
                        genre=source_filters.get("genre"),
                        top_k=top_k,
                        use_rerank=use_rerank,
                    )
                elif source == "power_vocabulary":
                    result = self.search_power_vocabulary(
                        query=query,
                        power_type=source_filters.get("power_type"),
                        top_k=top_k,
                        use_rerank=use_rerank,
                    )
                elif source == "dialogue_style":
                    result = self.search_dialogue_style(
                        query=query,
                        faction=source_filters.get("faction"),
                        top_k=top_k,
                        use_rerank=use_rerank,
                    )
                elif source == "emotion_arc":
                    result = self.search_emotion_arc(
                        query=query,
                        arc_type=source_filters.get("arc_type"),
                        top_k=top_k,
                        use_rerank=use_rerank,
                    )
                elif source == "worldview_element":
                    result = self.search_worldview_element(
                        query=query,
                        element_type=source_filters.get("element_type"),
                        top_k=top_k,
                        use_rerank=use_rerank,
                    )
                elif source == "character_relation":
                    result = self.search_character_relation(
                        query=query,
                        relation_type=source_filters.get("relation_type"),
                        top_k=top_k,
                        use_rerank=use_rerank,
                    )
                elif source == "author_style":
                    result = self.search_author_style(
                        query=query,
                        top_k=top_k,
                        use_rerank=use_rerank,
                    )
                elif source == "foreshadow_pair":
                    result = self.search_foreshadow_pair(
                        query=query,
                        top_k=top_k,
                        use_rerank=use_rerank,
                    )
                elif source == "power_cost":
                    result = self.search_power_cost(
                        query=query,
                        power_type=source_filters.get("power_type"),
                        top_k=top_k,
                        use_rerank=use_rerank,
                    )
                else:
                    # 未知数据源，返回空列表
                    result = []

                results[source] = result
                self._set_cache(cache_key, result)

        except Exception as e:
            # 异常时也记录延迟日志
            elapsed_ms = (time.time() - start_time) * 1000
            self._logger.error(
                "检索异常",
                query_len=len(query),
                sources=sources,
                elapsed_ms=round(elapsed_ms, 1),
                error=str(e),
            )
            raise

        # 记录检索延迟日志
        elapsed_ms = (time.time() - start_time) * 1000
        total_results = sum(len(r) for r in results.values() if isinstance(r, list))
        self._logger.info(
            "检索完成",
            query_len=len(query),
            sources=sources,
            total_results=total_results,
            elapsed_ms=round(elapsed_ms, 1),
            use_rerank=use_rerank,
        )

        # Prometheus 指标（prometheus_client 未安装时为 no-op）
        record_retrieval(
            source=",".join(sources),
            latency_seconds=elapsed_ms / 1000,
            results_count=total_results,
        )

        return results

    # ==================== 兼容现有接口 ====================

    def search_techniques(
        self,
        query: str,
        dimension: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        创作技法检索（兼容现有接口）

        Args:
            query: 查询文本
            dimension: 维度过滤（世界观维度、剧情维度等）
            top_k: 返回数量
            min_score: 最低相似度
            use_rerank: 是否使用 ColBERT 重排

        Returns:
            List[Dict]: 检索结果列表
        """
        return self._search_manager.search_technique(
            query=query,
            dimension=dimension,
            top_k=top_k,
            min_score=min_score,
            use_rerank=use_rerank,
        )

    # ── 维度专属技法检索（各写手 skill 便捷接口）──────────────────────────

    def search_by_keywords(
        self,
        keywords: list,
        dimension: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """关键词列表合并为查询串后检索技法"""
        query = " ".join(str(k) for k in keywords)
        return self.search_techniques(query, dimension=dimension, top_k=top_k)

    # ── 世界观维度（苍澜） ──────────────────────────────────────────────────

    def search_worldview_techniques(
        self,
        query: str = "世界观构建",
        dimension: str = "世界观维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索世界观维度技法"""
        return self.search_techniques(query, dimension=dimension, top_k=limit)

    def get_worldview_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取世界观专家级技法（史诗级世界观 + 力量体系）"""
        return self.search_techniques(
            "史诗级世界观架构 力量体系设计 世界观自生长",
            dimension="世界观维度",
            top_k=top_k,
        )

    # ── 剧情维度（玄一） ────────────────────────────────────────────────────

    def search_plot_techniques(
        self,
        query: str = "剧情推进",
        dimension: str = "剧情维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索剧情维度技法"""
        return self.search_techniques(query, dimension=dimension, top_k=limit)

    def search_foreshadowing_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索伏笔设置技法"""
        return self.search_techniques(
            "伏笔设置 埋线技法 伏笔回收",
            dimension="剧情维度",
            top_k=top_k,
        )

    def search_suspense_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索悬念制造技法"""
        return self.search_techniques(
            "悬念制造 钩子设计 读者好奇心",
            dimension="叙事维度",
            top_k=top_k,
        )

    def search_reversal_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索反转技法"""
        return self.search_techniques(
            "剧情反转 意外结局 逆转时机",
            dimension="剧情维度",
            top_k=top_k,
        )

    def get_plot_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取剧情专家级技法"""
        return self.search_techniques(
            "史诗级剧情架构 伏笔回收 三幕结构 高潮设计",
            dimension="剧情维度",
            top_k=top_k,
        )

    # ── 氛围意境维度（云溪） ────────────────────────────────────────────────

    def search_poetry_techniques(
        self,
        query: str = "氛围意境",
        dimension: str = "氛围意境维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索氛围意境维度技法"""
        return self.search_techniques(query, dimension=dimension, top_k=limit)

    def search_poetry_by_keywords(
        self, keywords: list, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """关键词检索氛围意境技法"""
        query = " ".join(str(k) for k in keywords)
        return self.search_techniques(query, dimension="氛围意境维度", top_k=top_k)

    def get_poetry_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取氛围意境专家级技法"""
        return self.search_techniques(
            "诗意氛围 意境营造 五感写作 留白技法",
            dimension="氛围意境维度",
            top_k=top_k,
        )

    # ── 人物维度（墨言） ────────────────────────────────────────────────────

    def search_character_techniques(
        self,
        query: str = "人物刻画",
        dimension: str = "人物维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索人物维度技法"""
        return self.search_techniques(query, dimension=dimension, top_k=limit)

    def search_emotion_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索情感描写技法"""
        return self.search_techniques(
            "情感描写 情绪渲染 内心独白",
            dimension="情感维度",
            top_k=top_k,
        )

    def get_character_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取人物塑造专家级技法"""
        return self.search_techniques(
            "史诗级人物塑造 角色弧光 创伤成长 群像技法",
            dimension="人物维度",
            top_k=top_k,
        )

    # ── 战斗冲突维度（剑尘） ────────────────────────────────────────────────

    def search_battle_techniques(
        self,
        query: str = "战斗描写",
        dimension: str = "战斗冲突维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索战斗冲突维度技法"""
        return self.search_techniques(query, dimension=dimension, top_k=limit)

    def search_battle_by_keywords(
        self, keywords: list, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """关键词检索战斗技法"""
        query = " ".join(str(k) for k in keywords)
        return self.search_techniques(query, dimension="战斗冲突维度", top_k=top_k)

    def get_battle_expert_techniques(
        self, power_system: str = "", top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """获取战斗冲突专家级技法，可按力量体系过滤"""
        query = f"史诗级战斗设计 力量体系对抗 弱胜强技法 {power_system}".strip()
        return self.search_techniques(query, dimension="战斗冲突维度", top_k=top_k)

    def search_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.5,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        标杆案例检索（兼容现有接口）

        Args:
            query: 查询文本
            scene_type: 场景类型过滤
            genre: 题材类型过滤
            top_k: 返回数量
            min_score: 最低相似度
            use_rerank: 是否使用 ColBERT 重排

        Returns:
            List[Dict]: 检索结果列表
        """
        return self._search_manager.search_case(
            query=query,
            scene_type=scene_type,
            genre=genre,
            top_k=top_k,
            min_score=min_score,
            use_rerank=use_rerank,
        )

    # ==================== 写手专属案例检索 ====================

    def search_worldview_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """世界观/势力案例检索（苍澜专用）"""
        return self.search_cases(query=query, scene_type=scene_type, top_k=limit)

    def search_plot_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """剧情/伏笔案例检索（玄一专用）"""
        return self.search_cases(query=query, scene_type=scene_type, top_k=limit)

    def search_poetry_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """意境/诗意案例检索（云溪专用）"""
        return self.search_cases(query=query, scene_type=scene_type, top_k=limit)

    def search_character_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """人物/情感案例检索（墨言专用）"""
        return self.search_cases(query=query, scene_type=scene_type, top_k=limit)

    def search_battle_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """战斗/力量案例检索（剑尘专用）"""
        return self.search_cases(query=query, scene_type=scene_type, top_k=limit)

    def search_novel(
        self,
        query: str,
        entity_type: Optional[str] = None,
        top_k: int = 10,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        小说设定检索（兼容现有接口）

        Args:
            query: 查询文本
            entity_type: 实体类型过滤（角色、势力、力量体系等）
            top_k: 返回数量
            use_rerank: 是否使用 ColBERT 重排

        Returns:
            List[Dict]: 检索结果列表
        """
        return self._search_manager.search_novel(
            query=query,
            entity_type=entity_type,
            top_k=top_k,
            use_rerank=use_rerank,
        )

    # ==================== 新增扩展维度检索 ====================

    def search_power_vocabulary(
        self,
        query: str,
        power_type: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        力量词汇检索

        Args:
            query: 查询文本（如 "剑法"、"神术"）
            power_type: 力量类型过滤（剑道、刀法、拳法、神术等）
            top_k: 返回数量
            min_score: 最低相似度
            use_rerank: 是否使用 ColBERT 重排

        Returns:
            List[Dict]: 检索结果列表

        Note:
            力量词汇从小说设定库中检索，entity_type="力量体系" 或 "力量派别"
        """
        # 力量词汇检索从小说设定库中获取
        # 使用 power_type 作为额外的语义提示
        enhanced_query = query
        if power_type:
            enhanced_query = f"{power_type} {query}"

        results = self._search_manager.search_novel(
            query=enhanced_query,
            entity_type="力量体系",  # 优先检索力量体系
            top_k=top_k * 2,  # 扩大召回范围
            use_rerank=use_rerank,
        )

        # 如果力量体系结果不足，补充力量派别
        if len(results) < top_k:
            additional = self._search_manager.search_novel(
                query=enhanced_query,
                entity_type="力量派别",
                top_k=top_k - len(results),
                use_rerank=use_rerank,
            )
            results.extend(additional)

        # 过滤低分结果
        filtered = [r for r in results if r.get("score", 0) >= min_score]

        return filtered[:top_k]

    def search_dialogue_style(
        self,
        query: str,
        faction: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        对话风格检索

        Args:
            query: 查询文本（如 "宗门对话"、"江湖言语"）
            faction: 派系类型过滤（宗门、世家、朝廷、江湖等）
            top_k: 返回数量
            min_score: 最低相似度
            use_rerank: 是否使用 ColBERT 重排

        Returns:
            List[Dict]: 检索结果列表

        Note:
            对话风格从小说设定库中检索，entity_type="势力" 或 "派系"
            同时从案例库中检索相关对话片段
        """
        # 对话风格检索从小说设定库和案例库双源检索
        enhanced_query = query
        if faction:
            enhanced_query = f"{faction} {query}"

        # 1. 从小说设定库检索势力/派系设定
        setting_results = self._search_manager.search_novel(
            query=enhanced_query,
            entity_type="势力",
            top_k=top_k,
            use_rerank=use_rerank,
        )

        # 2. 从案例库检索对话场景案例
        case_results = self._search_manager.search_case(
            query=f"对话 {enhanced_query}",
            scene_type="对话",  # 对话场景
            top_k=top_k,
            min_score=min_score,
            use_rerank=use_rerank,
        )

        # 合并结果
        combined = []

        # 添加设定结果（标记来源）
        for r in setting_results:
            r["_source"] = "novel_setting"
            combined.append(r)

        # 添加案例结果（标记来源）
        for r in case_results:
            r["_source"] = "case_library"
            combined.append(r)

        # 按分数排序并截取 top_k
        combined.sort(key=lambda x: x.get("score", 0), reverse=True)

        # 过滤低分结果
        filtered = [r for r in combined[: top_k * 2] if r.get("score", 0) >= min_score]

        return filtered[:top_k]

    def search_emotion_arc(
        self,
        query: str,
        arc_type: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        情感弧线检索

        Args:
            query: 查询文本（如 "高潮场景"、"低谷描写"）
            arc_type: 情感弧线类型过滤（开局、发展、高潮、转折、结局等）
            top_k: 返回数量
            min_score: 最低相似度
            use_rerank: 是否使用 ColBERT 重排

        Returns:
            List[Dict]: 检索结果列表

        Note:
            情感弧线从创作技法库和案例库双源检索
        """
        # 情感弧线检索从技法库和案例库双源检索
        enhanced_query = query
        if arc_type:
            enhanced_query = f"{arc_type} {query}"

        # 1. 从创作技法库检索情感维度技法
        technique_results = self._search_manager.search_technique(
            query=enhanced_query,
            dimension="情感维度",
            top_k=top_k,
            min_score=min_score,
            use_rerank=use_rerank,
        )

        # 2. 从案例库检索情感弧线案例
        # 根据 arc_type 推断 scene_type
        scene_type_map = {
            "开局": "开篇",
            "发展": "日常",
            "高潮": "战斗",
            "转折": "转折",
            "结局": "结局",
            "低谷": "低谷",
            "复苏": "转折",
            "蜕变": "转折",
        }
        inferred_scene_type = scene_type_map.get(arc_type) if arc_type else None

        case_results = self._search_manager.search_case(
            query=enhanced_query,
            scene_type=inferred_scene_type,
            top_k=top_k,
            min_score=min_score,
            use_rerank=use_rerank,
        )

        # 合并结果
        combined = []

        # 添加技法结果（标记来源）
        for r in technique_results:
            r["_source"] = "writing_techniques"
            combined.append(r)

        # 添加案例结果（标记来源）
        for r in case_results:
            r["_source"] = "case_library"
            combined.append(r)

        # 按分数排序并截取 top_k
        combined.sort(key=lambda x: x.get("score", 0), reverse=True)

        # 过滤低分结果
        filtered = [r for r in combined[: top_k * 2] if r.get("score", 0) >= min_score]

        return filtered[:top_k]

    # ==================== 新增扩展维度检索（8个JSON库） ====================

    def search_worldview_element(
        self,
        query: str,
        element_type: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        世界观元素检索

        Args:
            query: 查询文本（如 "城"、"宗"、"门"）
            element_type: 元素类型过滤（地点/组织/势力）
            top_k: 返回数量
            min_score: 最低相似度
            use_rerank: 是否使用重排

        Returns:
            命名规律列表
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            client = QdrantClient(url=get_qdrant_url())

            # 构建filter
            filter_conditions = []
            if element_type:
                filter_conditions.append(
                    models.FieldCondition(
                        key="element_type",
                        match=models.MatchValue(value=element_type),
                    )
                )

            filter_obj = (
                models.Filter(must=filter_conditions) if filter_conditions else None
            )

            # scroll获取数据
            results = client.scroll(
                collection_name="worldview_element_v1",
                with_payload=True,
                with_vectors=False,
                limit=top_k * 3,
                query_filter=filter_obj,
            )[0]

            # 按频次排序
            sorted_results = sorted(
                [p.payload for p in results],
                key=lambda x: x.get("total_frequency", 0),
                reverse=True,
            )

            return sorted_results[:top_k]

        except Exception as e:
            print(f"[警告] 世界观元素检索失败: {e}")
            return []

    def search_character_relation(
        self,
        query: str,
        relation_type: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        人物关系检索

        Args:
            query: 查询文本（如 "师徒"、"同门"）
            relation_type: 关系类型过滤
            top_k: 返回数量
            min_score: 最低相似度

        Returns:
            关系模式列表
        """
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url=get_qdrant_url())

            results = client.scroll(
                collection_name="character_relation_v1",
                with_payload=True,
                with_vectors=False,
                limit=top_k * 3,
            )[0]

            # 按共现次数排序
            sorted_results = sorted(
                [p.payload for p in results],
                key=lambda x: x.get("cooccurrence_count", 0),
                reverse=True,
            )

            return sorted_results[:top_k]

        except Exception as e:
            print(f"[警告] 人物关系检索失败: {e}")
            return []

    def search_author_style(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        作者风格检索

        Args:
            query: 查询文本（如 "简洁"、"华丽"）
            top_k: 返回数量
            min_score: 最低相似度

        Returns:
            风格特征列表
        """
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url=get_qdrant_url())

            results = client.scroll(
                collection_name="author_style_v1",
                with_payload=True,
                with_vectors=False,
                limit=top_k,
            )[0]

            return [p.payload for p in results]

        except Exception as e:
            print(f"[警告] 作者风格检索失败: {e}")
            return []

    def search_foreshadow_pair(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        伏笔配对检索

        Args:
            query: 查询文本（如 "悬念伏笔"）
            top_k: 返回数量

        Returns:
            伏笔配对列表
        """
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url=get_qdrant_url())

            results = client.scroll(
                collection_name="foreshadow_pair_v1",
                with_payload=True,
                with_vectors=False,
                limit=top_k,
            )[0]

            return [p.payload for p in results]

        except Exception as e:
            print(f"[警告] 伏笔配对检索失败: {e}")
            return []

    def search_power_cost(
        self,
        query: str,
        power_type: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        力量代价检索

        Args:
            query: 查询文本（如 "体力代价"）
            power_type: 力量类型过滤
            top_k: 返回数量

        Returns:
            代价模板列表
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            client = QdrantClient(url=get_qdrant_url())

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

            results = client.scroll(
                collection_name="power_cost_v1",
                with_payload=True,
                with_vectors=False,
                limit=top_k,
                query_filter=filter_obj,
            )[0]

            return [p.payload for p in results]

        except Exception as e:
            print(f"[警告] 力量代价检索失败: {e}")
            return []

    # ==================== 辅助方法 ====================

    def set_weight_preset(self, preset: str):
        """
        设置权重预设

        Args:
            preset: 预设名称 (general/semantic/exact/dense_only)
        """
        self._search_manager.set_weight_preset(preset)
        self.weight_preset = preset

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        return self._search_manager.get_stats()

    def list_dimensions(self) -> List[str]:
        """列出所有技法维度"""
        return self.TECHNIQUE_DIMENSIONS

    def list_entity_types(self) -> List[str]:
        """列出所有实体类型"""
        return self.ENTITY_TYPES

    def list_power_types(self) -> List[str]:
        """列出所有力量类型"""
        return self.POWER_TYPES

    def list_faction_types(self) -> List[str]:
        """列出所有派系类型"""
        return self.FACTION_TYPES

    def list_arc_types(self) -> List[str]:
        """列出所有情感弧线类型"""
        return self.ARC_TYPES

    def list_characters(self) -> List[str]:
        """列出所有角色名称"""
        return self._search_manager.list_characters()

    def list_factions(self) -> List[str]:
        """列出所有势力名称"""
        return self._search_manager.list_factions()

    def get_character(self, name: str) -> Optional[Dict[str, Any]]:
        """获取角色设定"""
        return self._search_manager.get_character(name)

    def get_faction(self, name: str) -> Optional[Dict[str, Any]]:
        """获取势力设定"""
        return self._search_manager.get_faction(name)


# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="统一检索API")
    parser.add_argument("--query", type=str, help="查询文本")
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["technique", "case"],
        choices=[
            "novel",
            "technique",
            "case",
            "power_vocabulary",
            "dialogue_style",
            "emotion_arc",
        ],
        help="数据源列表",
    )
    parser.add_argument("--dimension", type=str, help="技法维度过滤")
    parser.add_argument("--scene-type", type=str, help="场景类型过滤")
    parser.add_argument("--entity-type", type=str, help="实体类型过滤")
    parser.add_argument("--top-k", type=int, default=5, help="返回数量")
    parser.add_argument("--no-rerank", action="store_true", help="禁用 ColBERT 重排")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument(
        "--list",
        type=str,
        choices=[
            "dimensions",
            "entity_types",
            "power_types",
            "faction_types",
            "arc_types",
        ],
        help="列出类型",
    )
    parser.add_argument(
        "--preset",
        choices=["general", "semantic", "exact", "dense_only"],
        default="general",
        help="权重预设",
    )

    args = parser.parse_args()

    api = UnifiedRetrievalAPI(weight_preset=args.preset)

    if args.stats:
        print("\n📊 数据库统计")
        print("=" * 60)
        stats = api.get_stats()
        for name, info in stats.items():
            print(f"\n{name}:")
            for k, v in info.items():
                print(f"  {k}: {v}")
        print("=" * 60)

    elif args.list:
        items = []
        if args.list == "dimensions":
            items = api.list_dimensions()
        elif args.list == "entity_types":
            items = api.list_entity_types()
        elif args.list == "power_types":
            items = api.list_power_types()
        elif args.list == "faction_types":
            items = api.list_faction_types()
        elif args.list == "arc_types":
            items = api.list_arc_types()

        print(f"\n📋 {args.list}列表:")
        for i, item in enumerate(items, 1):
            print(f"  [{i}] {item}")

    elif args.query:
        print(f"\n🔍 查询: {args.query}")
        print(f"   数据源: {args.sources}")
        print(f"   重排: {'禁用' if args.no_rerank else '启用'}")
        print("=" * 60)

        # 构建过滤条件
        filters = {}
        if args.dimension:
            filters["technique"] = {"dimension": args.dimension}
        if args.scene_type:
            filters["case"] = {"scene_type": args.scene_type}
        if args.entity_type:
            filters["novel"] = {"entity_type": args.entity_type}

        results = api.retrieve(
            query=args.query,
            sources=args.sources,
            filters=filters if filters else None,
            top_k=args.top_k,
            use_rerank=not args.no_rerank,
        )

        for source, items in results.items():
            print(f"\n[{source}] 找到 {len(items)} 条结果:")
            for i, r in enumerate(items, 1):
                name = r.get("name", r.get("novel_name", "未知"))
                score = r.get("score", 0)
                print(f"  [{i}] {name}")
                print(f"      相似度: {score:.4f}")

                if "dimension" in r:
                    print(f"      维度: {r['dimension']}")
                if "writer" in r:
                    print(f"      作家: {r['writer']}")
                if "type" in r:
                    print(f"      类型: {r['type']}")

                content = r.get("content", "")[:150]
                if content:
                    print(f"      内容: {content}...")
