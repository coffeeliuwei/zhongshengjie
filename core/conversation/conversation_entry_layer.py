#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对话入口层
==========

所有用户输入的第一站，整合所有对话处理组件。

核心功能：
- 意图识别
- 意图澄清
- 状态检查
- 数据更新
- 错误恢复
- 进度反馈

参考：统一提炼引擎重构方案.md 第10.2节
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .intent_classifier import IntentClassifier, IntentResult, IntentCategory
from .intent_clarifier import IntentClarifier, ClarificationQuestion
from .workflow_state_checker import WorkflowStateChecker, WorkflowState
from .progress_reporter import ProgressReporter
from .undo_manager import UndoManager, OperationType
from .missing_info_detector import MissingInfoDetector, MissingInfo
from .data_extractor import ConversationDataExtractor, ExtractionResult
from .intent_router import IntentRouter
from core.feedback.feedback_collector import FeedbackCollector
from core.parsing.chapter_outline_parser import ChapterOutlineParser


class ProcessingStatus(Enum):
    """处理状态"""

    SUCCESS = "success"
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_CONFIRMATION = "needs_confirmation"
    MISSING_INFO = "missing_info"
    PENDING_WORKFLOW = "pending_workflow"
    ERROR = "error"
    FAILED = "failed"


@dataclass
class ProcessingResult:
    """处理结果"""

    status: ProcessingStatus
    intent: str
    entities: Dict[str, str]
    message: str
    clarification: Optional[ClarificationQuestion] = None
    missing_info: Optional[List[MissingInfo]] = None
    pending_workflow: Optional[WorkflowState] = None
    extraction_result: Optional[ExtractionResult] = None
    data: Optional[Dict[str, Any]] = None


class ConversationEntryLayer:
    """对话入口层"""

    def __init__(
        self, project_root: Optional[str] = None, session_id: Optional[str] = None
    ):
        """
        初始化对话入口层

        Args:
            project_root: 项目根目录路径
            session_id: 会话ID
        """
        self.project_root = (
            Path(project_root) if project_root else self._detect_project_root()
        )
        self.session_id = (
            session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        # 初始化所有组件
        self.intent_classifier = IntentClassifier()
        self.intent_clarifier = IntentClarifier()
        self.workflow_checker = WorkflowStateChecker(str(self.project_root))
        self.progress_reporter = ProgressReporter()
        self.undo_manager = UndoManager(str(self.project_root))
        self.missing_detector = MissingInfoDetector(str(self.project_root))
        self.data_extractor = ConversationDataExtractor(str(self.project_root))

        # FeedbackCollector 初始化
        self.feedback_collector = FeedbackCollector()
        self._feedback_history_path = (
            self.project_root / "data" / "feedback_history.json"
        )
        self.feedback_collector.load_history(self._feedback_history_path)
        self._pending_feedback_context: Optional[Dict[str, Any]] = None

        # 内部状态
        self._current_workflow: Optional[WorkflowState] = None
        self._last_intent: Optional[str] = None
        self._conversation_context: List[Dict[str, Any]] = []

        # 复用同一 IntentRouter 实例以保持多轮对话状态
        self._intent_router = IntentRouter()

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        current = Path(__file__).resolve()
        markers = ["README.md", "config.example.json", "tools", "设定"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                return parent

        return Path.cwd()

    def process_input(self, user_input: str) -> ProcessingResult:
        """
        处理用户输入（主入口）

        Args:
            user_input: 用户输入文本

        Returns:
            ProcessingResult
        """
        # 记录对话上下文
        self._conversation_context.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": "user",
                "content": user_input,
            }
        )

        # 1. 意图识别
        intent_result = self.intent_classifier.classify(user_input)

        # 1.5 FeedbackCollector 旁路（静默，不阻断主流程）
        self._pending_feedback_context = None
        if FeedbackCollector.has_feedback_signal(user_input):
            try:
                fb = self.feedback_collector.collect_from_explicit(user_input)
                if fb.get("feedback_type") != "general_feedback":
                    self._pending_feedback_context = {
                        "feedback_type": fb["feedback_type"],
                        "issue": fb.get("issue", ""),
                        "severity": fb.get("severity", "medium"),
                        "scene_type": fb.get("scene_type"),
                    }
                    self.feedback_collector.save_history(self._feedback_history_path)
            except Exception:
                pass  # 旁路失败不影响主流程

        # 2. 检查是否需要澄清
        if self.intent_clarifier.needs_clarification(intent_result):
            clarification = self.intent_clarifier.generate_clarification(
                intent_result, user_input
            )
            return ProcessingResult(
                status=ProcessingStatus.NEEDS_CLARIFICATION,
                intent=intent_result.intent,
                entities=intent_result.entities,
                message=clarification.question_text,
                clarification=clarification,
            )

        # 3. 特殊意图处理
        special_result = self._handle_special_intents(intent_result, user_input)
        if special_result:
            return special_result

        # 4. 检查是否有未完成的工作流
        pending = self.workflow_checker.check_pending_workflow(self.session_id)
        if pending and intent_result.intent not in [
            "continue_workflow",
            "start_chapter",
        ]:
            # 有未完成的工作流，询问用户
            return ProcessingResult(
                status=ProcessingStatus.PENDING_WORKFLOW,
                intent=intent_result.intent,
                entities=intent_result.entities,
                message=self.workflow_checker.generate_resume_prompt(pending),
                pending_workflow=pending,
            )

        # 5. 检测缺失信息
        missing = self.missing_detector.detect_missing(
            intent_result.intent,
            intent_result.entities,
            self.session_id,
        )

        critical_missing = [m for m in missing if m.severity.value == "critical"]
        if critical_missing:
            return ProcessingResult(
                status=ProcessingStatus.MISSING_INFO,
                intent=intent_result.intent,
                entities=intent_result.entities,
                message=self.missing_detector.generate_missing_prompt(critical_missing),
                missing_info=critical_missing,
            )

        # 6. 执行操作
        return self._execute_intent(intent_result, user_input, missing)

    def _handle_special_intents(
        self, intent_result: IntentResult, user_input: str
    ) -> Optional[ProcessingResult]:
        """
        处理特殊意图

        Args:
            intent_result: 意图识别结果
            user_input: 用户输入

        Returns:
            处理结果，或None表示不是特殊意图
        """
        intent = intent_result.intent

        # 撤销操作
        if intent == "undo_last":
            undone = self.undo_manager.undo_last()
            if undone:
                return ProcessingResult(
                    status=ProcessingStatus.SUCCESS,
                    intent="undo_last",
                    entities={},
                    message=f"已撤销：{undone.description}\n\n"
                    + self.undo_manager.generate_undo_prompt(),
                )
            else:
                return ProcessingResult(
                    status=ProcessingStatus.ERROR,
                    intent="undo_last",
                    entities={},
                    message="没有可撤销的操作。",
                )

        # 查询进度
        elif intent == "query_progress":
            if self._current_workflow:
                return ProcessingResult(
                    status=ProcessingStatus.SUCCESS,
                    intent="query_progress",
                    entities={},
                    message=self.progress_reporter.generate_full_report(
                        {
                            "current_phase": self._current_workflow.current_phase,
                            "total_phases": self._current_workflow.total_phases,
                            "workflow_type": self._current_workflow.workflow_type,
                            "chapter": self._current_workflow.chapter,
                            "scene_progress": self._current_workflow.scene_progress,
                            "started_at": self._current_workflow.started_at,
                        }
                    ),
                )
            else:
                return ProcessingResult(
                    status=ProcessingStatus.SUCCESS,
                    intent="query_progress",
                    entities={},
                    message="当前没有进行中的工作流。",
                )

        # 继续工作流
        elif intent == "continue_workflow":
            pending = self.workflow_checker.check_pending_workflow(self.session_id)
            if pending:
                self._current_workflow = pending
                return ProcessingResult(
                    status=ProcessingStatus.SUCCESS,
                    intent="continue_workflow",
                    entities={},
                    message=f"继续工作流：{pending.workflow_type}\n"
                    + self.progress_reporter.generate_quick_status(
                        {
                            "current_phase": pending.current_phase,
                            "total_phases": pending.total_phases,
                            "workflow_type": pending.workflow_type,
                        }
                    ),
                    pending_workflow=pending,
                )
            else:
                return ProcessingResult(
                    status=ProcessingStatus.ERROR,
                    intent="continue_workflow",
                    entities={},
                    message="没有未完成的工作流。",
                )

        # 查看历史
        elif intent == "view_history":
            history = self.undo_manager.get_history(10)
            if history:
                history_text = "最近的操作：\n"
                for op in history[-5:]:
                    icon = "✅" if op.undone else "📝"
                    history_text += f"{icon} {op.description}\n"
                return ProcessingResult(
                    status=ProcessingStatus.SUCCESS,
                    intent="view_history",
                    entities={},
                    message=history_text,
                )
            else:
                return ProcessingResult(
                    status=ProcessingStatus.SUCCESS,
                    intent="view_history",
                    entities={},
                    message="暂无操作历史。",
                )

        return None

    def _execute_intent(
        self,
        intent_result: IntentResult,
        user_input: str,
        missing_info: List[MissingInfo],
    ) -> ProcessingResult:
        """
        执行意图

        Args:
            intent_result: 意图识别结果
            user_input: 用户输入
            missing_info: 缺失信息

        Returns:
            ProcessingResult
        """
        intent = intent_result.intent
        entities = intent_result.entities

        # 记录意图
        self._last_intent = intent

        # 根据意图类型执行不同操作
        if intent_result.category == IntentCategory.SETTING_UPDATE:
            # 设定更新意图
            return self._inject_feedback_context(
                self._execute_setting_update(intent_result, user_input)
            )

        elif intent_result.category == IntentCategory.WORKFLOW_CONTROL:
            # 工作流控制意图
            return self._inject_feedback_context(
                self._execute_workflow_control(intent_result, user_input)
            )

        elif intent_result.category == IntentCategory.QUERY:
            # 查询意图
            return self._inject_feedback_context(
                self._execute_query(intent_result, user_input)
            )

        elif intent_result.category == IntentCategory.TRACKING:
            # 追踪系统意图
            return self._inject_feedback_context(
                self._execute_tracking(intent_result, user_input)
            )

        else:
            # 通过路由器处理未覆盖类别（FEEDBACK、MANAGEMENT、TECHNIQUE、EVALUATION 等）
            routing_result = self._intent_router.route(
                intent=intent,
                entities=entities,
                user_input=user_input,
            )
            return self._inject_feedback_context(
                ProcessingResult(
                    status=ProcessingStatus.SUCCESS
                    if routing_result.success
                    else ProcessingStatus.FAILED,
                    intent=intent,
                    entities=entities,
                    message=routing_result.message,
                    data=routing_result.data,
                )
            )

    def _execute_setting_update(
        self, intent_result: IntentResult, user_input: str
    ) -> ProcessingResult:
        """执行设定更新"""
        # 记录操作
        self.undo_manager.record_operation(
            operation_type=OperationType.SETTING_ADD,
            description=f"更新设定：{intent_result.intent}",
            data=intent_result.entities,
        )

        # 调用数据提取器
        extraction_result = self.data_extractor.extract_and_update(
            user_input, intent_result
        )

        if extraction_result.status == "updated":
            # 记录对话上下文
            self._conversation_context.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "system",
                    "content": extraction_result.message,
                }
            )

            return ProcessingResult(
                status=ProcessingStatus.SUCCESS,
                intent=intent_result.intent,
                entities=intent_result.entities,
                message=extraction_result.message,
                extraction_result=extraction_result,
                data=extraction_result.data,
            )

        else:
            return ProcessingResult(
                status=ProcessingStatus.ERROR,
                intent=intent_result.intent,
                entities=intent_result.entities,
                message=f"更新失败：{extraction_result.message}",
            )

    def _execute_workflow_control(
        self, intent_result: IntentResult, user_input: str
    ) -> ProcessingResult:
        """执行工作流控制"""
        intent = intent_result.intent

        if intent == "start_chapter":
            # 创建新工作流
            chapter = intent_result.entities.get("chapter", "1")
            chapter_num = self._parse_chapter_number(chapter)

            # ---- 大纲注入（I17）----
            outline_context = ""
            outline_dir = self.project_root / "章节大纲"
            if outline_dir.exists():
                parser = ChapterOutlineParser()
                outline_file = parser.find_outline_file(chapter_num, outline_dir)
                if outline_file is not None:
                    outline_data = parser.parse_file(outline_file)
                    if outline_data:
                        outline_context = outline_data.get("summary", "")
            # ---- 大纲注入结束 ----

            workflow = self.workflow_checker.create_workflow(
                session_id=self.session_id,
                workflow_type="chapter_creation",
                chapter=chapter_num,
                metadata={"chapter_outline": outline_context}
                if outline_context
                else None,
            )

            self._current_workflow = workflow

            return ProcessingResult(
                status=ProcessingStatus.SUCCESS,
                intent=intent,
                entities=intent_result.entities,
                message=f"开始创作第{chapter_num}章\n"
                + self.progress_reporter.generate_quick_status(
                    {
                        "current_phase": 0,
                        "total_phases": workflow.total_phases,
                        "workflow_type": "chapter_creation",
                    }
                ),
                pending_workflow=workflow,
            )

        elif intent == "pause_workflow":
            # 暂停工作流
            if self._current_workflow:
                self.workflow_checker.save_state(
                    self.session_id,
                    {
                        "workflow_id": self._current_workflow.workflow_id,
                        "workflow_type": self._current_workflow.workflow_type,
                        "current_phase": self._current_workflow.current_phase,
                        "total_phases": self._current_workflow.total_phases,
                        "chapter": self._current_workflow.chapter,
                    },
                )

                return ProcessingResult(
                    status=ProcessingStatus.SUCCESS,
                    intent=intent,
                    entities={},
                    message="工作流已暂停，可以随时继续。",
                )
            else:
                return ProcessingResult(
                    status=ProcessingStatus.ERROR,
                    intent=intent,
                    entities={},
                    message="当前没有进行中的工作流。",
                )

        return ProcessingResult(
            status=ProcessingStatus.SUCCESS,
            intent=intent,
            entities=intent_result.entities,
            message=f"工作流控制：{intent}",
        )

    def _execute_query(
        self, intent_result: IntentResult, user_input: str
    ) -> ProcessingResult:
        """执行查询"""
        # 这里简化实现，实际需要调用检索系统
        return ProcessingResult(
            status=ProcessingStatus.SUCCESS,
            intent=intent_result.intent,
            entities=intent_result.entities,
            message=f"查询意图：{intent_result.intent}\n实体：{intent_result.entities}",
            data={"query": intent_result.entities},
        )

    def _execute_tracking(
        self, intent_result: IntentResult, user_input: str
    ) -> ProcessingResult:
        """执行追踪系统操作"""
        # 追踪系统操作类似设定更新
        return self._execute_setting_update(intent_result, user_input)

    def _parse_chapter_number(self, chapter_str: str) -> int:
        """
        解析章节号

        Args:
            chapter_str: 章节字符串（如 "一", "1", "第一章"）

        Returns:
            章节数字
        """
        # 中文数字映射
        chinese_numbers = {
            "零": 0,
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
            "百": 100,
        }

        # 尝试直接解析数字
        try:
            return int(chapter_str)
        except ValueError:
            pass

        # 尝试从字符串中提取数字
        import re

        numbers = re.findall(r"\d+", chapter_str)
        if numbers:
            return int(numbers[0])

        # 尝试解析中文数字
        for cn, num in chinese_numbers.items():
            if cn in chapter_str:
                return num

        # 默认返回1
        return 1

    def update_workflow_progress(
        self, phase: int, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        更新工作流进度

        Args:
            phase: 当前阶段
            metadata: 附加元数据
        """
        if self._current_workflow:
            self.workflow_checker.update_phase(self.session_id, phase, metadata)
            self._current_workflow.current_phase = phase

    def complete_workflow(self) -> None:
        """完成当前工作流"""
        if self._current_workflow:
            self.workflow_checker.mark_completed(self.session_id)
            self._current_workflow = None

    def get_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取对话上下文

        Args:
            limit: 返回数量

        Returns:
            对话上下文列表
        """
        return self._conversation_context[-limit:]

    def clear_context(self) -> None:
        """清空对话上下文"""
        self._conversation_context = []

    def _inject_feedback_context(self, result: ProcessingResult) -> ProcessingResult:
        """将旁路收集的反馈上下文注入 ProcessingResult.data"""
        if self._pending_feedback_context is None:
            return result
        if result.data is None:
            result.data = {}
        result.data["feedback_context"] = self._pending_feedback_context
        self._pending_feedback_context = None
        return result


# 测试代码
if __name__ == "__main__":
    entry_layer = ConversationEntryLayer()

    print("=" * 60)
    print("对话入口层测试")
    print("=" * 60)

    # 测试输入
    test_inputs = [
        "血牙有个新能力叫血脉守护",
        "加个新势力叫暗影宗",
        "撤销",
        "进度",
    ]

    for input_text in test_inputs:
        result = entry_layer.process_input(input_text)

        print(f"\n输入: {input_text}")
        print(f"状态: {result.status.value}")
        print(f"意图: {result.intent}")
        print(f"消息: {result.message}")
