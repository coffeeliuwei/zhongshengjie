# tests/test_appraisal_agent.py
"""Tests for appraisal agent task spec building and result parsing."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import json
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


SAMPLE_VARIANTS = [
    {
        "id": "var_001",
        "writer_agent": "novelist-jianchen",
        "prompt": "...",
        "used_constraint_id": None,
        "text": "他抬手。",
    },
    {
        "id": "var_002",
        "writer_agent": "novelist-jianchen",
        "prompt": "...",
        "used_constraint_id": "ANTI_001",
        "text": "他没说话。",
    },
    {
        "id": "var_003",
        "writer_agent": "novelist-jianchen",
        "prompt": "...",
        "used_constraint_id": "ANTI_007",
        "text": "他抬手时屋檐在滴水。",
    },
]

SAMPLE_CONTEXT = {
    "scene_type": "打脸",
    "outline": "主角反击",
}


def test_build_cold_start_spec_no_references():
    """记忆点 < 50 时 prompt 不含参考样本"""
    from core.inspiration.appraisal_agent import build_appraisal_spec

    spec = build_appraisal_spec(
        candidates=SAMPLE_VARIANTS,
        scene_context=SAMPLE_CONTEXT,
        memory_point_count=20,
        retrieved_references=[],
    )
    assert spec["skill_name"] == "novelist-connoisseur"
    assert "你过去被击中" not in spec["prompt"]
    assert "var_001" in spec["prompt"]
    assert "var_002" in spec["prompt"]


def test_build_growing_spec_includes_references():
    """记忆点 50-300 时注入 top 3 参考"""
    from core.inspiration.appraisal_agent import build_appraisal_spec

    refs = [
        {
            "id": "mp_001",
            "payload": {
                "segment_text": "屋檐滴水",
                "polarity": "+",
                "intensity": 3,
                "note": "克制美",
            },
        },
        {
            "id": "mp_002",
            "payload": {
                "segment_text": "他没回头",
                "polarity": "+",
                "intensity": 3,
                "note": "压抑美",
            },
        },
        {
            "id": "mp_003",
            "payload": {
                "segment_text": "标准化对话",
                "polarity": "-",
                "intensity": 2,
                "note": "套路",
            },
        },
    ]
    spec = build_appraisal_spec(
        candidates=SAMPLE_VARIANTS,
        scene_context=SAMPLE_CONTEXT,
        memory_point_count=150,
        retrieved_references=refs,
    )
    assert "你过去被击中" in spec["prompt"] or "参照" in spec["prompt"]
    assert "屋檐滴水" in spec["prompt"]
    assert "克制美" in spec["prompt"]


def test_build_mature_spec_includes_summary():
    """记忆点 > 300 时含结构摘要"""
    from core.inspiration.appraisal_agent import build_appraisal_spec

    spec = build_appraisal_spec(
        candidates=SAMPLE_VARIANTS,
        scene_context=SAMPLE_CONTEXT,
        memory_point_count=500,
        retrieved_references=[],
        structural_summary="偏好紧-松-紧节奏、高意象密度",
    )
    assert "偏好" in spec["prompt"] or "结构" in spec["prompt"]


def test_parse_skill_response_valid():
    from core.inspiration.appraisal_agent import parse_appraisal_response

    raw = json.dumps(
        {
            "selected_id": "var_003",
            "ignition_point": "第3段 '屋檐在滴水'",
            "reason_fragment": "动作和环境错位的一瞬间",
            "confidence": "high",
        }
    )
    result = parse_appraisal_response(raw)
    assert result.selected_id == "var_003"
    assert result.confidence == "high"
    assert "屋檐" in result.ignition_point


def test_parse_none_response():
    from core.inspiration.appraisal_agent import parse_appraisal_response

    raw = json.dumps(
        {
            "selected_id": "none",
            "common_flaw": "三段都用同一种模板",
            "confidence": "high",
        }
    )
    result = parse_appraisal_response(raw)
    assert result.selected_id is None
    assert result.common_flaw == "三段都用同一种模板"


def test_parse_invalid_json_raises():
    from core.inspiration.appraisal_agent import (
        parse_appraisal_response,
        AppraisalParseError,
    )

    with pytest.raises(AppraisalParseError):
        parse_appraisal_response("not a json")


def test_parse_missing_ignition_point_when_selected_raises():
    """选了 ID 但没给 ignition_point 是无效输出"""
    from core.inspiration.appraisal_agent import (
        parse_appraisal_response,
        AppraisalParseError,
    )

    raw = json.dumps(
        {
            "selected_id": "var_001",
            "reason_fragment": "好",
            "confidence": "high",
        }
    )
    with pytest.raises(AppraisalParseError):
        parse_appraisal_response(raw)


def test_phase_determination():
    """phase 正确判断"""
    from core.inspiration.appraisal_agent import build_appraisal_spec

    # Cold
    spec = build_appraisal_spec(SAMPLE_VARIANTS, SAMPLE_CONTEXT, 10)
    assert spec["phase"] == "cold"

    # Growing
    spec = build_appraisal_spec(SAMPLE_VARIANTS, SAMPLE_CONTEXT, 100)
    assert spec["phase"] == "growing"

    # Mature
    spec = build_appraisal_spec(SAMPLE_VARIANTS, SAMPLE_CONTEXT, 500)
    assert spec["phase"] == "mature"
