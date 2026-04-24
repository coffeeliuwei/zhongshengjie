# 计划 P1-1:创意契约数据模型(creative_contract.py)

- **创建时间**:2026-04-19 (Asia/Shanghai)
- **执行者**:opencode (GLM5)
- **路线图位置**:[ROADMAP_众生界v2实施_20260419.md](./ROADMAP_众生界v2实施_20260419.md) §3.2 P1-1
- **依据设计**:[2026-04-19-inspiration-engine-design-v2.md](./superpowers/specs/2026-04-19-inspiration-engine-design-v2.md) §4
- **前置决策**:Q1-Q4 作者已表态(见 §0.3)
- **Python**:3.12.7(stdlib-only,不得引入 pydantic/attrs/marshmallow)
- **Shell**:bash

---

## 0. 本计划的目的 — 必读

P1-1 只做**创意契约数据模型与序列化**,产出独立可测的模块,**不碰** workflow / evaluator / dispatcher / skill 文件。

### 0.1 范围边界(不得扩张)

- ✅ 新建 `core/inspiration/creative_contract.py`(单文件,stdlib-only)
- ✅ 新建 `tests/test_creative_contract.py`
- ✅ 修改 `core/inspiration/__init__.py`(仅追加导出)
- ❌ 不动 `workflow.py`、`appraisal_agent.py`、`evaluator` 相关代码
- ❌ 不动任何 SKILL.md
- ❌ 不动 `.archived/` / `.vectorstore/`
- ❌ 不引入第三方依赖(pydantic/attrs/marshmallow 禁用)
- ❌ 不 git commit(除非 §5 自检全 PASS 且作者授权)

### 0.2 产出清单

| 文件 | 类型 | 验收 |
|------|------|------|
| `core/inspiration/creative_contract.py` | 新建 | pytest 本模块测试全 PASS,mypy/语法无误 |
| `tests/test_creative_contract.py` | 新建 | ≥ 25 个测试用例,覆盖数据模型 / 序列化 / 校验 / ID 生成 |
| `core/inspiration/__init__.py` | 修改 | 新增 6 个导出符号(见 §3.Task 11) |

### 0.3 作者已表态的 4 个决策(必须贯彻到代码)

| # | 决策 | 体现在 |
|---|------|--------|
| Q1 | 鉴赏师 0 条建议时不自动跳过,需作者确认 | 数据模型含 `skipped_by_author: bool = False` 字段 |
| Q2 | `preserve_list` 支持嵌套(item 内部分 preserve / drop aspects) | `PreserveItem.aspects: Aspects` 子结构 |
| Q3 | `author_force_pass` 不影响下次同类型鉴赏倾向 | 契约**不含**权重回流字段(本计划只需"不做"就够) |
| Q4 | 评估师豁免支持 `partial_exempt`(子项粒度) | `exempt_dimensions: List[ExemptDimension]`,`ExemptDimension.sub_items` 非空 |

---

## 1. 执行前真实状态

```
core/inspiration/
├── __init__.py                   [将修改:追加 6 个导出]
├── appraisal_agent.py            [不动]
├── audit_trigger.py              [不动]
├── constraint_library.py         [不动]
├── embedder.py                   [不动]
├── escalation_dialogue.py        [不动]
├── memory_point_sync.py          [不动]
├── resonance_feedback.py         [不动]
├── segment_locator.py            [不动]
├── status_reporter.py            [不动]
├── structural_analyzer.py        [不动]
├── variant_generator.py          [不动]
├── workflow_bridge.py            [不动]
└── creative_contract.py          [将新建]

tests/
├── (已有 47 个测试文件,不动)
└── test_creative_contract.py     [将新建]
```

pytest 基线:**467 passed / 1 skipped**。P1-1 完成后应为 **467 + N passed**(N = 新增测试数,≥ 25)。

---

## 2. opencode 执行规则(不可违反)

### 2.1 允许的操作

1. Write 工具新建 2 个文件(§3.Task 1 + §3.Task 12)
2. Edit 工具修改 `core/inspiration/__init__.py`(仅追加 import 与 `__all__`,不改已有行)
3. 按 §3 任务顺序,每任务内部按"写测试 → 跑测试 FAIL → 写实现 → 跑测试 PASS"执行(TDD)
4. 跑 §5 自检

### 2.2 禁止的操作

- ❌ 不引入第三方库(只能 stdlib)
- ❌ 不改 `core/inspiration/` 下其他 `.py` 文件
- ❌ 不改 SKILL.md
- ❌ 不 git commit
- ❌ 不跳步 — §3 Task 1-13 必须全做
- ❌ `created_at` 不得用 `datetime.now()` 裸调(必须显式 Shanghai tz,见 §3.Task 7)

### 2.3 TDD 严格执行

**每个 Task 内部按 "先写测试 → 跑测试见 FAIL → 写实现 → 跑测试见 PASS" 五步走,中间任一步失败立即停止并报告,不得跳到下个 Task。**

---

## 3. 执行步骤(按 Task 1 → Task 13 顺序)

### Task 1:创建 `creative_contract.py` 骨架 + 模块 docstring

**文件**:
- 新建:`core/inspiration/creative_contract.py`
- 测试:`tests/test_creative_contract.py`(骨架)

#### 步骤

- [ ] **1.1 用 Write 工具新建 `core/inspiration/creative_contract.py`**,完整内容:

```python
"""创意契约(Creative Contract)数据模型。

由鉴赏师 + 评估师 + 作者三方协商产出的本章创意锁定契约。
阶段 5.5 生成 → 阶段 5.6 派单写手使用 → 阶段 6 评估师按 exempt_dimensions 豁免 →
阶段 7 作者可撤销某条(进 rejected_list)或强制通过。

设计文档:docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md §4
实施计划:docs/计划_P1-1_creative_contract_20260419.md

【关键决策贯彻】
- Q1 鉴赏师 0 条建议时由作者决定跳过:见 `CreativeContract.skipped_by_author`
- Q2 preserve_list 支持嵌套 aspects:见 `PreserveItem.aspects`
- Q3 author_force_pass 不回流权重:本模块**不持有**权重字段,归档即止
- Q4 评估师豁免按子项:见 `ExemptDimension.sub_items`(非空)
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import List, Literal, Optional
import json
import re
import secrets

__all__ = [
    "Scope",
    "Aspects",
    "ExemptDimension",
    "PreserveItem",
    "RejectedItem",
    "NegotiationTurn",
    "WriterAssignment",
    "CreativeContract",
    "generate_contract_id",
    "ContractValidationError",
]

SHANGHAI_TZ = timezone(timedelta(hours=8))
_CONTRACT_ID_PATTERN = re.compile(r"^cc_\d{8}_[0-9a-f]{6}$")


class ContractValidationError(ValueError):
    """契约数据校验失败。"""
```

- [ ] **1.2 用 Write 工具新建 `tests/test_creative_contract.py`**,完整内容:

```python
"""core/inspiration/creative_contract.py 的单元测试。

覆盖:
- Scope / Aspects / ExemptDimension / PreserveItem / RejectedItem /
  NegotiationTurn / WriterAssignment / CreativeContract 各 dataclass
- 校验:字段非空 / 子项非空 / preserve 与 drop 不重叠 / iteration <= max_iterations /
  writer_assignments 引用的 item_id 必须在 preserve_list / contract_id 正则
- 序列化:to_json / from_json 往返
- ID 生成器:格式 cc_YYYYMMDD_<6hex>,Shanghai 日期

依据计划:docs/计划_P1-1_creative_contract_20260419.md
"""
from __future__ import annotations

import json
import re
import pytest

from core.inspiration.creative_contract import (
    Scope,
    Aspects,
    ExemptDimension,
    PreserveItem,
    RejectedItem,
    NegotiationTurn,
    WriterAssignment,
    CreativeContract,
    generate_contract_id,
    ContractValidationError,
)


def test_module_importable():
    """冒烟:模块可导入,所有 __all__ 符号已定义。"""
    from core.inspiration import creative_contract as cc
    for name in cc.__all__:
        assert hasattr(cc, name), f"{name} 不在模块中"
```

- [ ] **1.3 跑测试验证骨架可跑**:

```bash
cd "D:/动画/众生界"
python -m pytest tests/test_creative_contract.py -v
```

预期:1 passed(`test_module_importable`)。

---

### Task 2:`Scope` dataclass(段落定位)

#### 步骤

- [ ] **2.1 追加测试**(到 `tests/test_creative_contract.py` 末尾):

```python
# ===================== Scope =====================

def test_scope_basic():
    s = Scope(paragraph_index=3, char_start=234, char_end=567)
    assert s.paragraph_index == 3
    assert s.char_start == 234
    assert s.char_end == 567


def test_scope_rejects_negative_paragraph():
    with pytest.raises(ContractValidationError, match="paragraph_index"):
        Scope(paragraph_index=-1, char_start=0, char_end=10).validate()


def test_scope_rejects_char_start_ge_end():
    with pytest.raises(ContractValidationError, match="char_start"):
        Scope(paragraph_index=0, char_start=10, char_end=10).validate()
    with pytest.raises(ContractValidationError, match="char_start"):
        Scope(paragraph_index=0, char_start=20, char_end=10).validate()


def test_scope_rejects_negative_char_start():
    with pytest.raises(ContractValidationError, match="char_start"):
        Scope(paragraph_index=0, char_start=-1, char_end=5).validate()
```

- [ ] **2.2 跑测试**:`python -m pytest tests/test_creative_contract.py -v`。预期 `test_scope_*` 全 FAIL(Scope 未定义,或 validate 未定义)。

- [ ] **2.3 追加实现**(到 `core/inspiration/creative_contract.py` 末尾):

```python
# ===================== Scope =====================

@dataclass
class Scope:
    """段落内字符偏移区间 [char_start, char_end)。"""
    paragraph_index: int
    char_start: int
    char_end: int

    def validate(self) -> None:
        if self.paragraph_index < 0:
            raise ContractValidationError(
                f"paragraph_index 必须 >= 0,实得 {self.paragraph_index}"
            )
        if self.char_start < 0:
            raise ContractValidationError(
                f"char_start 必须 >= 0,实得 {self.char_start}"
            )
        if self.char_start >= self.char_end:
            raise ContractValidationError(
                f"char_start ({self.char_start}) 必须 < char_end ({self.char_end})"
            )
```

- [ ] **2.4 跑测试**:预期 4 个 `test_scope_*` 全 PASS,累计 5 passed。

---

### Task 3:`Aspects` dataclass(Q2 嵌套核心)

#### 步骤

- [ ] **3.1 追加测试**:

```python
# ===================== Aspects (Q2 嵌套核心) =====================

def test_aspects_basic():
    a = Aspects(preserve=["情绪强度", "心理动机"], drop=["具体台词"])
    assert a.preserve == ["情绪强度", "心理动机"]
    assert a.drop == ["具体台词"]


def test_aspects_preserve_non_empty_required():
    """Q2:至少保留一个子面,否则失去契约意义。"""
    with pytest.raises(ContractValidationError, match="preserve.*非空"):
        Aspects(preserve=[], drop=["台词"]).validate()


def test_aspects_drop_may_be_empty():
    """drop 可空,表示"整体保留"。"""
    Aspects(preserve=["情绪"], drop=[]).validate()  # 不应抛


def test_aspects_no_overlap():
    """preserve 与 drop 不得有重叠项(语义矛盾)。"""
    with pytest.raises(ContractValidationError, match="重叠"):
        Aspects(preserve=["情绪", "台词"], drop=["台词"]).validate()


def test_aspects_strips_blank_strings():
    """空字符串或纯空白视为非法。"""
    with pytest.raises(ContractValidationError, match="空字符串"):
        Aspects(preserve=["情绪", ""], drop=[]).validate()
    with pytest.raises(ContractValidationError, match="空字符串"):
        Aspects(preserve=["情绪"], drop=["   "]).validate()
```

- [ ] **3.2 跑测试**:预期 `test_aspects_*` 全 FAIL。

- [ ] **3.3 追加实现**:

```python
# ===================== Aspects (Q2 嵌套核心) =====================

@dataclass
class Aspects:
    """preserve_list[i] 内部的细粒度面切分(Q2 嵌套)。

    preserve: 必须锁定的子面(例:"情绪强度", "心理动机")
    drop:     可放开给写手重写的子面(例:"具体台词", "肢体表现")
    """
    preserve: List[str]
    drop: List[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.preserve:
            raise ContractValidationError(
                "Aspects.preserve 必须非空(否则失去契约意义,整体弃用请用 rejected_list)"
            )
        for s in self.preserve + self.drop:
            if not s or not s.strip():
                raise ContractValidationError(
                    f"Aspects 不允许空字符串或纯空白项,实得 {s!r}"
                )
        overlap = set(self.preserve) & set(self.drop)
        if overlap:
            raise ContractValidationError(
                f"Aspects.preserve 与 drop 不得重叠,冲突项:{sorted(overlap)}"
            )
```

- [ ] **3.4 跑测试**:预期 5 个 `test_aspects_*` 全 PASS,累计 10 passed。

---

### Task 4:`ExemptDimension` dataclass(Q4 子项豁免核心)

#### 步骤

- [ ] **4.1 追加测试**:

```python
# ===================== ExemptDimension (Q4 子项豁免) =====================

def test_exempt_dimension_basic():
    e = ExemptDimension(dimension="视角连贯性", sub_items=["主角一致性"])
    assert e.dimension == "视角连贯性"
    assert e.sub_items == ["主角一致性"]


def test_exempt_dimension_sub_items_non_empty_required():
    """Q4:禁止空 sub_items(避免误伤整维度)。"""
    with pytest.raises(ContractValidationError, match="sub_items.*非空"):
        ExemptDimension(dimension="视角连贯性", sub_items=[]).validate()


def test_exempt_dimension_rejects_blank_name():
    with pytest.raises(ContractValidationError, match="dimension.*非空"):
        ExemptDimension(dimension="", sub_items=["X"]).validate()
    with pytest.raises(ContractValidationError, match="dimension.*非空"):
        ExemptDimension(dimension="   ", sub_items=["X"]).validate()


def test_exempt_dimension_rejects_blank_sub_item():
    with pytest.raises(ContractValidationError, match="sub_items"):
        ExemptDimension(dimension="D", sub_items=["X", ""]).validate()
```

- [ ] **4.2 跑测试**:预期 FAIL。

- [ ] **4.3 追加实现**:

```python
# ===================== ExemptDimension (Q4 子项豁免) =====================

@dataclass
class ExemptDimension:
    """评估师豁免项(Q4 子项粒度)。

    sub_items 必须非空 — 整维度豁免已证明会导致整体偏离,禁止。
    如需豁免"某维度的所有子项",请显式列出全部子项名称。
    """
    dimension: str
    sub_items: List[str]

    def validate(self) -> None:
        if not self.dimension or not self.dimension.strip():
            raise ContractValidationError("ExemptDimension.dimension 必须非空")
        if not self.sub_items:
            raise ContractValidationError(
                f"ExemptDimension.sub_items 必须非空(维度 {self.dimension!r})— "
                "Q4 禁止整维度豁免,请显式列出子项"
            )
        for s in self.sub_items:
            if not s or not s.strip():
                raise ContractValidationError(
                    f"ExemptDimension.sub_items 不允许空字符串(维度 {self.dimension!r})"
                )
```

- [ ] **4.4 跑测试**:预期 4 个 `test_exempt_*` 全 PASS,累计 14 passed。

---

### Task 5:`PreserveItem` dataclass(聚合 Scope + Aspects + ExemptDimension)

#### 步骤

- [ ] **5.1 追加测试**:

```python
# ===================== PreserveItem =====================

def _make_preserve_item(**overrides):
    base = dict(
        item_id="#1",
        scope=Scope(paragraph_index=3, char_start=234, char_end=567),
        applied_constraint_id="ANTI_001",
        rationale="鉴赏师 + 作者共识: 败者视角 +3 爽快累计 7 条",
        evaluator_risk=["主角视角连贯性 -0.1"],
        aspects=Aspects(preserve=["情绪强度", "心理动机"], drop=["具体台词"]),
        exempt_dimensions=[
            ExemptDimension(dimension="视角连贯性", sub_items=["主角一致性"]),
        ],
    )
    base.update(overrides)
    return PreserveItem(**base)


def test_preserve_item_basic():
    p = _make_preserve_item()
    p.validate()
    assert p.item_id == "#1"
    assert p.aspects.preserve == ["情绪强度", "心理动机"]


def test_preserve_item_id_format():
    """item_id 必须以 # 开头后接数字(#1, #42, ...)。"""
    _make_preserve_item(item_id="#1").validate()
    _make_preserve_item(item_id="#42").validate()
    with pytest.raises(ContractValidationError, match="item_id"):
        _make_preserve_item(item_id="1").validate()
    with pytest.raises(ContractValidationError, match="item_id"):
        _make_preserve_item(item_id="#abc").validate()
    with pytest.raises(ContractValidationError, match="item_id"):
        _make_preserve_item(item_id="").validate()


def test_preserve_item_applied_constraint_id_optional():
    """applied_constraint_id 可为 None(非约束库触发的创意)。"""
    p = _make_preserve_item(applied_constraint_id=None)
    p.validate()


def test_preserve_item_rationale_non_empty():
    with pytest.raises(ContractValidationError, match="rationale"):
        _make_preserve_item(rationale="").validate()
    with pytest.raises(ContractValidationError, match="rationale"):
        _make_preserve_item(rationale="   ").validate()


def test_preserve_item_propagates_sub_validation():
    """嵌套字段的校验错误必须上浮。"""
    with pytest.raises(ContractValidationError, match="preserve"):
        _make_preserve_item(aspects=Aspects(preserve=[], drop=["台词"])).validate()
    with pytest.raises(ContractValidationError, match="sub_items"):
        _make_preserve_item(
            exempt_dimensions=[ExemptDimension(dimension="D", sub_items=[])]
        ).validate()


def test_preserve_item_exempt_dimensions_may_be_empty():
    """exempt_dimensions 允许空列表(不豁免任何维度)。"""
    p = _make_preserve_item(exempt_dimensions=[])
    p.validate()
```

- [ ] **5.2 跑测试**:预期 FAIL。

- [ ] **5.3 追加实现**:

```python
# ===================== PreserveItem =====================

_ITEM_ID_PATTERN = re.compile(r"^#\d+$")


@dataclass
class PreserveItem:
    """preserve_list 中的一条:采纳的创意手法,带嵌套 aspects + 子项豁免。"""
    item_id: str
    scope: Scope
    applied_constraint_id: Optional[str]
    rationale: str
    evaluator_risk: List[str]
    aspects: Aspects
    exempt_dimensions: List[ExemptDimension] = field(default_factory=list)

    def validate(self) -> None:
        if not _ITEM_ID_PATTERN.match(self.item_id or ""):
            raise ContractValidationError(
                f"item_id 必须匹配 /^#\\d+$/,实得 {self.item_id!r}"
            )
        if not self.rationale or not self.rationale.strip():
            raise ContractValidationError("PreserveItem.rationale 必须非空")
        self.scope.validate()
        self.aspects.validate()
        for ed in self.exempt_dimensions:
            ed.validate()
```

- [ ] **5.4 跑测试**:预期 6 个 `test_preserve_item_*` 全 PASS,累计 20 passed。

---

### Task 6:`RejectedItem` + `NegotiationTurn` + `WriterAssignment` dataclass

#### 步骤

- [ ] **6.1 追加测试**:

```python
# ===================== RejectedItem / NegotiationTurn / WriterAssignment =====================

def test_rejected_item_basic():
    r = RejectedItem(item_id="#2", reason="评估师标 12 一致性规则#7 违规")
    r.validate()


def test_rejected_item_id_format():
    with pytest.raises(ContractValidationError, match="item_id"):
        RejectedItem(item_id="2", reason="x").validate()


def test_rejected_item_reason_non_empty():
    with pytest.raises(ContractValidationError, match="reason"):
        RejectedItem(item_id="#2", reason="").validate()


def test_negotiation_turn_speakers():
    for sp in ("connoisseur", "evaluator", "author"):
        t = NegotiationTurn(speaker=sp, msg="x", timestamp="2026-04-19T12:00:00+08:00")
        t.validate()


def test_negotiation_turn_rejects_unknown_speaker():
    with pytest.raises(ContractValidationError, match="speaker"):
        NegotiationTurn(speaker="writer", msg="x", timestamp="2026-04-19T12:00:00+08:00").validate()


def test_negotiation_turn_msg_non_empty():
    with pytest.raises(ContractValidationError, match="msg"):
        NegotiationTurn(speaker="author", msg="", timestamp="2026-04-19T12:00:00+08:00").validate()


def test_writer_assignment_basic():
    w = WriterAssignment(item_id="#1", writer="novelist-jianchen", task="rewrite_paragraph")
    w.validate()


def test_writer_assignment_writer_whitelist():
    """writer 必须在 5 写手白名单内。"""
    valid = ["novelist-jianchen", "novelist-canglan", "novelist-moyan",
             "novelist-xuanyi", "novelist-yunxi"]
    for w in valid:
        WriterAssignment(item_id="#1", writer=w, task="rewrite_paragraph").validate()
    with pytest.raises(ContractValidationError, match="writer"):
        WriterAssignment(item_id="#1", writer="novelist-wrong", task="x").validate()


def test_writer_assignment_task_non_empty():
    with pytest.raises(ContractValidationError, match="task"):
        WriterAssignment(
            item_id="#1", writer="novelist-jianchen", task=""
        ).validate()
```

- [ ] **6.2 跑测试**:预期 FAIL。

- [ ] **6.3 追加实现**:

```python
# ===================== RejectedItem =====================

@dataclass
class RejectedItem:
    """被驳回的鉴赏师建议。"""
    item_id: str
    reason: str

    def validate(self) -> None:
        if not _ITEM_ID_PATTERN.match(self.item_id or ""):
            raise ContractValidationError(
                f"RejectedItem.item_id 必须匹配 /^#\\d+$/,实得 {self.item_id!r}"
            )
        if not self.reason or not self.reason.strip():
            raise ContractValidationError("RejectedItem.reason 必须非空")


# ===================== NegotiationTurn =====================

_VALID_SPEAKERS = ("connoisseur", "evaluator", "author")


@dataclass
class NegotiationTurn:
    """三方协商的一轮发言。"""
    speaker: str  # Literal["connoisseur", "evaluator", "author"]
    msg: str
    timestamp: str  # ISO 8601

    def validate(self) -> None:
        if self.speaker not in _VALID_SPEAKERS:
            raise ContractValidationError(
                f"NegotiationTurn.speaker 必须在 {_VALID_SPEAKERS},实得 {self.speaker!r}"
            )
        if not self.msg or not self.msg.strip():
            raise ContractValidationError("NegotiationTurn.msg 必须非空")
        if not self.timestamp or not self.timestamp.strip():
            raise ContractValidationError("NegotiationTurn.timestamp 必须非空")


# ===================== WriterAssignment =====================

_VALID_WRITERS = (
    "novelist-jianchen",
    "novelist-canglan",
    "novelist-moyan",
    "novelist-xuanyi",
    "novelist-yunxi",
)


@dataclass
class WriterAssignment:
    """派单:把某 preserve_item 指派给某写手。"""
    item_id: str
    writer: str
    task: str

    def validate(self) -> None:
        if not _ITEM_ID_PATTERN.match(self.item_id or ""):
            raise ContractValidationError(
                f"WriterAssignment.item_id 必须匹配 /^#\\d+$/,实得 {self.item_id!r}"
            )
        if self.writer not in _VALID_WRITERS:
            raise ContractValidationError(
                f"WriterAssignment.writer 必须在 {_VALID_WRITERS},实得 {self.writer!r}"
            )
        if not self.task or not self.task.strip():
            raise ContractValidationError("WriterAssignment.task 必须非空")
```

- [ ] **6.4 跑测试**:预期 9 个用例全 PASS,累计 29 passed。

---

### Task 7:`generate_contract_id()` 函数(ID 生成器)

#### 步骤

- [ ] **7.1 追加测试**:

```python
# ===================== generate_contract_id =====================

def test_generate_contract_id_format():
    cid = generate_contract_id()
    assert re.match(r"^cc_\d{8}_[0-9a-f]{6}$", cid), f"格式不符:{cid}"


def test_generate_contract_id_uniqueness():
    """连续 200 次生成应全部唯一(6 hex 约束下,碰撞概率 <1e-10)。"""
    ids = {generate_contract_id() for _ in range(200)}
    assert len(ids) == 200


def test_generate_contract_id_uses_shanghai_date():
    """日期段必须是 Shanghai 当日(不得被系统 tz 污染)。"""
    from datetime import datetime, timezone, timedelta
    expected_date = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
    cid = generate_contract_id()
    assert cid[3:11] == expected_date, f"日期段 {cid[3:11]} 不等于 Shanghai 当日 {expected_date}"
```

- [ ] **7.2 跑测试**:预期 FAIL。

- [ ] **7.3 追加实现**:

```python
# ===================== ID 生成器 =====================

def generate_contract_id() -> str:
    """生成 contract_id,格式 cc_YYYYMMDD_<6hex>,日期用 Shanghai 时区。"""
    date = datetime.now(SHANGHAI_TZ).strftime("%Y%m%d")
    suffix = secrets.token_hex(3)  # 3 bytes = 6 hex chars
    return f"cc_{date}_{suffix}"
```

- [ ] **7.4 跑测试**:预期 3 个用例 PASS,累计 32 passed。

---

### Task 8:`CreativeContract` 顶层 dataclass + 构造

#### 步骤

- [ ] **8.1 追加测试**:

```python
# ===================== CreativeContract 顶层 =====================

def _make_contract(**overrides):
    base = dict(
        contract_id=generate_contract_id(),
        chapter_ref="第3章",
        created_at="2026-04-19T12:00:00+08:00",
        negotiation_log=[
            NegotiationTurn(speaker="connoisseur", msg="建议 #1: 败者视角",
                            timestamp="2026-04-19T12:00:00+08:00"),
            NegotiationTurn(speaker="author", msg="采纳 #1",
                            timestamp="2026-04-19T12:05:00+08:00"),
        ],
        preserve_list=[_make_preserve_item()],
        rejected_list=[RejectedItem(item_id="#2", reason="12 一致性规则 #7 违规")],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph")
        ],
        iteration_count=0,
        max_iterations=3,
    )
    base.update(overrides)
    return CreativeContract(**base)


def test_contract_basic():
    c = _make_contract()
    c.validate()
    assert c.skipped_by_author is False  # 默认


def test_contract_default_fields():
    """检查 field default / default_factory 正确。"""
    c = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第1章",
        created_at="2026-04-19T00:00:00+08:00",
    )
    assert c.negotiation_log == []
    assert c.preserve_list == []
    assert c.rejected_list == []
    assert c.writer_assignments == []
    assert c.iteration_count == 0
    assert c.max_iterations == 3
    assert c.skipped_by_author is False


def test_contract_chapter_ref_non_empty():
    with pytest.raises(ContractValidationError, match="chapter_ref"):
        _make_contract(chapter_ref="").validate()
```

- [ ] **8.2 跑测试**:预期 FAIL。

- [ ] **8.3 追加实现**:

```python
# ===================== CreativeContract 顶层 =====================

@dataclass
class CreativeContract:
    """本章创意契约:阶段 5.5 产出,阶段 5.6 / 6 / 7 消费。"""
    contract_id: str
    chapter_ref: str
    created_at: str  # ISO 8601 (Shanghai tz)
    negotiation_log: List[NegotiationTurn] = field(default_factory=list)
    preserve_list: List[PreserveItem] = field(default_factory=list)
    rejected_list: List[RejectedItem] = field(default_factory=list)
    writer_assignments: List[WriterAssignment] = field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 3

    # Q1: 鉴赏师给出 0 条建议 + 作者确认跳过 阶段 5.5 → True
    # workflow (P2-1) 负责在条件满足时设 True;本字段仅供阶段 7 审计与日志
    skipped_by_author: bool = False

    def validate(self) -> None:
        """跨字段 + 级联校验。具体实现见 Task 9。"""
        raise NotImplementedError("Task 9 补完")
```

- [ ] **8.4 跑测试**:预期 `test_contract_basic` FAIL(validate 抛 NotImplementedError),其他 PASS。Task 9 补 validate 后全通过。**暂留此 FAIL 进入 Task 9**。

---

### Task 9:`CreativeContract.validate()` 跨字段校验

#### 步骤

- [ ] **9.1 追加测试**:

```python
def test_contract_validate_cascades_to_children():
    """子字段的校验错误必须上浮。"""
    with pytest.raises(ContractValidationError, match="preserve"):
        _make_contract(
            preserve_list=[_make_preserve_item(
                aspects=Aspects(preserve=[], drop=["台词"])
            )]
        ).validate()


def test_contract_rejects_bad_contract_id_format():
    with pytest.raises(ContractValidationError, match="contract_id"):
        _make_contract(contract_id="bad_id").validate()
    with pytest.raises(ContractValidationError, match="contract_id"):
        _make_contract(contract_id="cc_2026_abcdef").validate()
    with pytest.raises(ContractValidationError, match="contract_id"):
        _make_contract(contract_id="cc_20260419_XYZABC").validate()  # 非 hex


def test_contract_rejects_duplicate_preserve_item_ids():
    with pytest.raises(ContractValidationError, match="重复"):
        _make_contract(preserve_list=[
            _make_preserve_item(item_id="#1"),
            _make_preserve_item(item_id="#1"),
        ]).validate()


def test_contract_rejects_preserve_rejected_overlap():
    """同一 item_id 不可同时在 preserve 与 rejected 中。"""
    with pytest.raises(ContractValidationError, match="preserve.*rejected"):
        _make_contract(
            preserve_list=[_make_preserve_item(item_id="#1")],
            rejected_list=[RejectedItem(item_id="#1", reason="x")],
        ).validate()


def test_contract_writer_assignment_must_reference_existing_item():
    with pytest.raises(ContractValidationError, match="writer_assignments"):
        _make_contract(
            preserve_list=[_make_preserve_item(item_id="#1")],
            writer_assignments=[
                WriterAssignment(item_id="#99", writer="novelist-jianchen",
                                 task="rewrite_paragraph")
            ],
        ).validate()


def test_contract_iteration_count_bounds():
    with pytest.raises(ContractValidationError, match="iteration_count"):
        _make_contract(iteration_count=-1).validate()
    with pytest.raises(ContractValidationError, match="iteration_count"):
        _make_contract(iteration_count=5, max_iterations=3).validate()
    # 边界:iteration_count == max_iterations 允许(最后一轮)
    _make_contract(iteration_count=3, max_iterations=3).validate()


def test_contract_max_iterations_positive():
    with pytest.raises(ContractValidationError, match="max_iterations"):
        _make_contract(max_iterations=0).validate()
    with pytest.raises(ContractValidationError, match="max_iterations"):
        _make_contract(max_iterations=-1).validate()


def test_contract_skipped_by_author_requires_empty_lists():
    """Q1:skipped_by_author=True 意味着 0 条建议,三个列表都应为空。"""
    # True + 三空 → OK
    _make_contract(preserve_list=[], rejected_list=[], writer_assignments=[],
                   skipped_by_author=True).validate()
    # True + 非空 preserve → 语义矛盾
    with pytest.raises(ContractValidationError, match="skipped_by_author"):
        _make_contract(skipped_by_author=True).validate()
    # True + 非空 rejected → 语义矛盾
    with pytest.raises(ContractValidationError, match="skipped_by_author"):
        _make_contract(preserve_list=[], writer_assignments=[],
                       skipped_by_author=True).validate()
```

- [ ] **9.2 跑测试**:预期 8 个新测 + `test_contract_basic` 仍 FAIL。

- [ ] **9.3 替换 `CreativeContract.validate` 的 `NotImplementedError`**,用 Edit 工具把:

```python
    def validate(self) -> None:
        """跨字段 + 级联校验。具体实现见 Task 9。"""
        raise NotImplementedError("Task 9 补完")
```

替换为:

```python
    def validate(self) -> None:
        """跨字段 + 级联校验。"""
        if not _CONTRACT_ID_PATTERN.match(self.contract_id or ""):
            raise ContractValidationError(
                f"contract_id 必须匹配 /^cc_\\d{{8}}_[0-9a-f]{{6}}$/,实得 {self.contract_id!r}"
            )
        if not self.chapter_ref or not self.chapter_ref.strip():
            raise ContractValidationError("chapter_ref 必须非空")
        if not self.created_at or not self.created_at.strip():
            raise ContractValidationError("created_at 必须非空")
        if self.max_iterations <= 0:
            raise ContractValidationError(
                f"max_iterations 必须 > 0,实得 {self.max_iterations}"
            )
        if self.iteration_count < 0 or self.iteration_count > self.max_iterations:
            raise ContractValidationError(
                f"iteration_count ({self.iteration_count}) 必须在 "
                f"[0, max_iterations={self.max_iterations}] 区间"
            )

        # 级联
        for t in self.negotiation_log:
            t.validate()
        for p in self.preserve_list:
            p.validate()
        for r in self.rejected_list:
            r.validate()
        for w in self.writer_assignments:
            w.validate()

        # item_id 唯一 + 不与 rejected 重叠
        preserve_ids = [p.item_id for p in self.preserve_list]
        if len(preserve_ids) != len(set(preserve_ids)):
            dup = [i for i in set(preserve_ids) if preserve_ids.count(i) > 1]
            raise ContractValidationError(f"preserve_list 中 item_id 重复:{dup}")
        rejected_ids = {r.item_id for r in self.rejected_list}
        overlap = set(preserve_ids) & rejected_ids
        if overlap:
            raise ContractValidationError(
                f"item_id 同时出现在 preserve 与 rejected:{sorted(overlap)}"
            )

        # writer_assignments 必须引用 preserve_list 中的 item_id
        preserve_id_set = set(preserve_ids)
        for w in self.writer_assignments:
            if w.item_id not in preserve_id_set:
                raise ContractValidationError(
                    f"writer_assignments 引用了 preserve_list 中不存在的 "
                    f"item_id {w.item_id!r}"
                )

        # Q1:skipped_by_author=True 要求 preserve/rejected/writer_assignments 三者全空
        if self.skipped_by_author and (
            self.preserve_list or self.rejected_list or self.writer_assignments
        ):
            raise ContractValidationError(
                "skipped_by_author=True 要求 preserve_list / rejected_list / "
                "writer_assignments 三个列表全空(Q1:鉴赏师 0 条建议 + 作者确认跳过)"
            )
```

- [ ] **9.4 跑测试**:预期 Task 8+9 所有用例 PASS,累计 ~43 passed。

---

### Task 10:`to_json()` / `from_json()` 序列化 + 往返

#### 步骤

- [ ] **10.1 追加测试**:

```python
# ===================== 序列化 =====================

def test_contract_roundtrip_minimal():
    """空契约往返。"""
    c = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第1章",
        created_at="2026-04-19T00:00:00+08:00",
    )
    s = c.to_json()
    assert isinstance(s, str)
    c2 = CreativeContract.from_json(s)
    assert c2 == c


def test_contract_roundtrip_full():
    """含全部子结构的契约往返保持等价。"""
    c = _make_contract()
    s = c.to_json()
    parsed = json.loads(s)
    assert parsed["contract_id"] == c.contract_id
    assert parsed["preserve_list"][0]["aspects"]["preserve"] == ["情绪强度", "心理动机"]
    assert parsed["preserve_list"][0]["exempt_dimensions"][0]["sub_items"] == ["主角一致性"]
    c2 = CreativeContract.from_json(s)
    assert c2 == c


def test_contract_to_json_is_valid_json():
    c = _make_contract()
    s = c.to_json()
    json.loads(s)  # 不应抛


def test_contract_to_json_indent_optional():
    c = _make_contract()
    s2 = c.to_json(indent=2)
    assert "\n" in s2  # 含缩进
    assert json.loads(s2) == json.loads(c.to_json())


def test_contract_from_json_invalid_raises():
    with pytest.raises(ContractValidationError, match="JSON"):
        CreativeContract.from_json("not a json")
    with pytest.raises(ContractValidationError):
        CreativeContract.from_json('{"contract_id": "bad"}')  # 缺字段


def test_contract_from_json_validates():
    """from_json 必须跑 validate,拒绝损坏数据。"""
    c = _make_contract()
    raw = json.loads(c.to_json())
    raw["contract_id"] = "bad_id"
    bad = json.dumps(raw)
    with pytest.raises(ContractValidationError, match="contract_id"):
        CreativeContract.from_json(bad)


def test_contract_preserve_list_ascii_false():
    """中文字符必须能被 json 序列化并还原(ensure_ascii=False)。"""
    c = _make_contract()
    s = c.to_json()
    assert "情绪强度" in s  # 不应被转义成 \uXXXX
```

- [ ] **10.2 跑测试**:预期 FAIL。

- [ ] **10.3 追加实现**(加在 `CreativeContract` 类内,`validate` 之后):

```python
    def to_json(self, *, indent: Optional[int] = None) -> str:
        """序列化为 JSON 字符串,中文不转义。"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, s: str) -> "CreativeContract":
        """从 JSON 字符串反序列化并校验。"""
        try:
            raw = json.loads(s)
        except json.JSONDecodeError as e:
            raise ContractValidationError(f"输入不是合法 JSON: {e}") from e
        if not isinstance(raw, dict):
            raise ContractValidationError("JSON 顶层必须是对象")
        try:
            obj = cls(
                contract_id=raw["contract_id"],
                chapter_ref=raw["chapter_ref"],
                created_at=raw["created_at"],
                negotiation_log=[
                    NegotiationTurn(**t) for t in raw.get("negotiation_log", [])
                ],
                preserve_list=[
                    PreserveItem(
                        item_id=p["item_id"],
                        scope=Scope(**p["scope"]),
                        applied_constraint_id=p.get("applied_constraint_id"),
                        rationale=p["rationale"],
                        evaluator_risk=list(p.get("evaluator_risk", [])),
                        aspects=Aspects(
                            preserve=list(p["aspects"]["preserve"]),
                            drop=list(p["aspects"].get("drop", [])),
                        ),
                        exempt_dimensions=[
                            ExemptDimension(
                                dimension=ed["dimension"],
                                sub_items=list(ed["sub_items"]),
                            )
                            for ed in p.get("exempt_dimensions", [])
                        ],
                    )
                    for p in raw.get("preserve_list", [])
                ],
                rejected_list=[
                    RejectedItem(**r) for r in raw.get("rejected_list", [])
                ],
                writer_assignments=[
                    WriterAssignment(**w) for w in raw.get("writer_assignments", [])
                ],
                iteration_count=raw.get("iteration_count", 0),
                max_iterations=raw.get("max_iterations", 3),
                skipped_by_author=raw.get("skipped_by_author", False),
            )
        except KeyError as e:
            raise ContractValidationError(f"JSON 缺必需字段:{e}") from e
        except TypeError as e:
            raise ContractValidationError(f"JSON 字段类型不匹配:{e}") from e
        obj.validate()
        return obj
```

- [ ] **10.4 跑测试**:预期 7 个用例 PASS,累计 ~50 passed。

---

### Task 11:修改 `core/inspiration/__init__.py` 追加导出

#### 步骤

- [ ] **11.1 读当前文件**:`core/inspiration/__init__.py` 末尾已有 `__all__` 列表。

- [ ] **11.2 用 Edit 工具在**

```python
from core.inspiration.workflow_bridge import phase1_dispatch, _resolve_writer_skill
```

**那一行之后追加**:

```python
from core.inspiration.creative_contract import (
    Scope,
    Aspects,
    ExemptDimension,
    PreserveItem,
    RejectedItem,
    NegotiationTurn,
    WriterAssignment,
    CreativeContract,
    generate_contract_id,
    ContractValidationError,
)
```

- [ ] **11.3 用 Edit 工具在 `__all__` 列表末尾**(`]` 之前)**追加**:

```python
    "Scope",
    "Aspects",
    "ExemptDimension",
    "PreserveItem",
    "RejectedItem",
    "NegotiationTurn",
    "WriterAssignment",
    "CreativeContract",
    "generate_contract_id",
    "ContractValidationError",
```

- [ ] **11.4 冒烟验证**:

```bash
cd "D:/动画/众生界"
python -c "from core.inspiration import CreativeContract, generate_contract_id; print(generate_contract_id())"
```

预期:打印一行形如 `cc_20260419_abcdef`。

---

### Task 12:边界用例 + 冒烟集成测试

- [ ] **12.1 追加综合冒烟测试**(到 `tests/test_creative_contract.py` 末尾):

```python
# ===================== 冒烟集成 =====================

def test_end_to_end_contract_creation():
    """全流程冒烟:构造 → 校验 → JSON 往返 → 校验。"""
    c = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第3章",
        created_at="2026-04-19T12:00:00+08:00",
        negotiation_log=[
            NegotiationTurn(speaker="connoisseur",
                            msg="建议 #1:第3段改败者视角",
                            timestamp="2026-04-19T12:00:00+08:00"),
            NegotiationTurn(speaker="evaluator",
                            msg="#1 风险:主角视角连贯性 -0.1",
                            timestamp="2026-04-19T12:02:00+08:00"),
            NegotiationTurn(speaker="author",
                            msg="采纳 #1,驳回 #2",
                            timestamp="2026-04-19T12:05:00+08:00"),
        ],
        preserve_list=[
            PreserveItem(
                item_id="#1",
                scope=Scope(paragraph_index=3, char_start=234, char_end=567),
                applied_constraint_id="ANTI_001",
                rationale="鉴赏师 + 作者共识:败者视角 +3 爽快累计 7 条",
                evaluator_risk=["主角视角连贯性 -0.1"],
                aspects=Aspects(
                    preserve=["情绪强度", "心理动机"],
                    drop=["具体台词", "肢体表现"],
                ),
                exempt_dimensions=[
                    ExemptDimension(dimension="视角连贯性",
                                    sub_items=["主角一致性"]),
                ],
            ),
        ],
        rejected_list=[
            RejectedItem(item_id="#2", reason="评估师标 12 一致性规则#7 违规")
        ],
        writer_assignments=[
            WriterAssignment(item_id="#1",
                             writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
        iteration_count=0,
        max_iterations=3,
    )
    c.validate()
    s = c.to_json(indent=2)
    c2 = CreativeContract.from_json(s)
    assert c2 == c


def test_skipped_by_author_flow():
    """Q1:鉴赏师 0 条 → 作者确认跳过 → 空契约 skipped=True。"""
    c = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第5章",
        created_at="2026-04-19T13:00:00+08:00",
        skipped_by_author=True,
    )
    c.validate()
    c2 = CreativeContract.from_json(c.to_json())
    assert c2.skipped_by_author is True
    assert c2.preserve_list == []


def test_public_api_via_package_import():
    """通过 core.inspiration 顶层导入应可达全部公开符号。"""
    from core import inspiration as insp
    for name in ("Scope", "Aspects", "ExemptDimension", "PreserveItem",
                 "RejectedItem", "NegotiationTurn", "WriterAssignment",
                 "CreativeContract", "generate_contract_id",
                 "ContractValidationError"):
        assert hasattr(insp, name), f"{name} 未从 core.inspiration 导出"
```

- [ ] **12.2 跑**:`python -m pytest tests/test_creative_contract.py -v`。预期全 PASS,计数 ≥ 25 个用例。

---

### Task 13:全量 pytest + 回归

#### 步骤

- [ ] **13.1 跑全量**:

```bash
cd "D:/动画/众生界"
python -m pytest tests/ -v --tb=short 2>&1 | tee docs/m7_artifacts/p1-1_test_log_20260419.txt | tail -30
```

- [ ] **13.2 最后一行应形如**:

```
=== 492 passed, 1 skipped, 2 warnings in XX.XXs ===
```

(467 基线 + 本计划新增 ≥ 25 用例 ≈ 492+)

- [ ] **13.3 若出现 failed,不得继续,立即停止报告。**

---

## 4. 文件最终结构

`core/inspiration/creative_contract.py` 完成后应大致是:

```
"""模块 docstring"""
from __future__ import annotations
# imports
__all__ = [...]
SHANGHAI_TZ = ...
_CONTRACT_ID_PATTERN = ...

class ContractValidationError(ValueError): ...

# ===================== Scope =====================
@dataclass class Scope ...

# ===================== Aspects =====================
@dataclass class Aspects ...

# ===================== ExemptDimension =====================
@dataclass class ExemptDimension ...

# ===================== PreserveItem =====================
_ITEM_ID_PATTERN = ...
@dataclass class PreserveItem ...

# ===================== RejectedItem =====================
@dataclass class RejectedItem ...

# ===================== NegotiationTurn =====================
_VALID_SPEAKERS = (...)
@dataclass class NegotiationTurn ...

# ===================== WriterAssignment =====================
_VALID_WRITERS = (...)
@dataclass class WriterAssignment ...

# ===================== ID 生成器 =====================
def generate_contract_id() -> str: ...

# ===================== CreativeContract 顶层 =====================
@dataclass class CreativeContract
    # 字段 + validate + to_json + from_json
```

---

## 5. 自检命令(§3 全部完成后跑)

```bash
cd "D:/动画/众生界"

echo "===== P1-1 自检开始 ====="

# 文件存在
test -f core/inspiration/creative_contract.py && echo "PASS-F1 实现文件" || echo "FAIL-F1"
test -f tests/test_creative_contract.py && echo "PASS-F2 测试文件" || echo "FAIL-F2"

# Python 语法
python -c "import ast; ast.parse(open('core/inspiration/creative_contract.py', encoding='utf-8').read())" \
  && echo "PASS-S1 impl 语法 OK" || echo "FAIL-S1"
python -c "import ast; ast.parse(open('tests/test_creative_contract.py', encoding='utf-8').read())" \
  && echo "PASS-S2 test 语法 OK" || echo "FAIL-S2"

# 无第三方依赖(不允许出现 import pydantic / attrs / marshmallow)
if grep -qE "^(from|import) (pydantic|attrs|marshmallow)" core/inspiration/creative_contract.py; then
  echo "FAIL-D1 引入了禁用的第三方依赖"
else
  echo "PASS-D1 stdlib-only"
fi

# 包导出
python -c "from core.inspiration import CreativeContract, generate_contract_id, ContractValidationError, Scope, Aspects, ExemptDimension, PreserveItem, RejectedItem, NegotiationTurn, WriterAssignment; print('imports OK')" \
  && echo "PASS-E1 包导出齐全" || echo "FAIL-E1"

# 模块测试
python -m pytest tests/test_creative_contract.py -v 2>&1 | tail -5
count=$(python -m pytest tests/test_creative_contract.py --collect-only -q 2>&1 | grep -c "::test_")
[ "$count" -ge 25 ] && echo "PASS-T1 测试用例 $count 个 (≥25)" || echo "FAIL-T1 仅 $count 个"

python -m pytest tests/test_creative_contract.py 2>&1 | tail -2 | head -1
python -m pytest tests/test_creative_contract.py --tb=no -q 2>&1 | tail -1 | grep -E "passed.*failed|failed" && echo "FAIL-T2 有 failed" || echo "PASS-T2 模块测试全通过"

# 决策字段核验(Q1-Q4)
grep -q "skipped_by_author" core/inspiration/creative_contract.py && echo "PASS-Q1 Q1 字段存在" || echo "FAIL-Q1"
grep -q "class Aspects" core/inspiration/creative_contract.py && echo "PASS-Q2 Q2 嵌套 Aspects 存在" || echo "FAIL-Q2"
# Q3 反向:不得出现权重回流字段
if grep -qE "(retrieval_weight|weight_feedback|connoisseur_bias)" core/inspiration/creative_contract.py; then
  echo "FAIL-Q3 出现了权重回流字段"
else
  echo "PASS-Q3 无权重回流字段"
fi
grep -q "class ExemptDimension" core/inspiration/creative_contract.py && echo "PASS-Q4 Q4 子项豁免存在" || echo "FAIL-Q4"

# 保护性:其他 inspiration 模块未动
for f in appraisal_agent.py constraint_library.py memory_point_sync.py structural_analyzer.py variant_generator.py workflow_bridge.py; do
  status=$(git status --short "core/inspiration/$f" | head -1)
  if [ -z "$status" ]; then
    echo "PASS-P $f 未动"
  else
    echo "FAIL-P $f 被改动: $status"
  fi
done

# 全量回归
python -m pytest tests/ --tb=no -q 2>&1 | tail -1 | tee /tmp/p1-1_summary.txt
grep -qE "^[0-9]+ passed.*[0-9]+ skipped" /tmp/p1-1_summary.txt && echo "PASS-R1 全量跑通" || echo "FAIL-R1 全量异常"

# git HEAD 未 commit
hash=$(git log -1 --format=%h)
echo "HEAD=$hash (P1-1 不得 commit)"

echo "===== P1-1 自检结束 ====="
```

任一 `FAIL-` → **立即停止,不得声称完成**,报告给 Claude。

---

## 6. 完成判据

- [x] 13 个 Task 全部按 TDD 顺序完成
- [x] `tests/test_creative_contract.py` ≥ 25 个用例全 PASS
- [x] 全量 pytest:基线 467 + 新增 N (≥25) 全 passed,0 failed
- [x] §5 所有 `PASS-` 标记,无 `FAIL-`
- [x] `core/inspiration/` 其他 `.py` 文件无改动
- [x] 无第三方依赖
- [x] 无 git commit
- [x] Q1-Q4 四决策字段全部体现(skipped_by_author / Aspects / 无权重回流 / ExemptDimension)

---

## 7. 完成后更新 ROADMAP(仅在 §5 全 PASS 后才能改)

1. ROADMAP §3.2 P1-1 行:状态改 ✅,备注 "tests/test_creative_contract.py N 个用例全 PASS,全量 pytest X passed"
2. §5 时间线追加一行:

```
| 2026-04-19 | opencode | P1-1 创意契约数据模型完成 | core/inspiration/creative_contract.py + tests/test_creative_contract.py (≥25 用例全 PASS),全量 pytest 492+ passed |
```

3. §3 "★ 当前任务指针" 改:**P1-2 派单器(dispatcher.py)启动**

---

## 8. 下一步

- Claude 核验 §5 自检(不信 opencode "完成"声明,原样跑完全部 PASS 检查)
- 核验全 PASS → Claude 写 `docs/计划_P1-2_dispatcher_20260419.md`
- 任一 FAIL → Claude 报告作者,不改 ROADMAP ✅

---

**计划结束。opencode 按 Task 1 → Task 13 顺序 TDD 执行,§5 自检,§6 判据,§7 ROADMAP 更新。三部分全必做,自检任一 FAIL 不得改 ✅。**
