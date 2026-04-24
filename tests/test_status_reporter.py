# tests/test_status_reporter.py
"""Tests for inspiration engine status reporter."""

from unittest.mock import MagicMock
import pytest


def test_report_contains_total_and_overturn_counts():
    """报告文本包含总记忆点数和推翻事件数"""
    from core.inspiration.status_reporter import report_status

    sync = MagicMock()
    sync.count.return_value = 73
    sync.count_overturn_events.return_value = 4

    report = report_status(sync=sync)

    assert "73" in report
    assert "4" in report


def test_report_phase_cold_start():
    """记忆点 < 50 显示冷启动"""
    from core.inspiration.status_reporter import report_status

    sync = MagicMock()
    sync.count.return_value = 20
    sync.count_overturn_events.return_value = 0

    report = report_status(sync=sync)
    assert "冷启动" in report


def test_report_phase_growing():
    """记忆点 50-299 显示成长期"""
    from core.inspiration.status_reporter import report_status

    sync = MagicMock()
    sync.count.return_value = 100
    sync.count_overturn_events.return_value = 0

    assert "成长期" in report_status(sync=sync)


def test_report_phase_mature():
    """记忆点 >= 300 显示成熟期"""
    from core.inspiration.status_reporter import report_status

    sync = MagicMock()
    sync.count.return_value = 500
    sync.count_overturn_events.return_value = 12

    assert "成熟期" in report_status(sync=sync)
