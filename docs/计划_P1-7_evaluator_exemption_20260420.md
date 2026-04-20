# P1-7 计划:评估师豁免数据层(新建模块)

> **文档日期**:2026-04-20(Asia/Shanghai)
> **对象执行者**:opencode(GLM5)
> **计划类型**:纯新建模块(零影响面)
> **依据**:v2 设计 §1 阶段 6 "preserve_list 区域 → 相关维度跳过(豁免)";作者 Q4 硬约束 "`ExemptDimension.sub_items` 必须非空,禁止整维度豁免"
> **路线图位置**:`docs/ROADMAP_众生界v2实施_20260419.md` §3.2 P1-7

---

## 0. 本计划的目的 — 必读

新建 `core/inspiration/evaluator_exemption.py` — 纯数据层,把 `CreativeContract.preserve_list` 中的 `exempt_dimensions` 整理成评估师查询用的豁免索引:

- 按 `paragraph_index` 聚合
- 按 `dimension` 二级聚合
- 叶节点为 `sub_items` 列表(Q4 禁止整维度豁免,故叶节点必非空)

**本计划只做"契约 → 豁免查询结构"的纯函数转换**。与评估师 SKILL.md / workflow 的接线由 P2-3 / P1-7 的下游 skill 修改环节处理。

### 0.1 范围边界(不得扩张)

- ❌ 不改既有任何文件(100% 追加新文件)
- ❌ 不读任何外部文件、不写 JSON、不调 LLM
- ❌ 不处理段落"重叠"情况(若两个 `PreserveItem` 覆盖同一段,本层仅去重合并,不做区间精确切分)
- ❌ 不改动 creative_contract.py(其 P1-1 已提供所需类型)
- ✅ 仅新建 2 个文件:impl + test
- ✅ stdlib-only

### 0.2 产出清单

| 产出 | 路径 | 动作 |
|------|------|------|
| 实施 | `core/inspiration/evaluator_exemption.py` | **新建** |
| 测试 | `tests/test_evaluator_exemption.py` | **新建** |
| 追加导出 | `core/inspiration/__init__.py` | **追加 3 个符号** |

### 0.3 新 API 契约(不得偏离)

```python
# 类型别名(非 dataclass,仅 TypeAlias 风格,纯 dict 字面)
ExemptionMap = Dict[int, Dict[str, Set[str]]]
# 语义:{ paragraph_index: { dimension: { sub_item1, sub_item2, ... } } }
# sub_items 集合非空(Q4 铁律),若为空本函数会 raise ExemptionBuildError

class ExemptionBuildError(ValueError): ...

def build_exemption_map(contract: CreativeContract) -> ExemptionMap:
    """
    从契约的 preserve_list 提取段落级豁免索引。

    仅读取 contract.preserve_list[i].scope.paragraph_index
           + contract.preserve_list[i].exempt_dimensions[j].dimension
           + contract.preserve_list[i].exempt_dimensions[j].sub_items

    不修改契约本身。不调 contract.validate()(调用方负责)。
    同一 (paragraph, dimension) 多次出现 → sub_items 求并集。

    Raises:
        ExemptionBuildError: 若发现 sub_items 为空(Q4 违反)
        TypeError:           若 contract 非 CreativeContract
    """

def is_exempt(
    exemption_map: ExemptionMap,
    paragraph_index: int,
    dimension: str,
    sub_item: str,
) -> bool:
    """
    查询:该段该维度该子项是否被豁免。

    任一 key 不存在 → False(未豁免,须照常打分)。
    """

def format_exemption_report(exemption_map: ExemptionMap) -> str:
    """
    可读报告:人读 / 审计日志用。中文。
    空 map → '(本章无豁免)'
    """
```

---

## 1. 执行前真实状态

- `core/inspiration/creative_contract.py` 已导出 `CreativeContract`/`PreserveItem`/`ExemptDimension`/`Scope`/`Aspects`(P1-1 完成,验证通过)
- `core/inspiration/__init__.py` 当前导出约 13 符号;本计划只在 `__all__` 或等价导出段**追加** 3 符号,不删不改
- pytest 基线:假设 P1-6 已完成 → 584 passed;若直接在 P1-6 之前执行 → 571 passed(自检据此选预期数字)

**注意**:本计划的全量 pytest 期望 = `<当前基线> + 15`(新测试 15 条)。若是过夜批次中 P1-6 完成后执行,则期望 **599 passed**;否则 **586 passed**。

---

## 2. opencode 执行规则(不可违反)

### 2.1 允许

- 新建 `core/inspiration/evaluator_exemption.py`
- 新建 `tests/test_evaluator_exemption.py`
- **在 `core/inspiration/__init__.py` 末尾追加** 3 行 import + 扩展 `__all__`(或文件本来用其它显式导出方式 — 若没有 `__all__` 则只追加 import 行,不造新 `__all__`)
- 运行 pytest / python -c

### 2.2 禁止

- 不得修改 `creative_contract.py` 任何一行
- 不得 git add / commit / push
- 不得引入任何第三方库(stdlib-only,仅 `from __future__`、`dataclasses`、`typing`、`re` 允许)
- 不得读/写磁盘、网络、LLM
- 不得创建 `.archived/` / `.vectorstore/` 下任何东西

### 2.3 TDD 严格执行

同 P1-4 / P1-6:每个 Task 先写失败测试 → pytest 看到 FAIL → 写实现 → pytest 看到 PASS。

---

## 3. 执行步骤

### Task 1:新建测试文件骨架 + 第 1 组(build 基础,预期 FAIL)

**文件**:`tests/test_evaluator_exemption.py`(新建)

```python
# tests/test_evaluator_exemption.py
"""Tests for core.inspiration.evaluator_exemption.

仅测试纯数据转换 —— 不涉及任何评估师 prompt / LLM / 磁盘 I/O。
Q4 硬约束:sub_items 非空,否则 ExemptionBuildError。
"""
from __future__ import annotations

import pytest

from core.inspiration.creative_contract import (
    Aspects,
    CreativeContract,
    ExemptDimension,
    PreserveItem,
    Scope,
)


# ----------------- fixtures -----------------

def _make_item(
    item_id: str,
    paragraph_index: int,
    exempts: list[tuple[str, list[str]]],
    char_start: int = 0,
    char_end: int = 10,
) -> PreserveItem:
    """便捷构造 PreserveItem。exempts = [(dim, [sub,...]), ...]"""
    return PreserveItem(
        item_id=item_id,
        scope=Scope(
            paragraph_index=paragraph_index,
            char_start=char_start,
            char_end=char_end,
        ),
        applied_constraint_id=None,
        rationale="test",
        evaluator_risk=[],
        aspects=Aspects(preserve=["情绪强度"]),
        exempt_dimensions=[
            ExemptDimension(dimension=d, sub_items=list(s)) for d, s in exempts
        ],
    )


def _make_contract(preserve_list):
    return CreativeContract(
        contract_id="cc_20260420_abcdef",
        chapter_ref="test_ch",
        created_at="2026-04-20T03:30:00+08:00",
        preserve_list=preserve_list,
    )


# ===================== build_exemption_map 基础 =====================

def test_build_empty_contract_returns_empty_map():
    """空 preserve_list → 空 map"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    m = build_exemption_map(_make_contract([]))
    assert m == {}


def test_build_single_item_single_dimension():
    """单 item 单维度 → {para: {dim: {subs...}}}"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract(
        [_make_item("#1", paragraph_index=3,
                    exempts=[("视角连贯性", ["人称切换", "焦点切换"])])]
    )
    m = build_exemption_map(c)
    assert set(m.keys()) == {3}
    assert set(m[3].keys()) == {"视角连贯性"}
    assert m[3]["视角连贯性"] == {"人称切换", "焦点切换"}


def test_build_multiple_items_same_paragraph_merge():
    """两 item 同段同维度 → sub_items 并集"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract([
        _make_item("#1", paragraph_index=2, char_start=0, char_end=10,
                   exempts=[("节奏", ["重复句"])]),
        _make_item("#2", paragraph_index=2, char_start=20, char_end=30,
                   exempts=[("节奏", ["短句密集"])]),
    ])
    m = build_exemption_map(c)
    assert m[2]["节奏"] == {"重复句", "短句密集"}


def test_build_multiple_paragraphs_isolated():
    """不同 paragraph 互不干扰"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract([
        _make_item("#1", paragraph_index=0,
                   exempts=[("X", ["a"])]),
        _make_item("#2", paragraph_index=5,
                   exempts=[("X", ["b"])]),
    ])
    m = build_exemption_map(c)
    assert m[0]["X"] == {"a"}
    assert m[5]["X"] == {"b"}
```

**运行**:
```bash
python -m pytest tests/test_evaluator_exemption.py -v
```
**期望**:4 FAIL,均 `ModuleNotFoundError: evaluator_exemption`

---

### Task 2:最小实现 `build_exemption_map`

**文件**:`core/inspiration/evaluator_exemption.py`(新建)

```python
# core/inspiration/evaluator_exemption.py
"""评估师豁免数据层(Q4 子项粒度)。

把 CreativeContract.preserve_list 中的 exempt_dimensions 展成段落级查询索引:
    { paragraph_index: { dimension: { sub_item1, sub_item2, ... } } }

仅做纯数据转换,不涉及评估师 prompt / LLM / 磁盘 I/O。
Q4 硬约束:sub_items 非空;空值一律 ExemptionBuildError(禁止整维度豁免)。

设计文档:docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md §1 阶段 6
实施计划:docs/计划_P1-7_evaluator_exemption_20260420.md
"""
from __future__ import annotations

from typing import Dict, Set

from core.inspiration.creative_contract import CreativeContract

__all__ = [
    "ExemptionMap",
    "ExemptionBuildError",
    "build_exemption_map",
    "is_exempt",
    "format_exemption_report",
]

# 类型别名:{paragraph_index: {dimension: {sub_items}}}
ExemptionMap = Dict[int, Dict[str, Set[str]]]


class ExemptionBuildError(ValueError):
    """构建豁免索引时发现不合法数据(通常是 Q4 违反)。"""


def build_exemption_map(contract: CreativeContract) -> ExemptionMap:
    """从契约抽取段落级豁免索引。"""
    if not isinstance(contract, CreativeContract):
        raise TypeError(
            f"contract 必须是 CreativeContract,实得 {type(contract).__name__}"
        )

    result: ExemptionMap = {}
    for item in contract.preserve_list:
        para = item.scope.paragraph_index
        for ed in item.exempt_dimensions:
            if not ed.sub_items:
                raise ExemptionBuildError(
                    f"item {item.item_id} 维度 {ed.dimension!r} 的 sub_items 为空 — "
                    "Q4 禁止整维度豁免"
                )
            bucket = result.setdefault(para, {}).setdefault(ed.dimension, set())
            for sub in ed.sub_items:
                if not sub or not sub.strip():
                    raise ExemptionBuildError(
                        f"item {item.item_id} 维度 {ed.dimension!r} 含空白 sub_item"
                    )
                bucket.add(sub)
    return result
```

**运行**:
```bash
python -m pytest tests/test_evaluator_exemption.py -v
```
**期望**:4 passed

---

### Task 3:追加 `build_exemption_map` 校验测试(Q4 硬约束等)

**文件**:`tests/test_evaluator_exemption.py` 追加

```python


# ===================== build_exemption_map 校验 =====================

def test_build_rejects_non_contract():
    """非 CreativeContract → TypeError"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    with pytest.raises(TypeError):
        build_exemption_map({"preserve_list": []})  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        build_exemption_map(None)  # type: ignore[arg-type]


def test_build_item_no_exempt_dimensions_contributes_nothing():
    """preserve_item 未声明任何豁免 → map 不含该段落键"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract([
        _make_item("#1", paragraph_index=4, exempts=[]),
    ])
    m = build_exemption_map(c)
    assert 4 not in m
    assert m == {}


def test_build_multiple_dimensions_same_item():
    """同 item 多维度 → 各自独立"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract([
        _make_item("#1", paragraph_index=1, exempts=[
            ("维度A", ["a1", "a2"]),
            ("维度B", ["b1"]),
        ]),
    ])
    m = build_exemption_map(c)
    assert m[1]["维度A"] == {"a1", "a2"}
    assert m[1]["维度B"] == {"b1"}


def test_build_duplicate_sub_items_deduped():
    """同 (para, dim) 重复 sub_item → 集合去重"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract([
        _make_item("#1", paragraph_index=0, char_start=0, char_end=5,
                   exempts=[("X", ["共同项"])]),
        _make_item("#2", paragraph_index=0, char_start=10, char_end=15,
                   exempts=[("X", ["共同项"])]),
    ])
    m = build_exemption_map(c)
    assert m[0]["X"] == {"共同项"}
```

**运行**:
```bash
python -m pytest tests/test_evaluator_exemption.py -v
```
**期望**:8 passed(4 + 4 新)

---

### Task 4:`is_exempt` 测试(预期 FAIL)+ 实现

**文件 a**:测试追加到 `tests/test_evaluator_exemption.py`

```python


# ===================== is_exempt 查询 =====================

def test_is_exempt_hit():
    """命中 (para, dim, sub) → True"""
    from core.inspiration.evaluator_exemption import build_exemption_map, is_exempt

    c = _make_contract([
        _make_item("#1", paragraph_index=2, exempts=[("情绪一致性", ["心理旁白"])])
    ])
    m = build_exemption_map(c)
    assert is_exempt(m, paragraph_index=2, dimension="情绪一致性", sub_item="心理旁白") is True


def test_is_exempt_paragraph_miss():
    """段落未豁免 → False"""
    from core.inspiration.evaluator_exemption import build_exemption_map, is_exempt

    c = _make_contract([
        _make_item("#1", paragraph_index=2, exempts=[("X", ["a"])])
    ])
    m = build_exemption_map(c)
    assert is_exempt(m, paragraph_index=5, dimension="X", sub_item="a") is False


def test_is_exempt_dimension_miss():
    """段落命中但维度未豁免 → False"""
    from core.inspiration.evaluator_exemption import build_exemption_map, is_exempt

    c = _make_contract([
        _make_item("#1", paragraph_index=2, exempts=[("X", ["a"])])
    ])
    m = build_exemption_map(c)
    assert is_exempt(m, 2, "Y", "a") is False


def test_is_exempt_sub_item_miss():
    """段落+维度命中但 sub_item 未列 → False"""
    from core.inspiration.evaluator_exemption import build_exemption_map, is_exempt

    c = _make_contract([
        _make_item("#1", paragraph_index=2, exempts=[("X", ["a"])])
    ])
    m = build_exemption_map(c)
    assert is_exempt(m, 2, "X", "b") is False


def test_is_exempt_on_empty_map():
    """空 map → 恒 False"""
    from core.inspiration.evaluator_exemption import is_exempt

    assert is_exempt({}, 0, "X", "a") is False
```

**运行**:
```bash
python -m pytest tests/test_evaluator_exemption.py -k is_exempt -v
```
**期望**:5 FAIL(`is_exempt` 未定义)

**文件 b**:实现追加到 `core/inspiration/evaluator_exemption.py`

```python


def is_exempt(
    exemption_map: ExemptionMap,
    paragraph_index: int,
    dimension: str,
    sub_item: str,
) -> bool:
    """查询 (段落, 维度, 子项) 是否被豁免。

    任一 key 不存在 → False(未豁免,评估师照常打分)。
    """
    dims = exemption_map.get(paragraph_index)
    if not dims:
        return False
    subs = dims.get(dimension)
    if not subs:
        return False
    return sub_item in subs
```

**运行**:
```bash
python -m pytest tests/test_evaluator_exemption.py -k is_exempt -v
```
**期望**:5 passed

---

### Task 5:`format_exemption_report` 测试 + 实现

**文件 a**:测试追加

```python


# ===================== format_exemption_report =====================

def test_format_empty_map():
    """空 map → 明示无豁免"""
    from core.inspiration.evaluator_exemption import format_exemption_report

    t = format_exemption_report({})
    assert "本章无豁免" in t


def test_format_contains_all_keys():
    """报告应包含所有 paragraph / dimension / sub_item 标识"""
    from core.inspiration.evaluator_exemption import build_exemption_map, format_exemption_report

    c = _make_contract([
        _make_item("#1", paragraph_index=3, exempts=[("视角", ["切焦"])]),
        _make_item("#2", paragraph_index=7, exempts=[("节奏", ["短句", "停顿"])]),
    ])
    t = format_exemption_report(build_exemption_map(c))
    for s in ("3", "7", "视角", "切焦", "节奏", "短句", "停顿"):
        assert s in t, f"报告缺 {s!r}"


def test_format_paragraphs_sorted_ascending():
    """段落按 index 升序输出,利于作者阅读"""
    from core.inspiration.evaluator_exemption import build_exemption_map, format_exemption_report

    c = _make_contract([
        _make_item("#1", paragraph_index=9, exempts=[("A", ["x"])]),
        _make_item("#2", paragraph_index=2, exempts=[("B", ["y"])]),
    ])
    t = format_exemption_report(build_exemption_map(c))
    idx_2 = t.find("段落 2")
    idx_9 = t.find("段落 9")
    assert idx_2 != -1 and idx_9 != -1
    assert idx_2 < idx_9, "段落 2 应在段落 9 之前出现"
```

**运行**:
```bash
python -m pytest tests/test_evaluator_exemption.py -k format_ -v
```
**期望**:3 FAIL(`format_exemption_report` 未定义)

**文件 b**:实现追加

```python


def format_exemption_report(exemption_map: ExemptionMap) -> str:
    """生成可读的中文豁免报告。段落升序,维度按名称升序,子项按名称升序。"""
    if not exemption_map:
        return "(本章无豁免)"

    lines = ["本章评估师豁免清单:"]
    for para in sorted(exemption_map.keys()):
        lines.append(f"  段落 {para}:")
        dims = exemption_map[para]
        for dim in sorted(dims.keys()):
            subs = sorted(dims[dim])
            lines.append(f"    - {dim}:{', '.join(subs)}")
    return "\n".join(lines)
```

**运行**:
```bash
python -m pytest tests/test_evaluator_exemption.py -k format_ -v
```
**期望**:3 passed

---

### Task 6:追加导出到包 `__init__.py`

**文件**:`core/inspiration/__init__.py`

**做法**:在文件最末追加(不改既有行)。若该文件已有 `__all__` 列表且显式管理,则在对应位置把 3 个符号追加进去;若只是平铺 `from .xxx import Y` 形式,按既有风格追加 3 行 import。以下以"追加 3 行 import"风格为例;若现场格式不同,opencode 参考 P1-2 在此文件追加 dispatcher 相关符号时采用的风格,保持一致:

```python

# ===================== P1-7 追加:评估师豁免 =====================
from .evaluator_exemption import (
    ExemptionBuildError,
    ExemptionMap,
    build_exemption_map,
    is_exempt,
    format_exemption_report,
)
```

若 `__init__.py` 维护了 `__all__`,则同时把 5 个符号名加进末尾。**只追加,不删不重排。**

**运行**:
```bash
python -c "
from core.inspiration import (
    build_exemption_map, is_exempt, format_exemption_report,
    ExemptionMap, ExemptionBuildError,
)
print('pkg export OK')
"
```
**期望**:`pkg export OK`

---

### Task 7:端到端 smoke + 全量回归

**文件**:在 `tests/test_evaluator_exemption.py` 追加

```python


# ===================== 端到端 smoke =====================

def test_end_to_end_contract_to_report():
    """契约 → build → is_exempt → format,全链路贯通"""
    from core.inspiration.evaluator_exemption import (
        build_exemption_map,
        is_exempt,
        format_exemption_report,
    )

    c = _make_contract([
        _make_item("#1", paragraph_index=4, char_start=10, char_end=50,
                   exempts=[("人物动机连贯性", ["突兀转折"])]),
        _make_item("#2", paragraph_index=4, char_start=60, char_end=90,
                   exempts=[("人物动机连贯性", ["情绪跳脱"]),
                            ("节奏", ["停顿不足"])]),
    ])
    m = build_exemption_map(c)

    assert is_exempt(m, 4, "人物动机连贯性", "突兀转折") is True
    assert is_exempt(m, 4, "人物动机连贯性", "情绪跳脱") is True
    assert is_exempt(m, 4, "节奏", "停顿不足") is True
    assert is_exempt(m, 4, "节奏", "过长铺陈") is False
    assert is_exempt(m, 5, "节奏", "停顿不足") is False

    text = format_exemption_report(m)
    assert "段落 4" in text
    assert "突兀转折" in text and "情绪跳脱" in text
    assert "停顿不足" in text
```

**运行**:
```bash
python -m pytest tests/test_evaluator_exemption.py -v
```
**期望**:15 passed(全量新增)

```bash
python -m pytest tests/ --tb=no -q 2>&1 | tail -3
```
**期望**:
- 若 P1-6 已先完成:`599 passed, 1 skipped`(584 + 15)
- 若 P1-6 未做:`586 passed, 1 skipped`(571 + 15)

---

## 4. 文件最终结构

```
core/inspiration/
  evaluator_exemption.py      新建
    ExemptionMap (TypeAlias)
    ExemptionBuildError
    build_exemption_map(contract) -> ExemptionMap
    is_exempt(map, paragraph_index, dimension, sub_item) -> bool
    format_exemption_report(map) -> str

  __init__.py                 追加 5 个符号的 re-export

tests/
  test_evaluator_exemption.py  新建,15 用例
```

---

## 5. 自检命令

```bash
cd "D:/动画/众生界"

echo "===== P1-7 自检开始 ====="

# S1 语法
python -c "import ast; ast.parse(open('core/inspiration/evaluator_exemption.py',encoding='utf-8').read())" \
  && echo "PASS-S1 语法 OK" || echo "FAIL-S1"

# E1 包导出
python -c "
from core.inspiration import (
    build_exemption_map, is_exempt, format_exemption_report,
    ExemptionMap, ExemptionBuildError,
)
print('pkg export 5 OK')
" && echo "PASS-E1 包导出" || echo "FAIL-E1"

# Q4 硬约束(空 sub_items 必须 raise)
python -c "
from core.inspiration.creative_contract import (
    Aspects, CreativeContract, ExemptDimension, PreserveItem, Scope,
)
from core.inspiration.evaluator_exemption import build_exemption_map, ExemptionBuildError

# 绕过 ExemptDimension.validate() 构造非法状态(直接访问字段)
ed = ExemptDimension(dimension='X', sub_items=['ok'])
ed.sub_items.clear()  # 构造非法
p = PreserveItem(
    item_id='#1',
    scope=Scope(paragraph_index=0, char_start=0, char_end=5),
    applied_constraint_id=None,
    rationale='r',
    evaluator_risk=[],
    aspects=Aspects(preserve=['e']),
    exempt_dimensions=[ed],
)
c = CreativeContract(
    contract_id='cc_20260420_abcdef',
    chapter_ref='r',
    created_at='2026-04-20T03:30:00+08:00',
    preserve_list=[p],
)
try:
    build_exemption_map(c)
    print('FAIL-Q4: 未 raise')
    raise SystemExit(1)
except ExemptionBuildError as e:
    if 'Q4' in str(e) or '整维度' in str(e) or '空' in str(e):
        print('PASS-Q4 空 sub_items 正确 raise')
    else:
        print(f'PASS-Q4-weak: raise 但错误信息未显式提 Q4:{e}')
" && echo "PASS-Q4 done" || echo "FAIL-Q4"

# D1 无第三方依赖
python -c "
import ast, pathlib
src = pathlib.Path('core/inspiration/evaluator_exemption.py').read_text(encoding='utf-8')
tree = ast.parse(src)
banned = {'pydantic','attrs','jinja2','requests','anthropic','openai','qdrant_client','numpy','pandas'}
for node in ast.walk(tree):
    if isinstance(node,(ast.Import,ast.ImportFrom)):
        mod = node.module if isinstance(node,ast.ImportFrom) else node.names[0].name
        top = (mod or '').split('.')[0]
        if top in banned:
            raise SystemExit(f'禁用依赖:{top}')
print('stdlib+local only OK')
" && echo "PASS-D1 stdlib-only" || echo "FAIL-D1"

# T1 模块 pytest
python -m pytest tests/test_evaluator_exemption.py --tb=short -q 2>&1 | tail -3 | tee /tmp/p1-7_mod.txt
grep -qE "^15 passed" /tmp/p1-7_mod.txt && echo "PASS-T1 模块 15/15" || echo "FAIL-T1"

# R1 全量回归(检两种基线)
python -m pytest tests/ --tb=no -q 2>&1 | tail -1 | tee /tmp/p1-7_all.txt
if grep -qE "^599 passed" /tmp/p1-7_all.txt; then
    echo "PASS-R1 全量 599(P1-6 在前)"
elif grep -qE "^586 passed" /tmp/p1-7_all.txt; then
    echo "PASS-R1 全量 586(独立执行,P1-6 未做)"
else
    echo "FAIL-R1 全量数字异常"
fi

# P 保护性
for f in creative_contract.py dispatcher.py constraint_library.py variant_generator.py \
         escalation_dialogue.py workflow_bridge.py appraisal_agent.py; do
  path="core/inspiration/$f"
  [ ! -f "$path" ] && echo "SKIP-P $f 不存在" && continue
  # 允许 P1-6 对 escalation_dialogue.py 的追加 —— 检查不是整文件重写即可;此处仅警示,不判死
  echo "INFO $f 状态:$(git status --short "$path" | head -1 || echo '(clean)')"
done

# JSON 数据不得改
status=$(git status --short "config/dimensions/anti_template_constraints.json" 2>/dev/null | head -1)
if [ -z "$status" ]; then
  echo "PASS-J1 JSON 数据未动"
else
  echo "FAIL-J1 JSON 被改"
fi

# G1 git HEAD 未动
hash=$(git log -1 --format=%h)
[ "$hash" = "8365fe21a" ] && echo "PASS-G1 HEAD 未动" || echo "FAIL-G1 HEAD 改变"

echo "===== P1-7 自检结束 ====="
```

任一 `FAIL-` → **立即停止**,保留现场报告 Claude。

---

## 6. 完成判据

- [ ] `core/inspiration/evaluator_exemption.py` 新建 + 语法 PASS
- [ ] 15 新测试全 PASS
- [ ] `core/inspiration/__init__.py` 可导出 5 个新符号
- [ ] Q4 硬约束:空 sub_items 触发 `ExemptionBuildError`
- [ ] stdlib-only(仅标准库 + 本地 creative_contract)
- [ ] 全量 pytest 符合 599 或 586(看 P1-6 是否在前)
- [ ] `creative_contract.py` 未改
- [ ] HEAD 仍 `8365fe21a`,未 commit

---

## 7. 完成后

- 不 git commit / add(变更悬空)
- 在 `docs/ROADMAP_众生界v2实施_20260419.md` §3.2 P1-7 改为 `🟢 完成`(追加时间线)
- 继续过夜批次下一任务(若有)或等待作者
