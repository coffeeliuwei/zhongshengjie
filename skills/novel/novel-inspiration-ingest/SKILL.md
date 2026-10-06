---
name: novel-inspiration-ingest
description: >
  对话中所有信息储备的唯一入口。以下任一情况立即触发：
  用户粘贴文本>200字 / 提供 .txt/.pdf/.docx/.epub 路径 / 提供 URL / 上传图片 /
  手打描述（角色设定/章节内容/技法心得/灵感碎片）/
  触发短语：扔本书/看下这个/消化一下/吸收进设定/这个能不能用/学习这段写法/提炼技法/这段写得好/这个加进大纲。
  内部按资料层次路由到：设定/*.md / 创作技法/ / .case-library/ / 章节大纲/*.md / 总大纲.md。
  注意：批量外部小说库提炼（case_builder.py）是独立离线任务，不经过本 skill。
---

# [N18d 2026-04-19] P0-4 清理:已核验无死引用,纳入 N18 范围
# 灵感素材处理工作流（通用）

> **生成时间**：2026-04-17 20:58（上海时间）
> **适用范围**：用户扔进来的任何"突发灵感素材"——PDF、TXT、网页 URL、聊天粘贴、手打笔记、截图、音视频转写等
> **执行者**：Claude（本助手）。opencode(GLM5) 只在阶段 5 落实 PATCH 时介入
> **铁律**：原始素材永不修改、永不直接入库；未完成阶段 2 不得进入阶段 3

---

## 工作流总览

```
[用户扔素材] → 阶段0 归档 → 阶段1 提取 → 阶段2 加载世界观
                                               ↓
                                          阶段3 分类打标
                                               ↓
                                          阶段4 落库提案
                                               ↓
                                     用户审 → 阶段5 实施 → 阶段6 回溯
```

每一阶段的产出都落在同一个素材库目录，形成完整证据链。

---

## 阶段 0 · 归档素材（Ingest）

**目标**：把任何来源的素材统一成一份不可变原件。

### 目录结构
```
素材库/{YYYY-MM-DD}-{简短slug}/
├── source.{ext}          # 原始素材（永不修改）
├── meta.yml              # 元数据
├── units.md              # 阶段1 输出
├── context_snapshot.md   # 阶段2 输出
├── classify.md           # 阶段3 输出
├── propose.md            # 阶段4 输出
├── applied.md            # 阶段5 结果
└── rejected.md           # 被弃用的 Unit + 理由
```

### 来源适配器（Source Adapters）

| 素材类型 | 归档动作 | 落地文件 |
|---------|---------|---------|
| **PDF** | `pdftotext -enc UTF-8 源文件.pdf source.txt` | `source.pdf` + `source.txt` |
| **TXT/MD** | 复制原件 | `source.txt` 或 `source.md` |
| **对话中粘贴的文本** | Claude 把用户粘贴内容落成 `source.md`，顶部标注"来源：对话粘贴 + 时间" | `source.md` |
| **用户手打笔记** | 同上，标注"来源：用户口述/键入" | `source.md` |
| **URL 网页** | `WebFetch` 抓正文 → markdown | `source.url.md` + 原 URL 写入 meta |
| **截图/图片** | `Read` 图片（多模态解析）→ 抄写可见文本 + 视觉描述 → `source.md`；图片保留为 `source.png` | `source.png` + `source.md` |
| **视频/音频** | 用户自行转写为文字后落到 `source.md`（本工作流不负责转写） | `source.md` |

### meta.yml 模板
```yaml
archived_at: 2026-04-17T20:58+08:00
source_type: pdf | txt | paste | typed | url | image | av
source_origin: "<用户实际提供的路径或 URL>"  # 例: "D:/素材/某书.pdf" 或 "https://example.com/article"
user_intent: "<用户一句话说为什么扔给我>"
initial_tags:
  - AI文明
  - 经济转型
status: phase-0
```

---

## 阶段 1 · 全景化提取（Extract）

**目标**：把素材拆成最小可追溯的"信息单元"，不做任何判断。

### 单元粒度
- 每条信息独立成一行，≤50 字
- 编号 `U1 / U2 / U3 ...`
- 保留节号/页码/时间戳作为来源标签

### 输出 `units.md` 模板
```markdown
# Units

| 编号 | 原文节点 | 核心断言（≤50字） |
|------|---------|-------------------|
| U1 | §2.1 | 智能倒置：人类智能从工具变成累赘的四阶段过程 |
| U2 | §3.2 | "7个谎言"：对 AI 取代人类的自我安慰话术 |
| ... | ... | ... |
```

### 禁令
- **不要**在这一阶段做取舍（"这条不适合"留到阶段 3）
- **不要**概括合并（合并会丢失钩子）
- **不要**用"等等"省略——老老实实列完

---

## 阶段 2 · 加载世界观底座（Context Load）🔴 关键步骤

> **为什么这是关键步骤**：2026-04-17 的踩坑——跳过 context 直接按"古代修仙味"粗暴过滤，误把现代政策类内容判死，忽略了"世俗帝国是现代人族社会"的事实。**这个教训必须写死在流程里。**

### 必读清单（从配置动态发现，不得省略）

**步骤一：读大纲文件**

从 `config.json → worldview.outline_path` 获取大纲文件路径并读取。
重点提取：世界中有哪些主要势力/文明（名称、定位、人口规模、当前故事阶段）。

若 `config.json` 不存在或字段缺失，直接在项目根目录找名为 `总大纲.md` 或 `大纲.md` 的文件。

**步骤二：读设定目录**

从 `config.json → paths.settings_dir` 获取设定目录路径（默认 `设定/`），列出所有 `.md` 文件。
按以下优先级选读：
1. 含"势力"、"文明"、"社会结构"关键词的文件 → 理解各势力核心特征
2. 含"力量"、"技术"、"体系"关键词的文件 → 理解各势力力量来源
3. 与本素材主题最直接相关的文件 → 深入技术细节

若设定目录不存在，仅凭大纲文件继续，在 context_snapshot.md 中注明"设定目录缺失"

### 产出 `context_snapshot.md`

一页速查，回答四个问题：
1. **本素材主题涉及哪几个文明？**（不要只填一个，多选）
2. **每个候选文明当前在故事里处于什么阶段？**（合作期/渗透期/觉醒期/战争期 等）
3. **现有设定里，哪些钩子/留白可以被本素材填充？**（列 3-5 个具体点）
4. **本项目完整势力列表**（从大纲/设定中提取，供阶段3 Q1使用）

### 铁律
> **没有 context_snapshot.md，阶段 3 不得开工。**
>
> 这条规则存在是因为：Claude 在 context 不足时会"根据审美直觉过滤"，而审美直觉在这个世界观里是错的——世俗帝国是正常人族社会，兼容现代政策；科技文明是机械流派，兼容科幻概念；AI文明是入侵者，兼容算法概念；兽族/修仙/魔法 看似古代，其实也各自有社会经济系统。

---

## 阶段 3 · 单元分类（Classify）

### 六问过滤器

对 `units.md` 每个 Unit，逐条回答：

| 问题 | 选项 |
|------|------|
| Q1 **归属文明**（可多选） | 使用 context_snapshot.md 第4问中提取的势力列表 + "跨势力"。禁止使用硬编码名称 |
| Q2 **资料层次** | 设定 / 总大纲 / 章节大纲 / 技法 / 案例 / 术语 / 弃用 |

> **Q2 各层次说明**：
> - **设定**：角色/势力/力量体系/时间线等世界观内容 → `设定/*.md`
> - **总大纲**：对全书走向、时代背景、战役结构的补充 → `总大纲.md`
> - **章节大纲**：某一章的场景安排、时间线、视角设计 → `章节大纲/第N章-章名大纲.md`
> - **技法**：写作手法、叙事技巧、语言风格 → `创作技法/99-从小说提取/{维度}.md`
> - **案例**：具体散文段落，供写手参考 → `{case_library_dir}/cases/99-从小说提取/{维度}/{slug}.md`（`case_library_dir` 从 `config.json → paths.case_library_dir` 读取，默认 `E:/case-library`）
>   ⚠️ 此处"案例"指创作技法案例（`case_library_v2`），司法/犯罪案例请走独立离线管道，见文末"不在本 skill 范围内"说明
> - **术语**：词汇/概念定义
> - **弃用**：与世界观冲突，不采纳
| Q3 **契合度** | 直接可用 / 需改写 / 需抽象 / 不适合 |
| Q4 **冲突检查** | 无冲突 / 与 {具体文件:行号} 矛盾 |
| Q5 **剧情钩子** | 1 句话描述能引出的情节冲突 |
| Q6 **拒用理由**（仅 Q2=弃用 时填） | "不因 A 而因 B"——B 必须是实锤，不是直觉 |

### 输出 `classify.md`

```markdown
| Unit | 归属 | 层次 | 契合度 | 冲突 | 钩子 | 拒用理由 |
|------|------|------|--------|------|------|----------|
| U1 | AI文明+科技文明 | 设定 | 需改写 | 无 | AI觉醒期对"人类智能无用化"的自我辩护 | - |
| U7 | 世俗帝国 | 设定 | 直接可用 | 无 | 帝国税收改革引发地方叛乱 | - |
| U13 | - | 弃用 | 不适合 | - | - | 涉及现实地名"北京"，世界观不存在 |
```

### 分类规则（避坑清单）

1. **"语感不搭"不是弃用理由**：先查 context_snapshot.md，确认该势力的实际定位。很多世界观里"现代感"、"科幻感"的素材完全兼容某些势力。
2. **跨势力 Unit 不要强行归一**：多选归属，阶段 4 会按每个文明各出一份 PATCH 草案
3. **"弃用"必须给实锤**：弃用理由必须能引用 context_snapshot.md 中的具体设定；凭直觉说"不搭"= 未通过阶段 2，退回重做

---

## 阶段 4 · 落库提案（Propose）

按 `classify.md` 的"层次"列分组，为每组生成具体 PATCH 草案。

### 4.1 设定类 → `设定/{势力}.md` 或 `设定/十大势力社会结构.md`

```markdown
### PATCH-1（U1, U2, U5）
- **目标文件**: 设定/AI文明技术基础.md
- **插入位置**: "## AI 意识发展阶段" 章节之后
- **新增段落**:
  > ### 智能倒置机制
  > AI文明在觉醒期会主动推动"智能倒置"……
- **溯源**: units.md#U1, #U2, #U5
```

### 4.2 大纲类 → `总大纲.md` 或 `分章大纲/`

```markdown
### PATCH-2（U7, U18）
- **目标文件**: 总大纲.md §8.3
- **插入位置**: "世俗帝国第三幕" 之前
- **情节钩子**: 帝国推行双货币体系，商盟抵制……
- **涉及角色**: 赵恒（主推）、苏瑾（商盟视角）、林正阳（军方视角）
```

### 4.3 技法类 → `设定/xxx技术基础.md`

说明新增技法的 力量来源 / 代价 / 使用者 / 入侵防御表现。

### 4.4 技法+案例类 → `创作技法/` 和 `.case-library/`

当 Q2 = **技法** 或 **案例** 时（通常来自用户学习外部小说写法）：

**技法条目格式**（写入 `创作技法/99-从小说提取/{维度名}.md`）：

若该文件不存在，先创建，写入头部：
```
# {维度名}技法（从小说提取）
> 来源：{slug}
> 归档时间：{时间}

---
```

每条技法追加格式：
```
## {技法名称}

**适用场景**：{适用的场景类型}
**核心操作**：{1-2句说明怎么做}
**示例**：
> {原文引用，不超过100字}
**效果**：{达到什么叙事效果}

---
```

**案例条目格式**（写入 `{case_library_dir}/cases/99-从小说提取/{维度名}/{slug}-{小写字母编号}.md`，`case_library_dir` 从 `config.json → paths.case_library_dir` 读取）：

```markdown
---
case_id: {slug}-{编号}
scene_type: {维度名}
source: 素材库/{slug}/source.md
why_good: {1-2句说明为何值得入库}
---

{原文段落，200-800字}
```

目录不存在时先 `mkdir -p` 创建。

### 4.5 章节大纲类 → `章节大纲/第N章-章名大纲.md`

当 Q2 = **章节大纲** 时（用户描述某章的场景安排、时间线、视角）：

从 `schemas/chapter_outline_schema.json` 读取格式规范，生成符合 schema 的大纲文件。

**文件命名**：`章节大纲/第{N}章-{章名}大纲.md`
- N 从对话语境提取（如"第二章"→"二"或"2"，统一用中文数字"二"）
- 章名从用户描述提取，无法确定时询问用户

**标准格式**（参考 `章节大纲/第一章-天裂大纲.md`）：

```markdown
# 《众生界》第{N}章：{章名}

---

## 章节信息

| 项目 | 内容 |
|------|------|
| **章节名** | {章名} |
| **视角** | {视角角色名} |
| **身份** | {角色定位} |
| **核心情感** | {情感基调} |
| **预计字数** | {预计字数} |

---

## 核心逻辑

### 时间线

{用流程图或列表描述场景顺序}

### 场景列表

| 序号 | 场景名 | 视角 | 地点 | 核心事件 | 涉及角色 |
|------|--------|------|------|---------|---------|
| 1 | {场景名} | {视角} | {地点} | {核心事件} | {角色} |

---

## 写作要点

- {写作要点1}
- {写作要点2}

---

## 关键设定引用

- {需要注意的设定约束}
```

若信息不足（缺视角/场景列表等），先填写已知部分，用 `[待补充]` 占位，告知用户。

### 4.6 术语类 → `设定/术语表.md` 或 `设定/势力术语/{势力名}.md`

当 Q2 = **术语** 时：

**写入目标**：
- 通用术语（跨势力或无明确归属）→ `设定/术语表.md`
- 势力专属术语 → `设定/势力术语/{势力名}.md`

**写入格式**（追加到目标文件末尾）：

```markdown
## {术语名}

**定义**：{1-2句核心含义}
**来源**：{所属势力/技法体系}
**使用场景**：{在哪类情节/对话中出现}

---
```

**Sync 命令**：

```bash
python -m modules.knowledge_base.sync_manager --target novel
```

（同「设定类」，写入 `novel_settings_v2`；`sync_manager` 会自动处理 `设定/` 目录下所有 `.md` 文件，无需手动改 `knowledge_graph.json`）

---

### 4.7 向量库类 → `novel_settings_v2` / `writing_techniques_v2` / `case_library_v2` 等

**硬规则**：只有**用户在阶段 5 accept 了**的 Unit 才能入库。

入库 payload 模板：
```json
{
  "content": "<改写后的文本>",
  "source_ref": "素材库/2026-04-17-最后的经济/units.md#U1",
  "civilizations": ["AI文明", "科技文明"],
  "layer": "设定",
  "added_at": "2026-04-17"
}
```

### 输出 `propose.md`
一份按 PATCH 编号的清单，每条含：目标文件、插入位置、新增内容草案、溯源 Unit。

---

## 阶段 5 · 用户审阅与实施（Apply）

### 5.1 审阅
用户在 `propose.md` 上勾选 `accept` / `reject` / `modify`。

### 5.2 实施
- **accept**：Claude 生成交付给 opencode(GLM5) 的 PATCH 指令（精确路径+行号+完整代码/文本块）
- **reject**：落 `rejected.md`，写明用户给的否决理由
- **modify**：回退到阶段 4 改草案

### 5.3 产出 `applied.md`
```markdown
| PATCH | 状态 | 目标文件:行号 | 执行者 | 时间 |
|-------|------|--------------|--------|------|
| PATCH-1 | applied | 设定/AI文明技术基础.md:47 | opencode | 2026-04-17 21:30 |
| PATCH-2 | rejected | 总大纲.md:820 | - | - |
```

### 5.4 · 向量库入库执行规范 🔴 必读

> **存在原因**：仅修改 Markdown 设定/技法文件**不会**让 Qdrant 检索到新内容。每条 accept 的 PATCH 落盘后，必须按下表执行配套同步命令；否则 5 写手在后续生成时仍然检索不到这些新设定。

#### 5.4.1 落盘文件 → 同步动作映射表

| PATCH 目标文件类型 | 落盘后必跑的同步命令 | 写入的 Qdrant collection | 备注 |
|---|---|---|---|
| `设定/*.md`（含十大势力、技术基础、社会结构等） | `python -m modules.knowledge_base.sync_manager --target novel` | `novel_settings_v2` | sync_manager 内部处理，无需手动改 knowledge_graph.json |
| `创作技法/**/*.md` | `python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild` | `writing_techniques_v2` | 混合向量(dense+sparse+colbert)，必须用 hybrid_sync_manager |
| `{case_library_dir}/cases/**/*.md` | `python tools/case_builder.py --sync` | `case_library_v2` | `case_library_dir` 从 `config.json → paths.case_library_dir` 读取（默认 `E:/case-library`）；用 `--limit N` 可先小规模试同步 |
| `总大纲.md` | `python scripts/sync_outlines.py` | `worldview` | 大纲同步到 worldview collection |
| `章节大纲/*.md` | `python scripts/sync_outlines.py --chapters-only` | `chapter_outlines` | 章节大纲独立 collection |
| `素材库/**`（本工作流自身产物） | **不入向量库** | — | 素材库是证据链，不是检索源 |

#### 技法+案例类 sync

> ⚠️ **重要**：技法 sync 必须使用 `hybrid_sync_manager`，不能用 `sync_manager`。  
> `sync_manager --target technique` 会用无名向量重建集合，破坏 BGE-M3 混合检索。

```bash
# 同步技法到 writing_techniques_v2（混合向量：dense + sparse + colbert）
python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild

# 同步案例到 case_library_v2
python tools/case_builder.py --sync
```

#### 章节大纲类 sync

```bash
python scripts/sync_outlines.py --chapters-only
```

#### 5.4.2 执行顺序（每条 accept 的 PATCH 都走一遍）

1. **落盘**：opencode 按 PATCH 指令把文本写入目标文件
2. **判类**：按 5.4.1 表查目标文件类型
3. **如属"设定类"**：
   - 打开 `.vectorstore/knowledge_graph.json`
   - 在 `"实体"` 字典下定位到对应实体（例如 `faction_ai_civilization`）
   - 在该实体的"属性"或对应字段下追加/合并 PATCH 文本中的新断言
   - 保存
4. **跑同步命令**（5.4.1 表中对应那一行）
5. **校验**：
   ```bash
   python -m modules.knowledge_base.sync_manager --status
   ```
   确认目标 collection 的 point count 比执行前 > 旧值

#### 5.4.3 失败处理

| 症状 | 排查 |
|---|---|
| `sync_manager` 报 `BGE-M3 模型路径未配置` | 设 `BGE_M3_MODEL_PATH` 或检查 `config.json`，**不要**去改 sync_manager 代码 |
| `sync_manager` 报 `知识图谱不存在` | 确认 `.vectorstore/knowledge_graph.json` 在项目根的相对路径正确 |
| Qdrant 连接失败 | 先 `docker ps` 看 qdrant 容器，再 fallback 到本地模式（去掉 `--docker`） |
| 同步成功但检索不到 | 用 `python -m modules.knowledge_base.search_manager --query "<关键词>"` 认认，若仍无结果回到第 3 步检查 knowledge_graph.json 是否真的写入了 |

#### 5.4.4 在 `applied.md` 中追加"同步状态"列

`5.3 产出 applied.md` 中的表格扩展为：

| PATCH | 落盘状态 | 目标文件:行号 | 同步命令 | 同步状态 | collection point 增量 | 时间 |
|---|---|---|---|---|---|---|
| PATCH-1 | applied | 设定/AI文明技术基础.md:47 | `... --target novel` | synced | +3 | 2026-04-17 21:35 |
| PATCH-3 | applied | 总大纲.md:820 | — (大纲不入库) | n/a | — | 2026-04-17 21:36 |

**没有"同步状态=synced"或"n/a"的 PATCH 不算 done**——5.4 是 5 的子步骤，同步未完成则该 PATCH 退回阶段 5 重做。

---

---

## 阶段 6 · 回溯记录（Trace）

把 `applied.md` 的每一条在其目标文件里留**一行**溯源注释（仅 Markdown 文件适用）：

```markdown
<!-- source: 素材库/2026-04-17-最后的经济/units.md#U1,U2,U5 -->
```

这样日后谁看到某段设定都能一路追溯到原始素材。

---

## 故障排除

| 症状 | 根因 | 修复 |
|------|------|------|
| 分类时大量 Unit 被判"弃用-与世界观不搭" | 跳过了阶段 2 | 强制回阶段 2，重写 context_snapshot.md，再做阶段 3 |
| PATCH 草案与现有文件内容冲突 | 阶段 3 的 Q4 冲突检查没做 | 回阶段 3 重新做冲突检查 |
| 入库后检索不到 | source_ref 字段缺失或 civilizations 标签错 | 删除该点，按模板补齐后重入 |
| opencode 实施时走样 | PATCH 没写死行号/完整文本块 | 回阶段 5 细化 PATCH 指令（参照 feedback_workflow_division.md 规则） |
| 用户说"这明显属于 X 文明你居然判 Y" | context_snapshot.md 遗漏了 X 文明的特征 | 在必读清单里补充对应技术基础文件 |

---

## 调用方式

当用户扔素材过来时，Claude 第一句回应应当是：

> 收到 {素材类型}。我按灵感素材处理工作流启动阶段 0 归档。本素材初步看主题是 {一句话}，预计涉及文明：{候选列表}。开始阶段 1？

然后**严格顺序**走阶段 0 → 6。不得并行，不得跳步。

---

## 版本历史
- v1.0 · 2026-04-17 20:58 · 初版，确立 7 阶段（0-6）流程，以"阶段 2 必须先行"为铁律
- v1.1 · 2026-04-18 01:25 · 迁移为 skill `novel-inspiration-ingest`；补全阶段 5.4「向量库入库执行规范」；阶段 5.3 表格新增"同步状态"列
- v1.2 · 2026-04-22 12:23 · 通用化重设计：阶段2必读清单改为从 config.json worldview.outline_path + paths.settings_dir 动态发现；阶段3 Q1 势力列表改为从 context_snapshot.md 第4问读取；分类规则精简为3条通用版；撤销 config.example.json inspiration_ingest 节
- v1.3 · 2026-04-25 · 全面改造：description 改为"信息储备唯一入口"；Q2 资料层次新增"总大纲/章节大纲/技法/案例"；阶段4 新增 4.4 技法+案例类、4.5 章节大纲类；sync 命令统一 _v2 后缀；新增技法/案例/章节大纲 sync 步骤；废弃 novel-paste-extract（功能已合并）
- v1.4 · 2026-05-18 · 补充术语类落库规范：新增 4.6 术语类（写入目标、格式、sync 命令）；原 4.6 向量库类顺延为 4.7

---

## 不在本 skill 范围内

- **批量外部小说库提炼**：6000+ 本小说的离线处理 → `python tools/case_builder.py --scan/--extract/--sync`（独立任务，不经本 skill）
- **章节创作**：写小说章节 → `novel-workflow`（与信息储备无关）
- **视频/音频转写**：告知用户使用文字版材料
- **图片型 PDF 的 OCR**：告知用户使用文字版 PDF
- **司法/犯罪案例（judicial_cases）**：法律判决书、检察院典型案例、犯罪新闻报道等，
  **不**走本 skill 的入库流程，应使用专属离线管道：

  1. 抓取：`python tools/scrape_spp.py`（最高检）或 `python tools/scrape_thepaper.py`（澎湃）
  2. 过滤：`python tools/filter_judicial_cases.py --dir E:/司法案例`
  3. 入库：`python tools/ingest_judicial_cases.py --embed-batch 64`

  入库目标：`judicial_cases_v1`（写手检索时通过犯罪关键词自动触发）
