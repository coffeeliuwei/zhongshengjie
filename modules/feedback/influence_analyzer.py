# -*- coding: utf-8 -*-
"""
影响范围分析器 - 分析修改的影响范围
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field

from .types import ModificationLevel, InfluenceReport


class InfluenceAnalyzer:
    """影响范围分析器"""

    # 影响范围规则
    IMPACT_RULES = {
        ModificationLevel.WORD_POLISH: {
            "current_chapter": ["表达风格"],
            "tracking_files": [],
            "future_chapters": [],
            "global_settings": [],
            "severity": "LOW",
        },
        ModificationLevel.CONTENT_TWEAK: {
            "current_chapter": ["段落结构", "细节描述"],
            "tracking_files": ["可能影响伏笔"],
            "future_chapters": [],
            "global_settings": [],
            "severity": "LOW",
        },
        ModificationLevel.PLOT_CHANGE: {
            "current_chapter": ["剧情走向", "人物行为", "事件结果"],
            "tracking_files": ["hook_ledger", "payoff_tracking", "timeline_tracking"],
            "future_chapters": ["伏笔呼应", "人物发展", "事件影响"],
            "global_settings": [],
            "severity": "MEDIUM",
        },
        ModificationLevel.SETTING_CHANGE: {
            "current_chapter": ["设定表现", "人物行为", "世界观描述"],
            "tracking_files": [
                "hook_ledger",
                "payoff_tracking",
                "timeline_tracking",
                "information_boundary",
            ],
            "future_chapters": ["所有涉及该设定的章节"],
            "global_settings": ["人物设定", "势力设定", "力量体系"],
            "severity": "HIGH",
        },
    }

    # 关键实体类型
    ENTITY_TYPES = {
        "character": ["主角", "配角", "反派", "路人"],
        "faction": ["势力", "组织", "门派", "国家"],
        "power": ["血脉", "力量", "功法", "技能"],
        "item": ["道具", "武器", "宝物"],
    }

    def analyze(
        self,
        modification_level: ModificationLevel,
        content_changes: Dict[str, Any] = None,
    ) -> InfluenceReport:
        """
        分析修改影响范围

        Args:
            modification_level: 修改层级
            content_changes: 内容变化详情（可选）

        Returns:
            InfluenceReport: 影响范围报告
        """
        # 获取基础影响规则
        base_impact = self.IMPACT_RULES.get(
            modification_level, self.IMPACT_RULES[ModificationLevel.WORD_POLISH]
        )

        # 如果有内容变化，进行细化分析
        if content_changes:
            refined_impact = self._refine_impact(base_impact, content_changes)
        else:
            refined_impact = base_impact

        # 检测涉及的实体
        entities = self._detect_entities(content_changes) if content_changes else {}

        # 根据涉及实体调整影响范围
        if entities:
            refined_impact = self._adjust_by_entities(refined_impact, entities)

        return InfluenceReport(
            current_chapter=refined_impact.get("current_chapter", []),
            tracking_files=refined_impact.get("tracking_files", []),
            future_chapters=refined_impact.get("future_chapters", []),
            global_settings=refined_impact.get("global_settings", []),
            severity=refined_impact.get("severity", "LOW"),
        )

    def _refine_impact(
        self, base_impact: Dict[str, Any], content_changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """细化影响范围"""
        refined = base_impact.copy()

        changes = content_changes.get("changes", [])

        # 分析变化类型
        for change in changes:
            change_type = change.get("type", "")
            modified_text = change.get("modified", "")

            # 检测是否有伏笔相关
            if "伏笔" in modified_text or "暗示" in modified_text:
                if "tracking_files" not in refined:
                    refined["tracking_files"] = []
                if "hook_ledger" not in refined["tracking_files"]:
                    refined["tracking_files"].append("hook_ledger")

            # 检测是否有代价相关
            if "代价" in modified_text or "牺牲" in modified_text:
                if "tracking_files" not in refined:
                    refined["tracking_files"] = []
                if "payoff_tracking" not in refined["tracking_files"]:
                    refined["tracking_files"].append("payoff_tracking")

        return refined

    def _detect_entities(self, content_changes: Dict[str, Any]) -> Dict[str, List[str]]:
        """检测涉及的实体"""
        entities = {"characters": [], "factions": [], "powers": [], "items": []}

        if not content_changes:
            return entities

        # 简单的关键词检测
        # 实际应用中可以使用 NER 或知识库检索
        text = content_changes.get("full_text", "")

        # 检测人物（简化版，实际应使用知识库）
        character_keywords = ["主角", "血牙", "林远", "母亲"]
        for keyword in character_keywords:
            if keyword in text:
                entities["characters"].append(keyword)

        # 检测势力
        faction_keywords = ["佣兵联盟", "天道", "血脉者"]
        for keyword in faction_keywords:
            if keyword in text:
                entities["factions"].append(keyword)

        # 检测力量体系
        power_keywords = ["血脉", "天裂", "觉醒"]
        for keyword in power_keywords:
            if keyword in text:
                entities["powers"].append(keyword)

        return entities

    def _adjust_by_entities(
        self, impact: Dict[str, Any], entities: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """根据涉及实体调整影响范围"""
        adjusted = impact.copy()

        # 如果涉及势力，影响范围升级
        if entities.get("factions"):
            if adjusted["severity"] == "LOW":
                adjusted["severity"] = "MEDIUM"
            adjusted["global_settings"].append("势力相关设定")

        # 如果涉及力量体系，影响范围升级
        if entities.get("powers"):
            if adjusted["severity"] == "MEDIUM":
                adjusted["severity"] = "HIGH"
            adjusted["global_settings"].append("力量体系相关设定")

        return adjusted

    def generate_report_text(self, report: InfluenceReport) -> str:
        """生成人类可读的影响报告"""
        lines = ["【修改影响范围报告】\n"]

        # 当前章节影响
        if report.current_chapter:
            lines.append("📄 当前章节影响：")
            for item in report.current_chapter:
                lines.append(f"  - {item}")
            lines.append("")

        # 追踪文件影响
        if report.tracking_files:
            lines.append("📋 追踪文件影响：")
            for item in report.tracking_files:
                lines.append(f"  - {item}")
            lines.append("")

        # 后续章节影响
        if report.future_chapters:
            lines.append("📖 后续章节影响：")
            for item in report.future_chapters:
                lines.append(f"  - {item}")
            lines.append("")

        # 全书设定影响
        if report.global_settings:
            lines.append("🌍 全书设定影响：")
            for item in report.global_settings:
                lines.append(f"  - {item}")
            lines.append("")

        # 严重程度
        severity_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
        lines.append(
            f"影响等级：{severity_emoji.get(report.severity, '⚪')} {report.severity}"
        )

        return "\n".join(lines)


def analyze_influence(
    modification_level: ModificationLevel, content_changes: Dict[str, Any] = None
) -> InfluenceReport:
    """
    分析修改影响范围（便捷函数）

    Args:
        modification_level: 修改层级
        content_changes: 内容变化详情

    Returns:
        影响范围报告
    """
    analyzer = InfluenceAnalyzer()
    return analyzer.analyze(modification_level, content_changes)
