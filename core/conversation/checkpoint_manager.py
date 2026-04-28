# core/conversation/checkpoint_manager.py
"""场景级 Checkpoint 管理器

职责：文件 I/O。不负责工作流编排（那是 SKILL 的事）。

核心用途：
  1. 前序场景上下文注入（阶段4开始时加载已完成摘要）
  2. 每场完成后写入 200 字摘要 + 关键点
  3. 阶段7章节确认后清理当章 checkpoint

phase_sub 字段用于表示半步阶段（如 "5.5"），避免 int 字段存浮点。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field

try:
    from core.config_loader import get_project_root
except ImportError:

    def get_project_root() -> Path:
        return Path(__file__).resolve().parents[2]


@dataclass
class SceneSummary:
    """单场景完成后的摘要记录"""

    chapter: int
    scene_index: int
    scene_type: str
    summary: str  # 200字以内摘要
    key_points: List[str]  # 3-5个关键点（角色状态、道具、伏笔等）
    writer_agent: str  # 主笔作家
    saved_at: str = ""

    def __post_init__(self):
        if not self.saved_at:
            self.saved_at = datetime.now().isoformat()


@dataclass
class WorkflowCheckpoint:
    """工作流断点记录"""

    chapter: int
    phase: int  # 主阶段 0-8
    phase_sub: Optional[str] = None  # 半步阶段，存小数部分字符串：阶段5.5 → phase=5, phase_sub="5"
    scene_index: int = 0
    scene_total: int = 0
    active_writer: Optional[str] = None
    pending_actions: List[str] = field(default_factory=list)
    checkpoint_time: str = ""
    can_resume: bool = True
    note: str = ""  # 人读的备注

    def __post_init__(self):
        if not self.checkpoint_time:
            self.checkpoint_time = datetime.now().isoformat()


class CheckpointManager:
    """Checkpoint 文件 I/O。

    存储路径：.workflow_states/{session_id}_checkpoints/
    """

    def __init__(self, session_id: str, project_root: Optional[Path] = None):
        self.session_id = session_id
        root = project_root or get_project_root()
        base = root / ".workflow_states"
        self.checkpoint_dir = base / f"{session_id}_checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # ── 场景摘要 ──────────────────────────────────────────────

    def save_scene_summary(
        self,
        chapter: int,
        scene_index: int,
        scene_type: str,
        summary: str,
        key_points: List[str],
        writer_agent: str = "",
    ) -> str:
        """保存场景摘要（每场完成后调用）。

        Returns:
            写入的文件路径字符串
        """
        record = SceneSummary(
            chapter=chapter,
            scene_index=scene_index,
            scene_type=scene_type,
            summary=summary[:200],
            key_points=key_points[:5],
            writer_agent=writer_agent,
        )
        filename = f"ch{chapter:03d}_scene{scene_index:03d}_summary.json"
        filepath = self.checkpoint_dir / filename
        filepath.write_text(
            json.dumps(asdict(record), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(filepath)

    def load_chapter_summaries(self, chapter: int) -> List[SceneSummary]:
        """加载章节内所有已完成场景摘要（按 scene_index 排序）。

        供阶段4开始时注入上下文用。
        """
        summaries = []
        for f in sorted(
            self.checkpoint_dir.glob(f"ch{chapter:03d}_scene*_summary.json")
        ):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                summaries.append(SceneSummary(**data))
            except Exception as e:
                print(f"[checkpoint] 跳过损坏文件 {f.name}: {e}")
                continue
        summaries.sort(key=lambda s: s.scene_index)
        return summaries

    def format_summaries_for_prompt(self, chapter: int) -> str:
        """将已完成场景摘要格式化为注入字符串。

        返回空字符串表示无历史（首场或全新章节）。
        """
        summaries = self.load_chapter_summaries(chapter)
        if not summaries:
            return ""

        lines = ["【本章已完成场景摘要】"]
        for s in summaries:
            kp = "；".join(s.key_points) if s.key_points else "无"
            lines.append(
                f"  场景{s.scene_index}（{s.scene_type}）：{s.summary}\n  关键点：{kp}"
            )
        return "\n".join(lines)

    # ── 断点记录 ──────────────────────────────────────────────

    def save_checkpoint(
        self,
        chapter: int,
        phase: int,
        scene_index: int = 0,
        scene_total: int = 0,
        phase_sub: Optional[str] = None,
        active_writer: Optional[str] = None,
        pending_actions: Optional[List[str]] = None,
        note: str = "",
    ) -> str:
        """保存工作流断点。"""
        cp = WorkflowCheckpoint(
            chapter=chapter,
            phase=phase,
            phase_sub=phase_sub,
            scene_index=scene_index,
            scene_total=scene_total,
            active_writer=active_writer,
            pending_actions=pending_actions or [],
            note=note,
        )
        filename = f"ch{chapter:03d}_phase{phase}_checkpoint.json"
        if phase_sub:
            filename = f"ch{chapter:03d}_phase{phase}_{phase_sub}_checkpoint.json"
        filepath = self.checkpoint_dir / filename
        filepath.write_text(
            json.dumps(asdict(cp), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(filepath)

    def load_latest_checkpoint(self, chapter: int) -> Optional[WorkflowCheckpoint]:
        """加载章节最新断点。"""
        files = sorted(
            self.checkpoint_dir.glob(f"ch{chapter:03d}_*_checkpoint.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return None
        try:
            data = json.loads(files[0].read_text(encoding="utf-8"))
            return WorkflowCheckpoint(**data)
        except Exception:
            return None

    def get_resume_description(self, chapter: int) -> str:
        """返回可读的断点恢复说明（供 generate_resume_prompt 使用）。"""
        cp = self.load_latest_checkpoint(chapter)
        if not cp:
            return ""

        phase_label = f"阶段{cp.phase}"
        if cp.phase_sub:
            phase_label = f"阶段{cp.phase}.{cp.phase_sub}"

        parts = [f"上次中断于第{cp.chapter}章 {phase_label}"]
        if cp.scene_index:
            parts.append(f"场景 {cp.scene_index}/{cp.scene_total or '?'}")
        if cp.active_writer:
            parts.append(f"当前执行：{cp.active_writer}")
        if cp.note:
            parts.append(f"备注：{cp.note}")

        return "，".join(parts)

    # ── 清理 ──────────────────────────────────────────────────

    def clear_chapter_checkpoints(self, chapter: int) -> int:
        """章节确认后清理当章所有 checkpoint 文件（阶段7调用）。

        Returns:
            删除的文件数
        """
        count = 0
        for f in self.checkpoint_dir.glob(f"ch{chapter:03d}_*.json"):
            f.unlink()
            count += 1
        return count
