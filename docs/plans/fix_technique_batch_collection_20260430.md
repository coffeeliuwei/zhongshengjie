# 计划：批量技法独立 Collection（writing_techniques_batch_v1）

> **日期**：2026-04-30（Asia/Shanghai）
> **背景**：`writing_techniques_v2` 是 auto-ingest 持续写入的活数据（986条，持续增长），
> `technique_all.json`（138,968条）是一次性历史批量。两者不能共用同一 collection，
> 否则 `sync_technique_json --rebuild` 会清空用户亲自核验的 986 条。
> **方案**：为批量数据新建独立 `writing_techniques_batch_v1`；
> `search_technique()` 同时查两个 collection，合并结果对上层完全透明。
> **协议**：遵循 `docs/opencode_dev_protocol_20260420.md` v1，只在 master 分支操作。

---

## 涉及文件

| 文件 | 操作 |
|------|------|
| `.vectorstore/bge_m3_config.py` | 新增 `writing_techniques_batch` 键 |
| `modules/knowledge_base/hybrid_sync_manager.py` | `sync_technique_json()` 改用新 collection |
| `modules/knowledge_base/hybrid_search_manager.py` | `search_technique()` 双 collection 合并 |
| `tests/test_technique_json_sync.py` | 更新测试：验证新 collection 名 + 双查合并 |

---

## Task 1：bge_m3_config.py 新增 collection 键

**文件**：`.vectorstore/bge_m3_config.py`

**定位**：`COLLECTION_NAMES` 字典，当前第 43-58 行，内容如下（只展示相关行）：

```python
COLLECTION_NAMES = {
    "novel_settings": "novel_settings_v2",
    "writing_techniques": "writing_techniques_v2",   # 第 45 行
    "case_library": "case_library_v2",
    # ... 其余键 ...
    "evaluation_criteria": "evaluation_criteria_v1",
}
```

**修改**：在 `"writing_techniques": "writing_techniques_v2"` 后面，紧接着新增一行：

```python
    "writing_techniques_batch": "writing_techniques_batch_v1",  # 批量提炼技法（一次性历史数据）
```

**修改后该段落**：

```python
COLLECTION_NAMES = {
    "novel_settings": "novel_settings_v2",
    "writing_techniques": "writing_techniques_v2",
    "writing_techniques_batch": "writing_techniques_batch_v1",  # 批量提炼技法（一次性历史数据）
    "case_library": "case_library_v2",
    # ... 其余键保持不变 ...
    "evaluation_criteria": "evaluation_criteria_v1",
}
```

**验证**（Task 1 完成后立即运行）：

```bash
cd D:\动画\众生界
python -c "
import sys; sys.path.insert(0, '.vectorstore')
from bge_m3_config import COLLECTION_NAMES
assert 'writing_techniques_batch' in COLLECTION_NAMES, '键不存在'
assert COLLECTION_NAMES['writing_techniques_batch'] == 'writing_techniques_batch_v1', '值错误'
assert COLLECTION_NAMES['writing_techniques'] == 'writing_techniques_v2', 'v2 不得修改'
print('Task 1 验证通过')
"
```

---

## Task 2：sync_technique_json() 改用 writing_techniques_batch_v1

**文件**：`modules/knowledge_base/hybrid_sync_manager.py`

**定位**：`sync_technique_json()` 方法内，第 679 行（以当前代码为准，搜索如下字符串定位）：

```python
        collection_name = COLLECTION_NAMES["writing_techniques"]
```

该行出现在 `# 创建 Collection（重建）` 注释下方。

**修改**：将该行改为：

```python
        collection_name = COLLECTION_NAMES["writing_techniques_batch"]
```

**注意**：
- 此行是 `sync_technique_json()` 方法内的 **局部变量赋值**，只改这一处。
- `sync_techniques()` 方法（同文件另一处）中的 `COLLECTION_NAMES["writing_techniques"]` **不得修改**，那是 auto-ingest MD 文件的 sync，必须继续写 `writing_techniques_v2`。
- 搜索时注意区分：`sync_technique_json` 方法体从第 623 行开始，`sync_techniques` 方法体从更早开始。

**验证**（Task 2 完成后立即运行）：

```bash
cd D:\动画\众生界
python -c "
import sys; sys.path.insert(0, '.vectorstore')
import ast, pathlib
src = pathlib.Path('modules/knowledge_base/hybrid_sync_manager.py').read_text(encoding='utf-8')
# 找到 sync_technique_json 函数体
fn_start = src.index('def sync_technique_json(')
fn_body = src[fn_start:fn_start+3000]
assert 'writing_techniques_batch' in fn_body, 'sync_technique_json 未改用 batch collection'
assert fn_body.count('writing_techniques_batch') >= 1, '改动不足'
# 确认 sync_techniques 方法没被动到
idx_sync_tech = src.index('def sync_techniques(')
fn_sync_tech = src[idx_sync_tech:idx_sync_tech+2000]
assert 'writing_techniques_batch' not in fn_sync_tech, 'sync_techniques 不应引用 batch collection'
print('Task 2 验证通过')
"
```

---

## Task 3：search_technique() 双 collection 合并查询

**文件**：`modules/knowledge_base/hybrid_search_manager.py`

**定位**：`search_technique()` 方法，第 344-446 行（搜索 `def search_technique(` 定位）。

当前代码结构（伪代码，关键节点）：

```python
def search_technique(self, query, dimension=None, top_k=10, min_score=0.3, use_rerank=True):
    client = self._get_client()
    collection_name = COLLECTION_NAMES["writing_techniques"]   # 只查 v2

    collections = [c.name for c in client.get_collections().collections]
    if collection_name not in collections:
        return []

    query_vectors = self._encode_query(query)
    # ... 构建 query_filter ...
    # ... 阶段1: Dense + Sparse 混合召回 ...
    results = client.query_points(collection_name=collection_name, ...)

    # 阶段2: ColBERT 重排
    if use_rerank and ...:
        results = self._colbert_rerank(client, collection_name, ...)
    else:
        results = results.points[:top_k]

    # 格式化结果
    formatted = []
    for p in results:
        if p.score < min_score: continue
        formatted.append({"id": ..., "name": ..., ...})
    return formatted
```

**新实现**（完整替换 `search_technique` 方法体，从 `def search_technique(` 到方法末尾 `return formatted`）：

```python
    def search_technique(
        self,
        query: str,
        dimension: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        混合检索创作技法，同时查 writing_techniques_v2（auto-ingest活数据）
        和 writing_techniques_batch_v1（批量历史数据），合并后按 score 降序返回 top_k。
        """
        client = self._get_client()
        existing_collections = {c.name for c in client.get_collections().collections}

        collection_names = []
        for key in ("writing_techniques", "writing_techniques_batch"):
            name = COLLECTION_NAMES.get(key)
            if name and name in existing_collections:
                collection_names.append(name)

        if not collection_names:
            print("writing_techniques_v2 / writing_techniques_batch_v1 均不存在，请先运行同步")
            return []

        query_vectors = self._encode_query(query)

        query_filter = None
        if dimension:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="dimension",
                        match=models.MatchValue(value=dimension),
                    )
                ]
            )

        all_points = []
        for collection_name in collection_names:
            try:
                sparse_vector = SparseVector(
                    indices=query_vectors["sparse_indices"],
                    values=query_vectors["sparse_values"],
                )
                results = client.query_points(
                    collection_name=collection_name,
                    prefetch=[
                        models.Prefetch(
                            query=query_vectors["dense"],
                            using="dense",
                            limit=self.recall_config["dense_limit"],
                            filter=query_filter,
                        ),
                        models.Prefetch(
                            query=sparse_vector,
                            using="sparse",
                            limit=self.recall_config["sparse_limit"],
                            filter=query_filter,
                        ),
                    ],
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    limit=self.recall_config["fusion_limit"],
                    with_payload=True,
                )
                if use_rerank and self.rerank_config["enabled"] and len(results.points) > 0:
                    reranked = self._colbert_rerank(
                        client, collection_name, query_vectors["colbert"], results.points, top_k
                    )
                    all_points.extend(reranked)
                else:
                    all_points.extend(results.points[:top_k])
            except Exception as e:
                print(f"检索 {collection_name} 错误: {e}")

        # 按 score 降序，取 top_k
        all_points.sort(key=lambda p: p.score, reverse=True)
        top_points = all_points[:top_k]

        formatted = []
        for p in top_points:
            if p.score < min_score:
                continue
            formatted.append(
                {
                    "id": p.id,
                    "name": p.payload.get("name", "未知"),
                    "dimension": p.payload.get("dimension", "未知"),
                    "writer": p.payload.get("writer", "未知"),
                    "source_file": p.payload.get("source_file", ""),
                    "content": p.payload.get("content", ""),
                    "word_count": p.payload.get("word_count", 0),
                    "score": p.score,
                }
            )
        return formatted
```

**关键约束**：
- `COLLECTION_NAMES.get(key)` 使用 `.get()` 而非 `[]`，防止 `writing_techniques_batch` 键不存在时报错。
- 某个 collection 不存在时静默跳过（只用另一个），不报错不崩溃。
- 两个 collection 各自做一次完整的 Dense+Sparse+ColBERT 检索，然后合并排序——不是把所有点扔进同一个 ColBERT rerank，避免 collection 间 id 冲突。
- 最终排序用 `p.score`，两个 collection 的 score 尺度相同（都是 BGE-M3 RRF + ColBERT），可直接比较。

**验证**（Task 3 完成后立即运行）：

```bash
cd D:\动画\众生界
python -c "
import sys, pathlib
src = pathlib.Path('modules/knowledge_base/hybrid_search_manager.py').read_text(encoding='utf-8')
fn_start = src.index('def search_technique(')
fn_end = src.index('\n    def ', fn_start + 10)
fn_body = src[fn_start:fn_end]
assert 'writing_techniques_batch' in fn_body, 'search_technique 未引用 batch collection'
assert 'collection_names' in fn_body, '未实现双 collection 循环'
assert 'all_points' in fn_body, '未实现结果合并'
assert 'all_points.sort' in fn_body, '未实现按 score 排序'
print('Task 3 验证通过')
"
```

---

## Task 4：更新测试文件

**文件**：`tests/test_technique_json_sync.py`

### 4.1 修改 TestSyncTechniqueJsonExists.test_method_exists

原测试只验证方法存在，现在还需验证方法使用新 collection key：

找到以下测试（约第 66-75 行）：

```python
class TestSyncTechniqueJsonExists:
    def test_method_exists(self):
        """HybridSyncManager 应有 sync_technique_json 方法"""
        from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager
        assert hasattr(HybridSyncManager, "sync_technique_json"), \
            "HybridSyncManager 缺少 sync_technique_json 方法"
```

**替换为**：

```python
class TestSyncTechniqueJsonExists:
    def test_method_exists(self):
        """HybridSyncManager 应有 sync_technique_json 方法"""
        from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager
        assert hasattr(HybridSyncManager, "sync_technique_json"), \
            "HybridSyncManager 缺少 sync_technique_json 方法"

    def test_uses_batch_collection_not_v2(self):
        """sync_technique_json 必须写入 writing_techniques_batch_v1，不得动 v2"""
        import pathlib
        src = pathlib.Path("modules/knowledge_base/hybrid_sync_manager.py").read_text(encoding="utf-8")
        fn_start = src.index("def sync_technique_json(")
        fn_body = src[fn_start: fn_start + 3000]
        assert "writing_techniques_batch" in fn_body, \
            "sync_technique_json 未使用 writing_techniques_batch collection"
        # 方法体内不应出现直接写死 writing_techniques_v2 的字符串
        assert '"writing_techniques_v2"' not in fn_body, \
            "sync_technique_json 不得硬编码 writing_techniques_v2"
```

### 4.2 新增 TestSearchTechniqueMultiCollection 测试类

在文件末尾（`TestCliTechniqueJson` 之后）新增：

```python
# ==================== 双 collection 合并检索 ====================


class TestSearchTechniqueMultiCollection:
    """验证 search_technique() 同时查两个 collection 并合并结果"""

    def test_search_technique_queries_both_collections(self):
        """当两个 collection 都存在时，两个都应被查询"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from unittest.mock import MagicMock, patch
        from modules.knowledge_base.hybrid_search_manager import HybridSearchManager

        mgr = HybridSearchManager.__new__(HybridSearchManager)
        mgr.recall_config = {"dense_limit": 50, "sparse_limit": 50, "fusion_limit": 20}
        mgr.rerank_config = {"enabled": False}

        # mock _get_client：两个 collection 都存在
        mock_client = MagicMock()
        mock_client.get_collections.return_value.collections = [
            MagicMock(name="writing_techniques_v2"),
            MagicMock(name="writing_techniques_batch_v1"),
        ]
        # 每次 query_points 返回 2 个点
        def fake_query(collection_name, **kwargs):
            r = MagicMock()
            p1 = MagicMock(); p1.score = 0.9; p1.id = hash(collection_name + "1")
            p1.payload = {"name": f"tech_{collection_name}_1", "dimension": "剧情维度",
                          "writer": "玄一", "source_file": "", "content": "测试内容", "word_count": 10}
            p2 = MagicMock(); p2.score = 0.7; p2.id = hash(collection_name + "2")
            p2.payload = {"name": f"tech_{collection_name}_2", "dimension": "剧情维度",
                          "writer": "玄一", "source_file": "", "content": "测试内容2", "word_count": 10}
            r.points = [p1, p2]
            return r
        mock_client.query_points.side_effect = fake_query
        mgr._get_client = MagicMock(return_value=mock_client)
        mgr._encode_query = MagicMock(return_value={
            "dense": [0.0] * 1024,
            "sparse_indices": [0], "sparse_values": [0.1],
            "colbert": [[0.0] * 128],
        })

        results = mgr.search_technique("测试查询", top_k=10, use_rerank=False)
        # 两个 collection 各 2 条，应返回 4 条（top_k=10）
        assert len(results) == 4, f"期望4条，实际{len(results)}条"
        # query_points 应被调用两次（各查一个 collection）
        assert mock_client.query_points.call_count == 2, \
            f"期望查询2次，实际{mock_client.query_points.call_count}次"

    def test_search_technique_only_v2_if_batch_missing(self):
        """当 batch collection 不存在时，只查 v2，不报错"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from unittest.mock import MagicMock
        from modules.knowledge_base.hybrid_search_manager import HybridSearchManager

        mgr = HybridSearchManager.__new__(HybridSearchManager)
        mgr.recall_config = {"dense_limit": 50, "sparse_limit": 50, "fusion_limit": 20}
        mgr.rerank_config = {"enabled": False}

        mock_client = MagicMock()
        # 只有 v2，没有 batch
        mock_client.get_collections.return_value.collections = [
            MagicMock(name="writing_techniques_v2"),
        ]
        r = MagicMock()
        p = MagicMock(); p.score = 0.8; p.id = 1
        p.payload = {"name": "tech1", "dimension": "剧情维度", "writer": "玄一",
                     "source_file": "", "content": "内容", "word_count": 5}
        r.points = [p]
        mock_client.query_points.return_value = r
        mgr._get_client = MagicMock(return_value=mock_client)
        mgr._encode_query = MagicMock(return_value={
            "dense": [0.0] * 1024,
            "sparse_indices": [0], "sparse_values": [0.1],
            "colbert": [[0.0] * 128],
        })

        results = mgr.search_technique("测试", top_k=5, use_rerank=False)
        assert len(results) == 1
        assert mock_client.query_points.call_count == 1, "只有 v2 存在时只应查询1次"

    def test_results_sorted_by_score_descending(self):
        """合并结果必须按 score 降序排列"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from unittest.mock import MagicMock
        from modules.knowledge_base.hybrid_search_manager import HybridSearchManager

        mgr = HybridSearchManager.__new__(HybridSearchManager)
        mgr.recall_config = {"dense_limit": 50, "sparse_limit": 50, "fusion_limit": 20}
        mgr.rerank_config = {"enabled": False}

        mock_client = MagicMock()
        mock_client.get_collections.return_value.collections = [
            MagicMock(name="writing_techniques_v2"),
            MagicMock(name="writing_techniques_batch_v1"),
        ]
        scores_by_collection = {
            "writing_techniques_v2": [0.6, 0.4],
            "writing_techniques_batch_v1": [0.9, 0.5],
        }
        call_count = [0]
        def fake_query(collection_name, **kwargs):
            r = MagicMock()
            points = []
            for i, sc in enumerate(scores_by_collection.get(collection_name, [])):
                p = MagicMock(); p.score = sc; p.id = call_count[0] * 10 + i
                p.payload = {"name": f"t{i}", "dimension": "剧情维度", "writer": "玄一",
                             "source_file": "", "content": "x", "word_count": 1}
                points.append(p)
                call_count[0] += 1
            r.points = points
            return r
        mock_client.query_points.side_effect = fake_query
        mgr._get_client = MagicMock(return_value=mock_client)
        mgr._encode_query = MagicMock(return_value={
            "dense": [0.0] * 1024,
            "sparse_indices": [0], "sparse_values": [0.1],
            "colbert": [[0.0] * 128],
        })

        results = mgr.search_technique("测试", min_score=0.0, top_k=10, use_rerank=False)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), f"结果未按score降序：{scores}"
        assert scores[0] == 0.9, f"最高分应为0.9，实际{scores[0]}"
```

**验证**（Task 4 完成后立即运行）：

```bash
cd D:\动画\众生界
python -m pytest tests/test_technique_json_sync.py -v 2>&1 | tail -20
```

---

## 最终验证（全部 Task 完成后）

```bash
cd D:\动画\众生界
python -m pytest tests/test_technique_json_sync.py tests/test_ingest_sync_pipeline.py tests/test_unified_retrieval.py tests/test_search_manager.py -v 2>&1 | tee logs/opencode_batch_collection_$(date +%Y%m%d_%H%M%S).log
```

期望：**全部通过，无回归**。

---

## 实施后执行同步

测试全绿后，跑实际 sync（不在测试中跑，需要真实 BGE-M3 模型和 Qdrant）：

```bash
python modules/knowledge_base/hybrid_sync_manager.py \
  --sync technique-json \
  --json-path "E:/novel_extracted/technique/technique_all.json" \
  --rebuild
```

预期：写入 `writing_techniques_batch_v1`，`writing_techniques_v2` 不受影响（仍 986 条）。
