# 小说提炼系统使用指南

> **生成时间**: 2026-04-05
> **数据源**: E:\小说资源 (6,245本, 15.68GB)
> **输出目录**: D:\动画\众生界\.novel-extractor\

---

## 一、系统架构

```
┌─────────────────────────────────────────────────────────────┐
│              众生界 - 完整小说提炼系统 v2.0                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  E:\小说资源 (原始小说库)                                    │
│  ├── 6,245 本小说                                            │
│  ├── 15.68 GB 文本数据                                       │
│  └── 支持: txt / epub / mobi                                 │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              统一入口 run.py                          │   │
│  │  --status    查看系统状态                             │   │
│  │  --all       提炼所有维度                             │   │
│  │  --category  按类别提炼 (core/high/medium/low)        │   │
│  │  --dimension 提炼特定维度                             │   │
│  │  --sync      增量同步                                 │   │
│  │  --report    生成报告                                 │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│         ┌───────────────┼───────────────┐                   │
│         ▼               ▼               ▼                   │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐             │
│  │ 核心      │   │ 高价值    │   │ 中低价值  │             │
│  │ 场景案例  │   │ 扩展维度  │   │ 扩展维度  │             │
│  │ 256,083条 │   │ 3个维度   │   │ 6个维度   │             │
│  └─────┬─────┘   └─────┬─────┘   └─────┬─────┘             │
│        │               │               │                    │
│        └───────────────┼───────────────┘                    │
│                        ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              输出目录结构                             │   │
│  │  .case-library/cases/      # 核心场景案例             │   │
│  │  .novel-extractor/extracted/ # 扩展维度输出           │   │
│  │  ├── dialogue_style/    # 势力对话风格库             │   │
│  │  ├── power_cost/        # 力量体系代价库             │   │
│  │  ├── emotion_arc/       # 情感曲线模板               │   │
│  │  └── ...                                              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、提炼维度一览（10个维度）

### 核心维度 - 场景案例库

| 维度 | 说明 | 当前数量 |
|------|------|----------|
| **case** | 22种场景类型标杆案例 | **256,083条** |

**场景类型分布**:
| 场景 | 数量 | 场景 | 数量 |
|------|------|------|------|
| 打脸场景 | 147,846 | 高潮场景 | 103,070 |
| 开篇场景 | 2,437 | 对话场景 | 343 |
| 心理场景 | 343 | 人物出场 | 343 |
| 悬念场景 | 343 | 环境场景 | 343 |
| 情感场景 | 343 | 转折场景 | 340 |

### 高价值维度（直接用于创作）

| 维度 | 说明 | 状态 |
|------|------|------|
| **dialogue_style** | 势力对话风格库 - 10大势力对话特征 | ✅ 可用 |
| **power_cost** | 力量体系代价库 - 7大力量代价表现 | ✅ 可用 |
| **character_relation** | 人物关系图谱 - 人物共现关系网络 | ✅ 可用 |

### 中价值维度（需适配后使用）

| 维度 | 说明 | 状态 |
|------|------|------|
| **emotion_arc** | 情感曲线模板 - 6种叙事弧线 | ✅ 可用 |
| **power_vocabulary** | 力量体系词汇库 - 境界/功法/物品词汇 | ✅ 可用 |
| **chapter_structure** | 章节结构模式 - 章节节奏分析 | ✅ 可用 |

### 低价值维度（长期有益）

| 维度 | 说明 | 状态 |
|------|------|------|
| **author_style** | 作者风格指纹 - 风格特征向量 | ✅ 可用 |
| **foreshadow_pair** | 伏笔回收配对 - 伏笔配对示例 | ✅ 可用 |
| **worldview_element** | 世界观元素 - 地点/组织命名规律 | ✅ 可用 |

---

## 三、快速使用

### 1. 查看系统状态

```bash
cd D:\动画\众生界\.novel-extractor
python run.py --status
```

输出示例:
```
[系统状态]
------------------------------------------------------------
[核心]
  [OK] 场景案例库: 256,083 条

[高价值]
  [  ] 势力对话风格库: 0 条
  [  ] 力量体系代价库: 0 条
  ...

[场景案例库]
  打脸场景: 147846
  高潮场景: 103070
  开篇场景: 2437
  ...
```

### 2. 提炼所有维度

```bash
# 完整提炼
python run.py --all

# 测试模式（限制处理数量）
python run.py --all --limit 10
```

### 3. 按类别提炼

```bash
# 只提炼核心维度（场景案例）
python run.py --category core

# 只提炼高价值维度
python run.py --category high

# 只提炼中价值维度
python run.py --category medium

# 只提炼低价值维度
python run.py --category low
```

### 4. 提炼特定维度

```bash
# 只提取对话风格
python run.py --dimension dialogue_style

# 只提取力量代价
python run.py --dimension power_cost

# 只提取场景案例
python run.py --dimension case
```

### 5. 增量同步

```bash
# 扫描并同步新小说
python run.py --sync
```

### 6. 生成报告

```bash
python run.py --report
```

---

## 四、文件结构

```
众生界/
├── .case-library/                # 核心维度 - 场景案例库
│   ├── cases/                    # 256,083条案例
│   │   ├── 01-开篇场景/
│   │   ├── 03-战斗场景/
│   │   ├── 打脸场景/
│   │   └── ...
│   ├── unified_stats.json        # 统计数据
│   └── README.md                 # 案例库文档
│
├── .novel-extractor/             # 扩展维度提炼系统
│   ├── run.py                    # ⭐ 统一主入口
│   ├── unified_config.py         # 统一配置（10维度）
│   ├── config.py                 # 原配置
│   ├── incremental_sync.py       # 增量同步
│   │
│   ├── extractors/               # 提取器模块
│   │   ├── case_extractor.py     # 场景案例提取器
│   │   ├── dialogue_style_extractor.py
│   │   ├── power_cost_extractor.py
│   │   └── ...
│   │
│   ├── extracted/                # 提炼输出
│   │   ├── dialogue_style/
│   │   ├── power_cost/
│   │   ├── emotion_arc/
│   │   └── ...
│   │
│   ├── progress/                 # 进度追踪
│   │   └── *_progress.json
│   │
│   └── README.md                 # 本文档
│
└── .vectorstore/                 # 向量数据库
    └── qdrant/                   # 316,865向量点
```

---

## 五、核心维度：场景案例库

### 5.1 场景类型（22种）

| ID | 场景类型 | 数量 | 最佳来源 |
|----|----------|------|----------|
| 01 | 开篇场景 | 2,437 | 玄幻、科幻、悬疑 |
| 02 | 人物出场 | 343 | 玄幻、武侠、历史 |
| 03 | 战斗场景 | 332 | 玄幻、武侠、历史 |
| 04 | 对话场景 | 343 | 都市、言情、历史 |
| 05 | 情感场景 | 343 | 言情、校园、都市 |
| 06 | 悬念场景 | 343 | 悬疑、科幻、玄幻 |
| 07 | 转折场景 | 340 | 悬疑、玄幻、历史 |
| 08 | 结尾场景 | 0 | 玄幻、历史、言情 |
| 09 | 环境场景 | 343 | 玄幻、武侠、科幻 |
| 10 | 心理场景 | 343 | 都市、言情、校园 |
| - | 打脸场景 | 147,846 | 玄幻核心场景 |
| - | 高潮场景 | 103,070 | 玄幻核心场景 |

### 5.2 跨题材借鉴矩阵

| 来源题材 | 贡献场景 | 借鉴价值 |
|----------|----------|----------|
| **玄幻/仙侠** | 修炼突破、世界观构建、战斗 | 力量体系构建 |
| **历史军事** | 势力登场、权谋博弈、战争 | 史诗氛围，势力构建 |
| **悬疑推理** | 伏笔设置、悬念营造、反转 | 长线叙事张力 |
| **现代都市** | 对话技巧、情感细腻、心理 | 人物互动质量 |
| **女频言情** | 情感层次、心理描写 | 感情线处理 |

---

## 六、与创作系统集成

### 场景案例检索

```python
from extractors.case_extractor import CaseExtractor

extractor = CaseExtractor()

# 获取开篇场景案例
cases = extractor.extract_for_scene("开篇场景", top_k=5)
for case in cases:
    print(f"- {case['novel']} ({case['genre']})")
    print(f"  {case['content'][:200]}...")
```

### 对话风格使用

```python
import json
with open('.novel-extractor/extracted/dialogue_style/dialogue_style_all.json') as f:
    styles = json.load(f)

# 获取东方修仙对话特征
xiuxian_style = next(s for s in styles if s['faction'] == '东方修仙')
print(xiuxian_style['style_summary'])
# "常用称呼：道友、师尊、在下；语气倾向：坚定；风格：淡然"
```

---

## 七、扩展新维度

### 添加新提炼维度

1. 在 `unified_config.py` 的 `EXTRACTION_DIMENSIONS` 添加定义：

```python
"new_dimension": ExtractionDimension(
    id="new_dimension",
    name="新维度名称",
    description="维度说明",
    category=DimensionCategory.HIGH,  # core/high/medium/low
    extractor_module="extractors.new_dimension_extractor",
    extractor_class="NewDimensionExtractor",
)
```

2. 创建提取器 `extractors/new_dimension_extractor.py`：

```python
from base_extractor import BaseExtractor

class NewDimensionExtractor(BaseExtractor):
    def __init__(self):
        super().__init__("new_dimension")
    
    def extract_from_novel(self, content, novel_id, novel_path):
        # 实现提取逻辑
        return items
    
    def process_extracted(self, items):
        # 实现处理逻辑
        return processed_items
```

3. 在 `run.py` 的 `create_extractor()` 添加映射：

```python
"new_dimension": ("extractors.new_dimension_extractor", "NewDimensionExtractor"),
```

---

## 八、性能与资源

| 指标 | 数值 |
|------|------|
| 小说总量 | 6,245 本 |
| 总容量 | 15.68 GB |
| 支持格式 | txt / epub / mobi |
| **场景案例总数** | **256,083 条** |
| **向量数据库点数** | **316,865** |
| 提炼维度 | 10个 (1核心 + 3高 + 3中 + 3低) |
| 推荐配置 | 8GB+ 内存 |

---

## 九、常见问题

### Q: 如何查看提炼进度？
```bash
python run.py --status
```

### Q: 提炼中断了怎么办？
系统自动保存进度，再次运行会从中断处继续。

### Q: 如何重新提炼某个维度？
```bash
# 删除进度文件
rm progress/dialogue_style_progress.json

# 重新运行
python run.py --dimension dialogue_style
```

### Q: 如何只提炼新增的小说？
```bash
python run.py --sync
```

### Q: 场景案例库和扩展维度有什么区别？
- **场景案例库(核心)**: 已完成提取，256,083条案例，直接可用
- **扩展维度**: 需运行 `python run.py --all` 提炼

---

## 十、提炼内容与向量数据库映射关系

### 10.1 向量数据库 Collection 结构

```
┌─────────────────────────────────────────────────────────────┐
│              Qdrant 向量数据库 Collections                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  novel_settings_v2          # 小说设定                       │
│  ├── 196条实体（角色/势力/力量体系）                         │
│  ├── Dense + Sparse + ColBERT                               │
│  └── 来源: 众生界/设定/                                      │
│                                                              │
│  writing_techniques_v2      # 创作技法                       │
│  ├── 1,122条技法（11维度）                                   │
│  ├── Dense + Sparse + ColBERT                               │
│  └── 来源: 众生界/创作技法/                                  │
│                                                              │
│  case_library_v2            # 场景案例                       │
│  ├── 256,083条案例（22种场景）                               │
│  ├── Dense + Sparse                                         │
│  └── 来源: .case-library/cases/                              │
│                                                              │
│  总向量点: 316,865                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 提炼维度与数据库映射

| 提炼维度 | 数据库Collection | 数据来源 | 同步脚本 | 状态 |
|----------|------------------|----------|----------|------|
| **case** | case_library_v2 | .case-library/cases/ | migrate_lite_resumable.py --collection case | ✅ 已同步 |
| **technique** | writing_techniques_v2 | 众生界/创作技法/ | migrate_lite_resumable.py --collection technique | ⏳ 待提取 |
| **novel_settings** | novel_settings_v2 | 众生界/设定/ | migrate_lite_resumable.py --collection novel | ✅ 已同步 |
| dialogue_style | ❌ 不入向量库 | .novel-extractor/extracted/ | - | ✅ 已提取 |
| power_cost | ❌ 不入向量库 | .novel-extractor/extracted/ | - | ✅ 已提取 |
| emotion_arc | ❌ 不入向量库 | .novel-extractor/extracted/ | - | ✅ 已提取 |
| power_vocabulary | ❌ 不入向量库 | .novel-extractor/extracted/ | - | ✅ 已提取 |
| author_style | ❌ 不入向量库 | .novel-extractor/extracted/ | - | ✅ 已提取 |
| foreshadow_pair | ❌ 不入向量库 | .novel-extractor/extracted/ | - | ✅ 已提取 |

> **说明**: 扩展维度(dialogue_style等)目前不入向量库，存储为JSON文件供创作时直接调用。

### 10.3 各类内容提取后的数据库更新流程

#### 10.3.1 场景案例 (case)

**提取后更新**:
```bash
cd D:\动画\众生界
python tools/migrate_lite_resumable.py --collection case
```

**Collection**: `case_library_v2`

**数据格式**:
```json
{
  "id": "case_001",
  "vector": [...],
  "payload": {
    "scene_type": "打脸场景",
    "genre": "玄幻奇幻",
    "novel_name": "盘龙",
    "content": "...",
    "quality_score": 8.5
  }
}
```

#### 10.3.2 创作技法 (technique) ⏳ 待实现

**提取后更新**:
```bash
cd D:\动画\众生界
python tools/migrate_lite_resumable.py --collection technique
```

**Collection**: `writing_techniques_v2`

**数据格式**:
```json
{
  "id": "tech_001",
  "vector": [...],
  "payload": {
    "技法名称": "有代价胜利",
    "维度": "战斗冲突维度",
    "内容": "主角胜利必须付出代价...",
    "来源路径": "创作技法/04-战斗冲突维度/",
    "标签": ["战斗", "胜利", "代价"],
    "作家": "剑尘"
  }
}
```

#### 10.3.3 小说设定 (novel_settings)

**用户手动更新后同步**:
```bash
cd D:\动画\众生界
python tools/migrate_lite_resumable.py --collection novel
```

**Collection**: `novel_settings_v2`

**数据格式**:
```json
{
  "id": "entity_001",
  "vector": [...],
  "payload": {
    "name": "东方修仙",
    "type": "势力",
    "description": "修仙正道之首...",
    "relations": ["神殿/教会", "商盟"]
  }
}
```

### 10.4 向量数据库同步脚本一览

| 脚本 | 用途 | 推荐度 |
|------|------|--------|
| `tools/migrate_lite_resumable.py` | 轻量级，支持断点续传 | ⭐⭐⭐ 推荐 |
| `tools/migrate_bge_m3_live.py` | 完整迁移，Dense+Sparse | ⭐⭐ |
| `tools/migrate_resumable.py` | 旧版，支持ColBERT | ⭐ |

### 10.5 验证同步结果

```bash
# 查看所有collection状态
cd D:\动画\众生界
python -c "
from qdrant_client import QdrantClient
client = QdrantClient(path='.vectorstore/qdrant')

for name in ['novel_settings_v2', 'writing_techniques_v2', 'case_library_v2']:
    try:
        info = client.get_collection(name)
        print(f'{name}: {info.points_count} 条')
    except:
        print(f'{name}: 不存在')
"
```

---

## 十一、未完成部分：技法精炼提取

### 11.1 功能概述

从 `E:\小说资源` (6,245本小说) 中精炼提取创作技法，合并到现有技法库 `众生界/创作技法/`。

### 11.2 当前技法库状态

| 来源 | 数量 | 位置 |
|------|------|------|
| 用户提供的技法 | ~904条 | `众生界/创作技法/` |
| 从原始小说提取 | ❌ **未实现** | - |

### 11.3 实现方案（待开发）

```
┌─────────────────────────────────────────────────────────────┐
│                    技法精炼提取流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  E:\小说资源 (6,245本小说)                                  │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  技法提取器 (technique_extractor.py)                 │   │
│  │                                                      │   │
│  │  方法1: 从案例库反推技法                             │   │
│  │  - 分析256,083条案例的共性模式                       │   │
│  │  - 提炼可复用的写作技法                              │   │
│  │  - 标注技法适用场景                                  │   │
│  │                                                      │   │
│  │  方法2: 从高质量小说直接提取                         │   │
│  │  - 分析经典小说的写作手法                            │   │
│  │  - 提取叙事、人物、战斗等维度技法                    │   │
│  │  - 标注来源作品和章节                                │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  合并去重                                            │   │
│  │  - 与现有904条技法对比                               │   │
│  │  - 去除重复                                          │   │
│  │  - 合并相似技法                                      │   │
│  │  - 补充技法案例                                      │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  输出                                                │   │
│  │  ├── 众生界/创作技法/99-从小说提取/*.md              │   │
│  │  └── 向量数据库同步 (见 10.3.2)                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 11.4 开发任务清单

```
[ ] 创建 technique_extractor.py
    [ ] 实现 TechniqueExtractor 类
    [ ] 方法1: 从案例库反推技法
    [ ] 方法2: 从原始小说提取技法
    [ ] 实现与现有技法库的合并去重

[ ] 集成到统一入口
    [ ] 在 unified_config.py 添加 technique 维度
    [ ] 在 run.py 添加映射

[ ] 同步到向量数据库
    [ ] 运行 python tools/migrate_lite_resumable.py --collection technique
    [ ] 验证 writing_techniques_v2 collection

[ ] 测试验证
    [ ] 提取测试（少量小说）
    [ ] 合并测试
    [ ] 向量同步测试
```

---

**文档版本**: 2.2
**最后更新**: 2026-04-05
**整合状态**: ✅ 核心维度 + 扩展维度已整合到统一入口 `run.py`
**向量数据库**: ✅ 3个Collection，316,865向量点
**待完成**: ⏳ 技法精炼提取（见第十一章）