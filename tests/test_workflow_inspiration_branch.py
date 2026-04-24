# tests/test_workflow_inspiration_branch.py
"""Tests for workflow bridge - Stage 4 Phase 1 dispatch."""

import sys
from pathlib import Path
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def test_phase1_dispatch_disabled_returns_original():
    """enabled=False 时返回原作家列表"""
    from core.inspiration.workflow_bridge import phase1_dispatch

    result = phase1_dispatch(
        scene_type="战斗",
        scene_context={"outline": "X"},
        original_writers=["剑尘", "云溪"],
        config={"inspiration_engine": {"enabled": False}},
    )

    assert result["mode"] == "original"
    assert result["writers"] == ["剑尘", "云溪"]



def test_resolve_writer_skill():
    """中文作家名正确映射到 Skill 名"""
    from core.inspiration.workflow_bridge import _resolve_writer_skill

    assert _resolve_writer_skill("苍澜") == "novelist-canglan"
    assert _resolve_writer_skill("玄一") == "novelist-xuanyi"
    assert _resolve_writer_skill("墨言") == "novelist-moyan"
    assert _resolve_writer_skill("剑尘") == "novelist-jianchen"
    assert _resolve_writer_skill("云溪") == "novelist-yunxi"
    # 未映射时返回原名
    assert _resolve_writer_skill("未知作家") == "未知作家"


def test_phase1_dispatch_enabled_still_returns_original():
    """P1-5 后 enabled=True 也返回 original 模式（variant 逻辑已移除）"""
    from core.inspiration.workflow_bridge import phase1_dispatch

    result = phase1_dispatch(
        scene_type="战斗",
        scene_context={"outline": "主角反击"},
        original_writers=["剑尘"],
        config={"inspiration_engine": {"enabled": True, "variant_count": 3}},
        seed=42,
    )

    assert result["mode"] == "original"
    assert result["writers"] == ["剑尘"]
