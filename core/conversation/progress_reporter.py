#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
进度报告器
==========

生成工作流进度报告，提供实时反馈。

核心功能：
- 生成进度条
- 生成进度报告
- 场景级进度跟踪
- 时间估算

参考：统一提炼引擎重构方案.md 第10.3.5节
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ProgressInfo:
    """进度信息"""

    current_phase: int
    total_phases: int
    phase_name: str
    chapter: Optional[int] = None
    scene_progress: Optional[Dict[str, int]] = None
    elapsed_time: Optional[str] = None
    estimated_remaining: Optional[str] = None
    status: str = "进行中"  # "进行中", "等待中", "已完成"


class ProgressReporter:
    """进度报告器"""

    # 阶段名称映射（章节创作工作流）
    PHASE_NAMES = {
        0: "需求澄清",
        1: "章节大纲解析",
        2: "场景类型识别",
        2.3: "数据提炼",
        2.5: "经验检索",
        3: "设定自动检索",
        3.5: "场景契约提取",
        4: "逐场景创作",
        5: "整章整合",
        6: "整章评估",
        7: "用户确认",
        8: "经验写入",
        9: "完成",
    }

    # 数据提炼工作流阶段
    EXTRACTION_PHASE_NAMES = {
        0: "扫描小说库",
        1: "提取数据",
        2: "构建向量",
        3: "同步完成",
        4: "完成",
    }

    # 设定更新工作流阶段
    UPDATE_PHASE_NAMES = {
        0: "验证输入",
        1: "更新文件",
        2: "同步向量库",
        3: "完成",
    }

    # 阶段图标
    PHASE_ICONS = {
        "需求澄清": "📋",
        "章节大纲解析": "📖",
        "场景类型识别": "🎭",
        "数据提炼": "⚙️",
        "经验检索": "🔍",
        "设定自动检索": "📚",
        "场景契约提取": "📝",
        "逐场景创作": "✍️",
        "整章整合": "🔗",
        "整章评估": "✅",
        "用户确认": "👋",
        "经验写入": "💾",
        "完成": "🎉",
        "扫描小说库": "📂",
        "提取数据": "📊",
        "构建向量": "🧠",
        "同步完成": "☁️",
        "验证输入": "🔎",
        "更新文件": "📝",
        "同步向量库": "🔄",
    }

    # 阶段颜色（用于可视化）
    PHASE_COLORS = {
        0: "#3498db",  # 蓝色 - 需求澄清
        1: "#2ecc71",  # 绿色 - 大纲解析
        2: "#9b59b6",  # 紫色 - 场景识别
        3: "#e67e22",  # 橙色 - 检索
        4: "#e74c3c",  # 红色 - 创作
        5: "#1abc9c",  # 青色 - 整合
        6: "#f39c12",  # 黄色 - 评估
        7: "#95a5a6",  # 灰色 - 确认
        8: "#27ae60",  # 深绿 - 完成
    }

    def __init__(self):
        """初始化进度报告器"""
        self.start_time: Optional[datetime] = None
        self.phase_times: Dict[int, datetime] = {}

    def start_tracking(self) -> None:
        """开始跟踪"""
        self.start_time = datetime.now()
        self.phase_times = {}

    def record_phase_start(self, phase: int) -> None:
        """
        记录阶段开始时间

        Args:
            phase: 阶段号
        """
        self.phase_times[phase] = datetime.now()

    def get_phase_name(
        self, phase: int, workflow_type: str = "chapter_creation"
    ) -> str:
        """
        获取阶段名称

        Args:
            phase: 阶段号
            workflow_type: 工作流类型

        Returns:
            阶段名称
        """
        if workflow_type == "chapter_creation":
            return self.PHASE_NAMES.get(phase, f"阶段{phase}")
        elif workflow_type == "data_extraction":
            return self.EXTRACTION_PHASE_NAMES.get(phase, f"阶段{phase}")
        elif workflow_type == "setting_update":
            return self.UPDATE_PHASE_NAMES.get(phase, f"阶段{phase}")

        return f"阶段{phase}"

    def get_phase_icon(self, phase_name: str) -> str:
        """
        获取阶段图标

        Args:
            phase_name: 阶段名称

        Returns:
            阶段图标
        """
        return self.PHASE_ICONS.get(phase_name, "⏳")

    def generate_progress(self, state: Dict[str, Any]) -> str:
        """
        生成进度报告

        Args:
            state: 工作流状态

        Returns:
            进度报告文本
        """
        current = state.get("current_phase", 0)
        total = state.get("total_phases", 0)
        workflow_type = state.get("workflow_type", "chapter_creation")

        phase_name = self.get_phase_name(current, workflow_type)
        phase_icon = self.get_phase_icon(phase_name)

        # 进度条
        progress_bar = self._generate_progress_bar(current, total)

        # 状态文本
        status_text = state.get("status", "进行中")
        status_icon = (
            "🔄"
            if status_text == "进行中"
            else "⏸️"
            if status_text == "等待中"
            else "✅"
        )

        # 基础报告
        report = f"""
【工作流进度】
{progress_bar}
当前：{phase_icon} [{current}/{total}] {phase_name}
状态：{status_icon} {status_text}
        """.strip()

        # 添加章节信息
        if state.get("chapter"):
            report += f"\n章节：第{state['chapter']}章"

        # 如果在场景创作阶段，显示更详细的信息
        if phase_name == "逐场景创作" and "scene_progress" in state:
            scene_prog = state["scene_progress"]
            scene_bar = self._generate_progress_bar(
                scene_prog["current"], scene_prog["total"], width=10
            )
            report += f"\n场景进度：{scene_bar} ({scene_prog['current']}/{scene_prog['total']})"

        # 添加时间信息
        if state.get("started_at"):
            elapsed = self._calculate_elapsed_time(state["started_at"])
            if elapsed:
                report += f"\n已用时间：{elapsed}"

        return report

    def _generate_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """
        生成进度条

        Args:
            current: 当前进度
            total: 总进度
            width: 进度条宽度

        Returns:
            进度条字符串
        """
        if total == 0:
            return "[░░░░░░░░░░░░░░░░░░░░] 0%"

        filled = int(width * current / total)
        bar = "█" * filled + "░" * (width - filled)
        percent = int(100 * current / total)

        return f"[{bar}] {percent}%"

    def _calculate_elapsed_time(self, started_at: str) -> Optional[str]:
        """
        计算已用时间

        Args:
            started_at: 开始时间字符串

        Returns:
            时间描述
        """
        try:
            start_dt = datetime.fromisoformat(started_at)
            elapsed = datetime.now() - start_dt

            # 格式化时间
            if elapsed.total_seconds() < 60:
                return f"{int(elapsed.total_seconds())}秒"
            elif elapsed.total_seconds() < 3600:
                minutes = int(elapsed.total_seconds() / 60)
                seconds = int(elapsed.total_seconds() % 60)
                return f"{minutes}分{seconds}秒"
            else:
                hours = int(elapsed.total_seconds() / 3600)
                minutes = int((elapsed.total_seconds() % 3600) / 60)
                return f"{hours}小时{minutes}分"

        except Exception:
            return None

    def estimate_remaining_time(
        self, current: int, total: int, avg_phase_time: float = 60.0
    ) -> str:
        """
        估算剩余时间

        Args:
            current: 当前进度
            total: 总进度
            avg_phase_time: 平均阶段时间（秒）

        Returns:
            估算时间
        """
        remaining_phases = total - current
        remaining_seconds = remaining_phases * avg_phase_time

        if remaining_seconds < 60:
            return f"{int(remaining_seconds)}秒"
        elif remaining_seconds < 3600:
            minutes = int(remaining_seconds / 60)
            return f"约{minutes}分钟"
        else:
            hours = int(remaining_seconds / 3600)
            minutes = int((remaining_seconds % 3600) / 60)
            return f"约{hours}小时{minutes}分"

    def generate_phase_detail(
        self, phase: int, workflow_type: str = "chapter_creation"
    ) -> str:
        """
        生成阶段详细描述

        Args:
            phase: 阶段号
            workflow_type: 工作流类型

        Returns:
            详细描述
        """
        phase_name = self.get_phase_name(phase, workflow_type)
        phase_icon = self.get_phase_icon(phase_name)

        # 阶段详情
        phase_details = {
            "需求澄清": "确认创作需求，收集必要信息",
            "章节大纲解析": "分析章节结构，提取关键场景",
            "场景类型识别": "识别每个场景的类型（战斗、情感、悬念等）",
            "数据提炼": "从外部小说库提取新鲜数据",
            "经验检索": "检索前面章节的创作经验",
            "设定自动检索": "检索角色、势力、力量体系等设定",
            "场景契约提取": "提取场景间的契约约束",
            "逐场景创作": "作家逐个场景创作内容",
            "整章整合": "整合所有场景，统一风格",
            "整章评估": "审核评估师评估整章质量",
            "用户确认": "等待用户确认修改",
            "经验写入": "将本章经验写入经验库",
            "扫描小说库": "扫描外部小说库目录",
            "提取数据": "提取小说中的设定、技法、案例",
            "构建向量": "构建向量索引",
            "同步完成": "同步到向量数据库",
            "验证输入": "验证用户输入的设定信息",
            "更新文件": "更新设定文件",
            "同步向量库": "同步到向量数据库",
        }

        detail = phase_details.get(phase_name, "处理中...")

        return f"{phase_icon} {phase_name}\n   └─ {detail}"

    def generate_full_report(
        self, state: Dict[str, Any], include_details: bool = True
    ) -> str:
        """
        生成完整进度报告

        Args:
            state: 工作流状态
            include_details: 是否包含详细描述

        Returns:
            完整报告
        """
        current = state.get("current_phase", 0)
        total = state.get("total_phases", 0)
        workflow_type = state.get("workflow_type", "chapter_creation")

        report = self.generate_progress(state)

        if include_details:
            report += "\n\n【当前阶段详情】\n"
            report += self.generate_phase_detail(current, workflow_type)

            # 显示已完成阶段
            if current > 0:
                report += "\n\n【已完成阶段】\n"
                for phase in range(current):
                    phase_name = self.get_phase_name(phase, workflow_type)
                    phase_icon = self.get_phase_icon(phase_name)
                    report += f"  ✅ {phase_icon} {phase_name}\n"

        return report

    def generate_quick_status(self, state: Dict[str, Any]) -> str:
        """
        生成快速状态报告

        Args:
            state: 工作流状态

        Returns:
            状态文本
        """
        current = state.get("current_phase", 0)
        total = state.get("total_phases", 0)
        workflow_type = state.get("workflow_type", "chapter_creation")

        phase_name = self.get_phase_name(current, workflow_type)
        phase_icon = self.get_phase_icon(phase_name)

        percent = int(100 * current / total) if total > 0 else 0

        return f"{phase_icon} {phase_name} ({percent}%)"


# 测试代码
if __name__ == "__main__":
    reporter = ProgressReporter()

    print("=" * 60)
    print("进度报告器测试")
    print("=" * 60)

    # 测试进度条
    print("\n进度条测试:")
    for i in range(0, 10, 2):
        print(f"  阶段 {i}/9: {reporter._generate_progress_bar(i, 9)}")

    # 测试进度报告
    test_state = {
        "current_phase": 4,
        "total_phases": 9,
        "workflow_type": "chapter_creation",
        "chapter": 1,
        "scene_progress": {"current": 2, "total": 5},
        "status": "进行中",
        "started_at": datetime.now().isoformat(),
    }

    print("\n进度报告:")
    print(reporter.generate_progress(test_state))

    print("\n完整报告:")
    print(reporter.generate_full_report(test_state))

    print("\n快速状态:")
    print(reporter.generate_quick_status(test_state))
