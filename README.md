# 众生界

<p align="center">
  <img src="assets/unnamed.png" alt="众生界" width="600">
</p>

<p align="center">
  <i>千山隐迹路何寻，万象归墟棋自沉</i>
</p>

<p align="center">
  <i>执子终成枰上客，风碑无言证浮沉</i>
</p>

---

## 简介

天无主，地无归处。

千年的博弈从未停歇。岁月来去如风，执子之人终化作棋子，
被棋局困在缝隙之间；缝隙里的他们，早把名字尘封。

众生皆苦，众生皆弈，众生在追问：我是谁？

无人应答的沉默里——
风穿过石碑的纹路，穿过荒野的盐霜，穿过黎明前无人铭记的日落。

这不是答案。

千年的追问，既无答案，也无尽头；
却如同一枚未落定的棋子，静默地宣布自己的存在。

去问风，去问碑，去问那些死在黎明前的人。
他们曾以为自己知道。

---

## 项目简介

基于AI的小说创作辅助系统，采用Anthropic Harness架构实现Generator/Evaluator分离的多Agent协作创作。

**核心特性**：
- 5位专业作家 + 1位审核评估师
- 技法库/知识库/案例库向量检索（BGE-M3混合检索）
- 章节经验自动沉淀与检索
- 用户反馈闭环机制
- **自动场景发现**：从外部小说库学习新场景类型
- **28种场景类型**：开篇/战斗/情感/悬念/转折等

---

## 文档索引

| 文档 | 用途 |
|------|------|
| [新人快速上手指南](docs/新人快速上手指南.md) | 从零构建小说创作系统 |
| [AI项目掌控手册](docs/AI项目掌控手册.md) | AI快速理解项目全貌 |
| [配置说明](docs/配置说明.md) | 配置文件详细说明 |

> `docs/archived/` 目录包含历史文档，仅供参考

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

### 创作流程（7阶段）

```
需求澄清 → 大纲解析 → 场景识别 → 经验检索 → 设定检索 → 逐场景创作 → 整章评估 → 经验写入
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

| Collection | 用途 | 数据量 |
|------------|------|--------|
| writing_techniques_v2 | 创作技法检索 | 986条 |
| novel_settings_v2 | 小说设定检索 | 160条 |
| case_library_v2 | 标杆案例检索 | **38万+条** |

### 技术栈

- **向量数据库**: Qdrant (Docker, localhost:6333)
- **嵌入模型**: BGE-M3 (1024维，Dense+Sparse+ColBERT混合检索)
- **Agent系统**: Claude + Skills (30个技能)

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
- `章节经验日志/` - 经验日志

---

## 构建工具

| 工具 | 用途 |
|------|------|
| `build_all.py` | 一键构建全部 |
| `technique_builder.py` | 构建技法库 |
| `knowledge_builder.py` | 构建知识库 |
| `case_builder.py` | 构建案例库 + 自动场景发现 |
| `scene_discoverer.py` | 自动发现新场景类型 |
| `scene_mapping_builder.py` | 构建场景映射 |

---

## 新功能

### 自动场景发现

从外部小说库自动学习新场景类型：

```bash
# 发现新场景
python tools/case_builder.py --discover

# 审批发现的场景
python tools/scene_discoverer.py --approve "交易场景"

# 应用到配置
python tools/case_builder.py --apply-discovered
```

### 经验检索

从前面章节提取可复用经验：

```python
from workflow import retrieve_chapter_experience

experience = retrieve_chapter_experience(
    current_chapter=3,
    scene_types=["战斗"],
    writer_name="剑尘"
)
```

---

## 开发状态

| 模块 | 状态 |
|------|------|
| 核心工作流 | ✅ 完成 |
| 多Agent调度 | ✅ 完成 |
| 向量数据库 | ✅ 完成 |
| 数据构建工具 | ✅ 完成 |
| 自动场景发现 | ✅ 完成 |
| 经验检索系统 | ✅ 完成 |
| 测试覆盖 | ✅ 85%+通过率 |

---

## 测试结果

| 测试模块 | 通过率 |
|----------|--------|
| 配置系统测试 | 100% |
| 向量数据库测试 | 100% |
| API接口测试 | 94.7% |
| 工作流逻辑测试 | 75% |

---

> 此项目为教学用，不允许批量生成小说用于商业