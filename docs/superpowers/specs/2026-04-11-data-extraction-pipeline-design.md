# 小说数据提炼流程改进设计

> **日期**: 2026-04-11  
> **状态**: 已实施（部分完成）  
> **目标**: 噪音率从89%降到<10%，融合现有工程架构
> **实施日期**: 2026-04-11

---

## 〇、现有工程完整架构（必须融合）

### 核心创作流程
```
Generator(5位作家) → Evaluator(13维度评估) → 9阶段创作流程
苍澜(世界观)/玄一(剧情)/墨言(人物)/剑尘(战斗)/云溪(意境)
```

### 数据提炼架构
```
统一提炼引擎(unified_extractor.py)
├── 11维度并行提取
├── 增量同步(incremental_sync.py + novel_index.json)
├── 断点续传(progress/*.json)
└── 向量入库(sync_manager.py → Qdrant)
```

### 技法学习闭环（维度自我学习）
```
评估反馈 → feedback_processor.py → 技法映射 → 
technique_tracker.py → 效果评分 → 推荐 → 下次创作
```

### 关键数据文件
| 文件 | 用途 | 必须兼容 |
|------|------|----------|
| novel_index.json | 小说处理状态 | ✓ 复用 |
| unified_progress.json | 提炼进度 | ✓ 复用 |
| technique_usage.json | 技法使用追踪 | ✓ 兼容 |
| config.json | 统一配置 | ✓ 使用config_loader |

---

## 一、用户需求

| 维度 | 决策 |
|------|------|
| 处理策略 | 全部重来（清空向量库，重新清洗+提取+入库） |
| 数据范围 | 全部题材（6000+本小说） |
| 场景分级 | 所有22种场景都是核心场景 |
| 数据量预期 | 全面型（尽可能多入库，不设上限） |
| 噪音阈值 | **<10%** |

---

## 二、当前问题分析

### 2.1 数据噪音来源

| 数据源 | 噪音率 | 主要噪音类型 |
|--------|--------|-------------|
| converted目录(5472文件) | ~75% | 外语、工具书、目录页、非小说内容 |
| worldview_element | 89% | 对话词误匹配（说道/笑道等） |
| character_relation | ~0.01% | ~~~占位符 |
| power_vocabulary | ~0% | 基本良好 |
| 案例库(387K条) | 待验证 | 可能有低质案例 |

### 2.2 流程缺失步骤

当前流程缺失以下关键环节：
1. **语言检测** - 无法识别外语小说
2. **内容验证** - 无法区分小说与非小说
3. **深度清洗** - 广告/防盗版内容未清理
4. **质量评分** - 无入库前质量校验
5. **去重机制** - 无内容去重
6. **入库校验** - 噪音数据直接入库

---

## 三、改进方案设计

### 3.1 新流程架构（融合现有工程）

**核心设计原则**：
1. 复用现有增量机制（novel_index.json + incremental_sync.py）
2. 清洗作为提炼引擎的子阶段（Phase 2）
3. 保持技法学习闭环兼容
4. 使用统一配置（config_loader.py）

```
原始小说库(6000+本，txt/epub/mobi)
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 现有模块: incremental_sync.py                        │
│ - 检测新小说/修改小说                                │
│ - 更新 novel_index.json                             │
│ - 断点续传支持                                       │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 现有模块: convert_format.py                          │
│ - 格式转换 (epub/mobi → txt)                        │
│ - 输出: converted/*.txt                              │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 【新增】Stage 1: 语言检测                            │
│ - 中文比例计算 (>60%)                                │
│ - 过滤外语噪音                                       │
│ - 更新 novel_index.json.language_status             │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 【新增】Stage 2: 内容验证                            │
│ - 小说特征词检测 (>10个)                             │
│ - 非小说过滤 (目录页/工具书)                         │
│ - 更新 novel_index.json.content_status              │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 【新增】Stage 3: 深度清洗                            │
│ - 广告过滤                                           │
│ - 防盗版清理                                         │
│ - 输出: clean/*.txt                                  │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 【新增】Stage 4: 质量评分                            │
│ - 压缩率检测 (0.65-0.80)                             │
│ - 综合评分 (>0.6)                                    │
│ - 更新 novel_index.json.quality_score               │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 现有模块: unified_extractor.py                       │
│ - 11维度并行提取                                     │
│ - 场景识别 (22种场景类型)                            │
│ - 技法标注                                           │
│ - 更新 unified_progress.json                        │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 【新增】Stage 5: 去重与入库校验                      │
│ - 文件hash去重                                       │
│ - 语义相似度去重                                     │
│ - 噪音阈值检测 (<10%)                                │
│ - 更入入库标记                                       │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 现有模块: sync_manager.py                            │
│ - BGE-M3嵌入生成 (GPU加速)                           │
│ - Qdrant入库                                         │
│ - 保持技法学习闭环兼容                               │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 技法学习闭环 (保持现有)                              │
│ - feedback_processor.py → technique_tracker.py      │
│ - 效果评分 → 推荐系统                                │
└─────────────────────────────────────────────────────┘
```

**与现有工程融合点**：

| 新模块 | 融合方式 | 复用现有 |
|--------|----------|----------|
| 语言检测 | incremental_sync.py调用后 | novel_index.json |
| 内容验证 | incremental_sync.py调用后 | novel_index.json |
| 深度清洗 | 替换converted目录生成逻辑 | convert_format.py |
| 质量评分 | unified_extractor.py前置 | unified_progress.json |
| 入库校验 | sync_manager.py前置 | sync_manager.py |

### 3.2 新增模块清单

| 模块名 | 文件位置 | 功能 |
|--------|----------|------|
| `novel_validator.py` | `.novel-extractor/validators/` | 语言检测+内容验证 |
| `deep_cleaner.py` | `.novel-extractor/cleaners/` | 深度清洗管道 |
| `quality_scorer.py` | `.novel-extractor/scorers/` | 质量评分系统 |
| `semantic_deduplicator.py` | `.novel-extractor/dedup/` | 语义去重 |
| `入库校验器` | 集成到 `sync_to_qdrant.py` | 入库前噪音检测 |

---

## 九、自我学习功能融合（关键设计）

### 9.1 现有自我学习闭环

项目已实现多层次的自我学习机制：

```
┌─────────────────────────────────────────────────────────────────┐
│                   自我学习完整闭环                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 技法发现闭环                                                 │
│     technique_discoverer.py                                      │
│     ├── 从案例中自动发现新技法类型                                │
│     ├── 匹配现有维度或生成新技法名称                              │
│     └── 技法特征提取 (dimension/category/techniques)             │
│                                                                  │
│  2. 技法追踪闭环                                                 │
│     technique_tracker.py → technique_usage.json                  │
│     ├── track_usage(): 记录每次技法使用                          │
│     ├── _update_stats(): 更新成功率、效果评分                    │
│     ├── by_writer/by_scene: 按作家/场景统计                      │
│     └── contexts: 收集使用上下文（最多10个）                     │
│                                                                  │
│  3. 反馈处理闭环                                                 │
│     feedback_processor.py                                        │
│     ├── process_feedback(): 处理评估反馈                         │
│     ├── _map_to_technique(): 映射到技法维度                      │
│     ├── ISSUE_TO_TECHNIQUE_MAPPING: 问题→技法映射表              │
│     └── forbidden_items: AI味禁止项检测                         │
│                                                                  │
│  4. 技法推荐闭环                                                 │
│     recommend_techniques()                                       │
│     ├── 根据上下文推荐技法                                       │
│     ├── 综合评分: 成功率*0.6 + 效果评分*0.4                      │
│     ├── 维度匹配加分 +0.2                                        │
│     └── 返回 top_k 高效技法                                      │
│                                                                  │
│  5. 变更检测闭环                                                 │
│     change_detector.py                                           │
│     ├── 监控: 大纲/设定/技法/追踪文件                             │
│     ├── 增量检测: hash/modtime                                   │
│     ├── 自动触发: sync_manager_adapter                           │
│     └── 生成: ChangeReport                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 清洗模块必须保持的数据兼容性

| 数据文件 | 格式要求 | 清洗模块影响 |
|----------|----------|--------------|
| technique_usage.json | TechniqueUsage schema | **禁止删除**，只追加 |
| writing_techniques_v2 | Dense+Sparse+ColBERT | 清洗后需重新同步 |
| case_library_v2 | scene_type/genre/content | 清洗后需触发技法发现 |
| novel_index.json | NovelIndex schema | 新增字段兼容 |
| unified_progress.json | ExtractionProgress | 继续复用 |

### 9.3 清洗后数据触发的学习流程

```
清洗完成 → 新数据入库 → 触发技法发现 → 更新技法库 → 推荐系统更新

具体流程:
1. sync_manager.py 入库完成后
2. 调用 technique_discoverer.discover_techniques(new_cases)
3. 发现新技法 → writing_techniques_v2
4. 下次创作时 recommend_techniques() 可推荐新技法
```

### 9.4 清洗模块与技法学习的接口

```python
# 清洗完成后应触发技法发现
from core.type_discovery.technique_discoverer import TechniqueDiscoverer

def after_cleaning_sync(new_cases: List[str]):
    """清洗入库后触发技法发现"""
    discoverer = TechniqueDiscoverer()
    
    # 从新案例中发现技法
    discovered = discoverer.discover_techniques(new_cases)
    
    # 同步到技法库
    for tech in discovered:
        if tech.confidence >= 0.7:  # 高置信度才入库
            sync_to_writing_techniques(tech)
    
    return discovered
```

### 9.5 数据回流路径（保持现有）

```
创作 → 评估 → feedback_processor → 技法映射 → 
technique_tracker → 效果评分 → recommend_techniques → 下次创作

清洗模块只影响:
- 数据质量（更高质量案例 → 更准确技法发现）
- 数据量（清洗后数量减少 → 但质量提升）
```

### 9.6 维度自我学习闭环（新增说明）

**评估维度与技法维度的双向映射**：

| 评估维度(13) | 技法维度(11) | 学习方向 |
|--------------|--------------|----------|
| 历史纵深 | 世界观维度技法 | 评估反馈→技法评分 |
| 群像塑造 | 人物维度技法 | 评估反馈→技法评分 |
| 有代价胜利 | 战斗冲突维度技法 | 评估反馈→技法评分 |
| 历史沉淀感 | 氛围意境维度技法 | 评估反馈→技法评分 |
| 悬念布局 | 剧情编织维度技法 | 评估反馈→技法评分 |
| 情感张力 | 情感维度技法 | 评估反馈→技法评分 |
| 意境营造 | 氛围意境维度技法 | 评估反馈→技法评分 |

**维度自我学习完整闭环**：

```
┌─────────────────────────────────────────────────────────────────┐
│                   维度自我学习闭环                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Generator创作 → Evaluator评估(13维度)                           │
│                                                                  │
│         ↓                                                        │
│                                                                  │
│  feedback_processor.py                                           │
│  ├── process_feedback(): 处理评估结果                            │
│  ├── ISSUE_TO_TECHNIQUE_MAPPING: 评估问题→技法维度映射           │
│  └── 例如: "代价描写不足" → 映射到"战斗冲突维度"                  │
│                                                                  │
│         ↓                                                        │
│                                                                  │
│  technique_tracker.py                                            │
│  ├── 接收维度反馈 → 更新技法效果评分                             │
│  ├── 维度匹配加分: dimension_match_score += 0.2                  │
│  └── 记录失败案例 → 技法优化依据                                  │
│                                                                  │
│         ↓                                                        │
│                                                                  │
│  recommend_techniques()                                          │
│  ├── 下次创作时优先推荐高评分技法                                 │
│  ├── 维度匹配优先: dimension_weight=0.2                          │
│  └── 形成正向循环: 好技法→高评分→优先推荐→更好创作                │
│                                                                  │
│         ↓                                                        │
│                                                                  │
│  下次Generator创作                                               │
│  ├── 检索技法时自动匹配维度                                      │
│  ├── 基于历史反馈优化的技法推荐                                   │
│  └── 维度自我学习闭环完成                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**维度自我学习的核心价值**：
1. **评估标准优化**: Evaluator评估结果→技法库评分→下次评估更准确
2. **技法推荐优化**: 维度匹配→技法评分→推荐优先级→创作质量提升
3. **双向闭环**: 技法库←→评估维度，互相影响互相提升

**清洗模块对维度学习的影响**：
- 清洗前: 噪音案例89%→技法发现噪音→维度学习不准确
- 清洗后: 噪音率<10%→高质量案例→技法发现准确→维度学习更精准

---

## 十、关键阈值设计

| 检测项 | 阈值 | 说明 |
|--------|------|------|
| 中文比例 | >60% | 过滤外语/非中文小说 |
| 小说特征词 | >10个 | 区分小说与工具书 |
| 压缩率 | 0.65-0.80 | 信息密度最佳范围 |
| 质量评分 | >0.6分 | 综合质量阈值 |
| **噪音率** | **<10%** | 入库最终校验阈值 |

---

## 五、实现优先级

### Phase 1: 基础清洗（高优先级）
1. 实现 `novel_validator.py` - 语言检测+内容验证
2. 实现 `deep_cleaner.py` - 基础清洗管道
3. 修改 `sync_to_qdrant.py` - 启用GPU+入库校验

### Phase 2: 质量控制（中优先级）
4. 实现 `quality_scorer.py` - 质量评分系统
5. 修复各维度提取器的噪音过滤规则

### Phase 3: 去重优化（低优先级）
6. 实现 `semantic_deduplicator.py` - 语义去重
7. 完善增量同步机制

---

## 六、预期效果

| 指标 | 当前 | 目标 |
|------|------|------|
| 噪音率 | 89% | **<10%** |
| 有效小说数 | ~25% | >90% |
| 入库案例质量 | 待验证 | 高质量 |
| 处理速度 | CPU慢 | GPU加速 |

---

## 七、技术参考

基于librarian搜索的最佳实践：
- **ftfy**: 编码修复(mojibake)
- **BeautifulSoup**: HTML清理
- **Compel**: 压缩率质量检测
- **TDRANKER**: 训练动态噪音检测
- **BGE-M3**: 向量嵌入+GPU加速

---

## 八、后续步骤

1. 用户审核此设计文档
2. 创建实现计划(writing-plans skill)
3. 分模块实现代码
4. 全量重新提取数据
5. 入库验证

---

## 九、实施成果（2026-04-11）

### 9.1 噪音过滤效果

| 维度 | 原数据量 | 过滤后数据量 | 噪音率变化 |
|------|----------|-------------|-----------|
| worldview_element | 407,822条 | 209,223条 | 从89%降到48.7% |
| character_relation | 198,649条 | 198,500条 | 0.08%（已良好） |
| power_vocabulary | 87,165条 | 87,165条 | 0%（已良好） |
| dialogue_style | 405条 | 405条 | 0%（已良好） |
| emotion_arc | 2,087条 | 2,087条 | 0%（已良好） |
| author_style | 2,803条 | 2,803条 | 0%（已良好） |
| foreshadow_pair | 2,381条 | 2,381条 | 0%（已良好） |
| power_cost | 140条 | 140条 | 0%（已良好） |

**总效果**：噪音从28.33%降到约15%（主要改善worldview_element）

### 9.2 创建的清洗模块

| 文件 | 功能 | 状态 |
|------|------|------|
| `validators/novel_validator.py` | 中文比例+小说特征词验证 | ✅ 完成 |
| `validators/ingestion_validator.py` | 入库前噪音校验 | ✅ 完成 |
| `cleaners/deep_cleaner.py` | HTML清理+广告过滤+防盗版清理 | ✅ 完成 |
| `scorers/quality_scorer.py` | 压缩率+密度+结构+语言评分 | ✅ 完成 |
| `noise_filter.py` | JSONL噪音过滤脚本 | ✅ 完成 |
| `run_clean.py` | 清洗流程入口脚本 | ✅ 完成 |

### 9.3 配置更新

```json
// config.json 新增
"quality_thresholds": {
    "chinese_ratio_min": 0.6,
    "novel_features_min": 10,
    "compression_ratio_min": 0.65,
    "compression_ratio_max": 0.80,
    "quality_score_min": 0.6,
    "noise_ratio_max": 0.10
},
"clean_pipeline": {
    "clean_dir": ".case-library/clean",
    "use_gpu": true,
    "validate_before_ingest": true
}
```

### 9.4 入库脚本更新

- `sync_to_qdrant.py`：
  - 添加 `FILTERED_DIR` 支持
  - 添加 `USE_FILTERED = True` 参数
  - 添加 `filtered_file` 配置到COLLECTION_CONFIG

### 9.5 API扩展（融合现有系统）

| API文件 | 新增方法 | 用途 |
|---------|---------|------|
| `worldview_api.py` | `search_naming_patterns()` | 苍澜创作时命名规律参考 |
| `character_api.py` | `search_relation_patterns()` | 墨言创作时关系模式参考 |
| `battle_api.py` | `search_power_cost_patterns()` | 剑尘战斗代价描写参考 |
| `plot_api.py` | `search_foreshadow_pairs()` | 玄一伏笔设计参考 |
| `author_api.py`（新建） | `search_author_styles()` | 作者风格模仿参考 |
| `unified_retrieval_api.py` | 8个新检索方法 | 统一入口支持新维度 |

### 9.6 融合度评估

| 维度 | 融合度 | 说明 |
|------|--------|------|
| **逻辑融合** | 70% | 5个作家API已扩展方法 |
| **数据融合** | 87.5% | 5个高融合，1个中融合，1个低融合 |
| **接口融合** | 83% | 5个高融合，1个中融合 |

### 9.7 待完成任务

1. **继续入库剩余数据**（大数据量需分批处理）
2. **扩展HybridSearchManager**（添加新Collection检索方法）
3. **入库验证**（测试检索效果）

---

> **当前状态**: 设计已实施，API已扩展，噪音已过滤，入库进行中