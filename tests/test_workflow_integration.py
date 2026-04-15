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


def test_workflow_method_documentation():
    """验证 workflow.py 中方法文档"""
    workflow_path = project_root / ".vectorstore" / "core" / "workflow.py"
    content = workflow_path.read_text(encoding="utf-8")

    assert "def get_phase1_dispatch" in content
    assert "Stage 4 Phase 1 灵感引擎分发" in content
    assert "from core.inspiration.workflow_bridge import phase1_dispatch" in content


def test_integration_chain():
    """验证集成链条完整"""
    # 1. constraint_library
    from core.inspiration.constraint_library import ConstraintLibrary

    lib = ConstraintLibrary()
    assert lib.count_active() >= 40

    # 2. variant_generator
    from core.inspiration.variant_generator import generate_variant_specs

    specs = generate_variant_specs(
        scene_type="战斗",
        scene_context={"outline": "X"},
        writer_agent="novelist-jianchen",
        n=3,
        constraint_library=lib,
        seed=42,
    )
    assert len(specs) == 3

    # 3. workflow_bridge
    from core.inspiration.workflow_bridge import phase1_dispatch
    from core.config_loader import DEFAULT_CONFIG

    result = phase1_dispatch(
        scene_type="战斗",
        scene_context={"outline": "X"},
        original_writers=["剑尘"],
        config=DEFAULT_CONFIG,
        seed=42,
    )
    assert result["mode"] == "variants"
    assert len(result["variant_specs"]) == 3
