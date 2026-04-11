"""
作家执行器
集成 novelist-* skills，提供统一的作家调用接口

执行器负责：
1. 调用指定作家的 skill（novelist-canglan/xuanyi/moyan/jianchen/yunxi）
2. 构建标准化的输入上下文
3. 解析作家输出
"""

import json
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

# Skill 调用接口
# 注意：实际 skill 调用需要通过 OpenCode 的 skill 工具
# 这里提供接口定义和模拟实现


@dataclass
class WriterInput:
    """作家输入数据结构"""

    # 任务信息
    scene_id: str  # 场景ID
    task_type: str  # 任务类型（世界观设定、剧情编织、人物刻画、战斗设计、氛围营造）
    target_word_count: str  # 目标字数

    # 上下文
    existing_settings: str  # 已有设定
    relevant_outline: str  # 相关大纲
    previous_content: str  # 前文内容

    # 要求
    requirements: list  # 需要创作的元素
    plot_connection: str  # 与剧情的关联要求
    foreshadowing: list  # 需要埋设的伏笔

    # Phase 信息
    phase: str  # 当前 Phase（前置/核心/收尾）
    role: str  # 作家角色
    contribution: list  # 贡献项
    weight: float  # 权重

    # 迭代信息
    iteration: int  # 当前迭代次数
    previous_iteration_content: Optional[str] = None  # 上次迭代内容
    evaluation_feedback: Optional[str] = None  # 评估反馈


@dataclass
class WriterOutput:
    """作家输出数据结构"""

    scene_id: str
    task_type: str
    content: str  # 创作内容

    # 元数据
    actual_word_count: int
    new_settings: list  # 新增设定
    foreshadowing_planted: list  # 已埋设的伏笔
    pending_review: list  # 待审核项

    # 设定更新
    settings_updates: list  # 需要添加到设定文件的条目


# 作家任务类型映射
WRITER_TASK_TYPES = {
    "苍澜": ["世界观设定", "势力构建", "血脉体系", "代价设计"],
    "玄一": ["剧情编织", "伏笔设计", "悬念设置", "反转策划"],
    "墨言": ["人物刻画", "心理描写", "情感表达", "对话设计"],
    "剑尘": ["战斗设计", "功法体系", "冲突张力", "代价描写"],
    "云溪": ["氛围营造", "意境描写", "五感联动", "润色收尾"],
}

# 作家技能名称映射
WRITER_SKILL_NAMES = {
    "苍澜": "novelist-canglan",
    "玄一": "novelist-xuanyi",
    "墨言": "novelist-moyan",
    "剑尘": "novelist-jianchen",
    "云溪": "novelist-yunxi",
}


class WriterExecutor:
    """
    作家执行器

    负责调用 novelist-* skills 并管理输入输出
    """

    def __init__(
        self,
        skill_caller: Optional[Callable] = None,
        project_root: Optional[Path] = None,
    ):
        """
        初始化作家执行器

        Args:
            skill_caller: Skill 调用函数（需外部提供，实际调用 skill 工具）
            project_root: 项目根目录
        """
        self.skill_caller = skill_caller
        self.project_root = project_root or Path("D:/动画/众生界")

    def _build_writer_input(
        self,
        writer_name: str,
        scene_type: str,
        phase: str,
        input_context: Dict[str, Any],
    ) -> WriterInput:
        """
        构建作家输入

        Args:
            writer_name: 作家名称
            scene_type: 场景类型
            phase: Phase
            input_context: 输入上下文

        Returns:
            作家输入对象
        """
        # 提取上下文信息
        chapter_name = input_context.get("chapter_name", "")
        session_id = input_context.get("session_id", "")
        role = input_context.get("role", "")
        contribution = input_context.get("contribution", [])
        weight = input_context.get("weight", 0)
        iteration = input_context.get("iteration", 0)
        base_context = input_context.get("base_context", {})

        # 提取上下文
        existing_settings = base_context.get("existing_settings", "")
        relevant_outline = base_context.get("relevant_outline", "")
        previous_content = base_context.get("previous_content", "")
        requirements = base_context.get("requirements", [])
        plot_connection = base_context.get("plot_connection", "")
        foreshadowing = base_context.get("foreshadowing", [])

        # 迭代相关
        previous_iteration = input_context.get("previous_iteration", {})
        previous_content = previous_iteration.get("content", "")
        evaluation_feedback = ""
        if previous_iteration.get("evaluation"):
            evaluation_feedback = previous_iteration["evaluation"].feedback

        # 确定任务类型
        task_type = self._determine_task_type(writer_name, phase, contribution)

        # 目标字数
        target_word_count = self._estimate_target_words(phase, weight)

        return WriterInput(
            scene_id=f"{session_id}_{scene_type}_{phase}",
            task_type=task_type,
            target_word_count=target_word_count,
            existing_settings=existing_settings,
            relevant_outline=relevant_outline,
            previous_content=previous_content,
            requirements=requirements,
            plot_connection=plot_connection,
            foreshadowing=foreshadowing,
            phase=phase,
            role=role,
            contribution=contribution,
            weight=weight,
            iteration=iteration,
            previous_iteration_content=previous_content,
            evaluation_feedback=evaluation_feedback,
        )

    def _determine_task_type(
        self, writer_name: str, phase: str, contribution: list
    ) -> str:
        """
        确定任务类型

        Args:
            writer_name: 作家名称
            phase: Phase
            contribution: 贡献项列表

        Returns:
            任务类型字符串
        """
        task_types = WRITER_TASK_TYPES.get(writer_name, ["创作"])

        # 根据贡献项细化任务类型
        if contribution:
            first_contribution = contribution[0] if contribution else ""
            if "设定" in first_contribution or "世界观" in first_contribution:
                return task_types[0] if task_types else "世界观设定"
            elif "剧情" in first_contribution or "伏笔" in first_contribution:
                return task_types[1] if len(task_types) > 1 else "剧情编织"
            elif "人物" in first_contribution or "心理" in first_contribution:
                return task_types[2] if len(task_types) > 2 else "人物刻画"
            elif "战斗" in first_contribution or "冲突" in first_contribution:
                return task_types[3] if len(task_types) > 3 else "战斗设计"
            elif "氛围" in first_contribution or "意境" in first_contribution:
                return "氛围营造"

        return task_types[0] if task_types else "创作"

    def _estimate_target_words(self, phase: str, weight: float) -> str:
        """
        估算目标字数

        Args:
            phase: Phase
            weight: 权重

        Returns:
            目标字数字符串
        """
        # 基础字数（根据 Phase）
        base_words = {
            "前置": 300,
            "核心": 800,
            "收尾": 400,
        }

        base = base_words.get(phase, 500)

        # 根据权重调整
        adjusted = int(base * (0.5 + weight))

        return f"{adjusted}-{adjusted + 200}"

    def _format_skill_input(self, writer_input: WriterInput) -> Dict[str, Any]:
        """
        格式化 Skill 输入

        Args:
            writer_input: 作家输入对象

        Returns:
            Skill 输入字典
        """
        # 构建 YAML 格式的输入
        skill_input = {
            "任务信息": {
                "场景ID": writer_input.scene_id,
                "任务类型": writer_input.task_type,
                "目标字数": writer_input.target_word_count,
            },
            "上下文": {
                "已有设定": writer_input.existing_settings,
                "相关大纲": writer_input.relevant_outline,
                "前文内容": writer_input.previous_content,
            },
            "要求": {
                "需要创作的元素": writer_input.requirements,
                "与剧情的关联要求": writer_input.plot_connection,
                "需要埋设的伏笔": writer_input.foreshadowing,
            },
            "Phase信息": {
                "当前Phase": writer_input.phase,
                "作家角色": writer_input.role,
                "贡献项": writer_input.contribution,
                "权重": writer_input.weight,
            },
            "迭代信息": {
                "当前迭代次数": writer_input.iteration,
                "上次迭代内容": writer_input.previous_iteration_content or "无",
                "评估反馈": writer_input.evaluation_feedback or "无",
            },
        }

        return skill_input

    def execute(
        self,
        writer_name: str,
        writer_skill: str,
        scene_type: str,
        phase: str,
        input_context: Dict[str, Any],
    ) -> str:
        """
        执行作家创作

        Args:
            writer_name: 作家名称
            writer_skill: 作家技能名称
            scene_type: 场景类型
            phase: Phase
            input_context: 输入上下文

        Returns:
            创作内容
        """
        # 构建输入
        writer_input = self._build_writer_input(
            writer_name, scene_type, phase, input_context
        )

        # 格式化 Skill 输入
        skill_input = self._format_skill_input(writer_input)

        # 调用 Skill
        if self.skill_caller:
            # 实际调用
            result = self.skill_caller(
                skill_name=writer_skill,
                skill_input=skill_input,
            )

            # 解析输出
            if isinstance(result, dict):
                return result.get("content", result.get("输出", {}).get("内容", ""))

            return str(result)

        else:
            # 模拟调用（用于测试）
            return self._simulate_writer_execution(writer_name, writer_input)

    def _simulate_writer_execution(
        self, writer_name: str, writer_input: WriterInput
    ) -> str:
        """
        模拟作家执行（用于测试）

        Args:
            writer_name: 作家名称
            writer_input: 作家输入

        Returns:
            模拟的创作内容
        """
        # 生成模拟内容
        content = f"""
【{writer_name}】{writer_input.task_type} - Phase {writer_input.phase}

场景ID: {writer_input.scene_id}
任务类型: {writer_input.task_type}
目标字数: {writer_input.target_word_count}

贡献项: {", ".join(writer_input.contribution)}
权重: {writer_input.weight}

[创作内容示例]
{writer_name}正在创作{writer_input.task_type}相关内容...

根据已有设定: {writer_input.existing_settings[:100]}...
结合相关大纲: {writer_input.relevant_outline[:100]}...

迭代次数: {writer_input.iteration}
"""

        return content.strip()


def create_writer_executor_function(
    skill_caller: Optional[Callable] = None,
    project_root: Optional[Path] = None,
) -> Callable:
    """
    创建作家执行器函数（用于传递给 WorkflowScheduler）

    Args:
        skill_caller: Skill 调用函数
        project_root: 项目根目录

    Returns:
        作家执行器函数
    """
    executor = WriterExecutor(skill_caller=skill_caller, project_root=project_root)

    def writer_executor_function(
        writer_name: str,
        writer_skill: str,
        scene_type: str,
        phase: str,
        input_context: Dict[str, Any],
    ) -> str:
        """作家执行器函数"""
        return executor.execute(
            writer_name=writer_name,
            writer_skill=writer_skill,
            scene_type=scene_type,
            phase=phase,
            input_context=input_context,
        )

    return writer_executor_function


# 使用示例
if __name__ == "__main__":
    # 创建执行器
    executor = WriterExecutor()

    # 测试执行
    result = executor.execute(
        writer_name="苍澜",
        writer_skill="novelist-canglan",
        scene_type="战斗场景",
        phase="前置",
        input_context={
            "chapter_name": "第一章-天裂",
            "session_id": "test_session",
            "role": "世界观输入",
            "contribution": ["力量体系约束", "血脉代价设定"],
            "weight": 0.15,
            "iteration": 0,
            "base_context": {
                "existing_settings": "血脉者拥有血脉力量...",
                "relevant_outline": "主角血牙将面临血战...",
            },
        },
    )

    print(result)
