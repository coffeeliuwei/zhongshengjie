# 过夜批次调度器 v2(P1-6 + P1-7)

> **文档日期**:2026-04-20 03:30(Asia/Shanghai)
> **对象执行者**:opencode(GLM5)
> **启动条件**:作者睡眠 + `git HEAD = 8365fe21a` + 工作区含 P1-1/P1-2/P1-4 未 commit 产物
> **批次目的**:在作者不在线期间安全推进 P1-6 + P1-7,两者均为**纯追加/纯新建**,无级联迁移风险

---

## 0. 本文是什么

调度脚本,**不是**新实施计划。它指定两个独立计划的执行顺序、前置核验、失败回退规则。opencode 看这份就够,不必自己排序。

要执行的 2 个计划:

1. **Part A** — `docs/计划_P1-6_escalation_3choice_20260420.md`(escalation_dialogue.py 追加 2 函数 + 13 测试)
2. **Part B** — `docs/计划_P1-7_evaluator_exemption_20260420.md`(evaluator_exemption.py 新建 + 15 测试)

两者可独立跑通,**建议顺序为 A → B**(因 P1-7 §5 自检预期值以 A 完成为前提,且 Part B 为纯新建,风险更低,放最后可)。

---

## 1. 前置门禁(Step 0)— 必通过才能进 Part A

```bash
cd "D:/动画/众生界"

echo "===== Step 0 前置门禁 ====="

# 0.1 git HEAD 必须还是 8365fe21a(所有 P1-1/P1-2/P1-4 产物都悬空,不得被 commit)
hash=$(git log -1 --format=%h)
if [ "$hash" != "8365fe21a" ]; then
    echo "ABORT: HEAD 不是 8365fe21a(实际 $hash)→ 拒绝启动,报告作者"
    exit 1
fi
echo "OK HEAD=$hash"

# 0.2 P1-1/P1-2/P1-4 关键文件必须存在
for f in core/inspiration/creative_contract.py \
         core/inspiration/dispatcher.py \
         core/inspiration/constraint_library.py \
         core/inspiration/escalation_dialogue.py; do
    if [ ! -f "$f" ]; then
        echo "ABORT: 缺关键前置文件 $f"
        exit 1
    fi
done
echo "OK 4 关键文件齐全"

# 0.3 基线 pytest 必须是 571 passed
baseline=$(python -m pytest tests/ --tb=no -q 2>&1 | tail -1)
echo "基线:$baseline"
if ! echo "$baseline" | grep -qE "^571 passed"; then
    echo "ABORT: 基线非 571 passed(P1-4 未完成或有未知回归)→ 报告作者"
    exit 1
fi
echo "OK baseline=571 passed"

# 0.4 Part A 关键前置:escalation_dialogue.py 既有 4 函数可导入,测试 7 passed
python -c "
from core.inspiration.escalation_dialogue import (
    format_rater_vs_evaluator_conflict,
    format_all_variants_failed,
    format_appraisal_audit,
    format_overturn_audit,
)
print('既有 4 函数 OK')
" || { echo "ABORT: 既有 4 函数不全"; exit 1; }

python -m pytest tests/test_escalation_dialogue.py --tb=no -q 2>&1 | tail -1 | grep -qE "^7 passed" \
    || { echo "ABORT: 既有 7 测试有失败"; exit 1; }
echo "OK Part A 前置:既有 7/7"

# 0.5 Part B 关键前置:creative_contract 5 类型可导入
python -c "
from core.inspiration.creative_contract import (
    Aspects, CreativeContract, ExemptDimension, PreserveItem, Scope,
)
print('P1-1 类型 OK')
" || { echo "ABORT: P1-1 类型缺失"; exit 1; }

# 0.6 不应已有 evaluator_exemption.py
if [ -f "core/inspiration/evaluator_exemption.py" ]; then
    echo "ABORT: evaluator_exemption.py 已存在(不应该),先删除或改名再跑"
    exit 1
fi
echo "OK evaluator_exemption.py 尚未存在"

echo "===== Step 0 全部 PASS,可进 Part A ====="
```

**任一 `ABORT` → 立刻停止过夜批次,保留现场,等作者回来。不得尝试修复后继续。**

---

## 2. Part A — 执行 P1-6

```
读并执行:docs/计划_P1-6_escalation_3choice_20260420.md
```

严格按该计划 §3 Task 1~6 的 TDD 顺序执行,每 Task 完成时的 pytest 结果必须符合其"期望"行。

**Part A 完成判据**(同 P1-6 计划 §6):

- [ ] `tests/test_escalation_dialogue.py` **20 passed**(7 旧 + 13 新)
- [ ] `tests/` 全量 **584 passed, 1 skipped**
- [ ] P1-6 §5 自检全 `PASS-`
- [ ] HEAD 仍 `8365fe21a`

**Part A 失败处理**:

- 若某 Task 的 pytest FAIL 且无法通过"改回最小实现"恢复 → **停止**,记下最后失败 Task 号 + 错误文本 + 当时 pytest 输出,写入 `docs/m7_artifacts/overnight_v2_failure_log_20260420.txt`,不继续 Part B。
- 不得 `git reset` / `git checkout` / `git stash` / `git clean` / `git commit`,保留现场。
- 若 Part A 失败但已误改 `escalation_dialogue.py`:把新增区段(`# ===================== P1-6 追加`以下)整块删掉,恢复文件为 138 行状态;import 行若已改则回退。不得改任何既有函数。

---

## 3. Part A → Part B 之间的校验闸门(Step A→B)

```bash
echo "===== Step A→B 闸门 ====="

# A.1 Part A 的模块测试必须 20/20
python -m pytest tests/test_escalation_dialogue.py --tb=no -q 2>&1 | tail -1 | grep -qE "^20 passed" \
    || { echo "ABORT: Part A 模块测试未 20/20"; exit 1; }

# A.2 全量必须 584
python -m pytest tests/ --tb=no -q 2>&1 | tail -1 | grep -qE "^584 passed" \
    || { echo "ABORT: 全量 pytest 非 584 passed"; exit 1; }

# A.3 Part B 前置:evaluator_exemption.py 仍不存在(Part A 不该动它)
if [ -f "core/inspiration/evaluator_exemption.py" ]; then
    echo "ABORT: Part A 误创 evaluator_exemption.py"
    exit 1
fi

# A.4 HEAD 仍未动
hash=$(git log -1 --format=%h)
[ "$hash" = "8365fe21a" ] || { echo "ABORT: HEAD 已变 $hash"; exit 1; }

echo "===== Step A→B PASS,可进 Part B ====="
```

任一 `ABORT` → 停,不碰 Part B。

---

## 4. Part B — 执行 P1-7

```
读并执行:docs/计划_P1-7_evaluator_exemption_20260420.md
```

严格按该计划 §3 Task 1~7 TDD。

**Part B 完成判据**(同 P1-7 计划 §6):

- [ ] `core/inspiration/evaluator_exemption.py` 新建 15 用例全 PASS
- [ ] 全量 pytest **599 passed, 1 skipped**(= 584 + 15)
- [ ] `core/inspiration/__init__.py` 追加 5 个符号导出
- [ ] Q4 硬约束校验 PASS
- [ ] HEAD 仍 `8365fe21a`

**Part B 失败处理**:

- 纯新建文件,回退极简:把 `core/inspiration/evaluator_exemption.py`、`tests/test_evaluator_exemption.py` **删除**;回退 `core/inspiration/__init__.py` 末尾追加的 import 段;保留 `docs/m7_artifacts/overnight_v2_failure_log_20260420.txt` 记录。
- Part A 已完成的成果(escalation_dialogue.py / 测试)**不得回滚**。
- 停止批次,等作者。

---

## 5. Step Final — 全局合并核验

```bash
echo "===== Step Final 合并核验 ====="

# F.1 全量 pytest 应为 599
python -m pytest tests/ --tb=no -q 2>&1 | tail -1 | tee /tmp/overnight_v2_final.txt
grep -qE "^599 passed" /tmp/overnight_v2_final.txt || { echo "ABORT: 合并后非 599 passed"; exit 1; }

# F.2 四包导入冒烟(v2 灵感引擎新层全部通路)
python -c "
from core.inspiration import (
    # P1-1
    CreativeContract, PreserveItem, ExemptDimension, Scope, Aspects,
    RejectedItem, NegotiationTurn, WriterAssignment,
    generate_contract_id, ContractValidationError,
    # P1-2(若 __init__ 已导出)
)
from core.inspiration.dispatcher import dispatch as _d_dispatch
from core.inspiration.constraint_library import ConstraintLibrary
from core.inspiration.escalation_dialogue import (
    format_stage6_three_choice, parse_stage6_choice,
)
from core.inspiration.evaluator_exemption import (
    build_exemption_map, is_exempt, format_exemption_report,
    ExemptionMap, ExemptionBuildError,
)
print('v2 全新层导入 OK')
" && echo "PASS-I1 全链路导入 OK" || echo "FAIL-I1"

# F.3 HEAD 未动
hash=$(git log -1 --format=%h)
[ "$hash" = "8365fe21a" ] && echo "PASS-G-final HEAD 未动" || echo "FAIL-G-final HEAD 变了"

# F.4 未 commit
staged=$(git diff --cached --name-only | wc -l)
[ "$staged" = "0" ] && echo "PASS-C-final 未 staged" || echo "FAIL-C-final 有 staged: $staged 文件"

# F.5 未触及 .archived / .vectorstore
touched=$(git status --short | grep -E '^\s*[A-Z?]+\s+\.archived/|^\s*[A-Z?]+\s+\.vectorstore/' | wc -l)
[ "$touched" = "0" ] && echo "PASS-Safe 未碰归档目录" || echo "FAIL-Safe 动了归档目录($touched 条)"

echo "===== Step Final 结束 ====="
```

---

## 6. 失败落地规范

过夜批次任意 ABORT → opencode 必须:

1. 落地日志到 `docs/m7_artifacts/overnight_v2_failure_log_20260420.txt`,包含:
   - 失败发生的 Step / Part / Task 号
   - 失败时 pytest 完整 tail -30
   - `git status --short` 当时输出
   - `git log -1 --format='%h %s'` 当时输出
2. **不得自行恢复或重试超过 1 次**。超过 1 次失败即停止整批。
3. **不得 git commit / add / reset / stash / clean / checkout**。
4. 不得编辑本文件以及两份实施计划(P1-6/P1-7)。

---

## 7. 成功落地规范

全流程 PASS 后 opencode 只需:

1. 写成功日志 `docs/m7_artifacts/overnight_v2_success_log_20260420.txt`,含:
   - Step 0 / A / A→B / B / Final 各阶段 pytest 尾行
   - 新增 / 修改的文件清单(用 `git status --short` 即可)
   - 结束时 Shanghai 时间戳:`TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M:%S %Z'`
2. **不 git commit**,让作者起床自己决定。
3. 在 `docs/ROADMAP_众生界v2实施_20260419.md` §3.2 表格把 P1-6、P1-7 状态改 `🟢 完成`,并在 §5 时间线追加两行:
   - `| 2026-04-20 | opencode | P1-6 escalation 三选完成 | ...`
   - `| 2026-04-20 | opencode | P1-7 evaluator 豁免数据层完成 | ...`

---

## 8. 不做什么(硬边界)

| 任务 | 是否在本批次 | 原因 |
|------|-------------|------|
| P1-3 connoisseur SKILL.md 重写 | ❌ 不做 | 非代码,需作者判断 prompt 质量,不适合过夜无人值守 |
| P1-5 variant_generator 删除 | ❌ 不做 | 级联影响 workflow_bridge 等多处,夜间无人值守风险过高 |
| 任何 P2 集成 | ❌ 不做 | 需 P1 全部完成才能串联 |
| git commit | ❌ 不做 | 作者未授权 |
| 修改 creative_contract.py | ❌ 不做 | P1-1 已定型,任何变更需重审 |
| .archived / .vectorstore | ❌ 不动 | 作者硬规则 |

---

## 9. 预计耗时

- Step 0:1 分钟
- Part A(P1-6):20-30 分钟(2 函数 + 13 测试)
- Step A→B:1 分钟
- Part B(P1-7):25-35 分钟(1 模块 + 15 测试)
- Step Final:1 分钟

**总计 50-70 分钟。** 作者起床前完成可能性极高。

---

## 10. 入口命令(opencode 起步)

```bash
cd "D:/动画/众生界"
# 执行本文件 §1(Step 0)的脚本;全 PASS 后:
# 打开 docs/计划_P1-6_escalation_3choice_20260420.md 按 §3 Task 1~6 TDD
# A 完成后运行本文 §3(Step A→B);全 PASS 后:
# 打开 docs/计划_P1-7_evaluator_exemption_20260420.md 按 §3 Task 1~7 TDD
# B 完成后运行本文 §5(Step Final);全 PASS 后写成功日志
```

祝顺利。若失败按 §6 落地即可,作者起床会看日志。
