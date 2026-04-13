# Collection三维度功能增强设计方案

> **日期**: 2026-04-13
> **状态**: 待实施
> **作者**: AI分析生成

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

### 5.1 对话管理扩展（writing_techniques_v2）

**目标**: 用户可通过对话添加技法

**新增意图示例**:
```
用户: "加个技法叫有代价胜利"
用户: "战斗场景用节奏控制技法"
```

**实现步骤**:

| 步骤 | 文件 | 修改内容 |
|------|------|----------|
| 1 | `core/conversation/intent_classifier.py` | 添加 `add_technique` 意图模式 |
| 2 | `core/conversation/data_extractor.py` | 添加技法意图映射 |
| 3 | `core/conversation/data_extractor.py` | 实现 `_build_technique_data()` |

**意图模式**:
```python
# intent_classifier.py 新增
"add_technique": {
    "patterns": [
        r"加个技法叫(.+)",
        r"新增技法(.+)",
        r"加一个技法(.+)",
    ],
    "category": IntentCategory.TECHNIQUE,
    "entities": ["technique_name"],
},
"apply_technique": {
    "patterns": [
        r"(.+?)场景用(.+?)技法",
        r"(.+?)技法用于(.+?)场景",
    ],
    "category": IntentCategory.TECHNIQUE,
    "entities": ["scene_type", "technique_name"],
},
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

| 阶段 | 功能 | Collection | 预计工作量 | 优先级 |
|------|------|------------|-----------|--------|
| P0-1 | 自动同步 | case_library_v2 | 30行代码 | 高 |
| P0-2 | 自动同步 | novel_settings_v2 | 20行代码 | 高 |
| P0-3 | 自我学习集成 | case_library_v2 | 40行代码 | 高 |
| P1-1 | 对话管理 | writing_techniques_v2 | 60行代码 | 中 |
| P1-2 | 自我学习 | character_relation_v1 | 100行代码 | 中 |
| P1-3 | 自动同步 | dialogue_style_v1等 | 50行代码 | 中 |

**总预计工作量**: 约300行新增/修改代码

---

## 九、验收标准

### P0验收标准

| 功能 | 验收测试 |
|------|----------|
| case_library_v2自动同步 | `--apply-all --sync-qdrant` 后新场景可检索 |
| novel_settings_v2自动同步 | 对话添加势力后立即可检索 |
| 场景发现集成 | `--scan --discover-scenes` 输出发现结果 |

### P1验收标准

| 功能 | 验收测试 |
|------|----------|
| 技法对话添加 | "加个技法叫有代价胜利" → 技法入库 |
| 人物关系发现 | 新小说处理后发现关系模式 |
| 扩展维度同步 | `run.py --all` 后数据入库 |

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