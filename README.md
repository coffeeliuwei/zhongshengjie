# 众生界

> 多Agent协作小说创作系统

---

## 项目简介

基于AI的小说创作辅助系统，采用Anthropic Harness架构实现Generator/Evaluator分离的多Agent协作创作。

**核心特性**：
- 5位专业作家 + 1位审核评估师
- 技法库/知识库/案例库向量检索
- 章节经验自动沉淀
- 用户反馈闭环机制

---

## 文档索引

| 文档 | 用途 | 读者 |
|------|------|------|
| [新人快速上手指南](docs/新人快速上手指南.md) | 从零构建自己的小说创作系统 | 新用户 |
| [AI项目掌控手册](docs/AI项目掌控手册.md) | AI快速理解项目全貌 | AI/开发者 |

---

## 快速开始

### 新用户

```bash
# 1. 克隆项目
git clone https://github.com/coffeeliuwei/zhongshengjie.git

# 2. 一键构建
python tools/build_all.py

# 3. 开始创作
# 在对话中说 "写第一章"
```

详细步骤请阅读 [新人快速上手指南](docs/新人快速上手指南.md)

### 创作命令

| 命令 | 说明 |
|------|------|
| `写第一章` | 启动章节创作 |
| `帮我重写 第一章` | 情节保留重写 |
| `查看评估报告` | 查看审核结果 |

---

## 系统架构

### 创作流程

```
需求澄清 → 大纲解析 → 场景识别 → 设定检索 → 逐场景创作 → 整章评估 → 经验写入
```

### 作家分工

| 作家 | Skill | 专长 |
|------|-------|------|
| 苍澜 | novelist-canglan | 世界观架构 |
| 玄一 | novelist-xuanyi | 剧情编织 |
| 墨言 | novelist-moyan | 人物刻画 |
| 剑尘 | novelist-jianchen | 战斗设计 |
| 云溪 | novelist-yunxi | 意境营造 |
| Evaluator | novelist-evaluator | 审核评估 |

### 数据库

| Collection | 用途 |
|------------|------|
| writing_techniques_v2 | 创作技法检索 |
| novel_settings_v2 | 小说设定检索 |
| case_library_v2 | 标杆案例检索 |

### 技术栈

- **向量数据库**: Qdrant (Docker, localhost:6333)
- **嵌入模型**: BGE-M3 (1024维)
- **Agent系统**: Claude + Skills

---

## 目录结构

```
众生界/
├── tools/              # 数据构建工具
├── .vectorstore/       # 向量检索代码
├── core/               # 核心模块（预留）
├── modules/            # 功能模块（预留）
├── docs/               # 文档
│   ├── 新人快速上手指南.md
│   ├── AI项目掌控手册.md
│   └── archived/       # 归档文档
├── config.example.json # 配置模板
└── README.md
```

**敏感数据（不推送GitHub）**：
- `创作技法/` - 技法库
- `设定/` - 小说设定
- `.case-library/` - 案例库
- `knowledge_graph.json` - 知识图谱
- `scene_writer_mapping.json` - 场景映射

---

## 构建工具

| 工具 | 用途 |
|------|------|
| `build_all.py` | 一键构建全部 |
| `technique_builder.py` | 构建技法库 |
| `knowledge_builder.py` | 构建知识库 |
| `scene_mapping_builder.py` | 构建场景映射 |
| `case_builder.py` | 构建案例库 |

---

## 开发状态

| 模块 | 状态 |
|------|------|
| 核心工作流 | ✅ 完成 |
| 多Agent调度 | ✅ 完成 |
| 向量数据库 | ✅ 完成 |
| 数据构建工具 | ✅ 完成 |

---

> 此项目为教学用，不允许批量生成小说用于商业