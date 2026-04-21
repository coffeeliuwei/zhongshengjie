#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
世界观加载器 (M8 新增)
=====================

从 config.json 读取当前世界观，加载对应的 config/worlds/{name}.json。

用法：
    from core.world_loader import get_world_config, get_current_world_name

    world = get_world_config()
    print(world["world_name"])       # "众生界"
    print(world["power_systems"])    # {...}
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _load_config(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """加载 config.json"""
    root = project_root or Path.cwd()
    config_path = root / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def get_current_world_name(project_root: Optional[Path] = None) -> str:
    """
    返回当前世界观名称。

    优先读 config.json → worldview.current_world，
    缺省返回 "众生界"。
    """
    cfg = _load_config(project_root)
    return cfg.get("worldview", {}).get("current_world", "众生界")


def get_world_config(
    world_name: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    加载指定世界观的配置。

    Args:
        world_name: 世界观名称，None 表示读取 config.json 中的当前世界观
        project_root: 项目根目录，None 表示使用 CWD

    Returns:
        世界观配置字典，含 world_name / power_systems / factions 等键

    Raises:
        FileNotFoundError: 对应的 worlds/*.json 不存在
    """
    root = project_root or Path.cwd()
    name = world_name or get_current_world_name(root)
    worlds_dir = root / "config" / "worlds"
    world_file = worlds_dir / f"{name}.json"

    if not world_file.exists():
        # 尝试 列出已有世界观，给出提示
        available = [f.stem for f in worlds_dir.glob("*.json")] if worlds_dir.exists() else []
        raise FileNotFoundError(
            f"世界观配置文件不存在: {world_file}\n"
            f"可用世界观: {available}\n"
            f"请检查 config/worlds/ 目录或修改 config.json → worldview.current_world"
        )

    with open(world_file, encoding="utf-8") as f:
        return json.load(f)


def switch_world(new_world_name: str, project_root: Optional[Path] = None) -> None:
    """
    切换当前世界观（修改 config.json）。

    Args:
        new_world_name: 新世界观名称（必须在 config/worlds/ 下存在对应 .json）
        project_root: 项目根目录

    Raises:
        FileNotFoundError: 目标世界观配置文件不存在
        ValueError: 同名世界观已是当前激活项
    """
    root = project_root or Path.cwd()

    # 先验证目标世界观存在
    target_file = root / "config" / "worlds" / f"{new_world_name}.json"
    if not target_file.exists():
        available = [f.stem for f in (root / "config" / "worlds").glob("*.json")]
        raise FileNotFoundError(
            f"目标世界观配置不存在: {target_file}\n可用: {available}"
        )

    current = get_current_world_name(root)
    if current == new_world_name:
        raise ValueError(f"当前已是世界观 '{new_world_name}'，无需切换")

    # 修改 config.json
    config_path = root / "config.json"
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)

    cfg.setdefault("worldview", {})["current_world"] = new_world_name

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    print(f"✅ 世界观已切换: {current} → {new_world_name}")


def list_available_worlds(project_root: Optional[Path] = None) -> list:
    """列出 config/worlds/ 下所有可用世界观"""
    root = project_root or Path.cwd()
    worlds_dir = root / "config" / "worlds"
    if not worlds_dir.exists():
        return []
    return sorted(f.stem for f in worlds_dir.glob("*.json"))