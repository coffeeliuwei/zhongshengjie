# 众生界项目 - AI 快速掌握手册

> 本手册专为 AI 设计，帮助快速理解项目全局、核心逻辑和关键细节。

---

## 一、项目概述

### 1.1 项目性质

**众生界**是一个 AI 辅助小说创作系统，核心特点：

| 特点 | 说明 |
|------|------|
| **类型** | 玄幻/科幻融合小说 |
| **核心主题** | 「我是谁」身份认同 |
| **创作方式** | 多作家协作（基于 Anthropic Harness 设计） |
| **数据驱动** | 向量数据库 + 知识图谱 + 经验学习 |

### 1.2 核心架构图

```
用户输入 "写第一章"
        ↓
┌─────────────────────────────────────────────────────────────┐
│                    novelist-workflow                        │
│                    (工作流调度器 skill)                       │
├─────────────────────────────────────────────────────────────┤
│  阶段0: 需求澄清（互相启发讨论）                              │
│  阶段1: 章节大纲解析                                         │
│  阶段2: 场景类型识别                                         │
│  阶段2.5: 经验检索                                           │
│  阶段3: 设定检索                                             │
│  阶段4: 逐场景创作 ← 核心流程                                │
│  阶段5: 整章整合                                             │
│  阶段6: 整章评估                                             │
│  阶段7: 经验写入                                             │
└─────────────────────────────────────────────────────────────┘
        ↓
    正文输出
```

---

## 二、目录结构与职责

```
D:\动画\众生界\
│
├── core/                           # 核心基础设施
│   ├── cli.py                      # CLI 入口
│   ├── config_manager.py           # 配置管理
│   ├── path_manager.py             # 路径管理
│   ├── db_connection.py            # 数据库连接
│   ├── error_handler.py            # 统一错误处理
│   └── health_check.py             # 健康检查
│
├── modules/                        # 功能模块
│   ├── creation/                   # 创作模块（核心）
│   │   ├── workflow_scheduler.py   # 工作流调度器
│   │   ├── writer_executor.py      # 作家执行器
│   │   ├── evaluator_executor.py   # 评估执行器
│   │   ├── conflict_detector.py    # 冲突检测器
│   │   ├── creation_mode.py        # 创作模式（并行+融合）
│   │   ├── iteration_optimizer.py  # 迭代优化器
│   │   ├── yunxi_fusion_polisher.py# 云溪融合润色器
│   │   └── experience_retriever.py # 经验检索器
│   ├── knowledge_base/             # 知识库管理
│   ├── validation/                 # 验证模块
│   ├── migration/                  # 移植模块
│   └── visualization/              # 可视化模块
│
├── .vectorstore/                   # 向量数据库和数据层
│   ├── knowledge_search.py         # 小说设定检索
│   ├── technique_search.py         # 创作技法检索
│   ├── workflow.py                 # 统一工作流入口
│   ├── knowledge_graph.py          # 知识图谱
│   ├── scene_writer_mapping.json   # 场景-作家映射
│   └── qdrant/                     # Qdrant 数据库文件
│
├── 设定/                           # 小说设定文件
│   ├── 人物谱.md
│   ├── 十大势利.md
│   └── ...
│
├── 创作技法/                       # 11维度技法体系
│   ├── 世界观/
│   ├── 剧情/
│   ├── 人物/
│   └── ...
│
├── 章节大纲/                       # 章节规划
├── 正文/                           # 小说正文
├── 章节经验日志/                   # 经验学习
│
└── C:\Users\39477\.agents\skills\  # 技能文件（关键）
    ├── novelist-canglan/           # 苍澜 - 世界观架构师
    ├── novelist-xuanyi/            # 玄一 - 剧情编织师
    ├── novelist-moyan/             # 墨言 - 人物刻画师
    ├── novelist-jianchen/          # 剑尘 - 战斗设计师
    ├── novelist-yunxi/             # 云溪 - 意境营造师
    ├── novelist-evaluator/         # 审核评估师
    ├── novelist-workflow/          # 工作流调度器
    └── novelist-shared/            # 共享规范
```

---

## 三、核心概念速查

### 3.1 作家体系

| 作家 | 技能文件 | 专长 | Phase |
|------|----------|------|-------|
| **苍澜** | novelist-canglan | 世界观架构、力量体系、血脉设定 | Phase 1 (前置) |
| **玄一** | novelist-xuanyi | 剧情编织、伏笔设计、悬念布局 | Phase 1 (前置) |
| **墨言** | novelist-moyan | 人物刻画、情感描写、心理变化 | Phase 1 (前置) |
| **剑尘** | novelist-jianchen | 战斗设计、代价描写、弱者胜强 | Phase 2 (核心) |
| **云溪** | novelist-yunxi | 意境营造、氛围渲染、章节润色 | Phase 1.6 + 3 |
| **审核师** | novelist-evaluator | 禁止项检测、技法评估 | Evaluator |

### 3.2 Phase 执行模式

```
Phase 1: 前置（并行）
├── 苍澜 → 世界观约束
├── 玄一 → 剧情框架
└── 墨言 → 人物状态
        ↓
Phase 1.5: 一致性检测（自动）
        ↓
Phase 1.6: 融合调整（云溪）
├── 冲突 ≤ 2 → 自动融合
├── 冲突 3-5 → 云溪介入
└── 冲突 > 5 → 用户确认
        ↓
Phase 2: 核心（主作家）
└── 剑尘/墨言/苍澜/玄一 → 场景主要内容
        ↓
Phase 3: 收尾（云溪）
└── 云溪 → 润色统一
```

### 3.3 Generator/Evaluator 分离原则

| 角色 | 职责 | 说明 |
|------|------|------|
| **Generator** | 创作 | 作家专注创作，不自我评估 |
| **Evaluator** | 评估 | 独立评估，提供具体反馈 |
| **迭代** | 最多3次 | Evaluator 反馈 → Generator 修改 |

### 3.4 检索优先级

```
Level 1: Qdrant 向量数据库
├── novel_settings (小说设定)
├── writing_techniques (创作技法)
└── case_library (标杆案例)
        ↓ 不可用时
Level 2: 本地数据文件
├── .cache/db_cache/*.json
└── knowledge_graph.json
        ↓ 无结果
Level 3: 原始文件
├── 总大纲.md
├── 设定/*.md
└── 创作技法/**/*.md
        ↓ 无结果
Level 4: 标记"待补充"
```

---

## 四、核心流程详解

### 4.1 阶段0：需求澄清

**目的**：通过互相启发讨论，让模糊方向逐步细化。

**流程**：
```
用户提出方向
    ↓
系统提出方向/问题
├── "觉醒的是什么血脉？建议：血脉-天裂"
├── "觉醒的触发场景？建议：目睹母亲被肢解"
└── "觉醒的代价？建议：遗忘母亲的名字"
    ↓
用户反馈（接受/修改/拒绝）
    ↓
循环讨论 → 双方满意
    ↓
输出：明确的创作目标
```

**关键**：系统有自己的审美和坚持，不只是被动执行。

### 4.2 阶段4：逐场景创作（核心）

**详细流程**：

```
1. Phase 1: 并行生成（30秒）
   苍澜、玄一、墨言同时执行，各自输出草稿
   
2. Phase 1.5: 一致性检测（1秒）
   自动检测三个输出之间的冲突：
   - 记忆逻辑冲突（遗忘 vs 记住）
   - 伏笔不匹配
   - 时间线冲突
   - 设定不一致
   
3. Phase 1.6: 融合调整（0-30秒）
   - 冲突 ≤ 2 → 自动融合（无需调用作家）
   - 冲突 3-5 → 云溪介入融合
   - 冲突 > 5 → 用户确认
   
4. Phase 2: 核心创作（60秒）
   主作家使用融合后的统一约束创作
   
5. Phase 3: 收尾润色（30秒）
   云溪统一风格，消除拼合痕迹
   
6. Evaluator 评估（30秒）
   - 禁止项检测
   - 技法评估
   - 输出反馈
   
7. 迭代修改（如果需要）
   最多3次迭代
```

### 4.3 迭代优化机制

**三重保障**：

```
1. 迭代风险预测
   在阶段0结束时预测风险：
   - 风险因素：冲突数量、场景复杂度、经验丰富度
   - 风险等级：LOW/MEDIUM/HIGH/CRITICAL
   - CRITICAL → 建议返回阶段0继续讨论

2. 快速失败机制
   每个 Phase 输出后检查质量：
   - Phase 1 输出为空 → 立即重做
   - Phase 2 字数不足 → 立即重做
   - 避免无效后续操作

3. 动态迭代调整
   根据复杂度调整迭代上限：
   - 简单场景 → 最多1次
   - 中等场景 → 最多2次
   - 复杂场景 → 最多3次
```

---

## 五、关键设计决策

### 5.1 固定3人前置

**决策**：所有场景都由苍澜、玄一、墨言三人并行执行前置。

**原因**：
1. 三个维度对所有场景都有价值
2. 流程统一，代码简单
3. "无特殊约束"本身是有价值的信息

**处理**：
```yaml
# 某维度无特殊要求时
苍澜输出：
  内容: "无特殊约束"
  说明: "使用默认设定"
  默认引用: "血脉-天裂设定"
```

### 5.2 云溪负责融合

**决策**：Phase 1.6 融合由云溪负责，而非主作家。

**原因**：
1. 云溪专长意境营造，擅长风格统一
2. 融合和润色（Phase 3）是连贯的职责
3. 避免主作家过载

### 5.3 自动融合优先

**决策**：冲突 ≤ 2 时自动融合，减少作家调用。

**效率提升**：约 40-60% 的场景无需调用云溪融合。

### 5.4 经验学习

**设计**：
```
章节经验日志/
├── 第一章_log.json
├── 第二章_log.json
└── ...

每章日志包含：
- techniques_used: 使用的技法
- what_worked: 有效做法
- what_didnt_work: 无效做法
- insights: 可复用洞察
- for_next_chapter: 给下一章建议

创作时检索前3章经验 → 注入上下文
```

---

## 六、数据结构速查

### 6.1 场景-作家映射

```json
// .vectorstore/scene_writer_mapping.json
{
  "scene_writer_mapping": {
    "战斗场景": {
      "primary_writer": "剑尘",
      "workflow_order": ["苍澜", "玄一", "墨言", "剑尘", "云溪"],
      "collaboration": [
        {"writer": "苍澜", "phase": "前置", "role": "世界观输入"},
        {"writer": "玄一", "phase": "前置", "role": "剧情框架"},
        {"writer": "墨言", "phase": "前置", "role": "人物状态"},
        {"writer": "剑尘", "phase": "核心", "role": "战斗设计"},
        {"writer": "云溪", "phase": "收尾", "role": "润色收尾"}
      ]
    }
  }
}
```

### 6.2 冲突类型

```python
class ConflictType(Enum):
    MEMORY_LOGIC = "记忆逻辑冲突"      # 遗忘 vs 记住
    FORESHADOW_MISMATCH = "伏笔不匹配" # 伏笔与状态不匹配
    TIMELINE = "时间线冲突"
    SETTING = "设定不一致"
    CHARACTER = "人物矛盾"
    TONE = "基调冲突"
```

### 6.3 评估维度

```python
EVALUATION_DIMENSIONS = {
    "世界自洽": {"threshold": 7, "description": "世界观设定一致性"},
    "人物立体": {"threshold": 6, "description": "人物形象完整性"},
    "情感真实": {"threshold": 6, "description": "情感表达自然度"},
    "战斗逻辑": {"threshold": 6, "description": "战斗场面合理性"},
    "文风克制": {"threshold": 6, "description": "厚重基调"},
    "剧情张力": {"threshold": 6, "description": "剧情冲突强度"},
}
```

---

## 七、API 使用示例

### 7.1 完整创作流程

```python
from modules.creation import WorkflowScheduler, CreationAPI
from pathlib import Path

# 方式1：使用 API
api = CreationAPI()
result = api.create_scene(
    scene_type="战斗场景",
    chapter="第一章-天裂",
    outline="血牙目睹母亲被杀，血脉觉醒..."
)
print(f"成功: {result.success}")
print(f"内容: {result.content}")
api.shutdown()

# 方式2：使用调度器
scheduler = WorkflowScheduler(
    project_root=Path("D:/动画/众生界"),
    max_iterations=3
)
result = scheduler.execute_workflow(
    scene_type="战斗场景",
    chapter_name="第一章-天裂",
    input_context={"outline": "..."}
)
scheduler.shutdown()
```

### 7.2 健康检查

```python
from core import HealthChecker, run_health_check

# 快速检查
checker = HealthChecker()
is_healthy = checker.quick_check()

# 完整检查
report = checker.check_all(quick=False)
print(report.print_report())

# CLI 方式
# python -m core health
```

### 7.3 错误处理

```python
from core import NovelError, handle_errors, ErrorCollector

# 使用装饰器
@handle_errors(default_return=None)
def my_function():
    # 可能出错的代码
    pass

# 使用收集器
collector = ErrorCollector()
with collector.catch("操作1"):
    # 可能出错的代码
    pass

if collector.has_errors:
    print(collector.summary())
```

### 7.4 迭代预测

```python
from modules.creation import IterationPredictor, IterationRisk

predictor = IterationPredictor()
prediction = predictor.predict(
    scene_type="战斗场景",
    scene_description="复杂的战斗场景",
    experience_count=2,
    setting_completeness=0.7,
    discussion_rounds=2,
)

if prediction.risk_level == IterationRisk.CRITICAL:
    print("⚠️ 高迭代风险，建议继续讨论")
    print(f"风险因素: {prediction.risk_factors}")
```

---

## 八、常见问题排查

### 8.1 数据库连接失败

```
问题: DatabaseError: 数据库连接失败

检查:
1. Qdrant 服务是否启动
   - Windows: docker start qdrant
   - 或使用本地模式

2. 端口是否正确
   - 默认: localhost:6333

3. 检查健康状态
   - python -m core health
```

### 8.2 技能文件找不到

```
问题: FileNotFoundError: 技能文件不存在

检查:
1. 技能目录路径
   - C:\Users\{用户名}\.agents\skills\

2. 必需技能列表
   - novelist-canglan
   - novelist-xuanyi
   - novelist-moyan
   - novelist-jianchen
   - novelist-yunxi
   - novelist-evaluator
   - novelist-workflow
   - novelist-shared

3. 每个技能目录下应有 SKILL.md 文件
```

### 8.3 导入错误

```python
# 正确的导入方式

# 从项目根目录导入
sys.path.insert(0, "D:/动画/众生界")

# 核心模块
from core import ConfigManager, HealthChecker, NovelError

# 创作模块
from modules.creation import WorkflowScheduler, CreationMode

# 向量数据库模块
sys.path.insert(0, "D:/动画/众生界/.vectorstore")
from knowledge_search import KnowledgeSearcher
from technique_search import TechniqueSearcher
```

### 8.4 迭代次数过多

```
问题: 场景迭代超过3次仍未通过

原因分析:
1. 阶段0讨论不充分
2. 设定信息缺失
3. 场景复杂度过高

解决方案:
1. 使用迭代预测器在阶段0结束时检查风险
2. 补充相关设定文件
3. 降低场景复杂度或拆分场景
```

---

## 九、关键文件索引

### 9.1 必读文件

| 文件 | 用途 | 优先级 |
|------|------|--------|
| `novelist-workflow/SKILL.md` | 工作流完整定义 | ⭐⭐⭐⭐⭐ |
| `novelist-shared/SKILL.md` | 共享规范（文风、禁止项） | ⭐⭐⭐⭐⭐ |
| `novelist-evaluator/SKILL.md` | 评估标准 | ⭐⭐⭐⭐⭐ |
| `CONFIG.md` | 项目配置 | ⭐⭐⭐⭐☆ |
| `modules/creation/README.md` | 创作模块文档 | ⭐⭐⭐⭐☆ |

### 9.2 配置文件

| 文件 | 内容 |
|------|------|
| `scene_writer_mapping.json` | 场景-作家映射（28种场景） |
| `CONFIG.md` | 项目配置（文风、阈值） |
| `总大纲.md` | 小说总大纲 |
| `设定/*.md` | 人物、势力、力量体系 |

### 9.3 数据文件

| 文件/目录 | 内容 |
|-----------|------|
| `novel_settings` (Qdrant) | 143条小说设定 |
| `writing_techniques` (Qdrant) | 1122条创作技法 |
| `case_library` (Qdrant) | 256,083条案例 |
| `knowledge_graph.json` | 知识图谱 |
| `章节经验日志/` | 章节经验日志 |

---

## 十、扩展与修改指南

### 10.1 添加新场景类型

```json
// 编辑 scene_writer_mapping.json
{
  "新场景类型": {
    "description": "场景描述",
    "primary_writer": "主作家",
    "workflow_order": ["苍澜", "玄一", "墨言", "主作家", "云溪"],
    "collaboration": [...],
    "status": "active"
  }
}
```

### 10.2 添加新作家

```
1. 创建技能文件
   C:\Users\{用户}\.agents\skills\novelist-{新作家}\SKILL.md

2. 定义作家专长
   - 角色定位
   - 调用时机
   - 输入输出格式

3. 更新 scene_writer_mapping.json
   添加到相关场景的 collaboration 中
```

### 10.3 修改评估标准

```python
# 编辑 novelist-evaluator/SKILL.md
# 或在代码中自定义阈值

from modules.creation import EvaluatorExecutor

executor = EvaluatorExecutor(
    thresholds={
        "世界自洽": 8,  # 提高要求
        "人物立体": 7,
    }
)
```

### 10.4 添加新冲突类型

```python
# 编辑 conflict_detector.py

class ConflictType(Enum):
    # 现有类型...
    NEW_CONFLICT = "新冲突类型"

def _detect_new_conflict(outputs):
    # 检测逻辑
    pass
```

---

## 十一、性能优化建议

### 11.1 数据库优化

```
- 大数据集使用 Docker 模式（case_library 有 34万条）
- 定期重建索引
- 使用缓存减少重复查询
```

### 11.2 创作流程优化

```
- 使用迭代预测器提前识别高风险场景
- 简单场景降低迭代上限
- 使用云溪融合润色合并减少调用
```

### 11.3 内存优化

```
- 及时关闭 WorkflowScheduler
- 使用 with 语句管理上下文
- 避免重复加载模型
```

---

## 十二、版本信息

| 组件 | 版本/状态 |
|------|----------|
| 项目版本 | 1.0 |
| Python | 3.10+ |
| Qdrant | Latest |
| 核心模块 | ✅ 生产就绪 |
| 迭代优化 | ✅ 已完成 |
| 错误处理 | ✅ 已完成 |
| 健康检查 | ✅ 已完成 |
| 测试覆盖 | ✅ 100% 通过 |

---

## 附录：快速启动检查清单

```
□ 1. Qdrant 服务运行中
□ 2. 技能文件完整（8个）
□ 3. 设定文件存在
□ 4. 运行健康检查: python -m core health
□ 5. 测试导入: python -c "from modules.creation import WorkflowScheduler"
□ 6. 创建测试场景
```

---

*本手册最后更新: 2026-04-02*
*维护者: 众生界 AI 系统*