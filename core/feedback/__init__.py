"""
评估反馈回流模块

提供评估反馈收集、处理和章节经验沉淀功能。
"""

from .feedback_collector import FeedbackCollector
from .feedback_processor import FeedbackProcessor
try:
    from .experience_writer import ExperienceWriter
except ImportError:
    ExperienceWriter = None

__all__ = [
    "FeedbackCollector",
    "FeedbackProcessor",
    "ExperienceWriter",
]
