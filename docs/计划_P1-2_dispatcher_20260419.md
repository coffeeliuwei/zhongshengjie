# 计划 P1-2:派单器(dispatcher.py)

- **创建时间**:2026-04-19 (Asia/Shanghai)
- **执行者**:opencode (GLM5)
- **路线图位置**:[ROADMAP_众生界v2实施_20260419.md](./ROADMAP_众生界v2实施_20260419.md) §3.2 P1-2
- **依据设计**:[2026-04-19-inspiration-engine-design-v2.md](./superpowers/specs/2026-04-19-inspiration-engine-design-v2.md) §1 阶段 5.6 + §3 组件命运表 + §5 写手 prompt 增量
- **上游依赖**:P1-1 创意契约数据模型(`core/inspiration/creative_contract.py`)已完成
- **前置决策**:Q1-Q4 作者已表态,P1-1 已代码化贯彻。本计划仍须贯彻 Q1 / Q2(见 §0.3)
- **Python**:3.12.7(stdlib-only,不得引入 jinja2 / pydantic / attrs 等第三方库)
- **Shell**:bash

---

## 0. 本计划的目的 — 必读

P1-2 只做**派单器纯函数层**:读一份已校验的 `CreativeContract`,把 `writer_assignments` 按写手分组,为每位写手渲染 v2 §5 "创意契约约束" prompt 增量,产出 `List[DispatchPackage]`。

**本阶段不碰** workflow.py / skill 文件 / 实际的写手 LLM 调用 / Qdrant。派单器只产数据结构,**不执行**写手。执行动作由 P2-2 在 workflow 层完成。

### 0.1 范围边界(不得扩张)

- ✅ 新建 `core/inspiration/dispatcher.py`(单文件,stdlib-only)
- ✅ 新建 `tests/test_dispatcher.py`
- ✅ 修改 `core/inspiration/__init__.py`(仅追加 import + `__all__` 条目,不改已有行)
- ❌ 不动 `creative_contract.py`、`appraisal_agent.py`、`workflow_bridge.py`、`constraint_library.py` 等任何已有模块
- ❌ 不动 `workflow.py`
- ❌ 不动任何 SKILL.md
- ❌ 不动 `.archived/` / `.vectorstore/`
- ❌ 不引入第三方依赖(jinja2 / pydantic / attrs / marshmallow 等禁用)
- ❌ 不在 dispatcher 内直接调用写手 / 不做 LLM 调用 / 不做 I/O
- ❌ 不 git commit(除非 §5 自检全 PASS 且作者授权)

### 0.2 产出清单

| 文件 | 类型 | 验收 |
|------|------|------|
| `core/inspiration/dispatcher.py` | 新建 | 单文件,stdlib-only,pytest 本模块全 PASS |
| `tests/test_dispatcher.py` | 新建 | ≥ 20 个测试用例,覆盖分组 / 渲染 / 空/边界 / Q1 跳过 / Q2 嵌套 |
| `core/inspiration/__init__.py` | 修改 | 追加 3 个导出符号(`DispatchPackage` / `dispatch` / `DispatcherError`) |

### 0.3 Q1-Q4 在 P1-2 中的体现

| # | 决策 | 在 dispatcher 中的体现 |
|---|------|----------------------|
| Q1 | 鉴赏师 0 条建议时作者确认跳过 | `dispatch(contract)` 若 `contract.skipped_by_author=True` → 返回 `[]`(空列表,无派单) |
| Q2 | `preserve_list` 嵌套 aspects(preserve/drop) | prompt 增量必须分段渲染【必须保留】与【可放开】两块;drop 为空时改为"仅可优化字词/语流" |
| Q3 | `author_force_pass` 不回流权重 | dispatcher 与权重回流**无关**,自然贯彻 |
| Q4 | 评估师豁免按子项 | 豁免由 P1-7 评估师实现,dispatcher 只需**透传**(prompt 增量可提示"本项涉及豁免维度:X",便于写手理解约束,但**不改变豁免决策**) |

---

## 1. 执行前真实状态

### 1.1 目录

```
core/inspiration/
├── __init__.py                   [将修改:追加 3 个导出]
├── appraisal_agent.py            [不动]
├── audit_trigger.py              [不动]
├── constraint_library.py         [不动]
├── creative_contract.py          [上游,不动,只 import]
├── embedder.py                   [不动]
├── escalation_dialogue.py        [不动]
├── memory_point_sync.py          [不动]
├── resonance_feedback.py         [不动]
├── segment_locator.py            [不动]
├── status_reporter.py            [不动]
├── structural_analyzer.py        [不动]
├── variant_generator.py          [不动]
├── workflow_bridge.py            [不动]
└── dispatcher.py                 [将新建]

tests/
├── (已有 48 个测试文件,均不动)
└── test_dispatcher.py            [将新建]
```

### 1.2 pytest 基线

**基线**:P1-1 完成后 **506 passed / 1 skipped / 2 warnings**。

P1-2 完成后应为 **506 + N passed**(N = 新增测试数,≥ 20)。

### 1.3 上游 API 锚点(dispatcher 将 import 的符号)

来自 `core.inspiration.creative_contract`:

```python
from core.inspiration.creative_contract import (
    CreativeContract,       # 顶层契约
    PreserveItem,           # preserve_list[i]
    WriterAssignment,       # writer_assignments[i]
    ContractValidationError # dispatcher 校验失败时复用
)
```

上游已校验规则(dispatcher 可假设的不变量 — 由 `CreativeContract.validate()` 保证):
- `preserve_list` 中 `item_id` 唯一且不与 `rejected_list` 重叠
- 每个 `WriterAssignment.item_id` 必存在于 `preserve_list` 中
- `WriterAssignment.writer` 必在 5 写手白名单(novelist-jianchen / -canglan / -moyan / -xuanyi / -yunxi)
- `skipped_by_author=True` ⟹ `preserve_list / rejected_list / writer_assignments` 三者全空

**dispatcher 仍在入口显式调用 `contract.validate()`**,避免调用方忘记校验直接递交损坏契约。

---

## 2. opencode 执行规则(不可违反)

### 2.1 允许的操作

1. Write 工具新建 2 个文件(§3.Task 1 + §3.Task 12 之前均在一个测试文件里追加)
2. Edit 工具修改 `core/inspiration/__init__.py`(仅在既有 `from core.inspiration.creative_contract import (...)` 块之后追加一行 import,以及在 `__all__` 列表末追加 3 个条目)
3. 按 §3 任务顺序,每任务内部按"写测试 → 跑测试见 FAIL → 写实现 → 跑测试见 PASS"执行(TDD)
4. 跑 §5 自检

### 2.2 禁止的操作

- ❌ 不引入第三方库(只能 stdlib)
- ❌ 不改 `core/inspiration/` 下任何已有 `.py` 文件(`__init__.py` 仅追加,不删不改)
- ❌ 不改 `creative_contract.py`(若测试暴露出上游 bug,**停止并报告 Claude**,不得擅自修改 P1-1 产出)
- ❌ 不改 SKILL.md
- ❌ 不 git commit
- ❌ 不跳步 — §3 Task 1-14 必须全做
- ❌ dispatcher 不得做任何 I/O:不 open 文件、不调 LLM、不查 Qdrant;纯函数

### 2.3 TDD 严格执行

**每个 Task 内部按 "先写测试 → 跑测试见 FAIL → 写实现 → 跑测试见 PASS" 五步走,中间任一步失败立即停止并报告,不得跳到下个 Task。**

---

## 3. 执行步骤(按 Task 1 → Task 14 顺序)

### Task 1:创建 `dispatcher.py` 骨架 + 模块 docstring + 测试骨架

**文件**:
- 新建:`core/inspiration/dispatcher.py`
- 新建:`tests/test_dispatcher.py`

#### 步骤

- [ ] **1.1 用 Write 工具新建 `core/inspiration/dispatcher.py`**,完整内容:

```python
"""派单器(Dispatcher)— v2 阶段 5.6 核心纯函数层。

输入:一份已校验的 CreativeContract
输出:List[DispatchPackage],每个包含某一位写手需要承接的全部 item_ids、
      任务列表、对应的 PreserveItem 引用、以及渲染好的
      【创意契约约束】prompt 增量(v2 §5 模板)。

dispatcher 不做 I/O、不调 LLM、不查 Qdrant。
真正的写手调用由 workflow(P2-2)接收本层输出后实施。

设计文档:docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md §1 阶段 5.6 + §5
实施计划:docs/计划_P1-2_dispatcher_20260419.md

【关键决策贯彻】
- Q1 skipped_by_author=True → dispatch 返回空列表
- Q2 嵌套 aspects → prompt 分块渲染【必须保留】与【可放开】;drop 为空时降级为"仅优化字词/语流"
- Q3 不回流权重 → 本模块与权重无关,自然贯彻
- Q4 豁免按子项 → prompt 中透传 exempt_dimensions 提示,但不改变豁免决策(由 P1-7 评估师执行)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from core.inspiration.creative_contract import (
    CreativeContract,
    ContractValidationError,
    PreserveItem,
    WriterAssignment,
)

__all__ = [
    "DispatchPackage",
    "dispatch",
    "DispatcherError",
]


class DispatcherError(ContractValidationError):
    """派单器特有的错误(复用 ContractValidationError 的 ValueError 血统)。

    目前用于:dispatch 在入口发现契约字段被调用方伪造绕过 validate 时抛出。
    """
```

- [ ] **1.2 用 Write 工具新建 `tests/test_dispatcher.py`**,完整内容:

```python
"""core/inspiration/dispatcher.py 的单元测试。

覆盖:
- dispatch 对 skipped_by_author=True / 空 writer_assignments / 正常多写手派单的处理
- DispatchPackage 字段 / 校验
- prompt 增量:v2 §5 模板、Q2 嵌套 aspects 分块、drop 空降级、多 item 拼接、
  evaluator_risk 透传、exempt_dimensions 透传
- 保持 WriterAssignment 原始顺序(同一写手多 item 的 task 顺序稳定)
- 在契约未经 validate 时 dispatch 内部仍会 validate(不信任调用方)

依据计划:docs/计划_P1-2_dispatcher_20260419.md
"""
from __future__ import annotations

import pytest

from core.inspiration.creative_contract import (
    Aspects,
    CreativeContract,
    ContractValidationError,
    ExemptDimension,
    NegotiationTurn,
    PreserveItem,
    RejectedItem,
    Scope,
    WriterAssignment,
    generate_contract_id,
)
from core.inspiration.dispatcher import (
    DispatchPackage,
    DispatcherError,
    dispatch,
)


def test_module_importable():
    """冒烟:模块可导入,所有 __all__ 符号已定义。"""
    from core.inspiration import dispatcher as d
    for name in d.__all__:
        assert hasattr(d, name), f"{name} 不在模块中"
```

- [ ] **1.3 跑测试验证骨架**:

```bash
cd "D:/动画/众生界"
python -m pytest tests/test_dispatcher.py -v
```

预期:`test_module_importable` PASS(共 1 passed)。

---

### Task 2:`DispatchPackage` dataclass(派单包)

#### 步骤

- [ ] **2.1 追加测试**(`tests/test_dispatcher.py` 末尾):

```python
# ===================== DispatchPackage =====================


def _make_preserve_item(**overrides) -> PreserveItem:
    base = dict(
        item_id="#1",
        scope=Scope(paragraph_index=3, char_start=234, char_end=567),
        applied_constraint_id="ANTI_001",
        rationale="鉴赏师 + 作者共识:败者视角 +3 爽快累计 7 条",
        evaluator_risk=["主角视角连贯性 -0.1"],
        aspects=Aspects(preserve=["情绪强度", "心理动机"], drop=["具体台词"]),
        exempt_dimensions=[
            ExemptDimension(dimension="视角连贯性", sub_items=["主角一致性"]),
        ],
    )
    base.update(overrides)
    return PreserveItem(**base)


def test_dispatch_package_basic():
    p = DispatchPackage(
        contract_id="cc_20260419_abcdef",
        writer="novelist-jianchen",
        item_ids=["#1"],
        tasks=["rewrite_paragraph"],
        preserve_items=[_make_preserve_item()],
        prompt_increment="【创意契约约束】...",
    )
    p.validate()
    assert p.writer == "novelist-jianchen"
    assert p.item_ids == ["#1"]


def test_dispatch_package_item_ids_tasks_parallel():
    """item_ids 与 tasks 必须同长。"""
    with pytest.raises(DispatcherError, match="item_ids.*tasks"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            item_ids=["#1", "#2"],
            tasks=["rewrite_paragraph"],
            preserve_items=[_make_preserve_item()],
            prompt_increment="x",
        ).validate()


def test_dispatch_package_rejects_empty_writer():
    with pytest.raises(DispatcherError, match="writer"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="",
            item_ids=["#1"],
            tasks=["rewrite_paragraph"],
            preserve_items=[_make_preserve_item()],
            prompt_increment="x",
        ).validate()


def test_dispatch_package_rejects_empty_item_ids():
    with pytest.raises(DispatcherError, match="item_ids"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            item_ids=[],
            tasks=[],
            preserve_items=[],
            prompt_increment="x",
        ).validate()


def test_dispatch_package_rejects_empty_prompt_increment():
    with pytest.raises(DispatcherError, match="prompt_increment"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            item_ids=["#1"],
            tasks=["rewrite_paragraph"],
            preserve_items=[_make_preserve_item()],
            prompt_increment="",
        ).validate()


def test_dispatch_package_preserve_items_cardinality():
    """preserve_items 数量必须等于 item_ids 数量(且 item_id 一一对应)。"""
    p1 = _make_preserve_item(item_id="#1")
    p2 = _make_preserve_item(item_id="#2")
    with pytest.raises(DispatcherError, match="preserve_items"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            item_ids=["#1", "#2"],
            tasks=["t1", "t2"],
            preserve_items=[p1],  # 少一个
            prompt_increment="x",
        ).validate()
    # id 对应不上
    with pytest.raises(DispatcherError, match="preserve_items"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            item_ids=["#1", "#2"],
            tasks=["t1", "t2"],
            preserve_items=[p1, _make_preserve_item(item_id="#3")],
            prompt_increment="x",
        ).validate()
```

- [ ] **2.2 跑测试**:`python -m pytest tests/test_dispatcher.py -v`。
  预期:6 个新用例全 FAIL(`DispatchPackage` 未定义),`test_module_importable` 仍 PASS。

- [ ] **2.3 追加实现**(到 `core/inspiration/dispatcher.py` 末尾):

```python
# ===================== DispatchPackage =====================


@dataclass
class DispatchPackage:
    """某位写手在本次契约中的派单包。

    一个 DispatchPackage 对应 一位写手 × 本契约的 1..N 条 writer_assignments。
    workflow(P2-2)消费本包时:
      - 用 writer 作为目标 skill 名
      - 把 prompt_increment 追加到该写手的标准 prompt 尾部
      - tasks[i] / preserve_items[i] / item_ids[i] 三列表并行,表示第 i 条任务
    """

    contract_id: str
    writer: str                               # novelist-xxx 全名
    item_ids: List[str]                       # 顺序 = WriterAssignment 在契约中的出现顺序
    tasks: List[str]                          # 与 item_ids 并行
    preserve_items: List[PreserveItem]        # 与 item_ids 并行,同 item_id
    prompt_increment: str                     # 渲染好的【创意契约约束】整块 Chinese prompt

    def validate(self) -> None:
        if not self.contract_id or not self.contract_id.strip():
            raise DispatcherError("DispatchPackage.contract_id 必须非空")
        if not self.writer or not self.writer.strip():
            raise DispatcherError("DispatchPackage.writer 必须非空")
        if not self.item_ids:
            raise DispatcherError(
                "DispatchPackage.item_ids 必须非空(无任务的写手不应产出派单包)"
            )
        if len(self.item_ids) != len(self.tasks):
            raise DispatcherError(
                f"DispatchPackage.item_ids 与 tasks 长度必须一致,"
                f"实得 {len(self.item_ids)} vs {len(self.tasks)}"
            )
        if len(self.item_ids) != len(self.preserve_items):
            raise DispatcherError(
                f"DispatchPackage.preserve_items 长度必须等于 item_ids,"
                f"实得 {len(self.preserve_items)} vs {len(self.item_ids)}"
            )
        for i, (iid, pi) in enumerate(zip(self.item_ids, self.preserve_items)):
            if pi.item_id != iid:
                raise DispatcherError(
                    f"DispatchPackage.preserve_items[{i}].item_id "
                    f"({pi.item_id!r}) 不等于 item_ids[{i}] ({iid!r})"
                )
        if not self.prompt_increment or not self.prompt_increment.strip():
            raise DispatcherError("DispatchPackage.prompt_increment 必须非空")
```

- [ ] **2.4 跑测试**:预期 6 个 `test_dispatch_package_*` 全 PASS,累计 7 passed。

---

### Task 3:单项 preserve_item 渲染(`_format_preserve_block`)

派单 prompt 的核心渲染单元。每条 `PreserveItem` 渲染成一块 Chinese 区域,内含 scope / rationale / 风险提示 / Q2 嵌套 aspects / 豁免透传。

#### 步骤

- [ ] **3.1 追加测试**:

```python
# ===================== _format_preserve_block =====================


def _get_block(*, aspects=None, exempt_dimensions=None, evaluator_risk=None,
               task="rewrite_paragraph"):
    """构造一个 block + 调用内部渲染函数的便捷封装。"""
    from core.inspiration.dispatcher import _format_preserve_block
    p = _make_preserve_item(
        aspects=aspects or Aspects(preserve=["情绪强度", "心理动机"],
                                   drop=["具体台词"]),
        exempt_dimensions=exempt_dimensions if exempt_dimensions is not None else [
            ExemptDimension(dimension="视角连贯性", sub_items=["主角一致性"]),
        ],
        evaluator_risk=evaluator_risk if evaluator_risk is not None else ["主角视角连贯性 -0.1"],
    )
    return _format_preserve_block(preserve_item=p, task=task)


def test_format_preserve_block_contains_scope():
    text = _get_block()
    assert "第 3 段" in text
    assert "[234, 567)" in text or "234" in text and "567" in text


def test_format_preserve_block_contains_item_id_and_constraint():
    text = _get_block()
    assert "#1" in text
    assert "ANTI_001" in text


def test_format_preserve_block_contains_rationale():
    text = _get_block()
    assert "鉴赏师 + 作者共识" in text


def test_format_preserve_block_q2_renders_preserve_and_drop():
    """Q2:preserve 与 drop 必须分段出现。"""
    text = _get_block()
    assert "【必须保留】" in text
    assert "情绪强度" in text
    assert "心理动机" in text
    assert "【可放开】" in text
    assert "具体台词" in text


def test_format_preserve_block_q2_drop_empty_degrades():
    """drop 为空时,改为"仅可优化字词/语流"提示,不输出空的【可放开】块。"""
    text = _get_block(aspects=Aspects(preserve=["情绪强度"], drop=[]))
    assert "【必须保留】" in text
    assert "情绪强度" in text
    # 不应出现空块
    assert "【可放开】:\n  -" not in text
    # 应出现降级提示
    assert "仅可优化字词" in text or "仅优化字词" in text


def test_format_preserve_block_evaluator_risk_listed():
    text = _get_block(evaluator_risk=["主角视角连贯性 -0.1", "节奏打断风险"])
    assert "评估师风险" in text
    assert "主角视角连贯性 -0.1" in text
    assert "节奏打断风险" in text


def test_format_preserve_block_evaluator_risk_empty_section_absent():
    """evaluator_risk 为空时不渲染该段落,避免空表格。"""
    text = _get_block(evaluator_risk=[])
    assert "评估师风险" not in text


def test_format_preserve_block_exempt_dimensions_transparent():
    """Q4:豁免按子项透传到 prompt,便于写手知晓约束边界。"""
    text = _get_block(exempt_dimensions=[
        ExemptDimension(dimension="视角连贯性", sub_items=["主角一致性", "叙述人称一致性"]),
    ])
    assert "涉及豁免维度" in text or "豁免维度" in text
    assert "视角连贯性" in text
    assert "主角一致性" in text
    assert "叙述人称一致性" in text


def test_format_preserve_block_exempt_dimensions_empty_section_absent():
    text = _get_block(exempt_dimensions=[])
    assert "豁免维度" not in text


def test_format_preserve_block_applied_constraint_none():
    """applied_constraint_id 可为 None(非约束库触发)。"""
    from core.inspiration.dispatcher import _format_preserve_block
    p = _make_preserve_item(applied_constraint_id=None)
    text = _format_preserve_block(preserve_item=p, task="rewrite_paragraph")
    assert "ANTI_001" not in text
    assert "非约束库" in text or "无(" in text or "无约束" in text


def test_format_preserve_block_contains_task():
    text = _get_block(task="整章再润色,不得修改 preserve 区域")
    assert "整章再润色" in text
```

- [ ] **3.2 跑测试**:预期 11 个新用例全 FAIL(`_format_preserve_block` 未定义)。

- [ ] **3.3 追加实现**(到 `core/inspiration/dispatcher.py` 末尾):

```python
# ===================== prompt 模板 =====================

_BLOCK_SEPARATOR = "───────────── 项目 {item_id} ─────────────"
_BLOCK_CLOSER = "─────────────────────────────────────"


def _format_preserve_block(*, preserve_item: PreserveItem, task: str) -> str:
    """为单条 PreserveItem 渲染 v2 §5 模板中"项目"块(Chinese,Q2 嵌套)。"""
    p = preserve_item
    lines: List[str] = []
    lines.append(_BLOCK_SEPARATOR.format(item_id=p.item_id))
    lines.append(
        f"区域:第 {p.scope.paragraph_index} 段,"
        f"字符 [{p.scope.char_start}, {p.scope.char_end})"
    )
    if p.applied_constraint_id:
        lines.append(f"应用约束:{p.applied_constraint_id}")
    else:
        lines.append("应用约束:无(非约束库触发)")
    lines.append(f"采纳理由:{p.rationale}")

    # evaluator_risk(可选)
    if p.evaluator_risk:
        lines.append("评估师风险提示:")
        for risk in p.evaluator_risk:
            lines.append(f"  - {risk}")

    # Q2 嵌套 aspects
    lines.append("【必须保留】(preserve):")
    for s in p.aspects.preserve:
        lines.append(f"  - {s}")
    if p.aspects.drop:
        lines.append("【可放开】(drop,可在此范围内优化):")
        for s in p.aspects.drop:
            lines.append(f"  - {s}")
    else:
        lines.append("【可放开】:(无)— 仅可优化字词/语流,不改任何子面")

    # Q4 豁免透传(可选)
    if p.exempt_dimensions:
        lines.append("涉及豁免维度(评估师将跳过以下子项打分):")
        for ed in p.exempt_dimensions:
            subs = " / ".join(ed.sub_items)
            lines.append(f"  - {ed.dimension}:{subs}")

    lines.append(f"任务指令:{task}")
    lines.append(_BLOCK_CLOSER)
    return "\n".join(lines)
```

- [ ] **3.4 跑测试**:预期 11 个用例全 PASS,累计 18 passed。

---

### Task 4:单写手增量 prompt 构造(`_build_prompt_increment`)

把一位写手承接的全部 `(PreserveItem, task)` 对,拼成一整块【创意契约约束】prompt(开头说明 + N 个项目块 + 末尾守则)。

#### 步骤

- [ ] **4.1 追加测试**:

```python
# ===================== _build_prompt_increment =====================


def test_build_prompt_increment_header_and_footer():
    from core.inspiration.dispatcher import _build_prompt_increment
    p = _make_preserve_item(item_id="#1")
    text = _build_prompt_increment(
        contract_id="cc_20260419_abcdef",
        writer="novelist-jianchen",
        pairs=[(p, "rewrite_paragraph")],
    )
    assert "【创意契约约束】" in text
    assert "cc_20260419_abcdef" in text
    assert "novelist-jianchen" in text
    # 守则尾部
    assert "重写守则" in text
    assert "区域外保持原文" in text or "区域外正常修改" in text or "区域外可" in text


def test_build_prompt_increment_concatenates_multiple_items():
    """一位写手承接多 item 时,prompt 中出现多个"项目"块。"""
    from core.inspiration.dispatcher import _build_prompt_increment
    p1 = _make_preserve_item(item_id="#1")
    p3 = _make_preserve_item(
        item_id="#3",
        scope=Scope(paragraph_index=5, char_start=10, char_end=99),
    )
    text = _build_prompt_increment(
        contract_id="cc_20260419_abcdef",
        writer="novelist-jianchen",
        pairs=[(p1, "rewrite_paragraph"), (p3, "tighten_rhythm")],
    )
    # 两个项目都出现
    assert "项目 #1" in text
    assert "项目 #3" in text
    # 第 5 段信息来自 #3
    assert "第 5 段" in text


def test_build_prompt_increment_preserves_pair_order():
    """pairs 顺序 = 项目块顺序。"""
    from core.inspiration.dispatcher import _build_prompt_increment
    p1 = _make_preserve_item(item_id="#1")
    p2 = _make_preserve_item(
        item_id="#2",
        scope=Scope(paragraph_index=7, char_start=0, char_end=10),
    )
    text_a = _build_prompt_increment(
        contract_id="cc_20260419_abcdef",
        writer="novelist-jianchen",
        pairs=[(p1, "t1"), (p2, "t2")],
    )
    text_b = _build_prompt_increment(
        contract_id="cc_20260419_abcdef",
        writer="novelist-jianchen",
        pairs=[(p2, "t2"), (p1, "t1")],
    )
    assert text_a.index("项目 #1") < text_a.index("项目 #2")
    assert text_b.index("项目 #2") < text_b.index("项目 #1")


def test_build_prompt_increment_rejects_empty_pairs():
    from core.inspiration.dispatcher import _build_prompt_increment
    with pytest.raises(DispatcherError, match="pairs"):
        _build_prompt_increment(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            pairs=[],
        )
```

- [ ] **4.2 跑测试**:预期 4 个新用例 FAIL。

- [ ] **4.3 追加实现**:

```python
# ===================== _build_prompt_increment =====================

_PROMPT_HEADER = (
    "【创意契约约束】\n"
    "本次重写涉及创意契约 ID:{contract_id}\n"
    "承接写手:{writer}\n"
    "你负责以下 {n} 条采纳项的重写,每条均有标注区域与约束细则,"
    "**区域外**保持原文不动:"
)

_PROMPT_FOOTER = (
    "【重写守则】\n"
    "- 你只能在每个"项目"块标注的区域内修改,区域外保持原文\n"
    "- 标注为【必须保留】的子面禁止改动(否则触发评估师 MUST_PRESERVE 检查)\n"
    "- 标注为【可放开】的子面可根据"任务指令"重写\n"
    "- 若某项【可放开】为空,仅可优化字词/语流,不改核心手法\n"
    "- "涉及豁免维度"仅为知情提示,写手不得据此扩大修改范围"
)


def _build_prompt_increment(
    *,
    contract_id: str,
    writer: str,
    pairs: List,  # List[Tuple[PreserveItem, str]]
) -> str:
    """拼接整块派单 prompt:header + 多个项目块 + footer。"""
    if not pairs:
        raise DispatcherError(
            "_build_prompt_increment.pairs 必须非空(无任务的写手不应进入派单流程)"
        )
    parts: List[str] = []
    parts.append(
        _PROMPT_HEADER.format(
            contract_id=contract_id, writer=writer, n=len(pairs)
        )
    )
    for item, task in pairs:
        parts.append(_format_preserve_block(preserve_item=item, task=task))
    parts.append(_PROMPT_FOOTER)
    return "\n\n".join(parts)
```

- [ ] **4.4 跑测试**:预期 4 个用例 PASS,累计 22 passed。

---

### Task 5:写手分组(`_group_assignments_by_writer`)

按 `WriterAssignment.writer` 分组,保持原顺序。为后续 `dispatch` 提供基础。

#### 步骤

- [ ] **5.1 追加测试**:

```python
# ===================== _group_assignments_by_writer =====================


def _wa(item_id: str, writer: str, task: str = "rewrite_paragraph") -> WriterAssignment:
    return WriterAssignment(item_id=item_id, writer=writer, task=task)


def test_group_assignments_single_writer_multi_items():
    from core.inspiration.dispatcher import _group_assignments_by_writer
    groups = _group_assignments_by_writer([
        _wa("#1", "novelist-jianchen"),
        _wa("#2", "novelist-jianchen", task="tighten_rhythm"),
    ])
    assert list(groups.keys()) == ["novelist-jianchen"]
    assert [w.item_id for w in groups["novelist-jianchen"]] == ["#1", "#2"]
    assert groups["novelist-jianchen"][1].task == "tighten_rhythm"


def test_group_assignments_multi_writers_preserves_insertion_order():
    """dict 按写手首次出现的顺序排列;同一写手的 task 按原 list 顺序。"""
    from core.inspiration.dispatcher import _group_assignments_by_writer
    groups = _group_assignments_by_writer([
        _wa("#1", "novelist-yunxi"),
        _wa("#2", "novelist-jianchen"),
        _wa("#3", "novelist-yunxi"),
    ])
    assert list(groups.keys()) == ["novelist-yunxi", "novelist-jianchen"]
    assert [w.item_id for w in groups["novelist-yunxi"]] == ["#1", "#3"]
    assert [w.item_id for w in groups["novelist-jianchen"]] == ["#2"]


def test_group_assignments_empty_returns_empty_dict():
    from core.inspiration.dispatcher import _group_assignments_by_writer
    assert _group_assignments_by_writer([]) == {}
```

- [ ] **5.2 跑测试**:预期 3 个新用例 FAIL。

- [ ] **5.3 追加实现**:

```python
# ===================== 分组辅助 =====================


def _group_assignments_by_writer(
    assignments: List[WriterAssignment],
) -> Dict[str, List[WriterAssignment]]:
    """按 writer 分组并保持原列表中的相对顺序。"""
    groups: Dict[str, List[WriterAssignment]] = {}
    for wa in assignments:
        groups.setdefault(wa.writer, []).append(wa)
    return groups
```

- [ ] **5.4 跑测试**:预期 3 个用例 PASS,累计 25 passed。

---

### Task 6:顶层 `dispatch(contract)`— 正常路径

把契约转成 `List[DispatchPackage]`。本 Task 只实现**正常路径**(有 preserve_list + writer_assignments)。
跳过/空契约 放到 Task 7-8。

#### 步骤

- [ ] **6.1 追加测试**:

```python
# ===================== dispatch: 正常路径 =====================


def _make_contract(**overrides) -> CreativeContract:
    base = dict(
        contract_id=generate_contract_id(),
        chapter_ref="第3章",
        created_at="2026-04-19T12:00:00+08:00",
        negotiation_log=[
            NegotiationTurn(speaker="connoisseur", msg="建议 #1",
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


def test_dispatch_returns_list_of_dispatch_packages():
    c = _make_contract()
    packages = dispatch(c)
    assert isinstance(packages, list)
    assert len(packages) == 1
    assert isinstance(packages[0], DispatchPackage)


def test_dispatch_package_fields_populated():
    c = _make_contract()
    pkg = dispatch(c)[0]
    assert pkg.contract_id == c.contract_id
    assert pkg.writer == "novelist-jianchen"
    assert pkg.item_ids == ["#1"]
    assert pkg.tasks == ["rewrite_paragraph"]
    assert len(pkg.preserve_items) == 1
    assert pkg.preserve_items[0].item_id == "#1"
    assert "【创意契约约束】" in pkg.prompt_increment
    assert c.contract_id in pkg.prompt_increment


def test_dispatch_package_self_validates():
    """dispatch 返回的每个包必然通过自身 validate()。"""
    c = _make_contract()
    for pkg in dispatch(c):
        pkg.validate()  # 不应抛


def test_dispatch_multi_writers_produces_multi_packages():
    """两位写手各自拿到一个 package,顺序 = 首次出现顺序。"""
    p1 = _make_preserve_item(item_id="#1")
    p3 = _make_preserve_item(
        item_id="#3",
        scope=Scope(paragraph_index=5, char_start=10, char_end=99),
    )
    c = _make_contract(
        preserve_list=[p1, p3],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#3", writer="novelist-yunxi",
                             task="chapter_polish_with_preserve"),
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    pkgs = dispatch(c)
    assert [p.writer for p in pkgs] == ["novelist-yunxi", "novelist-jianchen"]
    yunxi = pkgs[0]
    assert yunxi.item_ids == ["#3"]
    assert yunxi.tasks == ["chapter_polish_with_preserve"]


def test_dispatch_single_writer_multi_items_keeps_order():
    """一位写手承接多 item 时,顺序与 writer_assignments 原顺序一致。"""
    p1 = _make_preserve_item(item_id="#1")
    p3 = _make_preserve_item(
        item_id="#3",
        scope=Scope(paragraph_index=7, char_start=0, char_end=50),
    )
    c = _make_contract(
        preserve_list=[p1, p3],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#3", writer="novelist-jianchen",
                             task="second_task"),
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="first_task"),
        ],
    )
    pkgs = dispatch(c)
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.item_ids == ["#3", "#1"]
    assert pkg.tasks == ["second_task", "first_task"]
    # prompt 中项目顺序一致
    assert pkg.prompt_increment.index("项目 #3") < pkg.prompt_increment.index("项目 #1")
```

- [ ] **6.2 跑测试**:预期 5 个新用例 FAIL(`dispatch` 未实现)。

- [ ] **6.3 追加实现**(到 `core/inspiration/dispatcher.py` 末尾):

```python
# ===================== dispatch 顶层 =====================


def dispatch(contract: CreativeContract) -> List[DispatchPackage]:
    """把一份已校验契约转成每位写手的派单包列表。

    规则:
      - contract.skipped_by_author=True → 返回 [](Q1)
      - contract.writer_assignments 为空 → 返回 []
      - 正常路径:按 writer 分组,每组渲染 prompt 增量,产出 DispatchPackage
    """
    # 内部 re-validate,不信任调用方
    contract.validate()

    if contract.skipped_by_author:
        return []
    if not contract.writer_assignments:
        return []

    # item_id → PreserveItem 反查表
    items_by_id: Dict[str, PreserveItem] = {
        p.item_id: p for p in contract.preserve_list
    }

    groups = _group_assignments_by_writer(contract.writer_assignments)

    packages: List[DispatchPackage] = []
    for writer, assignments in groups.items():
        item_ids = [wa.item_id for wa in assignments]
        tasks = [wa.task for wa in assignments]
        preserve_items = [items_by_id[iid] for iid in item_ids]
        pairs = list(zip(preserve_items, tasks))
        prompt = _build_prompt_increment(
            contract_id=contract.contract_id,
            writer=writer,
            pairs=pairs,
        )
        pkg = DispatchPackage(
            contract_id=contract.contract_id,
            writer=writer,
            item_ids=item_ids,
            tasks=tasks,
            preserve_items=preserve_items,
            prompt_increment=prompt,
        )
        pkg.validate()
        packages.append(pkg)
    return packages
```

- [ ] **6.4 跑测试**:预期 5 个用例全 PASS,累计 30 passed。

---

### Task 7:`dispatch` — Q1 跳过路径 + 空契约

#### 步骤

- [ ] **7.1 追加测试**:

```python
# ===================== dispatch: Q1 跳过 / 空契约 =====================


def test_dispatch_skipped_by_author_returns_empty():
    """Q1:鉴赏师 0 条 + 作者确认跳过 → 空契约 → dispatch 返回 []。"""
    c = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第5章",
        created_at="2026-04-19T13:00:00+08:00",
        skipped_by_author=True,
    )
    assert dispatch(c) == []


def test_dispatch_no_assignments_returns_empty():
    """writer_assignments 空(但契约本身合法,未 skip)→ dispatch 返回 []。

    语义:鉴赏师虽然有建议,但派单决定没落到任何写手头上
    (如:preserve_list 全靠 P2-2 的云溪兜底整章润色流程处理,
    不在 writer_assignments 表达)。
    """
    c = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第5章",
        created_at="2026-04-19T13:00:00+08:00",
        preserve_list=[_make_preserve_item()],
        rejected_list=[],
        writer_assignments=[],
    )
    assert dispatch(c) == []


def test_dispatch_rejects_unvalidated_tampered_contract():
    """调用方若绕过 validate 手动改坏字段,dispatch 入口会重新 validate 并抛错。"""
    c = _make_contract()
    # 后门伪造:插入指向不存在 item 的 assignment
    c.writer_assignments = [
        WriterAssignment(item_id="#1", writer="novelist-jianchen",
                         task="rewrite_paragraph"),
        WriterAssignment(item_id="#99", writer="novelist-jianchen",
                         task="bogus"),
    ]
    with pytest.raises(ContractValidationError, match="writer_assignments"):
        dispatch(c)
```

- [ ] **7.2 跑测试**:预期 3 个用例 PASS(Task 6 的 dispatch 实现已涵盖这三条支路)。

**若有 FAIL:检查 Task 6.3 的实现,确保 `contract.validate()` 在最前、`skipped_by_author` 与 `writer_assignments` 空分支先 return。**

累计 33 passed。

---

### Task 8:`dispatch` — Q2 嵌套渲染端到端

验证 Q2 在整个 dispatch 管道里真正到达 prompt。

#### 步骤

- [ ] **8.1 追加测试**:

```python
# ===================== dispatch: Q2 嵌套端到端 =====================


def test_dispatch_prompt_contains_q2_preserve_and_drop():
    p = _make_preserve_item(
        aspects=Aspects(
            preserve=["情绪强度", "心理动机"],
            drop=["具体台词", "肢体表现"],
        ),
    )
    c = _make_contract(
        preserve_list=[p],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    pkg = dispatch(c)[0]
    prompt = pkg.prompt_increment
    assert "【必须保留】" in prompt
    assert "情绪强度" in prompt
    assert "心理动机" in prompt
    assert "【可放开】" in prompt
    assert "具体台词" in prompt
    assert "肢体表现" in prompt


def test_dispatch_prompt_q2_empty_drop_degrades():
    p = _make_preserve_item(
        aspects=Aspects(preserve=["节奏张力"], drop=[]),
    )
    c = _make_contract(
        preserve_list=[p],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    prompt = dispatch(c)[0].prompt_increment
    assert "节奏张力" in prompt
    assert "仅可优化字词" in prompt or "仅优化字词" in prompt
```

- [ ] **8.2 跑测试**:预期 2 个用例 PASS(Task 3/4/6 链已实现)。累计 35 passed。

---

### Task 9:`dispatch` — 多写手并行端到端

验证 v2 §1 阶段 5.6 "鉴赏师对每条采纳建议派单" 的多写手场景。

#### 步骤

- [ ] **9.1 追加测试**:

```python
# ===================== dispatch: 多写手真实场景 =====================


def test_dispatch_three_writers_scenario():
    """v2 §1 阶段 5.6 典型场景:
    - #1 改第3段视角 → 剑尘 rewrite_paragraph
    - #2 整章节奏调整 → 云溪 chapter_polish
    - #3 对话打磨     → 墨言 tighten_dialogue
    """
    p1 = _make_preserve_item(
        item_id="#1",
        scope=Scope(paragraph_index=3, char_start=234, char_end=567),
        aspects=Aspects(preserve=["败者视角主导"], drop=["具体用词"]),
    )
    p2 = _make_preserve_item(
        item_id="#2",
        scope=Scope(paragraph_index=0, char_start=0, char_end=9999),
        applied_constraint_id=None,
        aspects=Aspects(preserve=["整章节奏: 紧-紧-松-紧"], drop=[]),
    )
    p3 = _make_preserve_item(
        item_id="#3",
        scope=Scope(paragraph_index=7, char_start=10, char_end=250),
        applied_constraint_id="ANTI_007",
        aspects=Aspects(preserve=["反派口语色调"], drop=["具体词汇"]),
    )
    c = _make_contract(
        preserve_list=[p1, p2, p3],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
            WriterAssignment(item_id="#2", writer="novelist-yunxi",
                             task="chapter_polish_with_preserve"),
            WriterAssignment(item_id="#3", writer="novelist-moyan",
                             task="tighten_dialogue"),
        ],
    )
    pkgs = dispatch(c)
    # 3 个 package,顺序 = 出现顺序
    assert [p.writer for p in pkgs] == [
        "novelist-jianchen", "novelist-yunxi", "novelist-moyan"
    ]
    # 每个 package 只承接本写手的项目
    assert pkgs[0].item_ids == ["#1"]
    assert pkgs[1].item_ids == ["#2"]
    assert pkgs[2].item_ids == ["#3"]
    # prompt 中不混入他人的 item
    assert "项目 #2" not in pkgs[0].prompt_increment
    assert "项目 #1" not in pkgs[1].prompt_increment
    assert "项目 #2" not in pkgs[2].prompt_increment


def test_dispatch_integrity_total_assignments_conserved():
    """所有 package 的 item_ids 总数 = 契约 writer_assignments 总数。"""
    p1 = _make_preserve_item(item_id="#1")
    p2 = _make_preserve_item(
        item_id="#2",
        scope=Scope(paragraph_index=4, char_start=0, char_end=100),
    )
    p3 = _make_preserve_item(
        item_id="#3",
        scope=Scope(paragraph_index=5, char_start=0, char_end=100),
    )
    c = _make_contract(
        preserve_list=[p1, p2, p3],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen", task="t1"),
            WriterAssignment(item_id="#2", writer="novelist-jianchen", task="t2"),
            WriterAssignment(item_id="#3", writer="novelist-yunxi", task="t3"),
        ],
    )
    pkgs = dispatch(c)
    total = sum(len(p.item_ids) for p in pkgs)
    assert total == len(c.writer_assignments) == 3
```

- [ ] **9.2 跑测试**:预期 2 个用例 PASS。累计 37 passed。

---

### Task 10:`dispatch` — Q4 豁免透传 + 多 evaluator_risk 端到端

#### 步骤

- [ ] **10.1 追加测试**:

```python
# ===================== dispatch: Q4 豁免透传 / evaluator_risk =====================


def test_dispatch_prompt_exempt_dimensions_transparent():
    p = _make_preserve_item(
        exempt_dimensions=[
            ExemptDimension(dimension="视角连贯性",
                            sub_items=["主角一致性", "叙述人称一致性"]),
            ExemptDimension(dimension="情绪节奏",
                            sub_items=["爽快度曲线"]),
        ],
    )
    c = _make_contract(
        preserve_list=[p],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    prompt = dispatch(c)[0].prompt_increment
    assert "视角连贯性" in prompt
    assert "主角一致性" in prompt
    assert "叙述人称一致性" in prompt
    assert "情绪节奏" in prompt
    assert "爽快度曲线" in prompt


def test_dispatch_prompt_evaluator_risk_transparent():
    p = _make_preserve_item(
        evaluator_risk=["主角视角连贯性 -0.1", "节奏打断风险", "读者代入感降低"],
    )
    c = _make_contract(
        preserve_list=[p],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    prompt = dispatch(c)[0].prompt_increment
    assert "评估师风险" in prompt
    assert "主角视角连贯性 -0.1" in prompt
    assert "节奏打断风险" in prompt
    assert "读者代入感降低" in prompt
```

- [ ] **10.2 跑测试**:预期 2 个用例 PASS。累计 39 passed。

---

### Task 11:`dispatch` — 防御性:拒绝未被上游校验过的契约(再保险)

此 Task 非常简短,只加 1 个断言测试,确保即使上游漏 validate,dispatch 也会在入口触发校验。

#### 步骤

- [ ] **11.1 追加测试**:

```python
# ===================== dispatch: 入口再校验 =====================


def test_dispatch_calls_validate_on_entry():
    """契约的 contract_id 伪造成非法格式,dispatch 必须抛 ContractValidationError。"""
    # 直接构造一个 contract_id 格式非法的契约,绕过 generate_contract_id
    c = CreativeContract(
        contract_id="not-a-valid-id",
        chapter_ref="第3章",
        created_at="2026-04-19T12:00:00+08:00",
        preserve_list=[_make_preserve_item()],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    with pytest.raises(ContractValidationError, match="contract_id"):
        dispatch(c)
```

- [ ] **11.2 跑测试**:预期 1 用例 PASS(Task 6 已在 dispatch 开头 `contract.validate()`)。累计 40 passed。

---

### Task 12:冒烟端到端 + `__init__.py` 导出

修改 `core/inspiration/__init__.py`,把 3 个符号追加到 import 块与 `__all__`。

#### 步骤

- [ ] **12.1 用 Edit 工具修改 `core/inspiration/__init__.py`**:

把原 import 段落:

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

**紧接其后追加**:

```python
from core.inspiration.dispatcher import (
    DispatchPackage,
    dispatch,
    DispatcherError,
)
```

- [ ] **12.2 用 Edit 工具在 `__all__` 列表的 `"ContractValidationError",` 之后**追加(仍在同一列表、结尾 `]` 之前):

```python
    "DispatchPackage",
    "dispatch",
    "DispatcherError",
```

- [ ] **12.3 冒烟**:

```bash
cd "D:/动画/众生界"
python -c "from core.inspiration import CreativeContract, dispatch, DispatchPackage, DispatcherError, generate_contract_id; c = CreativeContract(contract_id=generate_contract_id(), chapter_ref='第1章', created_at='2026-04-19T00:00:00+08:00', skipped_by_author=True); print('skipped →', dispatch(c))"
```

预期打印:`skipped → []`(或 `skipped → list`,空列表)。不应报错。

- [ ] **12.4 追加综合冒烟测试**(到 `tests/test_dispatcher.py` 末尾):

```python
# ===================== 综合冒烟 =====================


def test_end_to_end_smoke_full_v2_stage_5_6():
    """v2 §1 阶段 5.6 端到端冒烟:
    契约构造 → dispatch → 检查 prompt 含全部关键字段 → 每包自校验。
    """
    p1 = _make_preserve_item(
        item_id="#1",
        scope=Scope(paragraph_index=3, char_start=234, char_end=567),
        aspects=Aspects(
            preserve=["败者视角主导", "情绪强度"],
            drop=["具体用词", "肢体细节"],
        ),
        exempt_dimensions=[
            ExemptDimension(dimension="视角连贯性",
                            sub_items=["主角一致性"]),
        ],
        evaluator_risk=["主角视角连贯性 -0.1"],
    )
    p2 = _make_preserve_item(
        item_id="#2",
        scope=Scope(paragraph_index=0, char_start=0, char_end=9999),
        applied_constraint_id=None,
        aspects=Aspects(preserve=["整章节奏"], drop=[]),
        exempt_dimensions=[],
        evaluator_risk=[],
    )
    c = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第3章",
        created_at="2026-04-19T12:00:00+08:00",
        negotiation_log=[
            NegotiationTurn(speaker="connoisseur",
                            msg="建议 #1:第3段改败者视角;建议 #2:整章节奏",
                            timestamp="2026-04-19T12:00:00+08:00"),
            NegotiationTurn(speaker="evaluator",
                            msg="#1 风险:主角视角连贯性 -0.1;#2 无异议",
                            timestamp="2026-04-19T12:02:00+08:00"),
            NegotiationTurn(speaker="author",
                            msg="采纳 #1 和 #2",
                            timestamp="2026-04-19T12:05:00+08:00"),
        ],
        preserve_list=[p1, p2],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
            WriterAssignment(item_id="#2", writer="novelist-yunxi",
                             task="chapter_polish_with_preserve"),
        ],
        iteration_count=0,
        max_iterations=3,
    )
    pkgs = dispatch(c)
    # 2 位写手各得一个包
    assert len(pkgs) == 2
    names = [p.writer for p in pkgs]
    assert names == ["novelist-jianchen", "novelist-yunxi"]
    # 每个包自校验 + 关键字段齐全
    for pkg in pkgs:
        pkg.validate()
        assert c.contract_id in pkg.prompt_increment
        assert "【创意契约约束】" in pkg.prompt_increment
        assert "重写守则" in pkg.prompt_increment
    jianchen = pkgs[0]
    assert "败者视角主导" in jianchen.prompt_increment
    assert "情绪强度" in jianchen.prompt_increment
    assert "具体用词" in jianchen.prompt_increment
    assert "肢体细节" in jianchen.prompt_increment
    assert "主角视角连贯性 -0.1" in jianchen.prompt_increment
    assert "主角一致性" in jianchen.prompt_increment
    yunxi = pkgs[1]
    assert "整章节奏" in yunxi.prompt_increment
    # yunxi 的项目 drop 为空 → 降级提示
    assert "仅可优化字词" in yunxi.prompt_increment or "仅优化字词" in yunxi.prompt_increment


def test_public_api_via_package_import():
    """通过 core.inspiration 顶层导入应可达 dispatcher 3 个符号。"""
    from core import inspiration as insp
    for name in ("DispatchPackage", "dispatch", "DispatcherError"):
        assert hasattr(insp, name), f"{name} 未从 core.inspiration 导出"
```

- [ ] **12.5 跑测试**:`python -m pytest tests/test_dispatcher.py -v`。预期全 PASS,用例 ≥ 20。累计 42 passed。

---

### Task 13:保护性核验(其他模块未动)

#### 步骤

- [ ] **13.1 跑**(bash):

```bash
cd "D:/动画/众生界"
# creative_contract.py 不得改
git status --short core/inspiration/creative_contract.py
# 应无输出(或仅本地 cache 扰动,最好为空)
```

若输出非空 → **停止并报告 Claude**,不得继续。

- [ ] **13.2 跑**:

```bash
git status --short core/inspiration/appraisal_agent.py core/inspiration/workflow_bridge.py core/inspiration/constraint_library.py core/inspiration/variant_generator.py core/inspiration/memory_point_sync.py core/inspiration/structural_analyzer.py
```

应无输出。若任一文件被修改 → 立即停止并报告。

---

### Task 14:全量 pytest + 回归

#### 步骤

- [ ] **14.1 跑全量**:

```bash
cd "D:/动画/众生界"
python -m pytest tests/ -v --tb=short 2>&1 | tee docs/m7_artifacts/p1-2_test_log_20260419.txt | tail -30
```

- [ ] **14.2 最后一行应形如**:

```
=== 526 passed, 1 skipped, 2 warnings in XX.XXs ===
```

(基线 506 + 本计划新增 ≥ 20 用例 ≈ 526+)

- [ ] **14.3 若出现 failed,立即停止并报告,不得声称完成。**

---

## 4. 文件最终结构

`core/inspiration/dispatcher.py` 完成后应大致是:

```
"""模块 docstring"""
from __future__ import annotations
# imports: dataclass / typing / creative_contract 4 符号
__all__ = ["DispatchPackage", "dispatch", "DispatcherError"]

class DispatcherError(ContractValidationError): ...

# ===================== DispatchPackage =====================
@dataclass
class DispatchPackage:
    contract_id / writer / item_ids / tasks / preserve_items / prompt_increment
    def validate(self) -> None: ...

# ===================== prompt 模板 =====================
_BLOCK_SEPARATOR = "...{item_id}..."
_BLOCK_CLOSER = "..."
def _format_preserve_block(*, preserve_item, task) -> str: ...

# ===================== _build_prompt_increment =====================
_PROMPT_HEADER = "..."
_PROMPT_FOOTER = "..."
def _build_prompt_increment(*, contract_id, writer, pairs) -> str: ...

# ===================== 分组辅助 =====================
def _group_assignments_by_writer(assignments) -> Dict[str, List[WriterAssignment]]: ...

# ===================== dispatch 顶层 =====================
def dispatch(contract: CreativeContract) -> List[DispatchPackage]: ...
```

总行数预计 150-180 行。

---

## 5. 自检命令(§3 全部完成后跑)

```bash
cd "D:/动画/众生界"

echo "===== P1-2 自检开始 ====="

# 文件存在
test -f core/inspiration/dispatcher.py && echo "PASS-F1 实现文件" || echo "FAIL-F1"
test -f tests/test_dispatcher.py && echo "PASS-F2 测试文件" || echo "FAIL-F2"

# Python 语法
python -c "import ast; ast.parse(open('core/inspiration/dispatcher.py', encoding='utf-8').read())" \
  && echo "PASS-S1 impl 语法 OK" || echo "FAIL-S1"
python -c "import ast; ast.parse(open('tests/test_dispatcher.py', encoding='utf-8').read())" \
  && echo "PASS-S2 test 语法 OK" || echo "FAIL-S2"

# 无第三方依赖(禁用列表)
if grep -qE "^(from|import) (pydantic|attrs|marshmallow|jinja2)" core/inspiration/dispatcher.py; then
  echo "FAIL-D1 引入了禁用的第三方依赖"
else
  echo "PASS-D1 stdlib-only"
fi

# 无 I/O(dispatcher 必须是纯函数)
if grep -qE "^(import|from) (requests|httpx|urllib|qdrant_client|openai|anthropic)" core/inspiration/dispatcher.py; then
  echo "FAIL-D2 引入了 I/O 或 LLM 客户端"
else
  echo "PASS-D2 无 I/O/LLM 依赖"
fi
if grep -qE "(open\(|\.read\(\)|\.write\(|requests\.|httpx\.)" core/inspiration/dispatcher.py; then
  echo "FAIL-D3 dispatcher 出现 I/O 调用"
else
  echo "PASS-D3 dispatcher 纯函数"
fi

# 包导出
python -c "from core.inspiration import DispatchPackage, dispatch, DispatcherError, CreativeContract, generate_contract_id; print('imports OK')" \
  && echo "PASS-E1 包导出齐全" || echo "FAIL-E1"

# 模块测试数量
count=$(python -m pytest tests/test_dispatcher.py --collect-only -q 2>&1 | grep -c "::test_")
[ "$count" -ge 20 ] && echo "PASS-T1 测试用例 $count 个 (≥20)" || echo "FAIL-T1 仅 $count 个"

# 模块测试通过
python -m pytest tests/test_dispatcher.py --tb=short 2>&1 | tail -5
if python -m pytest tests/test_dispatcher.py --tb=no -q 2>&1 | tail -1 | grep -qE "passed.*failed|^[0-9]+ failed"; then
  echo "FAIL-T2 有 failed"
else
  echo "PASS-T2 模块测试全通过"
fi

# Q1/Q2 行为核验 —— 代码级关键字扫描
grep -q "skipped_by_author" core/inspiration/dispatcher.py && echo "PASS-Q1 Q1 跳过支路存在" || echo "FAIL-Q1"
grep -q "【必须保留】" core/inspiration/dispatcher.py && echo "PASS-Q2A Q2 preserve 标签" || echo "FAIL-Q2A"
grep -q "【可放开】" core/inspiration/dispatcher.py && echo "PASS-Q2B Q2 drop 标签" || echo "FAIL-Q2B"

# Q1/Q2 运行时断言 —— 真跑一趟 dispatch
python -c "
from core.inspiration import CreativeContract, dispatch, generate_contract_id
c = CreativeContract(
    contract_id=generate_contract_id(),
    chapter_ref='第1章',
    created_at='2026-04-19T00:00:00+08:00',
    skipped_by_author=True,
)
assert dispatch(c) == [], 'Q1 skipped 未返回空'
print('Q1 runtime OK')
" && echo "PASS-Q1R Q1 runtime" || echo "FAIL-Q1R"

# 保护性:其他 inspiration 模块未动
for f in creative_contract.py appraisal_agent.py constraint_library.py memory_point_sync.py structural_analyzer.py variant_generator.py workflow_bridge.py escalation_dialogue.py resonance_feedback.py; do
  status=$(git status --short "core/inspiration/$f" | head -1)
  if [ -z "$status" ]; then
    echo "PASS-P $f 未动"
  else
    echo "FAIL-P $f 被改动: $status"
  fi
done

# 全量回归(与 P1-1 基线对比)
python -m pytest tests/ --tb=no -q 2>&1 | tail -1 | tee /tmp/p1-2_summary.txt
if grep -qE "^[0-9]+ passed.*[0-9]+ skipped" /tmp/p1-2_summary.txt; then
  echo "PASS-R1 全量跑通"
else
  echo "FAIL-R1 全量异常"
fi
# 至少 526 passed(P1-1 后基线 506 + 本计划 ≥ 20)
total=$(grep -oE "^[0-9]+ passed" /tmp/p1-2_summary.txt | head -1 | grep -oE "^[0-9]+")
if [ -n "$total" ] && [ "$total" -ge 526 ]; then
  echo "PASS-R2 ≥526 passed(实得 $total)"
else
  echo "FAIL-R2 低于 526 passed(实得 ${total:-N/A})"
fi

# git HEAD 未 commit
hash=$(git log -1 --format=%h)
echo "HEAD=$hash (P1-2 不得 commit)"
if [ "$hash" != "8365fe21a" ]; then
  echo "FAIL-G1 HEAD 不再是 8365fe21a"
else
  echo "PASS-G1 HEAD 未推进"
fi

echo "===== P1-2 自检结束 ====="
```

任一 `FAIL-` → **立即停止,不得声称完成**,报告给 Claude。

---

## 6. 完成判据

- [x] 14 个 Task 全部按 TDD 顺序完成
- [x] `tests/test_dispatcher.py` ≥ 20 个用例全 PASS
- [x] 全量 pytest:基线 506 + 新增 N (≥20) 全 passed,0 failed
- [x] §5 所有 `PASS-` 标记,无 `FAIL-`
- [x] `core/inspiration/` 所有既有 `.py` 文件无改动(除 `__init__.py` 的追加外)
- [x] `creative_contract.py` 无任何改动
- [x] 无第三方依赖
- [x] dispatcher 无 I/O / 无 LLM 调用 / 纯函数
- [x] 无 git commit
- [x] Q1 / Q2 / Q4 在代码与 prompt 中体现(Q3 与本层无关)

---

## 7. 完成后更新 ROADMAP(仅在 §5 全 PASS 后才能改)

1. ROADMAP §3.2 P1-2 行:状态改 ✅,备注 "`core/inspiration/dispatcher.py` 新建,tests/test_dispatcher.py N 个用例全 PASS,全量 pytest X passed"
2. §5 时间线追加一行:

```
| 2026-04-19 | Claude | 写 P1-2 计划 | docs/计划_P1-2_dispatcher_20260419.md |
| 2026-04-19 | opencode | P1-2 派单器完成 | dispatcher.py + tests (≥20 用例全 PASS),全量 pytest 526+ passed |
| 2026-04-19 | Claude | P1-2 §5 自检(全 PASS,HEAD 未 commit) | - |
```

3. §3 "★ 当前任务指针" 改:**P1-3 鉴赏师 SKILL.md 大改启动**

---

## 8. 下一步

- Claude 核验 §5 自检(不信 opencode "完成"声明,原样跑完全部 PASS 检查)
- 核验全 PASS → Claude 写 `docs/计划_P1-3_connoisseur_skill重写_20260419.md`
- 任一 FAIL → Claude 报告作者,不改 ROADMAP ✅

---

**计划结束。opencode 按 Task 1 → Task 14 顺序 TDD 执行,§5 自检,§6 判据,§7 ROADMAP 更新。三部分全必做,自检任一 FAIL 不得改 ✅。**
