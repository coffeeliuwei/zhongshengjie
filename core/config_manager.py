"""config_manager.py — 已废弃（Deprecated）

此模块与 core.config_loader 功能重叠。
新代码请直接使用 core.config_loader，此模块将在后续版本移除。
"""

import warnings

warnings.warn(
    "core.config_manager is deprecated. Use core.config_loader instead.",
    DeprecationWarning,
    stacklevel=2,
)

"""
配置管理器
统一管理项目所有配置，支持CONFIG.md扩展和动态配置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

# 从配置加载器导入路径获取函数
try:
    from .config_loader import get_project_root

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False


@dataclass
class DatabaseConfig:
    """数据库配置"""

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    collections: Dict[str, str] = field(
        default_factory=lambda: {
            "novel_settings": "novel_settings",
            "writing_techniques": "writing_techniques",
            "case_library": "case_library",
            "creation_context": "creation_context",  # 新增：作家上下文存储
        }
    )


@dataclass
class DirectoryConfig:
    """目录配置"""

    # 核心目录
    root: Path = Path(".")
    settings_dir: Path = Path("设定")
    techniques_dir: Path = Path("创作技法")
    chapters_dir: Path = Path("章节大纲")
    content_dir: Path = Path("正文")

    # 系统目录
    vectorstore_dir: Path = Path(".vectorstore")
    case_library_dir: Path = Path(".case-library")
    modules_dir: Path = Path("modules")

    # 输出目录
    logs_dir: Path = Path("logs")
    cache_dir: Path = Path(".cache")
    archive_dir: Path = Path("存档")

    # 用户可自定义目录（小说资源）
    custom_resources: Dict[str, Path] = field(default_factory=dict)

    def resolve_paths(self, base_path: Path) -> None:
        """将所有路径转换为绝对路径"""
        for attr_name in [
            "settings_dir",
            "techniques_dir",
            "chapters_dir",
            "content_dir",
            "vectorstore_dir",
            "case_library_dir",
            "modules_dir",
            "logs_dir",
            "cache_dir",
            "archive_dir",
        ]:
            attr_value = getattr(self, attr_name)
            if not attr_value.is_absolute():
                setattr(self, attr_name, base_path / attr_value)

        # 处理自定义资源目录
        for resource_id, rel_path in self.custom_resources.items():
            if not rel_path.is_absolute():
                self.custom_resources[resource_id] = base_path / rel_path


@dataclass
class ModuleConfig:
    """模块配置"""

    # 入库模块
    knowledge_base_enabled: bool = True
    knowledge_base_auto_sync: bool = False

    # 验证模块
    validation_enabled: bool = True
    validation_thresholds: Dict[str, int] = field(
        default_factory=lambda: {
            "世界自洽": 7,
            "人物立体": 6,
            "情感真实": 6,
            "战斗逻辑": 6,
            "文风克制": 6,
            "剧情张力": 6,
        }
    )

    # 创作模块
    creation_enabled: bool = True
    creation_max_iterations: int = 3
    creation_parallel_enabled: bool = True
    creation_parallel_config: Dict[str, Any] = field(
        default_factory=lambda: {
            "max_parallel_writers": 3,
            "timeout_per_writer": 300,
            "retry_on_failure": True,
        }
    )

    # 可视化模块
    visualization_enabled: bool = True


@dataclass
class WriterConfig:
    """作家配置"""

    scene_writer_mapping_file: str = "scene_writer_mapping.json"
    skills_base_path: Optional[str] = (
        None  # 从 config.json 读取，默认使用 ~/.agents/skills
    )

    # 作家偏好映射
    writer_preferences: Dict[str, str] = field(
        default_factory=lambda: {
            "世界观": "novelist-canglan",
            "剧情": "novelist-xuanyi",
            "人物": "novelist-moyan",
            "战斗": "novelist-jianchen",
            "氛围": "novelist-yunxi",
        }
    )

    def get_skills_base_path(self) -> Path:
        """获取 skills 基础路径"""
        if self.skills_base_path:
            return Path(self.skills_base_path)
        return Path.home() / ".agents" / "skills"


class ConfigManager:
    """配置管理器"""

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化配置管理器

        Args:
            project_root: 项目根目录，默认从配置加载或当前工作目录
        """
        if HAS_CONFIG_LOADER:
            self.project_root = project_root or get_project_root()
        else:
            self.project_root = project_root or Path.cwd()
        self.config_file = self.project_root / "CONFIG.md"
        self.system_config_file = self.project_root / "system_config.json"

        # 初始化配置组件
        self.db_config = DatabaseConfig()
        self.dir_config = DirectoryConfig()
        self.module_config = ModuleConfig()
        self.writer_config = WriterConfig()

        # 加载配置
        self._load_config()

    def _load_config(self) -> None:
        """加载所有配置"""
        # 加载CONFIG.md
        if self.config_file.exists():
            self._parse_config_md()

        # 加载system_config.json（如果存在）
        if self.system_config_file.exists():
            self._load_system_config()

        # 解析路径
        self.dir_config.resolve_paths(self.project_root)

    def _parse_config_md(self) -> None:
        """解析CONFIG.md文件"""
        # CONFIG.md目前是简单格式，主要提供基本信息
        # 后续可以扩展为YAML或JSON块格式
        # 这里只提取基本信息，详细配置由system_config.json提供
        pass

    def _load_system_config(self) -> None:
        """加载system_config.json"""
        with open(self.system_config_file, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        # 更新数据库配置
        if "database" in config_data:
            db_data = config_data["database"]
            self.db_config.qdrant_host = db_data.get("host", self.db_config.qdrant_host)
            self.db_config.qdrant_port = db_data.get("port", self.db_config.qdrant_port)
            if "collections" in db_data:
                self.db_config.collections.update(db_data["collections"])

        # 更新目录配置
        if "directories" in config_data:
            dir_data = config_data["directories"]
            for key, value in dir_data.items():
                if key == "custom_resources":
                    self.dir_config.custom_resources = {
                        rid: Path(p) for rid, p in value.items()
                    }
                elif hasattr(self.dir_config, key):
                    setattr(self.dir_config, key, Path(value))

        # 更新模块配置
        if "modules" in config_data:
            mod_data = config_data["modules"]
            for key, value in mod_data.items():
                if hasattr(self.module_config, key):
                    setattr(self.module_config, key, value)

        # 更新作家配置
        if "writers" in config_data:
            writer_data = config_data["writers"]
            for key, value in writer_data.items():
                if hasattr(self.writer_config, key):
                    setattr(self.writer_config, key, value)

    def save_system_config(self) -> None:
        """保存system_config.json"""
        config_data = {
            "database": {
                "host": self.db_config.qdrant_host,
                "port": self.db_config.qdrant_port,
                "collections": self.db_config.collections,
            },
            "directories": {
                key: str(value) if isinstance(value, Path) else value
                for key, value in self.dir_config.__dict__.items()
                if not key.startswith("_")
            },
            "modules": {
                key: value
                for key, value in self.module_config.__dict__.items()
                if not key.startswith("_")
            },
            "writers": {
                key: value
                for key, value in self.writer_config.__dict__.items()
                if not key.startswith("_")
            },
        }

        with open(self.system_config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

    def get_db_connection_url(self) -> str:
        """获取数据库连接URL"""
        return f"http://{self.db_config.qdrant_host}:{self.db_config.qdrant_port}"

    def get_collection_name(self, collection_type: str) -> str:
        """获取集合名称"""
        return self.db_config.collections.get(collection_type, collection_type)

    def ensure_directories(self) -> None:
        """确保所有目录存在"""
        for attr_name in [
            "settings_dir",
            "techniques_dir",
            "chapters_dir",
            "content_dir",
            "vectorstore_dir",
            "case_library_dir",
            "modules_dir",
            "logs_dir",
            "cache_dir",
            "archive_dir",
        ]:
            dir_path = getattr(self.dir_config, attr_name)
            dir_path.mkdir(parents=True, exist_ok=True)

        # 创建modules子目录
        for submodule in ["knowledge_base", "validation", "creation", "visualization"]:
            (self.dir_config.modules_dir / submodule).mkdir(parents=True, exist_ok=True)

    def update_custom_resource(self, resource_id: str, path: Path) -> None:
        """
        更新自定义资源目录

        Args:
            resource_id: 资源ID
            path: 资源路径
        """
        self.dir_config.custom_resources[resource_id] = path
        if not path.is_absolute():
            self.dir_config.custom_resources[resource_id] = self.project_root / path

    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            "project_root": str(self.project_root),
            "database": {
                "url": self.get_db_connection_url(),
                "collections": list(self.db_config.collections.keys()),
            },
            "directories": {
                key: str(value)
                for key, value in self.dir_config.__dict__.items()
                if not key.startswith("_") and key != "custom_resources"
            },
            "custom_resources": {
                rid: str(p) for rid, p in self.dir_config.custom_resources.items()
            },
            "modules": {
                "knowledge_base": self.module_config.knowledge_base_enabled,
                "validation": self.module_config.validation_enabled,
                "creation": self.module_config.creation_enabled,
                "visualization": self.module_config.visualization_enabled,
            },
        }


# 全局配置实例（延迟初始化）
_global_config: Optional[ConfigManager] = None


def get_config(project_root: Optional[Path] = None) -> ConfigManager:
    """
    获取全局配置实例

    Args:
        project_root: 项目根目录

    Returns:
        ConfigManager实例
    """
    global _global_config
    if _global_config is None or project_root is not None:
        _global_config = ConfigManager(project_root)
    return _global_config
