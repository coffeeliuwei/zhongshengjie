import pytest
import json
from pathlib import Path


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    """将 STATE_FILE 重定向到 tmp_path"""
    f = tmp_path / "chapter_states.json"
    import scripts.chapter_state_tracker as tracker

    monkeypatch.setattr(tracker, "STATE_FILE", f)
    return f


def test_update_and_get_character_state(state_file):
    """更新角色状态后可正确读取"""
    from scripts.chapter_state_tracker import (
        update_character_state,
        get_character_state,
    )

    update_character_state(
        "林枫",
        "第3章",
        {
            "status": "alive",
            "injuries": ["左臂骨折"],
            "items": ["龙晶×1"],
        },
    )

    state = get_character_state("林枫")
    assert state["status"] == "alive"
    assert "左臂骨折" in state["injuries"]
    assert state["last_updated"] == "第3章"


def test_update_merges_fields(state_file):
    """多次更新同一角色时字段合并而非覆盖已有字段"""
    from scripts.chapter_state_tracker import (
        update_character_state,
        get_character_state,
    )

    update_character_state("血牙", "第1章", {"status": "alive", "injuries": []})
    update_character_state("血牙", "第2章", {"items": ["残魂碎片×1"]})

    state = get_character_state("血牙")
    assert state["status"] == "alive"
    assert state["items"] == ["残魂碎片×1"]
    assert state["last_updated"] == "第2章"


def test_get_all_active_states(state_file):
    """get_all_active_states 返回所有角色"""
    from scripts.chapter_state_tracker import (
        update_character_state,
        get_all_active_states,
    )

    update_character_state("林枫", "第3章", {"status": "alive"})
    update_character_state("血牙", "第2章", {"status": "alive"})

    states = get_all_active_states()
    assert "林枫" in states
    assert "血牙" in states


def test_get_nonexistent_character_returns_none(state_file):
    """查询不存在的角色返回 None"""
    from scripts.chapter_state_tracker import get_character_state

    assert get_character_state("不存在的角色") is None
