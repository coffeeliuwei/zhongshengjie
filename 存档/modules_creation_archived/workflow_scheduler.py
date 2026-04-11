"""
工作流调度器
基于 scene_writer_mapping.json 的场景-作家协作配置，
实现 Generator/Evaluator 分离的创作工作流。

设计原则：
1. Generator/Evaluator分离 - 创作家不自我评估
2. Phase分层执行 - 前置→核心→收尾
3. 迭代反馈 - 最多3次迭代优化
4. 硬性阈值 - 技法评分达标即通过
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from .writer_context_manager import WriterContextManager, WriterOutput
from .parallel_execution_manager import (
    ParallelExecutionManager,
    ParallelConfig,
    WriterTask,
)


class Phase(Enum):
    """执行Phase枚举"""

    PRE = "前置"  # 设定输入
    CORE = "核心"  # 主要创作
    POST = "收尾"  # 润色输出


class EvaluationStatus(Enum):
    """评估状态枚举"""

    PASS = "pass"
    FAIL = "fail"
    NEEDS_ITERATION = "needs_iteration"


@dataclass
class SceneConfig:
    """场景配置数据结构"""

    scene_type: str
    description: str
    collaboration: List[Dict[str, Any]]
    workflow_order: List[str]
    primary_writer: str
    case_library_filter: Dict[str, Any]
    status: str = "active"


@dataclass
class WriterConfig:
    """作家配置数据结构"""

    name: str
    role: str
    specialty: List[str]
    primary_dimension: str
    phase_preference: str
    skill_name: str
    dual_role: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """评估结果数据结构"""

    status: EvaluationStatus
    scores: Dict[str, int]
    total_score: float
    feedback: str
    iteration_needed: bool = False
    passed_thresholds: Dict[str, bool] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """工作流结果数据结构"""

    session_id: str
    chapter_name: str
    scene_type: str
    final_content: str
    iterations: int
    evaluation_results: List[EvaluationResult]
    writer_outputs: List[WriterOutput]
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowScheduler:
    """
    工作流调度器

    功能：
    1. 加载场景-作家映射配置
    2. Phase分层执行（前置→核心→收尾）
    3. 作家技能调用（novelist-*）
    4. 迭代循环控制（max_iterations=3）
    5. 评估集成（novelist-evaluator）
    6. 上下文管理
    7. 并行执行支持
    """

    # 评估阈值（来自CONFIG.md）
    EVALUATION_THRESHOLDS = {
        "世界自洽": 7,
        "人物立体": 6,
        "情感真实": 6,
        "战斗逻辑": 6,
        "文风克制": 6,
        "剧情张力": 6,
    }

    # 作家技能映射
    WRITER_SKILLS = {
        "苍澜": "novelist-canglan",
        "玄一": "novelist-xuanyi",
        "墨言": "novelist-moyan",
        "剑尘": "novelist-jianchen",
        "云溪": "novelist-yunxi",
    }

    # Evaluator技能
    EVALUATOR_SKILL = "novelist-evaluator"

    def __init__(
        self,
        project_root: Path,
        max_iterations: int = 3,
        context_manager: Optional[WriterContextManager] = None,
        parallel_manager: Optional[ParallelExecutionManager] = None,
        writer_executor: Optional[Callable] = None,
        evaluator_executor: Optional[Callable] = None,
    ):
        """
        初始化工作流调度器

        Args:
            project_root: 项目根目录
            max_iterations: 最大迭代次数（默认3次）
            context_manager: 上下文管理器（可选，自动创建）
            parallel_manager: 并行执行管理器（可选，自动创建）
            writer_executor: 作家执行函数（需外部提供，调用skill）
            evaluator_executor: 评估执行函数（需外部提供，调用skill）
        """
        self.project_root = project_root
        self.max_iterations = max_iterations

        # 加载配置
        self.scene_mapping = self._load_scene_mapping()
        self.writer_definitions = self._extract_writer_definitions()

        # 初始化管理器
        self.context_manager = context_manager or self._create_context_manager()
        self.parallel_manager = parallel_manager or self._create_parallel_manager()

        # 执行器（需外部提供，用于调用skill）
        self.writer_executor = writer_executor
        self.evaluator_executor = evaluator_executor

        print(f"✅ WorkflowScheduler 初始化完成")
        print(f"   场景配置: {len(self.scene_mapping)} 种")
        print(f"   作家配置: {len(self.writer_definitions)} 位")
        print(f"   最大迭代: {max_iterations} 次")

    def _load_scene_mapping(self) -> Dict[str, SceneConfig]:
        """
        加载场景-作家映射配置

        Returns:
            场景配置字典
        """
        mapping_path = self.project_root / ".vectorstore" / "scene_writer_mapping.json"

        if not mapping_path.exists():
            raise FileNotFoundError(f"场景映射文件不存在: {mapping_path}")

        with open(mapping_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 解析场景配置
        scene_configs = {}
        for scene_type, config in data.get("scene_writer_mapping", {}).items():
            scene_configs[scene_type] = SceneConfig(
                scene_type=scene_type,
                description=config.get("description", ""),
                collaboration=config.get("collaboration", []),
                workflow_order=config.get("workflow_order", []),
                primary_writer=config.get("primary_writer", ""),
                case_library_filter=config.get("case_library_filter", {}),
                status=config.get("status", "active"),
            )

        return scene_configs

    def _extract_writer_definitions(self) -> Dict[str, WriterConfig]:
        """
        从配置中提取作家定义

        Returns:
            作家配置字典
        """
        mapping_path = self.project_root / ".vectorstore" / "scene_writer_mapping.json"

        with open(mapping_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        writer_defs = {}
        for name, config in data.get("writer_definitions", {}).items():
            skill_name = self.WRITER_SKILLS.get(name, f"novelist-{name.lower()}")
            writer_defs[name] = WriterConfig(
                name=name,
                role=config.get("role", ""),
                specialty=config.get("specialty", []),
                primary_dimension=config.get("primary_dimension", ""),
                phase_preference=config.get("phase_preference", ""),
                skill_name=skill_name,
                dual_role=config.get("dual_role", []),
            )

        return writer_defs

    def _create_context_manager(self) -> WriterContextManager:
        """创建上下文管理器"""
        return WriterContextManager(
            qdrant_host="localhost",
            qdrant_port=6333,
            max_context_entries=100,
            auto_cleanup_days=30,
        )

    def _create_parallel_manager(self) -> ParallelExecutionManager:
        """创建并行执行管理器"""
        config = ParallelConfig(
            max_parallel_writers=3,
            timeout_per_writer=300,
            retry_on_failure=True,
            max_retries=2,
        )
        return ParallelExecutionManager(config)

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}_{uuid.uuid4().hex[:8]}"

    def get_scene_config(self, scene_type: str) -> Optional[SceneConfig]:
        """
        获取指定场景类型的配置

        Args:
            scene_type: 场景类型名称

        Returns:
            场景配置对象
        """
        return self.scene_mapping.get(scene_type)

    def get_writer_config(self, writer_name: str) -> Optional[WriterConfig]:
        """
        获取指定作家的配置

        Args:
            writer_name: 作家名称

        Returns:
            作家配置对象
        """
        return self.writer_definitions.get(writer_name)

    def _build_phase_tasks(
        self,
        scene_config: SceneConfig,
        chapter_name: str,
        session_id: str,
        input_context: Dict[str, Any],
        iteration: int = 0,
    ) -> Dict[str, List[WriterTask]]:
        """
        构建按Phase分组的任务列表

        Args:
            scene_config: 场景配置
            chapter_name: 章节名称
            session_id: 会话ID
            input_context: 输入上下文
            iteration: 当前迭代次数

        Returns:
            按Phase分组的任务字典
        """
        phase_tasks = {
            Phase.PRE.value: [],
            Phase.CORE.value: [],
            Phase.POST.value: [],
        }

        # 遍历协作配置
        for collab in scene_config.collaboration:
            writer_name = collab.get("writer", "")
            phase = collab.get("phase", "")
            role = collab.get("role", "")
            contribution = collab.get("contribution", [])
            weight = collab.get("weight", 0)

            # 获取作家配置
            writer_config = self.get_writer_config(writer_name)
            if not writer_config:
                print(f"⚠️ 作家配置未找到: {writer_name}")
                continue

            # 构建任务
            task = WriterTask(
                task_id=f"task_{uuid.uuid4().hex[:8]}",
                writer_name=writer_name,
                writer_skill=writer_config.skill_name,
                scene_type=scene_config.scene_type,
                phase=phase,
                input_context={
                    "chapter_name": chapter_name,
                    "session_id": session_id,
                    "scene_type": scene_config.scene_type,
                    "role": role,
                    "contribution": contribution,
                    "weight": weight,
                    "iteration": iteration,
                    "base_context": input_context,
                },
            )

            phase_tasks[phase].append(task)

        return phase_tasks

    def _execute_writer_phase(
        self,
        phase_tasks: Dict[str, List[WriterTask]],
        session_id: str,
        chapter_name: str,
    ) -> Dict[str, List[WriterOutput]]:
        """
        执行作家Phase（使用ParallelExecutionManager）

        Args:
            phase_tasks: 按Phase分组的任务
            session_id: 会话ID
            chapter_name: 章节名称

        Returns:
            按Phase分组的作家输出
        """
        if not self.writer_executor:
            raise ValueError("writer_executor 未设置，无法执行作家任务")

        # 执行Phase序列
        results = self.parallel_manager.execute_phase_sequence(
            phase_tasks, self.writer_executor
        )

        # 转换为WriterOutput并保存
        phase_outputs = {}
        for phase, phase_result in results.items():
            outputs = []
            for task in phase_result.get("completed", []):
                if task.success and task.output:
                    # 创建WriterOutput
                    output = WriterOutput(
                        output_id=task.task_id,
                        session_id=session_id,
                        chapter_name=chapter_name,
                        scene_type=task.scene_type,
                        phase=task.phase,
                        writer_name=task.writer_name,
                        writer_skill=task.writer_skill,
                        content=task.output,
                        timestamp=datetime.now().isoformat(),
                        iteration=task.input_context.get("iteration", 0),
                        metadata={
                            "role": task.input_context.get("role", ""),
                            "weight": task.input_context.get("weight", 0),
                            "execution_time": task.execution_time,
                        },
                    )

                    # 保存到上下文管理器
                    self.context_manager.save_writer_output(output)

                    outputs.append(output)

            phase_outputs[phase] = outputs

        return phase_outputs

    def _aggregate_phase_outputs(
        self,
        phase_outputs: Dict[str, List[WriterOutput]],
        scene_config: SceneConfig,
    ) -> str:
        """
        聚合各Phase输出，生成最终内容

        Args:
            phase_outputs: 各Phase的作家输出
            scene_config: 场景配置

        Returns:
            聚合后的内容
        """
        # 按workflow_order排序
        aggregated_parts = []

        for writer_name in scene_config.workflow_order:
            # 在所有Phase中找到该作家的输出
            for phase, outputs in phase_outputs.items():
                for output in outputs:
                    if output.writer_name == writer_name:
                        # 根据权重添加
                        weight = output.metadata.get("weight", 0)
                        aggregated_parts.append(
                            {
                                "writer": writer_name,
                                "phase": phase,
                                "weight": weight,
                                "content": output.content,
                            }
                        )

        # 简化聚合：直接拼接内容
        # TODO: 更智能的聚合策略（权重加权、内容融合）
        final_content = "\n\n".join(
            [
                f"【{p['writer']} - {p['phase']}】\n{p['content']}"
                for p in aggregated_parts
            ]
        )

        return final_content

    def _execute_evaluation(
        self,
        content: str,
        scene_config: SceneConfig,
        iteration: int,
    ) -> EvaluationResult:
        """
        执行评估（调用novelist-evaluator）

        Args:
            content: 待评估内容
            scene_config: 场景配置
            iteration: 当前迭代次数

        Returns:
            评估结果
        """
        if not self.evaluator_executor:
            # 无评估器时返回默认通过
            return EvaluationResult(
                status=EvaluationStatus.PASS,
                scores={},
                total_score=0,
                feedback="评估器未设置，默认通过",
                iteration_needed=False,
            )

        # 调用评估器
        eval_result = self.evaluator_executor(
            content=content,
            scene_type=scene_config.scene_type,
            primary_writer=scene_config.primary_writer,
            iteration=iteration,
            thresholds=self.EVALUATION_THRESHOLDS,
        )

        # 解析评估结果
        scores = eval_result.get("scores", {})
        total_score = sum(scores.values()) / len(scores) if scores else 0
        feedback = eval_result.get("feedback", "")

        # 检查阈值
        passed_thresholds = {}
        all_passed = True

        for dimension, threshold in self.EVALUATION_THRESHOLDS.items():
            score = scores.get(dimension, 0)
            passed = score >= threshold
            passed_thresholds[dimension] = passed
            if not passed:
                all_passed = False

        # 确定状态
        if all_passed:
            status = EvaluationStatus.PASS
            iteration_needed = False
        elif iteration < self.max_iterations - 1:
            status = EvaluationStatus.NEEDS_ITERATION
            iteration_needed = True
        else:
            status = EvaluationStatus.FAIL
            iteration_needed = False

        return EvaluationResult(
            status=status,
            scores=scores,
            total_score=total_score,
            feedback=feedback,
            iteration_needed=iteration_needed,
            passed_thresholds=passed_thresholds,
        )

    def execute_workflow(
        self,
        scene_type: str,
        chapter_name: str,
        input_context: Dict[str, Any],
    ) -> WorkflowResult:
        """
        执行完整工作流

        Args:
            scene_type: 场景类型
            chapter_name: 章节名称
            input_context: 输入上下文（大纲、设定等）

        Returns:
            工作流结果
        """
        # 获取场景配置
        scene_config = self.get_scene_config(scene_type)
        if not scene_config:
            raise ValueError(f"场景类型未配置: {scene_type}")

        if scene_config.status != "active":
            print(f"⚠️ 场景状态: {scene_config.status}")

        # 生成会话ID
        session_id = self._generate_session_id()

        print(f"\n{'=' * 60}")
        print(f"🚀 工作流启动")
        print(f"   场景类型: {scene_type}")
        print(f"   章节名称: {chapter_name}")
        print(f"   会话ID: {session_id}")
        print(f"   主责作家: {scene_config.primary_writer}")
        print(f"{'=' * 60}\n")

        # 迭代循环
        iterations = 0
        all_outputs = []
        all_evaluations = []
        final_content = ""
        success = False

        while iterations < self.max_iterations:
            print(f"\n▶ 迭代 {iterations + 1}/{self.max_iterations}")

            # 构建任务
            phase_tasks = self._build_phase_tasks(
                scene_config,
                chapter_name,
                session_id,
                input_context,
                iteration=iterations,
            )

            # 执行作家Phase
            phase_outputs = self._execute_writer_phase(
                phase_tasks, session_id, chapter_name
            )

            # 聚合输出
            final_content = self._aggregate_phase_outputs(phase_outputs, scene_config)

            # 收集输出
            for outputs in phase_outputs.values():
                all_outputs.extend(outputs)

            # 执行评估
            print(f"\n▶ 执行评估...")
            eval_result = self._execute_evaluation(
                final_content, scene_config, iterations
            )
            all_evaluations.append(eval_result)

            # 检查结果
            print(f"\n📊 评估结果:")
            print(f"   状态: {eval_result.status.value}")
            print(f"   总分: {eval_result.total_score:.2f}")
            print(f"   反馈: {eval_result.feedback[:100]}...")

            for dimension, passed in eval_result.passed_thresholds.items():
                status_icon = "✅" if passed else "❌"
                print(
                    f"   {status_icon} {dimension}: {eval_result.scores.get(dimension, 0)}"
                )

            if eval_result.status == EvaluationStatus.PASS:
                print(f"\n✅ 工作流完成 - 评估通过")
                success = True
                break

            elif eval_result.status == EvaluationStatus.FAIL:
                print(f"\n❌ 工作流完成 - 达到最大迭代仍未通过")
                break

            else:
                print(f"\n🔄 需要迭代优化...")
                # 更新输入上下文（加入评估反馈）
                input_context["previous_iteration"] = {
                    "content": final_content,
                    "evaluation": eval_result,
                    "iteration": iterations,
                }
                iterations += 1

        # 返回结果
        return WorkflowResult(
            session_id=session_id,
            chapter_name=chapter_name,
            scene_type=scene_type,
            final_content=final_content,
            iterations=iterations + 1,
            evaluation_results=all_evaluations,
            writer_outputs=all_outputs,
            success=success,
            metadata={
                "scene_config": scene_config,
                "primary_writer": scene_config.primary_writer,
                "workflow_order": scene_config.workflow_order,
            },
        )

    def execute_chapter_workflow(
        self,
        chapter_name: str,
        chapter_outline: Dict[str, Any],
    ) -> List[WorkflowResult]:
        """
        执行章节完整工作流（遍历所有场景）

        Args:
            chapter_name: 章节名称
            chapter_outline: 章节大纲（包含场景列表）

        Returns:
            各场景的工作流结果列表
        """
        results = []

        # 提取场景列表
        scenes = chapter_outline.get("scenes", [])

        print(f"\n{'=' * 60}")
        print(f"📖 章节工作流启动")
        print(f"   章节: {chapter_name}")
        print(f"   场景数: {len(scenes)}")
        print(f"{'=' * 60}\n")

        for scene in scenes:
            scene_type = scene.get("type", "")
            scene_context = scene.get("context", {})

            # 合并上下文
            input_context = {
                "chapter_outline": chapter_outline,
                "scene_outline": scene,
                **scene_context,
            }

            # 执行场景工作流
            result = self.execute_workflow(
                scene_type=scene_type,
                chapter_name=chapter_name,
                input_context=input_context,
            )

            results.append(result)

        # 汇总
        success_count = sum(1 for r in results if r.success)
        print(f"\n{'=' * 60}")
        print(f"📊 章节工作流完成")
        print(f"   成功: {success_count}/{len(results)}")
        print(f"{'=' * 60}")

        return results

    def get_available_scenes(self) -> List[str]:
        """
        获取可用的场景类型列表

        Returns:
            场景类型列表
        """
        active_scenes = [
            name
            for name, config in self.scene_mapping.items()
            if config.status == "active"
        ]
        return sorted(active_scenes)

    def get_scene_info(self, scene_type: str) -> Dict[str, Any]:
        """
        获取场景详细信息

        Args:
            scene_type: 场景类型

        Returns:
            场景信息字典
        """
        config = self.get_scene_config(scene_type)
        if not config:
            return {}

        return {
            "scene_type": config.scene_type,
            "description": config.description,
            "status": config.status,
            "primary_writer": config.primary_writer,
            "workflow_order": config.workflow_order,
            "collaboration_count": len(config.collaboration),
            "writers": [c.get("writer") for c in config.collaboration],
        }

    def shutdown(self) -> None:
        """关闭调度器"""
        if self.parallel_manager:
            self.parallel_manager.shutdown()
        print("✅ WorkflowScheduler 已关闭")


# 使用示例
if __name__ == "__main__":
    from pathlib import Path

    # 示例作家执行函数（实际需调用skill）
    def example_writer_executor(
        writer_name, writer_skill, scene_type, phase, input_context
    ):
        """示例作家执行器"""
        return f"[{writer_name}] {scene_type} - {phase} 阶段创作内容..."

    # 示例评估执行函数
    def example_evaluator_executor(
        content, scene_type, primary_writer, iteration, thresholds
    ):
        """示例评估执行器"""
        return {
            "scores": {"世界自洽": 7, "人物立体": 6, "情感真实": 6},
            "feedback": "内容整体符合要求，细节描写到位。",
        }

    # 初始化调度器
    project_root = Path(__file__).parent.parent.parent
    scheduler = WorkflowScheduler(
        project_root=project_root,
        max_iterations=3,
        writer_executor=example_writer_executor,
        evaluator_executor=example_evaluator_executor,
    )

    # 获取可用场景
    scenes = scheduler.get_available_scenes()
    print(f"可用场景: {scenes[:5]}...")

    # 执行场景工作流
    result = scheduler.execute_workflow(
        scene_type="战斗场景",
        chapter_name="第一章-天裂",
        input_context={"outline": "场景大纲内容..."},
    )

    print(f"\n结果: {result.success}")

    # 关闭
    scheduler.shutdown()
