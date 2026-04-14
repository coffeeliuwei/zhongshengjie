# 众生界 - 项目逻辑记录

> **作者**：coffeeliuwei
> **版本**：v14.0
> **最后更新**：2026-04-13
> 
> 本文件记录**众生界项目**的核心逻辑，用于指导AI自动生成小说。
> 
> **区分**：
> - 本文件 = 项目系统逻辑（工作流、作家分工、约束）
> - 小说内容 = 存储在 `总大纲.md`、`设定/` 等文件中

---

## 一、项目目标

**全自动小说生成**：用户输入章节名，系统自动完成创作、评估、输出。

---

## 二、核心架构

### Generator/Evaluator 分离

| 角色 | 职责 |
|------|------|
| **Generator** | 创作（5位作家各司其职） |
| **Evaluator** | 评估（独立审核，保证质量） |

**约束**：不允许跳过 Evaluator 评估（硬约束）

---

## 三、作家系统

| 作家 | Skill | 专长 |
|------|-------|------|
| **苍澜** | novelist-canglan | 世界观架构 |
| **玄一** | novelist-xuanyi | 剧情编织 |
| **墨言** | novelist-moyan | 人物刻画 |
| **剑尘** | novelist-jianchen | 战斗设计 |
| **云溪** | novelist-yunxi | 意境营造 |
| **Evaluator** | novelist-evaluator | 审核评估 |

---

## 四、创作工作流（9个阶段）

```
用户输入："写第一章"
        ↓
【阶段0】需求澄清（互相启发讨论）
        ↓
【阶段1】章节大纲解析
        ↓
【阶段2】场景类型识别（28种场景类型）
        ↓
【阶段2.5】经验检索 ← 从前章日志提取
        ↓
【阶段3】设定自动检索 ← 从Qdrant检索（14个Collection）
        ↓
【阶段3.5】场景契约 ← 12大一致性规则
        ↓
【阶段4】逐场景创作
│   ├── Phase 1：并行生成（苍澜/玄一/墨言）
│   ├── Phase 1.5：一致性检测
│   ├── Phase 1.6：融合调整（云溪）
│   ├── Phase 2：核心创作（主作家）
│   └── Phase 3：收尾润色（云溪）
        ↓
【阶段5】整章整合
        ↓
【阶段6】整章评估 ← Evaluator（13维度+动态审核标准）
        ↓
【阶段7】用户确认
        ↓
【阶段8】经验写入 ← 日志存储
```

---

## 五、场景类型与作家分工

### 28种场景类型

| 场景类型 | 负责作家 | Skill | 说明 |
|----------|----------|-------|------|
| 开篇 | 云溪 | novelist-yunxi | 章节开头引入 |
| 结尾 | 云溪 | novelist-yunxi | 章节收尾余韵 |
| 战斗 | 剑尘 | novelist-jianchen | 战斗场面描写 |
| 情感 | 墨言 | novelist-moyan | 情感细腻描写 |
| 悬念 | 玄一 | novelist-xuanyi | 悬念铺设紧张感 |
| 转折 | 玄一 | novelist-xuanyi | 剧情反转 |
| 世界观展开 | 苍澜 | novelist-canglan | 世界观细节展示 |
| **打脸** | 剑尘 | novelist-jianchen | 爽点爆发场景（新增） |
| **高潮** | 剑尘 | novelist-jianchen | 情节顶点场景（新增） |
| 人物出场 | 墨言 | novelist-moyan | 新角色登场 |
| 成长蜕变 | 墨言 | novelist-moyan | 角色内心转变 |
| 伏笔设置 | 玄一 | novelist-xuanyi | 埋下线索 |
| 伏笔回收 | 玄一 | novelist-xuanyi | 揭示前文线索 |
| **阴谋揭露** | 玄一 | novelist-xuanyi | 揭示隐藏计划（新增） |
| **社交** | 墨言 | novelist-moyan | 人物互动交往（新增） |
| 势力登场 | 苍澜 | novelist-canglan | 新势力引入 |
| 修炼突破 | 剑尘 | novelist-jianchen | 力量提升场景 |
| 资源获取 | 剑尘 | novelist-jianchen | 获得资源/宝物 |
| 探索发现 | 云溪 | novelist-yunxi | 探险发现新事物 |
| 情报揭示 | 玄一 | novelist-xuanyi | 关键信息披露 |
| 危机降临 | 剑尘 | novelist-jianchen | 危险到来 |
| 冲突升级 | 剑尘 | novelist-jianchen | 矛盾激化 |
| 团队组建 | 墨言 | novelist-moyan | 队伍集结 |
| 反派出场 | 墨言 | novelist-moyan | 反派角色登场 |
| 恢复休养 | 云溪 | novelist-yunxi | 战后休整 |
| 回忆场景 | 墨言 | novelist-moyan | 过往回忆插叙 |

---

### Phase 1：并行生成（3人）

```
苍澜 → 世界观约束草稿
玄一 → 剧情框架草稿
墨言 → 人物状态草稿
```

### Phase 1.5：一致性检测

自动检测冲突：
- 遗忘 vs 记住
- 时间线矛盾
- 设定不一致

### Phase 1.6：融合调整

| 冲突数 | 处理方式 |
|--------|----------|
| ≤2个 | 自动融合 |
| 3-5个 | 云溪介入 |
| >5个 | 用户确认 |

### Phase 2：核心创作

使用融合后的统一约束，由主作家执行

### Phase 3：收尾润色

云溪统一风格，消除拼合痕迹

---

## 六、评估系统

### 13个评估维度

1. 技法运用准确度
2. 约束遵守度
3. 角色行为一致性
4. 世界观设定一致性
5. 叙事流畅度
6. 情感张力
7. 节奏把控
8. 场景契约一致性
9. 语言风格
10. 主题表达
11. 伏笔质量
12. 读者体验
13. 创新度

### 约束检测（铁律）

| 约束 | 说明 | 级别 |
|------|------|------|
| **禁止具体年龄** | 只能用"幼年"、"青年"等模糊词 | HARD |
| **禁止模糊数字** | 必须用具体数字，如"三十七个男人" | HARD |
| **禁止AI味表达** | 禁止"眼中闪过一丝XXX"等模板 | HARD |
| **境界不能倒退** | 除非大纲明确标注 | SOFT |
| **Evaluator必须通过** | 不通过不能定稿 | HARD |

### AI味检测

| 禁止 | 替代 |
|------|------|
| "眼中闪过一丝XXX" | 用动作代替 |
| "心中涌起一股XXX" | 用身体反应代替 |
| "嘴角勾起一抹XXX" | 删除或用动作代替 |
| "**加粗文字**" | 中文小说不加粗 |

---

## 七、场景契约（12大一致性规则）

| 规则 | 检查项 | 级别 |
|------|--------|------|
| R001 | 人物数量一致性 | Critical |
| R002 | 时间因果性 | Critical |
| R003 | 空间连续性 | Warning |
| R004 | 代词一致性 | Critical |
| R005 | 物体状态连续性 | Critical/Warning |
| R006 | 角色状态转换合理性 | Critical |
| R007 | 势力攻击类型一致性 | Critical |
| R008 | 天气环境一致性 | Warning |
| R009 | 角色特征一致性 | Critical |
| R010 | 称呼一致性 | Warning |
| R011 | 势力构成一致性 | Warning |
| R012 | 能力技能一致性 | Critical |

---

## 八、检索系统

### Qdrant Collections（14个，更新于2026-04-13）

| Collection | 用途 | 数据量 | 三维度功能 |
|------------|------|--------|------------|
| `writing_techniques_v2` | 创作技法 | 986条 | ✅自我学习 ✅对话管理 ✅自动同步 |
| `novel_settings_v2` | 小说设定 | 160条 | ✅自我学习 ✅对话管理 ✅自动同步 |
| `case_library_v2` | 标杆案例 | 387,377条 | ✅自我学习 ❌对话管理 ✅自动同步 |
| `dialogue_style_v1` | 对话风格 | 405条 | ✅自我学习 ❌对话管理 ✅自动同步 |
| `power_cost_v1` | 力量代价 | 140条 | ✅自我学习 ❌对话管理 ✅自动同步 |
| `emotion_arc_v1` | 情感弧线 | 446条 | ✅自我学习 ❌对话管理 ✅自动同步 |
| `power_vocabulary_v1` | 力量词汇 | 41,247条 | ✅自我学习 ❌对话管理 ✅自动同步 |
| `foreshadow_pair_v1` | 伏笔对 | 54条 | ✅自我学习 ❌对话管理 ✅自动同步 |
| `evaluation_criteria_v1` | 审核标准 | - | ❌自我学习 ✅对话管理 ✅自动同步 |
| `chapter_experience_v1` | 章节经验 | - | ✅自我学习 ❌对话管理 ✅自动同步 |

> **Collection三维度功能说明**：
> - **自我学习**：Collection是否支持从用户反馈自动学习优化
> - **对话管理**：Collection是否支持在对话中直接增删改查
> - **自动同步**：Collection是否支持配置变更自动同步

### source_map场景检索映射（28种场景）

```python
source_map = {
    # 基础检索
    "novel": "novel_settings_v2",           # 角色/势力/设定
    "technique": "writing_techniques_v2",   # 创作技法
    "case": "case_library_v2",              # 标杆案例
    
    # 扩展维度检索（新增）
    "emotion_arc": "emotion_arc_v1",        # 情感弧线参考
    "foreshadow_pair": "foreshadow_pair_v1", # 伏笔对参考
    "dialogue_style": "dialogue_style_v1",  # 对话风格
    "power_cost": "power_cost_v1",          # 力量代价
    "power_vocabulary": "power_vocabulary_v1", # 力量词汇
}

# 28种场景类型检索策略
def retrieve_for_scene(scene_type: str, query: str):
    """根据场景类型智能选择检索源"""
    
    scene_sources = {
        "开篇": ["novel", "technique", "case", "emotion_arc"],
        "结尾": ["novel", "technique", "case", "emotion_arc", "foreshadow_pair"],
        "战斗": ["novel", "technique", "case", "power_cost", "power_vocabulary"],
        "打脸": ["novel", "technique", "case", "power_cost"],
        "高潮": ["novel", "technique", "case", "emotion_arc", "foreshadow_pair"],
        "情感": ["novel", "technique", "case", "emotion_arc", "dialogue_style"],
        "人物出场": ["novel", "technique", "case", "dialogue_style"],
        "成长蜕变": ["novel", "technique", "case", "emotion_arc"],
        "回忆场景": ["novel", "technique", "case", "emotion_arc"],
        "社交": ["novel", "technique", "case", "dialogue_style"],
        "悬念": ["novel", "technique", "case", "foreshadow_pair"],
        "伏笔设置": ["novel", "technique", "case", "foreshadow_pair"],
        "伏笔回收": ["novel", "technique", "case", "foreshadow_pair"],
        "阴谋揭露": ["novel", "technique", "case", "foreshadow_pair"],
        "情报揭示": ["novel", "technique", "case"],
        "转折": ["novel", "technique", "case", "foreshadow_pair"],
        "世界观展开": ["novel", "technique", "case"],
        "势力登场": ["novel", "technique", "case", "dialogue_style"],
        "反派出场": ["novel", "technique", "case", "dialogue_style"],
        "团队组建": ["novel", "technique", "case", "dialogue_style"],
        "修炼突破": ["novel", "technique", "case", "power_cost", "power_vocabulary"],
        "资源获取": ["novel", "technique", "case"],
        "探索发现": ["novel", "technique", "case"],
        "危机降临": ["novel", "technique", "case", "emotion_arc"],
        "冲突升级": ["novel", "technique", "case", "power_cost"],
        "恢复休养": ["novel", "technique", "case", "dialogue_style"],
    }
    
    sources = scene_sources.get(scene_type, ["novel", "technique", "case"])
    return {src: source_map[src] for src in sources}
```

### 检索流程

```
阶段2.5：经验检索
├── 读取：章节经验日志/前几章_log.json
├── 提取：what_worked / what_didnt_work / insights
└── 注入：作家创作上下文

阶段3：设定自动检索（智能选择Collection）
├── 场景类型识别（28种之一）
├── source_map映射 → 确定检索源
├── 多Collection并行检索
└── 结果融合注入
```

---

## 九、审核维度扩展（新增）

### 审核标准Collection

| Collection | 用途 | 特性 |
|------------|------|------|
| `evaluation_criteria_v1` | 动态审核标准 | 可按场景类型加载不同标准 |

### 审核维度配置

```json
{
  "evaluation_criteria_v1": {
    "通用维度": [
      "技法运用准确度",
      "约束遵守度",
      "角色行为一致性",
      "世界观设定一致性",
      "叙事流畅度",
      "情感张力",
      "节奏把控",
      "场景契约一致性",
      "语言风格",
      "主题表达",
      "伏笔质量",
      "读者体验",
      "创新度"
    ],
    "场景专用维度": {
      "战斗": ["战斗逻辑", "力量体系一致性", "代价描写"],
      "情感": ["情感层次", "共鸣度", "克制程度"],
      "悬念": ["紧张度", "节奏控制", "预期管理"],
      "打脸": ["爽点爆发", "节奏把控", "读者满足感"],
      "高潮": ["情感顶点", "多线汇聚", "节奏爆发"]
    }
  }
}
```

### Evaluator动态加载

```python
class Evaluator:
    """审核评估师（动态加载审核标准）"""
    
    def load_criteria(self, scene_type: str):
        """根据场景类型加载审核标准"""
        # 基础维度（13个）
        base_criteria = self._load_base_criteria()
        
        # 场景专用维度
        scene_specific = self._load_scene_criteria(scene_type)
        
        return base_criteria + scene_specific
    
    def evaluate(self, content: str, scene_type: str) -> dict:
        """评估内容"""
        criteria = self.load_criteria(scene_type)
        # 按维度评估...
```

**说明**：排除自动发现功能（用户明确不需要），审核标准通过对话管理配置。

---

## 十、关键文件

### 核心文件

| 文件 | 用途 |
|------|------|
| `config.json` | 项目配置 |
| `PROJECT_LOGIC.md` | 项目逻辑（本文档） |
| `scene_writer_mapping.json` | 场景类型→作家映射 |

### 创作数据

| 文件 | 用途 |
|------|------|
| `章节大纲/` | 章节大纲 |
| `正文/` | 输出正文 |
| `章节经验日志/` | 经验积累 |
| `评估报告/` | 评估结果 |

### 系统代码

| 文件 | 用途 |
|------|------|
| `.vectorstore/core/workflow.py` | 核心工作流 |
| `.vectorstore/core/technique_search.py` | 技法检索 |
| `tools/build_all.py` | 数据构建 |

---

## 十、推理规则

### 创作前

```
1. pm.search("场景关键词") 检索相关设定
2. pm.check_action("计划动作") 检查约束
3. 检索场景契约
4. 执行创作
5. pm.sync() 同步
```

### 遇到冲突

```
1. 检查约束级别（Hard > Soft）
2. 检查用户明确要求
3. 询问用户确认
```

### 不确定时

```
1. 检索 project-memory
2. 检查 PROJECT_LOGIC.md
3. 无结果 → 询问用户
```

---

## 十一、自动学习记录

> 以下内容由项目记忆系统自动学习并补充

### 设计决策

#### 使用角色成长曲线设计_因为需要体现角色的阶段性变化

- **决策**: 使用角色成长曲线设计，因为需要体现角色的阶段性变化
- **原因**: 用户指定

### 约束规则

（暂无）

