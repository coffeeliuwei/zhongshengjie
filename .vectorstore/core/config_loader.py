#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置加载器 - 用于读取Qdrant等服务的配置"""

import json
from pathlib import Path
from typing import Optional

# 默认Qdrant URL
DEFAULT_QDRANT_URL = "http://localhost:6333"


def get_qdrant_url() -> str:
    """
    获取Qdrant URL配置
    
    优先级:
    1. 从config.json读取
    2. 使用默认值 localhost:6333
    
    Returns:
        str: Qdrant服务URL
    """
    # 查找config.json位置
    # 先在当前文件所在目录的上级目录查找
    config_paths = [
        Path(__file__).parent.parent.parent / "config.json",  # .vectorstore/../config.json
        Path(__file__).parent.parent / "config.json",  # .vectorstore/config.json
        Path.cwd() / "config.json",  # 当前工作目录
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "qdrant_url" in config:
                        return config["qdrant_url"]
            except (json.JSONDecodeError, IOError):
                pass
    
    # 未找到配置,使用默认值
    return DEFAULT_QDRANT_URL


def get_config_path() -> Optional[Path]:
    """获取config.json文件的路径"""
    config_paths = [
        Path(__file__).parent.parent.parent / "config.json",
        Path(__file__).parent.parent / "config.json",
        Path.cwd() / "config.json",
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            return config_path
    
    return None