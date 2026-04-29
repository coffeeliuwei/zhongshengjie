# tests/test_validation_judge.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.validation.judge import SkipJudge, ManualJudge, make_judge


# ── SkipJudge ──────────────────────────────────────────────

def test_skip_judge_returns_none():
    judge = SkipJudge()
    result = judge.score("查询", "结果文本", "case_library_v2")
    assert result is None


def test_skip_judge_batch_all_none():
    judge = SkipJudge()
    results = [judge.score("q", f"result{i}", "case_library_v2") for i in range(5)]
    assert all(r is None for r in results)


# ── ManualJudge ────────────────────────────────────────────

def test_manual_judge_valid_input(monkeypatch):
    judge = ManualJudge()
    monkeypatch.setattr("builtins.input", lambda _: "2")
    result = judge.score("查询", "结果文本", "case_library_v2")
    assert result == 2


def test_manual_judge_invalid_then_valid(monkeypatch):
    judge = ManualJudge()
    responses = iter(["x", "5", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    result = judge.score("查询", "结果文本", "case_library_v2")
    assert result == 1


# ── make_judge 工厂 ────────────────────────────────────────

def test_make_judge_skip():
    judge = make_judge("skip")
    assert isinstance(judge, SkipJudge)


def test_make_judge_manual():
    judge = make_judge("manual")
    assert isinstance(judge, ManualJudge)


def test_make_judge_unknown_raises():
    import pytest
    with pytest.raises(ValueError, match="未知 judge provider"):
        make_judge("unknown_provider")
