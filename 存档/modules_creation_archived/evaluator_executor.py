"""
评估执行器
集成 novelist-evaluator skill，提供统一的评估调用接口

执行器负责：
1. 调用 novelist-evaluator skill
2. 构建标准化的评估输入
3. 解析评估输出
4. 返回结构化的评估结果
"""

import json
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path

# 评估阈值（来自 CONFIG.md）
EVALUATION_THRESHOLDS = {
    "世界自洽": 7,
    "人物立体": 6,
    "情感真实": 6,
    "战斗逻辑": 6,
    "文风克制": 6,
    "剧情张力": 6,
}

# 禁止项列表
FORBIDDEN_ITEMS = {
    "AI味表达": [
        "眼中闪过一丝",
        "心中涌起一股",
        "嘴角勾起一抹",
        "不禁",
        "忍不住",
    ],
    "古龙式极简": [r"^.{1,2}$"],  # 单字/双字成段
    "时间连接词": ["然后", "就在这时", "过了一会儿", "随后"],
    "抽象统计词": ["无数", "成千上万", "数不清"],
    "精确年龄": [r"\d+岁的"],
    "Markdown加粗": [r"\*\*[^*]+\*\*"],
}


@dataclass
class ForbiddenItemResult:
    """禁止项检测结果"""

    item_type: str
    count: int
    examples: List[str]
    passed: bool


@dataclass
class EvaluationScore:
    """评估分数"""

    dimension: str
    score: int
    threshold: int
    passed: bool
    explanation: str = ""


@dataclass
class EvaluationOutput:
    """评估输出"""

    # 禁止项检测
    forbidden_results: List[ForbiddenItemResult]
    forbidden_passed: bool

    # 技法评估
    technique_scores: Dict[str, EvaluationScore]
    technique_passed: bool

    # 整体质量
    overall_score: float
    overall_passed: bool

    # 反馈
    p0_issues: List[Dict[str, Any]]  # 必须修改项
    p1_issues: List[Dict[str, Any]]  # 建议优化项

    # 结论
    conclusion: str  # 通过/需修改后通过/需重写
    iteration_needed: bool


class EvaluatorExecutor:
    """
    评估执行器

    负责调用 novelist-evaluator skill 并管理输入输出
    """

    def __init__(
        self,
        skill_caller: Optional[Callable] = None,
        project_root: Optional[Path] = None,
        thresholds: Optional[Dict[str, int]] = None,
    ):
        """
        初始化评估执行器

        Args:
            skill_caller: Skill 调用函数（需外部提供）
            project_root: 项目根目录
            thresholds: 评估阈值
        """
        self.skill_caller = skill_caller
        self.project_root = project_root or Path("D:/动画/众生界")
        self.thresholds = thresholds or EVALUATION_THRESHOLDS.copy()

    def _detect_forbidden_items(self, content: str) -> List[ForbiddenItemResult]:
        """
        检测禁止项

        Args:
            content: 待检测内容

        Returns:
            禁止项检测结果列表
        """
        results = []

        for item_type, patterns in FORBIDDEN_ITEMS.items():
            examples = []
            count = 0

            for pattern in patterns:
                if pattern.startswith("^") or pattern.startswith(r"\d"):
                    # 正则模式
                    matches = re.findall(pattern, content, re.MULTILINE)
                    count += len(matches)
                    examples.extend(matches[:3])
                else:
                    # 字符串模式
                    matches = content.count(pattern)
                    if matches > 0:
                        count += matches
                        # 提取上下文
                        for match in re.finditer(re.escape(pattern), content):
                            start = max(0, match.start() - 10)
                            end = min(len(content), match.end() + 10)
                            examples.append(f"...{content[start:end]}...")
                            if len(examples) >= 3:
                                break

            # 判断是否通过
            # AI味表达式和古龙式极简：出现1个即失败
            # 时间连接词：≥3个失败
            # 抽象统计词：≥2个失败
            # 精确年龄：≥2个失败
            # Markdown加粗：出现1个失败

            if item_type in ["AI味表达", "古龙式极简", "Markdown加粗"]:
                passed = count == 0
            elif item_type == "时间连接词":
                passed = count < 3
            else:  # 抽象统计词, 精确年龄
                passed = count < 2

            results.append(
                ForbiddenItemResult(
                    item_type=item_type,
                    count=count,
                    examples=examples,
                    passed=passed,
                )
            )

        return results

    def _build_evaluation_input(
        self,
        content: str,
        scene_type: str,
        primary_writer: str,
        iteration: int,
    ) -> Dict[str, Any]:
        """
        构建评估输入

        Args:
            content: 待评估内容
            scene_type: 场景类型
            primary_writer: 主责作家
            iteration: 当前迭代次数

        Returns:
            评估输入字典
        """
        # 构建标准化的评估输入
        evaluation_input = {
            "审核请求": {
                "内容": content,
                "作者列表": [primary_writer],
                "场景类型": scene_type,
                "特别关注": self._get_special_focus(scene_type),
            },
            "元数据": {
                "场景ID": f"scene_{iteration}",
                "章节号": "当前章节",
                "字数": len(content),
            },
            "评估阈值": self.thresholds,
        }

        return evaluation_input

    def _get_special_focus(self, scene_type: str) -> List[str]:
        """
        根据场景类型获取特别关注项

        Args:
            scene_type: 场景类型

        Returns:
            特别关注项列表
        """
        focus_map = {
            "战斗场景": ["代价描写", "群体牺牲", "战斗逻辑"],
            "世界观": ["设定一致性", "逻辑自洽"],
            "人物出场": ["人物辨识度", "性格展示"],
            "情感场景": ["情感真实", "克制表达"],
            "对话场景": ["对话风格", "潜台词"],
            "悬念场景": ["信息差设计", "悬念布局"],
            "转折场景": ["反转设计", "伏笔回收"],
            "环境场景": ["氛围描写", "五感联动"],
        }

        return focus_map.get(scene_type, [])

    def _parse_evaluation_output(
        self,
        result: Dict[str, Any],
        forbidden_results: List[ForbiddenItemResult],
    ) -> EvaluationOutput:
        """
        解析评估输出

        Args:
            result: Skill 返回结果
            forbidden_results: 禁止项检测结果

        Returns:
            评估输出对象
        """
        # 解析技法评估
        technique_scores = {}
        technique_scores_raw = result.get("技法评估", {})

        for dimension, scores in technique_scores_raw.items():
            if isinstance(scores, dict):
                for technique, data in scores.items():
                    score = data.get("评分", 0) if isinstance(data, dict) else 0
                    threshold = self.thresholds.get(dimension, 6)

                    technique_scores[technique] = EvaluationScore(
                        dimension=dimension,
                        score=score,
                        threshold=threshold,
                        passed=score >= threshold,
                        explanation=data.get("说明", "")
                        if isinstance(data, dict)
                        else "",
                    )

        # 解析整体质量
        overall = result.get("整体质量", {})
        overall_score = overall.get("综合评分", 0)
        overall_passed = overall_score >= 6

        # 解析反馈
        feedback = result.get("反馈", {})
        p0_issues = feedback.get("P0需修改", [])
        p1_issues = feedback.get("P1建议优化", [])

        # 判断禁止项是否全部通过
        forbidden_passed = all(r.passed for r in forbidden_results)

        # 判断技法是否全部通过
        technique_passed = all(s.passed for s in technique_scores.values())

        # 确定结论
        conclusion = result.get("结论", "")
        if not conclusion:
            if forbidden_passed and technique_passed:
                conclusion = "通过"
            elif p0_issues:
                conclusion = "需修改后通过"
            else:
                conclusion = "需重写"

        # 判断是否需要迭代
        iteration_needed = conclusion != "通过"

        return EvaluationOutput(
            forbidden_results=forbidden_results,
            forbidden_passed=forbidden_passed,
            technique_scores=technique_scores,
            technique_passed=technique_passed,
            overall_score=overall_score,
            overall_passed=overall_passed,
            p0_issues=p0_issues,
            p1_issues=p1_issues,
            conclusion=conclusion,
            iteration_needed=iteration_needed,
        )

    def execute(
        self,
        content: str,
        scene_type: str,
        primary_writer: str,
        iteration: int,
        thresholds: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        执行评估

        Args:
            content: 待评估内容
            scene_type: 场景类型
            primary_writer: 主责作家
            iteration: 当前迭代次数
            thresholds: 评估阈值（可选，覆盖默认值）

        Returns:
            评估结果字典
        """
        # 更新阈值
        if thresholds:
            self.thresholds.update(thresholds)

        # 检测禁止项
        forbidden_results = self._detect_forbidden_items(content)

        # 构建评估输入
        evaluation_input = self._build_evaluation_input(
            content, scene_type, primary_writer, iteration
        )

        # 调用 Skill
        if self.skill_caller:
            # 实际调用
            result = self.skill_caller(
                skill_name="novelist-evaluator",
                skill_input=evaluation_input,
            )
        else:
            # 模拟调用（用于测试）
            result = self._simulate_evaluation(content, scene_type, forbidden_results)

        # 解析输出
        output = self._parse_evaluation_output(result, forbidden_results)

        # 转换为字典格式（兼容 WorkflowScheduler）
        return {
            "scores": {
                technique: score.score
                for technique, score in output.technique_scores.items()
            },
            "total_score": output.overall_score,
            "feedback": self._format_feedback(output),
            "forbidden_passed": output.forbidden_passed,
            "technique_passed": output.technique_passed,
            "p0_issues": output.p0_issues,
            "p1_issues": output.p1_issues,
            "conclusion": output.conclusion,
            "iteration_needed": output.iteration_needed,
        }

    def _simulate_evaluation(
        self,
        content: str,
        scene_type: str,
        forbidden_results: List[ForbiddenItemResult],
    ) -> Dict[str, Any]:
        """
        模拟评估（用于测试）

        Args:
            content: 待评估内容
            scene_type: 场景类型
            forbidden_results: 禁止项检测结果

        Returns:
            模拟的评估结果
        """
        # 简单模拟：基于内容长度和禁止项生成评分
        base_score = min(10, max(4, len(content) // 100))

        # 根据禁止项调整
        forbidden_penalty = sum(1 for r in forbidden_results if not r.passed)

        # 生成技法评分
        technique_scores = {}
        for dimension in self.thresholds.keys():
            score = max(4, base_score - forbidden_penalty)
            technique_scores[dimension] = {
                "评分": score,
                "说明": f"{dimension}评估说明",
            }

        # 整体评分
        overall_score = sum(data["评分"] for data in technique_scores.values()) / len(
            technique_scores
        )

        # 结论
        all_passed = all(r.passed for r in forbidden_results) and overall_score >= 6

        return {
            "技法评估": {"维度": technique_scores},
            "整体质量": {
                "综合评分": overall_score,
            },
            "反馈": {
                "P0需修改": []
                if all_passed
                else [{"问题": "示例问题", "建议": "示例建议"}],
                "P1建议优化": [],
            },
            "结论": "通过" if all_passed else "需修改后通过",
        }

    def _format_feedback(self, output: EvaluationOutput) -> str:
        """
        格式化反馈文本

        Args:
            output: 评估输出

        Returns:
            反馈文本
        """
        lines = []

        # 禁止项检测
        lines.append("【禁止项检测】")
        for result in output.forbidden_results:
            status = "✓" if result.passed else "✗"
            lines.append(
                f"  {status} {result.item_type}: {result.count}个"
                + (f" [{result.examples[0]}...]" if result.examples else "")
            )
        lines.append(f"  结果: {'通过' if output.forbidden_passed else '失败'}")

        # 技法评估
        lines.append("\n【技法评估】")
        for technique, score in output.technique_scores.items():
            status = "✓" if score.passed else "✗"
            lines.append(
                f"  {status} {technique}: {score.score}/{score.threshold} - {score.explanation}"
            )
        lines.append(f"  结果: {'通过' if output.technique_passed else '需改进'}")

        # 整体评分
        lines.append(f"\n【整体评分】{output.overall_score:.1f}/10")

        # 结论
        lines.append(f"\n【结论】{output.conclusion}")

        return "\n".join(lines)


def create_evaluator_executor_function(
    skill_caller: Optional[Callable] = None,
    project_root: Optional[Path] = None,
    thresholds: Optional[Dict[str, int]] = None,
) -> Callable:
    """
    创建评估执行器函数（用于传递给 WorkflowScheduler）

    Args:
        skill_caller: Skill 调用函数
        project_root: 项目根目录
        thresholds: 评估阈值

    Returns:
        评估执行器函数
    """
    executor = EvaluatorExecutor(
        skill_caller=skill_caller,
        project_root=project_root,
        thresholds=thresholds,
    )

    def evaluator_executor_function(
        content: str,
        scene_type: str,
        primary_writer: str,
        iteration: int,
        thresholds: Dict[str, int],
    ) -> Dict[str, Any]:
        """评估执行器函数"""
        return executor.execute(
            content=content,
            scene_type=scene_type,
            primary_writer=primary_writer,
            iteration=iteration,
            thresholds=thresholds,
        )

    return evaluator_executor_function


# 使用示例
if __name__ == "__main__":
    # 创建执行器
    executor = EvaluatorExecutor()

    # 测试评估
    test_content = """
    血牙挥舞战刀，眼中闪过一丝决然。

    然后他冲向敌人，心中涌起一股力量。

    无数敌人倒下了，但他的血脉力量也在燃烧...

    **血脉燃烧！** 他怒吼着。
    """

    result = executor.execute(
        content=test_content,
        scene_type="战斗场景",
        primary_writer="剑尘",
        iteration=0,
    )

    print(f"评分: {result['scores']}")
    print(f"总分: {result['total_score']}")
    print(f"反馈:\n{result['feedback']}")
