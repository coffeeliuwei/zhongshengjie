# AGENTS.md - 众生界项目 AI 协作规范

> **适用对象**: Claude、OpenCode、及其他 AI 编程助手
> **最后更新**: 2026-05-18
> **权威文档**: [docs/系统架构.md](./docs/系统架构.md) — 所有 SKILL.md / 计划文档与本文冲突，以系统架构.md为准

---

## 0. 快速认知（首次接触必读）

> 拿到任务前先读这份自动生成的骨架，3分钟掌握全项目结构：
> **[docs/PROJECT_SKELETON.md](./docs/PROJECT_SKELETON.md)**
> — 覆盖 181 个文件 / 164 个类 / 479 个函数，含签名和 docstring，随每次 commit 自动更新。

> **opencode 注意**：骨架较长（4631行），按需读对应目录段落即可，无需全量加载。
> 例如只改 `core/` 时，只读骨架中 `## \`core/\`` 段落；改 `tools/` 时只读 `## \`tools/\`` 段落。

> **骨架自动更新**：任何工具（Claude Code / opencode / 手动 git）提交时，
> 若有 `.py` 文件变更，git pre-commit hook 会自动重新生成骨架并追加进本次 commit，无需手动操作。

---

## 1. 项目上下文

```
项目路径: D:\动画\众生界
主分支: master（唯一分支，禁止创建新分支）
开发协议: docs/opencode_dev_protocol_20260420.md v1
语言: 中文（git commit、文档、报告均使用中文）
配置真相源: config.json（唯一配置，所有路径由其控制）
```

---

## 2. 系统全景：三条独立路径

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              用户对话 / CMD                                   │
└───────────────┬────────────────────────┬───────────────────────┬─────────────┘
                │                        │                       │
                ▼                        ▼                       ▼
  ┌─────────────────────┐   ┌────────────────────┐   ┌─────────────────────────┐
  │   信息储备路径        │   │   章节创作路径      │   │   批量外部小说提炼       │
  │ novel-inspiration-  │   │  novel-workflow     │   │  python tools/          │
  │ ingest              │   │  (0→8全阶段)        │   │  batch_extract.py       │
  │                     │   │                    │   │                         │
  │  触发：             │   │  触发：             │   │  ⛔ 不经对话路由        │
  │  · 粘贴文本>200字   │   │  · "写第N章"        │   │  ⛔ 不是 skill          │
  │  · .txt/.pdf/.docx  │   │  · "继续写"         │   └─────────────────────────┘
  │  · URL / 图片       │   │                    │
  │  · 手打描述         │   │  ⛔ 与信息储备      │
  │  · 扔本书/消化一下  │   │  完全独立           │
  └─────────────────────┘   └────────────────────┘
```

> **关键理解**: 三条路径完全独立，信息储备路径处理用户输入素材，章节创作路径处理写作任务，批量提炼是独立CLI工具。

---

## 3. 必须遵守的协议

### 3.1 开发协议（实施任务时必读）

> **实施任何代码修改前必须阅读**: [docs/opencode_dev_protocol_20260420.md](./docs/opencode_dev_protocol_20260420.md)

核心规则：
- **分支**: 仅 master，禁止创建任何新分支
- **测试**: 分 4 阶段（聚焦→邻居→全量→判定），必须 tee 到日志文件
- **commit**: AI 不许自己 commit，产出代码 + success_log 由作者/Claude审阅后提交
- **pytest**: 禁止裸跑全量测试，必须 `tee docs/m7_artifacts/<task>_stage3_full_<date>.txt`

---

## 4. 核心目录结构

### 4.1 D 盘：项目代码 + 内容

```
D:\动画\众生界\                        ← project_root
│
├── config.json                        ← ★ 配置真相源（唯一）
├── 总大纲.md                          ← 世界观总大纲
├── 设定/                              ← 角色势力设定
├── 章节大纲/                          ← 各章节大纲
├── 正文/                              ← 输出正文
├── 创作技法/                          ← 技法库（11维度）
├── 章节经验日志/                       ← 写作经验沉淀
│
├── core/                              ← 核心模块
│   ├── config_loader.py               ← 统一读取 config.json
│   ├── conversation/                  ← 对话路由
│   └── knowledge_base/                ← 检索/同步
│       ├── hybrid_search_manager.py   ← BGE-M3 混合检索
│       └── sync_manager.py            ← Qdrant 同步入口
│
├── modules/                           ← 功能模块
│   └── knowledge_base/                ← 向量库管理
│       └── hybrid_sync_manager.py     ← ★ 技法同步入口
│
├── tools/                             ← 工具脚本
│   ├── batch_extract.py               ← 批量提炼统一入口
│   ├── unified_extractor.py           ← 11维度并行提炼
│   ├── case_builder.py                ← 场景案例提取
│   ├── build_all.py                   ← 统一入库管线 v16
│   ├── style_injector.py              ← 去AI感·阶段3.7风格包生成（按作家权重采样）
│   ├── quality_gate.py                ← 去AI感·Phase 3.5 Burstiness+套句双检测
│   ├── narrative_ledger.py            ← 叙事台账·跨章节节拍/情绪/主题追踪
│   ├── scrape_spp.py                  ← 司法案例·最高检爬虫
│   ├── scrape_thepaper.py             ← 司法案例·澎湃新闻爬虫
│   ├── filter_judicial_cases.py       ← 司法案例·关键词评分过滤
│   └── ingest_judicial_cases.py       ← 司法案例·BGE-M3入库（judicial_cases_v1）
│
├── .novel-extractor/                  ← 小说提炼引擎
│   └── extractors/                    ← 各维度提取器
│
├── .vectorstore/                      ← 向量库工具
│
├── tests/                             ← pytest 测试
├── scripts/                           ← 同步脚本
└── config/                            ← 世界观配置
```

### 4.2 E 盘：大文件存储

```
E:\
├── 小说资源\                          ← 外部小说库（~5897本）
├── case-library\                      ← 案例库
│   └── cases\                         ← 场景案例 JSON
├── novel_extracted\                   ← 提炼输出
│   └── technique\                     ← 技法提取结果
│       └── technique_all.json         ← 138,968条批量技法
├── qdrant_storage\                    ← Qdrant 数据库
│   └── collections\                   ← 13个 collection
└── huggingface_cache\                 ← BGE-M3 模型缓存
```

---

## 5. Qdrant Collections 一览

| Collection | 点数 | 向量模式 | 用途 |
|-----------|------|---------|------|
| `novel_settings_v2` | ~数万 | colbert+sparse+dense | 角色/势力/设定检索 |
| `writing_techniques_v2` | 986 | colbert+sparse+dense | 技法检索（活数据） |
| `writing_techniques_batch_v1` | 138,968 | dense+sparse | 批量提炼技法 |
| `case_library_v2` | 152,293 | dense | 场景案例检索 |
| `chapter_outlines` | - | dense | 大纲检索 |
| `worldview` | - | dense | 世界观检索 |
| `dialogue_style_v1` | 8 | dense | 对话风格（每势力） |
| `emotion_arc_v1` | 5,655 | dense | 情感弧 |
| `power_vocabulary_v1` | 306,218 | dense | 力量词汇 |
| `foreshadow_pair_v1` | 19,768 | dense | 伏笔配对 |
| `character_relation_v1` | 22,254 | dense | 角色关系三元组 |
| `poetry_imagery_v2` | - | dense | 云溪诗词意象 |
| `evaluation_criteria_v1` | 26 | dense | 审核标准 |
| `judicial_cases_v1` | ~1007 | dense+sparse | 司法/犯罪案例写作素材 |
| `memory_points_v1` | - | dense | 写手自我风格记忆点 |

> 配置键名见 `config.json → database.collections`（v16起全量声明）

---

## 5.1 去AI感管线工具（2026-05-16 新增）

| 文件 | 用途 | 调用时机 |
|------|------|---------|
| `tools/style_injector.py` | 按写手作家配比生成风格包 | novel-workflow 阶段 3.7 |
| `tools/quality_gate.py` | Burstiness方差≥50 + 套句命中率≤15% | novel-workflow Phase 3.5（每场景） |
| `tools/narrative_ledger.py` | 节拍/情绪/主题三维度跨章节约束 | 阶段1读取 + 阶段8写入 |
| `config/writers_style_config.yaml` | 5写手作家权重 + quality_gate阈值 | style_injector/quality_gate 读取 |
| `docs/style_collection/author_styles.yaml` | 100位作家档案（AI套句黑名单等） | style_injector 读取 |

---

## 6. Sync 命令速查表

| 层次 | 写入路径 | Sync 命令 | Collection |
|------|---------|-----------|------------|
| 设定 | `设定/*.md` | `python -m modules.knowledge_base.sync_manager --target novel` | `novel_settings_v2` |
| 总大纲 | `总大纲.md` | `python scripts/sync_outlines.py` | `worldview` + `novel_plot_v1` |
| 章节大纲 | `章节大纲/` | `python scripts/sync_outlines.py --chapters-only` | `chapter_outlines` |
| 技法 | `创作技法/**/*.md` | ★ `python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild` | `writing_techniques_v2` |
| 案例 | `E:/case-library/cases/` | `python tools/case_builder.py --sync` | `case_library_v2` |

> ⚠️ **技法同步禁用**: `python -m core kb --sync technique` 已停用，必须用 `hybrid_sync_manager --sync technique --rebuild`

---

## 7. 报告生成强制验证规则

> **适用于**: 任何涉及配置文件、文件引用、导入声明、LSP诊断的报告
> **来源**: 2026-05-01 LSP报告校验事故提炼

### 7.1 配置文件规则（致命级）

```
IF 报告涉及配置文件内容:
    THEN 必须先 Read 该配置文件
    THEN 在报告中展示真实读取内容
    ELSE 禁止凭记忆/推断生成配置内容
```

### 7.2 文件引用规则（严重级）

```
IF 报告引用具体文件路径:
    THEN 必须先 Glob 验证文件存在
    THEN 对比 glob 返回列表确认拼写正确
    ELSE 禁止引用未验证的文件名
```

### 7.3 导入声明规则（严重级）

```
IF 报告声称"缺失导入/依赖":
    THEN 必须先 Grep 搜索该 import 语句
    THEN 必须先 Read 检查是否有 try/except 防御模式
    THEN 标注"可选依赖(已有防御)"或"硬依赖(需安装)"
```

### 7.4 LSP诊断范围规则（致命级）

```
IF 生成 LSP 诊断报告:
    THEN 必须先 Read pyrightconfig.json
    THEN 解析 include/exclude 字段
    THEN 过滤超出扫描范围的诊断
    THEN 在报告开头声明有效范围
```

---

## 8. 已废弃条目（禁止使用）

| 废弃项 | 替代方案 |
|-------|---------|
| `novel-paste-extract` skill | 并入 `novel-inspiration-ingest` |
| `sync_manager --target technique` | 用 `hybrid_sync_manager --sync technique --rebuild` |
| `novel_settings`（无 `_v2`）| 统一加 `_v2` 后缀 |
| `writing_techniques`（无 `_v2`）| 统一加 `_v2` 后缀 |
| `.case-library/`（D盘）| 迁移至 `E:/case-library` |
| `device="cpu"` 硬编码 | 用 `core.config_loader.get_device()` 自动检测 |

---

## 9. 版本历史

| 版本 | 日期 | 更新内容 |
|-----|------|---------|
| v1.0 | 2026-05-01 | 初稿：整合开发协议 + 报告验证规则 |
| v1.1 | 2026-05-01 | 整合系统架构.md：三条路径、目录结构、Collections、Sync命令 |

---

**引用规则**: 给 AI 的任务指令开头必须声明：

```
> 本任务遵循 AGENTS.md v1.1
> 涉及配置/文件/导入的报告必须完成 Phase 0-3 验证流程
> 与 docs/系统架构.md 冲突时，以系统架构.md为准
```