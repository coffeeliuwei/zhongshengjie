#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
类型发现模块
===========

统一类型发现器，支持从外部小说库自动发现新的力量类型、势力类型、技法类型、场景类型。

导出接口：
- TypeDiscoverer: 统一类型发现器基类
- PowerTypeDiscoverer: 力量类型发现器
- FactionDiscoverer: 势力类型发现器
- TechniqueDiscoverer: 技法类型发现器
- DiscoveredType: 发现的类型数据结构
"""

from .type_discoverer import TypeDiscoverer, DiscoveredType
from .power_type_discoverer import PowerTypeDiscoverer
from .faction_discoverer import FactionDiscoverer
from .technique_discoverer import TechniqueDiscoverer

__all__ = [
    "TypeDiscoverer",
    "DiscoveredType",
    "PowerTypeDiscoverer",
    "FactionDiscoverer",
    "TechniqueDiscoverer",
]
