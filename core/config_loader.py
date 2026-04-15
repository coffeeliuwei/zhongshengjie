#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一配置加载器
==============

提供全局配置访问，支持：
1. config.json 文件配置
2. 环境变量覆盖
3. 默认值兜底

用法：
    from core.config_loader import get_config, get_project_dir, get_model_path

    config = get_config()
    project_dir = get_project_dir()
    model_path = get_model_path()
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

# 默认配置
DEFAULT_CONFIG = {
    "project": {
        "name": "My Novel",
        "version": "1.0.0",
    },
    "paths": {
        "project_root": None,  # 自动检测
        "settings_dir": "设定",
        "techniques_dir": "创作技法",
        "chapters_dir": "章节大纲",
        "content_dir": "正文",
        "experience_dir": "章节经验日志",
        "standards_dir": "写作标准积累",
        "vectorstore_dir": ".vectorstore",
        "case_library_dir": ".case-library",
        "logs_dir": "logs",
        "cache_dir": ".cache",
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
        "model_path": None,  # 自动检测或从环境变量
        "hf_cache_dir": None,  # HuggingFace缓存目录，None表示使用默认位置
        "vector_size": 1024,
    },
    "novel_sources": {
        "directories": [],  # 小说资源目录列表，如 ["E:\\小说资源"]
    },
    "inspiration_engine": {
        "enabled": True,  # Feature Flag: True 启用意外性引擎
        "variant_count": 3,  # 每场景生成的变体数量
        "appraisal_cold_start_threshold": 50,  # 冷启动期：记忆点数<50
        "appraisal_growing_threshold": 300,  # 成长期：记忆点数<300
        "audit_interval_appraisals": 10,  # 每隔多少次鉴赏触发审计
        "overturn_audit_threshold": 10,  # 累计多少次推翻触发审计
        "memory_point_overturn_weight": 2.0,  # 推翻事件的检索权重
    },
}

# 全局配置实例
_global_config: Optional[Dict[str, Any]] = None
_project_root: Optional[Path] = None


def find_project_root() -> Path:
    """自动检测项目根目录"""
    # 从当前文件向上查找
    current = Path(__file__).resolve()

    # 标记文件：README.md, config.example.json, .gitignore
    markers = ["README.md", "config.example.json", ".gitignore", "tools"]

    for parent in current.parents:
        if any((parent / marker).exists() for marker in markers):
            # 额外检查是否有 tools 目录
            if (parent / "tools").exists():
                return parent

    # 如果找不到，使用当前工作目录
    return Path.cwd()


def get_project_root() -> Path:
    """获取项目根目录"""
    global _project_root

    if _project_root is None:
        # 优先从环境变量
        env_root = os.environ.get("NOVEL_PROJECT_ROOT")
        if env_root:
            _project_root = Path(env_root)
        else:
            # 自动检测（不依赖配置文件，避免循环引用）
            _project_root = find_project_root()

    return _project_root


def get_config_path() -> Path:
    """获取配置文件路径"""
    # 优先级：环境变量 > 项目根目录/config.json
    env_config = os.environ.get("NOVEL_CONFIG_PATH")
    if env_config:
        return Path(env_config)

    return get_project_root() / "config.json"


def load_config() -> Dict[str, Any]:
    """加载配置"""
    config = DEFAULT_CONFIG.copy()

    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)

            # 深度合并
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
            print(f"Warning: Failed to load config from {config_path}: {e}")

    return config


def get_config() -> Dict[str, Any]:
    """获取全局配置"""
    global _global_config

    if _global_config is None:
        _global_config = load_config()

    return _global_config


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


def get_model_path() -> Optional[str]:
    """获取模型路径"""
    # 优先级：环境变量 > 配置文件 > 自动检测

    # 1. 环境变量
    env_path = os.environ.get("BGE_M3_MODEL_PATH") or os.environ.get("NOVEL_MODEL_PATH")
    if env_path:
        return env_path

    # 2. 配置文件
    config = get_config()
    config_path = config.get("model", {}).get("model_path")
    if config_path:
        return config_path

    # 3. 自动检测常见位置
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
            # 查找 snapshots 目录
            snapshots_dir = base_path / "snapshots"
            if snapshots_dir.exists():
                # 获取最新的 snapshot
                snapshots = sorted(
                    snapshots_dir.iterdir(),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True,
                )
                if snapshots:
                    return str(snapshots[0])

    # 4. 返回 None，让模型自动下载
    return None


def get_hf_cache_dir() -> Optional[str]:
    """
    获取HuggingFace缓存目录

    优先级：
    1. 环境变量 HF_HOME
    2. 配置文件 model.hf_cache_dir
    3. 默认位置 (E:/huggingface_cache 或 ~/.cache/huggingface)

    Returns:
        str or None: 缓存目录路径
    """
    # 1. 环境变量
    env_cache = os.environ.get("HF_HOME")
    if env_cache:
        return env_cache

    # 2. 配置文件
    config = get_config()
    config_cache = config.get("model", {}).get("hf_cache_dir")
    if config_cache:
        return config_cache

    # 3. 检查默认位置
    default_paths = [
        Path("E:/huggingface_cache"),
        Path.home() / ".cache" / "huggingface",
    ]

    for default_path in default_paths:
        if default_path.exists():
            return str(default_path)

    # 4. 返回 None，使用 HuggingFace 默认位置
    return None


def get_qdrant_url() -> str:
    """获取Qdrant URL"""
    config = get_config()
    host = config.get("database", {}).get("qdrant_host", "localhost")
    port = config.get("database", {}).get("qdrant_port", 6333)
    return f"http://{host}:{port}"


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


def get_skip_rules() -> list:
    """
    获取跳过的校验规则列表

    Returns:
        规则ID列表，如 ["R007", "R008"]
    """
    config = get_config()
    return config.get("validation", {}).get("skip_rules", [])


def get_worldview_config() -> dict:
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


# 便捷函数
def get_settings_dir() -> Path:
    return get_path("settings_dir")


def get_techniques_dir() -> Path:
    return get_path("techniques_dir")


def get_vectorstore_dir() -> Path:
    return get_path("vectorstore_dir")


def get_case_library_dir() -> Path:
    return get_path("case_library_dir")


def get_logs_dir() -> Path:
    return get_path("logs_dir")


def get_cache_dir() -> Path:
    """获取缓存目录"""
    return get_path("cache_dir")


def get_temp_dir() -> Path:
    """获取临时目录（用于避免C盘空间问题）"""
    temp_dir = get_path("temp_dir")
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_contracts_dir() -> Path:
    """获取场景契约存储目录"""
    return get_path("contracts_dir")


def get_novel_extractor_dir() -> Path:
    """获取小说提取器目录 (.novel-extractor)"""
    return get_path("novel_extractor_dir")


def get_world_configs_dir() -> Path:
    """获取世界观配置目录 (.vectorstore/core/world_configs)"""
    return get_path("world_configs_dir")


def get_scene_writer_mapping_path() -> Path:
    """获取场景作家映射文件路径"""
    return get_path("scene_writer_mapping_file")


def get_knowledge_graph_path() -> Path:
    """获取知识图谱文件路径"""
    return get_path("knowledge_graph_file")


def get_qdrant_storage_dir() -> Path:
    """获取Qdrant存储目录"""
    return get_path("qdrant_storage_dir")


def get_config_dir() -> Path:
    """获取配置目录 (config/)"""
    return get_path("config_dir")


def get_world_config_path(world_name: str = None) -> Path:
    """
    获取指定世界观配置文件路径

    Args:
        world_name: 世界观名称，如果为 None 则使用 config.json 中的 current_world

    Returns:
        世界观配置文件的完整路径
    """
    if world_name is None:
        config = get_config()
        world_name = config.get("worldview", {}).get("current_world", "众生界")

    return get_world_configs_dir() / f"{world_name}.json"


def get_novel_sources() -> list:
    """获取小说资源目录列表"""
    config = get_config()
    novel_sources = config.get("novel_sources", {})
    directories = novel_sources.get("directories", [])
    # 过滤空值并转换为Path对象
    return [Path(d) for d in directories if d]


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


def get_realm_order(power_system: str = None) -> list:
    """
    获取境界等级顺序

    支持两种配置方式：
    1. 单一境界体系（向后兼容）：config.json 中的 validation.realm_order
    2. 多境界体系：世界观配置中的 power_systems.*.realms

    Args:
        power_system: 力量体系名称，如 "修仙"、"魔法"、"兽力" 等
                     如果为 None，返回 config.json 中的单一境界配置

    Returns:
        境界等级列表，如 ["炼气期", "筑基期", "金丹期", ...]
    """
    # 模式1：从 config.json 获取单一境界配置（向后兼容）
    if power_system is None:
        config = get_config()
        return config.get("validation", {}).get("realm_order", [])

    # 模式2：从世界观配置获取指定力量体系的境界
    try:
        # 尝试加载当前世界观配置
        world_config = _load_current_world_config()
        if world_config:
            power_systems = world_config.get("power_systems", {})
            system_config = power_systems.get(power_system, {})

            # 不同力量体系使用不同的境界字段名
            realm_fields = [
                "realms",
                "grades",
                "faith_levels",
                "upgrade_levels",
                "blood_realms",
                "ai_levels",
            ]

            for field in realm_fields:
                if field in system_config:
                    return system_config[field]
    except Exception:
        pass

    return []


def get_all_realm_orders() -> dict:
    """
    获取所有力量体系的境界配置

    Returns:
        {
            "修仙": ["炼气期", "筑基期", ...],
            "魔法": ["一级魔法", "二级魔法", ...],
            ...
        }
    """
    result = {}

    # 首先添加 config.json 中的默认配置
    config = get_config()
    default_realms = config.get("validation", {}).get("realm_order", [])
    if default_realms:
        result["default"] = default_realms

    # 然后添加世界观配置中的所有境界
    try:
        world_config = _load_current_world_config()
        if world_config:
            power_systems = world_config.get("power_systems", {})
            realm_fields = [
                "realms",
                "grades",
                "faith_levels",
                "upgrade_levels",
                "blood_realms",
                "ai_levels",
            ]

            for system_name, system_config in power_systems.items():
                for field in realm_fields:
                    if field in system_config:
                        result[system_name] = system_config[field]
                        break
    except Exception:
        pass

    return result


def _load_current_world_config() -> dict:
    """加载当前世界观配置"""
    try:
        import json

        # 从 config.json 获取当前世界观名称
        config = get_config()
        world_name = config.get("worldview", {}).get("current_world", "众生界")

        # 使用配置路径获取世界观配置文件
        world_config_path = get_world_config_path(world_name)

        if world_config_path.exists():
            with open(world_config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass

    return {}


def reset_config():
    """重置配置（用于测试）"""
    global _global_config, _project_root
    _global_config = None
    _project_root = None


def get_quality_thresholds() -> dict:
    """
    获取数据清洗质量阈值配置

    Returns:
        {
            "chinese_ratio_min": 0.6,      # 中文比例阈值
            "novel_features_min": 10,      # 小说特征词数量阈值
            "compression_ratio_min": 0.65, # 压缩率下限
            "compression_ratio_max": 0.80, # 压缩率上限
            "quality_score_min": 0.6,      # 综合质量评分阈值
            "noise_ratio_max": 0.10        # 噪音比例上限
        }
    """
    config = get_config()
    return config.get(
        "quality_thresholds",
        {
            "chinese_ratio_min": 0.6,
            "novel_features_min": 10,
            "compression_ratio_min": 0.65,
            "compression_ratio_max": 0.80,
            "quality_score_min": 0.6,
            "noise_ratio_max": 0.10,
        },
    )


def get_clean_pipeline_config() -> dict:
    """
    获取清洗流程配置

    Returns:
        {
            "clean_dir": ".case-library/clean",
            "use_gpu": True,
            "validate_before_ingest": True
        }
    """
    config = get_config()
    return config.get(
        "clean_pipeline",
        {
            "clean_dir": ".case-library/clean",
            "use_gpu": True,
            "validate_before_ingest": True,
        },
    )


def get_clean_dir() -> Path:
    """获取清洗后小说存储目录"""
    pipeline_config = get_clean_pipeline_config()
    clean_dir = pipeline_config.get("clean_dir", ".case-library/clean")
    return get_project_root() / clean_dir


# 初始化时打印配置信息（可选）
if __name__ == "__main__":
    print("=" * 60)
    print("配置信息")
    print("=" * 60)
    print(f"项目根目录: {get_project_root()}")
    print(f"配置文件: {get_config_path()}")
    print(f"Qdrant URL: {get_qdrant_url()}")
    print(f"模型路径: {get_model_path() or '自动下载'}")
    print(f"设定目录: {get_settings_dir()}")
    print(f"技法目录: {get_techniques_dir()}")
    print(f"向量库目录: {get_vectorstore_dir()}")
