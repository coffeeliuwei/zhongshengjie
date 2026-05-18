# -*- coding: utf-8 -*-
"""tests/test_narrative_ledger.py — narrative_ledger 单元测试"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.narrative_ledger as ledger_mod


def _make_temp_ledger():
    """返回一个临时文件路径用于测试隔离。"""
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    Path(tmp.name).unlink()  # 删掉，让 update_chapter 重新创建
    return Path(tmp.name)


# ─── update_chapter ────────────────────────────────────────────

def test_update_chapter_creates_file(tmp_path):
    ledger_file = tmp_path / "ledger.json"
    with patch.object(ledger_mod, "_ledger_path", return_value=ledger_file):
        ledger_mod.update_chapter(
            chapter=1,
            scene_types=["战斗", "突破"],
            tension_level=4,
            themes_touched={"力量的代价": 3},
        )
    assert ledger_file.exists()
    data = json.loads(ledger_file.read_text(encoding="utf-8"))
    assert "1" in data["chapters"]
    ch = data["chapters"]["1"]
    assert ch["scene_types"] == ["战斗", "突破"]
    assert ch["tension_level"] == 4
    assert ch["themes_touched"] == {"力量的代价": 3}


def test_update_chapter_tension_clamped(tmp_path):
    ledger_file = tmp_path / "ledger.json"
    with patch.object(ledger_mod, "_ledger_path", return_value=ledger_file):
        ledger_mod.update_chapter(5, ["战斗"], tension_level=99)
        data = json.loads(ledger_file.read_text(encoding="utf-8"))
    assert data["chapters"]["5"]["tension_level"] == 5  # 最大值5


def test_update_chapter_overwrites_same_chapter(tmp_path):
    ledger_file = tmp_path / "ledger.json"
    with patch.object(ledger_mod, "_ledger_path", return_value=ledger_file):
        ledger_mod.update_chapter(3, ["战斗"], 3)
        ledger_mod.update_chapter(3, ["悬念"], 2)
        data = json.loads(ledger_file.read_text(encoding="utf-8"))
    assert data["chapters"]["3"]["scene_types"] == ["悬念"]


# ─── get_diversity_constraints ─────────────────────────────────

def test_constraints_cold_start_returns_empty(tmp_path):
    ledger_file = tmp_path / "ledger.json"
    with patch.object(ledger_mod, "_ledger_path", return_value=ledger_file), \
         patch.object(ledger_mod, "_load_cfg", return_value={}):
        # 只写2章，不足3章 → 冷启动
        ledger_mod.update_chapter(1, ["战斗"], 3)
        ledger_mod.update_chapter(2, ["战斗"], 3)
        result = ledger_mod.get_diversity_constraints(next_chapter=3)
    assert result == ""


def test_constraints_returns_string_after_3_chapters(tmp_path):
    ledger_file = tmp_path / "ledger.json"
    cfg = {
        "beat_groups": {"战斗组": ["战斗", "突破"], "悬念组": ["悬念", "伏笔"]},
        "repeat_beat_window": 3,
        "repeat_tension_window": 4,
        "themes": ["力量的代价", "身份认同", "背叛"],
        "theme_sleep_threshold": 30,
        "ledger_path": str(ledger_file),
    }
    with patch.object(ledger_mod, "_ledger_path", return_value=ledger_file), \
         patch.object(ledger_mod, "_load_cfg", return_value=cfg):
        for i in range(1, 5):
            ledger_mod.update_chapter(i, ["战斗"], tension_level=4,
                                      themes_touched={"力量的代价": 2})
        result = ledger_mod.get_diversity_constraints(next_chapter=5)
    assert isinstance(result, str)
    # 连续4章战斗 → 应有节拍约束文字
    assert len(result) > 0


# ─── show_summary ──────────────────────────────────────────────

def test_show_summary_no_crash(tmp_path):
    ledger_file = tmp_path / "ledger.json"
    with patch.object(ledger_mod, "_ledger_path", return_value=ledger_file), \
         patch.object(ledger_mod, "_load_cfg", return_value={}):
        ledger_mod.update_chapter(1, ["战斗"], 3)
        result = ledger_mod.show_summary()
    assert isinstance(result, str)
    assert "1" in result  # 应包含章节号
