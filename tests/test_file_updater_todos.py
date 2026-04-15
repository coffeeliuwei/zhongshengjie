#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
file_updater TODO 方法测试
========================

TDD 测试文件，测试 5 个 TODO 方法的实现。
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def make_updater(tmp_path):
    """创建指向临时目录的 FileUpdater"""
    from core.conversation.file_updater import FileUpdater

    with patch.object(FileUpdater, "_detect_project_root", return_value=tmp_path):
        updater = FileUpdater.__new__(FileUpdater)
        updater.project_root = tmp_path
        updater.logs_dir = tmp_path / "logs"
        updater.logs_dir.mkdir()
    return updater


HOOK_LEDGER_SAMPLE = """# 伏笔台账

## 伏笔001
**描述**: 主角发现密室
**状态**: 未触发
**章节**: 第一章

## 伏笔002
**描述**: 神秘信件
**状态**: 未触发
**章节**: 第三章
"""


def test_update_hook_status_to_triggered(tmp_path):
    """测试更新伏笔状态到已触发"""
    updater = make_updater(tmp_path)
    hook_file = tmp_path / "hook_ledger.md"
    hook_file.write_text(HOOK_LEDGER_SAMPLE, encoding="utf-8")

    updater._update_hook_status(
        file_path=hook_file,
        data={"hook_id": "伏笔001", "new_status": "已触发", "chapter": "第三章"},
    )

    content = hook_file.read_text(encoding="utf-8")
    assert "已触发" in content
    assert "第三章" in content


def test_update_hook_status_missing_hook_does_not_crash(tmp_path):
    """测试不存在伏笔时不崩溃"""
    updater = make_updater(tmp_path)
    hook_file = tmp_path / "hook_ledger.md"
    hook_file.write_text(HOOK_LEDGER_SAMPLE, encoding="utf-8")

    # hook_id 不存在时不报错
    updater._update_hook_status(
        file_path=hook_file,
        data={"hook_id": "伏笔999", "new_status": "已触发", "chapter": "第五章"},
    )
    # 文件内容不变
    assert hook_file.read_text(encoding="utf-8") == HOOK_LEDGER_SAMPLE


PAYOFF_LEDGER_SAMPLE = """# 承诺台账

## 承诺001
**描述**: 答应给主角解释真相
**状态**: 未兑现
**目标章节**: 第十章

## 承诺002
**描述**: 反派的最终复仇
**状态**: 未兑现
**目标章节**: 第二十章
"""


def test_update_payoff_status_to_delivered(tmp_path):
    """测试更新承诺状态到已兑现"""
    updater = make_updater(tmp_path)
    payoff_file = tmp_path / "payoff_tracking.md"
    payoff_file.write_text(PAYOFF_LEDGER_SAMPLE, encoding="utf-8")

    updater._update_payoff_status(
        file_path=payoff_file,
        data={"payoff_id": "承诺001", "new_status": "已兑现", "chapter": "第十章"},
    )

    content = payoff_file.read_text(encoding="utf-8")
    assert "已兑现" in content


def test_update_payoff_status_missing_does_not_crash(tmp_path):
    """测试不存在承诺时不崩溃"""
    updater = make_updater(tmp_path)
    payoff_file = tmp_path / "payoff_tracking.md"
    payoff_file.write_text(PAYOFF_LEDGER_SAMPLE, encoding="utf-8")
    updater._update_payoff_status(
        file_path=payoff_file,
        data={"payoff_id": "承诺999", "new_status": "已兑现", "chapter": "第五章"},
    )
    assert payoff_file.read_text(encoding="utf-8") == PAYOFF_LEDGER_SAMPLE
