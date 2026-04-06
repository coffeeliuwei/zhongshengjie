#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器 - 用于读取Qdrant等服务的配置
=======================================

统一配置访问接口，支持config.json和环境变量
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

# 默认Qdrant URL
DEFAULT_QDRANT_URL = "http://localhost:6333"

# 默认配置
DEFAULT_CONFIG = {
    "project": {"name": "My Novel", "version": "1.0.0"},
    "paths": {
        "project_root": None,
        "settings_dir": "设定",
        "techniques_dir": "创作技法",
        "vectorstore_dir": ".vectorstore",
        "case_library_dir": ".case-library",
    },
    "database": {
        "qdrant_host": "localhost",
        "qdrant_port": 6333,
        "collections": {
            "novel_settings": "novel_settings_v2",
            "writing_techniques": "writing_techniques_v2",
            "case_library": "case_library_v2",
        },
    },
    "model": {
        "embedding_model": "BAAI/bge-m3",
        "model_path": None,
        "vector_size": 1024,
    },
}

# 全局配置
_global_config: Optional[Dict[str, Any]] = None
_project_root: Optional[Path] = None


def find_project_root() -> Path:
    """自动检测项目根目录"""
    current = Path(__file__).resolve()
    markers = ["README.md", "config.example.json", ".gitignore", "tools"]

    for parent in current.parents:
        if any((parent / marker).exists() for marker in markers):
            if (parent / "tools").exists():
                return parent
    return Path.cwd()


def get_project_root() -> Path:
    """获取项目根目录"""
    global _project_root
    if _project_root is None:
        env_root = os.environ.get("NOVEL_PROJECT_ROOT")
        if env_root:
            _project_root = Path(env_root)
        else:
            _project_root = find_project_root()
    return _project_root


def get_config_path() -> Optional[Path]:
    """获取config.json文件的路径"""
    config_paths = [
        get_project_root() / "config.json",
        Path(__file__).parent.parent.parent / "config.json",
        Path(__file__).parent.parent / "config.json",
        Path.cwd() / "config.json",
    ]

    for config_path in config_paths:
        if config_path.exists():
            return config_path
    return None


def load_config() -> Dict[str, Any]:
    """加载配置"""
    config = DEFAULT_CONFIG.copy()
    config_path = get_config_path()

    if config_path and config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)

            def deep_merge(base: dict, override: dict) -> dict:
                result = base.copy()
                for key, value in override.items():
                    if (
                        key in result
                        and isinstance(result[key], dict)
                        and isinstance(value, dict)
                    ):
                        result[key] = deep_merge(result[key], value)
                    else:
                        result[key] = value
                return result

            config = deep_merge(config, user_config)
        except Exception as e:
            print(f"Warning: Failed to load config: {e}")

    return config


def get_config() -> Dict[str, Any]:
    """获取全局配置"""
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config


def get_qdrant_url() -> str:
    """获取Qdrant URL配置"""
    # 优先级：环境变量 > config.json > 默认值
    env_url = os.environ.get("QDRANT_URL")
    if env_url:
        return env_url

    config = get_config()
    host = config.get("database", {}).get("qdrant_host", "localhost")
    port = config.get("database", {}).get("qdrant_port", 6333)
    return f"http://{host}:{port}"


def get_model_path() -> Optional[str]:
    """获取BGE-M3模型路径"""
    # 优先级：环境变量 > config.json > 自动检测
    env_path = os.environ.get("BGE_M3_MODEL_PATH") or os.environ.get("NOVEL_MODEL_PATH")
    if env_path:
        return env_path

    config = get_config()
    config_path = config.get("model", {}).get("model_path")
    if config_path:
        return config_path

    # 自动检测常见位置
    common_paths = [
        Path.home() / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-m3",
        Path("E:/huggingface_cache/hub/models--BAAI--bge-m3"),
        Path("C:/Users")
        / os.environ.get("USERNAME", "")
        / ".cache"
        / "huggingface"
        / "hub"
        / "models--BAAI--bge-m3",
    ]

    for base_path in common_paths:
        if base_path.exists():
            snapshots_dir = base_path / "snapshots"
            if snapshots_dir.exists():
                snapshots = sorted(
                    snapshots_dir.iterdir(),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True,
                )
                if snapshots:
                    return str(snapshots[0])

    return None


def get_path(path_name: str) -> Path:
    """获取路径配置"""
    project_root = get_project_root()
    config = get_config()

    path_config = config.get("paths", {})
    relative_path = path_config.get(path_name)

    if relative_path is None:
        raise ValueError(f"Unknown path: {path_name}")

    path = Path(relative_path)
    if not path.is_absolute():
        path = project_root / path
    return path


def get_vectorstore_dir() -> Path:
    """获取向量库目录"""
    return get_path("vectorstore_dir")


def get_case_library_dir() -> Path:
    """获取案例库目录"""
    return get_path("case_library_dir")


def get_settings_dir() -> Path:
    """获取设定目录"""
    return get_path("settings_dir")


def get_techniques_dir() -> Path:
    """获取技法目录"""
    return get_path("techniques_dir")


def get_collection_name(collection_type: str) -> str:
    """获取collection名称"""
    config = get_config()
    collections = config.get("database", {}).get("collections", {})
    return collections.get(collection_type, f"{collection_type}_v2")


if __name__ == "__main__":
    print("=" * 60)
    print("配置信息")
    print("=" * 60)
    print(f"项目根目录: {get_project_root()}")
    print(f"配置文件: {get_config_path()}")
    print(f"Qdrant URL: {get_qdrant_url()}")
    print(f"模型路径: {get_model_path() or '自动下载'}")
    print(f"向量库目录: {get_vectorstore_dir()}")
    print(f"案例库目录: {get_case_library_dir()}")
