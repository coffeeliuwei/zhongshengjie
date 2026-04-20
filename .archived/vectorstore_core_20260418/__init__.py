# -*- coding: utf-8 -*-
"""
核心检索与工作流模块

包含知识检索、技法检索、案例检索、工作流、知识图谱等核心功能。
"""

import sys
from pathlib import Path

# 添加项目根目录到 sys.path（确保能找到 core.config_loader）
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from .knowledge_search import KnowledgeSearcher
from .technique_search import TechniqueSearcher
from .case_search import CaseSearcher
from .workflow import NovelWorkflow
from .knowledge_graph import KnowledgeGraph
from .data_model import EntityType

__all__ = [
    "KnowledgeSearcher",
    "TechniqueSearcher",
    "CaseSearcher",
    "NovelWorkflow",
    "KnowledgeGraph",
    "EntityType",
]
