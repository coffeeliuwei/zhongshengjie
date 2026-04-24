# tests/test_workflow_integration.py
"""Tests for workflow integration - method signature verification."""

import sys
from pathlib import Path
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def test_workflow_bridge_exists():
    """验证 workflow_bridge 模块存在且可导入"""
    from core.inspiration.workflow_bridge import phase1_dispatch, _resolve_writer_skill

    assert callable(phase1_dispatch)
    assert callable(_resolve_writer_skill)


def test_phase1_dispatch_signature():
    """验证 phase1_dispatch 函数签名"""
    from core.inspiration.workflow_bridge import phase1_dispatch
    import inspect

    sig = inspect.signature(phase1_dispatch)
    params = list(sig.parameters.keys())

    assert "scene_type" in params
    assert "scene_context" in params
    assert "original_writers" in params
    assert "config" in params


@pytest.mark.skip(
    reason="[M4] .vectorstore/core/workflow.py 已在 M2-β 归档；"
    "本测试只验证文档字符串存在，目标文件不再维护。"
    "新框架的等价测试由 test_workflow_inspiration_branch.py 等覆盖。"
)
def test_workflow_method_documentation():
    """[已废弃] 原验证 .vectorstore/core/workflow.py 中方法文档"""
    pass


def test_integration_chain():
    """验证集成链条完整"""
    # 1. constraint_library
    from core.inspiration.constraint_library import ConstraintLibrary

    lib = ConstraintLibrary()
    assert lib.count_active() >= 40

    # 2. workflow_bridge（v2：phase1_dispatch 始终返回 original 模式）
    from core.inspiration.workflow_bridge import phase1_dispatch
    from core.config_loader import DEFAULT_CONFIG

    result = phase1_dispatch(
        scene_type="战斗",
        scene_context={"outline": "X"},
        original_writers=["剑尘"],
        config=DEFAULT_CONFIG,
        seed=42,
    )
    assert result["mode"] == "original"
    assert result["writers"] == ["剑尘"]
