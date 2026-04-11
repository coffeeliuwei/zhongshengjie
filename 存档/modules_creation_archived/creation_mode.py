"""
创作模式定义

功能：
1. 定义单模式流程（并行+智能融合）
2. 实现自动融合逻辑
3. 冲突判断和路由决策
4. 融合效率统计

设计原则：
- 只保留深度模式（并行+智能融合），无快速模式
- 云溪负责融合而非主作家
- 冲突≤2个自动融合，减少作家调用
"""

from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# 导入冲突检测模块
from .conflict_detector import (
    Conflict,
    ConflictSeverity,
    ConflictType,
    ConflictDetector,
)


class FusionStrategy(Enum):
    """融合策略"""

    AUTO = "auto"  # 自动融合（≤2个冲突）
    YUNXI = "yunxi"  # 云溪介入融合（3-5个冲突）
    USER = "user"  # 用户确认（>5个冲突）
    NONE = "none"  # 无冲突，无需融合


@dataclass
class FusionRule:
    """自动融合规则"""

    conflict_type: str
    rule_description: str
    example: str
    priority: str  # "worldview" / "character" / "plot" / "compromise"

    def apply(
        self, content_a: str, content_b: str, dimension_a: str, dimension_b: str
    ) -> Tuple[str, str]:
        """
        应用融合规则

        Returns:
            (融合结果, 融合说明)
        """
        if self.priority == "worldview":
            # 世界观优先
            result = content_a
            note = f"取世界观约束优先（{content_a}）"
        elif self.priority == "character":
            # 人物情感优先
            result = content_b
            note = f"取人物情感优先（{content_b}）"
        elif self.priority == "compromise":
            # 折中融合
            result = self._compromise_fusion(content_a, content_b)
            note = f"折中融合：{result}"
        else:
            # 默认取 A
            result = content_a
            note = f"默认取{dimension_a}"

        return result, note

    def _compromise_fusion(self, content_a: str, content_b: str) -> str:
        """折中融合逻辑"""
        # 记忆逻辑冲突的特殊处理
        if "遗忘" in content_a:
            # 遗忘细节，保留核心
            import re

            forget_match = re.search(r"遗忘[的]?([^，。]+)", content_a)
            if forget_match:
                forget_content = forget_match.group(1).strip()
                # 从 content_b 中提取保留内容
                remember_match = re.search(r"记住[的]?([^，。]+)", content_b)
                if remember_match:
                    remember_content = remember_match.group(1).strip()
                    return f"遗忘{forget_content}，但保留{remember_content}"

        return f"{content_a} + {content_b}"


# 自动融合规则库
AUTO_FUSION_RULES: Dict[str, FusionRule] = {
    ConflictType.MEMORY_LOGIC.value: FusionRule(
        conflict_type="记忆逻辑冲突",
        rule_description="遗忘'名字/细节'，保留'嘱托/核心情感'",
        example="遗忘母亲名字，记住嘱托'活下去'",
        priority="compromise",
    ),
    ConflictType.FORESHADOW_MISMATCH.value: FusionRule(
        conflict_type="伏笔不匹配",
        rule_description="伏笔改为'给道具'而非'对话/说出'",
        example="母亲给匕首，而非说出秘密",
        priority="plot",
    ),
    ConflictType.TIMELINE.value: FusionRule(
        conflict_type="时间线冲突",
        rule_description="事件发生在较早的时间点",
        example="觉醒发生在高潮前而非高潮后",
        priority="worldview",
    ),
    ConflictType.SETTING.value: FusionRule(
        conflict_type="设定不一致",
        rule_description="世界观约束 > 剧情/人物",
        example="血脉代价必须，剧情伏笔调整",
        priority="worldview",
    ),
    ConflictType.CHARACTER.value: FusionRule(
        conflict_type="人物矛盾",
        rule_description="情感/心理状态 > 行为反应",
        example="仇恨状态优先，行为可调整",
        priority="character",
    ),
    ConflictType.TONE.value: FusionRule(
        conflict_type="基调冲突",
        rule_description="添加过渡段落提示",
        example="悲壮→仇恨需要沉淀段落",
        priority="compromise",
    ),
}


@dataclass
class FusionResult:
    """融合结果"""

    strategy: FusionStrategy
    unified_constraints: Dict[str, Any]
    fusion_notes: List[str]
    conflicts_resolved: int
    auto_fused: bool
    yunxi_required: bool
    user_confirm_required: bool
    time_saved_seconds: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CreationMode:
    """
    创作模式：并行+智能融合

    只有深度模式，无快速模式。
    """

    MODE_NAME = "深度模式"
    MODE_DESCRIPTION = "并行生成 + 智能融合，创意独立 + 效率高"

    # 融合触发阈值
    AUTO_FUSION_THRESHOLD = 2  # ≤2个冲突自动融合
    YUNXI_FUSION_THRESHOLD = 5  # 3-5个冲突云溪介入
    # >5个冲突用户确认

    def __init__(self):
        self.detector = ConflictDetector()
        self.stats = {
            "total_scenes": 0,
            "auto_fused": 0,
            "yunxi_fused": 0,
            "user_confirmed": 0,
            "no_conflicts": 0,
            "avg_time_saved": 0,
        }

    def determine_fusion_strategy(self, conflicts: List[Conflict]) -> FusionStrategy:
        """
        根据冲突数量决定融合策略

        Args:
            conflicts: 冲突列表

        Returns:
            融合策略
        """
        num_conflicts = len(conflicts)

        if num_conflicts == 0:
            return FusionStrategy.NONE
        elif num_conflicts <= self.AUTO_FUSION_THRESHOLD:
            return FusionStrategy.AUTO
        elif num_conflicts <= self.YUNXI_FUSION_THRESHOLD:
            return FusionStrategy.YUNXI
        else:
            return FusionStrategy.USER

    def filter_valid_outputs(self, phase1_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        过滤掉"无特殊约束"的维度

        当某个维度输出"无特殊约束"时，不参与冲突检测和融合。

        判断规则：
        1. output.get("内容") == "无特殊约束"
        2. output.get("content") == "无特殊约束"
        3. output 只有"内容"/"说明"等元数据字段，无实际内容

        Args:
            phase1_outputs: Phase 1 的三个作家输出

        Returns:
            有效维度输出
        """
        valid = {}
        invalid_count = 0

        # 实际内容字段名（非元数据字段）
        content_fields = {
            "血脉觉醒",
            "剧情框架",
            "伏笔",
            "结构",
            "情感重点",
            "心理变化",
            "行为反应",
        }

        for dimension, output in phase1_outputs.items():
            # 情况1：明确标记"无特殊约束"
            if (
                output.get("内容") == "无特殊约束"
                or output.get("content") == "无特殊约束"
            ):
                invalid_count += 1
                continue

            # 情况2：空输出
            if not output or output == {}:
                invalid_count += 1
                continue

            # 情况3：只有元数据字段，无实际内容
            output_keys = set(output.keys())
            metadata_keys = {
                "内容",
                "content",
                "说明",
                "note",
                "默认引用",
                "default_ref",
            }

            # 如果输出只有元数据字段，判定为无效
            if output_keys.issubset(metadata_keys):
                invalid_count += 1
                continue

            # 情况4：检查是否有实际内容字段
            has_content = bool(output_keys & content_fields) or any(
                k not in metadata_keys for k in output_keys
            )

            if not has_content:
                invalid_count += 1
                continue

            # 保留有效输出
            valid[dimension] = output

        # 记录过滤统计
        if invalid_count > 0:
            self.stats.setdefault("filtered_outputs", 0)
            self.stats["filtered_outputs"] += invalid_count

        return valid

    def auto_fuse(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """
        自动融合冲突

        Args:
            conflicts: 冲突列表

        Returns:
            统一设定约束包
        """
        fusion_result = {
            "血脉觉醒": {},
            "剧情框架": {},
            "人物状态": {},
            "融合说明": [],
        }

        for conflict in conflicts:
            rule = AUTO_FUSION_RULES.get(conflict.type)

            if rule:
                result, note = rule.apply(
                    conflict.content_a,
                    conflict.content_b,
                    conflict.dimension_a,
                    conflict.dimension_b,
                )

                # 根据冲突类型分配到对应字段
                if conflict.dimension_a == "世界观约束":
                    fusion_result["血脉觉醒"]["融合结果"] = result
                elif conflict.dimension_a == "剧情框架":
                    fusion_result["剧情框架"]["融合结果"] = result
                elif conflict.dimension_a == "人物状态":
                    fusion_result["人物状态"]["融合结果"] = result

                fusion_result["融合说明"].append(
                    {
                        "冲突类型": conflict.type,
                        "原冲突": f"{conflict.content_a} vs {conflict.content_b}",
                        "融合决策": result,
                        "理由": note,
                    }
                )
            else:
                # 无规则，默认取 A
                fusion_result["融合说明"].append(
                    {
                        "冲突类型": conflict.type,
                        "原冲突": f"{conflict.content_a} vs {conflict.content_b}",
                        "融合决策": conflict.content_a,
                        "理由": f"默认取{conflict.dimension_a}",
                    }
                )

        return fusion_result

    def execute_phase1_parallel(
        self, scene_context: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        执行 Phase 1：并行生成（粗稿）

        Args:
            scene_context: 场景上下文

        Returns:
            三个维度的输出（世界观、剧情、人物）
        """
        # 这里只是结构定义，实际调用由 writer_executor 完成
        return {
            "世界观约束": {
                "血脉觉醒": scene_context.get("血脉设定", {}),
                "输出类型": "草稿",
                "来源作家": "苍澜",
            },
            "剧情框架": {
                "结构": scene_context.get("剧情结构", ""),
                "伏笔": scene_context.get("伏笔", []),
                "输出类型": "草稿",
                "来源作家": "玄一",
            },
            "人物状态": {
                "情感重点": scene_context.get("情感重点", ""),
                "心理变化": scene_context.get("心理变化", ""),
                "输出类型": "草稿",
                "来源作家": "墨言",
            },
        }

    def execute_phase1_5_detect(
        self, phase1_outputs: Dict[str, Any], filter_invalid: bool = True
    ) -> Tuple[List[Conflict], Dict[str, Any]]:
        """
        执行 Phase 1.5：一致性检测

        自动过滤"无特殊约束"的维度，只检测有效维度之间的冲突。

        Args:
            phase1_outputs: Phase 1 的三个输出
            filter_invalid: 是否过滤"无特殊约束"的输出（默认True）

        Returns:
            (冲突列表, 有效输出字典)
        """
        # 过滤"无特殊约束"的维度
        if filter_invalid:
            valid_outputs = self.filter_valid_outputs(phase1_outputs)
        else:
            valid_outputs = phase1_outputs

        # 单维度或无有效输出，无需检测冲突
        if len(valid_outputs) <= 1:
            return [], valid_outputs

        # 检测有效维度之间的冲突
        conflicts = self.detector.detect(valid_outputs)

        return conflicts, valid_outputs

    def execute_phase1_6_fuse(
        self,
        phase1_outputs: Dict[str, Any],
        conflicts: List[Conflict],
        user_confirm_callback: Optional[callable] = None,
    ) -> FusionResult:
        """
        执行 Phase 1.6：融合调整

        Args:
            phase1_outputs: Phase 1 输出
            conflicts: 冲突列表
            user_confirm_callback: 用户确认回调函数（>5冲突时使用）

        Returns:
            融合结果
        """
        strategy = self.determine_fusion_strategy(conflicts)

        if strategy == FusionStrategy.NONE:
            # 无冲突，直接返回原始输出
            return FusionResult(
                strategy=strategy,
                unified_constraints=phase1_outputs,
                fusion_notes=["无冲突，无需融合"],
                conflicts_resolved=0,
                auto_fused=False,
                yunxi_required=False,
                user_confirm_required=False,
                time_saved_seconds=30,
                metadata={"phase1_outputs": phase1_outputs},
            )

        elif strategy == FusionStrategy.AUTO:
            # 自动融合
            unified = self.auto_fuse(conflicts)
            self.stats["auto_fused"] += 1

            return FusionResult(
                strategy=strategy,
                unified_constraints=unified,
                fusion_notes=unified.get("融合说明", []),
                conflicts_resolved=len(conflicts),
                auto_fused=True,
                yunxi_required=False,
                user_confirm_required=False,
                time_saved_seconds=30,  # 节省调用云溪的时间
                metadata={"conflicts": [c.to_dict() for c in conflicts]},
            )

        elif strategy == FusionStrategy.YUNXI:
            # 需要云溪介入
            self.stats["yunxi_fused"] += 1

            return FusionResult(
                strategy=strategy,
                unified_constraints={},  # 需要调用云溪skill填充
                fusion_notes=["需要云溪介入融合"],
                conflicts_resolved=0,
                auto_fused=False,
                yunxi_required=True,
                user_confirm_required=False,
                time_saved_seconds=0,
                metadata={
                    "conflicts": [c.to_dict() for c in conflicts],
                    "yunxi_input_required": True,
                },
            )

        else:  # FusionStrategy.USER
            # 需要用户确认
            self.stats["user_confirmed"] += 1

            conflict_summary = self._generate_conflict_summary(conflicts)

            if user_confirm_callback:
                user_decision = user_confirm_callback(conflict_summary)
            else:
                user_decision = None

            return FusionResult(
                strategy=strategy,
                unified_constraints={},  # 用户确认后填充
                fusion_notes=[conflict_summary],
                conflicts_resolved=0,
                auto_fused=False,
                yunxi_required=False,
                user_confirm_required=True,
                time_saved_seconds=0,
                metadata={
                    "conflicts": [c.to_dict() for c in conflicts],
                    "user_decision_required": True,
                    "user_decision": user_decision,
                },
            )

    def _generate_conflict_summary(self, conflicts: List[Conflict]) -> str:
        """生成冲突摘要（用于用户确认）"""
        summary = "【冲突清单】\n\n"

        high = [c for c in conflicts if c.severity == ConflictSeverity.HIGH]
        medium = [c for c in conflicts if c.severity == ConflictSeverity.MEDIUM]
        low = [c for c in conflicts if c.severity == ConflictSeverity.LOW]

        if high:
            summary += "🔴 必须解决（HIGH）：\n"
            for c in high:
                summary += f"  - {c.type}: {c.content_a} vs {c.content_b}\n"
            summary += "\n"

        if medium:
            summary += "🟡 建议解决（MEDIUM）：\n"
            for c in medium:
                summary += f"  - {c.type}: {c.content_a} vs {c.content_b}\n"
            summary += "\n"

        if low:
            summary += "🟢 可选解决（LOW）：\n"
            for c in low:
                summary += f"  - {c.type}: {c.content_a} vs {c.content_b}\n"
            summary += "\n"

        summary += "请确认融合方向：\n"
        summary += "1. 自动融合（应用规则）\n"
        summary += "2. 手动指定（您决定）\n"
        summary += "3. 重新生成（回退Phase 1）"

        return summary

    def get_efficiency_stats(self) -> Dict[str, Any]:
        """获取效率统计"""
        total = self.stats["total_scenes"]

        if total == 0:
            return {"message": "尚未执行任何场景"}

        auto_rate = self.stats["auto_fused"] / total * 100
        yunxi_rate = self.stats["yunxi_fused"] / total * 100
        user_rate = self.stats["user_confirmed"] / total * 100
        no_conflict_rate = self.stats["no_conflicts"] / total * 100

        return {
            "总场景数": total,
            "自动融合": f"{self.stats['auto_fused']} ({auto_rate:.1f}%)",
            "云溪融合": f"{self.stats['yunxi_fused']} ({yunxi_rate:.1f}%)",
            "用户确认": f"{self.stats['user_confirmed']} ({user_rate:.1f}%)",
            "无冲突": f"{self.stats['no_conflicts']} ({no_conflict_rate:.1f}%)",
            "平均节省时间": f"{self.stats['avg_time_saved']}秒",
        }

    def update_stats(self, fusion_result: FusionResult):
        """更新统计"""
        self.stats["total_scenes"] += 1

        if fusion_result.strategy == FusionStrategy.NONE:
            self.stats["no_conflicts"] += 1
        elif fusion_result.strategy == FusionStrategy.AUTO:
            self.stats["auto_fused"] += 1
        elif fusion_result.strategy == FusionStrategy.YUNXI:
            self.stats["yunxi_fused"] += 1
        elif fusion_result.strategy == FusionStrategy.USER:
            self.stats["user_confirmed"] += 1

        # 计算平均节省时间
        total_saved = (
            self.stats["no_conflicts"] * 30
            + self.stats["auto_fused"] * 30
            + self.stats["yunxi_fused"] * 0
            + self.stats["user_confirmed"] * 0
        )
        self.stats["avg_time_saved"] = total_saved // self.stats["total_scenes"]


# 便捷函数
def create_creation_mode() -> CreationMode:
    """创建创作模式实例"""
    return CreationMode()


def determine_fusion_strategy(conflicts: List[Conflict]) -> FusionStrategy:
    """便捷函数：判断融合策略"""
    mode = CreationMode()
    return mode.determine_fusion_strategy(conflicts)


def auto_fuse_conflicts(conflicts: List[Conflict]) -> Dict[str, Any]:
    """便捷函数：自动融合"""
    mode = CreationMode()
    return mode.auto_fuse(conflicts)


# 使用示例
if __name__ == "__main__":
    # 示例1：正常场景（三个维度都有内容）
    print("=" * 60)
    print("示例1：正常场景（三个维度都有内容）")
    print("=" * 60)
    phase1_outputs = {
        "世界观约束": {
            "血脉觉醒": {"触发": "目睹母亲被肢解", "代价": "遗忘母亲的名字"}
        },
        "剧情框架": {"伏笔": ["母亲临死说出一个秘密"]},
        "人物状态": {"情感重点": "记住母亲的每一句话"},
    }

    mode = CreationMode()
    conflicts, valid_outputs = mode.execute_phase1_5_detect(phase1_outputs)
    print(f"有效维度数: {len(valid_outputs)}")
    print(f"检测到 {len(conflicts)} 个冲突")

    fusion_result = mode.execute_phase1_6_fuse(phase1_outputs, conflicts)
    print(f"\n融合策略: {fusion_result.strategy.value}")
    mode.update_stats(fusion_result)

    # 示例2：剧情推进场景（某维度无特殊约束）
    print("\n" + "=" * 60)
    print("示例2：剧情推进场景（某维度无特殊约束）")
    print("=" * 60)
    phase1_outputs_2 = {
        "世界观约束": {"内容": "无特殊约束", "说明": "使用默认设定"},
        "剧情框架": {"伏笔": ["悬念1", "悬念2"], "结构": "铺垫→高潮"},
        "人物状态": {"内容": "无特殊约束", "说明": "保持当前状态"},
    }

    conflicts2, valid_outputs2 = mode.execute_phase1_5_detect(phase1_outputs_2)
    print(f"有效维度数: {len(valid_outputs2)} (过滤了'无特殊约束')")
    print(f"有效维度: {list(valid_outputs2.keys())}")
    print(f"检测到 {len(conflicts2)} 个冲突")

    fusion_result2 = mode.execute_phase1_6_fuse(phase1_outputs_2, conflicts2)
    print(f"\n融合策略: {fusion_result2.strategy.value}")
    print(f"无需融合: {len(valid_outputs2) <= 1}")
    mode.update_stats(fusion_result2)

    # 输出效率统计
    print("\n" + "=" * 60)
    print("效率统计:")
    print("=" * 60)
    stats = mode.get_efficiency_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
