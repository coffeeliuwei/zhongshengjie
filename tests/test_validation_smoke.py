"""[N20 2026-04-18] modules/validation 冒烟测试

只验证 import + 实例化 + 配置加载，不验证业务逻辑。
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def test_validation_manager_import():
    """ValidationManager 可 import"""
    from modules.validation.validation_manager import ValidationManager

    assert ValidationManager is not None


def test_validation_manager_instantiate():
    """ValidationManager 可实例化"""
    from modules.validation.validation_manager import ValidationManager

    manager = ValidationManager()
    assert manager is not None
    # vectorstore_dir 应该是 Path 类型
    assert isinstance(manager.vectorstore_dir, Path)


def test_checker_manager_import():
    """CheckerManager 可 import"""
    from modules.validation.checker_manager import CheckerManager

    assert CheckerManager is not None


def test_checker_manager_instantiate():
    """CheckerManager 可实例化且 vectorstore_dir 是 Path"""
    from modules.validation.checker_manager import CheckerManager

    checker = CheckerManager()
    assert checker is not None
    assert isinstance(checker.vectorstore_dir, Path)
    assert isinstance(checker.qdrant_dir, Path)


def test_validation_no_dead_config_loader_fallback():
    """[N14 联动] 确认 HAS_CONFIG_LOADER=True(走 core 包,不走 fallback)"""
    from modules.validation import validation_manager

    assert validation_manager.HAS_CONFIG_LOADER is True, (
        "HAS_CONFIG_LOADER=False 说明 N14 修复回退,from core.config_loader import 失败"
    )
