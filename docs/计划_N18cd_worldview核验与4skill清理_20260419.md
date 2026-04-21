# 计划 P0-3 + P0-4 / N18cd:worldview 横幅与文件大小补核 + 4 个未覆盖 skill 清理

- **创建时间**:2026-04-19 (Asia/Shanghai)
- **执行者**:opencode (GLM5)
- **路线图位置**:[ROADMAP_众生界v2实施_20260419.md](./ROADMAP_众生界v2实施_20260419.md) §3.1 P0-3 **+** P0-4(合并)
- **依据**:[m7_artifacts/m7_summary.md](./m7_artifacts/m7_summary.md) §3.1 表格 + §3.0 12 skill 清单
- **前置**:P0-1 ✅(2026-04-19 Claude 核验)、P0-2 ✅(2026-04-19 n18_test_log.txt 157 行)
- **为什么合并**:P0-3 与 P0-4 同是 skill 层工作(`~/.agents/skills/` 下),工具链相同,数据快照相邻;合并为一份计划避免反复读取上下文的摩擦成本(来源 `memory/feedback_batch_plans_for_opencode.md`)
- **Shell**:bash

---

## 0. 本计划的目的(给 opencode 与未来 Claude)

把 P0 阶段"N18 残留修复"的**最后两块拼图**一次做完:

**Part A(P0-3 / N18c)**:只做**证据采集**,把 [N18-E](worldview DEPRECATED 横幅存在)和 [N18-F](8 SKILL.md 文件大小变化 <30%)的**真实判定证据**固化到审计日志 `docs/m7_artifacts/n18cd_audit_log_20260419.txt`。Claude 已预跑确认两项都真实 PASS(worldview 含 ⚠️ DEPRECATED;最大 delta = worldview 7.9%,远低于 30%),**opencode 不需要修任何 skill 内容**,只需把证据写到日志。

**Part B(P0-4 / N18d)**:给 12 skill 中原 N18 未覆盖的 **4 个 skill** 补上 `[N18d 2026-04-19]` 清理标记,使"12 skill 全清理"口径完整。4 skill 经 Claude 预跑核验**都没有** `.vectorstore/core` 死引用、`from modules.creation` 死引用或 M2-β 冲突,所以**本计划不修任何功能代码**,只在每份 SKILL.md 的 frontmatter 之后追加一段 `[N18d 2026-04-19]` 说明段落。

**范围边界**(不得扩张):
- 不重写任何 skill 的功能描述(鉴赏师 novelist-connoisseur 的大改交 **P1-3**,本计划仅登记"待 P1-3 大改"占位)
- 不跑 pytest
- 不 git commit
- 不改 8 个已清理 skill 的任何内容(只读)
- 不处理 [N18-E]/[N18-F] 之外的验收项(P0-2 N18b 已覆盖 [N18-A/B/C/D])

---

## 1. 执行前的真实状态(Claude 已于 2026-04-19 核验)

### 1.1 [N18-E] worldview DEPRECATED 横幅已存在(文件头部)

```
$ head -10 C:/Users/39477/.agents/skills/novelist-worldview-generator/SKILL.md
---
name: novelist-worldview-generator
description: "世界观生成器 - 从小说大纲自动提取并生成世界观配置。支持多用户、大纲同步、配置更新。"
---

> # ⚠️ DEPRECATED — M2-β 后该 skill 整体不可用
>
> **[N18 2026-04-18]** 本 skill 引用的 `.vectorstore/core/worldview_generator.py` 和
```

`grep -c "DEPRECATED"` = 1,`grep -c "N18 2026-04-18"` = 1 → **[N18-E] 实质 PASS**。

### 1.2 [N18-F] 8 SKILL.md 大小变化(backup vs current,post-N18a)

Claude 预跑数据:
```
novel-workflow                      backup=97544    current=97991    delta=+0.5%
novelist-evaluator                  backup=49057    current=49123    delta=+0.1%
novelist-canglan                    backup=6167     current=6345     delta=+2.9%
novelist-jianchen                   backup=5380     current=5567     delta=+3.5%
novelist-moyan                      backup=5489     current=5670     delta=+3.3%
novelist-xuanyi                     backup=5731     current=5918     delta=+3.3%
novelist-yunxi                      backup=6947     current=7140     delta=+2.8%
novelist-worldview-generator        backup=9256     current=9983     delta=+7.9%
```

最大 |delta| = **7.9%**,远低于 30% → **[N18-F] PASS**。

### 1.3 4 个未覆盖 skill 现状(Claude 已核验)

| skill | bytes | lines | .vectorstore/core | from modules.creation | 已有 [N18 标记 |
|-------|------:|------:|:-----------------:|:---------------------:|:--------------:|
| novel-inspiration-ingest    | 15160 | 324 | 0 | 0 | 0 |
| novelist-connoisseur         |  4960 | 129 | 0 | 0 | 0 |
| novelist-shared              | 15685 | 383 | 0 | 0 | 0 |
| novelist-technique-search    |  6555 | 285 | 0 | 0 | 0 |

**全部干净 — 无死引用、无 M2-β 冲突。**本计划只做"登记 + 加标记"。

---

## 2. opencode 执行规则(不可违反)

### 2.1 允许的操作

1. 新建 `docs/m7_artifacts/n18cd_audit_log_20260419.txt`(Part A)
2. 新建 `docs/m7_artifacts/skill_backup_20260419/` 子目录,内含 4 个 skill 的 SKILL.md 备份(Part B)
3. 修改 **4 个** SKILL.md 文件:`~/.agents/skills/{novel-inspiration-ingest,novelist-connoisseur,novelist-shared,novelist-technique-search}/SKILL.md`(每个只在 frontmatter 之后追加指定段落)
4. 运行 §4 自检命令

### 2.2 禁止的操作

- ❌ 不得修改 8 个已处理 skill 的任何内容(只读)
- ❌ 不得重写 novelist-connoisseur 的功能描述(交 P1-3)
- ❌ 不得删除 4 skill 原有 `---` frontmatter 或 description
- ❌ 不得 git commit
- ❌ 不得跑 pytest
- ❌ 不得 cp/mv/rm 除本计划指定外的文件
- ❌ 不得动 `.archived/` 与 `.vectorstore/` 数据目录
- ❌ **不得在 4 skill 中注入 `[N18 2026-04-18]`(错误日期)**——必须用 `[N18d 2026-04-19]` 区分

### 2.3 编码与格式约束

- 所有新文件:UTF-8 无 BOM、LF 换行
- SKILL.md 保持 Markdown 原格式,不动现有行尾与缩进
- Windows 路径用正斜杠:`C:/Users/39477/.agents/skills/...`

### 2.4 冲突处理

- 若 `docs/m7_artifacts/n18cd_audit_log_20260419.txt` 已存在 → 停止,报 `CONFLICT-AUDIT-EXISTS`
- 若 `docs/m7_artifacts/skill_backup_20260419/` 已存在 → 停止,报 `CONFLICT-BACKUP-EXISTS`
- 若任一 skill 已含 `[N18d 2026-04-19]` 字样 → 跳过该 skill(打印 "SKIP: 已注入"),继续其他
- 若任一 SKILL.md 不存在 → 停止,报 `MISSING: <skill>/SKILL.md`,不要自动创建

---

## 3. 执行步骤(严格按顺序)

### 3.A Part A — [N18-E] + [N18-F] 证据采集(写审计日志)

#### 3.A.1 Step A1:初始化 audit log 头部

```bash
cd "D:/动画/众生界"
AUDIT="docs/m7_artifacts/n18cd_audit_log_20260419.txt"

[ -f "$AUDIT" ] && { echo "CONFLICT-AUDIT-EXISTS"; exit 1; }

cat > "$AUDIT" <<'HEADER'
================================================================================
 n18cd_audit_log_20260419.txt — N18c + N18d 审计日志
================================================================================
生成时间 : 2026-04-19 (Asia/Shanghai)
生成执行 : opencode (GLM5),按 docs/计划_N18cd_worldview核验与4skill清理_20260419.md
覆盖范围 :
  Part A (P0-3 / N18c):
    - [N18-E] novelist-worldview-generator/SKILL.md ⚠️ DEPRECATED 横幅
    - [N18-F] 8 个已处理 SKILL.md 相对 skill_backup_20260418/ 的大小变化 < 30%
  Part B (P0-4 / N18d):
    - 4 个未覆盖 skill 注入 [N18d 2026-04-19] 清理标记
数据基线 : m7_summary.md (诚实版,2026-04-19)
================================================================================
HEADER
```

#### 3.A.2 Step A2:[N18-E] worldview DEPRECATED 横幅证据

```bash
{
  echo ""
  echo "################################################################################"
  echo "# [N18-E] novelist-worldview-generator/SKILL.md 含 ⚠️ DEPRECATED 横幅"
  echo "################################################################################"
  echo ""
  echo "--- 文件前 15 行(包含 frontmatter 和 DEPRECATED 横幅)---"
  head -15 "C:/Users/39477/.agents/skills/novelist-worldview-generator/SKILL.md"
  echo ""
  echo "--- grep -n DEPRECATED (预期 ≥ 1) ---"
  grep -n "DEPRECATED" "C:/Users/39477/.agents/skills/novelist-worldview-generator/SKILL.md"
  dep_count=$(grep -c "DEPRECATED" "C:/Users/39477/.agents/skills/novelist-worldview-generator/SKILL.md")
  echo "DEPRECATED 总命中:$dep_count"
  echo ""
  echo "--- grep -n 'N18 2026-04-18' (预期 ≥ 1) ---"
  grep -n "N18 2026-04-18" "C:/Users/39477/.agents/skills/novelist-worldview-generator/SKILL.md"
  echo ""
  if [ "$dep_count" -ge 1 ]; then
    echo "[N18-E] 判定:PASS"
  else
    echo "[N18-E] 判定:FAIL — DEPRECATED 横幅缺失"
  fi
} >> "$AUDIT" 2>&1
```

#### 3.A.3 Step A3:[N18-F] 8 SKILL.md 大小变化对比

```bash
{
  echo ""
  echo "################################################################################"
  echo "# [N18-F] 8 个已处理 SKILL.md 相对备份的大小变化 < 30%"
  echo "################################################################################"
  echo ""
  printf "%-35s %10s %10s %10s %s\n" "skill" "backup_B" "current_B" "delta%" "verdict"
  echo "------------------------------------------------------------------------------------------"
  max_abs=0
  fail=0
  for s in novel-workflow novelist-evaluator novelist-canglan novelist-jianchen novelist-moyan novelist-xuanyi novelist-yunxi novelist-worldview-generator; do
    bf="docs/m7_artifacts/skill_backup_20260418/$s/SKILL.md"
    cf="C:/Users/39477/.agents/skills/$s/SKILL.md"
    if [ ! -f "$bf" ] || [ ! -f "$cf" ]; then
      printf "%-35s %10s %10s %10s %s\n" "$s" "MISSING" "MISSING" "N/A" "FAIL"
      fail=1
      continue
    fi
    bb=$(wc -c < "$bf" | tr -d ' ')
    cb=$(wc -c < "$cf" | tr -d ' ')
    # delta% = (cb - bb) * 100 / bb
    delta=$(awk -v b="$bb" -v c="$cb" 'BEGIN{printf "%.2f", (c-b)*100.0/b}')
    abs=$(awk -v d="$delta" 'BEGIN{printf "%.2f", (d<0 ? -d : d)}')
    # verdict
    if awk -v a="$abs" 'BEGIN{exit !(a<30)}'; then verdict="PASS"; else verdict="FAIL"; fail=1; fi
    # track max
    max_abs=$(awk -v m="$max_abs" -v a="$abs" 'BEGIN{printf "%.2f", (a>m?a:m)}')
    printf "%-35s %10s %10s %10s%% %s\n" "$s" "$bb" "$cb" "$delta" "$verdict"
  done
  echo ""
  echo "最大 |delta| = ${max_abs}%(阈值 30%)"
  if [ "$fail" -eq 0 ]; then
    echo "[N18-F] 判定:PASS(8 个全部 <30%)"
  else
    echo "[N18-F] 判定:FAIL — 有至少 1 项超限或文件缺失"
  fi
} >> "$AUDIT" 2>&1
```

---

### 3.B Part B — 4 skill 注入 `[N18d 2026-04-19]` 清理标记

#### 3.B.1 Step B1:备份 4 skill 到 `skill_backup_20260419/`

```bash
BACKUP_DIR="docs/m7_artifacts/skill_backup_20260419"
[ -d "$BACKUP_DIR" ] && { echo "CONFLICT-BACKUP-EXISTS"; exit 1; }
mkdir -p "$BACKUP_DIR"

for s in novel-inspiration-ingest novelist-connoisseur novelist-shared novelist-technique-search; do
  src="C:/Users/39477/.agents/skills/$s/SKILL.md"
  [ -f "$src" ] || { echo "MISSING: $s/SKILL.md"; exit 1; }
  mkdir -p "$BACKUP_DIR/$s"
  cp "$src" "$BACKUP_DIR/$s/SKILL.md"
done

# 验证:4 份备份都在
for s in novel-inspiration-ingest novelist-connoisseur novelist-shared novelist-technique-search; do
  test -f "$BACKUP_DIR/$s/SKILL.md" || { echo "FAIL-BACKUP: $s"; exit 1; }
done
echo "Part B backup OK"
```

#### 3.B.2 Step B2:注入清理标记(用 Python 精确插入,避开 sed/awk Windows 兼容坑)

**为什么用 Python**:opencode 在 Windows bash 下 sed/awk 对 UTF-8 中文 + 多行处理易踩坑,Python 单文件脚本可保证行为一致。

新建脚本 `docs/m7_artifacts/_n18d_injector.py`(**完成后不删,留审计**):

```python
"""
[N18d 2026-04-19] skill 标记注入器
运行方式:python docs/m7_artifacts/_n18d_injector.py
作用:给 4 个 skill 的 SKILL.md 在 frontmatter 之后、正文之前追加一段 [N18d 2026-04-19] 说明
幂等:若目标文件已含 "[N18d 2026-04-19]" 字样则跳过
"""
from pathlib import Path
import sys

SKILLS_ROOT = Path(r"C:/Users/39477/.agents/skills")

# 模板:普通 3 skill(干净清单)
NOTE_GENERIC = """
> **[N18d 2026-04-19] 12 skill 清理口径**
>
> 本 skill 已纳入 v2 §6 第 3 步"12 skill 全清理"范围。
> 2026-04-19 核验:**无** `.vectorstore/core` 死引用、**无** `from modules.creation`
> 死引用、**无** M2-β 重构后的路径/符号冲突。skill 与当前代码库兼容,无需修改功能内容。
> 参见:`docs/计划_N18cd_worldview核验与4skill清理_20260419.md` Part B。
"""

# 模板:connoisseur 特殊(P1-3 将大改)
NOTE_CONNOISSEUR = """
> **[N18d 2026-04-19] 12 skill 清理口径 + P1-3 待重写占位**
>
> 本 skill 已纳入 v2 §6 第 3 步"12 skill 全清理"范围。
> 2026-04-19 核验:**无** `.vectorstore/core` 死引用、**无** `from modules.creation`
> 死引用、**无** M2-β 冲突。
>
> ⚠️ **重要**:本 skill 将由 **P1-3**(见 `docs/ROADMAP_众生界v2实施_20260419.md` §3.2)
> 大改为 v2"创意注入器 + 派单监工"角色。当前 v1"选最活的"描述**仅临时保留**,
> 请勿基于当前内容构建下游依赖。
> 参见:`docs/计划_N18cd_worldview核验与4skill清理_20260419.md` Part B。
"""

TARGETS = [
    ("novel-inspiration-ingest", NOTE_GENERIC),
    ("novelist-connoisseur",     NOTE_CONNOISSEUR),
    ("novelist-shared",          NOTE_GENERIC),
    ("novelist-technique-search", NOTE_GENERIC),
]

def inject(skill_name: str, note: str) -> str:
    """返回 'INJECTED' / 'SKIPPED' / 'FAIL:<reason>'"""
    f = SKILLS_ROOT / skill_name / "SKILL.md"
    if not f.is_file():
        return f"FAIL:missing {f}"
    text = f.read_text(encoding="utf-8")
    if "[N18d 2026-04-19]" in text:
        return "SKIPPED(已含标记)"
    # 定位 frontmatter 结束处(第二个 '---' 之后)
    if not text.startswith("---"):
        return "FAIL:frontmatter missing opening ---"
    second = text.find("\n---", 3)
    if second == -1:
        return "FAIL:frontmatter missing closing ---"
    # 跳到第二个 --- 行的换行之后
    insert_pos = text.find("\n", second + 1) + 1
    new_text = text[:insert_pos] + note + text[insert_pos:]
    # 原子写回
    tmp = f.with_suffix(".md.tmp")
    tmp.write_text(new_text, encoding="utf-8", newline="\n")
    tmp.replace(f)
    return "INJECTED"

if __name__ == "__main__":
    results = []
    for name, note in TARGETS:
        r = inject(name, note)
        print(f"{name:35s} {r}")
        results.append((name, r))
    fails = [r for r in results if r[1].startswith("FAIL")]
    sys.exit(1 if fails else 0)
```

执行:

```bash
python docs/m7_artifacts/_n18d_injector.py 2>&1 | tee -a "$AUDIT"
```

#### 3.B.3 Step B3:把 Part B 结果也写入 audit log

```bash
{
  echo ""
  echo "################################################################################"
  echo "# Part B — 4 个未覆盖 skill 注入 [N18d 2026-04-19] 标记"
  echo "################################################################################"
  echo ""
  echo "--- 注入结果(每 skill 一行)---"
  # 上一步 tee 已写;再补 grep 验证
  for s in novel-inspiration-ingest novelist-connoisseur novelist-shared novelist-technique-search; do
    f="C:/Users/39477/.agents/skills/$s/SKILL.md"
    hits=$(grep -c "N18d 2026-04-19" "$f")
    bytes_now=$(wc -c < "$f" | tr -d ' ')
    bytes_bak=$(wc -c < "docs/m7_artifacts/skill_backup_20260419/$s/SKILL.md" | tr -d ' ')
    delta=$(awk -v b="$bytes_bak" -v c="$bytes_now" 'BEGIN{printf "%.2f", (c-b)*100.0/b}')
    printf "%-35s  N18d-hits=%d  backup=%s  current=%s  delta=%s%%\n" "$s" "$hits" "$bytes_bak" "$bytes_now" "$delta"
  done
  echo ""
  echo "--- connoisseur 特殊段落(应含 'P1-3 待重写占位')---"
  grep -A 1 "N18d 2026-04-19" "C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md" | head -5
  echo ""
  echo "[Part B] 判定:若 4 个 skill 的 N18d-hits ≥ 1 → PASS"
} >> "$AUDIT" 2>&1
```

---

### 3.C Step C — audit log 收尾

```bash
{
  echo ""
  echo "################################################################################"
  echo "# 综合判定"
  echo "################################################################################"
  echo ""
  echo "P0-3 N18c 判定:[N18-E] + [N18-F] 均需 PASS"
  echo "P0-4 N18d 判定:4 skill 均 N18d-hits ≥ 1"
  echo ""
  echo "12 skill 清理口径完成后结构:"
  echo "  原 N18(8 skill,[N18 2026-04-18] 标记):novel-workflow, novelist-evaluator,"
  echo "    novelist-canglan, novelist-jianchen, novelist-moyan, novelist-xuanyi,"
  echo "    novelist-yunxi, novelist-worldview-generator"
  echo "  新增 N18d(4 skill,[N18d 2026-04-19] 标记):novel-inspiration-ingest,"
  echo "    novelist-connoisseur, novelist-shared, novelist-technique-search"
  echo "  合计 12 skill 全覆盖。"
  echo ""
  echo "================================================================================"
  echo "日志结束 — 生成时间(本机参考):$(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "================================================================================"
} >> "$AUDIT" 2>&1
```

---

## 4. 自检命令(执行完 §3 后必须跑,任一 FAIL 立即停止)

```bash
cd "D:/动画/众生界"
AUDIT="docs/m7_artifacts/n18cd_audit_log_20260419.txt"
BACKUP_DIR="docs/m7_artifacts/skill_backup_20260419"

echo "===== 自检开始 ====="

# ---------- Part A 自检 ----------

# A-1:audit log 存在
test -f "$AUDIT" || echo "FAIL-A1: audit log 不存在"

# A-2:audit log 行数 ≥ 80(本计划输出相对少,阈值 80)
lines=$(wc -l < "$AUDIT" | tr -d ' ')
echo "audit log 行数:$lines"
[ "$lines" -ge 80 ] || echo "FAIL-A2: 行数=$lines,应 ≥ 80"

# A-3:含 4 个章节标题
for tag in "N18-E]" "N18-F]" "Part B" "综合判定"; do
  grep -q "$tag" "$AUDIT" || echo "FAIL-A3: 缺章节 [$tag]"
done

# A-4:[N18-E] 判定 PASS
grep -q "^\[N18-E\] 判定:PASS" "$AUDIT" || echo "FAIL-A4: [N18-E] 未 PASS"

# A-5:[N18-F] 判定 PASS
grep -q "^\[N18-F\] 判定:PASS" "$AUDIT" || echo "FAIL-A5: [N18-F] 未 PASS"

# A-6:8 skill 数据行都在
for s in novel-workflow novelist-evaluator novelist-canglan novelist-jianchen novelist-moyan novelist-xuanyi novelist-yunxi novelist-worldview-generator; do
  grep -q "^$s " "$AUDIT" || echo "FAIL-A6: [N18-F] 表格缺 $s"
done

# ---------- Part B 自检 ----------

# B-1:backup 目录 4 子目录都在
test -d "$BACKUP_DIR" || echo "FAIL-B1: backup 目录不存在"
for s in novel-inspiration-ingest novelist-connoisseur novelist-shared novelist-technique-search; do
  test -f "$BACKUP_DIR/$s/SKILL.md" || echo "FAIL-B2: 缺备份 $s"
done

# B-2:4 skill SKILL.md 均含 [N18d 2026-04-19] ≥ 1 处
for s in novel-inspiration-ingest novelist-connoisseur novelist-shared novelist-technique-search; do
  f="C:/Users/39477/.agents/skills/$s/SKILL.md"
  test -f "$f" || { echo "FAIL-B3: $s SKILL.md 不存在"; continue; }
  hits=$(grep -c "N18d 2026-04-19" "$f")
  if [ "$hits" -ge 1 ]; then
    echo "PASS-B3: $s 含 $hits 处 [N18d 2026-04-19]"
  else
    echo "FAIL-B3: $s 缺 [N18d 2026-04-19] 标记"
  fi
done

# B-3:connoisseur 含 P1-3 占位说明
grep -q "P1-3" "C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md" \
  && echo "PASS-B4: connoisseur 含 P1-3 占位" \
  || echo "FAIL-B4: connoisseur 缺 P1-3 占位"

# B-4:4 skill 大小变化均合理(<30%;本步注入量很小,实际应 <5%)
for s in novel-inspiration-ingest novelist-connoisseur novelist-shared novelist-technique-search; do
  bf="$BACKUP_DIR/$s/SKILL.md"
  cf="C:/Users/39477/.agents/skills/$s/SKILL.md"
  bb=$(wc -c < "$bf" | tr -d ' ')
  cb=$(wc -c < "$cf" | tr -d ' ')
  abs=$(awk -v b="$bb" -v c="$cb" 'BEGIN{d=(c-b)*100.0/b; printf "%.2f", (d<0?-d:d)}')
  if awk -v a="$abs" 'BEGIN{exit !(a<30)}'; then
    echo "PASS-B5: $s delta=${abs}%"
  else
    echo "FAIL-B5: $s delta=${abs}% 超限"
  fi
done

# ---------- 保护性自检 ----------

# G-1:8 已处理 skill 未被修改(通过大小 + [N18 2026-04-18] 标记未变)
for s in novel-workflow novelist-evaluator novelist-canglan novelist-jianchen novelist-moyan novelist-xuanyi novelist-yunxi novelist-worldview-generator; do
  f="C:/Users/39477/.agents/skills/$s/SKILL.md"
  hits=$(grep -c "N18 2026-04-18" "$f")
  [ "$hits" -ge 1 ] || echo "FAIL-G1: 8 skill 中 $s 的 [N18 2026-04-18] 标记消失"
  # 同时不应被注入 [N18d 2026-04-19]
  hits_d=$(grep -c "N18d 2026-04-19" "$f")
  [ "$hits_d" -eq 0 ] || echo "FAIL-G2: 8 skill 中 $s 被误注入 [N18d 2026-04-19]"
done

# G-2:项目结构未被破坏
test -d core/inspiration || echo "FAIL-G3: 项目结构被破坏"
test -f docs/m7_artifacts/m7_summary.md || echo "FAIL-G4: m7_summary.md 被删"
test -f docs/m7_artifacts/n18_test_log.txt || echo "FAIL-G5: n18_test_log.txt 被删"

# G-3:注入器脚本留痕
test -f docs/m7_artifacts/_n18d_injector.py || echo "FAIL-G6: 注入器脚本应保留审计"

echo "===== 自检结束 — 若上方无 FAIL 字样则全部通过 ====="
```

任一 `FAIL-` 出现 → **立即停止**,不要尝试自动修补。回滚路径:
- Part B 已改 SKILL.md 可从 `$BACKUP_DIR/<skill>/SKILL.md` 还原
- audit log 可直接删除重跑

---

## 5. 完成判据

Part A(P0-3 / N18c):
- [x] `docs/m7_artifacts/n18cd_audit_log_20260419.txt` 存在,行数 ≥ 80
- [x] [N18-E] 判定 PASS(worldview 头部 DEPRECATED 横幅已记录)
- [x] [N18-F] 判定 PASS(8 skill 大小变化表完整,最大 |delta| <30%)

Part B(P0-4 / N18d):
- [x] `docs/m7_artifacts/skill_backup_20260419/` 存在,含 4 个 skill 子目录与 SKILL.md 备份
- [x] 4 个 skill 的 SKILL.md 各含 ≥ 1 处 `[N18d 2026-04-19]` 标记
- [x] `novelist-connoisseur/SKILL.md` 含 `P1-3` 占位说明
- [x] 4 skill 的大小变化 <30%(实际应 <5%)
- [x] 注入器脚本 `docs/m7_artifacts/_n18d_injector.py` 保留

保护性:
- [x] 8 个已处理 skill 未被修改(`[N18 2026-04-18]` 标记仍在,未被错误注入 `[N18d 2026-04-19]`)
- [x] 无 git commit
- [x] 未跑 pytest
- [x] `.archived/` / `.vectorstore/` 未动

---

## 6. 完成后更新 ROADMAP(opencode 执行)

1. 把 [ROADMAP_众生界v2实施_20260419.md](./ROADMAP_众生界v2实施_20260419.md) §3.1:
   - P0-3 行状态改为 ✅,产出列加 "← **已完成**"
   - P0-4 行状态改为 ✅,产出列加 "← **已完成**"
2. §3 顶部"★ 当前任务指针"从 **P0-3** 推进到 **P1 启动前:向作者确认 Q1-Q4**(见 §6 表格)
3. §5 时间线追加两行:

```
| 2026-04-19 | opencode | N18cd Part A 完成 | n18cd_audit_log_20260419.txt,[N18-E]/[N18-F] 双 PASS |
| 2026-04-19 | opencode | N18cd Part B 完成 | 4 未覆盖 skill 注入 [N18d 2026-04-19],12 skill 清理口径闭合 |
```

4. §1.3(或新建"P0 阶段完成"小节)在"真实基线事实"下方追加一句:

```
- **P0 阶段(N18 残留修复)已闭合**:2026-04-19 完成 N18a/b/c/d 全部 4 子任务
  (12 skill 清理口径完整:8 skill 含 [N18 2026-04-18],4 skill 含 [N18d 2026-04-19])
```

---

## 7. 下一步

P0 全部闭合后,进入 **P1 前置门禁**:**向作者 coffeeliuwei 确认 ROADMAP §6 的 Q1-Q4 四个决策问题**,未表态**不得启动** P1-1/P1-7 的任何代码实施计划。

Q1-Q4 列表(摘抄自 ROADMAP §6):
- Q1:阶段 5.5 若鉴赏师 0 条建议,是否跳过直接进阶段 6?(影响 P2-1)
- Q2:创意契约 preserve_list 是否支持嵌套?(影响 P1-1)
- Q3:author_force_pass 推翻事件是否影响下次同类型场景的鉴赏师建议倾向?(影响 P2-4)
- Q4:阶段 6 评估师豁免是否支持 partial_exempt(豁免部分维度)?(影响 P1-7 / P2-3)

---

**计划结束。opencode 按 §3.A → §3.B → §3.C 顺序执行,§4 自检,§6 更新 ROADMAP。**
