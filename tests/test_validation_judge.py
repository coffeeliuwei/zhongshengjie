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


from unittest.mock import patch, MagicMock
from tools.validation.judge import OpenAICompatibleJudge, OpenAIJudge, ClaudeJudge


# ── OpenAICompatibleJudge ──────────────────────────────────

def test_compatible_judge_returns_score(monkeypatch):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "2"
    with patch("openai.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response
        judge = OpenAICompatibleJudge(
            base_url="http://localhost:11434/v1",
            api_key="none",
            model="qwen2.5:7b",
        )
        result = judge.score("查询", "结果文本", "case_library_v2")
    assert result == 2


def test_compatible_judge_invalid_response_returns_none(monkeypatch):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "invalid"
    with patch("openai.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response
        judge = OpenAICompatibleJudge(
            base_url="http://localhost:11434/v1",
            api_key="none",
            model="qwen2.5:7b",
        )
        result = judge.score("查询", "结果文本", "case_library_v2")
    assert result is None


def test_compatible_judge_retries_on_exception():
    with patch("openai.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        judge = OpenAICompatibleJudge(
            base_url="http://localhost:11434/v1",
            api_key="none",
            model="qwen2.5:7b",
        )
        result = judge.score("查询", "结果文本", "case_library_v2")
    assert result is None
    assert mock_client.chat.completions.create.call_count == 3  # 重试 2 次


def test_openai_judge_uses_no_base_url():
    with patch("openai.OpenAI") as mock_cls:
        OpenAIJudge(api_key="sk-test", model="gpt-4o")
        call_kwargs = mock_cls.call_args[1]
        assert "base_url" not in call_kwargs or call_kwargs.get("base_url") is None


def test_claude_judge_returns_score():
    mock_message = MagicMock()
    mock_message.content[0].text = "1"
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_message
        judge = ClaudeJudge(api_key="sk-ant-test", model="claude-haiku-4-5-20251001")
        result = judge.score("查询", "结果文本", "case_library_v2")
    assert result == 1


def test_claude_judge_retries_on_exception():
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")
        judge = ClaudeJudge(api_key="sk-ant-test", model="claude-haiku-4-5-20251001")
        result = judge.score("查询", "结果文本", "case_library_v2")
    assert result is None
    assert mock_client.messages.create.call_count == 3  # 重试 2 次


def test_make_judge_openai():
    with patch("openai.OpenAI"):
        judge = make_judge("openai", api_key="sk-test", model="gpt-4o")
        assert isinstance(judge, OpenAIJudge)


def test_make_judge_claude():
    with patch("anthropic.Anthropic"):
        judge = make_judge("claude", api_key="sk-ant-test", model="claude-haiku-4-5-20251001")
        assert isinstance(judge, ClaudeJudge)


def test_make_judge_compatible():
    with patch("openai.OpenAI"):
        judge = make_judge(
            "compatible",
            base_url="http://localhost:11434/v1",
            api_key="none",
            model="qwen2.5:7b",
        )
        assert isinstance(judge, OpenAICompatibleJudge)
