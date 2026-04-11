"""
创作模块 - 入口文件
提供作家工作流和上下文管理功能

核心组件：
- WorkflowScheduler: 工作流调度器（核心）
- WriterContextManager: 作家上下文管理器
- ParallelExecutionManager: 并行执行管理器
- WriterExecutor: 作家执行器
- EvaluatorExecutor: 评估执行器
- ExperienceRetriever: 章节经验检索器
- ConflictDetector: 一致性检测器
- ConflictFusionGuide: 冲突融合指南生成器
- CreationMode: 创作模式（并行+智能融合）
- IterationPredictor: 迭代风险预测器
- QuickFailChecker: 快速失败检查器
- YunxiFusionPolisher: 云溪融合润色合并器

使用方式：
    from modules.creation import WorkflowScheduler, create_creation_api

    # 方式1：直接使用调度器
    scheduler = WorkflowScheduler(project_root=Path("D:/动画/众生界"))
    result = scheduler.execute_workflow(
        scene_type="战斗场景",
        chapter_name="第一章-天裂",
        input_context={"outline": "..."}
    )

    # 方式2：使用统一 API
    api = create_creation_api()
    result = api.create_scene(scene_type="战斗场景", chapter="第一章-天裂")

    # 方式3：使用迭代预测器
    from modules.creation import IterationPredictor
    predictor = IterationPredictor()
    prediction = predictor.predict(scene_type="战斗场景", scene_description="...")

    # 方式4：使用云溪融合润色合并器
    from modules.creation import YunxiFusionPolisher, fuse_and_polish
    result = fuse_and_polish(phase1_worldview, phase1_plot, phase1_character, conflicts)
"""

from .writer_context_manager import (
    WriterContextManager,
    WriterOutput as ContextWriterOutput,
)
from .parallel_execution_manager import (
    ParallelExecutionManager,
    ParallelConfig,
    WriterTask,
)
from .workflow_scheduler import (
    WorkflowScheduler,
    WorkflowResult,
    SceneConfig,
    WriterConfig,
    EvaluationResult,
    EvaluationStatus,
    Phase,
)
from .writer_executor import (
    WriterExecutor,
    WriterInput,
    WriterOutput as ExecutorWriterOutput,
    create_writer_executor_function,
)
from .evaluator_executor import (
    EvaluatorExecutor,
    EvaluationOutput,
    create_evaluator_executor_function,
)
from .api import (
    CreationAPI,
    CreationStats,
    SceneCreationResult,
    create_creation_api,
)
from .experience_retriever import (
    ExperienceRetriever,
    retrieve_chapter_experience,
    format_experience_context,
    write_chapter_log,
)
from .conflict_detector import (
    ConflictDetector,
    ConflictFusionGuide,
    Conflict,
    ConflictSeverity,
    ConflictType,
    detect_conflicts,
    generate_fusion_guide,
)
from .creation_mode import (
    CreationMode,
    FusionStrategy,
    FusionRule,
    FusionResult,
    AUTO_FUSION_RULES,
    create_creation_mode,
    determine_fusion_strategy,
    auto_fuse_conflicts,
)
from .iteration_optimizer import (
    IterationPredictor,
    IterationPrediction,
    IterationRisk,
    SceneComplexity,
    QuickFailChecker,
    PhaseQualityCheck,
    DynamicIterationAdjuster,
    predict_iteration_risk,
    check_phase_quality,
)
from .yunxi_fusion_polisher import (
    YunxiFusionPolisher,
    FusionPolishMode,
    FusionPolishInput,
    FusionPolishOutput,
    fuse_and_polish,
)

__all__ = [
    # 核心调度器
    "WorkflowScheduler",
    "WorkflowResult",
    "SceneConfig",
    "WriterConfig",
    "EvaluationResult",
    "EvaluationStatus",
    "Phase",
    # 上下文管理
    "WriterContextManager",
    "ContextWriterOutput",
    # 并行执行
    "ParallelExecutionManager",
    "ParallelConfig",
    "WriterTask",
    # 作家执行
    "WriterExecutor",
    "WriterInput",
    "ExecutorWriterOutput",
    "create_writer_executor_function",
    # 评估执行
    "EvaluatorExecutor",
    "EvaluationOutput",
    "create_evaluator_executor_function",
    # 统一 API
    "CreationAPI",
    "CreationStats",
    "SceneCreationResult",
    "create_creation_api",
    # 经验检索
    "ExperienceRetriever",
    "retrieve_chapter_experience",
    "format_experience_context",
    "write_chapter_log",
    # 冲突检测
    "ConflictDetector",
    "ConflictFusionGuide",
    "Conflict",
    "ConflictSeverity",
    "ConflictType",
    "detect_conflicts",
    "generate_fusion_guide",
    # 创作模式（并行+智能融合）
    "CreationMode",
    "FusionStrategy",
    "FusionRule",
    "FusionResult",
    "AUTO_FUSION_RULES",
    "create_creation_mode",
    "determine_fusion_strategy",
    "auto_fuse_conflicts",
    # 迭代优化
    "IterationPredictor",
    "IterationPrediction",
    "IterationRisk",
    "SceneComplexity",
    "QuickFailChecker",
    "PhaseQualityCheck",
    "DynamicIterationAdjuster",
    "predict_iteration_risk",
    "check_phase_quality",
    # 云溪融合润色
    "YunxiFusionPolisher",
    "FusionPolishMode",
    "FusionPolishInput",
    "FusionPolishOutput",
    "fuse_and_polish",
]
