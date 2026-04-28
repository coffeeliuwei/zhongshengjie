#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作流状态检查器
================

检查和管理工作流状态，支持中断恢复。

核心功能：
- 检查未完成的工作流
- 保存工作流状态
- 生成恢复提示
- 状态清理

参考：统一提炼引擎重构方案.md 第10.3.3节
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class WorkflowState:
    """工作流状态"""

    workflow_id: str
    workflow_type: str  # "chapter_creation", "data_extraction", "setting_update"
    current_phase: int
    total_phases: int
    chapter: Optional[int] = None
    scene_progress: Optional[Dict[str, int]] = None  # {"current": 1, "total": 5}
    started_at: Optional[str] = None
    last_activity: Optional[str] = None
    can_resume: bool = True
    metadata: Optional[Dict[str, Any]] = None


class WorkflowStateChecker:
    """工作流状态检查器"""

    # 工作流类型
    WORKFLOW_TYPES = {
        "chapter_creation": {
            "total_phases": 9,
            "phase_names": [
                "需求澄清",
                "章节大纲解析",
                "场景类型识别",
                "数据提炼",
                "经验检索",
                "设定自动检索",
                "场景契约提取",
                "逐场景创作",
                "整章评估",
            ],
        },
        "data_extraction": {
            "total_phases": 4,
            "phase_names": ["扫描小说库", "提取数据", "构建向量", "同步完成"],
        },
        "setting_update": {
            "total_phases": 3,
            "phase_names": ["验证输入", "更新文件", "同步向量库"],
        },
    }

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化状态检查器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = (
            Path(project_root) if project_root else self._detect_project_root()
        )
        self.state_dir = self.project_root / ".workflow_states"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        current = Path(__file__).resolve()
        markers = ["README.md", "config.example.json", "tools", "设定"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                return parent

        return Path.cwd()

    def check_pending_workflow(self, session_id: str) -> Optional[WorkflowState]:
        """
        检查是否有未完成的工作流

        Args:
            session_id: 会话ID

        Returns:
            WorkflowState or None
        """
        state_file = self.state_dir / f"{session_id}_workflow.json"

        if not state_file.exists():
            return None

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查是否已完成
            if data.get("completed", False):
                return None

            # 检查是否过期（超过24小时）
            last_activity = data.get("last_activity")
            if last_activity:
                last_dt = datetime.fromisoformat(last_activity)
                if (datetime.now() - last_dt).total_seconds() > 86400:  # 24小时
                    data["can_resume"] = False

            return WorkflowState(
                workflow_id=data.get("workflow_id", ""),
                workflow_type=data.get("workflow_type", ""),
                current_phase=data.get("current_phase", 0),
                total_phases=data.get("total_phases", 0),
                chapter=data.get("chapter"),
                scene_progress=data.get("scene_progress"),
                started_at=data.get("started_at"),
                last_activity=data.get("last_activity"),
                can_resume=data.get("can_resume", True),
                metadata=data.get("metadata"),
            )

        except Exception as e:
            print(f"Error reading workflow state: {e}")
            return None

    def save_state(self, session_id: str, state: Dict[str, Any]) -> bool:
        """
        保存工作流状态

        Args:
            session_id: 会话ID
            state: 状态数据

        Returns:
            是否成功保存
        """
        state_file = self.state_dir / f"{session_id}_workflow.json"

        try:
            # 添加时间戳
            state["saved_at"] = datetime.now().isoformat()
            state["last_activity"] = datetime.now().isoformat()

            # 如果是第一次保存，添加started_at
            if not state.get("started_at"):
                state["started_at"] = datetime.now().isoformat()

            # 写入文件
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f"Error saving workflow state: {e}")
            return False

    def mark_completed(self, session_id: str) -> bool:
        """
        标记工作流已完成

        Args:
            session_id: 会话ID

        Returns:
            是否成功标记
        """
        state_file = self.state_dir / f"{session_id}_workflow.json"

        if not state_file.exists():
            return False

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["completed"] = True
            data["completed_at"] = datetime.now().isoformat()

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f"Error marking workflow as completed: {e}")
            return False

    def clear_state(self, session_id: str) -> bool:
        """
        清除工作流状态

        Args:
            session_id: 会话ID

        Returns:
            是否成功清除
        """
        state_file = self.state_dir / f"{session_id}_workflow.json"

        if state_file.exists():
            try:
                state_file.unlink()
                return True
            except Exception as e:
                print(f"Error clearing workflow state: {e}")
                return False

        return True

    def generate_resume_prompt(self, pending: WorkflowState) -> str:
        """生成恢复提示，附加场景摘要上下文（如有）。"""
        # 原有逻辑：构建基础提示
        phase_name = ""
        if pending.workflow_type in self.WORKFLOW_TYPES:
            phase_names = self.WORKFLOW_TYPES[pending.workflow_type]["phase_names"]
            if 0 <= pending.current_phase - 1 < len(phase_names):
                phase_name = phase_names[pending.current_phase - 1]

        lines = [
            f"## 检测到未完成的工作流",
            f"",
            f"- **章节**：第 {pending.chapter} 章" if pending.chapter else "",
            f"- **当前阶段**：阶段 {pending.current_phase}（{phase_name}）",
            f"- **总阶段数**：{pending.total_phases}",
            f"- **可恢复**：{'是' if pending.can_resume else '否'}",
        ]

        if pending.scene_progress:
            lines.append(
                f"- **场景进度**：{pending.scene_progress.get('current', '?')}"
                f"/{pending.scene_progress.get('total', '?')}"
            )

        lines = [l for l in lines if l != ""]

        # 新增：加载已完成场景摘要
        if pending.chapter:
            try:
                from core.conversation.checkpoint_manager import CheckpointManager

                # session_id 从 workflow_id 取前缀（格式：{session_id}_{timestamp}）
                session_id = (
                    pending.workflow_id.rsplit("_", 1)[0]
                    if "_" in pending.workflow_id
                    else pending.workflow_id
                )
                mgr = CheckpointManager(session_id, project_root=self.project_root)
                scene_ctx = mgr.format_summaries_for_prompt(pending.chapter)
                if scene_ctx:
                    lines.append("")
                    lines.append(scene_ctx)
                resume_desc = mgr.get_resume_description(pending.chapter)
                if resume_desc:
                    lines.append("")
                    lines.append(f"**断点详情**：{resume_desc}")
            except Exception:
                pass  # checkpoint 加载失败不影响主流程

        return "\n".join(lines)

    def update_phase(
        self, session_id: str, phase: int, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新当前阶段

        Args:
            session_id: 会话ID
            phase: 当前阶段
            metadata: 附加元数据

        Returns:
            是否成功更新
        """
        state_file = self.state_dir / f"{session_id}_workflow.json"

        if not state_file.exists():
            return False

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["current_phase"] = phase
            data["last_activity"] = datetime.now().isoformat()

            if metadata:
                if "metadata" not in data:
                    data["metadata"] = {}
                data["metadata"].update(metadata)

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f"Error updating phase: {e}")
            return False

    def get_all_pending_workflows(self) -> List[WorkflowState]:
        """
        获取所有未完成的工作流

        Returns:
            未完成工作流列表
        """
        pending = []

        for state_file in self.state_dir.glob("*_workflow.json"):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if not data.get("completed", False):
                    pending.append(
                        WorkflowState(
                            workflow_id=data.get("workflow_id", ""),
                            workflow_type=data.get("workflow_type", ""),
                            current_phase=data.get("current_phase", 0),
                            total_phases=data.get("total_phases", 0),
                            chapter=data.get("chapter"),
                            scene_progress=data.get("scene_progress"),
                            started_at=data.get("started_at"),
                            last_activity=data.get("last_activity"),
                            can_resume=data.get("can_resume", True),
                            metadata=data.get("metadata"),
                        )
                    )

            except Exception as e:
                print(f"Error reading state file {state_file}: {e}")

        return pending

    def create_workflow(
        self,
        session_id: str,
        workflow_type: str,
        chapter: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowState:
        """
        创建新工作流

        Args:
            session_id: 会话ID
            workflow_type: 工作流类型
            chapter: 章节号（可选）
            metadata: 附加元数据

        Returns:
            WorkflowState
        """
        workflow_config = self.WORKFLOW_TYPES.get(workflow_type, {})

        state = {
            "workflow_id": f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "workflow_type": workflow_type,
            "current_phase": 0,
            "total_phases": workflow_config.get("total_phases", 0),
            "chapter": chapter,
            "completed": False,
            "can_resume": True,
            "metadata": metadata or {},
        }

        self.save_state(session_id, state)

        total_phases_value = state.get("total_phases", 0)
        total_phases: int = (
            total_phases_value if isinstance(total_phases_value, int) else 0
        )

        return WorkflowState(
            workflow_id=str(state.get("workflow_id", "")),
            workflow_type=workflow_type,
            current_phase=0,
            total_phases=total_phases,
            chapter=chapter,
            can_resume=True,
            metadata=metadata,
        )


# 测试代码
if __name__ == "__main__":
    checker = WorkflowStateChecker()

    print("=" * 60)
    print("工作流状态检查器测试")
    print("=" * 60)

    # 创建测试工作流
    test_session = "test_session_001"
    state = checker.create_workflow(
        session_id=test_session,
        workflow_type="chapter_creation",
        chapter=1,
        metadata={"user": "测试用户"},
    )

    print(f"\n创建工作流: {state.workflow_id}")
    print(f"类型: {state.workflow_type}")
    print(f"章节: {state.chapter}")
    print(f"阶段: {state.current_phase}/{state.total_phases}")

    # 更新阶段
    checker.update_phase(test_session, 2, {"scene_types": ["开篇", "战斗"]})

    # 检查待恢复工作流
    pending = checker.check_pending_workflow(test_session)
    if pending:
        print("\n" + checker.generate_resume_prompt(pending))

    # 清理
    checker.clear_state(test_session)
    print("\n测试完成，状态已清理")
