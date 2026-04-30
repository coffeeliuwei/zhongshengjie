# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build_all import STAGES, STAGE_ORDER, _build_cmd


def test_stage_names_match_order():
    stage_names = {s["name"] for s in STAGES}
    for name in STAGE_ORDER:
        assert name in stage_names, f"STAGE_ORDER 中 {name} 未在 STAGES 中定义"


def test_stage_has_required_keys():
    for s in STAGES:
        for key in ("name", "label", "cmd", "rebuild_extra", "log"):
            assert key in s, f"阶段 {s.get('name')} 缺少字段 {key}"


def test_build_cmd_substitutes_technique_json():
    from tools.build_all import STAGES
    technique_stage = next(s for s in STAGES if s["name"] == "technique_batch")
    cmd = _build_cmd(technique_stage, rebuild=False, technique_json="E:/test/technique.json")
    assert "E:/test/technique.json" in cmd
    assert "--rebuild" not in cmd


def test_build_cmd_adds_rebuild_extra():
    from tools.build_all import STAGES
    technique_stage = next(s for s in STAGES if s["name"] == "technique_batch")
    cmd = _build_cmd(technique_stage, rebuild=True, technique_json="E:/test/technique.json")
    assert "--rebuild" in cmd


def test_build_cmd_no_rebuild_for_case():
    from tools.build_all import STAGES
    case_stage = next(s for s in STAGES if s["name"] == "case")
    cmd = _build_cmd(case_stage, rebuild=True, technique_json="")
    # case 阶段 rebuild_extra 为空，即使 rebuild=True 也不加参数
    assert "--rebuild" not in cmd
