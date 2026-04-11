"""
并行执行管理器
管理多作家并行创作，支持超时控制和失败重试
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError


@dataclass
class ParallelConfig:
    """并行执行配置"""

    max_parallel_writers: int = 3
    timeout_per_writer: int = 300  # 秒
    retry_on_failure: bool = True
    max_retries: int = 2
    retry_delay: int = 5  # 秒


@dataclass
class WriterTask:
    """作家任务"""

    task_id: str
    writer_name: str
    writer_skill: str
    scene_type: str
    phase: str
    input_context: Dict[str, Any]
    output: Optional[str] = None
    success: bool = False
    execution_time: float = 0.0
    retry_count: int = 0


class ParallelExecutionManager:
    """
    并行执行管理器

    功能：
    1. 管理多作家并行执行
    2. 超时控制（每个作家独立超时）
    3. 失败重试（可配置重试次数）
    4. 执行结果汇总
    """

    def __init__(self, config: Optional[ParallelConfig] = None):
        """
        初始化并行执行管理器

        Args:
            config: 并行执行配置
        """
        self.config = config or ParallelConfig()
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_parallel_writers)
        self.completed_tasks: List[WriterTask] = []
        self.failed_tasks: List[WriterTask] = []

    def _execute_writer_task(
        self, task: WriterTask, writer_function: Callable
    ) -> WriterTask:
        """
        执行单个作家任务

        Args:
            task: 作家任务对象
            writer_function: 作家执行函数

        Returns:
            完成的任务对象
        """
        start_time = time.time()

        try:
            # 执行作家函数
            output = writer_function(
                writer_name=task.writer_name,
                writer_skill=task.writer_skill,
                scene_type=task.scene_type,
                phase=task.phase,
                input_context=task.input_context,
            )

            # 标记成功
            task.output = output
            task.success = True
            task.execution_time = time.time() - start_time

            print(
                f"✅ 作家任务完成: {task.writer_name} - {task.scene_type} - Phase {task.phase} (耗时 {task.execution_time:.2f}s)"
            )

        except Exception as e:
            # 标记失败
            task.success = False
            task.execution_time = time.time() - start_time

            print(f"❌ 作家任务失败: {task.writer_name} - {e}")

            # 重试逻辑
            if (
                self.config.retry_on_failure
                and task.retry_count < self.config.max_retries
            ):
                task.retry_count += 1
                print(f"🔄 重试任务 (第{task.retry_count}次): {task.writer_name}")

                # 等待重试延迟
                time.sleep(self.config.retry_delay)

                # 重新执行
                return self._execute_writer_task(task, writer_function)

        return task

    def execute_parallel_tasks(
        self, tasks: List[WriterTask], writer_function: Callable
    ) -> Dict[str, List[WriterTask]]:
        """
        并行执行多个作家任务

        Args:
            tasks: 任务列表
            writer_function: 作家执行函数

        Returns:
            任务结果字典（completed/failed）
        """
        print(f"🚀 开始并行执行 {len(tasks)} 个作家任务")
        print(
            f"配置: max_parallel={self.config.max_parallel_writers}, timeout={self.config.timeout_per_writer}s"
        )

        # 清空历史记录
        self.completed_tasks = []
        self.failed_tasks = []

        # 提交所有任务到线程池
        futures = []
        for task in tasks:
            future = self.executor.submit(
                self._execute_writer_task, task, writer_function
            )
            futures.append((task, future))

        # 等待所有任务完成（带超时）
        for task, future in futures:
            try:
                # 每个任务独立超时
                completed_task = future.result(timeout=self.config.timeout_per_writer)

                if completed_task.success:
                    self.completed_tasks.append(completed_task)
                else:
                    self.failed_tasks.append(completed_task)

            except FuturesTimeoutError:
                # 超时处理
                task.success = False
                task.execution_time = self.config.timeout_per_writer
                self.failed_tasks.append(task)

                print(f"⏰ 作家任务超时: {task.writer_name} - {task.scene_type}")

            except Exception as e:
                # 其他异常
                task.success = False
                self.failed_tasks.append(task)

                print(f"❌ 作家任务异常: {task.writer_name} - {e}")

        # 汇总结果
        print(f"\n📊 执行结果汇总:")
        print(f"✅ 成功: {len(self.completed_tasks)} 个")
        print(f"❌ 失败: {len(self.failed_tasks)} 个")

        return {"completed": self.completed_tasks, "failed": self.failed_tasks}

    def execute_phase_sequence(
        self,
        phase_tasks: Dict[
            str, List[WriterTask]
        ],  # {"前置": [...], "核心": [...], "收尾": [...]}
        writer_function: Callable,
    ) -> Dict[str, Dict[str, List[WriterTask]]]:
        """
        按Phase顺序执行任务（每个Phase内并行）

        Args:
            phase_tasks: 按Phase分组的任务字典
            writer_function: 作家执行函数

        Returns:
            按Phase分组的执行结果
        """
        results = {}

        # 按Phase顺序执行（前置 → 核心 → 收尾）
        phase_order = ["前置", "核心", "收尾"]

        for phase in phase_order:
            if phase in phase_tasks:
                print(f"\n▶ 执行 Phase: {phase}")

                tasks = phase_tasks[phase]
                phase_result = self.execute_parallel_tasks(tasks, writer_function)

                results[phase] = phase_result

                # 如果某个Phase全部失败，可以选择中断
                if len(phase_result["failed"]) == len(tasks):
                    print(f"⚠️ Phase {phase} 全部失败，后续Phase可能受影响")

        return results

    def get_execution_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要

        Returns:
            执行摘要字典
        """
        total_tasks = len(self.completed_tasks) + len(self.failed_tasks)

        avg_execution_time = 0.0
        if self.completed_tasks:
            avg_execution_time = sum(
                t.execution_time for t in self.completed_tasks
            ) / len(self.completed_tasks)

        return {
            "total_tasks": total_tasks,
            "completed_count": len(self.completed_tasks),
            "failed_count": len(self.failed_tasks),
            "success_rate": len(self.completed_tasks) / total_tasks
            if total_tasks > 0
            else 0,
            "avg_execution_time": avg_execution_time,
            "config": {
                "max_parallel_writers": self.config.max_parallel_writers,
                "timeout_per_writer": self.config.timeout_per_writer,
                "retry_on_failure": self.config.retry_on_failure,
            },
        }

    def shutdown(self) -> None:
        """关闭执行器"""
        self.executor.shutdown(wait=True)
        print("✅ 并行执行器已关闭")


# 使用示例
if __name__ == "__main__":
    # 示例作家执行函数
    def example_writer_function(
        writer_name, writer_skill, scene_type, phase, input_context
    ):
        """示例作家函数"""
        # 模拟创作过程
        time.sleep(2)  # 模拟耗时

        # 返回创作内容
        return f"[{writer_name}] {scene_type} - {phase} - 创作内容示例"

    # 创建并行执行管理器
    config = ParallelConfig(
        max_parallel_writers=3, timeout_per_writer=10, retry_on_failure=True
    )
    manager = ParallelExecutionManager(config)

    # 创建任务
    tasks = [
        WriterTask(
            task_id="task_001",
            writer_name="苍澜",
            writer_skill="novelist-canglan",
            scene_type="世界观",
            phase="前置",
            input_context={"chapter": "第一章"},
        ),
        WriterTask(
            task_id="task_002",
            writer_name="玄一",
            writer_skill="novelist-xuanyi",
            scene_type="剧情",
            phase="核心",
            input_context={"chapter": "第一章"},
        ),
        WriterTask(
            task_id="task_003",
            writer_name="墨言",
            writer_skill="novelist-moyan",
            scene_type="人物",
            phase="核心",
            input_context={"chapter": "第一章"},
        ),
    ]

    # 并行执行
    results = manager.execute_parallel_tasks(tasks, example_writer_function)

    # 获取摘要
    summary = manager.get_execution_summary()
    print(f"\n摘要: {summary}")

    # 关闭执行器
    manager.shutdown()
