# tests/test_constraint_library.py
"""Tests for constraint library loading and filtering."""

import sys
import json
import pytest
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.inspiration.constraint_library import (
    ConstraintLibrary,
    DEFAULT_CONSTRAINTS_PATH,
)


@pytest.fixture
def sample_constraints_file(tmp_path):
    """创建临时约束文件"""
    data = {
        "version": "1.0",
        "created_at": "2026-04-14",
        "constraints": [
            {
                "id": "ANTI_001",
                "category": "视角反叛",
                "trigger_scene_types": ["战斗", "高潮"],
                "constraint_text": "本场必须从败者视角",
                "intensity": "hard",
                "status": "active",
            },
            {
                "id": "ANTI_002",
                "category": "词汇剥夺",
                "trigger_scene_types": ["战斗"],
                "constraint_text": "禁用力量类词",
                "intensity": "hard",
                "status": "active",
            },
            {
                "id": "ANTI_003",
                "category": "情绪逆压",
                "trigger_scene_types": ["情感"],
                "constraint_text": "克制冷静笔调",
                "intensity": "soft",
                "status": "disabled",
            },
        ],
    }
    path = tmp_path / "constraints.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_load_returns_active_only(sample_constraints_file):
    """只返回 active 状态的约束"""
    lib = ConstraintLibrary(sample_constraints_file)
    all_active = lib.list_active()
    assert len(all_active) == 2
    ids = {c["id"] for c in all_active}
    assert ids == {"ANTI_001", "ANTI_002"}


def test_filter_by_scene_type(sample_constraints_file):
    """按场景类型筛选"""
    lib = ConstraintLibrary(sample_constraints_file)
    battle_constraints = lib.filter_by_scene_type("战斗")
    assert len(battle_constraints) == 2

    emotion_constraints = lib.filter_by_scene_type("情感")
    assert len(emotion_constraints) == 0  # ANTI_003 是 disabled


def test_random_pick_n_unique_categories(sample_constraints_file):
    """抽取 N 条时优先不同类别"""
    lib = ConstraintLibrary(sample_constraints_file)
    picked = lib.pick_for_variants(scene_type="战斗", n=2, seed=42)
    assert len(picked) == 2
    # 不同类别优先：应同时包含视角反叛和词汇剥夺
    categories = {c["category"] for c in picked}
    assert categories == {"视角反叛", "词汇剥夺"}


def test_random_pick_when_pool_smaller_than_n(sample_constraints_file):
    """约束池小于 N 时，返回全部可用"""
    lib = ConstraintLibrary(sample_constraints_file)
    picked = lib.pick_for_variants(scene_type="情感", n=2, seed=42)
    assert picked == []  # 情感无可用约束


def test_get_by_id(sample_constraints_file):
    """按 ID 查找约束"""
    lib = ConstraintLibrary(sample_constraints_file)
    c = lib.get_by_id("ANTI_001")
    assert c["constraint_text"] == "本场必须从败者视角"
    assert lib.get_by_id("ANTI_999") is None


def test_get_version(sample_constraints_file):
    """获取版本号"""
    lib = ConstraintLibrary(sample_constraints_file)
    assert lib.get_version() == "1.0"


def test_count_total(sample_constraints_file):
    """统计总数"""
    lib = ConstraintLibrary(sample_constraints_file)
    assert lib.count_total() == 3


def test_count_active(sample_constraints_file):
    """统计活跃数"""
    lib = ConstraintLibrary(sample_constraints_file)
    assert lib.count_active() == 2


def test_load_real_constraints_file():
    """加载真实约束文件"""
    lib = ConstraintLibrary(DEFAULT_CONSTRAINTS_PATH)
    assert lib.get_version() == "1.0"
    assert lib.count_total() == 45
    # 至少应有 40 个活跃约束
    assert lib.count_active() >= 40


# =========================================================================
# P1-4 新增:反模板约束库菜单化(as_menu / count_by_category /
#           search_by_keyword / format_menu_text)
# =========================================================================


@pytest.fixture
def multi_category_constraints_file(tmp_path):
    """P1-4 专用 fixture:覆盖 3 类别、多场景、含 disabled 条目。"""
    data = {
        "version": "1.0",
        "created_at": "2026-04-20",
        "constraints": [
            {
                "id": "ANTI_001",
                "category": "视角反叛",
                "trigger_scene_types": ["战斗", "高潮"],
                "constraint_text": "本场必须从败者视角写,禁止全知视角",
                "intensity": "hard",
                "status": "active",
            },
            {
                "id": "ANTI_002",
                "category": "视角反叛",
                "trigger_scene_types": ["战斗"],
                "constraint_text": "全程从旁观者视角描写",
                "intensity": "soft",
                "status": "active",
            },
            {
                "id": "ANTI_010",
                "category": "词汇剥夺",
                "trigger_scene_types": ["战斗", "情感"],
                "constraint_text": "禁用任何力量/强度类形容词",
                "intensity": "hard",
                "status": "active",
            },
            {
                "id": "ANTI_011",
                "category": "词汇剥夺",
                "trigger_scene_types": ["情感"],
                "constraint_text": "禁用色彩词",
                "intensity": "soft",
                "status": "active",
            },
            {
                "id": "ANTI_020",
                "category": "情绪逆压",
                "trigger_scene_types": ["情感"],
                "constraint_text": "克制冷静笔调,禁止情绪化描写",
                "intensity": "soft",
                "status": "active",
            },
            {
                "id": "ANTI_099",
                "category": "已弃用",
                "trigger_scene_types": ["战斗"],
                "constraint_text": "不应出现在任何 menu 中",
                "intensity": "hard",
                "status": "disabled",
            },
        ],
    }
    path = tmp_path / "multi_category.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_as_menu_no_filter_returns_all_active(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu()
    assert isinstance(menu, list)
    # 5 active(跳过 ANTI_099 disabled)
    assert len(menu) == 5
    ids = {c["id"] for c in menu}
    assert ids == {"ANTI_001", "ANTI_002", "ANTI_010", "ANTI_011", "ANTI_020"}


def test_as_menu_items_contain_expected_fields(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu()
    item = menu[0]
    # 5 字段齐全(status 不含,因为已筛为 active)
    for f in ("id", "category", "trigger_scene_types", "constraint_text", "intensity"):
        assert f in item, f"缺字段 {f}"
    assert "status" not in item  # 不对外暴露筛选字段


def test_as_menu_sorted_by_category_then_id(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu()
    keys = [(c["category"], c["id"]) for c in menu]
    assert keys == sorted(keys)


def test_as_menu_skips_disabled(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu()
    ids = {c["id"] for c in menu}
    assert "ANTI_099" not in ids


def test_as_menu_filtered_by_battle(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu(scene_type="战斗")
    ids = {c["id"] for c in menu}
    # ANTI_001, ANTI_002, ANTI_010 触发场景含"战斗";ANTI_099 disabled 排除
    assert ids == {"ANTI_001", "ANTI_002", "ANTI_010"}


def test_as_menu_filtered_by_emotion(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu(scene_type="情感")
    ids = {c["id"] for c in menu}
    # ANTI_010, ANTI_011, ANTI_020 触发场景含"情感"
    assert ids == {"ANTI_010", "ANTI_011", "ANTI_020"}


def test_as_menu_filtered_by_unknown_scene_empty(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    assert lib.as_menu(scene_type="不存在的场景") == []


def test_count_by_category_basic(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    counts = lib.count_by_category()
    # 视角反叛: 2 (ANTI_001, ANTI_002)
    # 词汇剥夺: 2 (ANTI_010, ANTI_011)
    # 情绪逆压: 1 (ANTI_020)
    # 已弃用:   0 (ANTI_099 disabled,不计入)
    assert counts == {"视角反叛": 2, "词汇剥夺": 2, "情绪逆压": 1}
    assert "已弃用" not in counts


def test_count_by_category_returns_dict(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    counts = lib.count_by_category()
    assert isinstance(counts, dict)


def test_count_by_category_empty_on_all_disabled(tmp_path):
    """所有约束 disabled → 空 dict。"""
    data = {
        "version": "1.0",
        "constraints": [
            {"id": "X1", "category": "A",
             "trigger_scene_types": ["X"],
             "constraint_text": "t", "intensity": "soft",
             "status": "disabled"},
        ],
    }
    path = tmp_path / "all_disabled.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    lib = ConstraintLibrary(path)
    assert lib.count_by_category() == {}


def test_search_by_keyword_substring(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    results = lib.search_by_keyword("视角")
    ids = {c["id"] for c in results}
    # ANTI_001 "败者视角"、ANTI_002 "旁观者视角" 命中;其他不含"视角"
    assert ids == {"ANTI_001", "ANTI_002"}


def test_search_by_keyword_no_match_returns_empty(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    assert lib.search_by_keyword("没有这个词") == []


def test_search_by_keyword_case_insensitive(tmp_path):
    """英文大小写不敏感。"""
    data = {
        "version": "1.0",
        "constraints": [
            {"id": "X1", "category": "A",
             "trigger_scene_types": ["X"],
             "constraint_text": "FOO bar baz",
             "intensity": "hard", "status": "active"},
            {"id": "X2", "category": "A",
             "trigger_scene_types": ["X"],
             "constraint_text": "没有关键词",
             "intensity": "hard", "status": "active"},
        ],
    }
    path = tmp_path / "case.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    lib = ConstraintLibrary(path)
    for kw in ("foo", "FOO", "Foo", "fOo"):
        results = lib.search_by_keyword(kw)
        assert {c["id"] for c in results} == {"X1"}, f"keyword {kw!r} 未命中"


def test_search_by_keyword_skips_disabled(multi_category_constraints_file):
    """disabled 条目不进入搜索结果,即使内容命中。"""
    lib = ConstraintLibrary(multi_category_constraints_file)
    # ANTI_099 的 constraint_text "不应出现在任何 menu 中" 含"不应"
    results = lib.search_by_keyword("不应")
    assert results == []


def test_search_by_keyword_empty_raises():
    from core.inspiration.constraint_library import ConstraintLibrary, DEFAULT_CONSTRAINTS_PATH
    lib = ConstraintLibrary(DEFAULT_CONSTRAINTS_PATH)
    with pytest.raises(ValueError, match="keyword"):
        lib.search_by_keyword("")
    with pytest.raises(ValueError, match="keyword"):
        lib.search_by_keyword("   ")


def test_search_by_keyword_returns_full_fields(multi_category_constraints_file):
    """返回项字段 = as_menu 的 5 字段(统一对外形状)。"""
    lib = ConstraintLibrary(multi_category_constraints_file)
    results = lib.search_by_keyword("视角")
    for r in results:
        for f in ("id", "category", "trigger_scene_types",
                  "constraint_text", "intensity"):
            assert f in r
        assert "status" not in r


def test_format_menu_text_header_all_scenes(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text()
    assert text.startswith("## 反模板约束菜单")
    assert "全部场景" in text
    assert "共 5 条" in text


def test_format_menu_text_header_scene_specific(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text(scene_type="战斗")
    assert "场景:战斗" in text
    assert "共 3 条" in text


def test_format_menu_text_category_grouping(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text()
    # 3 个分类标题都出现
    assert "### 视角反叛" in text
    assert "### 词汇剥夺" in text
    assert "### 情绪逆压" in text
    # 分类计数
    assert "视角反叛 (2)" in text
    assert "词汇剥夺 (2)" in text
    assert "情绪逆压 (1)" in text


def test_format_menu_text_item_lines(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text()
    # 每条: "- ANTI_XXX [intensity]: constraint_text"
    assert "- ANTI_001 [hard]:本场必须从败者视角写" in text
    assert "- ANTI_002 [soft]:全程从旁观者视角描写" in text
    assert "- ANTI_020 [soft]:克制冷静笔调" in text


def test_format_menu_text_filtered_category_omitted(multi_category_constraints_file):
    """场景过滤后空的 category 不出现。"""
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text(scene_type="情感")
    # 情感场景:ANTI_010(词汇剥夺) + ANTI_011(词汇剥夺) + ANTI_020(情绪逆压)= 3 条
    # "视角反叛" 不匹配"情感",应缺席
    assert "### 视角反叛" not in text
    assert "### 词汇剥夺" in text
    assert "### 情绪逆压" in text


def test_format_menu_text_empty_returns_no_items_marker(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text(scene_type="不存在")
    assert "无可用约束" in text
    assert "共 0 条" in text


def test_format_menu_text_disabled_excluded(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text()
    # ANTI_099 是 disabled,constraint_text 不得出现
    assert "ANTI_099" not in text
    assert "不应出现在任何 menu 中" not in text
