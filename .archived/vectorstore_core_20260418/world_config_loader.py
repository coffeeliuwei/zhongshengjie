#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
世界观配置加载器 - 加载和管理不同世界观配置
===========================================

支持多世界观切换，为统一API层提供世界观上下文
"""

import os
import json
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

# 默认世界观
DEFAULT_WORLD = "众生界"

# 全局世界观配置缓存（线程安全）
_world_configs: Dict[str, Dict[str, Any]] = {}
_current_world: Optional[str] = None
_config_lock = threading.Lock()


def get_world_configs_dir() -> Path:
    """获取世界观配置目录"""
    # 从config_loader导入
    try:
        from core.config_loader import get_world_configs_dir as _get_world_configs_dir

        return _get_world_configs_dir()
    except ImportError:
        try:
            from config_loader import get_world_configs_dir as _get_world_configs_dir

            return _get_world_configs_dir()
        except ImportError:
            # 回退
            from core.config_loader import get_project_root

            project_root = get_project_root()
            return project_root / "config" / "worlds"


def load_world_config(world_name: str) -> Dict[str, Any]:
    """加载指定世界观配置

    Args:
        world_name: 世界观名称

    Returns:
        世界观配置字典
    """
    # 如果已缓存，直接返回（读操作不需要锁）
    if world_name in _world_configs:
        return _world_configs[world_name]

    # 加载配置文件
    configs_dir = get_world_configs_dir()
    config_file = configs_dir / f"{world_name}.json"

    if not config_file.exists():
        raise FileNotFoundError(f"世界观配置文件不存在: {config_file}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        # 写入缓存需要锁保护
        with _config_lock:
            _world_configs[world_name] = config
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"世界观配置文件格式错误: {e}")


def get_current_world() -> str:
    """获取当前激活的世界观"""
    global _current_world
    if _current_world is None:
        # 尝试从 config.json 读取
        try:
            from core.config_loader import get_config
        except ImportError:
            from config_loader import get_config

        config = get_config()
        worldview_config = config.get("worldview", {})
        current = worldview_config.get("current_world", DEFAULT_WORLD)
        # 写入需要锁保护
        with _config_lock:
            _current_world = current
    return _current_world


def set_current_world(world_name: str) -> bool:
    """设置当前世界观

    Args:
        world_name: 世界观名称

    Returns:
        是否成功设置
    """
    global _current_world
    try:
        # 验证配置存在
        load_world_config(world_name)
        # 写入需要锁保护
        with _config_lock:
            _current_world = world_name
        return True
    except FileNotFoundError:
        return False


def get_current_config() -> Dict[str, Any]:
    """获取当前世界观配置"""
    return load_world_config(get_current_world())


def get_power_systems() -> Dict[str, Any]:
    """获取当前世界观的力量体系"""
    return get_current_config().get("power_systems", {})


def get_power_system(power_name: str) -> Optional[Dict[str, Any]]:
    """获取指定力量体系详情

    Args:
        power_name: 力量体系名称

    Returns:
        力量体系配置字典
    """
    power_systems = get_power_systems()
    return power_systems.get(power_name)


def get_factions() -> Dict[str, Any]:
    """获取当前世界的势力"""
    return get_current_config().get("factions", {})


def get_faction(faction_name: str) -> Optional[Dict[str, Any]]:
    """获取指定势力详情

    Args:
        faction_name: 势力名称

    Returns:
        势力配置字典
    """
    factions = get_factions()
    return factions.get(faction_name)


def get_characters() -> Dict[str, Any]:
    """获取当前世界观的关键角色"""
    return get_current_config().get("key_characters", {})


def get_character(character_name: str) -> Optional[Dict[str, Any]]:
    """获取指定角色详情

    Args:
        character_name: 角色名称

    Returns:
        角色配置字典
    """
    characters = get_characters()
    return characters.get(character_name)


def get_relationships() -> Dict[str, Any]:
    """获取当前世界观的关系网络"""
    return get_current_config().get("relationships", {})


def get_eras() -> Dict[str, Any]:
    """获取当前世界观的时代划分"""
    return get_current_config().get("eras", {})


def get_era(era_name: str) -> Optional[Dict[str, Any]]:
    """获取指定时代详情

    Args:
        era_name: 时代名称

    Returns:
        时代配置字典
    """
    eras = get_eras()
    return eras.get(era_name)


def get_core_principles() -> Dict[str, Any]:
    """获取当前世界观的核心原则"""
    return get_current_config().get("core_principles", {})


def get_technique_mappings() -> Dict[str, Any]:
    """获取技法映射配置"""
    return get_current_config().get("technique_mappings", {})


def get_technique_mapping(
    category: str, power_name: str = None
) -> Optional[Dict[str, Any]]:
    """获取指定类别的技法映射

    Args:
        category: 类别（战斗/意境/人物）
        power_name: 力量体系名称（可选）

    Returns:
        技法映射字典
    """
    mappings = get_technique_mappings()
    category_mapping = mappings.get(category, {})

    if power_name:
        power_specific = category_mapping.get("power_specific", {})
        return power_specific.get(power_name)

    return category_mapping


def list_available_worlds() -> List[str]:
    """列出所有可用的世界观"""
    configs_dir = get_world_configs_dir()
    worlds = []

    for config_file in configs_dir.glob("*.json"):
        world_name = config_file.stem
        worlds.append(world_name)

    return sorted(worlds)


def get_world_info(world_name: str = None) -> Dict[str, Any]:
    """获取世界观摘要信息

    Args:
        world_name: 世界观名称（默认当前）

    Returns:
        世界观摘要
    """
    if world_name is None:
        world_name = get_current_world()

    config = load_world_config(world_name)

    return {
        "name": config.get("world_name"),
        "type": config.get("world_type"),
        "description": config.get("description"),
        "power_systems_count": len(config.get("power_systems", {})),
        "factions_count": len(config.get("factions", {})),
        "characters_count": len(config.get("key_characters", {})),
        "eras_count": len(config.get("eras", {})),
        "core_principles": config.get("core_principles", {}),
    }


def validate_world_config(world_name: str) -> List[str]:
    """验证世界观配置完整性

    Args:
        world_name: 世界观名称

    Returns:
        错误列表（空列表表示配置完整）
    """
    errors = []
    config = load_world_config(world_name)

    # 必须字段
    required_fields = ["world_name", "world_type", "power_systems", "factions"]
    for field in required_fields:
        if field not in config:
            errors.append(f"缺少必需字段: {field}")

    # 力量体系必须有子类型
    for power_name, power_config in config.get("power_systems", {}).items():
        if "subtypes" not in power_config:
            errors.append(f"力量体系 {power_name} 缺少子类型定义")

    return errors


# ============================================================
# 高级查询API
# ============================================================


def query_by_power(power_name: str) -> Dict[str, Any]:
    """按力量体系查询相关信息

    Args:
        power_name: 力量体系名称

    Returns:
        力量体系完整信息（包含势力、角色、技法）
    """
    result = {
        "power_config": get_power_system(power_name),
        "related_factions": [],
        "related_characters": [],
        "techniques": get_technique_mapping("战斗", power_name),
    }

    # 查找相关势力
    for faction_name, faction_config in get_factions().items():
        # 检查势力是否使用该力量
        if result["power_config"] and faction_config:
            # 简单匹配：势力建筑风格或文化中包含该力量关键词
            result["related_factions"].append(
                {"name": faction_name, "structure": faction_config.get("structure")}
            )

    # 查找相关角色
    for char_name, char_config in get_characters().items():
        if char_config.get("power") == power_name:
            result["related_characters"].append(
                {
                    "name": char_name,
                    "faction": char_config.get("faction"),
                    "subtype": char_config.get("subtype"),
                    "abilities": char_config.get("abilities"),
                }
            )

    return result


def query_by_faction(faction_name: str) -> Dict[str, Any]:
    """按势力查询相关信息

    Args:
        faction_name: 势力名称

    Returns:
        势力完整信息（包含角色、技法）
    """
    result = {
        "faction_config": get_faction(faction_name),
        "related_characters": [],
        "techniques": get_technique_mapping("人物", faction_name),
    }

    # 查找相关角色
    for char_name, char_config in get_characters().items():
        if char_config.get("faction") == faction_name:
            result["related_characters"].append(
                {
                    "name": char_name,
                    "power": char_config.get("power"),
                    "subtype": char_config.get("subtype"),
                    "abilities": char_config.get("abilities"),
                }
            )

    return result


def query_by_era(era_name: str) -> Dict[str, Any]:
    """按时代查询相关信息

    Args:
        era_name: 时代名称

    Returns:
        时代完整信息（包含意境技法）
    """
    era_config = get_era(era_name)
    techniques = get_technique_mapping("意境")

    return {
        "era_config": era_config,
        "era_techniques": techniques.get("era_specific", {}).get(era_name)
        if techniques
        else None,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("世界观配置加载器测试")
    print("=" * 60)

    # 列出可用世界观
    worlds = list_available_worlds()
    print(f"\n可用世界观: {worlds}")

    # 测试加载众生界
    print(f"\n当前世界观: {get_current_world()}")
    info = get_world_info()
    print(f"世界观信息: {info}")

    # 测试力量体系
    print(f"\n力量体系数量: {len(get_power_systems())}")
    for power_name in get_power_systems():
        print(f"  - {power_name}")

    # 测试势力
    print(f"\n势力数量: {len(get_factions())}")
    for faction_name in get_factions():
        print(f"  - {faction_name}")

    # 测试角色
    print(f"\n角色数量: {len(get_characters())}")
    for char_name in get_characters():
        print(f"  - {char_name}")

    # 测试验证
    errors = validate_world_config(get_current_world())
    print(f"\n配置验证: {errors if errors else '完整'}")
