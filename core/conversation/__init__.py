#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
会话数据提取模块
===============

提供对话式工作流的数据提取和更新功能。

核心组件：
- IntentClassifier: 意图分类器，识别用户意图
- IntentClarifier: 意图澄清器，处理模糊表达
- ConversationDataExtractor: 数据提取器，提取结构化数据
- FileUpdater: 文件更新器，更新设定文件
- WorkflowStateChecker: 工作流状态检查器，检查未完成的工作流
- ProgressReporter: 进度报告器，生成进度反馈
- UndoManager: 撤销管理器，管理操作历史
- MissingInfoDetector: 缺失信息检测器，主动发现信息缺失
- ConversationEntryLayer: 对话入口层，所有用户输入的第一站

使用方式：
    from core.conversation import ConversationEntryLayer

    entry_layer = ConversationEntryLayer()
    result = entry_layer.process_input("血牙有个新能力叫血脉守护")

参考：统一提炼引擎重构方案.md 第九章
"""

from typing import Dict, Any, Optional

from .intent_classifier import (
    IntentClassifier,
    IntentCategory,
    IntentResult,
)
from .intent_clarifier import (
    IntentClarifier,
    ClarificationQuestion,
    ClarificationType,
)
from .data_extractor import (
    ConversationDataExtractor,
    ExtractionResult,
)
from .file_updater import (
    FileUpdater,
    UpdateResult,
)
from .workflow_state_checker import (
    WorkflowStateChecker,
    WorkflowState,
)
from .progress_reporter import (
    ProgressReporter,
    ProgressInfo,
)
from .undo_manager import (
    UndoManager,
    OperationType,
    OperationRecord,
)
from .missing_info_detector import (
    MissingInfoDetector,
    MissingInfo,
    SeverityLevel,
)
from .conversation_entry_layer import (
    ConversationEntryLayer,
    ProcessingResult,
    ProcessingStatus,
)

__all__ = [
    # 意图分类
    "IntentClassifier",
    "IntentCategory",
    "IntentResult",
    # 意图澄清
    "IntentClarifier",
    "ClarificationQuestion",
    "ClarificationType",
    # 数据提取
    "ConversationDataExtractor",
    "ExtractionResult",
    # 文件更新
    "FileUpdater",
    "UpdateResult",
    # 工作流状态
    "WorkflowStateChecker",
    "WorkflowState",
    # 进度报告
    "ProgressReporter",
    "ProgressInfo",
    # 撤销管理
    "UndoManager",
    "OperationType",
    "OperationRecord",
    # 缺失信息检测
    "MissingInfoDetector",
    "MissingInfo",
    "SeverityLevel",
    # 对话入口层
    "ConversationEntryLayer",
    "ProcessingResult",
    "ProcessingStatus",
]

__version__ = "2.0.0"


def process_user_input(
    user_input: str, project_root: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理用户输入的便捷函数

    Args:
        user_input: 用户输入的文本
        project_root: 项目根目录（可选）

    Returns:
        处理结果字典
    """
    # 使用对话入口层处理
    entry_layer = ConversationEntryLayer(project_root)
    result = entry_layer.process_input(user_input)

    return {
        "status": result.status.value,
        "intent": result.intent,
        "entities": result.entities,
        "message": result.message,
        "needs_clarification": result.clarification is not None,
        "missing_info": [m.message for m in result.missing_info]
        if result.missing_info
        else [],
        "data": result.data,
    }
