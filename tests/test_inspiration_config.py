# tests/test_inspiration_config.py
"""Tests for inspiration_engine config loading."""

import sys
import json
import pytest
import tempfile
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.config_loader import DEFAULT_CONFIG, load_config, get_config_path


def test_default_config_includes_inspiration_engine():
    """DEFAULT_CONFIG 必须包含 inspiration_engine 区块且默认 enabled=True"""
    assert "inspiration_engine" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["inspiration_engine"]["enabled"] is True
    assert DEFAULT_CONFIG["inspiration_engine"]["variant_count"] == 3


def test_user_config_can_override_inspiration_engine():
    """用户配置文件可覆盖 enabled 字段"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "config.json"
        config_path.write_text(
            json.dumps({"inspiration_engine": {"enabled": False}}), encoding="utf-8"
        )

        # 重新加载配置
        import core.config_loader as config_loader

        # 保存原始状态
        original_path_func = config_loader.get_config_path
        original_config = config_loader._global_config

        # 临时覆盖配置路径
        config_loader._global_config = None
        config_loader.get_config_path = lambda: config_path

        config = config_loader.load_config()
        assert config["inspiration_engine"]["enabled"] is False
        # 未覆盖字段保持默认
        assert config["inspiration_engine"]["variant_count"] == 3

        # 恢复原始状态
        config_loader.get_config_path = original_path_func
        config_loader._global_config = original_config
