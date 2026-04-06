# .vectorstore 目录重构建议

## 当前问题

### 1. 目录混乱

```
当前 .vectorstore/ 目录：
├── 核心模块（应保留）
│   ├── knowledge_search.py
│   ├── technique_search.py
│   ├── workflow.py
│   ├── knowledge_graph.py
│   ├── data_model.py
│   └── knowledge_vectorizer.py, technique_vectorizer.py
│
├── 同步脚本（应整理）
│   ├── sync_to_vectorstore_v3.py
│   ├── rebuild_knowledge_graph_v2.py
│   └── sync_*.py 系列
│
├── 验证脚本（应整理）
│   ├── verify_*.py 系列（20+个）
│   └── check_*.py 系列（10+个）
│
├── 测试脚本（应整理）
│   ├── test_*.py 系列
│   └── _analyze.py, _full_analyze.py
│
└── 历史存档（应移除）
    └── （已移到存档/）
```

**问题**：
- 核心功能、工具脚本、测试脚本混在一起
- 文件过多（40+个），难以维护
- 新人难以理解项目结构

---

## 重构方案

### 方案 A：按功能分类（推荐）

```
.vectorstore/
│
├── core/                          # 核心功能（长期维护）
│   ├── __init__.py
│   ├── knowledge_search.py        # 小说设定检索
│   ├── technique_search.py        # 创作技法检索
│   ├── case_search.py             # 案例检索
│   ├── workflow.py                # 统一工作流入口
│   ├── knowledge_graph.py         # 知识图谱
│   ├── data_model.py              # 数据模型
│   └── vectorizer/                # 向量化器
│       ├── knowledge_vectorizer.py
│       └── technique_vectorizer.py
│
├── sync/                          # 同步脚本（定期执行）
│   ├── sync_to_vectorstore.py     # 主同步脚本
│   ├── rebuild_knowledge_graph.py # 重建知识图谱
│   └── batch_sync.py              # 批量同步
│
├── tools/                         # 工具脚本（按需执行）
│   ├── verify/                    # 验证工具
│   │   ├── verify_all.py
│   │   ├── verify_structures.py
│   │   └── verify_sync.py
│   ├── check/                     # 检查工具
│   │   ├── check_entity.py
│   │   ├── check_techniques.py
│   │   └── check_missing.py
│   └── debug/                     # 调试工具
│       ├── db_viewer.py
│       └── debug_names.py
│
├── archived/                      # 历史存档（只读）
│   └── （历史脚本）
│
└── config/                        # 配置文件
    ├── qdrant_config.json
    └── mapping_config.json
```

---

### 方案 B：按模块分类

```
.vectorstore/
│
├── search/                        # 检索模块
│   ├── knowledge_search.py
│   ├── technique_search.py
│   └── case_search.py
│
├── sync/                          # 同步模块
│   ├── sync_manager.py
│   └── rebuild_*.py
│
├── graph/                         # 图谱模块
│   ├── knowledge_graph.py
│   └── graph_visualizer.py
│
└── utils/                         # 工具模块
    ├── data_model.py
    └── verify_*.py
```

---

## 重构步骤

### 阶段 1：创建新目录结构

```bash
cd D:\动画\众生界\.vectorstore

# 创建新目录
mkdir core
mkdir sync
mkdir tools\verify
mkdir tools\check
mkdir tools\debug
mkdir archived
mkdir config
```

### 阶段 2：移动核心文件

```bash
# 移动核心模块
move knowledge_search.py core\
move technique_search.py core\
move case_search.py core\
move workflow.py core\
move knowledge_graph.py core\
move data_model.py core\
move knowledge_vectorizer.py core\
move technique_vectorizer.py core\

# 创建 __init__.py
echo. > core\__init__.py
```

### 阶段 3：移动同步脚本

```bash
# 移动同步脚本
move sync_to_vectorstore_v3.py sync\sync_to_vectorstore.py
move rebuild_knowledge_graph_v2.py sync\rebuild_knowledge_graph.py
move sync_cases.py sync\
```

### 阶段 4：移动工具脚本

```bash
# 移动验证脚本
move verify_*.py tools\verify\

# 移动检查脚本
move check_*.py tools\check\

# 移动调试脚本
move db_viewer.py tools\debug\
move debug_*.py tools\debug\
```

### 阶段 5：移动历史脚本

```bash
# 已在存档目录的跳过
# 其他过时脚本移到 archived
move _analyze.py archived\
move _full_analyze.py archived\
```

### 阶段 6：更新导入路径

```python
# 更新 modules/creation/ 中的导入

# 旧路径
from .vectorstore.knowledge_search import KnowledgeSearcher

# 新路径
from .vectorstore.core.knowledge_search import KnowledgeSearcher
```

---

## 迁移影响分析

### 需要更新的文件

| 文件 | 变更内容 |
|------|----------|
| `modules/creation/workflow_scheduler.py` | 更新导入路径 |
| `modules/creation/writer_executor.py` | 更新导入路径 |
| `modules/knowledge_base/*.py` | 更新导入路径 |
| `core/cli.py` | 更新命令路径 |
| `.vectorstore/core/__init__.py` | 新建，导出核心模块 |

### 向后兼容方案

```python
# .vectorstore/__init__.py
"""
向后兼容层

保留旧的导入路径，重定向到新位置。
"""

# 旧导入方式仍然可用
from .core.knowledge_search import KnowledgeSearcher
from .core.technique_search import TechniqueSearcher
from .core.workflow import NovelWorkflow

__all__ = [
    "KnowledgeSearcher",
    "TechniqueSearcher", 
    "NovelWorkflow",
]
```

---

## 重构收益

| 方面 | 改善 |
|------|------|
| **可维护性** | 核心功能与工具脚本分离，职责清晰 |
| **可发现性** | 新人能快速找到需要的文件 |
| **可扩展性** | 新功能有明确的放置位置 |
| **可测试性** | 核心模块独立，便于单元测试 |

---

## CLI 命令更新

```bash
# 旧命令
python -m core kb --sync all

# 新命令（保持兼容）
python -m core kb --sync all          # 仍然可用
python -m .vectorstore.sync.sync_to_vectorstore  # 直接调用

# 新增命令
python -m core health                 # 健康检查
python -m core verify --all           # 运行所有验证
```

---

## 建议优先级

| 优先级 | 任务 | 预计时间 |
|--------|------|----------|
| P0 | 创建新目录结构 | 10分钟 |
| P1 | 移动核心文件 | 20分钟 |
| P2 | 创建向后兼容层 | 15分钟 |
| P3 | 更新导入路径 | 30分钟 |
| P4 | 移动工具脚本 | 20分钟 |
| P5 | 测试验证 | 30分钟 |

**总预计时间：约2小时**

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 导入路径变更 | 高 | 使用向后兼容层 |
| 脚本路径变更 | 中 | 更新 CLI 和文档 |
| 测试覆盖不足 | 中 | 重构后运行完整测试 |

---

## 执行建议

1. **备份**：重构前备份整个 .vectorstore 目录
2. **分支**：在 Git 分支上进行重构
3. **测试**：重构后运行 `python -m core health` 验证
4. **文档**：更新相关文档和 README