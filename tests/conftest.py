"""
众生界项目 - 共享测试配置和Fixture

提供跨测试文件共享的fixture，包括：
- 临时项目目录
- Mock配置
- 数据库连接Mock
- 测试数据生成
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_project_root(tmp_path):
    """创建临时项目根目录，模拟众生界项目结构"""
    dirs = ["设定", "正文", "创作技法", "config", "core", "modules"]
    for d in dirs:
        (tmp_path / d).mkdir(exist_ok=True)
    yield tmp_path


@pytest.fixture
def temp_config_dir(temp_project_root):
    """创建临时配置目录"""
    config_dir = temp_project_root / "config"
    return config_dir


@pytest.fixture
def sample_config(temp_project_root):
    """创建示例配置文件"""
    config = {
        "qdrant_url": "http://localhost:6333",
        "model_path": "BAAI/bge-m3",
        "project_root": str(temp_project_root),
        "cache_dir": str(temp_project_root / ".cache"),
    }
    config_path = temp_project_root / "config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config_path


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant客户端"""
    with patch("qdrant_client.QdrantClient") as mock_client:
        instance = MagicMock()
        mock_client.return_value = instance
        instance.get_collections.return_value = MagicMock(collections=[])
        instance.search.return_value = []
        yield instance


@pytest.fixture
def sample_novel_text():
    """示例小说文本"""
    return """
    陈凡盘膝而坐，体内的灵力缓缓流转。经过三个月的苦修，
    他终于突破到了炼气期第三层。体内的灵力如同一条银色的河流，
    在经脉中奔涌不息。

    "不错，你的修炼速度比同龄人快了三倍。"长老微微点头，
    眼中闪过一丝赞赏。

    陈凡心中暗喜，但他知道这仅仅是开始。修仙之路漫漫，
    前方还有筑基、金丹、元婴等重重境界等待着他。
    """


@pytest.fixture
def sample_power_config():
    """示例力量体系配置"""
    return {
        "修仙": {
            "description": "修仙体系",
            "keywords": ["灵力", "修炼", "突破"]
        },
        "魔法": {
            "description": "魔法体系",
            "keywords": ["魔力", "元素", "施法"]
        }
    }


@pytest.fixture
def isolated_env(monkeypatch, temp_project_root):
    """隔离环境变量，确保测试不影响真实环境"""
    monkeypatch.setenv("NOVEL_PROJECT_ROOT", str(temp_project_root))
    monkeypatch.setenv("NOVEL_CACHE_DIR", str(temp_project_root / ".cache"))
    monkeypatch.delenv("QDRANT_URL", raising=False)
    return temp_project_root
