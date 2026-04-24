# core/feedback/feedback_dispatcher.py
"""统一反馈调度入口

职责划分：
- inspiration 类（灵感引擎反馈）→ resonance_feedback.handle_reader_feedback → Qdrant
- quality 类（写作质量反馈）→ FeedbackCollector → feedback_history.json

设计文档：docs/superpowers/plans/2026-04-15-feedback-unification.md
"""

from pathlib import Path
from typing import Dict, Any, Callable, Optional

from core.inspiration.resonance_feedback import handle_reader_feedback
from core.feedback.feedback_collector import FeedbackCollector

# 极性映射：feedback_type → polarity
_POLARITY_MAP = {
    "rewrite_request": "-",
    "quality_feedback": "+",
    "style_feedback": "-",
    "consistency_feedback": "-",
    "detail_feedback": "-",
    "excessive_feedback": "-",
    "general_feedback": "?",
}


class FeedbackDispatcher:
    """统一反馈调度器

    Usage:
        dispatcher = FeedbackDispatcher()
        result = dispatcher.dispatch(
            feedback_category="inspiration",
            user_input="第二章那句话很震撼",
            scene_type_lookup=lambda ch: "情感",
        )
    """

    def __init__(self, history_path: Optional[Path] = None):
        self._history_path = history_path or Path("data/feedback_history.json")
        self._collector = FeedbackCollector()
        self._collector.load_history(self._history_path)

    def dispatch(
        self,
        feedback_category: str,
        user_input: str,
        scene_type_lookup: Optional[Callable[[str], str]] = None,
        is_overturn: bool = False,
    ) -> Dict[str, Any]:
        """路由反馈到对应子系统

        Args:
            feedback_category: "inspiration"（灵感引擎反馈）或 "quality"（写作质量反馈）
            user_input: 用户原始输入
            scene_type_lookup: 章节→场景类型映射（inspiration 类必须提供）
            is_overturn: 是否为推翻事件（inspiration 类）

        Returns:
            {
                "source": "resonance" | "collector",
                "feedback_type": str,
                "summary": {"polarity": str, "issue": str, ...},
                ...原始返回字段
            }
        """
        if feedback_category == "inspiration":
            return self._dispatch_to_resonance(
                user_input, scene_type_lookup, is_overturn
            )
        else:
            return self._dispatch_to_collector(user_input)

    def _dispatch_to_resonance(
        self,
        user_input: str,
        scene_type_lookup: Optional[Callable],
        is_overturn: bool,
    ) -> Dict[str, Any]:
        """灵感引擎反馈 → resonance_feedback"""
        if scene_type_lookup is None:
            scene_type_lookup = lambda ch: "未知"

        result = handle_reader_feedback(
            user_input=user_input,
            scene_type_lookup=scene_type_lookup,
            is_overturn=is_overturn,
        )
        return {
            "source": "resonance",
            "feedback_type": "reader_moment_feedback",
            "summary": {
                "polarity": "+" if not is_overturn else "overturn",
                "issue": user_input[:50],
            },
            **result,
        }

    def _dispatch_to_collector(self, user_input: str) -> Dict[str, Any]:
        """写作质量反馈 → FeedbackCollector"""
        fb = self._collector.collect_from_explicit(user_input)
        self._collector.save_history(self._history_path)

        polarity = _POLARITY_MAP.get(fb.get("feedback_type", "general_feedback"), "?")
        return {
            "source": "collector",
            "feedback_type": fb.get("feedback_type", "general_feedback"),
            "summary": {
                "polarity": polarity,
                "issue": fb.get("issue", ""),
                "severity": fb.get("severity", "medium"),
                "scene_type": fb.get("scene_type"),
            },
            **fb,
        }
