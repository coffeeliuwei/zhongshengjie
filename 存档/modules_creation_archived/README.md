# 创作模块 (modules/creation/)

> 作家工作流调度系统 - 基于场景-作家协作配置的多作家协同创作引擎

---

## 概述

创作模块是众生界项目的核心创作引擎，实现了基于 **Anthropic Harness** 设计原则的作家工作流调度系统。

### 核心特性

| 特性 | 说明 |
|------|------|
| **场景-作家协作** | 基于 `scene_writer_mapping.json` 的31种场景配置 |
| **Phase分层执行** | 前置 → 核心 → 收尾的三阶段执行模式 |
| **Generator/Evaluator分离** | 创作家与评估家职责分离 |
| **迭代循环控制** | 最多3次迭代的自动优化机制 |
| **并行执行支持** | 多作家并行创作，带超时控制 |
| **上下文持久化** | 基于向量数据库的作家输出存储 |

---

## 模块结构

```
modules/creation/
├── __init__.py              # 模块入口和导出
├── workflow_scheduler.py    # 核心工作流调度器
├── writer_executor.py       # 作家执行器（集成 novelist-* skills）
├── evaluator_executor.py    # 评估执行器（集成 novelist-evaluator）
├── writer_context_manager.py    # 作家上下文管理器
├── parallel_execution_manager.py # 并行执行管理器
├── api.py                   # 统一 API 接口
└── README.md                # 本文档
```

---

## 快速开始

### 方式1：使用统一 API

```python
from modules.creation import create_creation_api

# 创建 API 实例
api = create_creation_api()

# 获取可用场景
scenes = api.get_available_scenes()
print(f"可用场景: {scenes}")

# 创作场景
result = api.create_scene(
    scene_type="战斗场景",
    chapter="第一章-天裂",
    outline="血牙面对血战，血脉力量觉醒..."
)

print(f"创作成功: {result.success}")
print(f"内容长度: {len(result.content)} 字符")
print(f"迭代次数: {result.iterations}")

# 关闭
api.shutdown()
```

### 方式2：使用核心调度器

```python
from modules.creation import WorkflowScheduler
from pathlib import Path

# 创建调度器
scheduler = WorkflowScheduler(
    project_root=Path("D:/动画/众生界"),
    max_iterations=3,
)

# 执行工作流
result = scheduler.execute_workflow(
    scene_type="战斗场景",
    chapter_name="第一章-天裂",
    input_context={
        "outline": "场景大纲...",
        "existing_settings": "已有设定...",
    }
)

print(f"会话ID: {result.session_id}")
print(f"成功: {result.success}")
print(f"最终内容: {result.final_content}")

# 关闭
scheduler.shutdown()
```

### 方式3：使用 CLI

```bash
# 显示工作流信息
python -m core create --workflow

# 创作场景
python -m core create --scene "战斗场景" --chapter "第一章-天裂"

# 评估内容
python -m core create --evaluate "正文/第一章-天裂.md"
```

---

## 核心组件

### 1. WorkflowScheduler（工作流调度器）

**职责**：整体工作流协调

```python
class WorkflowScheduler:
    """工作流调度器"""
    
    def execute_workflow(scene_type, chapter_name, input_context) -> WorkflowResult:
        """执行完整工作流"""
        pass
    
    def execute_chapter_workflow(chapter_name, chapter_outline) -> List[WorkflowResult]:
        """执行章节完整工作流"""
        pass
    
    def get_available_scenes() -> List[str]:
        """获取可用场景列表"""
        pass
    
    def get_scene_info(scene_type) -> Dict:
        """获取场景详细信息"""
        pass
```

### 2. WriterExecutor（作家执行器）

**职责**：调用 novelist-* skills

```python
class WriterExecutor:
    """作家执行器"""
    
    def execute(writer_name, writer_skill, scene_type, phase, input_context) -> str:
        """执行作家创作"""
        pass
```

**支持的作家**：
| 作家 | 技能名称 | 专长 |
|------|----------|------|
| 苍澜 | novelist-canglan | 世界观架构 |
| 玄一 | novelist-xuanyi | 剧情编织 |
| 墨言 | novelist-moyan | 人物刻画 |
| 剑尘 | novelist-jianchen | 战斗设计 |
| 云溪 | novelist-yunxi | 氛围营造 |

### 3. EvaluatorExecutor（评估执行器）

**职责**：调用 novelist-evaluator skill

```python
class EvaluatorExecutor:
    """评估执行器"""
    
    def execute(content, scene_type, primary_writer, iteration, thresholds) -> Dict:
        """执行内容评估"""
        pass
```

**评估维度**：
- 禁止项检测（AI味表达、时间连接词等）
- 技法评估（世界自洽、人物立体、情感真实等）
- 整体质量评分

### 4. ParallelExecutionManager（并行执行管理器）

**职责**：多作家并行执行

```python
class ParallelExecutionManager:
    """并行执行管理器"""
    
    def execute_parallel_tasks(tasks, writer_function) -> Dict:
        """并行执行多个作家任务"""
        pass
    
    def execute_phase_sequence(phase_tasks, writer_function) -> Dict:
        """按Phase顺序执行任务"""
        pass
```

**配置**：
```python
ParallelConfig(
    max_parallel_writers=3,  # 最大并行作家数
    timeout_per_writer=300,  # 每个作家超时时间（秒）
    retry_on_failure=True,   # 失败重试
    max_retries=2,           # 最大重试次数
)
```

### 5. WriterContextManager（上下文管理器）

**职责**：作家输出持久化

```python
class WriterContextManager:
    """作家上下文管理器"""
    
    def save_writer_output(output: WriterOutput) -> str:
        """保存作家输出到向量数据库"""
        pass
    
    def retrieve_context(session_id, chapter_name, scene_type) -> List[WriterOutput]:
        """检索历史上下文"""
        pass
    
    def get_iteration_history(session_id, chapter_name, scene_type) -> List[WriterOutput]:
        """获取迭代历史"""
        pass
```

---

## 工作流设计

### Phase 执行模式

```
┌─────────────────────────────────────────────────────────┐
│                    Phase 执行流程                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Phase 1: 前置                                           │
│  ├── 设定输入                                            │
│  ├── 世界观约束                                          │
│  └── 并行作家: 苍澜、玄一                                 │
│           ↓                                              │
│  Phase 2: 核心                                           │
│  ├── 主要创作                                            │
│  ├── 场景内容输出                                        │
│  └── 并行作家: 墨言、剑尘                                 │
│           ↓                                              │
│  Phase 3: 收尾                                           │
│  ├── 润色输出                                            │
│  ├── 禁止项检测                                          │
│  └── 作家: 云溪                                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 迭代循环机制

```
┌─────────────────────────────────────────────────────────┐
│                    迭代循环流程                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Generator 输出                                          │
│       ↓                                                  │
│  Evaluator 评估                                          │
│       ↓                                                  │
│   ┌───┴───┐                                              │
│   通过？   否                                             │
│     ↓       ↓                                            │
│   结束   反馈给 Generator                                 │
│            ↓                                             │
│          Generator 修改                                   │
│            ↓                                             │
│          重新评估（迭代+1）                                │
│            ↓                                             │
│          迭代上限检查（最多3次）                           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 场景-作家协作示例

**战斗场景协作配置**：

```yaml
战斗场景:
  workflow_order: ["苍澜", "玄一", "墨言", "剑尘", "云溪"]
  primary_writer: "剑尘"
  
  collaboration:
    - writer: "苍澜"
      phase: "前置"
      role: "世界观输入"
      contribution: ["力量体系约束", "血脉代价设定"]
      weight: 0.15
      
    - writer: "玄一"
      phase: "前置"
      role: "剧情框架"
      contribution: ["战斗目的", "悬念布局"]
      weight: 0.20
      
    - writer: "墨言"
      phase: "前置"
      role: "人物状态"
      contribution: ["人物心理状态", "情感动机"]
      weight: 0.15
      
    - writer: "剑尘"
      phase: "核心"
      role: "战斗设计"
      contribution: ["战斗节奏控制", "代价描写", "弱者胜强逻辑"]
      weight: 0.35
      
    - writer: "云溪"
      phase: "收尾"
      role: "润色收尾"
      contribution: ["战斗氛围渲染", "禁止项检测"]
      weight: 0.15
```

---

## 评估体系

### 评估阈值

| 维度 | 阈值 | 说明 |
|------|------|------|
| 世界自洽 | ≥7 | 世界观设定一致性 |
| 人物立体 | ≥6 | 人物形象完整性 |
| 情感真实 | ≥6 | 情感表达自然度 |
| 战斗逻辑 | ≥6 | 战斗场面合理性 |
| 文风克制 | ≥6 | 文风是否符合厚重基调 |
| 剧情张力 | ≥6 | 剧情冲突强度 |

### 禁止项检测

| 检测项 | 标准 | 违规后果 |
|--------|------|----------|
| AI味表达 | "眼中闪过一丝"、"心中涌起一股" | 出现1个即失败 |
| 古龙式极简 | 单字/双字成段 | 出现1个即失败 |
| 时间连接词 | "然后"、"就在这时" 开头 | ≥3个即失败 |
| 抽象统计词 | "无数"、"成千上万" | ≥2个即失败 |
| Markdown加粗 | `**XXX**` | 出现1个即失败 |

---

## 数据结构

### WorkflowResult

```python
@dataclass
class WorkflowResult:
    session_id: str           # 会话ID
    chapter_name: str         # 章节名称
    scene_type: str           # 场景类型
    final_content: str        # 最终内容
    iterations: int           # 迭代次数
    evaluation_results: List  # 评估结果
    writer_outputs: List      # 作家输出
    success: bool             # 是否成功
    metadata: Dict            # 元数据
```

### WriterOutput

```python
@dataclass
class WriterOutput:
    output_id: str            # 输出ID
    session_id: str           # 会话ID
    chapter_name: str         # 章节名称
    scene_type: str           # 场景类型
    phase: str                # Phase
    writer_name: str          # 作家名称
    writer_skill: str         # 作家技能
    content: str              # 输出内容
    timestamp: str            # 时间戳
    iteration: int            # 迭代次数
    evaluation_score: Dict    # 评估分数
    evaluation_feedback: str  # 评估反馈
    metadata: Dict            # 元数据
```

---

## 配置说明

### 场景-作家映射

**路径**：`.vectorstore/scene_writer_mapping.json`

**结构**：
```json
{
  "version": "2.0",
  "scene_count": {
    "active": 16,
    "total": 31
  },
  "scene_writer_mapping": {
    "场景类型": {
      "description": "场景描述",
      "collaboration": [...],
      "workflow_order": ["作家1", "作家2", ...],
      "primary_writer": "主责作家"
    }
  }
}
```

### 作家技能配置

**路径**：`C:\Users\39477\.agents\skills\novelist-*/`

**作家列表**：
- `novelist-canglan` - 世界观架构师
- `novelist-xuanyi` - 剧情编织师
- `novelist-moyan` - 人物刻画师
- `novelist-jianchen` - 战斗设计师
- `novelist-yunxi` - 意境营造师
- `novelist-evaluator` - 审核评估师

---

## 最佳实践

### 1. 选择合适的场景类型

```python
# 查看可用场景
scenes = api.get_available_scenes()

# 查看场景详情
info = api.get_scene_info("战斗场景")
print(info["description"])  # 场景描述
print(info["primary_writer"])  # 主责作家
```

### 2. 提供充分的上下文

```python
result = api.create_scene(
    scene_type="战斗场景",
    chapter="第一章-天裂",
    outline="详细的大纲内容...",
    context={
        "existing_settings": "已有设定...",
        "character_info": "人物信息...",
        "plot_context": "剧情背景...",
    }
)
```

### 3. 处理迭代结果

```python
result = api.create_scene(...)

if not result.success:
    print(f"迭代 {result.iterations} 次后仍未达标")
    print(f"反馈: {result.feedback}")
    
    # 根据反馈进行手动调整
    # 或重新执行创作
```

### 4. 管理上下文

```python
from modules.creation import WriterContextManager

# 创建上下文管理器
ctx_manager = WriterContextManager()

# 检索历史上下文
history = ctx_manager.get_iteration_history(
    session_id="session_xxx",
    chapter_name="第一章-天裂",
    scene_type="战斗场景",
)

for output in history:
    print(f"迭代 {output.iteration}: {output.writer_name}")
    print(f"评估分数: {output.evaluation_score}")
```

---

## 故障排除

### 1. 模块导入失败

```
ImportError: cannot import name 'WorkflowScheduler'
```

**解决方案**：确保 `modules/creation/` 目录下所有文件存在，并检查 Python 路径。

### 2. 向量数据库连接失败

```
ImportError: qdrant-client未安装
```

**解决方案**：`pip install qdrant-client`

### 3. 作家执行超时

```
TimeoutError: 作家任务超时
```

**解决方案**：增加 `timeout_per_writer` 配置值。

### 4. 评估一直不通过

**解决方案**：
1. 检查评估阈值是否过高
2. 查看具体反馈，针对性改进
3. 增加输入上下文质量

---

## 扩展开发

### 添加新场景类型

编辑 `.vectorstore/scene_writer_mapping.json`：

```json
{
  "新场景类型": {
    "description": "场景描述",
    "collaboration": [
      {
        "writer": "作家名",
        "role": "角色",
        "phase": "前置/核心/收尾",
        "contribution": ["贡献项1", "贡献项2"],
        "weight": 0.30
      }
    ],
    "workflow_order": ["作家1", "作家2"],
    "primary_writer": "主责作家"
  }
}
```

### 自定义评估阈值

```python
from modules.creation import EvaluatorExecutor

executor = EvaluatorExecutor(
    thresholds={
        "世界自洽": 8,  # 提高要求
        "人物立体": 7,
        "情感真实": 6,
    }
)
```

---

## 参考资料

- [CONFIG.md](../../CONFIG.md) - 项目配置
- [scene_writer_mapping.json](../../.vectorstore/scene_writer_mapping.json) - 场景-作家映射
- [novelist-* skills](../../../.agents/skills/) - 作家技能定义

---

*模块版本: 1.0*
*更新时间: 2026-04-02*
*作者: 众生界 AI*