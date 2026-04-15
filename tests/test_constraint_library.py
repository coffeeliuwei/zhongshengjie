# tests/test_constraint_library.py
"""Tests for constraint library loading and filtering."""

import sys
import json
import pytest
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.inspiration.constraint_library import (
    ConstraintLibrary,
    DEFAULT_CONSTRAINTS_PATH,
)


@pytest.fixture
def sample_constraints_file(tmp_path):
    """创建临时约束文件"""
    data = {
        "version": "1.0",
        "created_at": "2026-04-14",
        "constraints": [
            {
                "id": "ANTI_001",
                "category": "视角反叛",
                "trigger_scene_types": ["战斗", "高潮"],
                "constraint_text": "本场必须从败者视角",
                "intensity": "hard",
                "status": "active",
            },
            {
                "id": "ANTI_002",
                "category": "词汇剥夺",
                "trigger_scene_types": ["战斗"],
                "constraint_text": "禁用力量类词",
                "intensity": "hard",
                "status": "active",
            },
            {
                "id": "ANTI_003",
                "category": "情绪逆压",
                "trigger_scene_types": ["情感"],
                "constraint_text": "克制冷静笔调",
                "intensity": "soft",
                "status": "disabled",
            },
        ],
    }
    path = tmp_path / "constraints.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_load_returns_active_only(sample_constraints_file):
    """只返回 active 状态的约束"""
    lib = ConstraintLibrary(sample_constraints_file)
    all_active = lib.list_active()
    assert len(all_active) == 2
    ids = {c["id"] for c in all_active}
    assert ids == {"ANTI_001", "ANTI_002"}


def test_filter_by_scene_type(sample_constraints_file):
    """按场景类型筛选"""
    lib = ConstraintLibrary(sample_constraints_file)
    battle_constraints = lib.filter_by_scene_type("战斗")
    assert len(battle_constraints) == 2

    emotion_constraints = lib.filter_by_scene_type("情感")
    assert len(emotion_constraints) == 0  # ANTI_003 是 disabled


def test_random_pick_n_unique_categories(sample_constraints_file):
    """抽取 N 条时优先不同类别"""
    lib = ConstraintLibrary(sample_constraints_file)
    picked = lib.pick_for_variants(scene_type="战斗", n=2, seed=42)
    assert len(picked) == 2
    # 不同类别优先：应同时包含视角反叛和词汇剥夺
    categories = {c["category"] for c in picked}
    assert categories == {"视角反叛", "词汇剥夺"}


def test_random_pick_when_pool_smaller_than_n(sample_constraints_file):
    """约束池小于 N 时，返回全部可用"""
    lib = ConstraintLibrary(sample_constraints_file)
    picked = lib.pick_for_variants(scene_type="情感", n=2, seed=42)
    assert picked == []  # 情感无可用约束


def test_get_by_id(sample_constraints_file):
    """按 ID 查找约束"""
    lib = ConstraintLibrary(sample_constraints_file)
    c = lib.get_by_id("ANTI_001")
    assert c["constraint_text"] == "本场必须从败者视角"
    assert lib.get_by_id("ANTI_999") is None


def test_get_version(sample_constraints_file):
    """获取版本号"""
    lib = ConstraintLibrary(sample_constraints_file)
    assert lib.get_version() == "1.0"


def test_count_total(sample_constraints_file):
    """统计总数"""
    lib = ConstraintLibrary(sample_constraints_file)
    assert lib.count_total() == 3


def test_count_active(sample_constraints_file):
    """统计活跃数"""
    lib = ConstraintLibrary(sample_constraints_file)
    assert lib.count_active() == 2


def test_load_real_constraints_file():
    """加载真实约束文件"""
    lib = ConstraintLibrary(DEFAULT_CONSTRAINTS_PATH)
    assert lib.get_version() == "1.0"
    assert lib.count_total() == 45
    # 至少应有 40 个活跃约束
    assert lib.count_active() >= 40
