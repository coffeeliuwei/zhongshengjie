# -*- coding: utf-8 -*-
"""
冲突检测器 - 检测多作家输出之间的冲突
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .types import Conflict, ConflictSeverity


class ConflictDetector:
    """冲突检测器"""

    # 记忆相关关键词
    MEMORY_KEYWORDS = {
        "forget": ["遗忘", "忘记", "不记得", "失去记忆", "记忆消失"],
        "remember": ["记住", "记得", "铭记", "牢记", "不忘"],
    }

    # 时间关键词
    TIME_KEYWORDS = ["先", "后", "然后", "接着", "最后", "当", "正在", "已经", "还没"]

    def detect_all(
        self, worldview: Dict[str, Any], plot: Dict[str, Any], character: Dict[str, Any]
    ) -> List[Conflict]:
        """
        检测所有冲突

        Args:
            worldview: 世界观约束（苍澜输出）
            plot: 剧情框架（玄一输出）
            character: 人物状态（墨言输出）

        Returns:
            冲突列表
        """
        conflicts = []

        # 1. 记忆逻辑冲突
        conflicts.extend(self.detect_memory_conflicts(worldview, character))

        # 2. 伏笔与人物状态冲突
        conflicts.extend(self.detect_foreshadow_conflicts(plot, character))

        # 3. 时间线冲突
        conflicts.extend(self.detect_timeline_conflicts(worldview, plot))

        # 4. 设定一致性冲突
        conflicts.extend(self.detect_setting_conflicts(worldview, plot, character))

        return conflicts

    def detect_memory_conflicts(
        self, worldview: Dict[str, Any], character: Dict[str, Any]
    ) -> List[Conflict]:
        """
        检测记忆逻辑冲突

        示例冲突：
        - 苍澜：血脉代价是"遗忘母亲的名字"
        - 墨言：人物要"记住母亲的每一句话"
        """
        conflicts = []

        worldview_text = str(worldview)
        character_text = str(character)

        # 检测遗忘内容
        forget_content = self._extract_memory_content(worldview_text, "forget")
        remember_content = self._extract_memory_content(character_text, "remember")

        # 检测冲突
        for forget_item in forget_content:
            for remember_item in remember_content:
                # 如果遗忘和记住的内容有重叠
                if self._is_memory_conflict(forget_item, remember_item):
                    conflicts.append(
                        Conflict(
                            type="记忆逻辑冲突",
                            severity=ConflictSeverity.HIGH,
                            dimension_a="世界观约束",
                            dimension_b="人物状态",
                            content_a=f"遗忘{forget_item}",
                            content_b=f"记住{remember_item}",
                            suggestion=f"建议统一：遗忘{forget_item}的细节，但保留情感核心",
                        )
                    )

        return conflicts

    def detect_foreshadow_conflicts(
        self, plot: Dict[str, Any], character: Dict[str, Any]
    ) -> List[Conflict]:
        """
        检测伏笔与人物状态的匹配

        示例冲突：
        - 玄一：伏笔是"母亲临死说出秘密"
        - 墨言：人物状态是"崩溃无意识"
        """
        conflicts = []

        foreshadows = plot.get("伏笔", [])
        character_state = character.get("心理状态", {})

        for foreshadow in foreshadows:
            foreshadow_text = str(foreshadow)

            # 检测人物是否处于能感知伏笔的状态
            if "无意识" in str(character_state) or "昏迷" in str(character_state):
                if "说出" in foreshadow_text or "看到" in foreshadow_text:
                    conflicts.append(
                        Conflict(
                            type="伏笔状态不匹配",
                            severity=ConflictSeverity.MEDIUM,
                            dimension_a="剧情框架",
                            dimension_b="人物状态",
                            content_a=f"伏笔：{foreshadow_text}",
                            content_b=f"人物状态：{character_state}",
                            suggestion="建议：人物无意识时，伏笔改为'道具传递'或'旁人见证'",
                        )
                    )

        return conflicts

    def detect_timeline_conflicts(
        self, worldview: Dict[str, Any], plot: Dict[str, Any]
    ) -> List[Conflict]:
        """
        检测时间线冲突

        示例冲突：
        - 苍澜：血脉觉醒后才能使用血脉力量
        - 玄一：在觉醒前就使用了血脉力量
        """
        conflicts = []

        worldview_text = str(worldview)
        plot_text = str(plot)

        # 检测因果顺序问题
        # 示例：觉醒前的血脉使用
        if "血脉" in worldview_text and "血脉" in plot_text:
            # 提取觉醒触发条件
            trigger_match = re.search(
                r"觉醒.*?触发[^：]*[：:]\s*([^，。]+)", worldview_text
            )

            if trigger_match:
                trigger = trigger_match.group(1)

                # 检查是否有觉醒前的血脉使用
                usage_before = self._check_usage_before_trigger(
                    plot_text, trigger, "血脉"
                )

                if usage_before:
                    conflicts.append(
                        Conflict(
                            type="时间线冲突",
                            severity=ConflictSeverity.HIGH,
                            dimension_a="世界观约束",
                            dimension_b="剧情框架",
                            content_a=f"觉醒触发条件：{trigger}",
                            content_b=f"觉醒前使用了血脉力量",
                            suggestion="建议：调整剧情顺序，确保血脉使用在觉醒之后",
                        )
                    )

        return conflicts

    def detect_setting_conflicts(
        self, worldview: Dict[str, Any], plot: Dict[str, Any], character: Dict[str, Any]
    ) -> List[Conflict]:
        """
        检测设定一致性

        示例冲突：
        - 苍澜：血脉-天裂的力量上限是X
        - 玄一/墨言：人物表现超出上限
        """
        conflicts = []

        worldview_text = str(worldview)
        plot_text = str(plot)
        character_text = str(character)

        # 检测力量等级一致性
        if "力量" in worldview_text or "能力" in worldview_text:
            # 提取力量限制
            limit_match = re.search(
                r"(力量|能力)[^。]*上限[^。]*[：:]\s*([^。]+)", worldview_text
            )

            if limit_match:
                limit = limit_match.group(2)

                # 检查是否有超出限制的表现
                overpower_keywords = ["超越极限", "突破上限", "不可思议的力量"]

                for keyword in overpower_keywords:
                    if keyword in plot_text or keyword in character_text:
                        conflicts.append(
                            Conflict(
                                type="设定不一致",
                                severity=ConflictSeverity.MEDIUM,
                                dimension_a="世界观约束",
                                dimension_b="剧情/人物",
                                content_a=f"力量上限：{limit}",
                                content_b=f"表现：{keyword}",
                                suggestion="建议：修改表现使其符合设定，或为突破设定提供合理理由",
                            )
                        )

        return conflicts

    def _extract_memory_content(self, text: str, memory_type: str) -> List[str]:
        """提取记忆相关内容"""
        contents = []
        keywords = self.MEMORY_KEYWORDS.get(memory_type, [])

        for keyword in keywords:
            # 匹配"遗忘/记住 + 内容"的模式
            pattern = rf"{keyword}[^，。]*([父母亲人物名字事件真相]+)"
            matches = re.findall(pattern, text)
            contents.extend(matches)

        return contents

    def _is_memory_conflict(self, forget_item: str, remember_item: str) -> bool:
        """判断是否存在记忆冲突"""
        # 简化判断：如果内容相似度超过阈值
        if not forget_item or not remember_item:
            return False

        # 检查关键词重叠
        forget_words = set(forget_item)
        remember_words = set(remember_item)

        overlap = forget_words & remember_words
        if len(overlap) >= min(len(forget_words), len(remember_words)) * 0.5:
            return True

        return False

    def _check_usage_before_trigger(
        self, text: str, trigger: str, ability: str
    ) -> bool:
        """检查是否在触发前使用了能力"""
        # 找到触发位置
        trigger_pos = text.find(trigger)
        if trigger_pos == -1:
            return False

        # 找到能力使用位置
        ability_pos = text.find(ability)
        if ability_pos == -1:
            return False

        # 如果能力使用在触发之前
        return ability_pos < trigger_pos


def detect_conflicts(
    worldview: Dict[str, Any], plot: Dict[str, Any], character: Dict[str, Any]
) -> List[Conflict]:
    """
    检测冲突（便捷函数）

    Args:
        worldview: 世界观约束
        plot: 剧情框架
        character: 人物状态

    Returns:
        冲突列表
    """
    detector = ConflictDetector()
    return detector.detect_all(worldview, plot, character)
