import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.extraction.extraction_runner import ExtractionRunner


def test_is_running_returns_false_when_no_pid_file(tmp_path):
    runner = ExtractionRunner(extractor_dir=tmp_path)
    assert runner.is_running() is False


def test_is_running_returns_false_and_cleans_orphan_pid(tmp_path):
    pid_file = tmp_path / "extraction.pid"
    pid_file.write_text("99999999")

    runner = ExtractionRunner(extractor_dir=tmp_path)
    with patch("os.kill", side_effect=OSError("no such process")):
        result = runner.is_running()

    assert result is False
    assert not pid_file.exists()


def test_is_running_returns_true_for_live_process(tmp_path):
    import os

    pid_file = tmp_path / "extraction.pid"
    pid_file.write_text(str(os.getpid()))

    runner = ExtractionRunner(extractor_dir=tmp_path)
    assert runner.is_running() is True


def test_start_incremental_when_not_running(tmp_path):
    runner = ExtractionRunner(extractor_dir=tmp_path)

    mock_proc = MagicMock()
    mock_proc.pid = 12345

    with (
        patch.object(runner, "is_running", return_value=False),
        patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
    ):
        result = runner.start("incremental")

    assert result["started"] is True
    assert result["pid"] == 12345
    assert result["mode"] == "incremental"
    call_args = mock_popen.call_args[0][0]
    assert "--no-resume" not in call_args
    assert (tmp_path / "extraction.pid").read_text() == "12345"


def test_start_full_passes_no_resume(tmp_path):
    runner = ExtractionRunner(extractor_dir=tmp_path)
    mock_proc = MagicMock()
    mock_proc.pid = 9999

    with (
        patch.object(runner, "is_running", return_value=False),
        patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
    ):
        result = runner.start("full")

    call_args = mock_popen.call_args[0][0]
    assert "--no-resume" in call_args
    assert result["started"] is True


def test_start_when_already_running_returns_status(tmp_path):
    runner = ExtractionRunner(extractor_dir=tmp_path)

    with (
        patch.object(runner, "is_running", return_value=True),
        patch.object(
            runner, "get_status", return_value={"raw": "status output", "running": True}
        ),
    ):
        result = runner.start("incremental")

    assert result["started"] is False
    assert result["status"]["running"] is True


def test_get_status_captures_stdout(tmp_path):
    runner = ExtractionRunner(extractor_dir=tmp_path)
    fake_output = "[系统状态]\n[核心]\n  [OK] 场景案例: 150 条\n"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=fake_output, returncode=0)
        with patch.object(runner, "is_running", return_value=False):
            status = runner.get_status()

    assert status["raw"] == fake_output
    assert status["running"] is False
