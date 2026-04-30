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
        """CLI --sync 参数应包含 technique-json 选项"""
        import subprocess

        result = subprocess.run(
            ["python", "-m", "modules.knowledge_base.hybrid_sync_manager", "--help"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert "technique-json" in result.stdout, "CLI --sync 选项中缺少 technique-json"

    def test_cli_has_json_path_argument(self):
        """CLI 应有 --json-path 参数"""
        import subprocess

        result = subprocess.run(
            ["python", "-m", "modules.knowledge_base.hybrid_sync_manager", "--help"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert "--json-path" in result.stdout, "CLI 缺少 --json-path 参数"
