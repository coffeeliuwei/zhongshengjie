# Collection三维度功能增强设计方案

> **日期**: 2026-04-13
> **状态**: ✅ P0已实现，P1部分实现
> **作者**: coffeeliuwei
> **版本**: v14.0
> **最后更新**: 2026-04-13

---

## 一、背景与问题

众生界项目包含12个Qdrant Collection，需要分析并解决以下三个核心问题：

1. **自我学习**: 能否从外部小说库自动学习出新的Collection或Collection内数据？
2. **对话管理**: 能否通过对话方式增删Collection或Collection内数据？
3. **自动同步**: 数据变更后，Collection是否会自动同步到向量库？

---

## 二、Collection分类与功能必要性

### 2.1 活跃类（需要完整或部分功能）

| Collection | 数据特点 | 需要的功能 |
|------------|----------|------------|
| **case_library_v2** | 从小说库动态提取，场景类型可扩展 | 自我学习✅、自动同步✅ |
| **novel_settings_v2** | 用户创作的核心内容，频繁更新 | 对话管理✅、自动同步✅ |
| **dialogue_style_v1** | 从小说库提取，势力可能增加 | 自我学习⚠️、自动同步✅ |
| **power_cost_v1** | 从小说库提取，力量体系固定 | 自动同步✅ |
| **character_relation_v1** | 从小说库提取，人物关系动态 | 自我学习✅、自动同步✅ |

### 2.2 静态类（只需要基础同步）

| Collection | 数据特点 | 需要的功能 |
|------------|----------|------------|
| **writing_techniques_v2** | 技法是抽象知识，需要人工提炼 | 对话管理⚠️（添加）、手动同步 |
| **emotion_arc_v1** | 6种情感弧线，固定模板 | 手动同步 |
| **power_vocabulary_v1** | 词汇库相对固定 | 手动同步 |
| **worldview_element_v1** | 地点/组织可增加但频率低 | 手动同步 |
| **foreshadow_pair_v1** | 伏笔配对模式固定 | 手动同步 |
| **author_style_v1** | 作者风格指纹，分析类 | 手动同步 |

### 2.3 冷数据类（不需要任何功能）

| Collection | 原因 |
|------------|------|
| **poetry_imagery_v2** | 诗词意象是固定文化知识，31个向量点足够，不需要动态更新 |
| **chapter_structure_v1** | 章节结构分析是一次性工作，长期使用 |

---

## 三、功能需求矩阵

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     12个Collection三维度功能需求矩阵                          │
├─────────────────────┬──────────────┬──────────────┬──────────────┬─────────┤
│ Collection          │ 自我学习     │ 对话管理     │ 自动同步     │ 适用性  │
├─────────────────────┼──────────────┼──────────────┼──────────────┼─────────┤
│ case_library_v2     │ ✅ 场景发现  │ ❌ 不支持    │ ⚠️ 手动触发 │ P0      │
│ writing_techniques_v2│ ❌ 人工总结 │ ✅ 添加技法  │ ⚠️ 手动触发 │ P1      │
│ novel_settings_v2   │ ❌ 用户定义  │ ✅ 添加设定  │ ⚠️ 手动触发 │ P0      │
│ dialogue_style_v1   │ ✅ 自动提取  │ ❌ 不支持    │ ⚠️ 手动触发 │ P1      │
│ power_cost_v1       │ ✅ 自动提取  │ ❌ 不支持    │ ⚠️ 手动触发 │ P1      │
│ emotion_arc_v1      │ ✅ 自动提取  │ ❌ 不支持    │ ⚠️ 手动触发 │ 不需要  │
│ power_vocabulary_v1 │ ✅ 自动提取  │ ❌ 不支持    │ ⚠️ 手动触发 │ 不需要  │
│ character_relation_v1│ ✅ 自动提取 │ ❌ 不支持    │ ⚠️ 手动触发 │ P1      │
│ worldview_element_v1 │ ✅ 自动提取 │ ❌ 不支持    │ ⚠️ 手动触发 │ 不需要  │
│ foreshadow_pair_v1  │ ✅ 自动提取  │ ❌ 不支持    │ ⚠️ 手动触发 │ 不需要  │
│ author_style_v1     │ ✅ 自动提取  │ ❌ 不支持    │ ⚠️ 手动触发 │ 不需要  │
│ poetry_imagery_v2   │ ❌ 无        │ ❌ 无        │ ❌ 无        │ 不需要  │
└─────────────────────┴──────────────┴──────────────┴──────────────┴─────────┘
```

---

## 四、P0必做功能实现方案

### 4.1 自动同步集成（case_library_v2）

**目标**: 场景发现审批后，自动同步到向量库

**当前流程（手动）**:
```bash
python scene_discoverer.py --discover
python scene_discoverer.py --approve "交易场景"
python scene_discoverer.py --apply-all  # ← 只更新配置文件
python tools/data_migrator.py --collection case  # ← 需要手动运行
```

**改进流程（自动）**:
```bash
python scene_discoverer.py --approve "交易场景"
python scene_discoverer.py --apply-all --sync-qdrant  # ← 自动同步向量库
```

**实现步骤**:

| 步骤 | 文件 | 修改内容 |
|------|------|----------|
| 1 | `tools/scene_discoverer.py` | 在 `sync_all()` 方法末尾添加向量库同步调用 |
| 2 | `tools/scene_discoverer.py` | 导入 `SyncManager` 或 `DataMigrator` |
| 3 | `tools/scene_discoverer.py` | 添加 `--sync-qdrant` 参数控制是否自动同步 |
| 4 | 验证 | 运行完整流程确认数据入库 |

**代码示例**:
```python
# scene_discoverer.py sync_all() 方法新增
def sync_all(self, scenes):
    # 现有逻辑：同步到配置文件
    synced_case_builder = self.sync_to_case_builder(scenes)
    synced_mapping = self.sync_to_scene_mapping(scenes)
    synced_skill = self.sync_to_skill_file(scenes)
    
    # 新增：同步到向量库（可选）
    if self.config.get("sync_qdrant") and synced_case_builder > 0:
        from modules.knowledge_base.sync_manager import SyncManager
        sync_manager = SyncManager()
        sync_manager.sync_cases()  # 触发案例库增量同步
        print(f"  [OK] 已同步 {synced_case_builder} 个场景到向量库")
```

---

### 4.2 自动同步集成（novel_settings_v2）

**目标**: 对话添加设定后，自动同步到向量库

**当前流程（手动）**:
```
用户: "加个新势力叫暗影宗"
系统: 更新 设定/十大势力.md  # ← 只更新文件
用户需要手动: python data_migrator.py --collection novel
```

**改进流程（自动）**:
```
用户: "加个新势力叫暗影宗"
系统: 更新 设定/十大势力.md → 自动同步 novel_settings_v2
```

**实现步骤**:

| 步骤 | 文件 | 修改内容 |
|------|------|----------|
| 1 | `core/conversation/data_extractor.py` | 实现 `_sync_to_vectorstore()` 方法 |
| 2 | `core/conversation/data_extractor.py` | 在 `extract_and_update()` 中调用同步 |
| 3 | 验证 | 测试对话添加设定后立即可检索 |

**代码示例**:
```python
# data_extractor.py 新增方法
def _sync_to_vectorstore(self, collection: str, data: Dict) -> bool:
    """同步数据到向量库"""
    if collection == "novel_settings_v2":
        from modules.knowledge_base.sync_manager import SyncManager
        sync_manager = SyncManager()
        sync_manager.sync_novel_settings()  # 增量同步
        return True
    return False

def extract_and_update(self, user_input: str, intent_result: IntentResult):
    # 现有逻辑：更新文件
    file_update_result = self._update_source_file(...)
    
    # 新增：自动同步到向量库
    collection = self.INTENT_COLLECTION_MAPPING.get(intent_result.intent)
    if collection and file_update_result:
        self._sync_to_vectorstore(collection, structured_data)
```

---

### 4.3 自我学习集成（case_library_v2 - 场景发现）

**目标**: 将已有的场景发现器集成到日常工作流

**当前状态**: 已实现 `scene_discoverer.py`，但需要手动触发

**改进方案**: 将场景发现作为增量同步的一部分

**实现步骤**:

| 步骤 | 文件 | 修改内容 |
|------|------|----------|
| 1 | `.novel-extractor/incremental_sync.py` | 添加 `--discover-scenes` 参数 |
| 2 | `.novel-extractor/incremental_sync.py` | 在扫描新小说后调用 `SceneDiscoverer` |
| 3 | `.novel-extractor/incremental_sync.py` | 输出发现的场景供用户审批 |

**工作流示例**:
```bash
python incremental_sync.py --scan --discover-scenes

# 输出：
# 扫描到 5 本新小说
# 发现 2 个潜在新场景类型：
#   - 交易场景（置信度 85%，样本 120）
#   - 修炼感悟（置信度 72%，样本 45）
# 
# 使用 scene_discoverer.py --approve "交易场景" 批准
```

---

## 五、P1建议做功能实现方案

### 5.1 技法提炼模式（writing_techniques_v2）

**目标**: 用户提供素材，系统自动提炼技法，用户确认后入库

**设计背景**:

用户通常不知道什么是"技法"，只会提供素材让系统分析：

| 用户实际表达 | 原设计假设 |
|------------|-----------|
| "这段战斗描写很好，提炼一下技法" | ❌ "加个技法叫有代价胜利" |
| "从这个案例学习一下写法" | ❌ 用户知道技法概念 |
| "分析这段文字用了什么技巧" | ❌ 手动命名添加 |

**新的工作流程**:
```
用户提供素材 → 技法提取器分析 → 生成技法候选 → 用户确认 → 入库

步骤详解：
1. 用户: "这段战斗描写很好，提炼一下技法"
2. 系统: 
   - 分析文本内容
   - 检索现有技法库进行对比学习
   - 提取技法要素（如"节奏控制"、"力量代价"、"心理博弈"）
   - 将技法归入合适的维度（如"战斗冲突维度"）
3. 系统: 展示提炼结果
   ```
   提炼结果：
   - 技法名称：有代价胜利
   - 维度：战斗冲突维度
   - 核心要素：胜利后需要付出代价（如消耗、伤势、心理创伤）
   - 适用场景：战斗场景、高潮场景
   - 示例片段：（用户提供的素材摘要）
   
   是否入库？[确认/修改/取消]
   ```
4. 用户确认 → 技法写入创作技法库 → 同步到向量库
```

**实现步骤**:

| 步骤 | 文件 | 修改内容 |
|------|------|----------|
| 1 | `core/conversation/intent_classifier.py` | 添加 `extract_technique` 意图模式 |
| 2 | `core/conversation/` | 创建 `technique_extractor.py` 技法提取器 |
| 3 | `core/conversation/data_extractor.py` | 调用技法提取器，处理用户确认 |
| 4 | `创作技法/` | 自动创建技法MD文件并同步 |

**意图模式**:
```python
# intent_classifier.py 新增
"extract_technique": {
    "patterns": [
        r"从(.+)提炼技法",
        r"这段(.+)用了什么技法",
        r"分析(.+)的写法",
        r"学习(.+)的技巧",
        r"(.+)有什么技法可以学习",
        r"看看(.+)用的是什么手法",
    ],
    "category": IntentCategory.TECHNIQUE,
    "entities": ["content_reference"],
},
"confirm_technique": {
    "patterns": [
        r"确认入库",
        r"这个技法可以",
        r"好的入库",
    ],
    "category": IntentCategory.CONFIRMATION,
    "entities": [],
},
```

**技法提取器核心逻辑**:
```python
# technique_extractor.py 核心方法
class TechniqueExtractor:
    def extract_from_content(self, content: str) -> TechniqueCandidate:
        """
        从用户提供的素材中提取技法
        
        流程：
        1. 检索现有技法库，找到相似技法和维度参考
        2. 分析素材中的技法要素（结构、节奏、对比等）
        3. 生成技法候选（名称、维度、要素、适用场景）
        """
        
        # 1. 检索相似技法
        similar_techniques = self.search_similar(content)
        
        # 2. 分析技法要素
        elements = self.analyze_elements(content)
        # 可能的要素：节奏控制、力量代价、心理博弈、情感层次...
        
        # 3. 归入维度
        dimension = self.match_dimension(elements)
        # 11个维度：开篇维度、人物维度、剧情维度、战斗冲突维度...
        
        # 4. 生成技法候选
        return TechniqueCandidate(
            name=self.generate_name(elements),
            dimension=dimension,
            elements=elements,
            applicable_scenes=self.infer_scenes(content),
            source_content=content[:500],  # 保留素材摘要
        )
```

**技法入库流程**:
```python
# data_extractor.py 新增
def extract_and_update(self, user_input: str, intent_result: IntentResult):
    if intent_result.intent == "extract_technique":
        # 1. 提取技法
        technique = self.technique_extractor.extract_from_content(
            user_input  # 或从上下文获取素材内容
        )
        
        # 2. 展示给用户确认
        return ExtractionResult(
            success=True,
            data={
                "technique": technique,
                "awaiting_confirmation": True
            }
        )
    
    elif intent_result.intent == "confirm_technique":
        # 3. 用户确认后入库
        technique = self.pending_technique  # 保存的待确认技法
        
        # 4. 写入技法文件
        self._write_technique_file(technique)
        
        # 5. 同步到向量库
        self._sync_to_vectorstore("writing_techniques_v2", technique)
```

### 5.1.1 技法提炼 - 文档路径模式（已实现）

> **新增**: 支持用户提供文档路径，系统自动分析提炼

**意图模式**:
```python
# intent_classifier.py 新增
"extract_technique_from_file": {
    "patterns": [
        r"从文件(.+)提炼技法",
        r"分析文档(.+)的技法",
        r"提炼(.+)\\.md里的技法",
        r"看看(.+)文档有什么技法",
        r"分析(.+)\\.txt中的技法",
        r"帮我分析(.+)文档",
        r"提炼这个文档(.+)的技法",
    ],
    "category": IntentCategory.TECHNIQUE,
    "entities": ["file_path"],
},
```

**文档分析流程**:
```
用户提供文档路径
    ↓
系统读取文档内容
    ↓
分段处理（每段100-5000字）
    ↓
逐段提炼技法候选
    ↓
去重合并相似技法
    ↓
展示候选列表供用户选择
    ↓
用户选择确认入库
```

**核心实现**:
```python
# technique_extractor.py 新增方法
def extract_from_file(self, file_path: str) -> List[TechniqueCandidate]:
    """
    从文档文件中批量提取技法
    
    Args:
        file_path: 文档路径（相对或绝对）
    
    Returns:
        技法候选列表（可能包含多个技法）
    """
    # 1. 解析路径（支持相对路径）
    full_path = self._resolve_file_path(file_path)
    
    # 2. 读取文档
    content = self._read_document(full_path)
    
    # 3. 分段分析（长文档需要分段）
    segments = self._segment_document(content)
    
    # 4. 对每个段提炼技法
    candidates = []
    for segment in segments:
        if len(segment) >= 100:
            candidate = self.extract_from_content(segment)
            candidates.append(candidate)
    
    # 5. 去重和合并相似技法
    unique_candidates = self._deduplicate_candidates(candidates)
    
    return unique_candidates
```

**使用示例**:
```
用户: "分析文档设定/人物谱.md的技法"

系统:
  [读取文档] 设定/人物谱.md (3000字符)
  [分段分析] 12个段落
  
  发现3个技法候选:
  1. 群像塑造技法 (维度: 人物维度, 置信度: 80%)
     - 核心要素: 多主角、独立命运线
     - 适用场景: 人物出场、剧情展开
  
  2. 性格对比技法 (维度: 人物维度, 置信度: 70%)
     - 核心要素: 道德灰色、立场分明
     - 适用场景: 人物塑造、对话场景
  
  3. 关系张力技法 (维度: 剧情维度, 置信度: 60%)
     - 核心要素: 选择代价、情感纠葛
     - 适用场景: 情感场景、转折场景
  
  选择确认入库？[全部/选择/取消]
```

---

### 5.2 自我学习扩展（character_relation_v1）

**目标**: 从新小说发现人物关系模式

**实现思路**: 利用 `TypeDiscoverer` 框架创建人物关系发现器

**实现步骤**:

| 步骤 | 文件 | 修改内容 |
|------|------|----------|
| 1 | `core/type_discovery/` | 创建 `CharacterRelationDiscoverer.py` |
| 2 | `.novel-extractor/incremental_sync.py` | 处理后调用发现器 |

---

### 5.3 自动同步扩展（dialogue_style_v1等）

**目标**: 小说增量同步后，扩展维度数据自动入库

**实现步骤**:

| 步骤 | 文件 | 修改内容 |
|------|------|----------|
| 1 | `.novel-extractor/run.py` | 在 `--all` 模式完成后调用同步 |
| 2 | `tools/data_migrator.py` | 为 v1 Collection 添加增量同步支持 |

---

## 六、P2可选功能（暂不实现）

### 6.1 维度自动发现（新Collection类型）

**目标**: 从小说内容发现新的数据类别

**复杂度**: 高，需要语义模型支持，暂不实施

### 6.2 Collection管理意图

**目标**: 通过对话创建/删除Collection

**风险**: 安全风险高，需要权限控制

### 6.3 文件监听自动同步

**目标**: 实时监听文件变更，自动触发同步

**技术**: 使用 `watchdog` 库

---

## 七、不需要实现的功能（明确排除）

| Collection | 排除的功能 | 原因 |
|------------|-----------|------|
| poetry_imagery_v2 | 全部三个功能 | 固定诗词知识库，无需动态更新 |
| chapter_structure_v1 | 全部三个功能 | 分析结果，一次提取长期使用 |
| author_style_v1 | 自我学习、对话管理 | 作者风格分析不频繁更新 |
| emotion_arc_v1 | 自我学习、对话管理 | 6种固定情感模板 |
| foreshadow_pair_v1 | 自我学习、对话管理 | 伏笔模式固定 |
| power_vocabulary_v1 | 对话管理 | 词汇库自动提取，不需要手动添加 |
| worldview_element_v1 | 对话管理 | 地点/组织通过设定添加 |

---

## 八、实施计划

| 阶段 | 功能 | Collection | 实现状态 | 优先级 |
|------|------|------------|----------|--------|
| P0-1 | 自动同步 | case_library_v2 | ✅ 已实现 | 高 |
| P0-2 | 自动同步 | novel_settings_v2 | ✅ 已实现 | 高 |
| P0-3 | 场景发现集成 | case_library_v2 | ✅ 已实现 | 高 |
| P1-1 | 对话管理（文本粘贴） | writing_techniques_v2 | ✅ 已实现 | 中 |
| P1-1.1 | 对话管理（文档路径） | writing_techniques_v2 | ✅ 已实现 | 中 |
| P1-2 | 自我学习 | character_relation_v1 | ⏳ 待实现 | 中 |
| P1-3 | 自动同步 | dialogue_style_v1等 | ⏳ 待实现 | 中 |

**总工作量**: 约300行新增/修改代码 + 新增2个文件

**已实现文件清单**:
```
tools/scene_discoverer.py          # 修改: 新增 --sync-qdrant 参数
core/conversation/file_updater.py  # 修改: 完善 sync_to_vectorstore()
.novel-extractor/incremental_sync.py # 修改: 新增 --discover-scenes 参数
core/conversation/technique_extractor.py # 新建: 技法提炼器
core/conversation/intent_classifier.py   # 修改: 新增技法相关意图
.vectorstore/bge_m3_config.py      # 修改: 新增 evaluation_criteria_v1
tools/eval_criteria_migrator.py    # 新建: 审核维度迁移工具
core/conversation/eval_criteria_extractor.py # 新建: 禁止项提炼器
```

---

## 九、验收标准

### P0验收标准

| 功能 | 验收测试 | 状态 |
|------|----------|------|
| case_library_v2自动同步 | `--apply-all --sync-qdrant` 后新场景可检索 | ✅ 通过 |
| novel_settings_v2自动同步 | 对话添加势力后立即可检索 | ✅ 通过 |
| 场景发现集成 | `--scan --discover-scenes` 输出发现结果 | ✅ 通过 |

### P1验收标准

| 功能 | 验收测试 | 状态 |
|------|----------|------|
| 技法对话添加（文本） | "从这段战斗描写提炼技法" → 展示候选 | ✅ 通过 |
| 技法对话添加（文档） | "分析文档设定/人物谱.md的技法" → 展示候选列表 | ✅ 通过 |
| 技法意图识别 | IntentClassifier识别 extract_technique_from_file | ✅ 通过 |
| 文档分段提炼 | 长文档分段处理 + 去重合并 | ✅ 通过 |
| 人物关系发现 | 新小说处理后发现关系模式 | ⏳ 待验证 |
| 扩展维度同步 | `run.py --all` 后数据入库 | ⏳ 待验证 |

### 集成测试结果

```
tests/test_integration.py: 26 passed in 1.02s
- TestDataFlowIntegration: 3 passed
- TestConversationLayerIntegration: 4 passed
- TestStateManagementIntegration: 4 passed
- TestErrorRecoveryIntegration: 4 passed
- TestConfigSystemIntegration: 4 passed
- TestMultiModuleIntegration: 4 passed
- TestPerformanceIntegration: 3 passed
```

---

## 十、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 自动同步触发频繁 | 向量库压力 | 添加阈值控制，批量同步 |
| 对话意图误识别 | 错误数据写入 | 添加确认机制，回滚支持 |
| 场景发现精度低 | 无效场景入库 | 提高置信度阈值，人工审批 |

---

## 十一、附录

### 附录A：现有基础设施

- `ChangeDetector`: 文件变更检测器（已实现，未启用）
- `FileWatcher`: mtime+hash监控（已实现）
- `SceneDiscoverer`: 场景类型发现器（已实现）
- `TypeDiscoverer`: 统一类型发现框架（已实现）

### 附录B：相关文件路径

- `tools/scene_discoverer.py` - 场景发现器
- `tools/data_migrator.py` - Collection同步工具
- `core/conversation/data_extractor.py` - 对话数据提取
- `core/conversation/intent_classifier.py` - 意图分类
- `modules/knowledge_base/sync_manager.py` - 同步管理器
- `.novel-extractor/incremental_sync.py` - 增量同步系统

---

**文档结束**