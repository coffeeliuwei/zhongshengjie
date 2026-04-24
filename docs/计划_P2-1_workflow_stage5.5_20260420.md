# P2-1：阶段 5.5 接入三方协商 实施计划

> **日期**：2026-04-20 13:01（Asia/Shanghai）
> **协议**：本计划遵循 `docs/opencode_dev_protocol_20260420.md v1`
> **分支**：v2-dev
> **For agentic workers:** 使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 按步骤实施。步骤采用 `- [ ]` 格式追踪。

**Goal：** 在 `NovelWorkflow` 中接入阶段 5.5 三方协商，把云溪整章润色后的章节文本交给鉴赏师，解析建议，询问作者采纳意愿，输出 `CreativeContract`。

**Architecture：**
- 新建 `core/inspiration/stage5_5.py` 作为纯函数编排层（无 I/O、无 LLM）
- `MemoryPointSync` 增加 `list_recent()` 方法供 workflow 拉取作者审美指纹
- `NovelWorkflow.run_stage5_5_negotiation()` 三段式调用：A→prompt、B→解析+展示、C→产出契约

**Tech Stack：** Python 3.11、qdrant-client、core/inspiration 已有模块（creative_contract / constraint_library / memory_point_sync）

---

## 文件清单

| 操作 | 路径 |
|------|------|
| 新建 | `core/inspiration/stage5_5.py` |
| 修改 | `core/inspiration/memory_point_sync.py`（增加 `list_recent`） |
| 修改 | `.vectorstore/core/workflow.py`（增加 `run_stage5_5_negotiation`） |
| 新建 | `tests/test_stage5_5.py` |

---

## Task 1：新建 `core/inspiration/stage5_5.py`

**Files：**
- 新建：`core/inspiration/stage5_5.py`

---

### Step 1-1：写失败测试（prompt builder）

**Test file：** `tests/test_stage5_5.py`（先写骨架+第一个测试）

```python
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
    from core.inspiration.creative_contract import RejectedItem
    resp = parse_connoisseur_response(CONNOISSEUR_JSON_WITH_SUGGESTIONS)
    candidates = suggestions_to_preserve_candidates(resp.suggestions)
    rejected = [RejectedItem(item_id=c.item_id, reason="作者驳回") for c in candidates]
    contract = build_creative_contract(
        accepted_items=[],
        rejected_items=rejected,
        chapter_ref="第3章",
        skipped_by_author=True,
    )
    assert contract.skipped_by_author is True
    assert len(contract.preserve_list) == 0
    contract.validate()
```

- [ ] **运行确认失败：**

```bash
python -m pytest tests/test_stage5_5.py -v 2>&1 | tee docs/m7_artifacts/P2-1_stage1_test_run.txt
```

期望：`ImportError: cannot import name 'build_connoisseur_prompt' from 'core.inspiration.stage5_5'`

---

### Step 1-2：实现 `core/inspiration/stage5_5.py`

创建文件 `core/inspiration/stage5_5.py`，内容完整如下：

```python
# core/inspiration/stage5_5.py
"""阶段 5.5 三方协商 — 纯函数编排层 (P2-1)

把 SKILL.md §5.5.1~5.5.3 协议翻译成可测试的纯函数:
  build_connoisseur_prompt()         — 构造发给鉴赏师的 prompt 规格
  parse_connoisseur_response()       — 解析鉴赏师 JSON 输出
  suggestions_to_preserve_candidates() — 建议 → PreserveItem 候选列表
  build_creative_contract()          — 作者采纳后生成 CreativeContract

设计文档: docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md
实施计划: docs/计划_P2-1_workflow_stage5.5_20260420.md
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from core.inspiration.creative_contract import (
    Aspects,
    CreativeContract,
    ExemptDimension,
    NegotiationTurn,
    PreserveItem,
    RejectedItem,
    Scope,
    generate_contract_id,
)

__all__ = [
    "ConnoisseurParseError",
    "ConnoisseurSuggestion",
    "ConnoisseurResponse",
    "build_connoisseur_prompt",
    "parse_connoisseur_response",
    "suggestions_to_preserve_candidates",
    "build_creative_contract",
]

SHANGHAI_TZ = timezone(timedelta(hours=8))


class ConnoisseurParseError(ValueError):
    """鉴赏师 JSON 解析失败。"""


# ── 数据类 ──────────────────────────────────────────────────────────────────


@dataclass
class ConnoisseurSuggestion:
    """鉴赏师单条建议（对应 SKILL.md suggestions[i]）。"""
    item_id: str
    scope_paragraph_index: int
    scope_char_start: int
    scope_char_end: int
    scope_excerpt: str
    applied_constraint_id: str
    applied_constraint_text: str
    rationale: str
    memory_point_refs: List[str]
    confidence: str  # "high" / "medium" / "low"
    expected_impact: str


@dataclass
class ConnoisseurResponse:
    """鉴赏师完整响应（对应 SKILL.md §5.5.3 输出结构）。"""
    chapter_ref: str
    suggestions: List[ConnoisseurSuggestion]
    overall_judgment: Optional[str]
    abstain_reason: Optional[str]
    menu_gap: Optional[List[Dict[str, Any]]]


# ── 私有渲染辅助 ─────────────────────────────────────────────────────────────


def _render_menu(menu_items: List[Dict[str, Any]]) -> str:
    """将约束菜单列表渲染为 SKILL.md §5.5.2 要求的分类文本块。"""
    by_cat: Dict[str, list] = defaultdict(list)
    for item in menu_items:
        by_cat[item["category"]].append(item)

    lines = []
    for cat in sorted(by_cat):
        items = by_cat[cat]
        lines.append(f"{cat}({len(items)}):")
        for it in items:
            lines.append(f"  - {it['id']}  {it['constraint_text']}")
    return "\n".join(lines) if lines else "  (约束库为空)"


def _render_samples(samples: List[Dict[str, Any]], label: str) -> str:
    """将记忆点列表渲染为审美指纹文本块。"""
    if not samples:
        return f"  (无{label})"
    lines = []
    for s in samples:
        payload = s.get("payload", {})
        mp_id = payload.get("mp_id", str(s.get("id", "?")))
        text = payload.get("segment_text", "")[:50]
        lines.append(f"  - {mp_id}: {text}")
    return "\n".join(lines)


# ── 公开函数 ─────────────────────────────────────────────────────────────────


def build_connoisseur_prompt(
    chapter_text: str,
    chapter_ref: str,
    menu_items: List[Dict[str, Any]],
    positive_samples: List[Dict[str, Any]],
    negative_samples: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """构造发给 novelist-connoisseur SKILL 的 prompt 规格。

    Args:
        chapter_text:     云溪整章润色完成的完整章节文本
        chapter_ref:      章节标识（例 "第3章"）
        menu_items:       constraint_library.as_menu() 的返回值
        positive_samples: memory_point_sync.list_recent("+") 的返回值
        negative_samples: memory_point_sync.list_recent("-") 的返回值

    Returns:
        {"skill_name": "novelist-connoisseur", "prompt": str}
    """
    menu_text = _render_menu(menu_items)
    pos_text = _render_samples(positive_samples, "正样本(击中过)")
    neg_text = _render_samples(negative_samples, "负样本(标过乏味)")
    n_menu = len(menu_items)

    prompt = (
        f"## 完整章节文本\n\n{chapter_text}\n\n"
        f"---\n\n"
        f"## 参考资料\n\n"
        f"【反模板约束库菜单({n_menu}条,按类别)】\n{menu_text}\n\n"
        f"【作者审美指纹 - 正样本(击中过)】\n{pos_text}\n\n"
        f"【作者审美指纹 - 负样本(标过乏味)】\n{neg_text}\n\n"
        f"---\n\n"
        f"请按 SKILL.md §5.5.3 格式输出 JSON。"
        f"chapter_ref 填 \"{chapter_ref}\"。"
    )
    return {"skill_name": "novelist-connoisseur", "prompt": prompt}


def parse_connoisseur_response(raw_json: str) -> ConnoisseurResponse:
    """解析鉴赏师返回的 JSON 字符串为 ConnoisseurResponse。

    Raises:
        ConnoisseurParseError: JSON 格式错误或缺少必要字段。
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ConnoisseurParseError(f"JSON 解析失败: {e}") from e

    if "chapter_ref" not in data:
        raise ConnoisseurParseError("缺少必要字段 chapter_ref")

    suggestions: List[ConnoisseurSuggestion] = []
    for s in data.get("suggestions", []):
        scope = s.get("scope", {})
        suggestions.append(
            ConnoisseurSuggestion(
                item_id=s["item_id"],
                scope_paragraph_index=scope["paragraph_index"],
                scope_char_start=scope["char_start"],
                scope_char_end=scope["char_end"],
                scope_excerpt=scope.get("excerpt", ""),
                applied_constraint_id=s["applied_constraint_id"],
                applied_constraint_text=s["applied_constraint_text"],
                rationale=s["rationale"],
                memory_point_refs=s.get("memory_point_refs", []),
                confidence=s["confidence"],
                expected_impact=s.get("expected_impact", ""),
            )
        )

    return ConnoisseurResponse(
        chapter_ref=data["chapter_ref"],
        suggestions=suggestions,
        overall_judgment=data.get("overall_judgment"),
        abstain_reason=data.get("abstain_reason"),
        menu_gap=data.get("menu_gap"),
    )


def suggestions_to_preserve_candidates(
    suggestions: List[ConnoisseurSuggestion],
) -> List[PreserveItem]:
    """将鉴赏师建议列表转为 PreserveItem 候选（供作者采纳/驳回）。

    每条建议映射规则:
      - scope           → Scope(paragraph_index, char_start, char_end)
      - applied_constraint_text → Aspects.preserve[0]（Q2 约定）
      - applied_constraint_id + text → ExemptDimension（Q4 子项豁免）
    """
    items: List[PreserveItem] = []
    for s in suggestions:
        scope = Scope(
            paragraph_index=s.scope_paragraph_index,
            char_start=s.scope_char_start,
            char_end=s.scope_char_end,
        )
        aspects = Aspects(
            preserve=[s.applied_constraint_text],
            drop=[],
        )
        exempt = ExemptDimension(
            dimension=s.applied_constraint_id,
            sub_items=[s.applied_constraint_text],
        )
        items.append(
            PreserveItem(
                item_id=s.item_id,
                scope=scope,
                applied_constraint_id=s.applied_constraint_id,
                rationale=s.rationale,
                evaluator_risk=[],
                aspects=aspects,
                exempt_dimensions=[exempt],
            )
        )
    return items


def build_creative_contract(
    accepted_items: List[PreserveItem],
    rejected_items: List[RejectedItem],
    chapter_ref: str,
    negotiation_log: Optional[List[NegotiationTurn]] = None,
    skipped_by_author: bool = False,
) -> CreativeContract:
    """根据作者采纳决策生成并校验 CreativeContract。

    Args:
        accepted_items:    作者采纳的 PreserveItem 列表
        rejected_items:    作者驳回的 RejectedItem 列表
        chapter_ref:       章节标识
        negotiation_log:   三方协商日志（可为 None）
        skipped_by_author: True = 作者确认跳过（Q1）

    Returns:
        已通过 validate() 的 CreativeContract 实例

    Raises:
        ContractValidationError: 契约数据不合法
    """
    now = datetime.now(SHANGHAI_TZ).isoformat()
    contract = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref=chapter_ref,
        created_at=now,
        negotiation_log=negotiation_log or [],
        preserve_list=accepted_items,
        rejected_list=rejected_items,
        iteration_count=1,
        skipped_by_author=skipped_by_author,
    )
    contract.validate()
    return contract
```

- [ ] **运行测试（Stage 1）：**

```bash
python -m pytest tests/test_stage5_5.py -v 2>&1 | tee -a docs/m7_artifacts/P2-1_stage1_test_run.txt
```

期望：**全部 13 个测试 PASS**

- [ ] **提交：**

```bash
git add core/inspiration/stage5_5.py tests/test_stage5_5.py
git commit -m "feat(p2-1): add stage5_5 pure-function orchestration layer"
```

---

## Task 2：`MemoryPointSync` 增加 `list_recent()`

**Files：**
- 修改：`core/inspiration/memory_point_sync.py`

---

### Step 2-1：写失败测试

在 `tests/test_stage5_5.py` 末尾追加以下测试（使用 in-memory Qdrant）：

```python
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
```

- [ ] **运行确认失败：**

```bash
python -m pytest tests/test_stage5_5.py::test_list_recent_returns_by_polarity tests/test_stage5_5.py::test_list_recent_empty_collection -v 2>&1 | tee -a docs/m7_artifacts/P2-1_stage1_test_run.txt
```

期望：`AttributeError: 'MemoryPointSync' object has no attribute 'list_recent'`

---

### Step 2-2：实现 `list_recent()`

在 `core/inspiration/memory_point_sync.py` 的 `MemoryPointSync` 类中，`get_stats()` 方法之前插入以下方法：

```python
    def list_recent(
        self,
        polarity: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """按极性列出最近的记忆点（按 created_at 降序，不需要 embedding）。

        Args:
            polarity: "+" 为正样本（击中过），"-" 为负样本（标过乏味）
            top_k:    返回条数上限

        Returns:
            List of {"id": str, "payload": dict}，按 created_at 降序
        """
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue

        flt = Filter(
            must=[FieldCondition(key="polarity", match=MatchValue(value=polarity))]
        )
        results, _ = self.client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=flt,
            limit=top_k * 3,  # 取多一些再在内存中排序
            with_payload=True,
        )
        points = [{"id": str(p.id), "payload": p.payload} for p in results]
        points.sort(
            key=lambda x: x["payload"].get("created_at", ""),
            reverse=True,
        )
        return points[:top_k]
```

- [ ] **运行测试（Stage 1 追加）：**

```bash
python -m pytest tests/test_stage5_5.py -v 2>&1 | tee -a docs/m7_artifacts/P2-1_stage1_test_run.txt
```

期望：**全部 15 个测试 PASS**

- [ ] **提交：**

```bash
git add core/inspiration/memory_point_sync.py tests/test_stage5_5.py
git commit -m "feat(p2-1): add MemoryPointSync.list_recent for aesthetic fingerprint retrieval"
```

---

## Task 3：`NovelWorkflow.run_stage5_5_negotiation()`

**Files：**
- 修改：`.vectorstore/core/workflow.py`

---

### Step 3-1：写失败测试

在 `tests/test_stage5_5.py` 末尾追加以下测试：

```python
# ── NovelWorkflow.run_stage5_5_negotiation ─────────────

def test_workflow_stage5_5_phase_a(monkeypatch):
    """Phase A：返回 pending_connoisseur 状态和 prompt。"""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / ".vectorstore"))

    from core.workflow import NovelWorkflow
    from unittest.mock import MagicMock, patch

    wf = NovelWorkflow.__new__(NovelWorkflow)

    with patch("core.inspiration.constraint_library.ConstraintLibrary.as_menu", return_value=MENU_ITEMS), \
         patch("core.inspiration.memory_point_sync.MemoryPointSync.list_recent", return_value=[]):
        result = wf.run_stage5_5_negotiation(
            chapter_text=CHAPTER_TEXT,
            chapter_ref="第3章",
        )

    assert result["status"] == "pending_connoisseur"
    assert result["skill_name"] == "novelist-connoisseur"
    assert CHAPTER_TEXT in result["prompt"]


def test_workflow_stage5_5_phase_b_with_suggestions(monkeypatch):
    """Phase B：解析建议后返回 pending_author 状态。"""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / ".vectorstore"))

    from core.workflow import NovelWorkflow

    wf = NovelWorkflow.__new__(NovelWorkflow)

    result = wf.run_stage5_5_negotiation(
        chapter_text=CHAPTER_TEXT,
        chapter_ref="第3章",
        connoisseur_raw=CONNOISSEUR_JSON_WITH_SUGGESTIONS,
    )

    assert result["status"] == "pending_author"
    assert len(result["suggestions"]) == 1
    assert result["suggestions"][0]["item_id"] == "#1"
    assert "display_text" in result


def test_workflow_stage5_5_phase_b_empty_suggestions():
    """Phase B：0条建议 → Q1 要求作者确认跳过。"""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / ".vectorstore"))

    from core.workflow import NovelWorkflow

    wf = NovelWorkflow.__new__(NovelWorkflow)

    result = wf.run_stage5_5_negotiation(
        chapter_text=CHAPTER_TEXT,
        chapter_ref="第3章",
        connoisseur_raw=CONNOISSEUR_JSON_EMPTY,
    )

    assert result["status"] == "pending_author_skip_confirm"
    assert result["abstain_reason"] is not None


def test_workflow_stage5_5_phase_c_accepted():
    """Phase C：作者采纳建议 → contract_ready + CreativeContract。"""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / ".vectorstore"))

    from core.workflow import NovelWorkflow

    wf = NovelWorkflow.__new__(NovelWorkflow)

    result = wf.run_stage5_5_negotiation(
        chapter_text=CHAPTER_TEXT,
        chapter_ref="第3章",
        connoisseur_raw=CONNOISSEUR_JSON_WITH_SUGGESTIONS,
        accepted_ids=["#1"],
    )

    assert result["status"] == "contract_ready"
    contract = result["contract"]
    assert len(contract.preserve_list) == 1
    assert contract.preserve_list[0].item_id == "#1"
    contract.validate()


def test_workflow_stage5_5_phase_c_all_rejected():
    """Phase C：作者全部驳回 → skipped_by_author=True。"""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / ".vectorstore"))

    from core.workflow import NovelWorkflow

    wf = NovelWorkflow.__new__(NovelWorkflow)

    result = wf.run_stage5_5_negotiation(
        chapter_text=CHAPTER_TEXT,
        chapter_ref="第3章",
        connoisseur_raw=CONNOISSEUR_JSON_WITH_SUGGESTIONS,
        accepted_ids=[],
    )

    assert result["status"] == "contract_ready"
    assert result["contract"].skipped_by_author is True
```

- [ ] **运行确认失败：**

```bash
python -m pytest tests/test_stage5_5.py::test_workflow_stage5_5_phase_a -v 2>&1 | tee -a docs/m7_artifacts/P2-1_stage1_test_run.txt
```

期望：`AttributeError: type object 'NovelWorkflow' has no attribute 'run_stage5_5_negotiation'`

---

### Step 3-2：实现 `run_stage5_5_negotiation()`

在 `.vectorstore/core/workflow.py` 的 `NovelWorkflow` 类中，`run_stage4_inspiration()` 方法之后（约 2385 行附近）插入以下方法：

```python
    def run_stage5_5_negotiation(
        self,
        chapter_text: str,
        chapter_ref: str,
        scene_type: Optional[str] = None,
        connoisseur_raw: Optional[str] = None,
        accepted_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Stage 5.5 三方协商三段式编排。

        调用约定（三阶段）
        -----------------
        Phase A — 获取鉴赏师 prompt（connoisseur_raw=None, accepted_ids=None）:
            spec = workflow.run_stage5_5_negotiation(chapter_text, chapter_ref)
            # spec["status"] == "pending_connoisseur"
            # spec["skill_name"] / spec["prompt"] → 发给 novelist-connoisseur Skill

        Phase B — 提交鉴赏师 JSON，获取建议列表（connoisseur_raw=<json>, accepted_ids=None）:
            result = workflow.run_stage5_5_negotiation(
                chapter_text, chapter_ref, connoisseur_raw=raw
            )
            # result["status"] == "pending_author"          → 有建议，展示 display_text 给作者
            # result["status"] == "pending_author_skip_confirm" → 0条建议，Q1询问作者确认跳过

        Phase C — 提交作者决策，生成契约（connoisseur_raw=<json>, accepted_ids=[...]）:
            final = workflow.run_stage5_5_negotiation(
                chapter_text, chapter_ref,
                connoisseur_raw=raw, accepted_ids=["#1", "#2"]
            )
            # final["status"] == "contract_ready"
            # final["contract"] → CreativeContract 实例

        Q1 贯彻：accepted_ids=[] 时（全部驳回）→ contract.skipped_by_author=True

        Args:
            chapter_text:     整章文本（云溪润色后版本）
            chapter_ref:      章节标识（例 "第3章"）
            scene_type:       场景类型，用于约束菜单筛选（None=全部）
            connoisseur_raw:  鉴赏师返回的 JSON 字符串（Phase B/C）
            accepted_ids:     作者采纳的建议 item_id 列表（Phase C）

        Returns:
            Phase A: {"status": "pending_connoisseur", "skill_name": str, "prompt": str}
            Phase B: {"status": "pending_author", "suggestions": [...], "display_text": str, ...}
                  or {"status": "pending_author_skip_confirm", "abstain_reason": str, ...}
            Phase C: {"status": "contract_ready", "contract": CreativeContract}
        """
        from core.inspiration.stage5_5 import (
            build_connoisseur_prompt,
            parse_connoisseur_response,
            suggestions_to_preserve_candidates,
            build_creative_contract,
        )
        from core.inspiration.constraint_library import ConstraintLibrary
        from core.inspiration.memory_point_sync import MemoryPointSync
        from core.inspiration.creative_contract import RejectedItem

        # ── Phase A：构造 prompt ──────────────────────────────────────────────
        if connoisseur_raw is None and accepted_ids is None:
            lib = ConstraintLibrary()
            menu = lib.as_menu(scene_type)

            try:
                mp_sync = MemoryPointSync()
                positive = mp_sync.list_recent("+", top_k=5)
                negative = mp_sync.list_recent("-", top_k=5)
            except Exception:
                positive, negative = [], []

            spec = build_connoisseur_prompt(
                chapter_text=chapter_text,
                chapter_ref=chapter_ref,
                menu_items=menu,
                positive_samples=positive,
                negative_samples=negative,
            )
            return {**spec, "status": "pending_connoisseur"}

        # ── Phase B：解析 connoisseur 返回 ────────────────────────────────────
        if connoisseur_raw is not None and accepted_ids is None:
            response = parse_connoisseur_response(connoisseur_raw)

            if not response.suggestions:
                # Q1：0条建议 → 不自动跳过，询问作者
                return {
                    "status": "pending_author_skip_confirm",
                    "abstain_reason": response.abstain_reason,
                    "menu_gap": response.menu_gap,
                    "overall_judgment": response.overall_judgment,
                }

            candidates = suggestions_to_preserve_candidates(response.suggestions)
            display_lines = [f"鉴赏师发现 {len(candidates)} 条创意建议："]
            for c in candidates:
                display_lines.append(
                    f"\n  {c.item_id} [段落 {c.scope.paragraph_index}]"
                    f" {c.applied_constraint_id}: {c.rationale}"
                )
            display_lines.append(
                "\n请回复采纳的 item_id 列表（例：['#1', '#2']），或 [] 全部驳回。"
            )

            return {
                "status": "pending_author",
                "suggestions": [
                    {
                        "item_id": s.item_id,
                        "paragraph": s.scope_paragraph_index,
                        "constraint": s.applied_constraint_id,
                        "rationale": s.rationale,
                        "confidence": s.confidence,
                    }
                    for s in response.suggestions
                ],
                "overall_judgment": response.overall_judgment,
                "display_text": "\n".join(display_lines),
            }

        # ── Phase C：生成契约 ─────────────────────────────────────────────────
        if connoisseur_raw is not None and accepted_ids is not None:
            response = parse_connoisseur_response(connoisseur_raw)
            all_candidates = suggestions_to_preserve_candidates(response.suggestions)

            accepted_set = set(accepted_ids)
            accepted = [c for c in all_candidates if c.item_id in accepted_set]
            rejected = [
                RejectedItem(item_id=c.item_id, reason="作者驳回")
                for c in all_candidates
                if c.item_id not in accepted_set
            ]

            skipped = not accepted and bool(response.suggestions)
            contract = build_creative_contract(
                accepted_items=accepted,
                rejected_items=rejected,
                chapter_ref=chapter_ref,
                skipped_by_author=skipped,
            )
            return {"status": "contract_ready", "contract": contract}

        # 参数组合不合法（只有 accepted_ids 但没有 connoisseur_raw）
        raise ValueError(
            "run_stage5_5_negotiation: accepted_ids 必须配合 connoisseur_raw 使用"
        )
```

> **注意**：`workflow.py` 使用的 `Optional` 和 `List` 已在文件顶部 import，确认 `from typing import Optional, List, Dict, Any` 存在（行约 7~10），无需额外添加。

- [ ] **运行测试（Stage 2）：**

```bash
python -m pytest tests/test_stage5_5.py -v 2>&1 | tee docs/m7_artifacts/P2-1_stage2_test_run.txt
```

期望：**全部 20 个测试 PASS**

- [ ] **提交：**

```bash
git add .vectorstore/core/workflow.py
git commit -m "feat(p2-1): add NovelWorkflow.run_stage5_5_negotiation three-phase negotiation"
```

---

## Task 4：全量回归

### Step 4-1：Stage 3 — 专项测试

```bash
python -m pytest tests/test_stage5_5.py tests/test_creative_contract.py tests/test_dispatcher.py -v 2>&1 | tee docs/m7_artifacts/P2-1_stage3_test_run.txt
```

期望：全部 PASS（无新增 failure）

### Step 4-2：Stage 4 — 全量 pytest

```bash
python -m pytest tests/ -q 2>&1 | tee docs/m7_artifacts/P2-1_stage4_test_run.txt
```

期望：**≥ 639 passed**（619 基线 + 20 新增），3 failed（预存在），2 skipped

> 若出现新 failure，对照 `P2-1_stage4_test_run.txt` 逐条排查，**不得跳过**。

### Step 4-3：最终提交

```bash
git add docs/m7_artifacts/P2-1_stage*_test_run.txt
git commit -m "test(p2-1): add stage 5.5 negotiation tests; baseline 639+ passed"
```

---

## 验收标准

| 项 | 期望 |
|----|------|
| `stage5_5.py` 所有函数 | 单元测试全 PASS（13 个） |
| `list_recent()` | 单元测试全 PASS（2 个） |
| `run_stage5_5_negotiation()` | Phase A/B/C + Q1 全 PASS（5 个） |
| 全量 pytest | ≥ 639 passed，3 failed（预存在），无新 failure |
| `stage_*_test_run.txt` | 4 份日志均已提交 |

---

## Q1 贯彻确认

- `accepted_ids=[]` 时 → `contract.skipped_by_author = True`（不自动跳，Phase C 处理）
- Phase B 0条建议 → `status = "pending_author_skip_confirm"`，等待作者明确确认

---

## 完成后 Claude 的动作

opencode 完成后，Claude 需要：
1. 检查 Stage 4 日志确认 ≥ 639 passed
2. 更新 ROADMAP P2-1 状态为 ✅
3. 写 P2-2 计划（阶段 5.6 派单执行接入 workflow）
