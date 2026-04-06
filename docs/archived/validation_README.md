# 验证模块 (validation)

统一验证入口，整合所有验证功能。

## 模块结构

```
modules/validation/
├── __init__.py           # 统一API接口
├── validation_manager.py # 统一验证入口 + 历史管理
├── checker_manager.py    # 检查功能集合
├── scorer_manager.py     # 评分功能
└── README.md             # 本文档
```

## 功能说明

### ValidationManager - 统一验证入口

整合 verify_all.py、verification_history.py 等功能：

- 运行所有验证脚本
- 验证历史管理
- 支持快速模式和选择性验证
- 设定验证（哲学设定、力量体系、技法入库）

```python
from modules.validation import ValidationManager

manager = ValidationManager()
report = manager.run_all()        # 运行所有验证
manager.run_quick()               # 快速验证
manager.validate_chapter("path")  # 验证章节
manager.show_history()            # 显示历史
```

### CheckerManager - 检查功能集合

整合 check_sources.py、check_missing.py 等检查脚本：

- 检查案例库来源分布
- 检查知识图谱缺失实体
- 检查关系格式
- 检查实体结构
- 检查血脉格式

```python
from modules.validation import CheckerManager

checker = CheckerManager()
checker.check_sources()     # 案例库来源
checker.check_missing()     # 缺失实体
checker.check_relations()   # 关系格式
checker.check_entity()      # 实体结构
checker.check_bloodline()   # 血脉格式
checker.check_all()         # 运行所有检查
```

### ScorerManager - 评分功能

整合 checklist_scorer.py 功能，11维度评分体系：

| 维度 | 权重 | 满分 | 检查项 |
|------|------|------|--------|
| 世界观 | 20% | 7 | 7项 (P0:3, P1:4) |
| 剧情 | 15% | 6 | 6项 (P0:3, P1:3) |
| 人物 | 15% | 6 | 6项 (P0:3, P1:3) |
| 战斗 | 5% | 5 | 5项 (P0:2, P1:3) |
| 氛围 | 15% | 6 | 6项 (P0:3, P1:3) |
| 节奏 | 10% | 5 | 5项 (P1:5) |
| 叙事 | 10% | 6 | 6项 (P1:6) |
| 主题 | 5% | 5 | 5项 (P1:5) |
| 情感 | 5% | 5 | 5项 (P1:5) |
| 读者体验 | 0% | 4 | 4项 (P2:4) |
| 元维度 | 0% | 4 | 4项 (P2:4) |

**评级标准：**

| 评级 | 分数 | 说明 |
|------|------|------|
| S | ≥52 | 史诗级标准 |
| A | ≥44 | 优秀 |
| B | ≥35 | 良好 |
| C | ≥26 | 合格 |
| D | <26 | 需改进 |

```python
from modules.validation import ScorerManager

scorer = ScorerManager()
scorer.load_chapter("正文/第一章-天裂.md")
scorer.set_scores({"世界观": 6, "剧情": 5, "人物": 5, ...})
report = scorer.generate_report()
threshold_check = scorer.check_thresholds()  # 检查是否达标
```

## 验证阈值

来自 CONFIG.md 的评估阈值：

| 维度 | 阈值 |
|------|------|
| 世界自洽 | ≥7 |
| 人物立体 | ≥6 |
| 情感真实 | ≥6 |
| 战斗逻辑 | ≥6 |
| 文风克制 | ≥6 |
| 剧情张力 | ≥6 |

## CLI 命令

```bash
# 运行所有验证
python -m core validate --all

# 快速验证
python -m core validate --all --quick

# 验证指定章节
python -m core validate --chapter "正文/第一章-天裂.md"

# 显示验证历史
python -m core validate --history
```

## 模块级便捷函数

```python
from modules.validation import validate_all, validate_chapter, check_all, score_chapter

# 运行所有验证
report = validate_all(quick=True)

# 验证章节
result = validate_chapter("正文/第一章-天裂.md")

# 运行所有检查
results = check_all()

# 评分章节
report = score_chapter("正文/第一章-天裂.md", {"世界观": 6, ...})
```

## 与原有脚本的对应关系

| 原脚本 | 新模块位置 |
|--------|------------|
| verify_all.py | validation_manager.py - ValidationManager |
| verification_history.py | validation_manager.py - ValidationHistory |
| verify_merge.py | validation_manager.py - _validate_merge() |
| verify_worldview.py | validation_manager.py - _validate_worldview() |
| verify_structures.py | validation_manager.py - VERIFICATION_SCRIPTS |
| check_sources.py | checker_manager.py - check_sources() |
| check_missing.py | checker_manager.py - check_missing() |
| check_relations.py | checker_manager.py - check_relations() |
| check_entity.py | checker_manager.py - check_entity() |
| check_bloodline.py | checker_manager.py - check_bloodline() |
| checklist_scorer.py | scorer_manager.py - ScorerManager |

---

*模块版本: 1.0*
*更新时间: 2026-04-02*
*重构支持: CLI统一接口 + 模块化架构*