# 检索系统API手册

> 最后更新: 2026-04-11

## 快速开始

```python
from modules.knowledge_base.hybrid_search_manager import HybridSearchManager

search = HybridSearchManager()

# 技法检索
techniques = search.search_technique("战斗胜利有代价", dimension="战斗冲突维度", top_k=5)

# 案例检索
cases = search.search_case("突破场景", scene_type="战斗", top_k=5)

# 世界观元素检索
worldviews = search.search_worldview("宗门", element_type="组织", top_k=5)

# 力量词汇检索
powers = search.search_power_vocabulary("剑法", category="功法", top_k=10)

# 人物关系检索
relations = search.search_character_relation("师徒", character="师父", top_k=5)
```

---

## 检索源一览

| 检索源 | Collection | 数据量 | 主要用途 |
|--------|------------|--------|----------|
| 技法库 | writing_techniques_v2 | 986 | 创作技法参考 |
| 案例库 | case_library_v2 | 387,377 | 场景案例参考 |
| 设定库 | novel_settings_v2 | 160 | 小说设定检索 |
| 世界观元素 | worldview_element_v1 | 209,223 | 地点/组织/势力命名 |
| 力量词汇 | power_vocabulary_v1 | 87,165 | 境界/功法/物品词汇 |
| 人物关系 | character_relation_v1 | 198,500 | 人物共现关系 |
| 情感弧线 | emotion_arc_v1 | 2,087 | 情感曲线模板 |
| 对话风格 | dialogue_style_v1 | 405 | 势力对话特征 |
| 伏笔配对 | foreshadow_pair_v1 | 2,381 | 伏笔回收示例 |
| 力量代价 | power_cost_v1 | 140 | 力量代价表现 |
| 作者风格 | author_style_v1 | 2,803 | 作者风格指纹 |

---

## 核心API

### search_technique(query, dimension, top_k)

检索创作技法

```python
results = search.search_technique(
    query="战斗胜利有代价",
    dimension="战斗冲突维度",  # 可选过滤
    top_k=5,
    min_score=0.3,  # 最低相似度
    use_rerank=True,  # ColBERT重排
)

for r in results:
    print(f"技法: {r['name']}")
    print(f"维度: {r['dimension']}")
    print(f"作家: {r['writer']}")
    print(f"相似度: {r['score']:.4f}")
    print(f"内容: {r['content'][:200]}...")
```

**维度列表**:
- 世界观维度
- 剧情维度
- 人物维度
- 战斗冲突维度
- 氛围意境维度
- 叙事维度
- 主题维度
- 情感维度
- 读者体验维度
- 元维度
- 节奏维度

---

### search_case(query, scene_type, genre, top_k)

检索标杆案例

```python
results = search.search_case(
    query="突破场景",
    scene_type="战斗",  # 可选过滤
    genre="玄幻",  # 可选过滤
    top_k=5,
)

for r in results:
    print(f"小说: {r['novel_name']}")
    print(f"场景: {r['scene_type']}")
    print(f"题材: {r['genre']}")
    print(f"内容: {r['content'][:200]}...")
```

---

### search_worldview(query, element_type, top_k)

检索世界观元素

```python
results = search.search_worldview(
    query="宗门",
    element_type="组织",  # 可选过滤: 地点/组织/势力
    top_k=10,
)

for r in results:
    print(f"元素: {r['text']}")
    print(f"类型: {r['element_type']}")
    print(f"频次: {r['total_frequency']}")
```

---

### search_power_vocabulary(query, category, top_k)

检索力量词汇

```python
results = search.search_power_vocabulary(
    query="剑法",
    category="功法",  # 可选过滤: 境界/功法/物品
    top_k=10,
)

for r in results:
    print(f"词汇: {r['text']}")
    print(f"类别: {r['category']}")
    print(f"类型: {r['power_type']}")
```

---

### search_character_relation(query, character, top_k)

检索人物关系

```python
results = search.search_character_relation(
    query="师徒",
    character="师父",  # 可选过滤
    top_k=5,
)

for r in results:
    print(f"人物1: {r['character1']}")
    print(f"人物2: {r['character2']}")
    print(f"描述: {r['text']}")
```

---

### retrieve_for_scene(scene_type, context, top_k)

场景创作素材一键检索

根据场景类型自动选择合适的检索源，返回完整素材包：

```python
materials = search.retrieve_for_scene(
    scene_type="战斗",
    context="主角突破",
    top_k=3,
)

# 返回结构:
# {
#   "technique": [...技法],
#   "case": [...案例],
#   "power": [...力量词汇],
# }

for source, items in materials.items():
    print(f"[{source}] {len(items)}条:")
    for item in items:
        print(f"  - {item.get('name', item.get('text', ''))[:50]}")
```

**场景类型映射**:
- 战斗 → 技法+案例+力量词汇
- 开篇 → 技法+案例+世界观元素
- 情感 → 技法+案例
- 对话 → 技法+对话风格
- 悬念 → 技法+案例
- 转折 → 技法+案例
- 心理 → 技法+案例
- 环境 → 技法+世界观元素

---

## 检索配置

### 权重预设

```python
search.set_weight_preset("general")  # 通用场景（默认）
search.set_weight_preset("semantic")  # 偏语义场景
search.set_weight_preset("exact")  # 偏精确匹配
search.set_weight_preset("dense_only")  # 仅Dense（最快）
```

---

## 统计信息

```python
stats = search.get_stats()
for name, info in stats.items():
    print(f"{name}: {info['总数']}条")
```

---

## 命令行使用

```bash
# 技法检索
python -m modules.knowledge_base.hybrid_search_manager --query "战斗代价" --type technique --top-k 5

# 案例检索
python -m modules.knowledge_base.hybrid_search_manager --query "突破场景" --type case --top-k 5

# 统计信息
python -m modules.knowledge_base.hybrid_search_manager --stats
```

---

## 与作家Skills集成

作家可以在创作时直接调用检索API获取素材：

```python
# 剑尘 - 战斗设计师
def create_battle_scene(scene_context):
    search = HybridSearchManager()
    materials = search.retrieve_for_scene("战斗", context=scene_context, top_k=3)
    
    # 使用技法指导
    for tech in materials.get("technique", []):
        apply_technique(tech)
    
    # 参考案例
    for case in materials.get("case", []):
        reference_case(case)
    
    # 力量词汇增强描写
    for vocab in materials.get("power", []):
        use_power_vocabulary(vocab)
```

---

## 性能建议

| 场景 | 推荐配置 |
|------|----------|
| 快速检索 | `use_rerank=False` |
| 高质量检索 | `use_rerank=True` + `preset="general"` |
| 精确匹配 | `use_rerank=True` + `preset="exact"` |
| 批量查询 | 先Dense召回，批量处理 |

---

## 文件位置

```
D:/动画/众生界/
├── modules/knowledge_base/
│   └── hybrid_search_manager.py  # 主检索API
├── .vectorstore/
│   ├── hybrid_retriever.py       # 混合检索核心
│   ├── unified_retrieval_api.py  # 统一检索API
│   ├── retrieval_evaluation.py   # 评估测试
│   └── bge_m3_config.py          # 配置
└── .novel-extractor/
    └── sync_to_qdrant.py         # 入库脚本
    └── incremental_sync.py       # 增量同步
```