"""
知识库模块 - 入口文件

⚠️ 状态说明：扩展备用，当前不启用

当前小说工作流通过 novelist-technique-search Skill 直接检索向量库，
无需通过本 Python 模块。本模块为未来扩展预留：
  - Web 后端 API 接口
  - CLI 批量同步命令
  - 自动化数据迁移脚本

对话形式使用时，AI 通过 Skills 调用向量检索，无需此模块。

功能清单（预留）：
  - 向量数据库同步（novel_settings/writing_techniques/case_library）
  - 检索接口（search_novel/search_technique/search_case）
  - 降级模式（Qdrant不可用时使用本地缓存）
"""

import sys
from pathlib import Path

# 从配置加载器导入路径获取函数
try:
    from core.config_loader import get_project_root, get_qdrant_url

    _config_host, _config_port = get_qdrant_url().replace("http://", "").split(":")
    _config_port = int(_config_port)
except ImportError:
    # 兼容独立运行场景
    def get_project_root():
        return Path.cwd()

    _config_host = "localhost"
    _config_port = 6333

# 添加项目根目录到路径（使用配置加载器获取路径）
project_root = get_project_root()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from .sync_manager import SyncManager
from .search_manager import SearchManager
from .vectorizer_manager import VectorizerManager

# BGE-M3 轻量混合检索管理器 (Dense + Sparse)
try:
    from .hybrid_search_manager_lite import HybridSearchManager

    HYBRID_SEARCH_AVAILABLE = True
except ImportError:
    HYBRID_SEARCH_AVAILABLE = False
    HybridSearchManager = None

# 导入数据库连接管理器
try:
    from core.db_connection import get_db_manager, DatabaseStatus

    DB_MANAGER_AVAILABLE = True
except ImportError:
    DB_MANAGER_AVAILABLE = False


class KnowledgeBase:
    """
    知识库统一接口

    整合同步、检索、向量化三大功能，提供统一API

    支持降级模式：
    - Qdrant 可用时：向量检索
    - Qdrant 不可用时：本地缓存 + 文本匹配
    """

    def __init__(self, use_docker: bool = True, auto_check_db: bool = True):
        """
        初始化知识库

        Args:
            use_docker: 是否优先使用Docker Qdrant
            auto_check_db: 是否自动检测数据库连接
        """
        # 初始化数据库连接管理器
        self.db_manager = None
        if DB_MANAGER_AVAILABLE and auto_check_db:
            try:
                self.db_manager = get_db_manager(
                    host=_config_host,
                    port=_config_port,
                    cache_dir=get_project_root() / ".cache" / "db_cache",
                    auto_check=True,
                )
            except Exception:
                pass

        # 初始化各管理器
        self.sync_manager = SyncManager(use_docker=use_docker)
        self.search_manager = SearchManager(use_docker=use_docker)
        self.vectorizer_manager = VectorizerManager()

        # 降级模式标志
        self._degraded_mode = False
        if self.db_manager and not self.db_manager.is_available:
            self._degraded_mode = True
            print("⚠️ 数据库不可用，使用本地缓存模式")

    @property
    def is_degraded(self) -> bool:
        """是否处于降级模式"""
        return self._degraded_mode

    @property
    def db_status(self) -> str:
        """获取数据库状态"""
        if self.db_manager:
            return self.db_manager.status.value
        return "unknown"

    def check_database(self) -> dict:
        """
        检查数据库连接状态

        Returns:
            连接信息字典
        """
        if self.db_manager:
            info = self.db_manager.check_connection()
            return {
                "status": info.status.value,
                "host": info.host,
                "port": info.port,
                "message": info.message,
                "latency_ms": info.latency_ms,
                "collections": info.collections,
            }
        return {"status": "unavailable", "message": "数据库管理器未初始化"}

    # ==================== 同步接口 ====================

    def sync(self, target: str = "all", rebuild: bool = False) -> dict:
        """
        同步数据到向量库

        Args:
            target: 同步目标 - "novel", "technique", "case", "all"
            rebuild: 是否重建数据库

        Returns:
            同步结果统计
        """
        return self.sync_manager.sync(target=target, rebuild=rebuild)

    def sync_novel_settings(self, rebuild: bool = False) -> int:
        """同步小说设定"""
        return self.sync_manager.sync_novel_settings(rebuild=rebuild)

    def sync_techniques(self, rebuild: bool = False) -> int:
        """同步创作技法"""
        return self.sync_manager.sync_techniques(rebuild=rebuild)

    def sync_cases(self, rebuild: bool = False) -> int:
        """同步案例库"""
        return self.sync_manager.sync_cases(rebuild=rebuild)

    # ==================== 检索接口 ====================

    def search_novel(
        self,
        query: str,
        entity_type: str = None,
        top_k: int = 5,
    ) -> list:
        """
        检索小说设定

        Args:
            query: 查询文本
            entity_type: 实体类型过滤（角色、势力、力量体系等）
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        return self.search_manager.search_novel(
            query=query,
            entity_type=entity_type,
            top_k=top_k,
        )

    def search_technique(
        self,
        query: str,
        dimension: str = None,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list:
        """
        检索创作技法

        Args:
            query: 查询文本
            dimension: 维度过滤（世界观、剧情、人物、战斗等）
            top_k: 返回数量
            min_score: 最低相似度

        Returns:
            检索结果列表
        """
        return self.search_manager.search_technique(
            query=query,
            dimension=dimension,
            top_k=top_k,
            min_score=min_score,
        )

    def search_case(
        self,
        query: str,
        scene_type: str = None,
        genre: str = None,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> list:
        """
        检索标杆案例

        Args:
            query: 查询文本
            scene_type: 场景类型过滤
            genre: 题材类型过滤
            top_k: 返回数量
            min_score: 最低相似度

        Returns:
            检索结果列表
        """
        return self.search_manager.search_case(
            query=query,
            scene_type=scene_type,
            genre=genre,
            top_k=top_k,
            min_score=min_score,
        )

    def get_character(self, name: str) -> dict:
        """获取角色设定"""
        return self.search_manager.get_character(name)

    def get_faction(self, name: str) -> dict:
        """获取势力设定"""
        return self.search_manager.get_faction(name)

    def get_power_branch(self, name: str) -> dict:
        """获取力量派别"""
        return self.search_manager.get_power_branch(name)

    # ==================== 统计接口 ====================

    def get_stats(self) -> dict:
        """获取数据库统计信息"""
        return self.search_manager.get_stats()

    def list_characters(self) -> list:
        """列出所有角色"""
        return self.search_manager.list_characters()

    def list_factions(self) -> list:
        """列出所有势力"""
        return self.search_manager.list_factions()

    def list_dimensions(self) -> list:
        """列出所有技法维度"""
        return self.search_manager.list_dimensions()

    # ==================== 向量化接口 ====================

    def vectorize_knowledge(self, rebuild: bool = False) -> dict:
        """
        向量化大纲/设定

        Args:
            rebuild: 是否重建数据库

        Returns:
            向量化结果统计
        """
        return self.vectorizer_manager.vectorize_knowledge(rebuild=rebuild)

    def vectorize_techniques(self, rebuild: bool = False) -> dict:
        """
        向量化创作技法

        Args:
            rebuild: 是否重建数据库

        Returns:
            向量化结果统计
        """
        return self.vectorizer_manager.vectorize_techniques(rebuild=rebuild)


# 导出主要类
__all__ = [
    "KnowledgeBase",
    "SyncManager",
    "SearchManager",
    "VectorizerManager",
    "HybridSearchManager",  # BGE-M3 混合检索 (Dense + Sparse)
]
