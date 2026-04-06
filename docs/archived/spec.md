# 众生界项目技术规格文档

> 生成时间: 2026-04-04
> 项目路径: `D:\动画\众生界`
> 分析方式: 后序遍历（深→浅）

---

## 1. 项目概览

### 1.1 基本信息

| 指标 | 数值 |
|------|------|
| **项目名称** | 众生界 - AI辅助小说创作系统 |
| **总目录数** | 75 |
| **总文件数** | 401 |
| **最大深度** | 3层 |
| **核心语言** | Python (166个), Markdown (202个) |

### 1.2 核心功能

- **多Agent协作创作**：5位作家(苍澜/玄一/墨言/剑尘/云溪) + 1位审核
- **知识图谱管理**：196实体 / 436关系
- **向量检索系统**：Qdrant (34万+案例库, 904技法)
- **追踪系统**：伏笔/承诺/信息边界/资源/时间线

### 1.3 技术栈

```
后端: Python 3.12
向量库: Qdrant Docker
嵌入模型: MiniLM-L12-v2 (384维) → BGE-M3 (1024维)
数据库: SQLite
前端: HTML/JS (可视化)
配置: YAML/JSON
```

---

## 2. 目录结构

```
众生界/
├── 📁 创作技法/           # 11维度技法库 (64个MD)
│   ├── 01-世界观维度/     # 7个文件
│   ├── 02-剧情维度/       # 9个文件
│   ├── 03-人物维度/       # 8个文件
│   ├── 04-战斗冲突维度/   # 5个文件
│   ├── 05-氛围意境维度/   # 5个文件
│   ├── 06-叙事维度/       # 8个文件
│   ├── 07-主题维度/       # 3个文件
│   ├── 08-情感维度/       # 4个文件
│   ├── 09-读者体验维度/   # 2个文件
│   ├── 10-元维度/         # 4个文件
│   ├── 11-节奏维度/       # 2个文件
│   ├── 99-通用模板/       # 6个文件
│   ├── 99-实战案例/       # 1个文件
│   └── 99-外部资源/       # 44个文件
│
├── 📁 设定/               # 世界观设定 (25个MD)
│   ├── 核心设定/          # 人物谱、十大势力、力量体系、时间线
│   ├── 技术基础/          # 10个文明技术基础
│   └── 追踪文件/          # hook_ledger、payoff_tracking等
│
├── 📁 正文/               # 创作成果
│   ├── 手稿/              # 第一章多版本
│   └── 场景草稿/          # 第一章-v3 (8个场景)
│
├── 📁 章节大纲/           # 章节规划
├── 📁 评估报告/           # Evaluator输出
├── 📁 章节经验日志/       # 经验沉淀
├── 📁 写作标准积累/       # 用户修改要求
│
├── 📁 core/               # ⚠️ 扩展备用，当前不启用
│   │                      # （对话形式通过 Skills 驱动，无需此模块）
│   ├── cli.py             # CLI命令入口（预留Web/API）
│   ├── config_manager.py  # 配置管理（预留）
│   ├── db_connection.py   # 数据库连接+降级模式（预留）
│   ├── error_handler.py   # 错误处理框架（预留）
│   ├── health_check.py    # 健康检查（预留）
│   └── path_manager.py    # 路径管理（预留）
│
├── 📁 modules/            # ⚠️ 扩展备用，当前不启用
│   │                      # （对话形式通过 Skills 驱动，无需此模块）
│   ├── feedback/          # 反馈处理（预留）
│   ├── knowledge_base/    # 知识库管理（预留）
│   ├── migration/         # 数据迁移（预留）
│   ├── validation/        # 验证系统（预留）
│   └── visualization/     # 可视化（预留）
│
├── 📁 tests/              # 测试文件 (7个Python)
├── 📁 docs/               # 文档 (2个MD)
├── 📁 tools/              # 工具脚本
├── 📁 存档/               # 历史版本
│   ├── 学习笔记/          # 17个MD
│   ├── modules_creation_archived/  # 已弃用模块 (13个Python)
│   └── vectorstore临时脚本/         # 历史脚本 (20个Python)
│
├── 📁 .vectorstore/       # 向量数据库系统
│   ├── sync/              # 同步脚本
│   ├── qdrant_docker/     # Qdrant数据
│   └── knowledge_graph.json  # 知识图谱
│
└── 📁 .case-library/      # 案例库 (34万JSON)
```

---

## 3. 分层详解（后序遍历）

### 第3层（最深层）

#### 📁 正文/场景草稿/第一章-v3/

**文件列表**：
- 场景1-血月荒原.md
- 场景2-血脉暴走.md
- 场景3-村口血战.md
- 场景4-山林掩护.md
- 场景5-妇孺诀别.md
- 场景6-分尸与目睹.md
- 场景7-返回战场.md
- 场景8-仇恨誓言.md

**核心内容**：第一章第三版的8个场景拆分，按时间线推进

---

#### 📁 存档/modules_creation_archived/

**文件列表**（13个Python）：
- api.py - API接口
- conflict_detector.py - 冲突检测
- creation_mode.py - 创作模式
- evaluator_executor.py - 评估执行器
- experience_retriever.py - 经验检索
- iteration_optimizer.py - 迭代优化
- parallel_execution_manager.py - 并行执行
- workflow_scheduler.py - 工作流调度
- writer_executor.py - 作家执行器
- yunxi_fusion_polisher.py - 云溪融合润色

**状态**：已弃用，保留用于参考

---

### 第2层

#### 📁 modules/feedback/

**核心模块**：
- intent_recognizer.py - 意图识别
- conflict_detector.py - 冲突检测
- influence_analyzer.py - 影响分析
- tracking_syncer.py - 追踪同步

**功能**：处理用户反馈，检测冲突，分析影响范围

---

#### 📁 modules/knowledge_base/

**核心模块**：
- search_manager.py - 检索管理
- sync_manager.py - 同步管理
- vectorizer_manager.py - 向量化管理

**功能**：管理Qdrant向量库，同步知识数据

---

#### 📁 modules/validation/

**核心模块**：
- checker_manager.py - 检查器
- scorer_manager.py - 评分器
- validation_manager.py - 验证管理

**功能**：验证创作结果，评分检查

---

#### 📁 modules/visualization/

**核心模块**：
- db_visualizer.py - 数据库可视化
- graph_visualizer.py - 图谱可视化
- stats_visualizer.py - 统计可视化

**功能**：生成HTML可视化报告

---

### 第1层

#### 📁 core/

**核心模块**（8个Python）：

| 文件 | 功能 |
|------|------|
| cli.py | 命令行入口 |
| config_manager.py | 配置加载与管理 |
| db_connection.py | SQLite连接池 |
| error_handler.py | 全局错误处理 |
| health_check.py | 系统健康检查 |
| path_manager.py | 路径解析与管理 |

**依赖关系**：
```
cli.py → config_manager.py → db_connection.py
       → path_manager.py
       → error_handler.py
```

---

#### 📁 创作技法/

**11维度技法库**：

| 维度 | 文件数 | 作家 |
|------|--------|------|
| 01-世界观 | 7 | 苍澜 |
| 02-剧情 | 9 | 玄一 |
| 03-人物 | 8 | 墨言 |
| 04-战斗冲突 | 5 | 剑尘 |
| 05-氛围意境 | 5 | 云溪 |
| 06-叙事 | 8 | 玄一 |
| 07-主题 | 3 | - |
| 08-情感 | 4 | 墨言 |
| 09-读者体验 | 2 | - |
| 10-元 | 4 | - |
| 11-节奏 | 2 | - |

**外部资源分类**（44个）：
- 心理学类：7个
- 逻辑学类：4个
- 网文技法类：7个
- AI写作类：5个
- 其他学科：21个

---

#### 📁 设定/

**核心设定文件**：

| 分类 | 文件 |
|------|------|
| **角色** | 人物谱.md、主角哲学心理基调.md、角色过往经历与情绪触发.md |
| **势力** | 十大势力.md、十大势力社会结构.md |
| **力量** | 力量体系.md |
| **时间** | 时间线.md |
| **技术基础** | 10个文明技术（科技/AI/异化人/修仙/魔法等） |

**追踪文件**（5个）：
- hook_ledger.md - 伏笔账本
- payoff_tracking.md - 爽点承诺
- information_boundary.md - 信息边界
- resource_ledger.md - 资源账本
- timeline_tracking.md - 时间线追踪

---

### 第0层（根目录）

#### 配置文件

| 文件 | 功能 |
|------|------|
| README.md | 项目总览 |
| PROJECT_GUIDE.md | 项目指南 |
| CONFIG.md | 配置说明 |
| API.md | API文档 |
| MIGRATION.md | 迁移指南 |
| AI_GUIDE.md | AI使用指南 |
| requirements.txt | Python依赖 |
| 总大纲.md | 故事总大纲 |
| 标准化方案.md | 标准化说明 |

---

## 4. 核心文件分析

### 4.1 入口文件

```
入口点: core/__main__.py
命令行: core/cli.py
配置: core/config_manager.py
```

### 4.2 数据文件

| 文件 | 位置 | 规模 |
|------|------|------|
| knowledge_graph.json | .vectorstore/ | 196实体/436关系 |
| 第一章_log.json | 章节经验日志/ | 经验沉淀 |
| unified_index.json | .case-library/ | 案例索引 |

### 4.3 向量库配置

```
Qdrant Collections:
├── case_library      # 256,083条案例
├── creation_context  # 创作上下文
├── novel_settings    # 143条设定
└── writing_techniques # 904条技法
```

---

## 5. 依赖关系图

```
┌─────────────────────────────────────────────────────┐
│                    用户交互层                        │
│  cli.py / config_manager.py / path_manager.py      │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                    业务逻辑层                        │
│  modules/feedback/  modules/validation/             │
│  modules/knowledge_base/  modules/visualization/   │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                    数据存储层                        │
│  SQLite (db_connection.py)                         │
│  Qdrant (vectorizer_manager.py)                    │
│  JSON Files (sync_manager.py)                      │
└─────────────────────────────────────────────────────┘
```

---

## 6. 数据流向

### 创作流程

```
用户请求 → cli.py
    ↓
意图识别 → modules/feedback/intent_recognizer.py
    ↓
知识检索 → modules/knowledge_base/search_manager.py
    ↓
作家执行 → 创作技法/ + 设定/
    ↓
结果验证 → modules/validation/validation_manager.py
    ↓
可视化 → modules/visualization/graph_visualizer.py
```

### 数据同步

```
设定文件 → .vectorstore/sync/md_parser.py
    ↓
知识图谱 → knowledge_graph.json
    ↓
向量库 → Qdrant Collections
```

---

## 7. 关键配置

### 环境变量

```bash
HF_HOME=E:\huggingface_cache
HF_ENDPOINT=https://hf-mirror.com
```

### Qdrant配置

```yaml
host: localhost
port: 6333
collections:
  - case_library
  - creation_context
  - novel_settings
  - writing_techniques
```

---

## 8. 文件统计汇总

| 类型 | 数量 | 主要位置 |
|------|------|---------|
| Python | 166 | core/, modules/, tests/, .vectorstore/sync/ |
| Markdown | 202 | 创作技法/, 设定/, 正文/, docs/ |
| JSON | 8 | 章节经验日志/, .vectorstore/ |
| HTML | 4 | .vectorstore/ (可视化) |
| 其他 | 21 | 配置、脚本等 |

---

## 9. 模块状态说明

### 核心驱动路径

当前小说工作流通过 **Skill 系统** 驱动，而非 Python 模块：

```
对话请求 → novelist-* Skills → 文件读取 / 向量检索 → 输出
```

### 模块状态表

| 模块/目录 | 状态 | 当前用途 | 扩展预留 |
|-----------|------|----------|----------|
| novelist-* Skills | ✅ 启用 | 5作家+1审核，对话核心驱动 | - |
| .vectorstore/ | ✅ 启用 | Qdrant向量库、知识图谱、场景映射 | - |
| 创作技法/ | ✅ 启用 | 11维度技法库，Skill检索源 | - |
| 设定/ | ✅ 启用 | 世界观/角色设定，Skill检索源 | - |
| core/ | ⚠️ 扩展备用 | 对话中不使用 | CLI/Web后端/API |
| modules/ | ⚠️ 扩展备用 | 对话中不使用 | 功能模块化 |

### 扩展模块清单

| Python 模块 | 预留功能 | 启用条件 |
|-------------|----------|----------|
| core/cli.py | CLI命令入口 | 需要命令行工具时 |
| core/config_manager.py | 配置管理 | Web/API需要配置对象 |
| core/db_connection.py | 数据库连接+降级模式 | 独立Python程序 |
| core/health_check.py | 健康检查 | 自动化运维脚本 |
| modules/knowledge_base/ | 向量库同步/检索 | Web后端/API |
| modules/validation/ | 章节评估 | Web评估报告界面 |
| modules/feedback/ | 用户反馈处理 | Web反馈系统 |
| modules/visualization/ | 可视化 | Web可视化界面 |
| modules/migration/ | 项目迁移 | 批量迁移脚本 |

---

## 10. 待办事项

- [ ] BGE-M3向量迁移
- [ ] 启用混合检索模式
- [ ] 补充地理设定
- [ ] 更新势力文化习俗

---

*文档生成: 2026-04-04*
*分析工具: 后序遍历目录树分析器*
*模块状态: 已标注 core/modules 为扩展备用*