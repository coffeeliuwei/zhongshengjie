# tests/test_variant_generator.py
"""Tests for variant generator (task spec construction)."""

import sys
import json
import pytest
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.inspiration.constraint_library import ConstraintLibrary
from core.inspiration.variant_generator import generate_variant_specs


@pytest.fixture
def sample_constraints_file(tmp_path):
    """创建临时约束文件"""
    data = {
        "version": "1.0",
        "constraints": [
            {
                "id": "ANTI_A",
                "category": "视角反叛",
                "trigger_scene_types": ["战斗"],
                "constraint_text": "从败者视角写",
                "intensity": "hard",
                "status": "active",
            },
            {
                "id": "ANTI_B",
                "category": "词汇剥夺",
                "trigger_scene_types": ["战斗"],
                "constraint_text": "禁用力量类词",
                "intensity": "hard",
                "status": "active",
            },
        ],
    }
    p = tmp_path / "constraints.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_generate_variants_returns_n_specs(sample_constraints_file):
    """生成 N 个变体规格"""
    lib = ConstraintLibrary(sample_constraints_file)
    specs = generate_variant_specs(
        scene_type="战斗",
        scene_context={"outline": "主角反击", "characters": ["A", "B"]},
        writer_agent="novelist-jianchen",
        n=3,
        constraint_library=lib,
        seed=42,
    )
    assert len(specs) == 3


def test_one_variant_is_baseline_no_constraint(sample_constraints_file):
    """必有且仅有 1 个基准变体（无约束）"""
    lib = ConstraintLibrary(sample_constraints_file)
    specs = generate_variant_specs(
        scene_type="战斗",
        scene_context={"outline": "主角反击"},
        writer_agent="novelist-jianchen",
        n=3,
        constraint_library=lib,
        seed=42,
    )
    baselines = [s for s in specs if s["used_constraint_id"] is None]
    assert len(baselines) == 1


def test_variant_spec_structure(sample_constraints_file):
    """变体规格结构验证"""
    lib = ConstraintLibrary(sample_constraints_file)
    specs = generate_variant_specs(
        scene_type="战斗",
        scene_context={"outline": "X"},
        writer_agent="novelist-jianchen",
        n=3,
        constraint_library=lib,
        seed=42,
    )
    for s in specs:
        assert "id" in s
        assert "writer_agent" in s
        assert "prompt" in s
        assert "used_constraint_id" in s
        assert s["writer_agent"] == "novelist-jianchen"
        assert s["id"].startswith("var_")


def test_constraint_text_injected_into_prompt(sample_constraints_file):
    """约束文本必须注入到 prompt 中"""
    lib = ConstraintLibrary(sample_constraints_file)
    specs = generate_variant_specs(
        scene_type="战斗",
        scene_context={"outline": "X"},
        writer_agent="novelist-jianchen",
        n=3,
        constraint_library=lib,
        seed=42,
    )
    constrained = [s for s in specs if s["used_constraint_id"] is not None]
    for s in constrained:
        constraint = lib.get_by_id(s["used_constraint_id"])
        # 约束文本必须出现在 prompt 中
        assert constraint["constraint_text"] in s["prompt"]


def test_n_minimum_two(sample_constraints_file):
    """N=2 时：1 baseline + 1 constrained"""
    lib = ConstraintLibrary(sample_constraints_file)
    specs = generate_variant_specs(
        scene_type="战斗",
        scene_context={"outline": "X"},
        writer_agent="novelist-jianchen",
        n=2,
        constraint_library=lib,
        seed=42,
    )
    assert len(specs) == 2
    baselines = [s for s in specs if s["used_constraint_id"] is None]
    assert len(baselines) == 1


def test_no_constraints_available_all_baseline(sample_constraints_file):
    """场景无可用约束时，所有变体都是 baseline"""
    lib = ConstraintLibrary(sample_constraints_file)
    specs = generate_variant_specs(
        scene_type="开篇",  # 测试约束库无该场景
        scene_context={"outline": "X"},
        writer_agent="novelist-yunxi",
        n=3,
        constraint_library=lib,
        seed=42,
    )
    assert len(specs) == 3
    for s in specs:
        assert s["used_constraint_id"] is None


def test_baseline_prompt_has_context(sample_constraints_file):
    """基准变体 prompt 包含场景上下文"""
    lib = ConstraintLibrary(sample_constraints_file)
    specs = generate_variant_specs(
        scene_type="战斗",
        scene_context={"outline": "主角反击", "characters": ["林夕", "血牙"]},
        writer_agent="novelist-jianchen",
        n=2,
        constraint_library=lib,
        seed=42,
    )
    baseline = specs[0]  # 基准始终第一个
    assert "主角反击" in baseline["prompt"]
    assert "林夕" in baseline["prompt"]
