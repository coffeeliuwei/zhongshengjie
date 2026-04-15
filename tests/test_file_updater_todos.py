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


CHARACTER_PROFILE_SAMPLE = """# 人物档案

## 凌云
**势力**: 天剑宗
**境界**: 凝气期

### 能力
- 御剑术

### 关系
- 师父：剑圣
"""


def test_add_character_ability(tmp_path):
    """测试添加角色能力"""
    updater = make_updater(tmp_path)
    profile_file = tmp_path / "characters.md"
    profile_file.write_text(CHARACTER_PROFILE_SAMPLE, encoding="utf-8")

    updater._add_character_ability(
        file_path=profile_file,
        data={"character_name": "凌云", "ability": "天雷斩"},
    )

    content = profile_file.read_text(encoding="utf-8")
    assert "天雷斩" in content


def test_add_character_relation(tmp_path):
    """测试添加角色关系"""
    updater = make_updater(tmp_path)
    profile_file = tmp_path / "characters.md"
    profile_file.write_text(CHARACTER_PROFILE_SAMPLE, encoding="utf-8")

    updater._add_character_relation(
        file_path=profile_file,
        data={"character_name": "凌云", "relation": "师弟：墨尘"},
    )

    content = profile_file.read_text(encoding="utf-8")
    assert "墨尘" in content


def test_add_character_ability_missing_character(tmp_path):
    """测试不存在角色时追加到文件末尾"""
    updater = make_updater(tmp_path)
    profile_file = tmp_path / "characters.md"
    profile_file.write_text(CHARACTER_PROFILE_SAMPLE, encoding="utf-8")
    # 角色不存在时追加到文件末尾
    updater._add_character_ability(
        file_path=profile_file,
        data={"character_name": "不存在角色", "ability": "未知技能"},
    )
    content = profile_file.read_text(encoding="utf-8")
    assert "未知技能" in content


POWER_SYSTEM_SAMPLE = """# 力量体系

## 修仙体系
**描述**: 通过修炼灵气提升境界

### 境界列表
- 凝气期
- 筑基期
- 金丹期

### 代价
- 寿命消耗
"""


def test_update_power_system_add_realm(tmp_path):
    """测试添加境界到现有体系"""
    updater = make_updater(tmp_path)
    ps_file = tmp_path / "power_system.md"
    ps_file.write_text(POWER_SYSTEM_SAMPLE, encoding="utf-8")

    updater._update_power_system(
        file_path=ps_file,
        data={"system_name": "修仙体系", "field": "境界列表", "value": "元婴期"},
    )

    content = ps_file.read_text(encoding="utf-8")
    assert "元婴期" in content


def test_update_power_system_new_system(tmp_path):
    """测试添加新体系"""
    updater = make_updater(tmp_path)
    ps_file = tmp_path / "power_system.md"
    ps_file.write_text(POWER_SYSTEM_SAMPLE, encoding="utf-8")

    updater._update_power_system(
        file_path=ps_file,
        data={"system_name": "武道体系", "field": "境界列表", "value": "炼体境"},
    )

    content = ps_file.read_text(encoding="utf-8")
    assert "武道体系" in content
    assert "炼体境" in content


PAYOFF_WITH_CHAPTER_SAMPLE = """# 承诺台账

## payoff-001

**状态**: ⏳ 待兑现
**兑现章节**: 待填写

---

## payoff-002

**状态**: ⏳ 待兑现
**兑现章节**: 待填写

---
"""


def test_update_payoff_status_updates_chapter(tmp_path):
    """_update_payoff_status 在提供 chapter 时同步更新兑现章节字段"""
    updater = make_updater(tmp_path)
    payoff_file = tmp_path / "payoffs.md"
    payoff_file.write_text(PAYOFF_WITH_CHAPTER_SAMPLE, encoding="utf-8")

    updater._update_payoff_status(
        payoff_file,
        {"payoff_id": "payoff-001", "new_status": "✅ 已兑现", "chapter": "第18章"},
    )

    result = payoff_file.read_text(encoding="utf-8")
    assert "**状态**: ✅ 已兑现" in result
    assert "**兑现章节**: 第18章" in result


def test_update_payoff_status_no_chapter_leaves_field_intact(tmp_path):
    """_update_payoff_status 不提供 chapter 时不修改兑现章节字段"""
    updater = make_updater(tmp_path)
    payoff_file = tmp_path / "payoffs.md"
    payoff_file.write_text(PAYOFF_WITH_CHAPTER_SAMPLE, encoding="utf-8")

    updater._update_payoff_status(
        payoff_file,
        {"payoff_id": "payoff-002", "new_status": "✅ 已兑现"},
    )

    result = payoff_file.read_text(encoding="utf-8")
    assert "**状态**: ✅ 已兑现" in result
    assert "**兑现章节**: 待填写" in result  # 未被修改
