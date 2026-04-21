"""[N20 2026-04-18] modules/visualization 冒烟测试"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def test_stats_visualizer_import():
    from modules.visualization.stats_visualizer import StatsVisualizer

    assert StatsVisualizer is not None


def test_stats_visualizer_instantiate():
    from modules.visualization.stats_visualizer import StatsVisualizer

    viz = StatsVisualizer()
    assert isinstance(viz.vectorstore_dir, Path)


def test_graph_visualizer_import():
    from modules.visualization.graph_visualizer import GraphVisualizer

    assert GraphVisualizer is not None


def test_db_visualizer_import():
    from modules.visualization.db_visualizer import DBVisualizer

    assert DBVisualizer is not None


def test_db_visualizer_instantiate():
    from modules.visualization.db_visualizer import DBVisualizer

    viz = DBVisualizer()
    assert isinstance(viz.vectorstore_dir, Path)
