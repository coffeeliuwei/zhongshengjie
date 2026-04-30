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

        assert hasattr(HybridSyncManager, "sync_technique_json"), (
            "缺失方法 sync_technique_json"
        )

    def test_uses_batch_collection_not_v2(self):
        """sync_technique_json 必须写入 writing_techniques_batch_v1，不得动 v2"""
        import pathlib

        src = pathlib.Path("modules/knowledge_base/hybrid_sync_manager.py").read_text(
            encoding="utf-8"
        )
        fn_start = src.index("def sync_technique_json(")
        fn_body = src[fn_start : fn_start + 3000]
        assert "writing_techniques_batch" in fn_body, (
            "sync_technique_json 未使用 writing_techniques_batch collection"
        )
        # 方法体内不应出现直接写死 writing_techniques_v2 的字符串
        assert '"writing_techniques_v2"' not in fn_body, (
            "sync_technique_json 不得硬编码 writing_techniques_v2"
        )


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
                {
                    "technique_name": "技法A",
                    "dimension": "战斗冲突维度",
                    "description": "",
                    "keywords": [],
                    "examples": [],
                    "source_novels": [],
                    "_novel_id": "n1",
                    "occurrence_count": 1,
                }
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
                    "description": "太短",  # < 20字，应被过滤
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
            assert point.payload["writer"] == expected_writer, (
                f"{dim} 应映射 writer={expected_writer}，实际 {point.payload['writer']}"
            )

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
        """CLI --sync 参数应包含 technique-json 选项（AST 读源码验证）"""
        src = (
            PROJECT_ROOT / "modules" / "knowledge_base" / "hybrid_sync_manager.py"
        ).read_text(encoding="utf-8")
        assert "technique-json" in src, (
            "hybrid_sync_manager.py CLI 中缺少 technique-json 选项"
        )

    def test_cli_has_json_path_argument(self):
        """CLI 应有 --json-path 参数（AST 读源码验证）"""
        src = (
            PROJECT_ROOT / "modules" / "knowledge_base" / "hybrid_sync_manager.py"
        ).read_text(encoding="utf-8")
        assert "--json-path" in src, (
            "hybrid_sync_manager.py CLI 中缺少 --json-path 参数"
        )


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
        # 创建简单的 mock collection 对象，确保 .name 返回字符串
        mock_v2 = MagicMock()
        mock_v2.name = "writing_techniques_v2"
        mock_batch = MagicMock()
        mock_batch.name = "writing_techniques_batch_v1"
        mock_client.get_collections.return_value.collections = [mock_v2, mock_batch]

        # 每次 query_points 返回 2 个点
        def fake_query(collection_name, **kwargs):
            r = MagicMock()
            p1 = MagicMock()
            p1.score = 0.9
            p1.id = hash(collection_name + "1")
            p1.payload = {
                "name": f"tech_{collection_name}_1",
                "dimension": "剧情维度",
                "writer": "玄一",
                "source_file": "",
                "content": "测试内容",
                "word_count": 10,
            }
            p2 = MagicMock()
            p2.score = 0.7
            p2.id = hash(collection_name + "2")
            p2.payload = {
                "name": f"tech_{collection_name}_2",
                "dimension": "剧情维度",
                "writer": "玄一",
                "source_file": "",
                "content": "测试内容2",
                "word_count": 10,
            }
            r.points = [p1, p2]
            return r

        mock_client.query_points.side_effect = fake_query
        mgr._get_client = MagicMock(return_value=mock_client)
        mgr._encode_query = MagicMock(
            return_value={
                "dense": [0.0] * 1024,
                "sparse_indices": [0],
                "sparse_values": [0.1],
                "colbert": [[0.0] * 128],
            }
        )

        results = mgr.search_technique("测试查询", top_k=10, use_rerank=False)
        # 两个 collection 各 2 条，应返回 4 条（top_k=10）
        assert len(results) == 4, f"期望4条，实际{len(results)}条"
        # query_points 应被调用两次（各查一个 collection）
        assert mock_client.query_points.call_count == 2, (
            f"期望查询2次，实际{mock_client.query_points.call_count}次"
        )

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
        # 只有 v2，没有 batch - 确保 .name 是字符串
        mock_v2 = MagicMock()
        mock_v2.name = "writing_techniques_v2"
        mock_client.get_collections.return_value.collections = [mock_v2]
        r = MagicMock()
        p = MagicMock()
        p.score = 0.8
        p.id = 1
        p.payload = {
            "name": "tech1",
            "dimension": "剧情维度",
            "writer": "玄一",
            "source_file": "",
            "content": "内容",
            "word_count": 5,
        }
        r.points = [p]
        mock_client.query_points.return_value = r
        mgr._get_client = MagicMock(return_value=mock_client)
        mgr._encode_query = MagicMock(
            return_value={
                "dense": [0.0] * 1024,
                "sparse_indices": [0],
                "sparse_values": [0.1],
                "colbert": [[0.0] * 128],
            }
        )

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
        # 确保 .name 是字符串
        mock_v2 = MagicMock()
        mock_v2.name = "writing_techniques_v2"
        mock_batch = MagicMock()
        mock_batch.name = "writing_techniques_batch_v1"
        mock_client.get_collections.return_value.collections = [mock_v2, mock_batch]
        scores_by_collection = {
            "writing_techniques_v2": [0.6, 0.4],
            "writing_techniques_batch_v1": [0.9, 0.5],
        }
        call_count = [0]

        def fake_query(collection_name, **kwargs):
            r = MagicMock()
            points = []
            for i, sc in enumerate(scores_by_collection.get(collection_name, [])):
                p = MagicMock()
                p.score = sc
                p.id = call_count[0] * 10 + i
                p.payload = {
                    "name": f"t{i}",
                    "dimension": "剧情维度",
                    "writer": "玄一",
                    "source_file": "",
                    "content": "x",
                    "word_count": 1,
                }
                points.append(p)
                call_count[0] += 1
            r.points = points
            return r

        mock_client.query_points.side_effect = fake_query
        mgr._get_client = MagicMock(return_value=mock_client)
        mgr._encode_query = MagicMock(
            return_value={
                "dense": [0.0] * 1024,
                "sparse_indices": [0],
                "sparse_values": [0.1],
                "colbert": [[0.0] * 128],
            }
        )

        results = mgr.search_technique(
            "测试", min_score=0.0, top_k=10, use_rerank=False
        )
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), f"结果未按score降序：{scores}"
        assert scores[0] == 0.9, f"最高分应为0.9，实际{scores[0]}"
