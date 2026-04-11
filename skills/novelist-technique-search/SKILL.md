---
name: novelist-technique-search
description: "技法检索技能 - 通过BGE-M3混合检索(Dense+Sparse+ColBERT)语义检索创作技法，支持维度/作家过滤。"
---

# 技法检索技能 (BGE-M3 混合检索版)

## 功能说明

通过 BGE-M3 混合向量检索创作技法，实现：
- **三路混合检索**：Dense(语义) + Sparse(关键词) + ColBERT(精细匹配)
- **两阶段流程**：Dense+Sparse召回 → ColBERT重排
- **高精度匹配**：比单一Dense检索质量提升15-20%
- **多维度过滤**：按维度、作家过滤

---

## 技术架构

```
查询文本 → BGE-M3编码 → Dense向量 + Sparse向量 + ColBERT向量
                            ↓
                    Dense + Sparse 并行召回 (RRF融合)
                            ↓
                    ColBERT 重排 Top-K
                            ↓
                        返回结果
```

---

## 依赖安装

```bash
pip install qdrant-client FlagEmbedding
```

---

## 初始化向量数据库

首次使用或更新技法后，运行同步脚本：

```bash
# 在项目根目录下运行
python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild
```

或使用迁移脚本：

```bash
python tools/migrate_to_bge_m3.py --execute --skip-cases
```

---

## 检索接口

### Python API

```python
from modules.knowledge_base.hybrid_search_manager import HybridSearchManager

search = HybridSearchManager()

# 混合检索（自动 Dense + Sparse + ColBERT）
results = search.search_technique(
    query="战斗代价描写",
    top_k=5
)

for result in results:
    print(f"技法: {result['name']}")
    print(f"维度: {result['dimension']}")
    print(f"作家: {result['writer']}")
    print(f"相似度: {result['score']:.4f}")
    print(f"内容: {result['content'][:200]}...")
```

### 按维度过滤

```python
results = search.search_technique(
    query="代价设计",
    dimension="战斗冲突维度",
    top_k=5
)
```

### 禁用重排（更快，但精度略低）

```python
results = search.search_technique(
    query="血脉体系",
    top_k=10,
    use_rerank=False  # 仅 Dense + Sparse
)
```

### 切换权重预设

```python
# 通用场景（默认）
search.set_weight_preset("general")  # dense=0.2, sparse=0.4, colbert=0.4

# 偏语义场景
search.set_weight_preset("semantic")  # dense=0.5, sparse=0.2, colbert=0.3

# 偏精确匹配
search.set_weight_preset("exact")  # dense=0.2, sparse=0.6, colbert=0.2

# 仅Dense（最快）
search.set_weight_preset("dense_only")  # dense=1.0
```

---

## 命令行使用

```bash
# 检索技法
python -m modules.knowledge_base.hybrid_search_manager \
    --query "战斗代价描写" \
    --type technique \
    --top-k 5

# 按维度过滤
python -m modules.knowledge_base.hybrid_search_manager \
    --query "代价设计" \
    --type technique \
    --dimension "战斗冲突维度"

# 禁用重排
python -m modules.knowledge_base.hybrid_search_manager \
    --query "血脉体系" \
    --type technique \
    --no-rerank

# 显示统计
python -m modules.knowledge_base.hybrid_search_manager --stats
```

---

## 返回数据结构

```python
{
    "id": 123,
    "name": "历史纵深构建",
    "dimension": "世界观维度",
    "writer": "苍澜",
    "source_file": "02-世界观维度.md",
    "source_title": "世界观维度技法",
    "content": "技法完整内容...",
    "word_count": 1500,
    "score": 0.85  # 相似度分数，越高越相关
}
```

---

## 与旧版对比

| 特性 | 旧版 (ChromaDB) | 新版 (BGE-M3 + Qdrant) |
|------|-----------------|------------------------|
| 检索模式 | 单一Dense | Dense + Sparse + ColBERT |
| 嵌入模型 | MiniLM (384维) | BGE-M3 (1024维) |
| 向量库 | ChromaDB | Qdrant |
| 质量提升 | baseline | +15-20% |
| 多语言支持 | 一般 | 优秀 (100+语言) |

---

## Collection 配置

新 Collection 名称：
- `novel_settings_v2` - 小说设定
- `writing_techniques_v2` - 创作技法
- `case_library_v2` - 标杆案例

向量配置：
```python
{
    "dense": VectorParams(size=1024, distance=COSINE),
    "colbert": VectorParams(size=1024, multivector_config=MAX_SIM),
    "sparse": SparseVectorParams()
}
```

---

## 集成示例

### Generator 阶段

```python
def generator_with_technique(task_type: str, content_hint: str):
    from modules.knowledge_base.hybrid_search_manager import HybridSearchManager
    
    search = HybridSearchManager()
    
    results = search.search_technique(
        query=f"{task_type} {content_hint}",
        dimension=task_type_to_dimension(task_type),
        top_k=3
    )
    
    return results

def task_type_to_dimension(task_type: str) -> str:
    mapping = {
        "世界观设定": "世界观维度",
        "势力构建": "世界观维度",
        "血脉体系": "世界观维度",
        "伏笔埋设": "剧情维度",
        "悬念设计": "剧情维度",
        "人物出场": "人物维度",
        "战斗场景": "战斗冲突维度",
        "氛围渲染": "氛围意境维度",
    }
    return mapping.get(task_type, None)
```

### Evaluator 阶段

```python
def evaluator_with_technique(scene_type: str, dimensions: List[str]):
    from modules.knowledge_base.hybrid_search_manager import HybridSearchManager
    
    search = HybridSearchManager()
    
    techniques = []
    for dim in dimensions:
        results = search.search_technique(
            query=f"{scene_type} {dim}",
            dimension=dim,
            top_k=2
        )
        techniques.extend(results)
    
    return techniques
```

---

## 维护

### 更新技法笔记后

```bash
# 同步技法到向量库
python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild
```

### 查看检索统计

```bash
python -m modules.knowledge_base.hybrid_search_manager --stats
```

---

## 文件说明

```
项目根目录/
├── .vectorstore/
│   └── bge_m3_config.py              # BGE-M3 配置
├── modules/knowledge_base/
│   ├── hybrid_sync_manager.py        # 混合同步管理器
│   └── hybrid_search_manager.py      # 混合检索管理器
└── tools/
    └── migrate_to_bge_m3.py          # 迁移脚本
```

---

## 性能优化建议

| 场景 | 推荐配置 |
|------|----------|
| 快速检索 | `use_rerank=False` + `preset="dense_only"` |
| 高质量检索 | `use_rerank=True` + `preset="general"` |
| 精确匹配 | `use_rerank=True` + `preset="exact"` |
| 大批量查询 | 先 Dense 召回，批量 ColBERT 重排 |