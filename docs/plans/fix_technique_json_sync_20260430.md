# 计划：technique_all.json 直接同步到 writing_techniques_v2
# 日期：2026-04-30（Asia/Shanghai）
# 协议：docs/opencode_dev_protocol_20260420.md v1
# 执行者：opencode(GLM5)

---

## 背景

`E:/novel_extracted/technique/technique_all.json` 有 138,968 条批量提炼技法，
字段结构（已确认）：
```
technique_name, dimension, description, keywords,
example_count, examples, source_novels, occurrence_count, _novel_id
```

关键点：**`dimension` 字段已由 `unified_extractor` 正确填写**（如 `"战斗冲突维度"`），
无需通过目录结构推断。

现有问题：`sync_extracted_to_qdrant.py` 故意跳过 `technique` 维度（见架构文档 §9），
这 138,968 条数据永远进不了 `writing_techniques_v2`。

本计划在 `hybrid_sync_manager.py` 新增 `sync_technique_json()` 方法，
直接读 JSON → BGE-M3 编码 → 写入 `writing_techniques_v2`，复用所有已有基础设施。

---

## 总览

| 任务 | 文件 | 改动说明 |
|------|------|---------|
| 任务一 | `modules/knowledge_base/hybrid_sync_manager.py` | 新增 `sync_technique_json()` 方法（619行后插入） |
| 任务二 | `modules/knowledge_base/hybrid_sync_manager.py` | CLI 新增 `--json-path` 参数 + `technique-json` 选项（705行后修改） |
| 任务三 | `tests/test_technique_json_sync.py` | 新建测试文件 |

---

## 任务一：新增 sync_technique_json() 方法

### 插入位置

打开 `modules/knowledge_base/hybrid_sync_manager.py`，找到第 **619 行**：
```python
        print(f"  ✅ 已同步 {total_synced} 条案例")
        return total_synced
```

在第 619 行末尾（`return total_synced` 之后）和第 620 行（`def _upload_points`）之间，
**插入以下完整方法**（缩进4个空格，与类中其他方法一致）：

```python

    def sync_technique_json(
        self,
        json_path: Optional[str] = None,
        rebuild: bool = True,
    ) -> int:
        """
        直接从 technique_all.json 同步 138,968 条批量提炼技法到 writing_techniques_v2。

        JSON 字段：technique_name, dimension, description, keywords,
                   example_count, examples, source_novels, _novel_id

        Args:
            json_path: technique_all.json 路径，None 时从 config.json 自动推断
            rebuild:   是否重建 Collection（默认 True）
        """
        print("\n" + "=" * 60)
        print("[同步批量技法 JSON] BGE-M3 混合检索模式")
        print("=" * 60)

        # 解析 JSON 路径
        if json_path is None:
            try:
                cfg_file = Path(get_project_root()) / "config.json"
                with open(cfg_file, "r", encoding="utf-8") as _f:
                    _cfg = json.load(_f)
                output_dir = _cfg.get("extractor", {}).get("output_dir", "E:/novel_extracted")
            except Exception:
                output_dir = "E:/novel_extracted"
            resolved_path = Path(output_dir) / "technique" / "technique_all.json"
        else:
            resolved_path = Path(json_path)

        if not resolved_path.exists():
            print(f"  [错误] 文件不存在: {resolved_path}")
            return 0

        # 读取 JSON
        print(f"  读取: {resolved_path}")
        with open(resolved_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        print(f"  原始条数: {len(raw_data):,}")

        # 过滤：description 不为空，长度 >= 20
        valid_data = [
            t for t in raw_data
            if t.get("description") and len(t.get("description", "")) >= 20
        ]
        print(f"  有效条数（description >= 20字）: {len(valid_data):,}")

        if not valid_data:
            return 0

        # 创建 Collection（重建）
        collection_name = COLLECTION_NAMES["writing_techniques"]
        if rebuild:
            client = self._get_client()
            existing = [c.name for c in client.get_collections().collections]
            if collection_name in existing:
                client.delete_collection(collection_name)
                print(f"  [删除] 旧 collection: {collection_name}")
        if not self._create_hybrid_collection(collection_name):
            return 0

        # 分批处理（138k 条，每批 1000）
        batch_size = 1000
        total_synced = 0

        for batch_start in range(0, len(valid_data), batch_size):
            batch = valid_data[batch_start: batch_start + batch_size]

            # 组合嵌入文本：技法名 + 描述 + 第一条示例（截断）
            texts = []
            for t in batch:
                parts = [t["technique_name"]]
                if t.get("description"):
                    parts.append(t["description"])
                if t.get("examples") and t["examples"]:
                    parts.append("示例：" + str(t["examples"][0])[:300])
                texts.append("\n".join(parts)[:500])

            batch_num = batch_start // batch_size + 1
            total_batches = (len(valid_data) + batch_size - 1) // batch_size
            print(f"\n  批次 {batch_num}/{total_batches}（{len(texts)} 条）")

            embeddings = self._encode_batch(texts)

            # 构建 Points（payload 与 sync_techniques 保持一致）
            points = []
            for i, tech in enumerate(batch):
                idx = batch_start + i
                dense_vec = embeddings["dense_vecs"][i].tolist()
                sparse_dict = embeddings["lexical_weights"][i]
                colbert_vecs = embeddings["colbert_vecs"][i]

                sparse_indices = list(sparse_dict.keys())
                sparse_values = list(sparse_dict.values())

                if isinstance(colbert_vecs, list):
                    colbert_list = [
                        v.tolist() if hasattr(v, "tolist") else v
                        for v in colbert_vecs
                    ]
                else:
                    colbert_list = (
                        colbert_vecs.tolist()
                        if hasattr(colbert_vecs, "tolist")
                        else colbert_vecs
                    )

                dimension = tech.get("dimension", "未知")
                writer = self.WRITER_MAP.get(dimension, "未知")
                source_novels = tech.get("source_novels", [])
                source_file = source_novels[0] if source_novels else tech.get("_novel_id", "")
                full_content = texts[i]

                point = PointStruct(
                    id=idx,
                    vector={
                        "dense": dense_vec,
                        "colbert": colbert_list,
                        "sparse": SparseVector(
                            indices=sparse_indices, values=sparse_values
                        ),
                    },
                    payload={
                        "name": tech["technique_name"],
                        "dimension": dimension,
                        "writer": writer,
                        "source_file": str(source_file),
                        "source_title": tech["technique_name"],
                        "content": full_content,
                        "word_count": len(full_content),
                        "keywords": tech.get("keywords", []),
                        "occurrence_count": tech.get("occurrence_count", 0),
                    },
                )
                points.append(point)

            self._upload_points(collection_name, points)
            total_synced += len(points)

        print(f"\n  ✅ 已同步 {total_synced:,} 条批量提炼技法")
        return total_synced

```

---

## 任务二：修改 CLI 入口（第 705 行起）

### 当前代码（第 705-729 行）：

```python
# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BGE-M3 混合同步管理器")
    parser.add_argument(
        "--sync",
        choices=["novel", "technique", "case", "all"],
        default="all",
        help="同步目标",
    )
    parser.add_argument("--rebuild", action="store_true", help="重建 Collection")

    args = parser.parse_args()

    sync = HybridSyncManager()

    if args.sync == "all":
        sync.sync_all(rebuild=args.rebuild)
    elif args.sync == "novel":
        sync.sync_novel_settings(rebuild=args.rebuild)
    elif args.sync == "technique":
        sync.sync_techniques(rebuild=args.rebuild)
    elif args.sync == "case":
        sync.sync_cases(rebuild=args.rebuild)
```

### 替换为（完整替换第 705-729 行）：

```python
# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BGE-M3 混合同步管理器")
    parser.add_argument(
        "--sync",
        choices=["novel", "technique", "case", "all", "technique-json"],
        default="all",
        help="同步目标（technique-json: 直接从 technique_all.json 同步）",
    )
    parser.add_argument("--rebuild", action="store_true", help="重建 Collection")
    parser.add_argument(
        "--json-path",
        default=None,
        help="technique_all.json 路径（仅 --sync technique-json 时使用，默认从 config.json 自动推断）",
    )

    args = parser.parse_args()

    sync = HybridSyncManager()

    if args.sync == "all":
        sync.sync_all(rebuild=args.rebuild)
    elif args.sync == "novel":
        sync.sync_novel_settings(rebuild=args.rebuild)
    elif args.sync == "technique":
        sync.sync_techniques(rebuild=args.rebuild)
    elif args.sync == "case":
        sync.sync_cases(rebuild=args.rebuild)
    elif args.sync == "technique-json":
        sync.sync_technique_json(json_path=args.json_path, rebuild=args.rebuild)
```

---

## 任务三：新建测试文件 tests/test_technique_json_sync.py

直接创建新文件，完整内容如下：

```python
"""
测试 sync_technique_json()：从 technique_all.json 直接同步到 writing_techniques_v2
"""
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest


@pytest.fixture
def mock_manager():
    """创建带 mock Qdrant 客户端的 HybridSyncManager"""
    from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager

    mgr = HybridSyncManager.__new__(HybridSyncManager)
    mgr.WRITER_MAP = {
        "世界观维度": "苍澜",
        "剧情维度": "玄一",
        "人物维度": "墨言",
        "战斗冲突维度": "剑尘",
        "氛围意境维度": "云溪",
    }

    # mock _get_client
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []
    mgr._get_client = MagicMock(return_value=mock_client)

    # mock _create_hybrid_collection
    mgr._create_hybrid_collection = MagicMock(return_value=True)

    # mock _encode_batch：返回假向量
    def fake_encode(texts):
        n = len(texts)
        import numpy as np
        return {
            "dense_vecs": [np.zeros(1024) for _ in range(n)],
            "lexical_weights": [{0: 0.1, 1: 0.2} for _ in range(n)],
            "colbert_vecs": [np.zeros((10, 128)) for _ in range(n)],
        }
    mgr._encode_batch = fake_encode

    # mock _upload_points
    mgr._upload_points = MagicMock()

    return mgr


def _make_json_file(tmpdir, entries):
    """在临时目录写入 technique_all.json，返回路径"""
    p = Path(tmpdir) / "technique_all.json"
    p.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return str(p)


class TestSyncTechniqueJsonExists:
    def test_method_exists(self):
        """HybridSyncManager 应有 sync_technique_json 方法"""
        from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager
        assert hasattr(HybridSyncManager, "sync_technique_json"), \
            "缺失方法 sync_technique_json"


class TestSyncTechniqueJsonBasic:

    def test_returns_zero_when_file_missing(self, mock_manager):
        """文件不存在时返回 0，不报错"""
        result = mock_manager.sync_technique_json(
            json_path="/nonexistent/path/technique_all.json"
        )
        assert result == 0

    def test_returns_zero_when_all_empty_description(self, mock_manager):
        """所有条目 description 为空时返回 0"""
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = [
                {"technique_name": "技法A", "dimension": "战斗冲突维度",
                 "description": "", "keywords": [], "examples": [],
                 "source_novels": [], "_novel_id": "n1", "occurrence_count": 1}
            ]
            path = _make_json_file(tmpdir, entries)
            result = mock_manager.sync_technique_json(json_path=path)
        assert result == 0

    def test_syncs_valid_entries(self, mock_manager):
        """有效条目（description >= 20字）应被同步"""
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = [
                {
                    "technique_name": "战斗节奏控制",
                    "dimension": "战斗冲突维度",
                    "description": "通过短句和长句交替控制战斗节奏，短句加速紧张感，长句给读者喘息。",
                    "keywords": ["节奏", "短句"],
                    "examples": ["他出剑，对方退。再出剑，对方再退。"],
                    "source_novels": ["某玄幻小说"],
                    "_novel_id": "novel_001",
                    "occurrence_count": 5,
                },
                {
                    "technique_name": "短",
                    "dimension": "战斗冲突维度",
                    "description": "太短",   # < 20字，应被过滤
                    "keywords": [],
                    "examples": [],
                    "source_novels": [],
                    "_novel_id": "n2",
                    "occurrence_count": 1,
                },
            ]
            path = _make_json_file(tmpdir, entries)
            result = mock_manager.sync_technique_json(json_path=path)
        assert result == 1, f"应同步 1 条有效技法，实际 {result}"

    def test_upload_points_called(self, mock_manager):
        """_upload_points 应被调用"""
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = [
                {
                    "technique_name": "伏笔技法",
                    "dimension": "剧情维度",
                    "description": "在情节早期埋下细节，后文呼应形成结构闭环，增强读者惊喜感。",
                    "keywords": ["伏笔", "呼应"],
                    "examples": ["第一章提到的匕首，在第十章成为关键道具。"],
                    "source_novels": ["某小说"],
                    "_novel_id": "n3",
                    "occurrence_count": 3,
                }
            ]
            path = _make_json_file(tmpdir, entries)
            mock_manager.sync_technique_json(json_path=path)
        mock_manager._upload_points.assert_called_once()


class TestSyncTechniqueJsonPayload:

    def test_payload_dimension_correct(self, mock_manager):
        """入库 payload 的 dimension 字段应与 JSON 中一致"""
        captured_points = []

        def capture_upload(collection_name, points):
            captured_points.extend(points)

        mock_manager._upload_points = capture_upload

        with tempfile.TemporaryDirectory() as tmpdir:
            entries = [
                {
                    "technique_name": "力量代价描写",
                    "dimension": "战斗冲突维度",
                    "description": "每次使用力量必须付出具体代价，让读者感受力量的重量和主角的意志。",
                    "keywords": ["代价", "力量"],
                    "examples": ["鲜血从指尖渗出，但他没有停下。"],
                    "source_novels": ["某小说"],
                    "_novel_id": "n4",
                    "occurrence_count": 8,
                }
            ]
            path = _make_json_file(tmpdir, entries)
            mock_manager.sync_technique_json(json_path=path)

        assert len(captured_points) == 1
        payload = captured_points[0].payload
        assert payload["dimension"] == "战斗冲突维度"
        assert payload["writer"] == "剑尘"
        assert payload["name"] == "力量代价描写"
        assert "content" in payload
        assert len(payload["content"]) > 0

    def test_payload_writer_mapped_correctly(self, mock_manager):
        """WRITER_MAP 中存在的维度应正确映射 writer"""
        captured_points = []
        mock_manager._upload_points = lambda cn, pts: captured_points.extend(pts)

        dim_writer_pairs = [
            ("世界观维度", "苍澜"),
            ("剧情维度", "玄一"),
            ("人物维度", "墨言"),
            ("战斗冲突维度", "剑尘"),
            ("氛围意境维度", "云溪"),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = [
                {
                    "technique_name": f"{dim}技法",
                    "dimension": dim,
                    "description": f"这是{dim}的一种核心写作技法，适合在关键场景中使用。",
                    "keywords": [],
                    "examples": [],
                    "source_novels": [],
                    "_novel_id": f"n_{i}",
                    "occurrence_count": 1,
                }
                for i, (dim, _) in enumerate(dim_writer_pairs)
            ]
            path = _make_json_file(tmpdir, entries)
            mock_manager.sync_technique_json(json_path=path)

        assert len(captured_points) == 5
        for point, (dim, expected_writer) in zip(captured_points, dim_writer_pairs):
            assert point.payload["writer"] == expected_writer, \
                f"{dim} 应映射 writer={expected_writer}，实际 {point.payload['writer']}"

    def test_unknown_dimension_writer_is_unknown(self, mock_manager):
        """不在 WRITER_MAP 里的维度，writer 应为 '未知'"""
        captured_points = []
        mock_manager._upload_points = lambda cn, pts: captured_points.extend(pts)

        with tempfile.TemporaryDirectory() as tmpdir:
            entries = [
                {
                    "technique_name": "元叙事技法",
                    "dimension": "元维度",
                    "description": "打破第四堵墙，让叙述者直接与读者对话，制造间离效果。",
                    "keywords": ["元叙事"],
                    "examples": ["读者，你现在正在读的这本书，其实是主角写的。"],
                    "source_novels": [],
                    "_novel_id": "n5",
                    "occurrence_count": 1,
                }
            ]
            path = _make_json_file(tmpdir, entries)
            mock_manager.sync_technique_json(json_path=path)

        assert captured_points[0].payload["writer"] == "未知"


class TestCliTechniqueJson:

    def test_cli_has_technique_json_choice(self):
        """CLI --sync 参数应包含 technique-json 选项"""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "modules.knowledge_base.hybrid_sync_manager", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert "technique-json" in result.stdout, \
            "CLI --sync 选项中缺少 technique-json"

    def test_cli_has_json_path_argument(self):
        """CLI 应有 --json-path 参数"""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "modules.knowledge_base.hybrid_sync_manager", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert "--json-path" in result.stdout, \
            "CLI 缺少 --json-path 参数"
```

---

## 验证步骤（4阶段）

### 阶段1：新测试
```bash
cd D:/动画/众生界
python -m pytest tests/test_technique_json_sync.py -v 2>&1 | tee logs/test_technique_json_sync.log
```
预期：全部通过（约12个测试）。

### 阶段2：回归
```bash
python -m pytest tests/ -x --ignore=tests/test_unified_retrieval.py -q 2>&1 | tee logs/test_regression_technique_json.log
```
预期：无新增 FAILED。

### 阶段3：CLI 冒烟
```bash
python -m modules.knowledge_base.hybrid_sync_manager --help 2>&1 | grep -E "technique-json|json-path"
```
预期：两行都能看到。

### 阶段4：小规模试跑（仅前1000条，验证不崩溃）
> ⚠️ 此步骤需要 Qdrant 容器运行中（docker start qdrant）且 BGE-M3 模型在 E 盘
```bash
python -c "
import sys; sys.path.insert(0, '.')
import json
from pathlib import Path

# 截取前1000条写临时文件
src = Path('E:/novel_extracted/technique/technique_all.json')
with open(src, 'r', encoding='utf-8') as f:
    data = json.load(f)
tmp = Path('E:/novel_extracted/technique/technique_test_1k.json')
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(data[:1000], f, ensure_ascii=False)

from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager
sync = HybridSyncManager()
n = sync.sync_technique_json(json_path=str(tmp), rebuild=True)
print(f'试跑结果：同步 {n} 条')
tmp.unlink()
" 2>&1 | tee logs/test_technique_json_smoke.log
```
预期：输出 `试跑结果：同步 N 条`（N 约为 900-1000，过滤掉 description 过短的）。

---

## 完成后的使用方式

```bash
# 全量同步 technique_all.json → writing_techniques_v2（重建集合）
python -m modules.knowledge_base.hybrid_sync_manager --sync technique-json --rebuild

# 指定自定义路径
python -m modules.knowledge_base.hybrid_sync_manager --sync technique-json --json-path E:/other/path/technique_all.json --rebuild
```
