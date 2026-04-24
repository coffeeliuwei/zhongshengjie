# -*- coding: utf-8 -*-
"""
智能反馈系统 - 数据类型定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ModificationLevel(Enum):
    """修改层级"""

    WORD_POLISH = 1  # 文字润色 - 不改变内容
    CONTENT_TWEAK = 2  # 内容微调 - 改细节
    PLOT_CHANGE = 3  # 剧情修改 - 改事件/结局
    SETTING_CHANGE = 4  # 设定修改 - 全书影响


class RewriteMode(Enum):
    """重写模式"""

    PLOT_PRESERVE = "A"  # 剧情保留重写
    PLOT_ADJUST = "B"  # 剧情调整重写
    FULL_RECREATE = "C"  # 完全重新创作
    REFERENCE_BASED = "D"  # 参考原稿创作


class ModificationStrategy(Enum):
    """修改策略"""

    EXACT_ONLY = "A"  # 只改指定的
    RELATED_TOO = "B"  # 连带调整相关
    AI_JUDGED = "C"  # AI判断范围


class ConflictSeverity(Enum):
    """冲突严重程度"""

    HIGH = "high"  # 必须解决
    MEDIUM = "medium"  # 建议解决
    LOW = "low"  # 可选解决


# ==================== 意图识别 ====================


@dataclass
class IntentResult:
    """意图识别结果"""

    is_rewrite: bool  # 是否是重写
    modification_level: ModificationLevel  # 修改层级
    rewrite_mode: Optional[RewriteMode] = None  # 重写模式
    confidence: float = 0.0  # 置信度
    routing: str = ""  # 路由目标
    target_chapter: Optional[str] = None  # 目标章节
    keywords: List[str] = field(default_factory=list)  # 关键词


# ==================== 反馈解析 ====================


@dataclass
class FeedbackLocation:
    """反馈定位"""

    paragraph: int  # 段落号
    sentence: int  # 句子号
    text: str  # 原文片段


@dataclass
class ParsedFeedback:
    """解析后的反馈"""

    satisfied_parts: List[str] = field(default_factory=list)  # 满意的部分
    unsatisfied_parts: List[str] = field(default_factory=list)  # 不满意的部分
    locations: List[FeedbackLocation] = field(default_factory=list)  # 定位信息
    related_dimensions: List[str] = field(default_factory=list)  # 关联的评估维度


# ==================== 满意度分离 ====================


@dataclass
class ContentSection:
    """内容片段"""

    start: int  # 起始位置
    end: int  # 结束位置
    text: str  # 内容
    status: str  # protected / modifiable


@dataclass
class ContentMask:
    """内容掩码"""

    protected: List[ContentSection] = field(default_factory=list)  # 保护的部分
    modifiable: List[ContentSection] = field(default_factory=list)  # 可修改的部分
    influence_range: Dict[str, Any] = field(default_factory=dict)  # 影响范围


# ==================== 智能修改 ====================


@dataclass
class ModificationResult:
    """修改结果"""

    modified_content: str  # 修改后内容
    changed_parts: List[Dict[str, Any]] = field(default_factory=list)  # 变更部分
    tracking_updates: Dict[str, Any] = field(default_factory=dict)  # 追踪更新
    influence_report: str = ""  # 影响报告


# ==================== 重写处理 ====================


@dataclass
class PlotFramework:
    """剧情框架"""

    scenes: List[Dict[str, Any]] = field(default_factory=list)  # 场景列表
    events: List[Dict[str, Any]] = field(default_factory=list)  # 事件序列
    foreshadows: List[Dict[str, Any]] = field(default_factory=list)  # 伏笔设置
    character_states: Dict[str, Any] = field(default_factory=dict)  # 角色状态


# ==================== 追踪同步 ====================


@dataclass
class TrackingUpdate:
    """追踪更新"""

    hook_ledger: Dict[str, Any] = field(default_factory=dict)
    timeline_tracking: Dict[str, Any] = field(default_factory=dict)
    information_boundary: Dict[str, Any] = field(default_factory=dict)
    payoff_tracking: Dict[str, Any] = field(default_factory=dict)
    manual_confirm_needed: List[str] = field(default_factory=list)


# ==================== 影响范围分析 ====================


@dataclass
class InfluenceReport:
    """影响范围报告"""

    current_chapter: List[str] = field(default_factory=list)  # 当前章节影响
    tracking_files: List[str] = field(default_factory=list)  # 追踪文件影响
    future_chapters: List[str] = field(default_factory=list)  # 后续章节影响
    global_settings: List[str] = field(default_factory=list)  # 全书设定影响
    severity: str = "LOW"  # LOW / MEDIUM / HIGH


# ==================== 冲突检测 ====================


@dataclass
class Conflict:
    """冲突检测结果"""

    type: str  # 冲突类型
    severity: ConflictSeverity  # 严重程度
    dimension_a: str  # 维度A
    dimension_b: str  # 维度B
    content_a: str  # 内容A
    content_b: str  # 内容B
    suggestion: str = ""  # 建议解决方案


# ==================== 迭代安全 ====================


@dataclass
class SafetyCheck:
    """安全检查结果"""

    can_continue: bool  # 是否可以继续
    reason: str = ""  # 原因
    recommendation: str = ""  # 建议
