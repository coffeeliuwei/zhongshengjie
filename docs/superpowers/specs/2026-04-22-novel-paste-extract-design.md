# novel-paste-extract Skill 设计文档

> **生成时间**：2026-04-22（Asia/Shanghai）
> **状态**：待实施

---

## 背景与问题

学生在使用众生界系统时，没有批量外部小说文件可供 `unified_extractor.py` 处理。他们将零散小说内容（粘贴文本、txt/pdf/docx 文件）直接扔进对话框，希望提炼成写作技法和案例入库，供写手参考。

现有 `novel-inspiration-ingest` skill 不适用：它的分类框架和必读文件全部绑定众生界世界观（十大势力、设定文件），学生的小说项目里不存在这些文件，运行到 Phase 2 就会报错。

---

## 目标

新建通用 skill `novel-paste-extract`，让学生把任意小说片段（文本或文件）提炼为：
1. **写作技法条目** → 写入 `创作技法/99-从小说提取/{维度名}.md` → sync 进 `writing_techniques_v2`
2. **案例条目** → 写入 `.case-library/cases/{维度名}/{slug}.md` → sync 进 `case_library_v2`

---

## 触发条件

满足以下任一条件时立即调用本 skill：

- 用户粘贴连续文本 >200 字
- 用户提供 `.txt` / `.pdf` / `.docx` 文件路径
- 用户说"学习这段写法"、"提炼这段"、"这段写得好"、"这本书能不能学"

---

## 五阶段流程

### Phase 0：归档

将输入统一转为不可变原件，保存到 `素材库/YYYY-MM-DD-paste-{N}/source.md`。

| 输入类型 | 处理方式 |
|---------|---------|
| 粘贴文本 | 原文写入 `source.md`，顶部标注"来源：对话粘贴 + 时间" |
| `.txt` | 读取文件内容 → `source.md` |
| `.pdf` | `pdftotext -enc UTF-8 文件 source.txt`；若命令不存在则用 `Read` 工具多模态解析 |
| `.docx` | `python -c "import docx; print(docx.Document('文件').paragraphs...)"` 提取正文 |

**截断规则**：文件 >50KB 时，只取前 30KB 进行提炼，向用户说明截断位置。

**meta.yml 写入**：
```yaml
archived_at: <时间>
source_type: paste | txt | pdf | docx
source_origin: "<路径或'对话粘贴'>"
user_intent: "<用户一句话说明>"
status: phase-0
```

---

### Phase 1：提炼分析

AI 读取 `source.md` 全文，产出两类内容。**不做世界观匹配，不读设定文件。**

#### 1A 技法条目（3-8条）

每条包含：
- `dimension`：归属维度（从下表11个中选，可多选）
- `name`：技法名称（≤10字）
- `description`：一句话说明（≤30字）
- `example_quote`：原文中最能体现该技法的1-2句话
- `applicable_scene`：适用场景（如"战斗收尾"、"人物初登场"）

**11个维度**（对应 `创作技法/` 目录）：
```
01-世界观维度 / 02-剧情维度 / 03-人物维度 / 04-战斗冲突维度 /
05-氛围意境维度 / 06-叙事维度 / 07-主题维度 / 08-情感维度 /
09-读者体验维度 / 10-元维度 / 11-节奏维度
```

#### 1B 案例条目（2-5条）

每条包含：
- `dimension`：归属维度
- `title`：案例标题（≤15字）
- `content`：原文片段（100-500字，完整保留原文）
- `why_good`：为什么值得学习（2-3句话，聚焦写法而非内容）
- `applicable_scene`：适用场景

---

### Phase 2：展示确认

向用户展示提炼结果，格式如下：

```
【提炼结果 · 请确认】─────────────────────────────
来源：{source_origin}  字数：约{N}字

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

用户回复后处理：
- `✓` → 进入 Phase 3
- `✗` → 终止，不写任何文件
- `删 [编号]` → 删除指定条目后重新展示，等待再次确认

---

### Phase 3：写文件

#### 技法文件

目标：`创作技法/99-从小说提取/{维度名}.md`

追加格式（与现有文件保持一致）：
```markdown
### {技法名}

{说明}

- **示例**："{example_quote}"
- **适用场景**：{applicable_scene}
- **来源**：素材库/{slug}/source.md

---
```

若文件不存在则创建，顶部加：
```markdown
# {维度名} - 从小说提取的技法

> 由 novel-paste-extract skill 生成
```

#### 案例文件

目标：`.case-library/cases/{维度名}/{slug}.md`

格式：
```markdown
---
title: {title}
dimension: {dimension}
applicable_scene: {applicable_scene}
source: 素材库/{slug}/source.md
created_at: {时间}
---

# {title}

## 原文

{content}

## 为什么值得学习

{why_good}
```

---

### Phase 4：sync 入库

依次执行：

```bash
# 同步技法
python -m modules.knowledge_base.sync_manager --target technique

# 同步案例
python .case-library/scripts/sync_to_qdrant.py --docker
```

执行完成后输出汇报：

```
【写入完成】─────────────────────────────
✅ 技法条目：{N}条 → writing_techniques_v2
✅ 案例条目：{M}条 → case_library_v2
📁 素材存档：素材库/{slug}/
──────────────────────────────────────────
```

失败处理：
- sync 失败不回滚文件（文件已落盘，下次手动 sync 可补救）
- 向用户说明失败原因和手动 sync 命令

---

## Skill 元数据

```yaml
name: novel-paste-extract
description: >
  Use when user pastes novel text (>200 chars) or provides txt/pdf/docx file path
  for technique extraction. Extracts writing techniques and case examples into
  case_library_v2 and writing_techniques_v2. Generic — not tied to any specific
  novel worldview. Requires user confirmation before writing.
trigger_keywords:
  - 粘贴文本 >200字
  - .txt / .pdf / .docx 路径
  - 学习这段写法 / 提炼这段 / 这段写得好
```

---

## 不在范围内

- 世界观适配（那是 novel-inspiration-ingest 的职责）
- 整本小说批量提炼（那是 unified_extractor.py 的职责）
- 图片型 PDF 的 OCR（告知学生用文字版 PDF）
- 视频/音频转写

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `C:\Users\{USERNAME}\.agents\skills\novel-paste-extract\SKILL.md` | Skill 主体 |
| `创作技法/99-从小说提取/{维度名}.md` | 技法输出（运行时生成） |
| `.case-library/cases/{维度名}/{slug}.md` | 案例输出（运行时生成） |
| `素材库/{slug}/source.md` | 原文存档（运行时生成） |
| `素材库/{slug}/meta.yml` | 元数据（运行时生成） |
