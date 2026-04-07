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
        "cache_dir": ".cache",
        "contracts_dir": "scene_contracts",
    },
    "validation": {
        "realm_order": ["凡人", "觉醒", "淬体", "凝脉", "结丹", "元婴", "化神"],
        "skip_rules": [],
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
    # 必须同时存在这些文件/目录才能确认是项目根目录
    required_markers = ["README.md", "config.example.json"]
    optional_markers = [".gitignore", "tools", ".git"]

    for parent in current.parents:
        # 检查必需标记
        if all((parent / marker).exists() for marker in required_markers):
            return parent

    # 回退：检查 config.json
    for parent in current.parents:
        if (parent / "config.json").exists():
            return parent

    return Path.cwd()


def get_project_root() -> Path:
    """获取项目根目录"""
    global _project_root
    if _project_root is None:
        # 优先级：环境变量 > 自动检测 > config.json
        env_root = os.environ.get("NOVEL_PROJECT_ROOT")
        if env_root:
            _project_root = Path(env_root)
        else:
            # 先用自动检测
            _project_root = find_project_root()

            # 再尝试从 config.json 读取覆盖
            config_path = _project_root / "config.json"
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        user_config = json.load(f)
                    config_root = user_config.get("paths", {}).get("project_root")
                    if config_root:
                        _project_root = Path(config_root)
                except Exception:
                    pass
    return _project_root


def get_config_path() -> Optional[Path]:
    """获取config.json文件的路径"""
    # 使用 find_project_root() 避免循环依赖
    root = find_project_root()
    config_paths = [
        root / "config.json",
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
    db_config = config.get("database", {})

    # 如果直接配置了 qdrant_url，优先使用
    if "qdrant_url" in db_config:
        return db_config["qdrant_url"]

    host = db_config.get("qdrant_host", "localhost")
    port = db_config.get("qdrant_port", 6333)
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


def get_cache_dir() -> Path:
    """获取缓存目录"""
    return get_path("cache_dir")


def get_contracts_dir() -> Path:
    """获取场景契约存储目录"""
    cache_dir = get_cache_dir()
    config = get_config()
    contracts_subdir = config.get("paths", {}).get("contracts_dir", "scene_contracts")
    return cache_dir / contracts_subdir


def get_realm_order() -> Optional[list]:
    """
    获取境界等级顺序（用于R012规则检测境界倒退）

    Returns:
        境界列表（从低到高），如果配置为null则返回None（跳过检测）
    """
    config = get_config()
    return config.get("validation", {}).get("realm_order")


def get_skip_rules() -> list:
    """
    获取跳过的校验规则列表

    Returns:
        规则ID列表，如 ["R007", "R008"]
    """
    config = get_config()
    return config.get("validation", {}).get("skip_rules", [])


def get_skills_base_path() -> Path:
    """
    获取Skills基础路径

    Returns:
        Skills目录路径
    """
    config = get_config()
    skills_path = config.get("paths", {}).get("skills_base_path")

    if skills_path:
        return Path(skills_path)

    # 默认位置
    return Path.home() / ".agents" / "skills"


def get_novel_sources() -> list:
    """
    获取小说资源目录列表

    Returns:
        目录路径列表
    """
    config = get_config()
    return config.get("novel_sources", {}).get("directories", [])


def get_worldview_config() -> Dict[str, Any]:
    """
    获取世界观配置

    Returns:
        {
            "current_world": "众生界",
            "outline_path": "总大纲.md",
            "auto_sync": True
        }
    """
    config = get_config()
    return config.get(
        "worldview",
        {"current_world": "众生界", "outline_path": "总大纲.md", "auto_sync": False},
    )


def get_current_world() -> str:
    """获取当前世界观名称"""
    worldview = get_worldview_config()
    return worldview.get("current_world", "众生界")


def get_outline_path() -> Optional[str]:
    """获取大纲文件路径"""
    worldview = get_worldview_config()
    outline_path = worldview.get("outline_path")
    if outline_path:
        return str(get_project_root() / outline_path)
    return None


def is_auto_sync_enabled() -> bool:
    """检查是否启用自动同步"""
    worldview = get_worldview_config()
    return worldview.get("auto_sync", False)


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


def get_database_timeout() -> int:
    """获取数据库超时时间（秒）"""
    config = get_config()
    return config.get("database", {}).get("timeout", 10)


def get_batch_size() -> int:
    """获取批处理大小"""
    config = get_config()
    return config.get("model", {}).get("batch_size", 20)


def get_retrieval_config() -> dict:
    """
    获取检索配置

    Returns:
        {
            "dense_limit": 100,
            "sparse_limit": 100,
            "fusion_limit": 50,
            "max_content_length": 3000,
            "max_payload_size": 8000
        }
    """
    config = get_config()
    return config.get(
        "retrieval",
        {
            "dense_limit": 100,
            "sparse_limit": 100,
            "fusion_limit": 50,
            "max_content_length": 3000,
            "max_payload_size": 8000,
        },
    )


def get_max_content_length() -> int:
    """获取最大内容长度"""
    return get_retrieval_config().get("max_content_length", 3000)


def get_max_payload_size() -> int:
    """获取最大payload大小"""
    return get_retrieval_config().get("max_payload_size", 8000)


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
