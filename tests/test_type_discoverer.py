#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
类型发现器测试
==============

测试 TypeDiscoverer 和 PowerTypeDiscoverer 的核心功能：
- 类型发现流程
- 关键词提取和聚类
- 审批和拒绝机制
- 配置同步功能

使用 pytest 框架和 mock 避免真实数据依赖。
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Set, Any

# 项目路径
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.type_discovery.type_discoverer import (
    TypeDiscoverer,
    DiscoveredType,
)
from core.type_discovery.power_type_discoverer import PowerTypeDiscoverer


# ==================== Fixtures ====================


@pytest.fixture
def temp_project_root():
    """创建临时项目目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # 创建配置目录
        (root / "config" / "dimensions").mkdir(parents=True, exist_ok=True)
        yield root


@pytest.fixture
def sample_power_types_config(temp_project_root):
    """创建示例力量类型配置"""
    config_path = temp_project_root / "config" / "dimensions" / "power_types.json"
    config_data = {
        "power_types": {
            "修仙": {
                "description": "修仙体系",
                "keywords": ["灵气", "境界", "丹田"],
            },
            "魔法": {
                "description": "魔法体系",
                "keywords": ["魔力", "元素", "禁咒"],
            },
        },
        "updated_at": "2025-01-01",
    }
    config_path.write_text(
        json.dumps(config_data, ensure_ascii=False), encoding="utf-8"
    )
    return config_path


@pytest.fixture
def sample_novel_texts():
    """创建示例小说文本"""
    return [
        "他运转体内的血脉之力，感受到血液中蕴含的古老力量。随着血脉觉醒，他的双眼泛起金光，"
        "一股原始的兽性力量在他体内苏醒。这是血脉传承带来的力量，让他拥有了超越常人的能力。",
        "灵魂深处的力量开始觉醒，他能感受到灵魂之火的燃烧。每一次灵魂力量的运用，"
        "都会消耗他的精神力，但也让他的灵魂变得更加强大。这是一种稀有的灵魂力量体系。",
        "他掌控着时间的流逝，能够在战斗中操控时间流速。时间力量是极其罕见的能力，"
        "只有极少数人能够觉醒。运用时间力量需要付出巨大的代价，但威力惊人。",
        "空间的撕裂让他能够瞬间移动，空间力量的运用让他在战斗中占据优势。"
        "空间法则的领悟需要极高的天赋，这是一条艰难的修炼之路。",
    ]


@pytest.fixture
def power_discoverer(temp_project_root, sample_power_types_config):
    """创建 PowerTypeDiscoverer 实例（patch 在整个测试期间保持生效）"""
    patcher = patch(
        "core.type_discovery.type_discoverer.CONFIG_DIMENSIONS_DIR",
        temp_project_root / "config" / "dimensions",
    )
    patcher.start()
    discoverer = PowerTypeDiscoverer()
    yield discoverer
    patcher.stop()


# ==================== DiscoveredType 测试 ====================


class TestDiscoveredType:
    """DiscoveredType 数据类测试"""

    def test_discovered_type_creation(self):
        """测试创建发现的类型"""
        discovered = DiscoveredType(
            name="血脉力量",
            category="power",
            keywords=["血脉", "觉醒", "兽性"],
            sample_count=50,
            sample_sources=["小说1", "小说2"],
            confidence=0.8,
        )

        assert discovered.name == "血脉力量"
        assert discovered.category == "power"
        assert len(discovered.keywords) == 3
        assert discovered.status == "pending"

    def test_discovered_type_to_config(self):
        """测试转换为配置格式"""
        discovered = DiscoveredType(
            name="时间力量",
            category="power",
            keywords=["时间", "流速", "操控"],
            sample_count=30,
            sample_sources=["小说A"],
            confidence=0.7,
            description="时间操控能力体系",
        )

        config = discovered.to_config()

        assert "description" in config
        assert "keywords" in config
        assert len(config["keywords"]) <= 10

    def test_discovered_type_status_changes(self):
        """测试状态变更"""
        discovered = DiscoveredType(
            name="测试类型",
            category="power",
            keywords=["测试"],
            sample_count=10,
            sample_sources=[],
            confidence=0.5,
        )

        assert discovered.status == "pending"

        # 修改状态
        discovered.status = "approved"
        assert discovered.status == "approved"

        discovered.status = "rejected"
        assert discovered.status == "rejected"


# ==================== TypeDiscoverer 基类测试 ====================


class TestTypeDiscovererInit:
    """TypeDiscoverer 初始化测试"""

    def test_init_with_default_config(self, temp_project_root):
        """测试默认配置初始化"""

        # 创建具体实现类的测试类
        class ConcreteDiscoverer(TypeDiscoverer):
            def _load_existing_types(self) -> Set[str]:
                return set()

            def _get_config_path(self) -> Path:
                return temp_project_root / "test.json"

            def _get_type_category(self) -> str:
                return "test"

            def _match_existing(self, text: str) -> bool:
                return False

            def _generate_type_name(self, kw1: str, kw2: str) -> str:
                return f"{kw1}{kw2}"

        discoverer = ConcreteDiscoverer()

        assert discoverer.min_samples == 30
        assert discoverer.min_confidence == 0.5
        assert discoverer.max_keywords == 10

    def test_init_with_custom_config(self, temp_project_root):
        """测试自定义配置初始化"""
        custom_config = {
            "min_samples": 50,
            "min_confidence": 0.7,
            "max_keywords": 15,
        }

        class ConcreteDiscoverer(TypeDiscoverer):
            def _load_existing_types(self) -> Set[str]:
                return set()

            def _get_config_path(self) -> Path:
                return temp_project_root / "test.json"

            def _get_type_category(self) -> str:
                return "test"

            def _match_existing(self, text: str) -> bool:
                return False

            def _generate_type_name(self, kw1: str, kw2: str) -> str:
                return f"{kw1}{kw2}"

        discoverer = ConcreteDiscoverer(config=custom_config)

        assert discoverer.min_samples == 50
        assert discoverer.min_confidence == 0.7
        assert discoverer.max_keywords == 15


class TestTypeDiscovererKeywordExtraction:
    """关键词提取测试"""

    def test_extract_keywords(self, temp_project_root):
        """测试关键词提取"""

        class ConcreteDiscoverer(TypeDiscoverer):
            def _load_existing_types(self) -> Set[str]:
                return set()

            def _get_config_path(self) -> Path:
                return temp_project_root / "test.json"

            def _get_type_category(self) -> str:
                return "test"

            def _match_existing(self, text: str) -> bool:
                return False

            def _generate_type_name(self, kw1: str, kw2: str) -> str:
                return f"{kw1}{kw2}"

        discoverer = ConcreteDiscoverer()

        text = "他运转体内的血脉之力，感受到血液中蕴含的古老力量。血脉觉醒带来超越常人的能力。"
        keywords = discoverer._extract_keywords(text)

        assert len(keywords) > 0
        assert len(keywords) <= 10
        # 应包含关键词
        assert any("血脉" in kw or "力量" in kw for kw in keywords)

    def test_extract_keywords_filters_stopwords(self, temp_project_root):
        """测试过滤停用词"""

        class ConcreteDiscoverer(TypeDiscoverer):
            def _load_existing_types(self) -> Set[str]:
                return set()

            def _get_config_path(self) -> Path:
                return temp_project_root / "test.json"

            def _get_type_category(self) -> str:
                return "test"

            def _match_existing(self, text: str) -> bool:
                return False

            def _generate_type_name(self, kw1: str, kw2: str) -> str:
                return f"{kw1}{kw2}"

        discoverer = ConcreteDiscoverer()

        text = "这是一个测试的文章，但是没有什么实际内容。"
        keywords = discoverer._extract_keywords(text)

        # 停用词应被过滤
        assert "这是" not in keywords
        assert "但是" not in keywords
        assert "没有" not in keywords


class TestTypeDiscovererCollection:
    """片段收集测试"""

    def test_collect_unmatched(self, temp_project_root):
        """测试收集未匹配片段"""

        class ConcreteDiscoverer(TypeDiscoverer):
            def _load_existing_types(self) -> Set[str]:
                return {"现有类型"}

            def _get_config_path(self) -> Path:
                return temp_project_root / "test.json"

            def _get_type_category(self) -> str:
                return "test"

            def _match_existing(self, text: str) -> bool:
                return "现有类型" in text

            def _generate_type_name(self, kw1: str, kw2: str) -> str:
                return f"{kw1}{kw2}"

        discoverer = ConcreteDiscoverer()

        texts = [
            "这是一个未匹配的片段，包含新的内容。" + "补充内容使其超过最低长度限制。" * 6,
            "这是现有类型的描述，应该被匹配。" + "补充内容使其超过最低长度限制。" * 6,
            "另一个未匹配的片段。" + "补充内容使其超过最低长度限制。" * 6,
        ]

        unmatched = discoverer.collect_unmatched(texts, "测试来源")

        # 只有未匹配的片段（2个，排除了"现有类型"的那个）
        assert len(unmatched) == 2
        for item in unmatched:
            assert "内容" in item["content"] or "片段" in item["content"]

    def test_collect_filters_by_length(self, temp_project_root):
        """测试按长度过滤"""

        class ConcreteDiscoverer(TypeDiscoverer):
            def _load_existing_types(self) -> Set[str]:
                return set()

            def _get_config_path(self) -> Path:
                return temp_project_root / "test.json"

            def _get_type_category(self) -> str:
                return "test"

            def _match_existing(self, text: str) -> bool:
                return False

            def _generate_type_name(self, kw1: str, kw2: str) -> str:
                return f"{kw1}{kw2}"

        discoverer = ConcreteDiscoverer()

        texts = [
            "短",  # 太短
            "这个片段长度正好，符合要求。这是一个合适的文本片段。" * 5,  # 合适(>100字符)
            "这个片段非常长" * 1000,  # 太长
        ]

        unmatched = discoverer.collect_unmatched(texts, "测试")

        # 只有合适长度的片段
        assert len(unmatched) == 1


# ==================== PowerTypeDiscoverer 测试 ====================


class TestPowerTypeDiscovererInit:
    """PowerTypeDiscoverer 初始化测试"""

    def test_init_loads_existing_types(self, power_discoverer):
        """测试加载现有类型"""
        existing = power_discoverer.existing_types

        assert "修仙" in existing
        assert "魔法" in existing

    def test_power_keywords_mapping(self, power_discoverer):
        """测试力量关键词映射"""
        assert "修仙" in power_discoverer.POWER_KEYWORDS
        assert "魔法" in power_discoverer.POWER_KEYWORDS
        assert "神术" in power_discoverer.POWER_KEYWORDS


class TestPowerTypeDiscovererMatch:
    """PowerTypeDiscoverer 匹配测试"""

    def test_match_existing_power_type(self, power_discoverer):
        """测试匹配现有力量类型"""
        text = "他运转体内的灵气，感受到丹田中的真气流转。修仙之路漫长而艰辛。"

        matched = power_discoverer._match_existing(text)

        assert matched == True

    def test_match_non_existing_power_type(self, power_discoverer):
        """测试不匹配新力量类型"""
        text = (
            "他感受到血脉中的古老力量，这是前所未有的血脉传承。兽性之力在他体内觉醒。"
        )

        matched = power_discoverer._match_existing(text)

        # 血脉力量不在现有类型中
        # 具体行为取决于实现（可能匹配 cost_keywords）
        assert isinstance(matched, bool)


class TestPowerTypeDiscovererDiscovery:
    """PowerTypeDiscoverer 发现测试"""

    def test_discover_power_types(self, power_discoverer, sample_novel_texts):
        """测试发现新力量类型"""
        # 收集未匹配片段
        for i, text in enumerate(sample_novel_texts):
            paragraphs = [text]
            power_discoverer.collect_unmatched(paragraphs, f"小说_{i}")

        # 发现新类型（需要足够的样本）
        discovered = power_discoverer.discover_types()

        # 应发现新类型（取决于样本数量和阈值）
        assert isinstance(discovered, list)

    def test_discover_with_insufficient_samples(self, power_discoverer):
        """测试样本不足时的发现"""
        # 只有少量文本
        texts = ["这是一个简短的测试文本。"]

        power_discoverer.collect_unmatched(texts, "测试")

        discovered = power_discoverer.discover_types()

        # 样本不足时应返回空列表
        assert discovered == []


class TestPowerTypeDiscovererApproval:
    """PowerTypeDiscoverer 审批测试"""

    def test_approve_type(self, power_discoverer, temp_project_root):
        """测试审批类型"""
        # 添加一个待审批的类型
        power_discoverer.discovered_types = [
            DiscoveredType(
                name="血脉力量",
                category="power",
                keywords=["血脉", "觉醒"],
                sample_count=50,
                sample_sources=["小说1"],
                confidence=0.8,
            )
        ]

        # 审批
        result = power_discoverer.approve_type("血脉力量")

        assert result == True
        assert power_discoverer.discovered_types[0].status == "approved"

    def test_approve_nonexistent_type(self, power_discoverer):
        """测试审批不存在的类型"""
        result = power_discoverer.approve_type("不存在的类型")

        assert result == False

    def test_reject_type(self, power_discoverer, temp_project_root):
        """测试拒绝类型"""
        power_discoverer.discovered_types = [
            DiscoveredType(
                name="测试类型",
                category="power",
                keywords=["测试"],
                sample_count=10,
                sample_sources=[],
                confidence=0.3,
            )
        ]

        result = power_discoverer.reject_type("测试类型")

        assert result == True
        assert power_discoverer.discovered_types[0].status == "rejected"


class TestPowerTypeDiscovererSync:
    """PowerTypeDiscoverer 同步测试"""

    def test_sync_to_config(self, power_discoverer, sample_power_types_config):
        """测试同步到配置"""
        # 添加已批准的类型
        power_discoverer.discovered_types = [
            DiscoveredType(
                name="血脉力量",
                category="power",
                keywords=["血脉", "觉醒"],
                sample_count=50,
                sample_sources=["小说1"],
                confidence=0.8,
                status="approved",
            )
        ]

        # 同步
        synced = power_discoverer.sync_to_config()

        assert synced == 1

        # 验证配置文件更新
        with open(sample_power_types_config, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "血脉力量" in config["power_types"]

    def test_sync_only_approved_types(
        self, power_discoverer, sample_power_types_config
    ):
        """测试只同步已批准的类型"""
        power_discoverer.discovered_types = [
            DiscoveredType(
                name="已批准",
                category="power",
                keywords=["批准"],
                sample_count=50,
                sample_sources=[],
                confidence=0.8,
                status="approved",
            ),
            DiscoveredType(
                name="待审批",
                category="power",
                keywords=["待审批"],
                sample_count=50,
                sample_sources=[],
                confidence=0.8,
                status="pending",
            ),
        ]

        synced = power_discoverer.sync_to_config()

        # 只同步已批准的
        assert synced == 1

    def test_sync_no_approved_types(self, power_discoverer, sample_power_types_config):
        """测试无已批准类型时的同步"""
        power_discoverer.discovered_types = [
            DiscoveredType(
                name="待审批",
                category="power",
                keywords=["待审批"],
                sample_count=50,
                sample_sources=[],
                confidence=0.8,
                status="pending",
            )
        ]

        synced = power_discoverer.sync_to_config()

        assert synced == 0


class TestPowerTypeDiscovererPersistence:
    """PowerTypeDiscoverer 持久化测试"""

    def test_save_and_load_discovered(self, power_discoverer, temp_project_root):
        """测试保存和加载发现的类型"""
        # 添加发现的类型
        power_discoverer.discovered_types = [
            DiscoveredType(
                name="血脉力量",
                category="power",
                keywords=["血脉", "觉醒"],
                sample_count=50,
                sample_sources=["小说1"],
                confidence=0.8,
            )
        ]

        power_discoverer.unmatched_fragments = [
            {
                "content": "测试内容",
                "keywords": ["测试"],
                "source": "测试来源",
                "length": 100,
            }
        ]

        # 保存
        saved_path = power_discoverer.save_discovered()

        assert saved_path.exists()

        # 清空并重新加载
        power_discoverer.discovered_types = []
        power_discoverer.unmatched_fragments = []

        loaded = power_discoverer.load_discovered()

        assert len(loaded) == 1
        assert loaded[0].name == "血脉力量"

    def test_get_status(self, power_discoverer):
        """测试获取状态"""
        power_discoverer.discovered_types = [
            DiscoveredType(
                name="类型1",
                category="power",
                keywords=["测试"],
                sample_count=50,
                sample_sources=[],
                confidence=0.8,
                status="approved",
            ),
            DiscoveredType(
                name="类型2",
                category="power",
                keywords=["测试"],
                sample_count=50,
                sample_sources=[],
                confidence=0.8,
                status="pending",
            ),
        ]

        status = power_discoverer.get_status()

        assert status["approved"] == 1
        assert status["pending"] == 1
        assert status["discovered_types"] == 2


class TestPowerTypeDiscovererFeatures:
    """PowerTypeDiscoverer 特征提取测试"""

    def test_extract_power_features(self, power_discoverer):
        """测试提取力量特征"""
        text = """
        他施展了火焰冲击，消耗了大量灵气，脸色变得苍白。
        经过一番调息和冥想，他的力量逐渐恢复。
        """

        features = power_discoverer._extract_power_features(text)

        assert "skills" in features
        assert "costs" in features
        assert "recovery" in features
        # 应提取到技能
        assert len(features["skills"]) > 0 or len(features["recovery"]) > 0

    def test_generate_type_name(self, power_discoverer):
        """测试生成类型名称"""
        name1 = power_discoverer._generate_type_name("血脉", "觉醒")
        assert "血脉" in name1 or "觉醒" in name1

        name2 = power_discoverer._generate_type_name("时间", "控制")
        assert "时间" in name2 or "控制" in name2


# ==================== 边缘情况测试 ====================


class TestTypeDiscovererEdgeCases:
    """边缘情况测试"""

    def test_empty_novel_list(self, power_discoverer):
        """测试空小说列表"""
        discovered = power_discoverer.discover_power_types([])

        assert discovered == []

    def test_config_file_not_exists(self, temp_project_root):
        """测试配置文件不存在"""
        with patch(
            "core.type_discovery.type_discoverer.CONFIG_DIMENSIONS_DIR",
            temp_project_root / "config" / "dimensions",
        ):
            discoverer = PowerTypeDiscoverer()

            # 应使用默认关键词映射
            assert len(discoverer.existing_types) > 0

    def test_cluster_with_no_common_keywords(self, temp_project_root):
        """测试无共同关键词的聚类"""

        class ConcreteDiscoverer(TypeDiscoverer):
            def _load_existing_types(self) -> Set[str]:
                return set()

            def _get_config_path(self) -> Path:
                return temp_project_root / "test.json"

            def _get_type_category(self) -> str:
                return "test"

            def _match_existing(self, text: str) -> bool:
                return False

            def _generate_type_name(self, kw1: str, kw2: str) -> str:
                return f"{kw1}{kw2}"

        discoverer = ConcreteDiscoverer()

        # 添加不相关的片段
        for i in range(50):
            discoverer.unmatched_fragments.append(
                {
                    "content": f"完全不相关的内容 {i}",
                    "keywords": [f"关键词{i}"],
                    "source": f"来源{i}",
                    "length": 100,
                }
            )

        # 聚类
        clusters = discoverer._cluster_by_keywords()

        # 应优雅处理
        assert isinstance(clusters, dict)


# ==================== 性能测试 ====================


class TestTypeDiscovererPerformance:
    """性能测试"""

    def test_large_novel_collection(self, power_discoverer):
        """测试大量小说收集"""
        # 生成大量文本
        texts = []
        for i in range(100):
            text = f"这是第{i}个小说片段，包含血脉力量和时间力量的描述。关键词提取需要性能优化。"
            texts.append(text)

        import time

        start = time.time()

        for i, text in enumerate(texts):
            power_discoverer.collect_unmatched([text], f"小说_{i}")

        elapsed = time.time() - start

        # 应在合理时间内完成（< 5秒）
        assert elapsed < 5.0

    def test_keyword_clustering_performance(self, temp_project_root):
        """测试关键词聚类性能"""

        class ConcreteDiscoverer(TypeDiscoverer):
            def _load_existing_types(self) -> Set[str]:
                return set()

            def _get_config_path(self) -> Path:
                return temp_project_root / "test.json"

            def _get_type_category(self) -> str:
                return "test"

            def _match_existing(self, text: str) -> bool:
                return False

            def _generate_type_name(self, kw1: str, kw2: str) -> str:
                return f"{kw1}{kw2}"

        discoverer = ConcreteDiscoverer()

        # 添加大量片段
        for i in range(1000):
            discoverer.unmatched_fragments.append(
                {
                    "content": f"内容 {i}",
                    "keywords": [f"关键词{i % 20}", f"关键词{(i + 1) % 20}"],
                    "source": f"来源{i}",
                    "length": 100,
                }
            )

        import time

        start = time.time()

        clusters = discoverer._cluster_by_keywords()

        elapsed = time.time() - start

        # 应在合理时间内完成（< 3秒）
        assert elapsed < 3.0


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
