#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一检索接口模块
================

提供统一的多数据源检索API，支持：
1. 小说设定检索（novel_settings_v2）
2. 创作技法检索（writing_techniques_v2）
3. 标杆案例检索（case_library_v2）
4. 扩展维度检索（力量词汇、对话风格、情感弧线）

用法：
    from core.retrieval import UnifiedRetrievalAPI

    api = UnifiedRetrievalAPI()

    # 统一入口 - 同时检索多个数据源
    results = api.retrieve("战斗场景描写", sources=["technique", "case"])

    # 兼容现有接口
    techniques = api.search_techniques("战斗描写", dimension="战斗冲突维度")
    cases = api.search_cases("战斗场景", scene_type="战斗")
    novel = api.search_novel("主角", entity_type="角色")

    # 新增扩展维度检索
    power_vocab = api.search_power_vocabulary("剑法", power_type="剑道")
    dialogues = api.search_dialogue_style("宗门对话", faction="宗门")
    emotion_arcs = api.search_emotion_arc("高潮", arc_type="高潮")
"""

from .unified_retrieval_api import UnifiedRetrievalAPI

__all__ = ["UnifiedRetrievalAPI"]
