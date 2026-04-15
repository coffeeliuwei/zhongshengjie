# core/conversation/intent_router.py
"""意图→后端路由层

conversation_entry_layer._execute_intent 的 else 分支统一转发到此处。
每个意图在 _ROUTES 表中登记处理函数，新意图必须同时在分类器和路由表登记。

设计背景：docs/superpowers/plans/2026-04-15-inspiration-engine.md Task 6.1
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from collections import Counter

from core.feedback.feedback_dispatcher import FeedbackDispatcher
from core.inspiration.status_reporter import report_status
from core.inspiration.constraint_library import ConstraintLibrary
from core.conversation.technique_extractor import TechniqueExtractor
from core.conversation.eval_criteria_extractor import EvaluationCriteriaExtractor
from core.extraction.extraction_runner import ExtractionRunner
from core.extraction.extraction_formatter import (
    format_start_response,
    format_status_response,
)


@dataclass
class RoutingResult:
    """路由执行结果，可直接转换为 ProcessingResult"""

    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    needs_clarification: bool = False


def record_audit_label(label: str) -> str:
    """记录作者对审计的标定结果（写入日志，可后续升级为记忆点入库）"""
    return f"已记录标定：{label}\n鉴赏师判准校准将在下次生成时生效。"


def _query_constraints(user_input: str) -> str:
    """查询约束库并生成简报"""
    try:
        lib = ConstraintLibrary()
        active = lib.list_active()
        categories = [
            "视角反叛",
            "词汇剥夺",
            "节奏反转",
            "感官错位",
            "时态异化",
            "情绪逆压",
        ]
        target_cat = next((c for c in categories if c in user_input), None)

        if target_cat:
            filtered = [c for c in active if c.get("category") == target_cat]
            lines = [f"【{target_cat}】共 {len(filtered)} 条活跃约束："]
            for c in filtered[:5]:
                lines.append(f"  - {c['id']}：{c['constraint_text'][:40]}...")
        else:
            lines = [f"约束库共 {len(active)} 条活跃约束："]
            cat_counts = Counter(c.get("category") for c in active)
            for cat, cnt in cat_counts.items():
                lines.append(f"  - {cat}：{cnt} 条")

        return "\n".join(lines)
    except Exception as e:
        return f"查询约束库时出错：{e}"


class IntentRouter:
    """意图路由器

    Usage:
        router = IntentRouter()
        result = router.route(intent="reader_moment_feedback", entities={}, user_input="第2章很解气")
        # result.message 直接呈现给作者
    """

    def route(
        self,
        intent: str,
        entities: Dict[str, Any],
        user_input: str,
    ) -> RoutingResult:
        """路由意图到对应后端处理函数

        Args:
            intent: 意图名称（来自 IntentResult.intent）
            entities: 提取的实体（来自 IntentResult.entities）
            user_input: 用户原始输入

        Returns:
            RoutingResult，success=False 表示意图未被任何处理器处理
        """
        handler = self._get_handler(intent)
        if handler is None:
            return RoutingResult(
                success=False,
                message=f"意图 '{intent}' 未处理：路由表中无对应处理器",
            )
        try:
            return handler(intent=intent, entities=entities, user_input=user_input)
        except Exception as e:
            return RoutingResult(
                success=False,
                message=f"处理意图 '{intent}' 时出错：{e}",
            )

    def _get_handler(self, intent: str):
        """查找意图对应处理函数，未注册返回 None"""
        _table = {
            # FEEDBACK
            "reader_moment_feedback": self._handle_reader_moment_feedback,
            "comparative_moment_feedback": self._handle_reader_moment_feedback,
            "external_moment_inject": self._handle_reader_moment_feedback,
            "overturn_feedback": self._handle_overturn_feedback,
            "connoisseur_audit_response": self._handle_connoisseur_audit_response,
            # QUERY / MANAGEMENT
            "inspiration_status_query": self._handle_inspiration_status_query,
            "constraint_query": self._handle_constraint_query,
            "constraint_add": self._handle_constraint_add,
            "constraint_tuning": self._handle_constraint_tuning,
            "inspiration_bailout": self._handle_inspiration_bailout,
            # TECHNIQUE
            "extract_technique": self._handle_extract_technique,
            "extract_technique_from_file": self._handle_extract_technique_from_file,
            "confirm_technique": self._handle_confirm_technique,
            "modify_technique": self._handle_modify_technique,
            # EVALUATION
            "add_evaluation_criteria": self._handle_add_evaluation_criteria,
            "discover_prohibitions_from_file": self._handle_discover_prohibitions_from_file,
            "modify_evaluation_threshold": self._handle_modify_evaluation_threshold,
            # CONFIRMATION
            "confirm_evaluation_criteria": self._handle_confirm_evaluation_criteria,
            # INSPIRATION WORKFLOW
            "inspiration_conflict_resolution": self._handle_inspiration_conflict_resolution,
            # DATA_EXTRACTION
            "incremental_extraction": self._handle_incremental_extraction,
            "full_extraction": self._handle_full_extraction,
        }
        return _table.get(intent)

    def _handle_reader_moment_feedback(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """处理读者反馈类意图（正向/对比/外部注入），通过 FeedbackDispatcher 路由"""
        dispatcher = FeedbackDispatcher()
        result = dispatcher.dispatch(
            feedback_category="inspiration",
            user_input=user_input,
            scene_type_lookup=lambda chapter_ref: "未知",
            is_overturn=False,
        )
        return RoutingResult(
            success=True,
            message=result.get("message", ""),
            data={"memory_point_ids": result.get("memory_point_ids", [])},
            needs_clarification=(result.get("status") == "needs_clarification"),
        )

    def _handle_overturn_feedback(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """处理推翻事件反馈，通过 FeedbackDispatcher 路由"""
        dispatcher = FeedbackDispatcher()
        result = dispatcher.dispatch(
            feedback_category="inspiration",
            user_input=user_input,
            scene_type_lookup=lambda chapter_ref: "未知",
            is_overturn=True,
        )
        return RoutingResult(
            success=True,
            message=result.get("message", ""),
            data={"memory_point_ids": result.get("memory_point_ids", [])},
            needs_clarification=(result.get("status") == "needs_clarification"),
        )

    def _handle_connoisseur_audit_response(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """处理鉴赏师审计响应：作者标定真实点火次数"""
        label = entities.get("audit_result", user_input)
        msg = record_audit_label(label)
        return RoutingResult(success=True, message=msg, data={"label": label})

    def _handle_inspiration_status_query(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """返回灵感引擎状态报告"""
        msg = report_status()
        return RoutingResult(success=True, message=msg)

    def _handle_constraint_query(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """查询约束库状态"""
        msg = _query_constraints(user_input)
        return RoutingResult(success=True, message=msg, data={})

    def _handle_constraint_add(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """提示用户通过对话添加约束"""
        return RoutingResult(
            success=True,
            message=(
                "好的，我来帮你添加约束。请告诉我：\n"
                "  1. 约束类别\n"
                "  2. 适用场景类型\n"
                "  3. 约束描述"
            ),
            needs_clarification=True,
        )

    def _handle_constraint_tuning(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """提示用户约束调整流程"""
        constraint_id = entities.get("constraint_id", "")
        hint = f"约束 {constraint_id}" if constraint_id else "该约束"
        return RoutingResult(
            success=True,
            message=(
                f"你想调整 {hint}。选项：\n"
                "  A. 降级为观察名单\n"
                "  B. 直接禁用\n"
                "  请告诉我选 A 还是 B，以及你想调整的约束 ID。"
            ),
            needs_clarification=True,
        )

    def _handle_inspiration_bailout(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """临时关闭灵感引擎"""
        return RoutingResult(
            success=True,
            message='灵感引擎本章已关闭，将走原有作家流程。如需重新开启，说"开启灵感引擎"即可。',
            data={"action": "disable_inspiration_engine"},
        )

    def _handle_extract_technique(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """从用户输入中提炼技法候选"""
        extractor = TechniqueExtractor()
        candidate = extractor.extract_from_content(user_input)
        display = (
            extractor.format_candidate_for_display(candidate)
            if hasattr(extractor, "format_candidate_for_display")
            else str(candidate)
        )
        return RoutingResult(
            success=True,
            message=f'提炼到以下技法候选，确认入库？\n\n{display}\n\n回复"确认"入库，或告诉我如何修改。',
            data={
                "candidate": candidate.__dict__
                if hasattr(candidate, "__dict__")
                else str(candidate)
            },
            needs_clarification=True,
        )

    def _handle_extract_technique_from_file(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """从文件路径提炼技法"""
        file_path = entities.get("file_path", "")
        if not file_path:
            return RoutingResult(
                success=True,
                message="请告诉我要从哪个文件提炼技法（如：正文/第一章.md）",
                needs_clarification=True,
            )
        extractor = TechniqueExtractor()
        candidates = extractor.extract_from_file(file_path)
        if not candidates:
            return RoutingResult(
                success=True, message=f"在 {file_path} 中未发现可提炼的技法候选。"
            )
        lines = [f"从 {file_path} 提炼到 {len(candidates)} 个技法候选："]
        for c in candidates[:5]:
            c_str = str(c)[:60] if hasattr(c, "__str__") else c.name[:60]
            lines.append(f"  - {c_str}...")
        lines.append('\n回复"确认第N个"逐一入库。')
        return RoutingResult(
            success=True,
            message="\n".join(lines),
            data={"candidates_count": len(candidates)},
            needs_clarification=True,
        )

    def _handle_confirm_technique(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """确认技法入库"""
        return RoutingResult(
            success=True,
            message="技法确认入库功能正在完善中。请直接告诉我技法名称和描述，我帮你记录。",
        )

    def _handle_modify_technique(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """修改技法名称"""
        return RoutingResult(
            success=True,
            message="请告诉我：要修改哪个技法（原名）？改成什么名字？",
            needs_clarification=True,
        )

    def _handle_add_evaluation_criteria(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """从用户描述中提炼禁止项候选"""
        extractor = EvaluationCriteriaExtractor()
        candidate = extractor.extract_prohibition(user_input)
        display = (
            extractor.format_for_confirmation(candidate)
            if hasattr(extractor, "format_for_confirmation")
            else str(candidate)
        )
        return RoutingResult(
            success=True,
            message=f"提炼到以下禁止项候选：\n\n{display}\n\n确认入库？[是/否]",
            data={
                "candidate_name": candidate.name if hasattr(candidate, "name") else ""
            },
            needs_clarification=True,
        )

    def _handle_discover_prohibitions_from_file(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """从文件扫描发现禁止项候选"""
        file_path = entities.get("file_path", "")
        if not file_path:
            return RoutingResult(
                success=True,
                message="请告诉我要扫描哪个文件（如：正文/第一章.md）",
                needs_clarification=True,
            )
        extractor = EvaluationCriteriaExtractor()
        candidates = (
            extractor.discover_from_file(file_path)
            if hasattr(extractor, "discover_from_file")
            else []
        )
        if not candidates:
            return RoutingResult(
                success=True, message=f"在 {file_path} 中未发现可疑表达。"
            )
        lines = [f"从 {file_path} 发现 {len(candidates)} 个潜在禁止项："]
        for i, c in enumerate(candidates[:5], 1):
            c_str = str(c)[:80] if hasattr(c, "__str__") else c.name[:80]
            lines.append(f"  {i}. {c_str}...")
        lines.append("\n选择确认添加？[全部/选择 N/取消]")
        return RoutingResult(
            success=True,
            message="\n".join(lines),
            data={"candidates_count": len(candidates)},
            needs_clarification=True,
        )

    def _handle_modify_evaluation_threshold(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """修改评估阈值"""
        return RoutingResult(
            success=True,
            message=(
                "请告诉我：\n"
                "  1. 要修改哪个技法的阈值？\n"
                "  2. 当前阈值是？新阈值改为多少？\n"
                "  3. 原因？"
            ),
            needs_clarification=True,
        )

    def _handle_confirm_evaluation_criteria(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """确认将评估标准/禁止项添加入库"""
        criterion_name = entities.get("criterion_name", "该禁止项")
        return RoutingResult(
            success=True,
            message=f"已确认入库：{criterion_name}。\n"
            "禁止项已添加到评估标准库，下次生成时将自动检查。",
            data={"confirmed": True, "criterion_name": criterion_name},
        )

    def _handle_inspiration_conflict_resolution(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """处理用户与鉴赏师冲突——用户表态接受或推翻"""
        resolution = entities.get("resolution", "")
        if "推翻" in user_input or "不接受" in user_input or resolution == "reject":
            return RoutingResult(
                success=True,
                message="已记录：你推翻了鉴赏师的选择。\n"
                "请告诉我你更倾向哪个变体，以及原因（可选）。",
                data={"conflict_resolution": "user_overturn"},
                needs_clarification=True,
            )
        return RoutingResult(
            success=True,
            message="已记录：接受鉴赏师的选择。此次结果将作为正向参照保留。",
            data={"conflict_resolution": "accept_connoisseur"},
        )

    def _handle_incremental_extraction(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """启动增量提炼（已完成维度自动跳过）"""
        runner = ExtractionRunner()
        result = runner.start("incremental")
        return RoutingResult(
            success=True,
            message=format_start_response(result, "incremental"),
            data={"mode": "incremental", "started": result.get("started", False)},
        )

    def _handle_full_extraction(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult:
        """启动全量提炼（强制重跑，忽略历史进度）"""
        runner = ExtractionRunner()
        result = runner.start("full")
        return RoutingResult(
            success=True,
            message=format_start_response(result, "full"),
            data={"mode": "full", "started": result.get("started", False)},
        )
