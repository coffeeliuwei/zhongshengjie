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
    cmd = _build_cmd(
        technique_stage, rebuild=False, technique_json="E:/test/technique.json"
    )
    assert "E:/test/technique.json" in cmd
    assert "--rebuild" not in cmd


def test_build_cmd_adds_rebuild_extra():
    from tools.build_all import STAGES

    technique_stage = next(s for s in STAGES if s["name"] == "technique_batch")
    cmd = _build_cmd(
        technique_stage, rebuild=True, technique_json="E:/test/technique.json"
    )
    assert "--rebuild" in cmd


def test_build_cmd_no_rebuild_for_case():
    from tools.build_all import STAGES

    case_stage = next(s for s in STAGES if s["name"] == "case")
    cmd = _build_cmd(case_stage, rebuild=True, technique_json="")
    # case 阶段 rebuild_extra 为空，即使 rebuild=True 也不加参数
    assert "--rebuild" not in cmd


def test_clear_case_data_removes_files(tmp_path, monkeypatch):
    """clear_case_data 应删除索引文件、清空 cases/"""
    # 构造临时 case-library
    case_lib = tmp_path / "case-library"
    (case_lib / "cases" / "场景A").mkdir(parents=True)
    (case_lib / "case_index.json").write_text("{}")
    (case_lib / "dedup_index.pkl").write_bytes(b"data")

    from tools.build_all import clear_case_data

    clear_case_data(case_lib_path=case_lib)

    assert not (case_lib / "case_index.json").exists()
    assert not (case_lib / "dedup_index.pkl").exists()
    assert (case_lib / "cases").exists()
    assert list((case_lib / "cases").iterdir()) == []


def test_show_status_handles_connection_error(capsys):
    """show_status 在 Qdrant 不可达时不崩溃"""
    from tools.build_all import show_status

    show_status(qdrant_url="http://localhost:19999")  # 必然连不上
    captured = capsys.readouterr()
    assert "错误" in captured.out or "error" in captured.out.lower()
