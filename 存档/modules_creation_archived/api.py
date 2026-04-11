"""
创作模块 - 统一 API 接口
提供与 core/cli.py 对接的高层 API

功能：
1. 场景创作 - create_scene()
2. 章节创作 - create_chapter()
3. 评估功能 - evaluate_content()
4. 统计信息 - get_stats()
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from .workflow_scheduler import WorkflowScheduler, WorkflowResult
from .writer_executor import create_writer_executor_function
from .evaluator_executor import create_evaluator_executor_function


@dataclass
class CreationStats:
    """创作统计"""

    available_scenes: int
    active_scenes: int
    writers: int
    max_iterations: int


@dataclass
class SceneCreationResult:
    """场景创作结果"""

    success: bool
    scene_type: str
    chapter_name: str
    content: str
    iterations: int
    scores: Dict[str, int]
    feedback: str
    session_id: str


class CreationAPI:
    """
    创作模块统一 API

    提供与 CLI 对接的高层接口
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        max_iterations: int = 3,
        skill_caller: Optional[Callable] = None,
        auto_init: bool = True,
    ):
        """
        初始化创作 API

        Args:
            project_root: 项目根目录
            max_iterations: 最大迭代次数
            skill_caller: Skill 调用函数（用于实际调用 novelist-* skills）
            auto_init: 是否自动初始化调度器
        """
        self.project_root = project_root or Path("D:/动画/众生界")
        self.max_iterations = max_iterations
        self.skill_caller = skill_caller

        # 调度器（延迟初始化）
        self._scheduler: Optional[WorkflowScheduler] = None

        if auto_init:
            self._init_scheduler()

    def _init_scheduler(self) -> None:
        """初始化调度器"""
        if self._scheduler is not None:
            return

        # 创建执行器函数
        writer_executor = create_writer_executor_function(
            skill_caller=self.skill_caller,
            project_root=self.project_root,
        )

        evaluator_executor = create_evaluator_executor_function(
            skill_caller=self.skill_caller,
            project_root=self.project_root,
        )

        # 创建调度器
        self._scheduler = WorkflowScheduler(
            project_root=self.project_root,
            max_iterations=self.max_iterations,
            writer_executor=writer_executor,
            evaluator_executor=evaluator_executor,
        )

    def get_available_scenes(self) -> List[str]:
        """
        获取可用的场景类型列表

        Returns:
            场景类型列表
        """
        if not self._scheduler:
            self._init_scheduler()

        return self._scheduler.get_available_scenes()

    def get_scene_info(self, scene_type: str) -> Dict[str, Any]:
        """
        获取场景详细信息

        Args:
            scene_type: 场景类型

        Returns:
            场景信息字典
        """
        if not self._scheduler:
            self._init_scheduler()

        return self._scheduler.get_scene_info(scene_type)

    def create_scene(
        self,
        scene_type: str,
        chapter: str,
        outline: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> SceneCreationResult:
        """
        创作单个场景

        Args:
            scene_type: 场景类型
            chapter: 章节名称
            outline: 场景大纲
            context: 额外上下文

        Returns:
            场景创作结果
        """
        if not self._scheduler:
            self._init_scheduler()

        # 构建输入上下文
        input_context = {
            "outline": outline or "",
            **(context or {}),
        }

        # 执行工作流
        result = self._scheduler.execute_workflow(
            scene_type=scene_type,
            chapter_name=chapter,
            input_context=input_context,
        )

        # 提取评估分数
        scores = {}
        if result.evaluation_results:
            last_eval = result.evaluation_results[-1]
            scores = last_eval.scores

        # 提取反馈
        feedback = ""
        if result.evaluation_results:
            last_eval = result.evaluation_results[-1]
            feedback = last_eval.feedback

        return SceneCreationResult(
            success=result.success,
            scene_type=scene_type,
            chapter_name=chapter,
            content=result.final_content,
            iterations=result.iterations,
            scores=scores,
            feedback=feedback,
            session_id=result.session_id,
        )

    def create_chapter(
        self,
        chapter_name: str,
        chapter_outline: Dict[str, Any],
    ) -> List[SceneCreationResult]:
        """
        创作完整章节

        Args:
            chapter_name: 章节名称
            chapter_outline: 章节大纲（包含场景列表）

        Returns:
            各场景创作结果列表
        """
        if not self._scheduler:
            self._init_scheduler()

        # 执行章节工作流
        results = self._scheduler.execute_chapter_workflow(
            chapter_name=chapter_name,
            chapter_outline=chapter_outline,
        )

        # 转换为 SceneCreationResult
        scene_results = []
        for result in results:
            # 提取评估分数
            scores = {}
            if result.evaluation_results:
                last_eval = result.evaluation_results[-1]
                scores = last_eval.scores

            # 提取反馈
            feedback = ""
            if result.evaluation_results:
                last_eval = result.evaluation_results[-1]
                feedback = last_eval.feedback

            scene_results.append(
                SceneCreationResult(
                    success=result.success,
                    scene_type=result.scene_type,
                    chapter_name=result.chapter_name,
                    content=result.final_content,
                    iterations=result.iterations,
                    scores=scores,
                    feedback=feedback,
                    session_id=result.session_id,
                )
            )

        return scene_results

    def evaluate_content(
        self,
        content: str,
        scene_type: str,
        primary_writer: str = "unknown",
    ) -> Dict[str, Any]:
        """
        评估内容

        Args:
            content: 待评估内容
            scene_type: 场景类型
            primary_writer: 主责作家

        Returns:
            评估结果
        """
        if not self._scheduler:
            self._init_scheduler()

        # 使用调度器的评估执行器
        result = self._scheduler.evaluator_executor(
            content=content,
            scene_type=scene_type,
            primary_writer=primary_writer,
            iteration=0,
            thresholds=self._scheduler.EVALUATION_THRESHOLDS,
        )

        return result

    def get_stats(self) -> CreationStats:
        """
        获取创作模块统计信息

        Returns:
            创作统计
        """
        if not self._scheduler:
            self._init_scheduler()

        available_scenes = self._scheduler.get_available_scenes()

        return CreationStats(
            available_scenes=len(self._scheduler.scene_mapping),
            active_scenes=len(available_scenes),
            writers=len(self._scheduler.writer_definitions),
            max_iterations=self.max_iterations,
        )

    def shutdown(self) -> None:
        """关闭创作模块"""
        if self._scheduler:
            self._scheduler.shutdown()
            self._scheduler = None


def create_creation_api(
    project_root: Optional[Path] = None,
    max_iterations: int = 3,
    skill_caller: Optional[Callable] = None,
) -> CreationAPI:
    """
    创建创作 API 实例

    Args:
        project_root: 项目根目录
        max_iterations: 最大迭代次数
        skill_caller: Skill 调用函数

    Returns:
        创作 API 实例
    """
    return CreationAPI(
        project_root=project_root,
        max_iterations=max_iterations,
        skill_caller=skill_caller,
    )


# 使用示例
if __name__ == "__main__":
    # 创建 API
    api = create_creation_api()

    # 获取统计
    stats = api.get_stats()
    print(f"可用场景: {stats.available_scenes}")
    print(f"活跃场景: {stats.active_scenes}")
    print(f"作家数量: {stats.writers}")

    # 获取可用场景
    scenes = api.get_available_scenes()
    print(f"\n场景列表: {scenes[:5]}...")

    # 创作场景（模拟）
    result = api.create_scene(
        scene_type="战斗场景",
        chapter="第一章-天裂",
        outline="血牙面对血战，血脉力量觉醒...",
    )

    print(f"\n创作结果: {'成功' if result.success else '失败'}")
    print(f"迭代次数: {result.iterations}")
    print(f"内容长度: {len(result.content)} 字符")
