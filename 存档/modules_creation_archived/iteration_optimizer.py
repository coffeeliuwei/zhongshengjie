"""
迭代优化器

功能：
1. 迭代风险预测：预估场景迭代风险，提前预警
2. 快速失败机制：Phase 输出质量检查，避免后续浪费
3. 动态迭代调整：根据场景复杂度调整迭代上限
4. 效率统计：记录迭代数据，持续优化

设计目的：
- 解决"迭代循环导致时间不可控"的核心瓶颈
- 将最坏情况（8分钟/场景）控制在合理范围（3-5分钟）
"""

from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import re


class IterationRisk(Enum):
    """迭代风险等级"""

    LOW = "low"  # 低风险，预期1次通过
    MEDIUM = "medium"  # 中风险，预期2次通过
    HIGH = "high"  # 高风险，预期3次通过
    CRITICAL = "critical"  # 极高风险，建议增加讨论


class SceneComplexity(Enum):
    """场景复杂度"""

    SIMPLE = "simple"  # 简单场景：单一类型，无复杂冲突
    MODERATE = "moderate"  # 中等场景：2种类型，简单冲突
    COMPLEX = "complex"  # 复杂场景：3+类型，复杂冲突
    VERY_COMPLEX = "very_complex"  # 极复杂场景：多类型+强冲突


@dataclass
class IterationPrediction:
    """迭代预测结果"""

    risk_level: IterationRisk
    expected_iterations: int
    confidence: float  # 0-1，预测置信度
    risk_factors: List[str]
    recommendations: List[str]
    suggested_max_iterations: int
    estimated_time_seconds: int


@dataclass
class PhaseQualityCheck:
    """Phase 输出质量检查结果"""

    phase: str
    passed: bool
    score: float  # 0-1
    issues: List[str]
    retry_recommended: bool
    retry_reason: Optional[str] = None


class IterationPredictor:
    """
    迭代风险预测器

    在阶段0结束时预测迭代风险，提前预警。
    """

    # 风险因素权重
    RISK_WEIGHTS = {
        "conflict_count": 0.25,
        "scene_complexity": 0.20,
        "experience_richness": 0.15,
        "setting_completeness": 0.15,
        "discussion_depth": 0.15,
        "technique_count": 0.10,
    }

    # 场景类型复杂度基准
    SCENE_COMPLEXITY_BASELINE = {
        "战斗场景": SceneComplexity.COMPLEX,
        "世界观展开": SceneComplexity.MODERATE,
        "人物出场": SceneComplexity.MODERATE,
        "人物成长": SceneComplexity.COMPLEX,
        "剧情推进": SceneComplexity.MODERATE,
        "情感场景": SceneComplexity.MODERATE,
        "章节润色": SceneComplexity.SIMPLE,
        "伏笔埋设": SceneComplexity.MODERATE,
        "悬念设计": SceneComplexity.MODERATE,
    }

    def __init__(self):
        self.history = []  # 历史预测记录

    def predict(
        self,
        scene_type: str,
        scene_description: str,
        phase1_outputs: Optional[Dict] = None,
        experience_count: int = 0,
        setting_completeness: float = 0.5,
        discussion_rounds: int = 1,
        techniques_planned: int = 0,
    ) -> IterationPrediction:
        """
        预测迭代风险

        Args:
            scene_type: 场景类型
            scene_description: 场景描述
            phase1_outputs: Phase 1 输出（如果有）
            experience_count: 前章经验数量
            setting_completeness: 设定完整度（0-1）
            discussion_rounds: 阶段0讨论轮次
            techniques_planned: 计划使用的技法数量

        Returns:
            迭代预测结果
        """
        risk_factors = []
        recommendations = []

        # 1. 计算冲突数量风险
        conflict_risk = 0.0
        if phase1_outputs:
            from .conflict_detector import ConflictDetector

            detector = ConflictDetector()
            conflicts = detector.detect(phase1_outputs)
            conflict_count = len(conflicts)
            conflict_risk = min(conflict_count / 5, 1.0)

            if conflict_count > 3:
                risk_factors.append(f"检测到 {conflict_count} 个冲突")
                recommendations.append("建议在阶段0明确方向，减少冲突")
        else:
            conflict_risk = 0.3  # 默认值

        # 2. 计算场景复杂度风险
        scene_complexity = self._estimate_scene_complexity(
            scene_type, scene_description
        )
        complexity_risk = {
            SceneComplexity.SIMPLE: 0.1,
            SceneComplexity.MODERATE: 0.3,
            SceneComplexity.COMPLEX: 0.6,
            SceneComplexity.VERY_COMPLEX: 0.9,
        }.get(scene_complexity, 0.3)

        if scene_complexity in [SceneComplexity.COMPLEX, SceneComplexity.VERY_COMPLEX]:
            risk_factors.append(f"场景复杂度高（{scene_complexity.value}）")

        # 3. 计算经验丰富度风险
        experience_risk = max(0, 1 - experience_count / 10)
        if experience_count < 3:
            risk_factors.append("前章经验不足")
            recommendations.append("建议降低首次创作标准，积累经验")

        # 4. 计算设定完整度风险
        setting_risk = 1 - setting_completeness
        if setting_completeness < 0.5:
            risk_factors.append(f"设定完整度低（{setting_completeness:.0%}）")
            recommendations.append("建议先补充相关设定")

        # 5. 计算讨论深度风险
        discussion_risk = max(0, 1 - discussion_rounds / 3)
        if discussion_rounds < 2:
            risk_factors.append("阶段0讨论不充分")
            recommendations.append("建议继续讨论，明确创作方向")

        # 6. 计算技法数量风险
        technique_risk = (
            min(techniques_planned / 5, 1.0) if techniques_planned > 0 else 0.2
        )
        if techniques_planned > 3:
            risk_factors.append(f"计划使用 {techniques_planned} 个技法，复杂度高")

        # 计算综合风险
        total_risk = (
            conflict_risk * self.RISK_WEIGHTS["conflict_count"]
            + complexity_risk * self.RISK_WEIGHTS["scene_complexity"]
            + experience_risk * self.RISK_WEIGHTS["experience_richness"]
            + setting_risk * self.RISK_WEIGHTS["setting_completeness"]
            + discussion_risk * self.RISK_WEIGHTS["discussion_depth"]
            + technique_risk * self.RISK_WEIGHTS["technique_count"]
        )

        # 确定风险等级
        if total_risk < 0.25:
            risk_level = IterationRisk.LOW
            expected_iterations = 1
        elif total_risk < 0.5:
            risk_level = IterationRisk.MEDIUM
            expected_iterations = 2
        elif total_risk < 0.75:
            risk_level = IterationRisk.HIGH
            expected_iterations = 3
        else:
            risk_level = IterationRisk.CRITICAL
            expected_iterations = 3
            recommendations.insert(0, "⚠️ 建议返回阶段0继续讨论，降低风险")

        # 计算预测置信度
        confidence = self._calculate_confidence(
            phase1_outputs is not None,
            experience_count > 0,
            discussion_rounds > 1,
        )

        # 建议最大迭代次数
        suggested_max = self._suggest_max_iterations(risk_level, scene_complexity)

        # 预估时间
        estimated_time = self._estimate_time(expected_iterations, scene_complexity)

        return IterationPrediction(
            risk_level=risk_level,
            expected_iterations=expected_iterations,
            confidence=confidence,
            risk_factors=risk_factors,
            recommendations=recommendations,
            suggested_max_iterations=suggested_max,
            estimated_time_seconds=estimated_time,
        )

    def _estimate_scene_complexity(
        self, scene_type: str, scene_description: str
    ) -> SceneComplexity:
        """估算场景复杂度"""
        # 基于场景类型的基准
        base_complexity = self.SCENE_COMPLEXITY_BASELINE.get(
            scene_type, SceneComplexity.MODERATE
        )

        # 基于描述的调整
        complexity_keywords = {
            "同时": 0.1,
            "多个": 0.1,
            "交织": 0.15,
            "复杂": 0.2,
            "冲突": 0.1,
            "矛盾": 0.1,
            "转折": 0.1,
        }

        additional_risk = 0
        for keyword, weight in complexity_keywords.items():
            if keyword in scene_description:
                additional_risk += weight

        # 调整复杂度
        complexity_order = [
            SceneComplexity.SIMPLE,
            SceneComplexity.MODERATE,
            SceneComplexity.COMPLEX,
            SceneComplexity.VERY_COMPLEX,
        ]
        current_index = complexity_order.index(base_complexity)
        adjusted_index = min(
            current_index + int(additional_risk * 2), len(complexity_order) - 1
        )

        return complexity_order[adjusted_index]

    def _calculate_confidence(
        self, has_phase1_output: bool, has_experience: bool, has_discussion: bool
    ) -> float:
        """计算预测置信度"""
        confidence = 0.5  # 基准置信度

        if has_phase1_output:
            confidence += 0.2
        if has_experience:
            confidence += 0.15
        if has_discussion:
            confidence += 0.15

        return min(confidence, 0.95)

    def _suggest_max_iterations(
        self, risk_level: IterationRisk, complexity: SceneComplexity
    ) -> int:
        """建议最大迭代次数"""
        base_iterations = {
            IterationRisk.LOW: 1,
            IterationRisk.MEDIUM: 2,
            IterationRisk.HIGH: 3,
            IterationRisk.CRITICAL: 3,
        }

        complexity_adjustment = {
            SceneComplexity.SIMPLE: -1,
            SceneComplexity.MODERATE: 0,
            SceneComplexity.COMPLEX: 0,
            SceneComplexity.VERY_COMPLEX: 1,
        }

        base = base_iterations.get(risk_level, 2)
        adjustment = complexity_adjustment.get(complexity, 0)

        return max(1, base + adjustment)

    def _estimate_time(
        self, expected_iterations: int, complexity: SceneComplexity
    ) -> int:
        """预估创作时间（秒）"""
        # 基准时间（单次创作）
        base_time = {
            SceneComplexity.SIMPLE: 120,
            SceneComplexity.MODERATE: 150,
            SceneComplexity.COMPLEX: 180,
            SceneComplexity.VERY_COMPLEX: 240,
        }

        single_pass = base_time.get(complexity, 150)

        # 迭代增加时间（每次迭代约增加80%时间，因为有反馈）
        if expected_iterations == 1:
            return single_pass
        elif expected_iterations == 2:
            return int(single_pass * 1.8)
        else:
            return int(single_pass * 2.5)


class QuickFailChecker:
    """
    快速失败检查器

    在每个 Phase 输出后检查质量，不合格立即返回重做。
    """

    # 各 Phase 的最低质量阈值
    PHASE_THRESHOLDS = {
        "phase1_worldview": 0.5,
        "phase1_plot": 0.5,
        "phase1_character": 0.5,
        "phase2_content": 0.6,
        "phase3_polished": 0.7,
    }

    def check_phase1_output(
        self, dimension: str, output: Dict[str, Any]
    ) -> PhaseQualityCheck:
        """
        检查 Phase 1 输出质量

        Args:
            dimension: 维度名称（"世界观约束"/"剧情框架"/"人物状态"）
            output: Phase 1 输出

        Returns:
            质量检查结果
        """
        issues = []
        score = 1.0

        # 检查1：是否为空输出
        if not output or output == {}:
            return PhaseQualityCheck(
                phase=f"phase1_{dimension}",
                passed=False,
                score=0.0,
                issues=["输出为空"],
                retry_recommended=True,
                retry_reason="作家输出为空，需要重新生成",
            )

        # 检查2：是否为"无特殊约束"（合法输出，直接通过）
        if output.get("内容") == "无特殊约束" or output.get("content") == "无特殊约束":
            return PhaseQualityCheck(
                phase=f"phase1_{dimension}",
                passed=True,
                score=1.0,
                issues=[],
                retry_recommended=False,
            )

        # 检查3：内容完整性
        dimension_requirements = {
            "世界观约束": ["血脉觉醒", "设定", "约束"],
            "剧情框架": ["伏笔", "结构", "钩子"],
            "人物状态": ["情感", "心理", "行为"],
        }

        requirements = dimension_requirements.get(dimension, [])
        has_content = any(req in str(output) for req in requirements)

        if not has_content and len(str(output)) < 50:
            issues.append("输出内容不完整")
            score -= 0.3

        # 检查4：逻辑一致性（简单检查）
        output_str = str(output)
        if "遗忘" in output_str and "记住" in output_str:
            # 可能存在矛盾，但需要融合阶段处理
            pass

        # 计算最终分数
        threshold = self.PHASE_THRESHOLDS.get(f"phase1_{dimension}", 0.5)
        passed = score >= threshold

        return PhaseQualityCheck(
            phase=f"phase1_{dimension}",
            passed=passed,
            score=max(0, score),
            issues=issues,
            retry_recommended=not passed and score < 0.4,
            retry_reason="输出质量过低" if not passed else None,
        )

    def check_phase2_output(
        self, output: str, target_word_count: int = 2000
    ) -> PhaseQualityCheck:
        """
        检查 Phase 2 输出质量

        Args:
            output: Phase 2 输出内容
            target_word_count: 目标字数

        Returns:
            质量检查结果
        """
        issues = []
        score = 1.0

        # 检查1：是否为空
        if not output or len(output.strip()) < 100:
            return PhaseQualityCheck(
                phase="phase2_content",
                passed=False,
                score=0.0,
                issues=["输出内容过短或为空"],
                retry_recommended=True,
                retry_reason="核心创作内容不足，需要重新生成",
            )

        # 检查2：字数检查
        actual_words = len(output)
        word_ratio = actual_words / target_word_count

        if word_ratio < 0.5:
            issues.append(f"字数不足（{actual_words}/{target_word_count}）")
            score -= 0.2
        elif word_ratio < 0.7:
            issues.append(f"字数略少（{actual_words}/{target_word_count}）")
            score -= 0.1

        # 检查3：禁止项快速检查
        forbidden_patterns = [
            (r"眼中闪过一丝", "AI味表达：眼中闪过一丝"),
            (r"心中涌起一股", "AI味表达：心中涌起一股"),
            (r"^\s*然后\s", "时间连接词开头"),
            (r"^\s*就在这时\s", "时间连接词开头"),
            (r"\*\*[^*]+\*\*", "Markdown加粗"),
        ]

        for pattern, issue_name in forbidden_patterns:
            if re.search(pattern, output):
                issues.append(f"发现{issue_name}")
                score -= 0.15

        # 计算最终分数
        threshold = self.PHASE_THRESHOLDS.get("phase2_content", 0.6)
        passed = score >= threshold

        return PhaseQualityCheck(
            phase="phase2_content",
            passed=passed,
            score=max(0, score),
            issues=issues,
            retry_recommended=not passed and score < 0.5,
            retry_reason="内容质量不达标" if not passed else None,
        )


class DynamicIterationAdjuster:
    """
    动态迭代调整器

    根据场景复杂度和实时反馈调整迭代上限。
    """

    def __init__(self):
        self.iteration_history = []

    def get_max_iterations(
        self,
        scene_type: str,
        complexity: SceneComplexity,
        prediction: IterationPrediction,
        user_preference: Optional[str] = None,
    ) -> int:
        """
        获取最大迭代次数

        Args:
            scene_type: 场景类型
            complexity: 场景复杂度
            prediction: 迭代预测
            user_preference: 用户偏好（"speed"/"quality"/"balanced"）

        Returns:
            最大迭代次数
        """
        # 默认值
        default_iterations = {
            SceneComplexity.SIMPLE: 1,
            SceneComplexity.MODERATE: 2,
            SceneComplexity.COMPLEX: 3,
            SceneComplexity.VERY_COMPLEX: 3,
        }

        base_iterations = default_iterations.get(complexity, 2)

        # 用户偏好调整
        if user_preference == "speed":
            base_iterations = max(1, base_iterations - 1)
        elif user_preference == "quality":
            base_iterations = min(3, base_iterations + 1)

        # 风险等级调整
        if prediction.risk_level == IterationRisk.LOW:
            base_iterations = min(base_iterations, 2)
        elif prediction.risk_level == IterationRisk.CRITICAL:
            # 高风险场景，限制迭代次数，避免无限循环
            base_iterations = min(base_iterations, 2)
            # 但建议用户继续讨论

        return base_iterations

    def should_continue_iteration(
        self,
        current_iteration: int,
        max_iterations: int,
        quality_score: float,
        improvement_rate: float,
    ) -> Tuple[bool, str]:
        """
        判断是否应该继续迭代

        Args:
            current_iteration: 当前迭代次数
            max_iterations: 最大迭代次数
            quality_score: 当前质量分数
            improvement_rate: 改进率（相比上次）

        Returns:
            (是否继续, 原因)
        """
        # 已达上限
        if current_iteration >= max_iterations:
            return False, f"已达最大迭代次数（{max_iterations}次）"

        # 质量已达标
        if quality_score >= 0.8:
            return False, "质量已达标，无需继续迭代"

        # 改进率过低（连续迭代无明显改进）
        if current_iteration > 1 and improvement_rate < 0.05:
            return False, "连续迭代改进不明显，建议接受当前结果"

        # 继续迭代
        return True, f"继续迭代（{current_iteration + 1}/{max_iterations}）"


# 便捷函数
def predict_iteration_risk(
    scene_type: str,
    scene_description: str,
    **kwargs,
) -> IterationPrediction:
    """便捷函数：预测迭代风险"""
    predictor = IterationPredictor()
    return predictor.predict(scene_type, scene_description, **kwargs)


def check_phase_quality(phase: str, output: Any) -> PhaseQualityCheck:
    """便捷函数：检查 Phase 输出质量"""
    checker = QuickFailChecker()

    if phase.startswith("phase1"):
        dimension = phase.replace("phase1_", "")
        return checker.check_phase1_output(dimension, output)
    elif phase == "phase2":
        return checker.check_phase2_output(output)
    else:
        return PhaseQualityCheck(
            phase=phase,
            passed=True,
            score=1.0,
            issues=[],
            retry_recommended=False,
        )


# 使用示例
if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    # 示例1：预测迭代风险
    print("=" * 60)
    print("示例1：迭代风险预测")
    print("=" * 60)

    predictor = IterationPredictor()
    prediction = predictor.predict(
        scene_type="战斗场景",
        scene_description="主角目睹母亲被杀，血脉觉醒，与敌人战斗",
        experience_count=2,
        setting_completeness=0.7,
        discussion_rounds=2,
        techniques_planned=2,
    )

    print(f"风险等级: {prediction.risk_level.value}")
    print(f"预期迭代: {prediction.expected_iterations} 次")
    print(f"预测置信度: {prediction.confidence:.0%}")
    print(f"建议最大迭代: {prediction.suggested_max_iterations} 次")
    print(f"预估时间: {prediction.estimated_time_seconds} 秒")
    print(f"风险因素: {prediction.risk_factors}")
    print(f"建议: {prediction.recommendations}")

    # 示例2：快速失败检查
    print("\n" + "=" * 60)
    print("示例2：Phase 输出质量检查")
    print("=" * 60)

    checker = QuickFailChecker()

    # 检查 Phase 1 输出
    phase1_output = {
        "血脉觉醒": {"触发": "目睹母亲被杀", "代价": "遗忘名字"},
    }
    result = checker.check_phase1_output("世界观约束", phase1_output)
    print(f"\nPhase 1 检查结果:")
    print(f"  通过: {result.passed}")
    print(f"  分数: {result.score:.2f}")
    print(f"  建议重试: {result.retry_recommended}")

    # 检查 Phase 2 输出
    phase2_output = "这是一段测试内容，字数较少。"
    result = checker.check_phase2_output(phase2_output, target_word_count=2000)
    print(f"\nPhase 2 检查结果:")
    print(f"  通过: {result.passed}")
    print(f"  分数: {result.score:.2f}")
    print(f"  问题: {result.issues}")

    # 示例3：动态迭代调整
    print("\n" + "=" * 60)
    print("示例3：动态迭代调整")
    print("=" * 60)

    adjuster = DynamicIterationAdjuster()
    max_iter = adjuster.get_max_iterations(
        scene_type="战斗场景",
        complexity=SceneComplexity.COMPLEX,
        prediction=prediction,
        user_preference="balanced",
    )
    print(f"\n最大迭代次数: {max_iter}")

    should_continue, reason = adjuster.should_continue_iteration(
        current_iteration=1,
        max_iterations=max_iter,
        quality_score=0.6,
        improvement_rate=0.1,
    )
    print(f"是否继续: {should_continue}")
    print(f"原因: {reason}")
