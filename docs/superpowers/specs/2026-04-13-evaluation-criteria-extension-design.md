# 审核维度扩展方案设计

> **日期**: 2026-04-13
> **状态**: ✅ P0+P1已实现
> **作者**: coffeeliuwei
> **版本**: v14.0
> **目标**: 实现审核维度的动态扩展能力
> **最后更新**: 2026-04-13

---

## 一、背景与问题

### 1.1 当前状态

审核维度（评估标准）目前**硬编码**在 `novelist-evaluator/SKILL.md` 中：

```markdown
### 维度一：禁止项检测（硬性阈值）

| 检测类型 | 具体内容 | 失败标准 |
|----------|----------|----------|
| **AI味表达** | "眼中闪过一丝"、"心中涌起一股"... | 出现1个即失败 |
| **古龙式极简** | 词字独立成段（"痒。""疼。"） | 出现1个即失败 |
```

### 1.2 问题

| 问题 | 影响 |
|------|------|
| **无法动态扩展** | 用户发现新的AI味表达，需手动修改Skill文件 |
| **无法从小说库学习** | 不能从外部小说库自动发现常见问题表达 |
| **无法对话添加** | 用户只能通过编辑文件添加评估标准 |
| **无法自动入库** | 添加后需手动同步，工作流不会自动使用 |

---

## 二、审核维度类型分析

### 2.1 可动态扩展的维度

| 维度类型 | 扩展方式 | 自动发现可行性 |
|----------|----------|----------------|
| **禁止项检测** | 对话添加✅ + 自动发现✅ | 从大量文本中提取高频负面模式 |
| **技法评估阈值** | 对话添加✅ + 手动设定⚠️ | 阈值需人工判断，不可自动发现 |
| **技法评估标准** | 对话添加✅ | 需人工提炼抽象标准 |

### 2.2 不适合动态扩展的维度

| 维度类型 | 原因 |
|----------|------|
| **评估维度分类** | 5大类（禁止项、世界观、剧情、人物、氛围）是固定框架 |
| **输出格式模板** | 评估报告格式需要稳定一致 |

---

## 三、功能需求矩阵

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     审核维度三功能需求矩阵                                     │
├─────────────────────┬──────────────┬──────────────┬──────────────┬─────────┤
│ 维度类型            │ 自动发现     │ 对话添加     │ 自动入库     │ 优先级  │
├─────────────────────┼──────────────┼──────────────┼──────────────┼─────────┤
│ 禁止项检测项        │ ❌ 无用功能  │ ✅ 用户资料  │ ✅ 自动同步  │ P0      │
│ 技法评估标准        │ ❌ 人工提炼  │ ✅ 素材提炼  │ ✅ 自动同步  │ P1      │
│ 技法评估阈值        │ ❌ 手动设定  │ ✅ 对话设定  │ ✅ 自动同步  │ P1      │
└─────────────────────┴──────────────┴──────────────┴──────────────┴─────────┘
```

> **说明**: "自动发现"功能被排除，原因见【十一、不实现的无用功能】

---

## 四、Collection设计

### 4.1 新建Collection: `evaluation_criteria_v1`

**用途**: 存储所有动态审核标准

**Schema设计**:

```python
{
    "id": "eval_001",
    "dimension_type": "prohibition",  # 禁止项/技法标准/技法阈值
    "dimension_name": "禁止项检测",
    
    # 禁止项字段
    "name": "AI味表达",
    "pattern": "眼中闪过{emotion}",
    "examples": ["眼中闪过一丝", "眼中闪过一丝冷意"],
    "threshold": "出现1个即失败",
    
    # 技法标准字段
    "technique_name": "历史纵深",
    "technique_description": "有断层、遗忘、回响",
    "reference_file": "02-世界观维度.md",
    "threshold_score": 6,
    
    # 元数据
    "source": "user_dialogue",  # user_dialogue / auto_discovery / manual
    "created_at": "2026-04-13",
    "updated_at": "2026-04-13",
    "is_active": true
}
```

### 4.2 初始数据来源

**迁移现有硬编码标准**:

| 来源 | 迁移内容 | 数量 |
|------|----------|------|
| `novelist-evaluator/SKILL.md` | 禁止项检测项 | 6类 |
| `novelist-evaluator/SKILL.md` | 技法评估标准 | 5大类×多个技法 |
| `novelist-evaluator/SKILL.md` | 技法评估阈值 | ~15个阈值 |

### 4.3 数据同步实现（已完成）

**同步脚本**: `tools/sync_eval_criteria_to_qdrant.py`

**功能**:
- 从 `evaluation_criteria_migrated.json` 加载26条审核标准
- 使用 BGE-M3 生成1024维向量
- 创建 `evaluation_criteria_v1` Collection
- 批量上传到 Qdrant

**使用方式**:
```bash
# 查看状态
python tools/sync_eval_criteria_to_qdrant.py --status

# 执行同步
python tools/sync_eval_criteria_to_qdrant.py --sync

# 验证结果
python tools/sync_eval_criteria_to_qdrant.py --verify
```

**同步结果**（2026-04-13）:
```
Collection: evaluation_criteria_v1
总记录: 26 条
  - prohibition: 6 条（禁止项检测）
  - technique_criteria: 14 条（技法评估标准）
  - threshold: 6 条（阈值配置）

验证测试:
  - 检索 "AI味表达" → 成功返回匹配结果
  - 检索 "历史纵深" → 成功返回技法标准
```

---

## 五、Evaluator Skill重构方案

### 5.1 当前架构（硬编码）

```
novelist-evaluator/SKILL.md
    ├── 禁止项检测项（硬编码）
    ├── 技法评估标准（硬编码）
    └── 技法评估阈值（硬编码）
    ↓
审核时直接读取Skill内容
```

### 5.2 重构架构（动态加载）

```
novelist-evaluator/SKILL.md（框架层）
    ├── 评估维度分类（固定）
    ├── 输出格式模板（固定）
    └── 动态加载逻辑（新增）
    ↓
启动时从Collection检索：
    ├── evaluation_criteria_v1 → 禁止项列表
    ├── evaluation_criteria_v1 → 技法标准列表
    ├── evaluation_criteria_v1 → 阈值配置
    └── writing_techniques_v2 → 技法内容（现有）
    ↓
动态组合生成评估标准
```

### 5.3 Skill修改内容

**新增章节**: `## 动态评估标准加载`

```markdown
## 动态评估标准加载

### 启动时加载

审核开始前，必须从以下Collection加载最新评估标准：

```python
# 加载禁止项
prohibitions = retrieve_from_collection(
    "evaluation_criteria_v1",
    filter={"dimension_type": "prohibition", "is_active": true}
)

# 加载技法标准
technique_criteria = retrieve_from_collection(
    "evaluation_criteria_v1",
    filter={"dimension_type": "technique_criteria", "is_active": true}
)

# 加载阈值配置
thresholds = retrieve_from_collection(
    "evaluation_criteria_v1",
    filter={"dimension_type": "threshold", "is_active": true}
)
```

### 审核时应用

禁止项检测项使用动态加载的列表，而非硬编码列表。

技法评估使用动态加载的标准和阈值。
```

---

## 六、对话入口层扩展

### 6.1 新增意图类型

| 意图 | 触发词 | 处理流程 |
|------|--------|----------|
| `add_evaluation_criteria` | "添加禁止项"、"新评估标准" | 禁止项提炼流程 |
| `modify_evaluation_threshold` | "修改阈值"、"调整评分标准" | 阈值修改流程 |
| `discover_prohibition_patterns` | "发现常见问题表达" | 自动发现流程 |

### 6.2 禁止项提炼流程

**用户对话示例**:

```
用户: "我发现很多小说用'嘴角勾起一抹'这个表达，感觉很假，能不能加入禁止项？"

系统识别意图: add_evaluation_criteria
    ↓
IntentClarifier: 
    Q: "请确认：您想添加的是禁止项检测项，还是技法评估标准？"
    A: 禁止项
    
    Q: "请提供具体的表达模式，如：'嘴角勾起一抹XX'"
    A: 嘴角勾起一抹微笑/冷笑/弧度
    ↓
PatternExtractor:
    提取模式："嘴角勾起一抹{emotion}"
    提取示例：["嘴角勾起一抹微笑", "嘴角勾起一抹冷笑"]
    与现有禁止项对比（避免重复）
    ↓
入库前确认:
    【建议新增禁止项】
    名称：嘴角勾起一抹
    模式：嘴角勾起一抹{emotion}
    示例：嘴角勾起一抹微笑、嘴角勾起一抹冷笑
    失败标准：出现1个即失败
    
    确认入库？[是/否]
    ↓
用户确认 → 自动入库 → Evaluator下次审核自动使用
```

### 6.2.1 禁止项发现 - 文档路径模式（已实现）

> **新增**: 支持用户提供文档路径，系统自动扫描发现禁止项候选

**意图模式**:
```python
# intent_classifier.py 新增
"discover_prohibitions_from_file": {
    "patterns": [
        r"从文档(.+)发现禁止项",
        r"扫描文件(.+)找禁止项",
        r"分析(.+)文档的禁止项",
        r"发现(.+)\\.md里的假表达",
        r"扫描(.+)文档找假表达",
        r"帮我从(.+)文档发现常见问题表达",
    ],
    "category": IntentCategory.EVALUATION,
    "entities": ["file_path"],
},
```

**文档扫描流程**:
```
用户提供文档路径
    ↓
系统读取文档内容
    ↓
扫描已知"假表达"模式
    ↓
统计高频可疑表达
    ↓
生成禁止项候选列表
    ↓
展示候选供用户选择
    ↓
用户选择确认入库
```

**核心实现**:
```python
# eval_criteria_extractor.py 新增方法
def discover_from_file(self, file_path: str) -> List[ProhibitionCandidate]:
    """
    从文档文件中批量发现禁止项候选
    
    Args:
        file_path: 文档路径
    
    Returns:
        禁止项候选列表
    """
    # 1. 读取文档
    content = self._read_document(file_path)
    
    # 2. 扫描已知"假表达"模式
    candidates = self._scan_for_fake_expressions(content)
    
    # 3. 分析高频可疑表达
    frequency_candidates = self._analyze_high_frequency_patterns(content)
    
    # 4. 合并并去重
    all_candidates = candidates + frequency_candidates
    
    return self._deduplicate_candidates(all_candidates)
```

**已知"假表达"模式库**:
```python
FAKE_EXPRESSION_PATTERNS = [
    # AI味表达
    {"name": "眼中闪过", "pattern": r"眼中闪过(一丝|一抹|一道)"},
    {"name": "心中涌起", "pattern": r"心中涌起(一股|一丝)"},
    {"name": "嘴角勾起", "pattern": r"嘴角勾起(一抹|一丝)"},
    {"name": "不禁表达", "pattern": r"不禁(V+)"},
    
    # 精确数字滥用
    {"name": "精确年龄", "pattern": r"\d{1,2}岁的"},
    
    # 抽象统计词
    {"name": "无数滥用", "pattern": r"无数"},
]
```

**使用示例**:
```
用户: "扫描文件正文/第一章.md找禁止项"

系统:
  [扫描文档] 正文/第一章.md
  
  发现2个潜在禁止项:
  
  1. "眼中闪过" - 出现5次
     类型: 已知AI味表达
     置信度: 80%
     示例: "眼中闪过一丝冷意"、"眼中闪过一抹笑意"
     建议: 添加到禁止项
  
  2. "微微一笑" - 出现8次
     类型: 高频模板表达
     置信度: 50%
     示例: "她微微一笑"、"他微微一笑"
     建议: 需人工判断，可能出现频率过高
  
  选择确认添加？[全部/选择/取消]
```

### 6.3 自动发现流程（❌ 不实现）

> **排除原因**: 高频表达≠禁止项。用户阅读时发现的"假"表达才是真正的禁止项，而非统计高频词。
>
> **替代方案**: 用户通过对话添加（6.2流程），这是最精准的来源。

---

## 七、实施计划

### 7.1 P0阶段（核心功能）

| 步骤 | 任务 | 文件 | 实现状态 |
|------|------|------|----------|
| 1 | 创建Collection | `.vectorstore/bge_m3_config.py` | ✅ 已实现 |
| 2 | 迁移现有标准 | `tools/eval_criteria_migrator.py`（新建） | ✅ 已实现（26条） |
| 3 | 重构Evaluator Skill | `novelist-evaluator/SKILL.md` | ✅ 已实现（动态加载章节） |
| 4 | 对话意图扩展 | `core/conversation/intent_classifier.py` | ✅ 已实现 |

**已实现工作量**: ~185行代码 + Skill修改

### 7.2 P1阶段（完善功能）

| 步骤 | 任务 | 文件 | 实现状态 |
|------|------|------|----------|
| 5 | 禁止项提炼流程（文本） | `core/conversation/eval_criteria_extractor.py`（新建） | ✅ 已实现 |
| 5.1 | 禁止项发现流程（文档） | `core/conversation/eval_criteria_extractor.py` | ✅ 已实现 |
| 6 | 阈值修改流程 | `core/conversation/intent_classifier.py` | ✅ 已实现意图 |
| 7 | 自动入库集成 | `tools/evaluation_criteria_migrated.json` | ✅ 已实现 |

**已实现工作量**: ~190行代码

---

## 八、验收标准

### 8.1 P0验收标准

| 功能 | 验收测试 | 状态 |
|------|----------|------|
| Collection配置 | `bge_m3_config.py` 包含 evaluation_criteria_v1 | ✅ 通过 |
| 标准迁移 | 迁移后生成26条记录（6禁止项+14技法+6阈值） | ✅ 通过 |
| Evaluator动态加载 | SKILL.md 新增动态加载章节 | ✅ 通过 |
| 对话意图识别 | IntentClassifier识别 add_evaluation_criteria | ✅ 通过 |

### 8.2 P1验收标准

| 功能 | 验收测试 | 状态 |
|------|----------|------|
| 禁止项提炼（文本） | "这个表达很假" → 提取模式 → 展示候选 | ✅ 通过 |
| 禁止项发现（文档） | "扫描文件正文/第一章.md找禁止项" → 展示候选列表 | ✅ 通过 |
| 文档意图识别 | IntentClassifier识别 discover_prohibitions_from_file | ✅ 通过 |
| 已知模式匹配 | 扫描文档发现AI味表达（眼中闪过、嘴角勾起等） | ✅ 通过 |
| 高频表达分析 | 识别高频模板表达（微微一笑等） | ✅ 通过 |
| 自动入库 | 确认后写入 evaluation_criteria_migrated.json | ✅ 通过 |

### 8.3 P2验收标准

| 功能 | 验收测试 | 状态 |
|------|----------|------|
| 自动发现（大批量） | 扫描1000篇小说后，输出≥10个候选禁止项 | ⏳ 待验证 |
| 批量审批 | 选择多个候选后，批量入库成功 | ⏳ 待验证 |

### 集成测试结果

```
tests/test_integration.py: 26 passed in 1.02s
```

---

## 九、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Evaluator加载失败 | 使用默认标准 | 保留Skill硬编码作为fallback |
| 禁止项误添加 | 过度严格审核 | 添加审批流程，用户确认后入库 |
| 阈值设置不当 | 评估结果偏差 | 提供阈值调整建议，不自动设定 |

---

## 十、与其他系统的关系

### 10.1 与Collection增强方案的关系

| 系统 | 关系 |
|------|------|
| Collection三维度增强 | 本方案是三维度功能在审核维度的具体应用 |
| 技法素材提炼模式 | 禁止项提炼复用技法提炼流程 |
| 统一检索API | Evaluator从Collection检索评估标准 |

### 10.2 与现有Collection的关系

| Collection | 关系 |
|------------|------|
| `evaluation_criteria_v1` | **新建**，存储审核标准 |
| `writing_techniques_v2` | 技法内容来源（现有） |
| `case_library_v2` | 禁止项自动发现的文本来源（现有） |

---

## 十一、不需要实现的功能（明确排除）

| 功能 | 排除原因 |
|------|----------|
| 评估维度分类自动发现 | 5大类框架固定，不应动态变化 |
| 输出格式模板动态修改 | 评估报告格式需要稳定一致 |
| 技法阈值自动设定 | 阈值需要人工判断，不可自动推断 |

---

## 十二、后续优化方向

1. **禁止项模式库扩充**: 通过持续使用积累更多禁止项
2. **阈值自适应调整**: 根据历史评估结果自动建议阈值调整
3. **跨用户标准共享**: 支持不同用户有不同的评估标准配置
4. **评估标准版本管理**: 支持回退到历史版本评估标准

---

> **设计完成**: 待用户确认后进入实施阶段