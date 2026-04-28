#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置桥接模块
============

为现有代码提供兼容层，让硬编码路径逐步迁移到配置系统。

用法：
    # 旧代码（硬编码）
    PROJECT_DIR = Path(r"D:\动画\众生界")
    model_path = r"E:\huggingface_cache\..."

    # 新代码（配置化）
    from core.config_bridge import PROJECT_DIR, get_model_path
    model_path = get_model_path()
"""

from pathlib import Path
from typing import Optional

# 延迟导入避免循环依赖
_config = None


def _get_config():
    global _config
    if _config is None:
        from core.config_loader import get_config

        _config = get_config()
    return _config


def get_project_dir() -> Path:
    """获取项目根目录"""
    from core.config_loader import get_project_root

    return get_project_root()


def get_model_path() -> Optional[str]:
    """获取模型路径"""
    from core.config_loader import get_model_path as _get_model_path

    return _get_model_path()


def get_qdrant_url() -> str:
    """获取Qdrant URL"""
    from core.config_loader import get_qdrant_url

    return get_qdrant_url()


def get_vectorstore_dir() -> Path:
    """获取向量库目录"""
    from core.config_loader import get_vectorstore_dir

    return get_vectorstore_dir()


# 兼容旧代码的全局变量
# 这些变量在模块加载时初始化，用于兼容现有的硬编码方式
PROJECT_DIR = Path(__file__).resolve().parent.parent
VECTORSTORE_DIR = PROJECT_DIR / ".vectorstore"
try:
    from core.config_loader import get_case_library_dir as _gcld
    CASE_LIBRARY_DIR = _gcld()
except Exception:
    CASE_LIBRARY_DIR = PROJECT_DIR / ".case-library"
TECHNIQUES_DIR = PROJECT_DIR / "创作技法"
SETTINGS_DIR = PROJECT_DIR / "设定"
CHAPTERS_DIR = PROJECT_DIR / "章节大纲"
CONTENT_DIR = PROJECT_DIR / "正文"
LOGS_DIR = PROJECT_DIR / "logs"


def init_paths_from_config():
    """
    从配置文件重新初始化路径

    在程序启动时调用此函数，可以让全局变量使用配置文件中的路径。

    Example:
        # main.py
        from core.config_bridge import init_paths_from_config
        init_paths_from_config()
    """
    global PROJECT_DIR, VECTORSTORE_DIR, CASE_LIBRARY_DIR
    global TECHNIQUES_DIR, SETTINGS_DIR, CHAPTERS_DIR, CONTENT_DIR, LOGS_DIR

    from core.config_loader import (
        get_project_root,
        get_path,
        get_vectorstore_dir,
        get_case_library_dir,
    )

    PROJECT_DIR = get_project_root()
    VECTORSTORE_DIR = get_vectorstore_dir()
    CASE_LIBRARY_DIR = get_case_library_dir()
    TECHNIQUES_DIR = get_path("techniques_dir")
    SETTINGS_DIR = get_path("settings_dir")
    CHAPTERS_DIR = get_path("chapters_dir")
    CONTENT_DIR = get_path("content_dir")
    LOGS_DIR = get_path("logs_dir")


# 打印配置信息（调试用）
if __name__ == "__main__":
    print("=" * 60)
    print("配置桥接模块")
    print("=" * 60)
    print(f"PROJECT_DIR: {PROJECT_DIR}")
    print(f"VECTORSTORE_DIR: {VECTORSTORE_DIR}")
    print(f"MODEL_PATH: {get_model_path() or '自动下载'}")
    print(f"QDRANT_URL: {get_qdrant_url()}")
    print("\n提示: 调用 init_paths_from_config() 可从配置文件加载路径")
