"""跨章节人物状态追踪工具

维护 chapter_states.json，记录每章定稿后各角色的持续状态。
供 novel-workflow 阶段3读取（注入上下文）和阶段8写入（更新状态）。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

# 支持环境变量覆盖项目根目录，便于跨环境使用
_project_root = Path(os.environ.get("NOVEL_PROJECT_ROOT", "D:/动画/众生界"))
STATE_FILE = _project_root / "chapter_states.json"


def load_states() -> Dict[str, Any]:
    """加载当前状态文件，文件不存在时返回空字典"""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_states(states: Dict[str, Any]) -> None:
    """写入状态文件"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(states, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def update_character_state(
    character: str, chapter: str, updates: Dict[str, Any]
) -> None:
    """更新单个角色状态（合并更新，不覆盖未提及字段）

    Args:
        character: 角色名，如"林枫"
        chapter: 更新来源章节，如"第3章"
        updates: 要更新的字段，如 {"injuries": ["左臂骨折"], "items": ["龙晶×1"]}
    """
    states = load_states()
    if character not in states:
        states[character] = {}
    states[character].update(updates)
    states[character]["last_updated"] = chapter
    _save_states(states)


def get_character_state(character: str) -> Optional[Dict[str, Any]]:
    """获取角色当前状态，角色不存在时返回 None"""
    return load_states().get(character)


def get_all_active_states() -> Dict[str, Any]:
    """获取所有角色的当前状态，用于注入创作上下文"""
    return load_states()


def format_states_for_context(states: Dict[str, Any]) -> str:
    """将状态字典格式化为可注入创作上下文的文字"""
    if not states:
        return ""

    lines = ["【角色持续状态（来自前章）】"]
    for char, state in states.items():
        parts = []
        injuries = state.get("injuries", [])
        if injuries:
            parts.append(f"伤势：{', '.join(injuries)}")
        items = state.get("items", [])
        if items:
            parts.append(f"持有：{', '.join(items)}")
        relationships = state.get("relationships", [])
        if relationships:
            parts.append(f"关系：{', '.join(relationships)}")
        status = state.get("status", "alive")
        if status != "alive":
            parts.append(f"状态：{status}")
        updated = state.get("last_updated", "未知")

        if parts:
            lines.append(f"- {char}（更新于{updated}）：{' | '.join(parts)}")
        else:
            lines.append(f"- {char}（更新于{updated}）：无特殊持续状态")

    return "\n".join(lines)
