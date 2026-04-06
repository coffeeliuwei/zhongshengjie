# 众生界 API 文档

> 本文档记录重构后的模块API和CLI接口
> 
> **兼容性说明**：所有数据库相关操作支持自动降级，当 Qdrant 不可用时使用本地缓存。

---

## 零、数据库兼容性

### 自动降级机制

系统在检测到 Qdrant 不可用时自动切换到本地缓存模式：

```python
from modules.knowledge_base import KnowledgeBase

kb = KnowledgeBase()

# 检查是否降级模式
if kb.is_degraded:
    print("使用本地缓存模式")

# 获取数据库状态
info = kb.check_database()
print(f"状态: {info['status']}")  # available/degraded/unavailable
```

### CLI 检查命令

```bash
# 检查数据库状态
python -m core kb --db-status
```

### 降级行为

| 功能 | Qdrant 可用 | Qdrant 不可用 |
|------|-------------|---------------|
| 同步 | 向量存储 | JSON 文件 |
| 检索 | 向量搜索 | 文本匹配 |
| 缓存 | Docker 卷 | `.cache/` 目录 |

详细说明见：[DATABASE_COMPATIBILITY.md](DATABASE_COMPATIBILITY.md)

---

## 一、CLI 命令行接口

### 1.1 配置管理 (config)

#### 显示配置

```bash
python -m core config --show
```

输出当前配置摘要，包括项目路径、数据库连接、模块状态等。

#### 初始化配置

```bash
python -m core config --init
```

初始化项目配置，创建目录结构，生成 `system_config.json`。

#### 添加自定义资源

```bash
python -m core config --add-resource <资源ID> <资源路径>
```

示例：
```bash
python -m core config --add-resource 玄幻奇幻 "E:\小说资源\玄幻奇幻"
```

---

### 1.2 知识入库 (kb)

#### 数据库统计

```bash
python -m core kb --stats
```

显示向量数据库统计信息（各集合的条目数量）。

#### 同步数据

```bash
python -m core kb --sync <类型>
```

类型选项：
- `novel` - 同步小说设定
- `technique` - 同步创作技法
- `case` - 同步案例库
- `all` - 同步全部

#### 检索数据

```bash
# 检索小说设定
python -m core kb --search-novel "关键词"

# 检索创作技法
python -m core kb --search-technique "关键词" --dimension "维度名称"

# 检索案例
python -m core kb --search-case "关键词" --scene "场景类型"
```

---

### 1.3 验证管理 (validate)

#### 运行验证

```bash
# 运行所有验证
python -m core validate --all

# 快速验证（跳过耗时检查）
python -m core validate --quick

# 验证指定章节
python -m core validate --chapter "第一章-天裂"
```

#### 验证历史

```bash
python -m core validate --history
```

显示验证历史记录。

---

### 1.4 创作管理 (create)

#### 执行工作流

```bash
python -m core create --workflow
```

执行完整的创作工作流（基于 scene_writer_mapping.json）。

#### 创作场景

```bash
python -m core create --scene "战斗场景"
```

创作指定类型的场景。

#### 评估章节

```bash
python -m core create --evaluate "正文/第一章-天裂.md"
```

评估章节内容（使用 novelist-evaluator）。

---

### 1.5 移植管理 (migrate)

#### 导出模板

```bash
python -m core migrate --export-template --target <目标目录>
```

导出项目模板（保留结构和工具，清空数据）。

#### 初始化环境

```bash
python -m core migrate --init-environment
```

初始化新环境，创建目录结构和配置文件。

---

### 1.6 可视化 (visualize)

#### 知识图谱

```bash
python -m core visualize --graph
```

生成知识图谱可视化（HTML格式）。

#### 统计可视化

```bash
python -m core visualize --stats
```

生成项目统计可视化。

---

## 二、模块 API

### 2.1 核心模块 (core)

#### ConfigManager

```python
from core import ConfigManager

# 初始化配置管理器
config = ConfigManager(project_root)

# 获取数据库连接URL
db_url = config.get_db_connection_url()

# 获取集合名称
collection_name = config.get_collection_name("novel_settings")

# 确保目录存在
config.ensure_directories()

# 更新自定义资源
config.update_custom_resource("玄幻奇幻", Path("E:\\小说资源\\玄幻奇幻"))

# 保存配置
config.save_system_config()

# 获取配置摘要
summary = config.get_config_summary()
```

#### PathManager

```python
from core import PathManager

# 初始化路径管理器
paths = PathManager()

# 获取核心文件路径
config_file = paths.config_file
project_guide = paths.project_guide

# 获取设定文件路径
character_profiles = paths.character_profiles
factions = paths.factions
power_system = paths.power_system

# 获取追踪系统路径
hook_ledger = paths.hook_ledger
payoff_tracking = paths.payoff_tracking

# 获取系统路径
workflow_script = paths.workflow_script
knowledge_graph = paths.knowledge_graph

# 获取模块目录
kb_module = paths.get_module_dir("knowledge_base")

# 自定义资源路径
resource_path = paths.get_custom_resource("玄幻奇幻")
paths.add_custom_resource("武侠仙侠", Path("E:\\小说资源\\武侠仙侠"))
```

---

### 2.2 创作模块 (modules.creation)

#### WriterContextManager

```python
from modules.creation import WriterContextManager
from modules.creation.writer_context_manager import WriterOutput

# 初始化上下文管理器
context_manager = WriterContextManager(
    qdrant_host="localhost",
    qdrant_port=6333
)

# 创建作家输出
output = WriterOutput(
    session_id="session_001",
    chapter_name="第一章-天裂",
    scene_type="战斗场景",
    phase="核心",
    writer_name="剑尘",
    writer_skill="novelist-jianchen",
    content="血牙挥舞战刀...",
    iteration=0
)

# 保存输出
output_id = context_manager.save_writer_output(output)

# 检索上下文
context = context_manager.retrieve_context(
    chapter_name="第一章-天裂",
    scene_type="战斗场景"
)

# 搜索相似上下文
similar = context_manager.search_similar_context(
    query_content="血脉燃烧的力量",
    scene_type="战斗场景"
)

# 获取迭代历史
history = context_manager.get_iteration_history(
    session_id="session_001",
    chapter_name="第一章-天裂",
    scene_type="战斗场景"
)

# 清理过期上下文
cleaned_count = context_manager.cleanup_old_context()

# 获取统计
stats = context_manager.get_stats()
```

#### ParallelExecutionManager

```python
from modules.creation import ParallelExecutionManager
from modules.creation.parallel_execution_manager import ParallelConfig, WriterTask

# 配置并行执行
config = ParallelConfig(
    max_parallel_writers=3,
    timeout_per_writer=300,
    retry_on_failure=True
)

# 初始化管理器
executor = ParallelExecutionManager(config)

# 创建任务
tasks = [
    WriterTask(
        task_id="task_001",
        writer_name="苍澜",
        writer_skill="novelist-canglan",
        scene_type="世界观",
        phase="前置",
        input_context={"chapter": "第一章"}
    ),
    WriterTask(
        task_id="task_002",
        writer_name="玄一",
        writer_skill="novelist-xuanyi",
        scene_type="剧情",
        phase="核心",
        input_context={"chapter": "第一章"}
    )
]

# 定义作家执行函数
def writer_function(writer_name, writer_skill, scene_type, phase, input_context):
    # 调用作家skill进行创作
    # 返回创作内容
    return "创作内容"

# 并行执行
results = executor.execute_parallel_tasks(tasks, writer_function)

# 获取摘要
summary = executor.get_execution_summary()

# 关闭执行器
executor.shutdown()
```

---

### 2.3 移植模块 (modules.migration)

#### TemplateExporter

```python
from modules.migration import TemplateExporter
from pathlib import Path

# 初始化导出器
exporter = TemplateExporter(project_root)

# 导出模板
stats = exporter.export_template(
    target_dir=Path("../new-project"),
    preserve_structure=True,
    create_examples=True
)
```

#### EnvironmentInitializer

```python
from modules.migration import EnvironmentInitializer
from pathlib import Path

# 初始化环境初始化器
initializer = EnvironmentInitializer(project_root)

# 初始化环境
stats = initializer.initialize(
    create_examples=True,
    init_vectorstore=False
)
```

---

## 三、集成示例

### 3.1 完整创作流程

```python
from core import ConfigManager, PathManager
from modules.creation import WriterContextManager, ParallelExecutionManager
from modules.creation.writer_context_manager import WriterOutput
from modules.creation.parallel_execution_manager import ParallelConfig, WriterTask

# 1. 初始化
config = ConfigManager()
paths = PathManager()
context_manager = WriterContextManager()
executor = ParallelExecutionManager(ParallelConfig())

# 2. 准备任务
tasks = [
    WriterTask(
        task_id="task_001",
        writer_name="苍澜",
        writer_skill="novelist-canglan",
        scene_type="世界观",
        phase="前置",
        input_context={"chapter": "第一章"}
    ),
    WriterTask(
        task_id="task_002",
        writer_name="玄一",
        writer_skill="novelist-xuanyi",
        scene_type="剧情",
        phase="核心",
        input_context={"chapter": "第一章"}
    )
]

# 3. 执行创作
def writer_function(writer_name, writer_skill, scene_type, phase, input_context):
    # 调用作家skill
    # 返回创作内容
    return "创作内容"

results = executor.execute_parallel_tasks(tasks, writer_function)

# 4. 保存上下文
for task in results["completed"]:
    output = WriterOutput(
        session_id="session_001",
        chapter_name="第一章",
        scene_type=task.scene_type,
        phase=task.phase,
        writer_name=task.writer_name,
        writer_skill=task.writer_skill,
        content=task.output,
        iteration=0
    )
    context_manager.save_writer_output(output)

# 5. 清理
executor.shutdown()
```

---

## 四、原有接口（保留）

### 4.1 workflow.py

原有 `workflow.py` 接口保持不变，可直接使用：

```bash
cd .vectorstore
python workflow.py --stats
python workflow.py --search-novel "关键词"
python workflow.py --search-technique "关键词"
python workflow.py --search-case "关键词"
```

### 4.2 verify_all.py

原有验证接口保持不变：

```bash
cd .vectorstore
python verify_all.py
python verify_all.py --quick
```

---

## 五、配置文件

### 5.1 CONFIG.md

项目基本配置（小说信息、文风配置、评估阈值）。

### 5.2 system_config.json

系统详细配置（数据库、目录、模块、作家）。

---

*API版本: 2.0*
*更新时间: 2026-04-02*