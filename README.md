# 众生界

<p align="center">
  <img src="assets/unnamed.png" alt="众生界" width="600">
</p>

<p align="center">
  <i>千山无名谁曾记，万骨归尘风不知</i>
</p>

<p align="center">
  <i>山风吹尽千年事，更有何人问此时</i>
</p>

---

## 简介

天无主，地无归处。

千年时光流转，众生在洪流中浮沉。

那些鲜活的人——有过名字，有过希望。
如今，名字尘封在岁月深处。

众生皆苦，众生在追问：我是谁？

无人应答。

风穿过无名的墓，穿过荒野的风，穿过那些从未被铭记的人。
他们曾以为自己知道答案。

千年的追问，既无答案，也无尽头。
却如同一粒尘埃，静默地宣布自己存在过。

去问风，去问那些死在黎明前的人——
时光之下，皆是众生。

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
- **场景契约系统**：解决多作家并行创作拼接冲突（12大一致性规则）

---

## 文档索引

| 文档 | 用途 |
|------|------|
| [AI项目掌控手册](docs/AI项目掌控手册.md) | AI快速理解项目全貌 |

> 本项目文档极简，仅保留README.md（用户）和AI项目掌控手册.md（AI）。`docs/archived/` 目录包含历史文档。

---

## 快速开始

### 第一步：安装依赖

```bash
# 克隆项目
git clone https://github.com/coffeeliuwei/zhongshengjie.git
cd zhongshengjie

# 安装Python依赖
pip install -r requirements.txt

# 启动Qdrant向量数据库
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

### 第二步：配置系统（⚠️ 必须完成）

```bash
# 1. 复制配置模板
cp config.example.json config.json

# 2. 编辑 config.json，修改以下必填项：
```

**必填配置项**：

```json
{
  "paths": {
    "project_root": "D:/动画/众生界",           // 👈 改为你的项目路径
    "skills_base_path": "C:/Users/你的用户名/.agents/skills"  // 👈 Skills安装目录
  },
  "model": {
    "model_path": "E:/huggingface_cache/...",  // 👈 BGE-M3模型路径（可选，null自动检测）
    "hf_cache_dir": "E:/huggingface_cache"     // 👈 HuggingFace缓存目录（可选）
  },
  "novel_sources": {
    "directories": ["E:\\小说资源"]            // 👈 小说资源目录（可选）
  }
}
```

**关键配置说明**：

| 配置项 | 说明 | 如何获取 |
|--------|------|----------|
| `project_root` | 项目根目录 | 项目所在文件夹路径 |
| `skills_base_path` | Skills安装目录 | 默认 `~/.agents/skills`，查看：`ls ~/.agents/skills` |
| `model_path` | BGE-M3模型路径 | 已下载模型则填写，否则设为 `null` 自动检测 |
| `hf_cache_dir` | HuggingFace缓存目录 | 模型下载位置，Windows常见 `E:/huggingface_cache` |

**Windows 路径格式**：
```json
// ✅ 推荐
"path": "D:/动画/众生界"
"path": "D:\\动画\\众生界"

// ❌ 错误（单反斜杠会转义）
"path": "D:\动画\众生界"
```

### 第三步：构建数据

```bash
# 一键构建所有数据
python tools/build_all.py

# 检查构建状态
python tools/build_all.py --status
```

### 第四步：开始创作

在AI对话中说：**"写第一章"**

系统将自动执行：需求澄清 → 大纲解析 → 场景创作 → 评估 → 输出

---

## 配置项详解

### 路径配置 (`paths`)

```json
{
  "paths": {
    "project_root": null,           // 项目根目录，null自动检测
    "settings_dir": "设定",          // 设定文件目录
    "techniques_dir": "创作技法",     // 技法目录
    "content_dir": "正文",           // 已创作正文目录
    "skills_base_path": null,        // Skills安装目录
    "cache_dir": ".cache",           // 缓存目录
    "contracts_dir": "scene_contracts"  // 场景契约存储子目录
  }
}
```

### 校验规则配置 (`validation`)

```json
{
  "validation": {
    // 境界等级顺序（用于检测境界倒退）
    "realm_order": ["凡人", "觉醒", "淬体", "凝脉", "结丹", "元婴", "化神"],
    // 跳过的校验规则
    "skip_rules": []
  }
}
```

**自定义境界体系**：
```json
// 玄幻小说
"realm_order": ["炼气", "筑基", "金丹", "元婴", "化神", "渡劫", "大乘"]

// 跳过境界检测
"realm_order": null
```

### 数据库配置 (`database`)

```json
{
  "database": {
    "qdrant_host": "localhost",
    "qdrant_port": 6333,
    "timeout": 10  // 操作超时（秒）
  }
}
```

### 模型配置 (`model`)

```json
{
  "model": {
    "embedding_model": "BAAI/bge-m3",
    "model_path": null,      // null自动检测
    "batch_size": 20         // 批处理大小，内存充足可增大
  }
}
```

### 检索配置 (`retrieval`)

```json
{
  "retrieval": {
    "dense_limit": 100,       // 稠密向量检索数量
    "sparse_limit": 100,      // 稀疏向量检索数量
    "fusion_limit": 50,       // 混合检索融合数量
    "max_content_length": 3000  // 内容最大长度
  }
}
```

---

## 验证配置

```bash
# 快速检查
python tools/build_all.py --status

# 详细检查
python -c "
import sys; sys.path.insert(0, '.vectorstore')
from config_loader import *
print(f'项目: {get_project_root()}')
print(f'Skills: {get_skills_base_path()}')
print(f'模型: {get_model_path() or \"自动检测\"}')
print(f'Qdrant: {get_qdrant_url()}')
"
```

---

## 常见问题

### Q: Skills目录在哪里？

```bash
# 默认位置
~/.agents/skills           # Linux/Mac
C:\Users\你的用户名\.agents\skills  # Windows

# 查看已安装Skills
ls ~/.agents/skills
# 输出：
# novelist-canglan/   (苍澜-世界观架构师)
# novelist-xuanyi/    (玄一-剧情编织师)
# novelist-moyan/     (墨言-人物刻画师)
# novelist-jianchen/  (剑尘-战斗设计师)
# novelist-yunxi/     (云溪-意境营造师)
# novelist-evaluator/ (审核评估师)
```

### Q: BGE-M3模型如何下载？

```bash
# 方法1：自动下载（首次运行时）
python tools/build_all.py

# 方法2：手动下载
# 从 HuggingFace 下载 BAAI/bge-m3
# 解压到：E:/huggingface_cache/hub/models--BAAI--bge-m3/snapshots/xxx

# 方法3：使用镜像
export HF_ENDPOINT=https://hf-mirror.com
```

### Q: 配置不生效？

1. 检查文件名：必须是 `config.json`（不是 `config.example.json`）
2. 检查JSON格式：使用 [JSONLint](https://jsonlint.com/) 校验
3. 重启Python进程：配置在启动时加载

---

## 系统架构

### 创作流程（8阶段）

```
需求澄清 → 大纲解析 → 场景识别 → 经验检索 → 设定检索 → 场景契约 → 逐场景创作 → 整章评估 → 经验写入
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
│   ├── AI项目掌控手册.md  # AI专用文档
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
- `章节大纲/` - 章节规划
- `config.json` - 用户配置（含本地路径）

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