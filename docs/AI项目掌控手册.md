# AI项目掌控手册

> 本文档帮助AI快速理解项目全貌，包含流程、配置、数据、API等一切必要信息
> 
> **AI新环境快速启动**：阅读本文档后即可配置运行项目

---

## 一、项目概述

### 1.1 项目定位

多Agent协作小说创作辅助系统，核心能力：
- **技法检索**：按场景/维度检索写作技法
- **设定检索**：自动检索相关设定确保一致性
- **案例检索**：参考标杆片段
- **多Agent协作**：5作家+1审核

### 1.2 技术架构

```
用户输入 → Skills (novelist-*) → 向量检索 → 生成内容 → 评估 → 输出
                ↑
         配置加载器 (core/config_loader.py)
                ↑
         config.json (用户配置)
```

### 1.3 核心组件

| 组件 | 位置 | 作用 |
|------|------|------|
| 配置加载器 | `core/config_loader.py` | 统一配置管理 |
| Skills | `~/.agents/skills/` | 作家技能定义 |
| 向量检索 | `.vectorstore/core/` | Qdrant检索接口 |
| 工作流 | `.vectorstore/core/workflow.py` | 检索协调 |
| 数据构建 | `tools/*.py` | 构建各种数据 |

---

## 二、配置系统（重要）

### 2.1 配置文件

| 文件 | 用途 | Git状态 |
|------|------|---------|
| `config.example.json` | 配置模板 | ✅ 推送GitHub |
| `config.json` | 用户配置 | ❌ 不推送（含敏感路径） |

### 2.2 快速配置

```bash
# 1. 复制模板
cp config.example.json config.json

# 2. 编辑配置（修改为您自己的路径）
# 必填项：project_root, model_path, novel_sources
```

### 2.3 配置项说明

```json
{
  "project": {
    "name": "我的小说",
    "version": "1.0.0"
  },
  
  "paths": {
    "project_root": null,
    "settings_dir": "设定",
    "techniques_dir": "创作技法",
    "vectorstore_dir": ".vectorstore",
    "case_library_dir": ".case-library",
    "logs_dir": "logs"
  },
  
  "database": {
    "qdrant_host": "localhost",
    "qdrant_port": 6333,
    "qdrant_url": "http://localhost:6333",
    "collections": {
      "novel_settings": "novel_settings_v2",
      "writing_techniques": "writing_techniques_v2",
      "case_library": "case_library_v2"
    }
  },
  
  "model": {
    "embedding_model": "BAAI/bge-m3",
    "model_path": null,
    "hf_cache_dir": null,
    "vector_size": 1024
  },
  
  "novel_sources": {
    "directories": ["E:\\小说资源"]
  }
}
```

### 2.4 配置加载API

```python
from core.config_loader import (
    get_config,           # 获取完整配置
    get_project_root,     # 项目根目录 Path
    get_model_path,       # 模型路径 str
    get_qdrant_url,       # Qdrant URL str
    get_novel_sources,    # 小说资源目录列表 [Path]
    get_settings_dir,     # 设定目录 Path
    get_techniques_dir,   # 技法目录 Path
    get_vectorstore_dir,  # 向量库目录 Path
    get_case_library_dir, # 案例库目录 Path
    get_logs_dir,         # 日志目录 Path
    get_hf_cache_dir,     # HuggingFace缓存目录 str
    get_collection_name,  # Collection名称
)
```

### 2.5 环境变量覆盖

| 环境变量 | 对应配置 |
|---------|---------|
| `NOVEL_PROJECT_ROOT` | `paths.project_root` |
| `NOVEL_CONFIG_PATH` | 配置文件路径 |
| `BGE_M3_MODEL_PATH` | `model.model_path` |
| `HF_HOME` | `model.hf_cache_dir` |

---

## 三、创作流程

### 3.1 完整流程

```
阶段0: 需求澄清 → 阶段1: 大纲解析 → 阶段2: 场景识别
→ 阶段3: 设定检索 → 阶段4: 逐场景创作 → 阶段5: 整章评估
```

### 3.2 触发命令

| 命令 | 触发流程 |
|------|----------|
| `写第N章` | 完整创作流程 |
| `重写第N章` | 情节保留重写 |
| `查看评估报告` | 显示Evaluator输出 |

### 3.3 作家调度

**固定3人并行前置**：苍澜(世界观) + 玄一(剧情) + 墨言(人物)

**场景类型分配**：
- 开篇/结尾 → 云溪
- 人物/情感 → 墨言
- 战斗/修炼 → 剑尘
- 悬念/转折 → 玄一
- 世界观展开 → 苍澜

---

## 四、数据源

### 4.1 技法库

| 项目 | 值 |
|------|-----|
| 位置 | `创作技法/` |
| 向量库 | `writing_techniques_v2` |
| 数据量 | 986条 |
| 接口 | `.vectorstore/core/technique_search.py` |

### 4.2 知识库

| 项目 | 值 |
|------|-----|
| 位置 | `设定/` |
| 向量库 | `novel_settings_v2` |
| 数据量 | 160条 |
| 接口 | `.vectorstore/core/knowledge_search.py` |

### 4.3 案例库

| 项目 | 值 |
|------|-----|
| 位置 | `.case-library/` |
| 向量库 | `case_library_v2` |
| 数据量 | 374K+条 |
| 接口 | `.vectorstore/core/case_search.py` |

---

## 五、向量数据库

### 5.1 连接

```python
from core.config_loader import get_qdrant_url
QDRANT_URL = get_qdrant_url()  # 默认 http://localhost:6333
```

### 5.2 Collections

| Collection | 数据量 | 用途 |
|------------|--------|------|
| writing_techniques_v2 | 986 | 创作技法 |
| novel_settings_v2 | 160 | 小说设定 |
| case_library_v2 | 374K+ | 标杆案例 |

### 5.3 模型

- 模型：`BAAI/bge-m3`
- 维度：1024
- 特性：Dense + Sparse 混合检索

---

## 六、Skills系统

### 6.1 位置

```
~/.agents/skills/
├── novelist-canglan/     # 世界观架构师
├── novelist-xuanyi/      # 剧情编织师
├── novelist-moyan/       # 人物刻画师
├── novelist-jianchen/    # 战斗设计师
├── novelist-yunxi/       # 意境营造师
├── novelist-evaluator/   # 审核评估师
└── novelist-shared/      # 共享规范
```

### 6.2 作家分工

| Skill | 专长 |
|-------|------|
| novelist-canglan | 世界观架构 |
| novelist-xuanyi | 剧情编织 |
| novelist-moyan | 人物刻画 |
| novelist-jianchen | 战斗设计 |
| novelist-yunxi | 意境营造 |

---

## 七、数据构建工具

### 7.1 一键构建

```bash
python tools/build_all.py
python tools/build_all.py --status
```

### 7.2 分类构建

```bash
# 技法库
python tools/technique_builder.py --init
python tools/technique_builder.py --sync

# 知识库
python tools/knowledge_builder.py --init
python tools/knowledge_builder.py --sync

# 案例库
python tools/case_builder.py --init
python tools/case_builder.py --scan
python tools/case_builder.py --sync

# 场景映射
python tools/scene_mapping_builder.py --init
```

---

## 八、常见操作

### 8.1 新环境初始化

```bash
# 1. 克隆项目
git clone https://github.com/xxx/zhongshengjie.git
cd zhongshengjie

# 2. 配置
cp config.example.json config.json
# 编辑 config.json

# 3. 启动Qdrant
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# 4. 构建
python tools/build_all.py

# 5. 验证
python tools/data_builder.py --status
```

### 8.2 检查系统

```bash
docker ps | grep qdrant
curl http://localhost:6333/collections
python tools/config_helper.py
python tools/data_builder.py --status
```

---

## 九、数据分离原则

### 推送到GitHub
- `tools/` - 构建工具
- `core/` - 核心模块
- `modules/` - 功能模块
- `.vectorstore/core/` - 检索代码
- `docs/` - 文档
- `config.example.json` - 配置模板

### 不推送（敏感数据）
- `创作技法/` - 技法库
- `设定/` - 小说设定
- `.case-library/` - 案例库
- `config.json` - 用户配置
- `knowledge_graph.json`
- `scene_writer_mapping.json`

---

## 十、API速查

### 配置API
```python
from core.config_loader import (
    get_config, get_project_root, get_model_path, 
    get_qdrant_url, get_novel_sources, get_settings_dir,
    get_techniques_dir, get_vectorstore_dir, get_case_library_dir
)
```

### 检索API
```python
from vectorstore.core.technique_search import TechniqueSearch
from vectorstore.core.knowledge_search import KnowledgeSearch
from vectorstore.core.case_search import CaseSearch
from vectorstore.core.workflow import WorkflowSearcher
```

---

> **配置文件**: `config.json` (用户) / `config.example.json` (模板)
> 
> **详细配置说明**: `docs/配置说明.md`