"""[N20 2026-04-18] modules/migration 冒烟测试"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def test_export_template_import():
    """export_template 模块可 import"""
    from modules.migration import export_template

    assert export_template is not None


def test_init_environment_import():
    """init_environment 模块可 import"""
    from modules.migration import init_environment

    assert init_environment is not None
