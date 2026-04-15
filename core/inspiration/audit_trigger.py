# core/inspiration/audit_trigger.py
"""审计触发器

计数器驱动的两类审计：
  - 鉴赏退化审计：每 N 次鉴赏后检查点火点质量 + 基准选择率
  - 推翻审计：累计 M 次推翻事件后提示系统性偏差

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §9.1（触发 3/触发 4）、§10.3
"""

from typing import Dict, Any, List, Optional

from core.inspiration.escalation_dialogue import (
    format_appraisal_audit,
    format_overturn_audit,
)

# 点火点中的笼统词，出现则视为退化信号
_VAGUE_WORDS = ["节奏", "画面", "鲜明", "流畅", "生动", "饱满", "整体", "氛围"]


class AuditTrigger:
    """审计触发器

    Usage:
        trigger = AuditTrigger()

        # 每次鉴赏后调用
        report = trigger.record_appraisal(appraisal_result_dict)
        if report:
            present_to_author(report)  # 非 None 表示触发审计

        # 每次推翻事件后调用
        report = trigger.record_overturn()
        if report:
            present_to_author(report)
    """

    def __init__(
        self,
        appraisal_interval: int = 10,
        overturn_threshold: int = 10,
    ):
        """
        Args:
            appraisal_interval: 每多少次鉴赏触发一次退化审计（默认 10）
            overturn_threshold: 累计多少次推翻触发推翻审计（默认 10）
        """
        self._appraisal_interval = appraisal_interval
        self._overturn_threshold = overturn_threshold

        self._appraisal_log: List[Dict[str, Any]] = []
        self._overturn_count: int = 0

    def record_appraisal(self, result: Dict[str, Any]) -> Optional[str]:
        """记录一次鉴赏结果

        Args:
            result: 鉴赏结果字典，应含：
                - selected_id (str): 被选中的变体 ID，或 None
                - ignition_point (str | None): 点火句
                - used_constraint_id (str | None): 选中变体的约束 ID（None 表示基准）

        Returns:
            审计报告文本（需呈现给作者），或 None（未到触发阈值）
        """
        self._appraisal_log.append(result)

        if len(self._appraisal_log) >= self._appraisal_interval:
            report = self._run_appraisal_audit()
            self._appraisal_log = []
            return report

        return None

    def record_overturn(self) -> Optional[str]:
        """记录一次推翻事件

        Returns:
            推翻审计报告文本（需呈现给作者），或 None（未到触发阈值）
        """
        self._overturn_count += 1

        if self._overturn_count >= self._overturn_threshold:
            report = format_overturn_audit(overturn_count=self._overturn_count)
            self._overturn_count = 0
            return report

        return None

    def _run_appraisal_audit(self) -> str:
        """分析当前批次鉴赏日志，生成退化审计报告"""
        count = len(self._appraisal_log)

        vague_count = sum(
            1
            for r in self._appraisal_log
            if r.get("ignition_point")
            and any(w in r["ignition_point"] for w in _VAGUE_WORDS)
        )

        # 基准变体：used_constraint_id 为 None 且有 selected_id
        baseline_win_count = sum(
            1
            for r in self._appraisal_log
            if r.get("selected_id") and r.get("used_constraint_id") is None
        )

        return format_appraisal_audit(
            appraisal_count=count,
            vague_count=vague_count,
            baseline_win_count=baseline_win_count,
        )
