# novel-paste-extract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `C:\Users\39477\.agents\skills\novel-paste-extract\SKILL.md` — a skill that extracts writing techniques and case examples from pasted novel text or uploaded files (txt/pdf/docx), shows a confirmation card to the user, then writes to `创作技法/99-从小说提取/` and `.case-library/cases/99-从小说提取/`, and syncs to Qdrant.

**Architecture:** Single SKILL.md file with 5 phases (Phase 0 archive → Phase 1 extract → Phase 2 confirm → Phase 3 write files → Phase 4 sync). The skill is natural-language instructions executed by the AI agent. No Python scripts are created — the skill reuses existing `sync_manager` and `sync_to_qdrant.py`. Case files land in a new subdirectory `.case-library/cases/99-从小说提取/{维度名}/` which the existing sync script auto-discovers.

**Tech Stack:** Markdown skill file; Python (existing: `sync_manager --target technique`, `sync_to_qdrant.py --docker`); pdftotext (optional); python-docx (optional)

**Reference spec:** `docs/superpowers/specs/2026-04-22-novel-paste-extract-design.md`

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `C:\Users\39477\.agents\skills\novel-paste-extract\SKILL.md` | **Create** | The entire skill implementation |
| `D:\动画\众生界\创作技法\99-从小说提取\` | Created at runtime | Technique output files |
| `D:\动画\众生界\.case-library\cases\99-从小说提取\` | Created at runtime | Case output files |
| `D:\动画\众生界\素材库\{slug}\source.md` | Created at runtime | Archived source text |
| `D:\动画\众生界\素材库\{slug}\meta.yml` | Created at runtime | Archive metadata |

---

## Task 1: Create SKILL.md — Metadata + Trigger

**Files:**
- Create: `C:\Users\39477\.agents\skills\novel-paste-extract\SKILL.md`

- [ ] **Step 1: Create the skill directory**

```bash
mkdir -p /c/Users/39477/.agents/skills/novel-paste-extract
```

Expected: directory exists, no error.

- [ ] **Step 2: Create SKILL.md with the full content below**

Write the following complete file to `C:\Users\39477\.agents\skills\novel-paste-extract\SKILL.md`:

```markdown
---
name: novel-paste-extract
description: >
  Use IMMEDIATELY when user pastes novel text (>200 chars) OR provides a .txt/.pdf/.docx
  file path for technique study. Extracts 3-8 writing technique items and 2-5 case
  examples into writing_techniques_v2 and case_library_v2. Generic — not tied to any
  specific novel worldview. Shows confirmation card before writing any files.
  Trigger phrases: 学习这段写法 / 提炼这段 / 这段写得好 / 这本书能不能学 / 粘贴文本>200字 / .txt/.pdf/.docx路径
---

# novel-paste-extract Skill

从粘贴文本或文件中提炼写作技法与案例，写入 writing_techniques_v2 和 case_library_v2。
**不做世界观适配，不读设定文件。**

---

## 触发条件

满足以下任一条件时立即执行本 skill（无需用户主动说"使用skill"）：

- 用户粘贴连续文本 >200 字
- 用户提供 `.txt` / `.pdf` / `.docx` 文件路径
- 用户说"学习这段写法"、"提炼这段"、"这段写得好"、"这本书能不能学"

---

## 阶段 0：归档

### 0.1 确定存档目录

运行以下命令获取当前上海时间：

```bash
TZ=Asia/Shanghai date "+%Y-%m-%d %H:%M"
```

扫描项目根目录下 `素材库/` 目录，找出所有以当日日期（`YYYY-MM-DD`）开头的子目录，
取其中最大编号 N + 1 作为本次编号。若当日无目录则 N = 1。

- **存档目录**：`素材库/YYYY-MM-DD-paste-{N}/`
- **slug**（后续步骤引用）：`YYYY-MM-DD-paste-{N}`

### 0.2 将输入转为 source.md

根据用户输入类型，用对应方式获取文本内容：

| 输入类型 | 处理方式 |
|---------|---------|
| 粘贴文本 | 直接使用对话中的文本 |
| `.txt` 路径 | 用 Read 工具读取文件内容 |
| `.pdf` 路径 | 先尝试运行 `pdftotext -enc UTF-8 "{路径}" -`；若命令不存在，用 Read 工具以多模态方式解析 |
| `.docx` 路径 | 运行 `python -c "import docx; d=docx.Document('{路径}'); print('\n'.join(p.text for p in d.paragraphs if p.text.strip()))"` |

**截断规则**：若内容超过 50000 字符（约 50KB），只保留前 30000 字符，
并在 source.md 顶部加注：`（已截断：原文超过 50KB，仅处理前约 30000 字符）`。

将以下内容写入 `素材库/{slug}/source.md`：

```
> 来源：{对话粘贴 | 文件完整路径}
> 归档时间：{YYYY-MM-DD HH:MM}（Asia/Shanghai）
> 字数：约 {实际字数} 字{（已截断，原文超过50KB）}

---

{文本内容}
```

### 0.3 写入 meta.yml

将以下内容写入 `素材库/{slug}/meta.yml`：

```yaml
archived_at: "YYYY-MM-DD HH:MM Asia/Shanghai"
source_type: paste   # 或 txt / pdf / docx
source_origin: "对话粘贴"   # 或文件完整路径
user_intent: "用户原话"   # 若无原话则填 "提炼写法"
status: phase-0
```

---

## 阶段 1：提炼分析

读取 `素材库/{slug}/source.md` 全文，进行提炼。
**不读设定文件，不做世界观分析。**

### 1A 技法条目（3-8条）

提取体现写作技巧的条目，每条包含：

- `dimension`：从下表 11 个维度中选一个（选最主要的维度）
- `name`：技法名称（≤10字，自行命名，体现技巧核心）
- `description`：一句话说明该技法（≤30字）
- `example_quote`：原文中最能体现该技法的 1-2 句话（直接引用，不改写）
- `applicable_scene`：最适合使用该技法的场景（如"战斗收尾"、"人物初登场"）

**11 个维度**（对应 `创作技法/` 目录）：

```
01-世界观维度 / 02-剧情维度 / 03-人物维度 / 04-战斗冲突维度 /
05-氛围意境维度 / 06-叙事维度 / 07-主题维度 / 08-情感维度 /
09-读者体验维度 / 10-元维度 / 11-节奏维度
```

### 1B 案例条目（2-5条）

提取值得直接临摹学习的原文片段，每条包含：

- `dimension`：归属维度（同上 11 个）
- `title`：案例标题（≤15字，概括该片段的写法亮点）
- `content`：原文片段（100-500字，完整保留原文，不得改写）
- `why_good`：为什么值得学习（2-3句话，聚焦写作技巧，不谈情节内容）
- `applicable_scene`：适用场景

---

## 阶段 2：展示确认

向用户展示提炼结果，**严格使用以下格式**，不得省略分隔线：

```
【提炼结果 · 请确认】─────────────────────────────
来源：{source_origin}  字数：约 {N} 字

▌技法条目（{N}条）
[1] {维度} · {技法名}
    {说明}
    示例："..."

[2] ...

▌案例条目（{N}条）
[A] {维度} · {标题}
    为什么好：{why_good}

[B] ...

请回复：
  ✓  全部确认，写入
  ✗  全部放弃
  删 [编号]  删掉指定条目（如：删 2, B）
──────────────────────────────────────────────────────
```

**等待用户回复，按以下逻辑处理：**

- 用户回复 `✓` 或 `确认` → 进入阶段 3，写入全部剩余条目
- 用户回复 `✗` 或 `放弃` → 立即终止，不写任何文件，告知"已放弃，未写入任何文件"
- 用户回复 `删 [编号]`（如 `删 2, B`）→ 从列表中删除指定条目，重新展示确认卡，再次等待回复

---

## 阶段 3：写文件

### 3A 技法文件

**目标路径**：`创作技法/99-从小说提取/{维度名}.md`
（维度名示例：`03-人物维度`、`05-氛围意境维度`）

若该文件**不存在**，先创建文件，写入以下头部：

```markdown
# {维度名} - 从小说提取的技法

> 由 novel-paste-extract skill 生成

---
```

向文件**末尾追加**每条技法（每条之间用 `---` 分隔）：

```markdown
### {name}

{description}

- **示例**："{example_quote}"
- **适用场景**：{applicable_scene}
- **来源**：素材库/{slug}/source.md

---
```

### 3B 案例文件

**目标路径**：`.case-library/cases/99-从小说提取/{维度名}/{slug}.md`
（目录不存在时先创建，`mkdir -p`）

为每条案例创建一个新文件，内容如下：

```markdown
---
title: {title}
dimension: {dimension}
applicable_scene: {applicable_scene}
source: 素材库/{slug}/source.md
created_at: "{YYYY-MM-DD HH:MM} Asia/Shanghai"
---

# {title}

## 原文

{content}

## 为什么值得学习

{why_good}
```

---

## 阶段 4：sync 入库

在项目根目录依次执行以下命令：

```bash
# 同步技法到 writing_techniques_v2
python -m modules.knowledge_base.sync_manager --target technique

# 同步案例到 case_library_v2
python .case-library/scripts/sync_to_qdrant.py --docker
```

**执行完成后**，向用户输出：

```
【写入完成】─────────────────────────────
✅ 技法条目：{N}条 → writing_techniques_v2
✅ 案例条目：{M}条 → case_library_v2
📁 素材存档：素材库/{slug}/
──────────────────────────────────────────
```

**sync 失败处理**：
- 不回滚已写入的文件（文件已落盘，下次手动 sync 可补救）
- 向用户说明失败原因
- 提示手动补救命令：

```
手动 sync 命令（在项目根目录运行）：
  python -m modules.knowledge_base.sync_manager --target technique
  python .case-library/scripts/sync_to_qdrant.py --docker
```

---

## 不在本 skill 范围内

- 世界观适配（由 `novel-inspiration-ingest` 负责）
- 整本小说批量提炼（由 `unified_extractor.py` 负责）
- 图片型 PDF 的 OCR（告知用户使用文字版 PDF）
- 视频/音频转写
```

- [ ] **Step 3: Verify the file was created and has content**

```bash
wc -c /c/Users/39477/.agents/skills/novel-paste-extract/SKILL.md
```

Expected: output shows a number greater than 3000 (the file is substantial).

```bash
head -10 /c/Users/39477/.agents/skills/novel-paste-extract/SKILL.md
```

Expected: First line is `---`, second line starts with `name: novel-paste-extract`.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/39477/.agents/skills
git add novel-paste-extract/SKILL.md
git commit -m "feat(skill): add novel-paste-extract — 5-phase technique & case extraction"
```

If this directory is not a git repo, skip the git step — the skill is ready to use.

---

## Task 2: Smoke Test — Phase 0 with Pasted Text

This is a manual test. Execute it to verify Phase 0 works before testing the full flow.

**Files:**
- Runtime: `D:\动画\众生界\素材库\2026-04-22-paste-1\source.md`
- Runtime: `D:\动画\众生界\素材库\2026-04-22-paste-1\meta.yml`

- [ ] **Step 1: Invoke the skill with a short test paste**

In the Claude/opencode chat window, paste the following text and send:

```
学习这段写法：

风从西面来，带着腥气，像是远处有什么腐烂的东西。陈墨站在山脊上，看着脚下的山谷，那里曾经是他长大的地方，现在只剩下断壁残垣。他没有哭，不是因为不悲伤，而是眼泪早在三年前就流干了。他只是站着，像一根钉入土地的桩。
```

- [ ] **Step 2: Verify source.md is created**

```bash
cat "D:/动画/众生界/素材库/$(TZ=Asia/Shanghai date +%Y-%m-%d)-paste-1/source.md"
```

Expected output:
- First line: `> 来源：对话粘贴`
- Second line: `> 归档时间：YYYY-MM-DD HH:MM（Asia/Shanghai）`
- Contains the pasted text

- [ ] **Step 3: Verify meta.yml is created**

```bash
cat "D:/动画/众生界/素材库/$(TZ=Asia/Shanghai date +%Y-%m-%d)-paste-1/meta.yml"
```

Expected: YAML file with `source_type: paste` and `status: phase-0`.

---

## Task 3: Smoke Test — Phase 1 + 2 (Extraction + Confirmation)

Continue from Task 2 — verify the skill proceeds to extraction and shows the confirmation card.

- [ ] **Step 1: Check that the skill showed a confirmation card**

After the paste in Task 2, the skill should display a card starting with:
```
【提炼结果 · 请确认】─────────────────────────────
```

Verify it shows:
- At least 1 technique item `[1]` under `▌技法条目`
- At least 1 case item `[A]` under `▌案例条目`
- The three response options (✓ / ✗ / 删)

- [ ] **Step 2: Test the "删" command**

Reply with: `删 1`

Expected: confirmation card is reshown with item `[1]` removed. Remaining items are renumbered.

- [ ] **Step 3: Test confirmation with ✓**

Reply with: `✓`

Expected: skill proceeds to Phase 3 (file writing).

---

## Task 4: Smoke Test — Phase 3 File Writing

Verify that technique and case files are written correctly.

- [ ] **Step 1: Check that 创作技法/99-从小说提取/ directory has at least one file**

```bash
ls "D:/动画/众生界/创作技法/99-从小说提取/"
```

Expected: at least one `.md` file named after a dimension (e.g., `03-人物维度.md`, `05-氛围意境维度.md`).

- [ ] **Step 2: Read one technique file and verify format**

```bash
cat "D:/动画/众生界/创作技法/99-从小说提取/$(ls D:/动画/众生界/创作技法/99-从小说提取/ | head -1)"
```

Expected: file starts with `# {维度名} - 从小说提取的技法`, contains at least one `### {技法名}` section with `**示例**`, `**适用场景**`, `**来源**` fields.

- [ ] **Step 3: Check that .case-library/cases/99-从小说提取/ has at least one subdirectory**

```bash
ls "D:/动画/众生界/.case-library/cases/99-从小说提取/"
```

Expected: at least one subdirectory named after a dimension.

- [ ] **Step 4: Read one case file and verify YAML front matter**

```bash
find "D:/动画/众生界/.case-library/cases/99-从小说提取/" -name "*.md" | head -1 | xargs cat
```

Expected: file starts with `---`, contains `title:`, `dimension:`, `applicable_scene:`, `source:`, `created_at:` fields, then `# {title}`, `## 原文`, `## 为什么值得学习` sections.

---

## Task 5: Smoke Test — Phase 4 Sync

Verify sync commands run without fatal errors.

- [ ] **Step 1: Run technique sync manually**

```bash
cd "D:/动画/众生界" && python -m modules.knowledge_base.sync_manager --target technique 2>&1 | tail -20
```

Expected: output ends with a success message or count of synced items. No `Traceback` or unhandled exception.

- [ ] **Step 2: Run case sync manually**

```bash
cd "D:/动画/众生界" && python .case-library/scripts/sync_to_qdrant.py --docker 2>&1 | tail -20
```

Expected: output ends with a count of synced items (e.g., "Synced N points"). No `Traceback`.

If Docker is not running, the error message will say "Connection refused" — this is expected. Tell the user:
```
Qdrant Docker 未运行。启动 Docker Desktop 后重新运行：
python .case-library/scripts/sync_to_qdrant.py --docker
```

- [ ] **Step 3: Verify skill output the completion card**

After Phase 4, the skill should have shown:
```
【写入完成】─────────────────────────────
✅ 技法条目：N条 → writing_techniques_v2
✅ 案例条目：M条 → case_library_v2
📁 素材存档：素材库/YYYY-MM-DD-paste-1/
──────────────────────────────────────────
```

---

## Task 6: Edge Case Test — .txt File Input

- [ ] **Step 1: Create a test .txt file**

```bash
cat > /tmp/test_novel.txt << 'EOF'
剑光如虹，横贯山河。

李玄站在悬崖边缘，脚下是万丈深渊，身后是三十六路追兵。他没有回头，只是慢慢地握紧了手中的剑柄。

"你们来得正好，"他说，声音平静得像在谈论天气，"省得我一个个去找。"

追兵停下了脚步。不是被他的话吓到，而是被他的平静吓到——一个知道自己必死的人，不应该是这种表情。
EOF
```

- [ ] **Step 2: Invoke skill with .txt file path**

In Claude/opencode chat, send:
```
提炼这段写法：/tmp/test_novel.txt
```

- [ ] **Step 3: Verify Phase 0 reads the file correctly**

Check that `素材库/{slug}/source.md` contains `> 来源：/tmp/test_novel.txt` (not "对话粘贴") and contains the file content.

- [ ] **Step 4: Follow through to ✓ confirmation and verify a second slug is created**

```bash
ls "D:/动画/众生界/素材库/" | grep $(TZ=Asia/Shanghai date +%Y-%m-%d)
```

Expected: two directories — `YYYY-MM-DD-paste-1` and `YYYY-MM-DD-paste-2`.

---

## Self-Review

### Spec coverage check

| Spec requirement | Covered in |
|-----------------|------------|
| Phase 0: archive pasted text | Task 1 SKILL.md §阶段0 + Task 2 |
| Phase 0: archive .txt file | Task 1 SKILL.md §0.2 table + Task 6 |
| Phase 0: archive .pdf file | Task 1 SKILL.md §0.2 table |
| Phase 0: archive .docx file | Task 1 SKILL.md §0.2 table |
| Phase 0: truncate >50KB | Task 1 SKILL.md §0.2 截断规则 |
| Phase 0: write meta.yml | Task 1 SKILL.md §0.3 + Task 2 |
| Phase 1A: 3-8 technique items | Task 1 SKILL.md §1A |
| Phase 1A: 11 dimensions | Task 1 SKILL.md §1A |
| Phase 1B: 2-5 case items | Task 1 SKILL.md §1B |
| Phase 2: confirmation card format | Task 1 SKILL.md §阶段2 + Task 3 |
| Phase 2: handle ✓/✗/删 | Task 1 SKILL.md §阶段2 + Task 3 |
| Phase 3: write technique file | Task 1 SKILL.md §3A + Task 4 |
| Phase 3: write case file | Task 1 SKILL.md §3B + Task 4 |
| Phase 4: run sync commands | Task 1 SKILL.md §阶段4 + Task 5 |
| Phase 4: handle sync failure | Task 1 SKILL.md §sync失败处理 |

**Note on case-library path:** The spec says `.case-library/cases/{维度名}/`. The existing `cases/` directory uses *scene-based* names (01-开篇场景 etc.), which differ from the 11 technique dimensions. This plan resolves the conflict by placing extracted cases under `.case-library/cases/99-从小说提取/{维度名}/`. The existing `sync_to_qdrant.py` auto-discovers all subdirectories under `cases/`, so no script changes are needed.

### Placeholder scan

No TBD/TODO placeholders found. All code blocks contain actual content.

### Type consistency

- `slug` variable defined in §0.1 and used consistently throughout Phases 0-4
- `dimension` field names match the 11-dimension list
- File paths are consistent between Phase 3 write steps and Phase 4 sync commands
