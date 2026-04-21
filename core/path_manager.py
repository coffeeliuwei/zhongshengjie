"""
路径管理器
统一管理项目所有文件路径，提供便捷的路径访问接口
"""

from pathlib import Path
from typing import Dict, Optional, List
from .config_manager import get_config, ConfigManager


class PathManager:
    """路径管理器"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """
        初始化路径管理器

        Args:
            config: 配置管理器实例，默认使用全局配置
        """
        self.config = config or get_config()
        self._cache: Dict[str, Path] = {}

    # ==================== 核心文件路径 ====================

    @property
    def config_file(self) -> Path:
        """CONFIG.md文件"""
        return self.config.project_root / "CONFIG.md"

    @property
    def project_guide(self) -> Path:
        """PROJECT_GUIDE.md文件"""
        return self.config.project_root / "PROJECT_GUIDE.md"

    @property
    def system_config(self) -> Path:
        """system_config.json文件"""
        return self.config.project_root / "system_config.json"

    # ==================== 设定文件路径 ====================

    @property
    def main_outline(self) -> Path:
        """总大纲.md"""
        return self.config.dir_config.settings_dir / "总大纲.md"

    @property
    def character_profiles(self) -> Path:
        """人物谱.md"""
        return self.config.dir_config.settings_dir / "人物谱.md"

    @property
    def factions(self) -> Path:
        """十大势力.md"""
        return self.config.dir_config.settings_dir / "十大势力.md"

    @property
    def power_system(self) -> Path:
        """力量体系.md"""
        return self.config.dir_config.settings_dir / "力量体系.md"

    @property
    def timeline(self) -> Path:
        """时间线.md"""
        return self.config.dir_config.settings_dir / "时间线.md"

    # ==================== 追踪系统路径 ====================

    @property
    def hook_ledger(self) -> Path:
        """伏笔追踪"""
        return self.config.dir_config.settings_dir / "hook_ledger.md"

    @property
    def payoff_tracking(self) -> Path:
        """承诺追踪"""
        return self.config.dir_config.settings_dir / "payoff_tracking.md"

    @property
    def information_boundary(self) -> Path:
        """信息边界"""
        return self.config.dir_config.settings_dir / "information_boundary.md"

    @property
    def resource_ledger(self) -> Path:
        """资源账本"""
        return self.config.dir_config.settings_dir / "resource_ledger.md"

    # ==================== 技法文件路径 ====================

    @property
    def checklist(self) -> Path:
        """创作检查清单"""
        return self.config.dir_config.techniques_dir / "01-创作检查清单.md"

    def get_technique_dimension_dir(self, dimension: str) -> Path:
        """
        获取技法维度目录

        Args:
            dimension: 维度名称（如"世界观维度"、"剧情维度"等）

        Returns:
            维度目录路径
        """
        return self.config.dir_config.techniques_dir / dimension

    # ==================== 正文文件路径 ====================

    def get_chapter_file(self, chapter_name: str) -> Path:
        """
        获取章节文件路径

        Args:
            chapter_name: 章节名称（如"第一章-天裂")

        Returns:
            章节文件路径
        """
        return self.config.dir_config.content_dir / f"{chapter_name}.md"

    def get_chapter_outline(self, chapter_name: str) -> Path:
        """
        获取章节大纲文件路径

        Args:
            chapter_name: 章节名称

        Returns:
            章节大纲文件路径
        """
        return self.config.dir_config.chapters_dir / f"{chapter_name}大纲.md"

    # ==================== 系统路径 ====================

    @property
    def vectorstore_dir(self) -> Path:
        """向量数据库目录"""
        return self.config.dir_config.vectorstore_dir

    # [N19 2026-04-18] 已删除 4 个返回 .vectorstore/*.py 死路径的 property:
    # workflow_script / verify_all_script / checklist_scorer_script / verification_history_script
    # 原因: M2-β 后对应 .py 文件已归档至 .archived/vectorstore_core_20260418/
    # scene_writer_mapping 保留（JSON 数据文件可能仍在 .vectorstore/）

    @property
    def scene_writer_mapping(self) -> Path:
        """场景-作家映射文件"""
        return self.config.dir_config.vectorstore_dir / "scene_writer_mapping.json"

    @property
    def knowledge_graph(self) -> Path:
        """知识图谱文件"""
        return self.config.dir_config.vectorstore_dir / "knowledge_graph.json"

    @property
    def case_library_dir(self) -> Path:
        """案例库目录"""
        return self.config.dir_config.case_library_dir

    # ==================== 模块路径 ====================

    def get_module_dir(self, module_name: str) -> Path:
        """
        获取模块目录路径

        Args:
            module_name: 模块名称（knowledge_base/validation/creation/visualization）

        Returns:
            模块目录路径
        """
        return self.config.dir_config.modules_dir / module_name

    # ==================== 日志和缓存 ====================

    @property
    def logs_dir(self) -> Path:
        """日志目录"""
        return self.config.dir_config.logs_dir

    def get_log_file(self, log_name: str) -> Path:
        """
        获取日志文件路径

        Args:
            log_name: 日志名称

        Returns:
            日志文件路径
        """
        return self.logs_dir / f"{log_name}.log"

    @property
    def cache_dir(self) -> Path:
        """缓存目录"""
        return self.config.dir_config.cache_dir

    # ==================== 自定义资源路径 ====================

    def get_custom_resource(self, resource_id: str) -> Optional[Path]:
        """
        获取自定义资源路径

        Args:
            resource_id: 资源ID

        Returns:
            资源路径，不存在返回None
        """
        return self.config.dir_config.custom_resources.get(resource_id)

    def add_custom_resource(self, resource_id: str, path: Path) -> None:
        """
        添加自定义资源路径

        Args:
            resource_id: 资源ID
            path: 资源路径
        """
        self.config.update_custom_resource(resource_id, path)

    # ==================== 验证文件路径 ====================

    # [N19 2026-04-18] 注释占位：原 verify_all_script / checklist_scorer_script / verification_history_script
    # 三个 property 已删除，因为对应 .py 文件在 M2-β 后归档到 .archived/vectorstore_core_20260418/

    # ==================== 工具方法 ====================

    def detect_project_root(self) -> Path:
        """
        检测项目根目录

        从当前工作目录向上搜索，直到找到项目标志文件。
        这是公共方法，避免多个模块重复实现相同逻辑。

        Returns:
            项目根目录Path对象
        """
        current = Path.cwd()
        markers = ["config.json", ".git", "README.md", "总大纲.md"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                return parent

        # 如果找不到，返回当前目录
        return current

    def list_setting_files(self) -> List[Path]:
        """列出所有设定文件"""
        return list(self.config.dir_config.settings_dir.glob("*.md"))

    def list_technique_files(self) -> List[Path]:
        """列出所有技法文件"""
        return list(self.config.dir_config.techniques_dir.rglob("*.md"))

    def list_chapter_files(self) -> List[Path]:
        """列出所有章节文件"""
        return list(self.config.dir_config.content_dir.glob("*.md"))

    def ensure_path(self, path: Path) -> Path:
        """
        确保路径存在

        Args:
            path: 目标路径

        Returns:
            已创建的路径
        """
        path.mkdir(parents=True, exist_ok=True)
        return path

    def resolve_relative_path(self, relative_path: str) -> Path:
        """
        将相对路径转换为绝对路径

        Args:
            relative_path: 相对路径字符串

        Returns:
            绝对路径
        """
        path = Path(relative_path)
        if not path.is_absolute():
            path = self.config.project_root / path
        return path


# 全局路径管理实例（延迟初始化）
_global_path_manager: Optional[PathManager] = None


def get_path_manager(config: Optional[ConfigManager] = None) -> PathManager:
    """
    获取全局路径管理实例

    Args:
        config: 配置管理器实例

    Returns:
        PathManager实例
    """
    global _global_path_manager
    if _global_path_manager is None or config is not None:
        _global_path_manager = PathManager(config)
    return _global_path_manager
