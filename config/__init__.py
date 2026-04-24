#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置模块

提供统一的配置读取接口

使用方式：
    from config import get_scene_types, get_power_types

    scene_types = get_scene_types()
    power_types = get_power_types()

或者：
    from config import DimensionSync

    sync = DimensionSync()
    scene_types = sync.get_scene_types()
"""

from .dimension_sync import (
    DimensionSync,
    get_scene_types,
    get_power_types,
    get_faction_types,
    get_technique_types,
)

__all__ = [
    # 核心类
    "DimensionSync",
    # 便捷函数
    "get_scene_types",
    "get_power_types",
    "get_faction_types",
    "get_technique_types",
]

__version__ = "1.0.0"
