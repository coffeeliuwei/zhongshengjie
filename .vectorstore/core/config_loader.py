# -*- coding: utf-8 -*-
"""
配置加载器代理模块

将请求转发到 core.config_loader 模块
"""

import sys
from pathlib import Path

# 添加项目根目录到 sys.path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 从真正的配置加载器导入所有内容
from core.config_loader import *

# 重新导出所有函数
__all__ = [
    "get_config",
    "get_project_root",
    "get_qdrant_url",
    "get_model_path",
    "get_collection_name",
    "get_vectorstore_dir",
    "get_case_library_dir",
    "get_novel_extractor_dir",
    "get_novel_sources",
    "get_skills_base_path",
    "get_path",
    "get_world_configs_dir",
    "get_scene_writer_mapping_path",
    "get_knowledge_graph_path",
    "get_qdrant_storage_dir",
    "get_realm_order",
    "get_all_realm_orders",
]
