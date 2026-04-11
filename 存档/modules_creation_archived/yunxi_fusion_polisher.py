"""
云溪融合润色合并器

功能：
1. 将 Phase 1.6（融合）和 Phase 3（润色）合并为一次调用
2. 减少调用次数（2次 → 1次）
3. 共享上下文，风格更统一
4. 节省时间（约30秒）

设计原因：
- 云溪同时负责融合（Phase 1.6）和润色（Phase 3）
- 两个职责是连贯的（融合→润色）
- 合并调用可提高效率和一致性
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class FusionPolishMode(Enum):
    """融合润色模式"""

    FULL = "full"  # 完整模式：融合 + 润色
    FUSION_ONLY = "fusion_only"  # 仅融合
    POLISH_ONLY = "polish_only"  # 仅润色
    AUTO = "auto"  # 自动判断


@dataclass
class FusionPolishInput:
    """融合润色输入"""

    # Phase 1 输出
    phase1_worldview: Dict[str, Any]
    phase1_plot: Dict[str, Any]
    phase1_character: Dict[str, Any]

    # 冲突信息
    conflicts: List[Dict[str, Any]]
    fusion_strategy: str  # "auto" / "yunxi" / "user"

    # Phase 2 输出（核心创作内容）
    phase2_content: Optional[str] = None

    # 模式
    mode: FusionPolishMode = FusionPolishMode.AUTO

    # 上下文
    scene_type: str = ""
    chapter_name: str = ""
    target_word_count: int = 3000


@dataclass
class FusionPolishOutput:
    """融合润色输出"""

    # 融合结果
    unified_constraints: Dict[str, Any]
    fusion_notes: List[str]

    # 润色结果
    polished_content: str
    word_count: int

    # 统计
    time_saved_seconds: int
    calls_saved: int


class YunxiFusionPolisher:
    """
    云溪融合润色合并器

    一次调用完成融合 + 润色。
    """

    # 时间节省估算
    TIME_SAVED_PER_CALL = 30  # 秒
    CALLS_SAVED = 1  # 节省调用次数

    def __init__(self):
        self.stats = {
            "total_calls": 0,
            "full_mode": 0,
            "fusion_only_mode": 0,
            "polish_only_mode": 0,
            "total_time_saved": 0,
        }

    def execute(self, input_data: FusionPolishInput) -> FusionPolishOutput:
        """
        执行融合润色

        Args:
            input_data: 融合润色输入

        Returns:
            融合润色输出
        """
        self.stats["total_calls"] += 1

        # 确定模式
        mode = self._determine_mode(input_data)

        # Step 1: 融合（如果需要）
        unified_constraints = {}
        fusion_notes = []

        if mode in [FusionPolishMode.FULL, FusionPolishMode.FUSION_ONLY]:
            unified_constraints, fusion_notes = self._fuse(
                input_data.phase1_worldview,
                input_data.phase1_plot,
                input_data.phase1_character,
                input_data.conflicts,
            )
            self.stats["full_mode"] += 1 if mode == FusionPolishMode.FULL else 0
            self.stats["fusion_only_mode"] += (
                1 if mode == FusionPolishMode.FUSION_ONLY else 0
            )
        else:
            unified_constraints = {
                "世界观约束": input_data.phase1_worldview,
                "剧情框架": input_data.phase1_plot,
                "人物状态": input_data.phase1_character,
            }
            self.stats["polish_only_mode"] += 1

        # Step 2: 润色（如果需要）
        polished_content = ""
        word_count = 0

        if mode in [FusionPolishMode.FULL, FusionPolishMode.POLISH_ONLY]:
            if input_data.phase2_content:
                polished_content = self._polish(
                    input_data.phase2_content,
                    unified_constraints,
                    input_data.scene_type,
                )
                word_count = len(polished_content)
            else:
                polished_content = "[无核心内容需要润色]"
        else:
            # 仅融合模式，不润色
            polished_content = "[仅融合模式，请调用主作家创作后润色]"

        # 统计
        time_saved = self.TIME_SAVED_PER_CALL if mode == FusionPolishMode.FULL else 0
        self.stats["total_time_saved"] += time_saved

        return FusionPolishOutput(
            unified_constraints=unified_constraints,
            fusion_notes=fusion_notes,
            polished_content=polished_content,
            word_count=word_count,
            time_saved_seconds=time_saved,
            calls_saved=self.CALLS_SAVED if mode == FusionPolishMode.FULL else 0,
        )

    def _determine_mode(self, input_data: FusionPolishInput) -> FusionPolishMode:
        """确定执行模式"""
        if input_data.mode != FusionPolishMode.AUTO:
            return input_data.mode

        # 自动判断
        has_conflicts = len(input_data.conflicts) > 0
        has_content = (
            input_data.phase2_content is not None and len(input_data.phase2_content) > 0
        )

        if has_conflicts and has_content:
            return FusionPolishMode.FULL
        elif has_conflicts and not has_content:
            return FusionPolishMode.FUSION_ONLY
        elif not has_conflicts and has_content:
            return FusionPolishMode.POLISH_ONLY
        else:
            return FusionPolishMode.FUSION_ONLY

    def _fuse(
        self,
        worldview: Dict[str, Any],
        plot: Dict[str, Any],
        character: Dict[str, Any],
        conflicts: List[Dict[str, Any]],
    ) -> tuple[Dict[str, Any], List[str]]:
        """
        执行融合

        Returns:
            (统一约束, 融合说明)
        """
        # 使用自动融合逻辑
        from .creation_mode import CreationMode, FusionStrategy

        mode = CreationMode()

        # 构建 Phase 1 输出
        phase1_outputs = {
            "世界观约束": worldview,
            "剧情框架": plot,
            "人物状态": character,
        }

        # 过滤无效输出
        valid_outputs = mode.filter_valid_outputs(phase1_outputs)

        # 如果没有冲突或只有一个有效维度，直接返回
        if len(conflicts) == 0 or len(valid_outputs) <= 1:
            return valid_outputs, ["无冲突，直接合并"]

        # 自动融合
        from .conflict_detector import Conflict

        conflict_objects = []
        for c in conflicts:
            from .conflict_detector import ConflictSeverity

            conflict_objects.append(
                Conflict(
                    type=c.get("type", ""),
                    severity=ConflictSeverity(c.get("severity", "medium")),
                    dimension_a=c.get("dimension_a", ""),
                    dimension_b=c.get("dimension_b", ""),
                    content_a=c.get("content_a", ""),
                    content_b=c.get("content_b", ""),
                    suggestion=c.get("suggestion", ""),
                )
            )

        fusion_result = mode.auto_fuse(conflict_objects)

        return fusion_result, fusion_result.get("融合说明", ["自动融合完成"])

    def _polish(
        self,
        content: str,
        unified_constraints: Dict[str, Any],
        scene_type: str,
    ) -> str:
        """
        执行润色

        注意：实际润色由云溪 skill 执行，这里只是框架
        """
        # 润色指令（传递给云溪 skill）
        polish_instruction = f"""
【润色任务】

场景类型: {scene_type}

设定约束:
{self._format_constraints(unified_constraints)}

原始内容:
{content[:500]}...

润色要求:
1. 统一风格，消除拼合痕迹
2. 氛围渲染，增强意境
3. 禁止项检测（AI味表达、时间连接词等）
4. 保持原有内容的核心不变
"""
        # 实际调用由 writer_executor 完成
        # 这里返回占位符
        return f"[云溪润色后]\n{content}"

    def _format_constraints(self, constraints: Dict[str, Any]) -> str:
        """格式化约束为文本"""
        lines = []
        for key, value in constraints.items():
            if isinstance(value, dict):
                lines.append(f"- {key}: {value}")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "总调用次数": self.stats["total_calls"],
            "完整模式": self.stats["full_mode"],
            "仅融合模式": self.stats["fusion_only_mode"],
            "仅润色模式": self.stats["polish_only_mode"],
            "累计节省时间": f"{self.stats['total_time_saved']}秒",
        }


# 便捷函数
def fuse_and_polish(
    phase1_worldview: Dict[str, Any],
    phase1_plot: Dict[str, Any],
    phase1_character: Dict[str, Any],
    conflicts: List[Dict[str, Any]],
    phase2_content: Optional[str] = None,
    mode: FusionPolishMode = FusionPolishMode.AUTO,
) -> FusionPolishOutput:
    """
    便捷函数：融合 + 润色

    Args:
        phase1_worldview: Phase 1 世界观输出
        phase1_plot: Phase 1 剧情输出
        phase1_character: Phase 1 人物输出
        conflicts: 冲突列表
        phase2_content: Phase 2 核心内容
        mode: 执行模式

    Returns:
        融合润色输出
    """
    polisher = YunxiFusionPolisher()

    input_data = FusionPolishInput(
        phase1_worldview=phase1_worldview,
        phase1_plot=phase1_plot,
        phase1_character=phase1_character,
        conflicts=conflicts,
        fusion_strategy="auto",
        phase2_content=phase2_content,
        mode=mode,
    )

    return polisher.execute(input_data)


# 使用示例
if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    # 示例：融合 + 润色
    print("=" * 60)
    print("示例：云溪融合润色合并")
    print("=" * 60)

    # Phase 1 输出
    worldview = {
        "血脉觉醒": {"触发": "目睹母亲被杀", "代价": "遗忘名字"},
    }
    plot = {
        "伏笔": ["母亲临死说出秘密"],
        "结构": "铺垫→高潮→收尾",
    }
    character = {
        "情感重点": "记住母亲的话",
    }

    # 冲突
    conflicts = [
        {
            "type": "记忆逻辑冲突",
            "severity": "high",
            "dimension_a": "世界观约束",
            "dimension_b": "人物状态",
            "content_a": "遗忘名字",
            "content_b": "记住母亲的话",
            "suggestion": "遗忘名字，保留嘱托",
        }
    ]

    # Phase 2 内容
    phase2_content = "这是一段战斗场景的核心内容..." * 100

    # 执行融合润色
    result = fuse_and_polish(
        phase1_worldview=worldview,
        phase1_plot=plot,
        phase1_character=character,
        conflicts=conflicts,
        phase2_content=phase2_content,
        mode=FusionPolishMode.FULL,
    )

    print(f"\n融合说明: {result.fusion_notes}")
    print(f"润色字数: {result.word_count}")
    print(f"节省时间: {result.time_saved_seconds}秒")
    print(f"节省调用: {result.calls_saved}次")
