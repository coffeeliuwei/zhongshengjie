# P1-6 计划:对话升级器 — 阶段 6 三选升级

> **文档日期**:2026-04-20(Asia/Shanghai)
> **对象执行者**:opencode(GLM5)
> **计划类型**:纯追加(不改既有函数,不改签名)
> **依据**:v2 设计 §1 阶段 6 `<0.8 第 3 次 → 触发对话升级` 三选;作者 Q1/Q2/Q3/Q4 硬约束(已在 P1-1 落地)
> **路线图位置**:`docs/ROADMAP_众生界v2实施_20260419.md` §3.2 P1-6

---

## 0. 本计划的目的 — 必读

在 `core/inspiration/escalation_dialogue.py` **追加两个新公开函数**,覆盖 v2 §1 阶段 6 "整章评估 <0.8 连续第 3 次触发作者三选":

- `[a]` 撤销某条采纳建议 → 进 `rejected_list`
- `[b]` 强制通过 → 标记 `author_force_pass`,触发推翻事件回流(P2-4 管)
- `[c]` 整章重协商 → 回 5.5

**本计划只做"文本格式化 + 输入解析"纯函数层**。与 workflow / 契约写回 / 回流审计的联动由 P2-3 / P2-4 负责。

### 0.1 范围边界(不得扩张)

- ❌ 不改既有 4 个格式化函数(`format_rater_vs_evaluator_conflict` / `format_all_variants_failed` / `format_appraisal_audit` / `format_overturn_audit`)
- ❌ 不 import `core.inspiration.creative_contract`(保持本模块零依赖,仅 stdlib)
- ❌ 不读文件、不调 LLM、不写 JSON
- ❌ 不碰 workflow.py / appraisal_agent.py / evaluator_*.py
- ✅ 仅追加 2 个新函数 + 对应测试
- ✅ 仅依赖 typing + stdlib

### 0.2 产出清单

| 产出 | 路径 | 动作 |
|------|------|------|
| 实施 | `core/inspiration/escalation_dialogue.py` | **追加 2 函数**(不动旧函数) |
| 测试 | `tests/test_escalation_dialogue.py` | **追加 12 测试**(不动旧 7 测试) |

### 0.3 新函数 API 契约(不得偏离)

```python
def format_stage6_three_choice(
    item_summaries: List[Dict[str, str]],
    failed_dimensions: List[str],
    consecutive_fail_count: int,
) -> str:
    """
    阶段 6 整章评估连续 3 次 <0.8 触发的三选升级对话。

    Args:
        item_summaries: 当前契约的 preserve_list 摘要,
                        每项 {"item_id": "#1", "summary": "采纳的创意一句话"}
        failed_dimensions: 持续不过的评估维度名(例 ["人物动机连贯性","情绪一致性"])
        consecutive_fail_count: 连续失败次数(触发时固定为 3)

    Returns:
        三选结构化对话文本,末尾含 "[a]/[b]/[c]" 选项
    """

def parse_stage6_choice(
    user_input: str,
) -> Tuple[str, Optional[str]]:
    """
    解析作者对 format_stage6_three_choice 的回复。

    Args:
        user_input: 作者原文输入,允许前后空白、大小写不敏感

    Returns:
        (choice, item_id)
        - choice ∈ {"revoke", "force_pass", "renegotiate"}
        - choice == "revoke" 时,item_id 必须形如 "#N"
        - 其余 choice,item_id 为 None

    Raises:
        ValueError: 输入无法识别、或 revoke 未带合法 #N
    """
```

---

## 1. 执行前真实状态

### 1.1 当前 `escalation_dialogue.py`

```
138 行;4 公开函数(N6 已汉化);无第三方依赖;无 __all__。
```

### 1.2 pytest 基线(P1-6 开工前必须与上一步一致)

```
tests/test_escalation_dialogue.py   7 passed(pytest --collect-only 确认)
tests/ 全量                         571 passed, 1 skipped(P1-4 完成后)
```

如全量不是 571 → **立即停止**报告 Claude。

---

## 2. opencode 执行规则(不可违反)

### 2.1 允许

- 追加代码到 `escalation_dialogue.py` 末尾
- 追加测试到 `tests/test_escalation_dialogue.py` 末尾
- 运行 pytest / python -c 自检

### 2.2 禁止

- 不得修改既有 4 函数任何一行
- 不得删除/重命名既有 4 测试任何一个
- 不得 git add / git commit / git push(整包保持未 commit)
- 不得引入 pydantic / attrs / dataclasses_json / 任何第三方库(stdlib-only)
- 不得编辑 `.archived/` 与 `.vectorstore/`
- 不得跳过 Task 的 "运行测试验证失败" 步骤(TDD 铁律)

### 2.3 TDD 严格执行

每个 Task 必须:写失败测试 → 跑 pytest 看到 FAIL → 写最小实现 → 跑 pytest 看到 PASS。不得反过来、不得并合、不得跳步。

---

## 3. 执行步骤

### Task 1:追加 3-choice 基础格式化测试(预期 FAIL)

**文件**:`tests/test_escalation_dialogue.py` 末尾追加

```python


# ===================== P1-6 追加:阶段 6 三选升级 =====================

def test_stage6_three_choice_contains_warning_header():
    """三选格式化:包含警告头"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[
            {"item_id": "#1", "summary": "红裙少女的侧脸近景"},
            {"item_id": "#3", "summary": "冰镜倒映回廊"},
        ],
        failed_dimensions=["人物动机连贯性", "情绪一致性"],
        consecutive_fail_count=3,
    )
    assert "警告" in result
    assert "阶段 6" in result or "整章评估" in result


def test_stage6_three_choice_lists_all_items():
    """三选格式化:列出所有 preserve_item 供作者选择撤销"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[
            {"item_id": "#1", "summary": "A 摘要"},
            {"item_id": "#2", "summary": "B 摘要"},
            {"item_id": "#7", "summary": "C 摘要"},
        ],
        failed_dimensions=["维度X"],
        consecutive_fail_count=3,
    )
    for iid in ("#1", "#2", "#7"):
        assert iid in result
    assert "A 摘要" in result and "B 摘要" in result and "C 摘要" in result


def test_stage6_three_choice_lists_failed_dimensions():
    """三选格式化:列出持续失败维度"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[{"item_id": "#1", "summary": "x"}],
        failed_dimensions=["节奏", "情绪"],
        consecutive_fail_count=3,
    )
    assert "节奏" in result
    assert "情绪" in result


def test_stage6_three_choice_contains_three_options():
    """三选格式化:三个选项 a/b/c 都在"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[{"item_id": "#1", "summary": "x"}],
        failed_dimensions=["X"],
        consecutive_fail_count=3,
    )
    assert "[a]" in result and "[b]" in result and "[c]" in result
    assert "撤销" in result
    assert "强制通过" in result
    assert "重协商" in result or "回 5.5" in result


def test_stage6_three_choice_mentions_force_pass_consequence():
    """三选格式化:[b] 强制通过必须提醒'推翻事件回流'"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[{"item_id": "#1", "summary": "x"}],
        failed_dimensions=["X"],
        consecutive_fail_count=3,
    )
    assert "author_force_pass" in result or "推翻事件" in result


def test_stage6_three_choice_shows_fail_count():
    """三选格式化:显示连续失败次数"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[{"item_id": "#1", "summary": "x"}],
        failed_dimensions=["X"],
        consecutive_fail_count=3,
    )
    assert "3" in result


def test_stage6_three_choice_empty_items_renders_placeholder():
    """三选格式化:preserve_list 为空时不崩,显示占位"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[],
        failed_dimensions=["X"],
        consecutive_fail_count=3,
    )
    assert "(无)" in result or "无采纳建议" in result
    assert "[a]" in result and "[b]" in result and "[c]" in result
```

**运行**:
```bash
python -m pytest tests/test_escalation_dialogue.py::test_stage6_three_choice_contains_warning_header -v
```
**期望**:FAIL with `ImportError` 或 `AttributeError: format_stage6_three_choice`

---

### Task 2:最小实现 `format_stage6_three_choice`

**文件**:`core/inspiration/escalation_dialogue.py` 末尾追加

```python


# ===================== P1-6 追加:阶段 6 三选升级 =====================

def format_stage6_three_choice(
    item_summaries: List[Dict[str, str]],
    failed_dimensions: List[str],
    consecutive_fail_count: int,
) -> str:
    """格式化阶段 6 整章评估连续失败触发的三选升级对话。

    v2 设计 §1 阶段 6 `<0.8 第 3 次 → 触发对话升级`:
      [a] 撤销某条采纳建议(进 rejected_list)
      [b] 强制通过(标 author_force_pass,推翻事件回流)
      [c] 整章重协商(回 5.5)

    Args:
        item_summaries: preserve_list 摘要,每项 {"item_id": "#N", "summary": "..."}
        failed_dimensions: 持续 <0.8 的评估维度名
        consecutive_fail_count: 连续失败次数(触发时通常为 3)

    Returns:
        可直接呈现给作者的结构化三选文本
    """
    if item_summaries:
        items_text = "\n".join(
            f"  - {it['item_id']}: {it.get('summary', '(无摘要)')}"
            for it in item_summaries
        )
    else:
        items_text = "  (无采纳建议)"

    dims_text = "、".join(failed_dimensions) if failed_dimensions else "(未列出)"

    return (
        f"⚠️ 警告:阶段 6 整章评估连续 {consecutive_fail_count} 次 <0.8\n\n"
        f"  持续不过的维度:{dims_text}\n\n"
        f"  当前采纳建议(preserve_list):\n"
        f"{items_text}\n\n"
        f"请选择处理方式:\n"
        f"  [a] 撤销某条采纳建议(进 rejected_list,回 5.6 再改写)\n"
        f"      用法示例:`a #1`\n"
        f"  [b] 强制通过(标 author_force_pass,推翻事件回流,触发审计)\n"
        f"      用法示例:`b`\n"
        f"  [c] 整章重协商(丢弃本次契约,回阶段 5.5 重来)\n"
        f"      用法示例:`c`\n"
    )
```

**运行**:
```bash
python -m pytest tests/test_escalation_dialogue.py -k stage6_three_choice -v
```
**期望**:7 passed(Task 1 的 7 条全绿)

---

### Task 3:追加解析函数测试(预期 FAIL)

**文件**:`tests/test_escalation_dialogue.py` 末尾继续追加

```python


def test_parse_revoke_with_item_id():
    """解析:'a #2' → ('revoke', '#2')"""
    from core.inspiration.escalation_dialogue import parse_stage6_choice

    assert parse_stage6_choice("a #2") == ("revoke", "#2")
    assert parse_stage6_choice("A #10") == ("revoke", "#10")
    assert parse_stage6_choice("  a   #7  ") == ("revoke", "#7")


def test_parse_force_pass():
    """解析:'b' / 'B' / 空白包围 → ('force_pass', None)"""
    from core.inspiration.escalation_dialogue import parse_stage6_choice

    assert parse_stage6_choice("b") == ("force_pass", None)
    assert parse_stage6_choice("B") == ("force_pass", None)
    assert parse_stage6_choice("  b\n") == ("force_pass", None)


def test_parse_renegotiate():
    """解析:'c' → ('renegotiate', None)"""
    from core.inspiration.escalation_dialogue import parse_stage6_choice

    assert parse_stage6_choice("c") == ("renegotiate", None)
    assert parse_stage6_choice("C") == ("renegotiate", None)


def test_parse_revoke_missing_item_id_raises():
    """解析:'a' 缺 #N → ValueError"""
    import pytest
    from core.inspiration.escalation_dialogue import parse_stage6_choice

    with pytest.raises(ValueError, match="revoke"):
        parse_stage6_choice("a")


def test_parse_revoke_bad_item_id_raises():
    """解析:'a abc' / 'a #' / 'a #abc' → ValueError"""
    import pytest
    from core.inspiration.escalation_dialogue import parse_stage6_choice

    for bad in ("a abc", "a #", "a #abc", "a 1", "a ##1"):
        with pytest.raises(ValueError):
            parse_stage6_choice(bad)


def test_parse_unknown_choice_raises():
    """解析:不在 a/b/c → ValueError"""
    import pytest
    from core.inspiration.escalation_dialogue import parse_stage6_choice

    for bad in ("", "   ", "d", "x y z", "撤销", "abc"):
        with pytest.raises(ValueError):
            parse_stage6_choice(bad)
```

**运行**:
```bash
python -m pytest tests/test_escalation_dialogue.py -k parse_ -v
```
**期望**:6 FAIL(均因 `parse_stage6_choice` 未定义)

---

### Task 4:最小实现 `parse_stage6_choice`

**文件**:`core/inspiration/escalation_dialogue.py` 末尾追加

注意:`re` 需 import。若文件头没有则顶部加 `import re`;若已有就不重复。当前文件头仅 `from typing import List, Dict, Any` — **需在顶部补** `import re` 和 `from typing import Tuple, Optional`(后者合并进既有 typing 行)。

**步骤 4.1**:编辑 import 行

```python
# 原:
from typing import List, Dict, Any
# 改为:
import re
from typing import List, Dict, Any, Tuple, Optional
```

**步骤 4.2**:在文件末尾追加

```python


_STAGE6_REVOKE_RE = re.compile(r"^a\s+(#\d+)$", re.IGNORECASE)


def parse_stage6_choice(user_input: str) -> Tuple[str, Optional[str]]:
    """解析作者对 format_stage6_three_choice 的回复。

    语法:
      'a #N'  → ('revoke', '#N')         撤销第 N 条采纳建议
      'b'     → ('force_pass', None)     强制通过
      'c'     → ('renegotiate', None)    整章重协商

    允许前后空白、字母大小写不敏感。其余一律 ValueError。
    """
    if user_input is None:
        raise ValueError("user_input 不得为 None")
    stripped = user_input.strip()
    if not stripped:
        raise ValueError("user_input 不得为空白")

    lower = stripped.lower()
    if lower == "b":
        return ("force_pass", None)
    if lower == "c":
        return ("renegotiate", None)

    # revoke 必须形如 "a #N"
    if lower == "a" or lower.startswith("a ") or lower.startswith("a\t"):
        m = _STAGE6_REVOKE_RE.match(lower)
        if not m:
            raise ValueError(
                f"revoke 格式错误,须 'a #N'(N 为正整数),实得 {user_input!r}"
            )
        return ("revoke", m.group(1))

    raise ValueError(
        f"无法识别的选择 {user_input!r};合法:'a #N' / 'b' / 'c'"
    )
```

**运行**:
```bash
python -m pytest tests/test_escalation_dialogue.py -k parse_ -v
```
**期望**:6 passed

---

### Task 5:模块全量回归

**运行**:
```bash
python -m pytest tests/test_escalation_dialogue.py -v
```
**期望**:
- 原 7 测试仍 PASS
- 新 13 测试(7 format + 6 parse)全 PASS
- 合计 20 passed

---

### Task 6:全量 pytest 回归

**运行**:
```bash
python -m pytest tests/ --tb=no -q 2>&1 | tail -3
```
**期望**:`584 passed, 1 skipped`(= 571 基线 + 13 新)

若数字 ≠ 584 → **停止**,报告 Claude。

---

## 4. 文件最终结构(自检参考)

`core/inspiration/escalation_dialogue.py`:

```
import re                           # P1-6 追加
from typing import List, Dict, Any, Tuple, Optional   # P1-6 补 Tuple/Optional

def format_rater_vs_evaluator_conflict(...)       # 既有,不改
def format_all_variants_failed(...)               # 既有,不改
def format_appraisal_audit(...)                   # 既有,不改
def format_overturn_audit(...)                    # 既有,不改

# ===================== P1-6 追加:阶段 6 三选升级 =====================
def format_stage6_three_choice(...)               # 新增
_STAGE6_REVOKE_RE = re.compile(...)               # 私有正则
def parse_stage6_choice(user_input)               # 新增
```

---

## 5. 自检命令

```bash
cd "D:/动画/众生界"

echo "===== P1-6 自检开始 ====="

# F1 语法
python -c "import ast; ast.parse(open('core/inspiration/escalation_dialogue.py',encoding='utf-8').read())" \
  && echo "PASS-S1 语法 OK" || echo "FAIL-S1"

# F2 新函数存在
python -c "
from core.inspiration.escalation_dialogue import (
    format_stage6_three_choice, parse_stage6_choice,
    format_rater_vs_evaluator_conflict, format_all_variants_failed,
    format_appraisal_audit, format_overturn_audit,
)
print('6 函数全部可导入')
" && echo "PASS-M1 函数齐全" || echo "FAIL-M1"

# F3 解析基础用例
python -c "
from core.inspiration.escalation_dialogue import parse_stage6_choice
assert parse_stage6_choice('a #3') == ('revoke', '#3')
assert parse_stage6_choice('b') == ('force_pass', None)
assert parse_stage6_choice('c') == ('renegotiate', None)
print('3 选项解析 OK')
" && echo "PASS-P1 解析 smoke" || echo "FAIL-P1"

# F4 格式化含关键字
python -c "
from core.inspiration.escalation_dialogue import format_stage6_three_choice
t = format_stage6_three_choice(
    item_summaries=[{'item_id':'#1','summary':'x'}],
    failed_dimensions=['节奏'],
    consecutive_fail_count=3,
)
assert '[a]' in t and '[b]' in t and '[c]' in t
assert 'author_force_pass' in t or '推翻事件' in t
assert '节奏' in t and '#1' in t
print('format smoke OK')
" && echo "PASS-F1 format smoke" || echo "FAIL-F1"

# F5 D1 无第三方依赖
python -c "
import ast, pathlib
src = pathlib.Path('core/inspiration/escalation_dialogue.py').read_text(encoding='utf-8')
tree = ast.parse(src)
banned = {'pydantic','attrs','jinja2','requests','anthropic','openai','qdrant_client'}
for node in ast.walk(tree):
    if isinstance(node,(ast.Import,ast.ImportFrom)):
        mod = node.module if isinstance(node,ast.ImportFrom) else node.names[0].name
        top = (mod or '').split('.')[0]
        if top in banned:
            raise SystemExit(f'禁用依赖:{top}')
print('stdlib-only OK')
" && echo "PASS-D1 stdlib-only" || echo "FAIL-D1"

# F6 模块 pytest
python -m pytest tests/test_escalation_dialogue.py --tb=no -q 2>&1 | tail -1 | tee /tmp/p1-6_mod.txt
grep -q "^20 passed" /tmp/p1-6_mod.txt && echo "PASS-T1 模块 20/20" || echo "FAIL-T1 数量不对"

# F7 全量
python -m pytest tests/ --tb=no -q 2>&1 | tail -1 | tee /tmp/p1-6_all.txt
grep -q "^584 passed" /tmp/p1-6_all.txt && echo "PASS-R1 全量 584 passed" || echo "FAIL-R1"

# F8 保护性
for f in creative_contract.py dispatcher.py constraint_library.py variant_generator.py \
         workflow_bridge.py appraisal_agent.py; do
  path="core/inspiration/$f"
  [ ! -f "$path" ] && echo "SKIP-P $f 不存在" && continue
  # 既有 P1-2 dispatcher.py 和 P1-1 creative_contract.py 是 untracked,允许未改动(status 仍是 ??)
  diffcnt=$(git diff --stat "$path" 2>/dev/null | wc -l)
  if [ "$diffcnt" = "0" ]; then
    echo "PASS-P $f 未改动"
  else
    echo "FAIL-P $f 被改: diff 非空"
  fi
done

# F9 git HEAD 未动
hash=$(git log -1 --format=%h)
[ "$hash" = "8365fe21a" ] && echo "PASS-G1 HEAD 未动" || echo "FAIL-G1 HEAD 改变"

echo "===== P1-6 自检结束 ====="
```

任一 `FAIL-` → **立即停止,不得声称完成**,保留现场报告 Claude。

---

## 6. 完成判据(全部 ✅ 才算完成)

- [ ] `format_stage6_three_choice` 可导入且 4 关键字段全在
- [ ] `parse_stage6_choice` 三路径正确 + 非法输入 ValueError
- [ ] `tests/test_escalation_dialogue.py` 20 passed(7 旧 + 13 新)
- [ ] `tests/` 全量 **584 passed, 1 skipped**
- [ ] 既有 4 函数未改任何一行
- [ ] stdlib-only,无第三方依赖
- [ ] HEAD 仍 `8365fe21a`,未 commit
- [ ] §5 自检全 `PASS-`

---

## 7. 完成后

- 不 git commit、不 git add(变更悬空)
- 在 `docs/ROADMAP_众生界v2实施_20260419.md` §3.2 把 P1-6 状态改为 `🟢 完成`(追加一行时间线即可)
- 继续执行过夜批次的下一任务(若在批次里)
