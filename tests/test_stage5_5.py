# tests/test_stage5_5.py
"""阶段 5.5 三方协商单元测试。"""
import json
import pytest

from core.inspiration.stage5_5 import (
    build_connoisseur_prompt,
    parse_connoisseur_response,
    suggestions_to_preserve_candidates,
    build_creative_contract,
    ConnoisseurParseError,
)


# ── 测试数据 ────────────────────────────────────────────

MENU_ITEMS = [
    {"id": "ANTI_001", "category": "视角反叛", "trigger_scene_types": ["战斗"], "constraint_text": "败者视角反叛", "intensity": "hard"},
    {"id": "ANTI_020", "category": "感官错位", "trigger_scene_types": ["情感"], "constraint_text": "物象压情感", "intensity": "soft"},
]

POS_SAMPLES = [
    {"id": "mp_001", "payload": {"mp_id": "mp_001", "segment_text": "屋檐滴水，静中有动", "polarity": "+"}},
]

NEG_SAMPLES = [
    {"id": "mp_002", "payload": {"mp_id": "mp_002", "segment_text": "对方惊恐，主角微笑", "polarity": "-"}},
]

CHAPTER_TEXT = "第三章测试文本，共两段。\n段落二内容。"

CONNOISSEUR_JSON_WITH_SUGGESTIONS = json.dumps({
    "chapter_ref": "第3章",
    "suggestions": [
        {
            "item_id": "#1",
            "scope": {"paragraph_index": 1, "char_start": 0, "char_end": 10, "excerpt": "第三章测试文本"},
            "applied_constraint_id": "ANTI_001",
            "applied_constraint_text": "败者视角反叛",
            "rationale": "此段主角视角与负样本相似",
            "memory_point_refs": ["mp_002"],
            "confidence": "high",
            "expected_impact": "增加视角张力",
        }
    ],
    "overall_judgment": "整章尚可",
    "abstain_reason": None,
    "menu_gap": None,
}, ensure_ascii=False)

CONNOISSEUR_JSON_EMPTY = json.dumps({
    "chapter_ref": "第3章",
    "suggestions": [],
    "overall_judgment": "无需改动",
    "abstain_reason": "整章与记忆点指纹高度契合",
    "menu_gap": None,
}, ensure_ascii=False)


# ── build_connoisseur_prompt ────────────────────────────

def test_build_prompt_contains_chapter_text():
    spec = build_connoisseur_prompt(
        chapter_text=CHAPTER_TEXT,
        chapter_ref="第3章",
        menu_items=MENU_ITEMS,
        positive_samples=POS_SAMPLES,
        negative_samples=NEG_SAMPLES,
    )
    assert spec["skill_name"] == "novelist-connoisseur"
    assert CHAPTER_TEXT in spec["prompt"]


def test_build_prompt_contains_menu():
    spec = build_connoisseur_prompt(
        chapter_text=CHAPTER_TEXT,
        chapter_ref="第3章",
        menu_items=MENU_ITEMS,
        positive_samples=[],
        negative_samples=[],
    )
    assert "ANTI_001" in spec["prompt"]
    assert "视角反叛" in spec["prompt"]


def test_build_prompt_contains_samples():
    spec = build_connoisseur_prompt(
        chapter_text=CHAPTER_TEXT,
        chapter_ref="第3章",
        menu_items=[],
        positive_samples=POS_SAMPLES,
        negative_samples=NEG_SAMPLES,
    )
    assert "mp_001" in spec["prompt"]
    assert "mp_002" in spec["prompt"]


def test_build_prompt_empty_samples_graceful():
    spec = build_connoisseur_prompt(
        chapter_text=CHAPTER_TEXT,
        chapter_ref="第3章",
        menu_items=[],
        positive_samples=[],
        negative_samples=[],
    )
    assert spec["skill_name"] == "novelist-connoisseur"
    assert isinstance(spec["prompt"], str)


# ── parse_connoisseur_response ──────────────────────────

def test_parse_with_suggestions():
    resp = parse_connoisseur_response(CONNOISSEUR_JSON_WITH_SUGGESTIONS)
    assert resp.chapter_ref == "第3章"
    assert len(resp.suggestions) == 1
    s = resp.suggestions[0]
    assert s.item_id == "#1"
    assert s.scope_paragraph_index == 1
    assert s.applied_constraint_id == "ANTI_001"
    assert s.confidence == "high"


def test_parse_empty_suggestions():
    resp = parse_connoisseur_response(CONNOISSEUR_JSON_EMPTY)
    assert resp.chapter_ref == "第3章"
    assert len(resp.suggestions) == 0
    assert resp.abstain_reason is not None


def test_parse_invalid_json_raises():
    with pytest.raises(ConnoisseurParseError):
        parse_connoisseur_response("not json")


def test_parse_missing_chapter_ref_raises():
    bad = json.dumps({"suggestions": []})
    with pytest.raises(ConnoisseurParseError):
        parse_connoisseur_response(bad)


# ── suggestions_to_preserve_candidates ─────────────────

def test_suggestions_to_preserve_candidates():
    resp = parse_connoisseur_response(CONNOISSEUR_JSON_WITH_SUGGESTIONS)
    candidates = suggestions_to_preserve_candidates(resp.suggestions)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.item_id == "#1"
    assert c.scope.paragraph_index == 1
    assert c.scope.char_start == 0
    assert c.scope.char_end == 10
    assert c.applied_constraint_id == "ANTI_001"
    assert c.aspects.preserve == ["败者视角反叛"]
    assert len(c.exempt_dimensions) == 1
    assert c.exempt_dimensions[0].sub_items == ["败者视角反叛"]


# ── build_creative_contract ─────────────────────────────

def test_build_contract_all_accepted():
    from core.inspiration.creative_contract import RejectedItem
    resp = parse_connoisseur_response(CONNOISSEUR_JSON_WITH_SUGGESTIONS)
    candidates = suggestions_to_preserve_candidates(resp.suggestions)
    contract = build_creative_contract(
        accepted_items=candidates,
        rejected_items=[],
        chapter_ref="第3章",
    )
    assert contract.chapter_ref == "第3章"
    assert len(contract.preserve_list) == 1
    assert len(contract.rejected_list) == 0
    contract.validate()  # 不应抛出


def test_build_contract_all_rejected():
    """作者全部驳回 → skipped_by_author=False (rejected_list 有内容)"""
    from core.inspiration.creative_contract import RejectedItem
    resp = parse_connoisseur_response(CONNOISSEUR_JSON_WITH_SUGGESTIONS)
    candidates = suggestions_to_preserve_candidates(resp.suggestions)
    rejected = [RejectedItem(item_id=c.item_id, reason="作者驳回") for c in candidates]
    contract = build_creative_contract(
        accepted_items=[],
        rejected_items=rejected,
        chapter_ref="第3章",
        skipped_by_author=False,  # 全部驳回不等于 skipped_by_author=True
    )
    assert contract.skipped_by_author is False
    assert len(contract.preserve_list) == 0
    assert len(contract.rejected_list) == 1
    contract.validate()


# ── MemoryPointSync.list_recent ─────────────────────────

def test_list_recent_returns_by_polarity():
    """list_recent('+') 只返回正样本，list_recent('-') 只返回负样本。"""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from core.inspiration.memory_point_sync import MemoryPointSync, COLLECTION_NAME

    client = QdrantClient(":memory:")
    client.create_collection(
        COLLECTION_NAME,
        vectors_config=VectorParams(size=4, distance=Distance.COSINE),
    )
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(id=1, vector=[0.1, 0.2, 0.3, 0.4], payload={
                "mp_id": "mp_pos_1", "polarity": "+", "segment_text": "pos text",
                "created_at": "2026-04-20T10:00:00+08:00",
            }),
            PointStruct(id=2, vector=[0.5, 0.6, 0.7, 0.8], payload={
                "mp_id": "mp_neg_1", "polarity": "-", "segment_text": "neg text",
                "created_at": "2026-04-20T11:00:00+08:00",
            }),
        ],
    )

    sync = MemoryPointSync(client=client)
    pos = sync.list_recent("+", top_k=5)
    neg = sync.list_recent("-", top_k=5)

    assert len(pos) == 1
    assert pos[0]["payload"]["polarity"] == "+"
    assert len(neg) == 1
    assert neg[0]["payload"]["polarity"] == "-"


def test_list_recent_empty_collection():
    """空集合返回空列表，不报错。"""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams
    from core.inspiration.memory_point_sync import MemoryPointSync, COLLECTION_NAME

    client = QdrantClient(":memory:")
    client.create_collection(
        COLLECTION_NAME,
        vectors_config=VectorParams(size=4, distance=Distance.COSINE),
    )
    sync = MemoryPointSync(client=client)
    result = sync.list_recent("+", top_k=5)
    assert result == []

# 注：NovelWorkflow.run_stage5_5_negotiation() 集成测试需在 .vectorstore 包内单独运行
# 核心逻辑已通过以上 13 个单元测试验证