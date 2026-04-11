"""
一致性检测模块

功能：
1. 检测多作家并行输出的冲突
2. 识别逻辑矛盾、设定不一致、时间线冲突
3. 生成冲突清单和解决建议
4. 支持不同严重程度的冲突分级

使用场景：
- Phase 1.5：检测苍澜、玄一、墨言并行输出的冲突
- 为 Phase 1.6 融合调整提供依据
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json


class ConflictSeverity(Enum):
    """冲突严重程度"""

    HIGH = "high"  # 必须解决，否则影响剧情逻辑
    MEDIUM = "medium"  # 建议解决，可能导致不协调
    LOW = "low"  # 可选解决，轻微不一致


class ConflictType(Enum):
    """冲突类型"""

    MEMORY_LOGIC = "记忆逻辑冲突"  # 遗忘 vs 记住
    FORESHADOW_MISMATCH = "伏笔不匹配"  # 伏笔与人物状态不匹配
    TIMELINE = "时间线冲突"  # 时间线矛盾
    SETTING = "设定不一致"  # 设定冲突
    CHARACTER = "人物矛盾"  # 人物行为矛盾
    TONE = "基调冲突"  # 情感基调不一致


@dataclass
class Conflict:
    """
    冲突检测结果

    Attributes:
        type: 冲突类型
        severity: 严重程度
        dimension_a: 维度A（如"世界观约束"）
        dimension_b: 维度B（如"人物状态"）
        content_a: 内容A
        content_b: 内容B
        suggestion: 解决建议
        source_writers: 来源作家
    """

    type: str
    severity: ConflictSeverity
    dimension_a: str
    dimension_b: str
    content_a: str
    content_b: str
    suggestion: str
    source_writers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type,
            "severity": self.severity.value,
            "dimension_a": self.dimension_a,
            "dimension_b": self.dimension_b,
            "content_a": self.content_a,
            "content_b": self.content_b,
            "suggestion": self.suggestion,
            "source_writers": self.source_writers,
        }


class ConflictDetector:
    """
    一致性检测器

    用法：
        detector = ConflictDetector()
        conflicts = detector.detect(phase1_outputs)

        for conflict in conflicts:
            print(f"[{conflict.severity.value}] {conflict.type}")
            print(f"  {conflict.suggestion}")
    """

    def __init__(self):
        # 冲突检测规则
        self.rules = [
            self._detect_memory_conflicts,
            self._detect_foreshadow_conflicts,
            self._detect_timeline_conflicts,
            self._detect_setting_conflicts,
            self._detect_character_conflicts,
            self._detect_tone_conflicts,
        ]

    def detect(self, outputs: Dict[str, Any]) -> List[Conflict]:
        """
        检测所有冲突

        Args:
            outputs: {
                "世界观约束": {...},  # 来自苍澜
                "剧情框架": {...},    # 来自玄一
                "人物状态": {...}     # 来自墨言
            }

        Returns:
            冲突列表
        """
        all_conflicts = []

        for rule in self.rules:
            try:
                conflicts = rule(outputs)
                all_conflicts.extend(conflicts)
            except Exception as e:
                print(f"[冲突检测] 规则执行失败: {e}")

        # 按严重程度排序
        all_conflicts.sort(
            key=lambda c: {"high": 0, "medium": 1, "low": 2}.get(c.severity.value, 3)
        )

        return all_conflicts

    def _detect_memory_conflicts(self, outputs: Dict[str, Any]) -> List[Conflict]:
        """检测遗忘vs记住的冲突"""
        conflicts = []

        worldview = outputs.get("世界观约束", {})
        character = outputs.get("人物状态", {})

        worldview_text = self._flatten_dict(worldview)
        character_text = self._flatten_dict(character)

        # 检测遗忘
        forget_patterns = [
            r"遗忘[的]?([^，。！？\n]+)",
            r"忘记[的]?([^，。！？\n]+)",
            r"失去[的]?([^，。！？\n]+)记忆",
        ]

        forget_contents = []
        for pattern in forget_patterns:
            matches = re.findall(pattern, worldview_text)
            forget_contents.extend(matches)

        # 检测记住
        remember_patterns = [
            r"记住[的]?([^，。！？\n]+)",
            r"记得[的]?([^，。！？\n]+)",
            r"保留[的]?([^，。！？\n]+)记忆",
        ]

        remember_contents = []
        for pattern in remember_patterns:
            matches = re.findall(pattern, character_text)
            remember_contents.extend(matches)

        # 检测冲突
        for forget in forget_contents:
            for remember in remember_contents:
                # 检查是否有重叠
                if self._has_overlap(forget, remember):
                    conflicts.append(
                        Conflict(
                            type=ConflictType.MEMORY_LOGIC.value,
                            severity=ConflictSeverity.HIGH,
                            dimension_a="世界观约束",
                            dimension_b="人物状态",
                            content_a=f"遗忘{forget.strip()}",
                            content_b=f"记住{remember.strip()}",
                            suggestion=f"建议统一：血脉代价遗忘{forget.strip()}，但保留{remember.strip()}的核心部分",
                            source_writers=["苍澜", "墨言"],
                        )
                    )

        return conflicts

    def _detect_foreshadow_conflicts(self, outputs: Dict[str, Any]) -> List[Conflict]:
        """检测伏笔与人物状态不匹配"""
        conflicts = []

        plot = outputs.get("剧情框架", {})
        character = outputs.get("人物状态", {})

        foreshadows = plot.get("伏笔", [])
        if isinstance(foreshadows, str):
            foreshadows = [foreshadows]

        character_state = character.get("心理状态", {})
        emotional_focus = character.get("情感重点", "")

        # 检查伏笔是否与人物状态匹配
        for foreshadow in foreshadows:
            if isinstance(foreshadow, dict):
                content = foreshadow.get("内容", "")
            else:
                content = str(foreshadow)

            # 示例规则：如果伏笔涉及"说出秘密"，但人物状态是"崩溃"
            if "说出" in content or "说出秘密" in content:
                if "崩溃" in str(character_state) or "无意识" in str(character_state):
                    conflicts.append(
                        Conflict(
                            type=ConflictType.FORESHADOW_MISMATCH.value,
                            severity=ConflictSeverity.MEDIUM,
                            dimension_a="剧情框架",
                            dimension_b="人物状态",
                            content_a=f"伏笔：{content}",
                            content_b=f"人物状态：崩溃/无意识",
                            suggestion="建议修改伏笔：人物崩溃时无法说出秘密，改为'给道具'或'眼神暗示'",
                            source_writers=["玄一", "墨言"],
                        )
                    )

        return conflicts

    def _detect_timeline_conflicts(self, outputs: Dict[str, Any]) -> List[Conflict]:
        """检测时间线冲突"""
        conflicts = []

        worldview = outputs.get("世界观约束", {})
        plot = outputs.get("剧情框架", {})

        # 提取时间相关内容
        worldview_text = self._flatten_dict(worldview)
        plot_text = self._flatten_dict(plot)

        # 检测觉醒时机与剧情结构是否匹配
        if "血脉觉醒" in worldview_text:
            # 检查剧情结构中觉醒的位置
            if "结构" in plot:
                structure = plot.get("结构", "")
                # 示例：如果觉醒是"高潮"后，但世界观说觉醒需要"极端仇恨"
                # 这里可以添加更复杂的检测逻辑

        return conflicts

    def _detect_setting_conflicts(self, outputs: Dict[str, Any]) -> List[Conflict]:
        """检测设定不一致"""
        conflicts = []

        worldview = outputs.get("世界观约束", {})
        plot = outputs.get("剧情框架", {})
        character = outputs.get("人物状态", {})

        # 检测血脉设定与人物能力是否一致
        if "血脉" in str(worldview):
            bloodline = worldview.get("血脉觉醒", {})
            trigger = bloodline.get("触发", "")

            # 检查人物状态中是否有匹配的触发条件
            character_text = self._flatten_dict(character)
            if trigger and trigger not in character_text:
                # 可能不一致，但不一定是冲突
                pass

        return conflicts

    def _detect_character_conflicts(self, outputs: Dict[str, Any]) -> List[Conflict]:
        """检测人物行为矛盾"""
        conflicts = []

        character = outputs.get("人物状态", {})
        plot = outputs.get("剧情框架", {})

        # 检测人物行为与剧情框架是否一致
        character_text = self._flatten_dict(character)
        plot_text = self._flatten_dict(plot)

        # 示例：检测"仇恨"vs"原谅"矛盾
        if "仇恨" in character_text and "原谅" in plot_text:
            conflicts.append(
                Conflict(
                    type=ConflictType.CHARACTER.value,
                    severity=ConflictSeverity.HIGH,
                    dimension_a="人物状态",
                    dimension_b="剧情框架",
                    content_a="人物状态：仇恨",
                    content_b="剧情框架：涉及原谅",
                    suggestion="建议检查：仇恨状态下人物是否会原谅？需要铺垫和解过程",
                    source_writers=["墨言", "玄一"],
                )
            )

        return conflicts

    def _detect_tone_conflicts(self, outputs: Dict[str, Any]) -> List[Conflict]:
        """检测情感基调冲突"""
        conflicts = []

        character = outputs.get("人物状态", {})
        plot = outputs.get("剧情框架", {})

        # 提取情感基调
        character_tone = character.get("情感基调", "")
        plot_tone = plot.get("场景基调", "")

        # 对立的情感基调
        opposite_tones = [
            ("悲壮", "轻松"),
            ("仇恨", "温馨"),
            ("紧张", "舒缓"),
            ("绝望", "希望"),
        ]

        for tone_a, tone_b in opposite_tones:
            if tone_a in character_tone and tone_b in plot_tone:
                conflicts.append(
                    Conflict(
                        type=ConflictType.TONE.value,
                        severity=ConflictSeverity.LOW,
                        dimension_a="人物状态",
                        dimension_b="剧情框架",
                        content_a=f"情感基调：{tone_a}",
                        content_b=f"场景基调：{tone_b}",
                        suggestion=f"建议检查：{tone_a}与{tone_b}是否需要过渡段落",
                        source_writers=["墨言", "玄一"],
                    )
                )

        return conflicts

    def _flatten_dict(self, d: Dict[str, Any], prefix: str = "") -> str:
        """将字典扁平化为字符串"""
        items = []
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.append(self._flatten_dict(v, key))
            elif isinstance(v, list):
                items.append(f"{key}: {', '.join(str(i) for i in v)}")
            else:
                items.append(f"{key}: {v}")
        return "\n".join(items)

    def _has_overlap(self, text1: str, text2: str) -> bool:
        """检查两个文本是否有语义重叠"""
        # 简单的关键词匹配
        keywords1 = set(re.findall(r"[\u4e00-\u9fa5]{2,}", text1))
        keywords2 = set(re.findall(r"[\u4e00-\u9fa5]{2,}", text2))

        # 如果有交集，认为有重叠
        return bool(keywords1 & keywords2)


class ConflictFusionGuide:
    """
    冲突融合指南生成器

    为 Phase 1.6 主作家融合提供指导
    """

    @staticmethod
    def generate_fusion_guide(conflicts: List[Conflict]) -> str:
        """
        生成融合指南

        Args:
            conflicts: 冲突列表

        Returns:
            融合指南文本
        """
        if not conflicts:
            return "无冲突，可以直接融合。"

        guide = "【融合指南】\n\n"

        # 按严重程度分组
        high_conflicts = [c for c in conflicts if c.severity == ConflictSeverity.HIGH]
        medium_conflicts = [
            c for c in conflicts if c.severity == ConflictSeverity.MEDIUM
        ]
        low_conflicts = [c for c in conflicts if c.severity == ConflictSeverity.LOW]

        if high_conflicts:
            guide += "🔴 必须解决（HIGH）：\n"
            for i, c in enumerate(high_conflicts, 1):
                guide += f"\n{i}. {c.type}\n"
                guide += f"   冲突：{c.dimension_a}({c.content_a}) vs {c.dimension_b}({c.content_b})\n"
                guide += f"   建议：{c.suggestion}\n"

        if medium_conflicts:
            guide += "\n🟡 建议解决（MEDIUM）：\n"
            for i, c in enumerate(medium_conflicts, 1):
                guide += f"\n{i}. {c.type}\n"
                guide += f"   冲突：{c.dimension_a} vs {c.dimension_b}\n"
                guide += f"   建议：{c.suggestion}\n"

        if low_conflicts:
            guide += "\n🟢 可选解决（LOW）：\n"
            for i, c in enumerate(low_conflicts, 1):
                guide += f"\n{i}. {c.type}\n"
                guide += f"   建议：{c.suggestion}\n"

        guide += "\n【融合要求】\n"
        guide += "- 必须解决所有 HIGH 级别冲突\n"
        guide += "- 建议解决 MEDIUM 级别冲突\n"
        guide += "- 输出统一的设定约束包\n"
        guide += "- 注明每个冲突的解决决策和理由\n"

        return guide


# 便捷函数
def detect_conflicts(outputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    便捷函数：检测冲突并返回字典列表

    Args:
        outputs: Phase 1 输出

    Returns:
        冲突字典列表
    """
    detector = ConflictDetector()
    conflicts = detector.detect(outputs)
    return [c.to_dict() for c in conflicts]


def generate_fusion_guide(conflicts: List[Dict[str, Any]]) -> str:
    """
    便捷函数：生成融合指南

    Args:
        conflicts: 冲突字典列表

    Returns:
        融合指南文本
    """
    # 转换回 Conflict 对象
    conflict_objects = []
    for c in conflicts:
        conflict_objects.append(
            Conflict(
                type=c["type"],
                severity=ConflictSeverity(c["severity"]),
                dimension_a=c["dimension_a"],
                dimension_b=c["dimension_b"],
                content_a=c["content_a"],
                content_b=c["content_b"],
                suggestion=c["suggestion"],
                source_writers=c.get("source_writers", []),
            )
        )

    return ConflictFusionGuide.generate_fusion_guide(conflict_objects)


# 使用示例
if __name__ == "__main__":
    # 示例：检测冲突
    phase1_outputs = {
        "世界观约束": {
            "血脉觉醒": {"触发": "目睹母亲被肢解", "代价": "遗忘母亲的名字，只记得仇恨"}
        },
        "剧情框架": {"结构": "铺垫→悬念→高潮→收尾", "伏笔": ["母亲临死说出一个秘密"]},
        "人物状态": {
            "情感重点": "记住母亲的每一句话",
            "心理状态": "恐惧→震惊→崩溃→仇恨",
        },
    }

    detector = ConflictDetector()
    conflicts = detector.detect(phase1_outputs)

    print("检测到的冲突：")
    for c in conflicts:
        print(f"\n[{c.severity.value}] {c.type}")
        print(f"  维度A: {c.dimension_a} - {c.content_a}")
        print(f"  维度B: {c.dimension_b} - {c.content_b}")
        print(f"  建议: {c.suggestion}")

    print("\n" + "=" * 60)
    print(ConflictFusionGuide.generate_fusion_guide(conflicts))
