# -*- coding: utf-8 -*-
"""
智能反馈系统 - 统一入口

⚠️ 状态说明：扩展备用，当前不启用

当前用户反馈通过对话中 AI 直接处理，并更新追踪文件（如 hook_ledger.md），
无需通过本 Python 模块。本模块为未来扩展预留：
  - Web 界面反馈处理
  - 自动化冲突检测
  - 影响范围分析

对话形式使用时，AI 直接识别意图并更新文件，无需此模块。

功能清单（预留）：
  1. 意图识别 - 识别用户修改/重写意图
  2. 追踪同步 - 修改后自动更新追踪文件
  3. 影响分析 - 分析修改的影响范围
  4. 冲突检测 - 检测多作家输出之间的冲突
"""

from .types import (
    # 枚举类型
    ModificationLevel,
    RewriteMode,
    ModificationStrategy,
    ConflictSeverity,
    # 数据类型
    IntentResult,
    ParsedFeedback,
    FeedbackLocation,
    ContentMask,
    ContentSection,
    ModificationResult,
    PlotFramework,
    TrackingUpdate,
    InfluenceReport,
    Conflict,
    SafetyCheck,
)

from .intent_recognizer import (
    IntentRecognizer,
    recognize_intent,
)

from .tracking_syncer import (
    TrackingSyncer,
    sync_tracking,
)

from .influence_analyzer import (
    InfluenceAnalyzer,
    analyze_influence,
)

from .conflict_detector import (
    ConflictDetector,
    detect_conflicts,
)


__all__ = [
    # 枚举类型
    "ModificationLevel",
    "RewriteMode",
    "ModificationStrategy",
    "ConflictSeverity",
    # 数据类型
    "IntentResult",
    "ParsedFeedback",
    "FeedbackLocation",
    "ContentMask",
    "ContentSection",
    "ModificationResult",
    "PlotFramework",
    "TrackingUpdate",
    "InfluenceReport",
    "Conflict",
    "SafetyCheck",
    # 意图识别
    "IntentRecognizer",
    "recognize_intent",
    # 追踪同步
    "TrackingSyncer",
    "sync_tracking",
    # 影响分析
    "InfluenceAnalyzer",
    "analyze_influence",
    # 冲突检测
    "ConflictDetector",
    "detect_conflicts",
]


def quick_analyze(user_input: str, content: str = "") -> dict:
    """
    快速分析用户输入

    Args:
        user_input: 用户输入
        content: 当前内容（可选）

    Returns:
        分析结果字典
    """
    # 1. 识别意图
    intent = recognize_intent(user_input)

    # 2. 分析影响
    influence = analyze_influence(intent.modification_level)

    return {
        "intent": {
            "is_rewrite": intent.is_rewrite,
            "modification_level": intent.modification_level.name,
            "rewrite_mode": intent.rewrite_mode.value if intent.rewrite_mode else None,
            "confidence": intent.confidence,
            "routing": intent.routing,
            "target_chapter": intent.target_chapter,
            "keywords": intent.keywords,
        },
        "influence": {
            "severity": influence.severity,
            "current_chapter": influence.current_chapter,
            "tracking_files": influence.tracking_files,
            "needs_manual_confirm": len(influence.tracking_files) > 0
            or influence.severity == "HIGH",
        },
    }
