# 计划 OVERNIGHT-BATCH:P1-2 + P1-4 夜间连跑调度器

- **创建时间**:2026-04-20 (Asia/Shanghai)
- **执行者**:opencode (GLM5,无人值守夜间批次)
- **总时长预估**:90-150 分钟
- **总新增测试**:≥ 65 用例(P1-2 的 42 + P1-4 的 23)
- **全量 pytest 目标**:506 基线 + 65 = **571 passed**

---

## 0. 本调度器的作用

作者睡前一次性交给 opencode 批量跑。本文件是**唯一入口**,opencode 按顺序读完本文件后跳转到各子计划执行。

**两份子计划可独立完成、独立验收**,但 opencode 必须按以下**硬顺序**执行,不得并行、不得跳步、任一段 §5 自检出现 `FAIL-` 即整批停止。

---

## 1. 执行顺序

### 步 0:前置核验(opencode 先自检环境,5 分钟)

```bash
cd "D:/动画/众生界"

# 1. 仓库处于预期 HEAD
hash=$(git log -1 --format=%h)
[ "$hash" = "8365fe21a" ] && echo "PASS-ENV1 HEAD OK" || { echo "FAIL-ENV1 HEAD=$hash 意外变化,停止整批"; exit 1; }

# 2. P1-1 产物在位
test -f core/inspiration/creative_contract.py && echo "PASS-ENV2 creative_contract.py 在位" || { echo "FAIL-ENV2,停止"; exit 1; }
test -f tests/test_creative_contract.py && echo "PASS-ENV3" || { echo "FAIL-ENV3,停止"; exit 1; }

# 3. 基线 pytest 绿
python -m pytest tests/ --tb=no -q 2>&1 | tail -1 | tee /tmp/overnight_baseline.txt
grep -qE "506 passed" /tmp/overnight_baseline.txt && echo "PASS-ENV4 基线 506 passed" || { echo "FAIL-ENV4 基线异常"; exit 1; }

# 4. 关键子计划文件存在
test -f docs/计划_P1-2_dispatcher_20260419.md && echo "PASS-ENV5 P1-2 计划" || { echo "FAIL-ENV5,停止"; exit 1; }
test -f docs/计划_P1-4_constraint_library_menu_20260420.md && echo "PASS-ENV6 P1-4 计划" || { echo "FAIL-ENV6,停止"; exit 1; }

echo "===== 步 0 前置核验 全 PASS,进入 Part A ====="
```

任一 FAIL-ENV → **整批停止**,记录错误,不进 Part A。

---

### Part A:执行 P1-2 派单器(预估 45-75 分钟)

**入口文件**:`docs/计划_P1-2_dispatcher_20260419.md`

**opencode 动作**:
1. 读完 P1-2 计划 §0 - §8
2. 按 §3 Task 1 → Task 14 顺序 TDD 执行
3. 执行完跑 P1-2 §5 全部自检命令
4. 记录自检日志到 `docs/m7_artifacts/p1-2_selfcheck_20260420.txt`

**Part A 完成判据**(缺一不可):
- [ ] `core/inspiration/dispatcher.py` 新建,stdlib-only
- [ ] `tests/test_dispatcher.py` 新建,≥ 20 用例(实际目标 42)全 PASS
- [ ] `core/inspiration/__init__.py` 仅追加 3 个导出(DispatchPackage / dispatch / DispatcherError)
- [ ] 全量 pytest ≥ 526 passed, 0 failed
- [ ] P1-2 §5 自检全 `PASS-`,无 `FAIL-`
- [ ] git HEAD 仍 `8365fe21a`(未 commit)

**Part A 任一项 FAIL → 整批停止,跳过 Part B**,写失败报告到 `docs/m7_artifacts/overnight_FAILURE_report_20260420.txt`,包含:失败的 Task/步骤编号、pytest 输出最后 30 行、`git status --short` 输出、失败原因分析。

---

### Part B:执行 P1-4 约束库菜单化(预估 30-45 分钟)

**前置条件**:Part A 完成判据全部 ✅。若 Part A 未全 ✅,**不得进入 Part B**。

**入口文件**:`docs/计划_P1-4_constraint_library_menu_20260420.md`

**opencode 动作**:
1. 读完 P1-4 计划 §0 - §8
2. 按 §3 Task 1 → Task 7 顺序 TDD 执行
3. 执行完跑 P1-4 §5 全部自检命令
4. 记录自检日志到 `docs/m7_artifacts/p1-4_selfcheck_20260420.txt`

**Part B 完成判据**:
- [ ] `core/inspiration/constraint_library.py` 追加 4 个方法,前 115 行原样
- [ ] `tests/test_constraint_library.py` 追加 ≥ 13 用例(实际目标 23)全 PASS
- [ ] `config/dimensions/anti_template_constraints.json` 未改
- [ ] `core/inspiration/__init__.py` 未改(Part A 动过的除外)
- [ ] 全量 pytest ≥ 549 passed, 0 failed
- [ ] P1-4 §5 自检全 `PASS-`,无 `FAIL-`
- [ ] git HEAD 仍 `8365fe21a`

**Part B 任一项 FAIL → 停止,写失败报告**(不回退 Part A 的成果,让 Claude 早上核验时决定)。

---

### 步 末:最终合并核验(5 分钟)

```bash
cd "D:/动画/众生界"

echo "===== 最终合并核验 ====="

# 1. 两份子计划产物同时在位
test -f core/inspiration/dispatcher.py && echo "PASS-FIN1 dispatcher.py" || echo "FAIL-FIN1"
test -f tests/test_dispatcher.py && echo "PASS-FIN2 test_dispatcher.py" || echo "FAIL-FIN2"

# 2. constraint_library.py 4 新方法
python -c "
from core.inspiration.constraint_library import ConstraintLibrary
for m in ('as_menu', 'count_by_category', 'search_by_keyword', 'format_menu_text'):
    assert hasattr(ConstraintLibrary, m), f'{m} 缺失'
print('constraint_library 4 新方法齐全')
" && echo "PASS-FIN3" || echo "FAIL-FIN3"

# 3. 包导出
python -c "from core.inspiration import CreativeContract, dispatch, DispatchPackage, DispatcherError, ConstraintLibrary; print('imports OK')" \
  && echo "PASS-FIN4 包导出齐全" || echo "FAIL-FIN4"

# 4. 全量 pytest
python -m pytest tests/ --tb=no -q 2>&1 | tail -1 | tee /tmp/overnight_final.txt
total=$(grep -oE "^[0-9]+ passed" /tmp/overnight_final.txt | head -1 | grep -oE "^[0-9]+")
echo "全量总数:${total:-N/A} passed"
if [ -n "$total" ] && [ "$total" -ge 549 ]; then
  echo "PASS-FIN5 全量 ≥ 549(Part A+B 最小合计)"
else
  echo "FAIL-FIN5 全量低于预期"
fi

# 5. git HEAD 未动
hash=$(git log -1 --format=%h)
[ "$hash" = "8365fe21a" ] && echo "PASS-FIN6 HEAD 未 commit" || echo "FAIL-FIN6"

# 6. 工作区未污染意外文件
git status --short 2>&1 | wc -l | xargs -I {} echo "工作区未跟踪/改动数:{} 项"

# 7. 生成总结
cat > docs/m7_artifacts/overnight_summary_20260420.txt <<'EOF'
# Overnight Batch 运行总结(2026-04-20)
## 执行子计划
- Part A: docs/计划_P1-2_dispatcher_20260419.md
- Part B: docs/计划_P1-4_constraint_library_menu_20260420.md
## 自检日志
- p1-2_selfcheck_20260420.txt
- p1-4_selfcheck_20260420.txt
## 下一步
- Claude 早上核验两份 §5 自检日志,全 PASS 则继续 P1-3/P1-5/P1-6/P1-7
EOF
echo "PASS-FIN7 总结已写入"

echo "===== OVERNIGHT 批次全部完成 ====="
```

---

## 2. 失败恢复策略(opencode 遇错的决策树)

```
┌─────────────────────────────────────────────┐
│ 步 0 前置核验 FAIL → 整批不启动              │
│   写 overnight_FAILURE_report_20260420.txt   │
│   HEAD 不动、工作区不动                       │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Part A 中某 Task FAIL                        │
│   → 不进 Part B                              │
│   → Part A 的部分产物留在工作区(Claude 收)  │
│   → 写 overnight_FAILURE_report,注明失败 Task │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Part B 中某 Task FAIL                        │
│   → Part A 的完整成果已留在工作区             │
│   → Part B 部分产物留在工作区                │
│   → 写 overnight_FAILURE_report             │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ 步 末最终核验 某项 FAIL                      │
│   → 两 Part 产物都在,但合并态存疑            │
│   → 写 overnight_SUSPICIOUS_report          │
│   → 给 Claude 早上分析                       │
└─────────────────────────────────────────────┘
```

**绝对禁忌**:
- ❌ 任何情况下不得 `git reset` / `git checkout -- .` / `git clean`
- ❌ 任何情况下不得 `git commit`
- ❌ 任何情况下不得删除 Claude 早上需要核验的日志/报告

**允许**:
- ✅ 在出错 Task 的文件中回滚当前 Task 的局部变更(比如 Task 5 写错测试 → 只删该 Task 追加的那几个测试函数),然后报错停止
- ✅ 多次跑 pytest 作为诊断(不改代码的情况下)

---

## 3. 日志与报告落地

| 文件路径 | 何时写 | 内容 |
|----------|--------|------|
| `docs/m7_artifacts/p1-2_selfcheck_20260420.txt` | Part A §5 跑完 | P1-2 自检完整输出 |
| `docs/m7_artifacts/p1-2_test_log_20260420.txt` | P1-2 Task 14.1 | 全量 pytest -v 输出 |
| `docs/m7_artifacts/p1-4_selfcheck_20260420.txt` | Part B §5 跑完 | P1-4 自检完整输出 |
| `docs/m7_artifacts/p1-4_test_log_20260420.txt` | P1-4 Task 7.2 | 全量 pytest -v 输出 |
| `docs/m7_artifacts/overnight_summary_20260420.txt` | 步 末成功时 | 批次总结 |
| `docs/m7_artifacts/overnight_FAILURE_report_20260420.txt` | 任一阶段失败 | 失败 Task/日志/status |
| `docs/m7_artifacts/overnight_SUSPICIOUS_report_20260420.txt` | 步末存疑时 | 合并检查失败详情 |

---

## 4. Claude 早上接手流程(作者起床后触发)

```bash
cd "D:/动画/众生界"

# 1. 找失败报告
ls docs/m7_artifacts/overnight_* 2>/dev/null

# 2. 若只有 overnight_summary → 成功路径
#    → 读两份 selfcheck 日志确认 PASS
#    → 跑 Part A §5 + Part B §5 自检复核一次(不信 opencode 自述)
#    → 全 PASS → ROADMAP §3.2 P1-2 + P1-4 改 ✅
#    → 写 P1-3 连舷师 SKILL.md 计划(下一个单独交)

# 3. 若有 overnight_FAILURE_report → 失败路径
#    → 读报告,定位失败 Task
#    → 根据失败类型:代码错(Claude 修测试或实现) / 计划错(Claude 改计划再交一次)
#    → 修复后让 opencode 再跑失败段
```

---

## 5. 作者须知

- **opencode 夜间无需人工干预**,但若 HEAD/基线异常会在"步 0"就停止,不会产生任何变更
- **工作区所有变更不 commit**,作者早上看 `git status` 可见全部增删
- **最糟情况**:Part A 做到一半 FAIL → 工作区留 dispatcher.py 和部分测试。**不会破坏任何现有文件**(只追加 + 新建,不删除)
- **最好情况**:Part A+B 全 PASS → 工作区新增 dispatcher.py + 4 个 constraint_library 方法 + 2 个测试文件增量,pytest 571 passed

---

## 6. 下一步(Part A+B 成功后,Claude 早上写)

按 ROADMAP §3.2 顺序,剩余 P1 阶段:

| # | 下一份计划 | 类型 |
|---|-----------|------|
| P1-3 | `docs/计划_P1-3_connoisseur_skill重写_20260420.md` | SKILL.md 重写(鉴赏师) |
| P1-5 | `docs/计划_P1-5_删除variant_generator_20260420.md` | 归档 + 调用方迁移 |
| P1-6 | `docs/计划_P1-6_escalation_dialogue三方协商_20260420.md` | 代码改造 |
| P1-7 | `docs/计划_P1-7_evaluator_exemption_20260420.md` | 代码 + SKILL 同步 |

**P1-3/P1-5/P1-6/P1-7 均不由本批次处理**,Claude 早上按情况逐一写计划 + 发给 opencode。

---

**调度器结束。opencode 按步 0 → Part A → Part B → 步末 顺序执行。任一 FAIL 即停。**
