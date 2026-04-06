# AI项目掌控手册

> 本文档帮助AI快速理解项目全貌，包含流程、用法、数据、数据源等一切必要信息

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
```

### 1.3 核心组件

| 组件 | 位置 | 作用 |
|------|------|------|
| Skills | ~/.agents/skills/ | 作家技能定义 |
| 向量检索 | .vectorstore/core/ | Qdrant检索接口 |
| 工作流 | .vectorstore/core/workflow.py | 检索协调 |
| 数据构建 | tools/*.py | 构建各种数据 |

---

## 二、创作流程

### 2.1 完整流程

```
阶段0: 需求澄清
    ↓ 用户说 "写第一章"
阶段1: 章节大纲解析
    ↓ 读取 章节大纲/第一章大纲.md
阶段2: 场景类型识别
    ↓ 识别开篇/战斗/对话等场景
阶段2.5: 经验检索
    ↓ 检索 章节经验日志/ 前章经验
阶段3: 设定自动检索
    ↓ 向量检索 设定/ 相关内容
阶段4: 逐场景创作
    ↓ 5作家协作生成
阶段5: 整章整合
    ↓ 合并场景
阶段6: 整章评估
    ↓ Evaluator审核
阶段7: 经验写入
    ↓ 写入 章节经验日志/
```

### 2.2 触发命令

| 命令 | 触发流程 |
|------|----------|
| `写第N章` | 完整创作流程 |
| `重写第N章` | 情节保留重写 |
| `查看评估报告` | 显示Evaluator输出 |

### 2.3 作家调度

**固定3人并行前置**：
- 苍澜(世界观) + 玄一(剧情) + 墨言(人物)

**场景类型分配**（scene_writer_mapping.json）：
- 开篇/结尾 → 云溪
- 人物/情感 → 墨言
- 战斗/修炼 → 剑尘
- 悬念/转折 → 玄一
- 世界观展开 → 苍澜

---

## 三、数据源详解

### 3.1 技法库

**位置**: `创作技法/`

**结构**:
```
创作技法/
├── 01-世界观维度/
├── 02-剧情维度/
├── 03-人物维度/
├── 04-战斗冲突维度/
├── 05-氛围意境维度/
├── 06-情感维度/
├── 07-叙事维度/
├── 08-对话维度/
├── 09-描写维度/
├── 10-开篇维度/
├── 11-高潮维度/
└── 99-外部资源/
```

**文件格式**:
```markdown
# 技法名称

**技法名称**：伏笔设计

**适用场景**：
- 章节结尾悬念设置

**核心原理**：
[原理描述]

**具体示例**：
[示例内容]

**注意事项**：
1. [注意1]
```

**向量库**: `writing_techniques_v2`

**检索接口**: `.vectorstore/core/technique_search.py`

**检索参数**:
```python
TechniqueSearch.search(
    query="开篇 悬念设置",
    dimension="剧情维度",  # 可选
    scene="开篇场景",      # 可选
    writer="玄一",         # 可选
    top_k=5
)
```

### 3.2 知识库（设定）

**位置**: `设定/`

**核心文件**:
| 文件 | 内容 |
|------|------|
| 总大纲.md | 全书剧情规划 |
| 人物谱.md | 人物设定、弧光、关系 |
| 十大势力.md | 势力设定、关系网络 |
| 力量体系.md | 等级划分、能力类型 |
| 时间线.md | 事件时间顺序 |
| hook_ledger.md | 伏笔追踪表 |
| payoff_tracking.md | 承诺追踪表 |
| information_boundary.md | 信息边界管理 |

**向量库**: `novel_settings_v2`

**检索接口**: `.vectorstore/core/knowledge_search.py`

**知识图谱**: `.vectorstore/knowledge_graph.json`
- 人物节点
- 势力节点
- 关系边

### 3.3 案例库

**位置**: `.case-library/`

**结构**:
```
.case-library/
├── converted/      # 转换后的小说
├── cases/          # 提取的案例
│   ├── 开篇场景/
│   ├── 打脸场景/
│   ├── 战斗场景/
│   └── ...
├── scripts/        # 提取脚本
└── config.json     # 配置
```

**场景类型**:
| 类型 | 关键词 |
|------|--------|
| 开篇场景 | 第一章、序章 |
| 打脸场景 | 废物、嘲讽、震惊、震撼 |
| 高潮场景 | 决战、爆发、生死、巅峰 |
| 战斗场景 | 招、剑、刀、攻击、防御 |
| 对话场景 | 说道、问道、答道 |
| 情感场景 | 泪、感动、心疼、温暖 |
| 悬念场景 | 究竟、到底、秘密、真相 |
| 转折场景 | 突然、意外、反转、转折 |

**向量库**: `case_library_v2`

**检索接口**: `.vectorstore/core/case_search.py`

### 3.4 场景映射

**位置**: `.vectorstore/scene_writer_mapping.json`

**结构**:
```json
{
  "scene_to_writer": {
    "开篇场景": "novelist-yunxi",
    "战斗场景": "novelist-jianchen",
    ...
  },
  "writers": {
    "novelist-canglan": {
      "name": "苍澜",
      "specialty": "世界观架构师",
      ...
    }
  }
}
```

### 3.5 经验日志

**位置**: `章节经验日志/`

**文件**: `第一章经验.md`

**用途**: 前章经验自动检索，指导后续章节

### 3.6 用户反馈

**位置**: `写作标准积累/`

**状态流转**: `pending → applying → applied`

---

## 四、向量数据库

### 4.1 连接信息

```python
QDRANT_URL = "http://localhost:6333"
```

### 4.2 Collections

| Collection | 维度 | 数据量 | 用途 |
|------------|------|--------|------|
| writing_techniques_v2 | 1024 | 动态 | 创作技法 |
| novel_settings_v2 | 1024 | 动态 | 小说设定 |
| case_library_v2 | 1024 | 动态 | 标杆案例 |

### 4.3 嵌入模型

```python
MODEL = "BAAI/bge-m3"
VECTOR_SIZE = 1024
```

**特性**: Dense + Sparse 混合检索

### 4.4 检索接口

**技法检索**:
```python
from .vectorstore.core.technique_search import TechniqueSearch
searcher = TechniqueSearch()
results = searcher.search("伏笔设计", top_k=5)
```

**设定检索**:
```python
from .vectorstore.core.knowledge_search import KnowledgeSearch
searcher = KnowledgeSearch()
results = searcher.search("林雷", top_k=5)
```

**案例检索**:
```python
from .vectorstore.core.case_search import CaseSearch
searcher = CaseSearch()
results = searcher.search("开篇 世界观植入", scene_type="开篇场景", top_k=5)
```

**统一检索**:
```python
from .vectorstore.core.workflow import WorkflowSearcher
workflow = WorkflowSearcher()

# 检索技法
techniques = workflow.search_techniques("开篇", dimension="开篇维度")

# 检索设定
settings = workflow.search_settings("林雷")

# 检索案例
cases = workflow.search_cases("战斗", scene_type="战斗场景")
```

---

## 五、Skills系统

### 5.1 Skills位置

```
~/.agents/skills/
├── novelist-canglan/
├── novelist-xuanyi/
├── novelist-moyan/
├── novelist-jianchen/
├── novelist-yunxi/
├── novelist-evaluator/
└── novelist-shared/
```

### 5.2 作家Skills

| Skill | 专长 | 负责场景 |
|-------|------|----------|
| novelist-canglan | 世界观架构 | 世界观展开、势力登场 |
| novelist-xuanyi | 剧情编织 | 悬念、转折、高潮 |
| novelist-moyan | 人物刻画 | 人物出场、情感、心理 |
| novelist-jianchen | 战斗设计 | 战斗、修炼、资源争夺 |
| novelist-yunxi | 意境营造 | 开篇、结尾、环境 |

### 5.3 共享规范 (novelist-shared)

**文风要求**:
- 禁止AI味表达
- 禁止古龙式描写
- 禁止过度形容词堆砌

**字数规则**:
- 单场景: 800-2000字
- 整章: 3000-8000字

**禁止项**:
- 禁止"总之"、"综上所述"
- 禁止"不得不说"、"让人不禁"
- 禁止过度心理描写

### 5.4 评估师 (novelist-evaluator)

**评估维度**:
| 维度 | 满分 | 及格线 |
|------|------|--------|
| 世界自洽 | 10 | 7 |
| 人物立体 | 10 | 6 |
| 情感真实 | 10 | 6 |
| 战斗逻辑 | 10 | 6 |
| 文风克制 | 10 | 6 |
| 剧情张力 | 10 | 6 |

**评估流程**:
1. 检查禁止项
2. 评估各维度得分
3. 生成修改建议
4. 决定通过/迭代

---

## 六、数据构建工具

### 6.1 一键构建

```bash
python tools/build_all.py
```

### 6.2 分类构建

**技法库**:
```bash
python tools/technique_builder.py --init
python tools/technique_builder.py --import 技法文件.md
python tools/technique_builder.py --sync
```

**知识库**:
```bash
python tools/knowledge_builder.py --init
# 编辑设定文件
python tools/knowledge_builder.py --build-graph
python tools/knowledge_builder.py --sync
```

**场景映射**:
```bash
python tools/scene_mapping_builder.py --init
python tools/scene_mapping_builder.py --show
python tools/scene_mapping_builder.py --set "开篇场景" "novelist-yunxi"
```

**案例库**:
```bash
python tools/case_builder.py --init
python tools/case_builder.py --scan E:/小说资源
python tools/case_builder.py --convert
python tools/case_builder.py --extract --limit 5000
python tools/case_builder.py --sync
```

### 6.3 数据管理

```bash
python tools/data_builder.py --init    # 初始化向量库
python tools/data_builder.py --status  # 查看状态
```

---

## 七、配置文件

### 7.1 config.example.json

```json
{
  "project": {
    "name": "我的小说"
  },
  "paths": {
    "data_base_path": ".",
    "techniques": "创作技法",
    "settings": "设定",
    "case_library": ".case-library"
  },
  "database": {
    "qdrant_host": "localhost",
    "qdrant_port": 6333,
    "collections": {
      "novel_settings": "novel_settings_v2",
      "writing_techniques": "writing_techniques_v2",
      "case_library": "case_library_v2"
    }
  },
  "model": {
    "embedding_model": "BAAI/bge-m3",
    "vector_size": 1024
  }
}
```

### 7.2 .gitignore

**排除的敏感数据**:
- `创作技法/`
- `设定/`
- `.case-library/`
- `knowledge_graph.json`
- `scene_writer_mapping.json`
- `正文/`
- `章节大纲/`
- `章节经验日志/`

**推送的功能代码**:
- `tools/`
- `core/`
- `modules/`
- `docs/`
- `config.example.json`

---

## 八、常见操作

### 8.1 更新设定

```bash
# 1. 编辑设定文件
vim 设定/人物谱.md

# 2. 重建知识图谱
python tools/knowledge_builder.py --build-graph

# 3. 同步到向量库
python tools/knowledge_builder.py --sync
```

### 8.2 添加技法

```bash
# 方法1：创建文件
vim 创作技法/02-剧情维度/新技法.md

# 方法2：导入外部资源
python tools/technique_builder.py --import 写作技法大全.md

# 同步
python tools/technique_builder.py --sync
```

### 8.3 检查系统状态

```bash
# 检查Docker
docker ps | grep qdrant

# 检查向量库
curl http://localhost:6333/collections

# 检查数据
python tools/data_builder.py --status
```

### 8.4 修复问题

**向量库连接失败**:
```bash
docker restart qdrant
curl http://localhost:6333/collections
```

**模型加载失败**:
```bash
# 设置环境变量
export BGE_M3_MODEL_PATH=/path/to/bge-m3

# 或在config.json中配置model_path
```

---

## 九、调试接口

### 9.1 测试检索

```python
# 测试技法检索
from tools.test_search import test_technique_search
test_technique_search("伏笔设计")

# 测试设定检索
from tools.test_search import test_knowledge_search
test_knowledge_search("林雷")

# 测试案例检索
from tools.test_search import test_case_search
test_case_search("开篇")
```

### 9.2 验证系统

```bash
python tools/verify_vectors.py
```

---

## 十、重要注意事项

### 10.1 数据分离原则

**敏感数据（不推送GitHub）**:
- 所有众生界小说相关数据
- 从外部提炼的技法
- 从外部提取的案例
- 知识图谱
- 场景映射

**功能代码（推送GitHub）**:
- 构建工具
- 检索代码
- 文档
- 配置模板

### 10.2 向量检索优先级

```
1. 向量库 (Qdrant)
2. 本地缓存
3. 文件回退
```

### 10.3 创作约束

- 禁止AI味表达
- 主角视角>=15%
- 单场景800-2000字
- 自动迭代最多3轮

---

> 本文档为AI快速理解项目全貌而编写，包含所有必要信息