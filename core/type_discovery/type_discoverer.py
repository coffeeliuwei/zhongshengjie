#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一类型发现器基类
===============

从外部小说库自动发现新的力量类型、势力类型、技法类型。

功能：
1. 提取未匹配片段
2. 关键词聚类分析
3. 生成新类型候选
4. 人工审批确认
5. 同步到配置文件

集成现有的 scene_discoverer.py（场景类型发现）。
"""

import json
import re
import sys
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置目录
CONFIG_DIMENSIONS_DIR = PROJECT_ROOT / "config" / "dimensions"

# 现有场景发现器（复用）
SCENE_DISCOVERER_PATH = PROJECT_ROOT / "tools" / "scene_discoverer.py"


@dataclass
class DiscoveredType:
    """发现的类型数据结构"""

    name: str  # 类型名称
    category: str  # 类型类别: power, faction, technique, scene
    keywords: List[str]  # 关键词列表
    sample_count: int  # 样本数量
    sample_sources: List[str]  # 来源列表
    confidence: float  # 置信度 0-1
    description: str = ""  # 描述
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"  # pending, approved, rejected

    def to_config(self) -> Dict:
        """转换为配置文件格式（子类可覆盖）"""
        return {
            "description": self.description or f"自动发现的{self.category}类型",
            "keywords": self.keywords[:10],
        }


class TypeDiscoverer(ABC):
    """统一类型发现器基类"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.min_samples = self.config.get("min_samples", 30)  # 最少样本数
        self.min_confidence = self.config.get("min_confidence", 0.5)  # 最低置信度
        self.max_keywords = self.config.get("max_keywords", 10)  # 最大关键词数

        # 加载现有类型
        self.existing_types = self._load_existing_types()

        # 未匹配片段
        self.unmatched_fragments: List[Dict] = []

        # 发现的新类型
        self.discovered_types: List[DiscoveredType] = []

    @abstractmethod
    def _load_existing_types(self) -> Set[str]:
        """加载现有类型（子类实现）"""
        pass

    @abstractmethod
    def _get_config_path(self) -> Path:
        """获取配置文件路径（子类实现）"""
        pass

    @abstractmethod
    def _get_type_category(self) -> str:
        """获取类型类别（子类实现）"""
        pass

    @abstractmethod
    def _match_existing(self, text: str) -> bool:
        """匹配现有类型（子类实现）"""
        pass

    @abstractmethod
    def _generate_type_name(self, kw1: str, kw2: str) -> str:
        """根据关键词生成类型名称（子类实现）"""
        pass

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 停用词
        stopwords = set(
            [
                "的",
                "了",
                "是",
                "在",
                "我",
                "有",
                "和",
                "就",
                "不",
                "人",
                "都",
                "一",
                "一个",
                "上",
                "也",
                "很",
                "到",
                "说",
                "要",
                "去",
                "你",
                "会",
                "着",
                "没有",
                "看",
                "好",
                "自己",
                "这",
                "那",
                "他",
                "她",
                "它",
                "们",
                "这个",
                "那个",
                "什么",
                "怎么",
                "但是",
                "因为",
                "所以",
                "然后",
                "虽然",
                "如果",
            ]
        )

        # 简单分词（按标点和空格）
        words = re.findall(r"[\u4e00-\u9fa5]{2,4}", text)

        # 过滤停用词
        words = [w for w in words if w not in stopwords and len(w) >= 2]

        # 统计词频
        counter = Counter(words)

        # 返回高频词
        return [w for w, _ in counter.most_common(10)]

    def collect_unmatched(self, texts: List[str], source_name: str) -> List[Dict]:
        """
        收集未匹配的片段

        Args:
            texts: 文本列表
            source_name: 来源名称

        Returns:
            未匹配的片段列表
        """
        unmatched = []

        for text in texts:
            if len(text) < 100 or len(text) > 5000:
                continue

            # 检查是否匹配现有类型
            if not self._match_existing(text):
                # 提取关键词
                keywords = self._extract_keywords(text)
                unmatched.append(
                    {
                        "content": text[:500],
                        "keywords": keywords,
                        "source": source_name,
                        "length": len(text),
                    }
                )

        self.unmatched_fragments.extend(unmatched)
        return unmatched

    def _cluster_by_keywords(self) -> Dict[str, Dict]:
        """关键词聚类分析"""
        # 统计关键词共现
        keyword_pairs: Counter = Counter()
        keyword_to_fragments: Dict[str, List[Dict]] = defaultdict(list)

        for frag in self.unmatched_fragments:
            keywords = frag.get("keywords", [])

            # 记录关键词对应的片段
            for kw in keywords[:5]:
                keyword_to_fragments[kw].append(frag)

            # 记录关键词共现
            for i, kw1 in enumerate(keywords[:5]):
                for kw2 in keywords[i + 1 : 5]:
                    pair = tuple(sorted([kw1, kw2]))
                    keyword_pairs[pair] += 1

        # 找出高频共现关键词组
        clusters: Dict[str, Dict] = {}

        for (kw1, kw2), count in keyword_pairs.most_common(50):
            if count < 5:  # 最少共现次数
                continue

            # 生成类型名称
            cluster_name = self._generate_type_name(kw1, kw2)

            if cluster_name not in clusters:
                clusters[cluster_name] = {
                    "keywords": [kw1, kw2],
                    "count": count,
                    "sources": [],
                }
            else:
                if kw1 not in clusters[cluster_name]["keywords"]:
                    clusters[cluster_name]["keywords"].append(kw1)
                if kw2 not in clusters[cluster_name]["keywords"]:
                    clusters[cluster_name]["keywords"].append(kw2)
                clusters[cluster_name]["count"] += count

            # 收集来源
            for frag in keyword_to_fragments.get(kw1, [])[:3]:
                if frag["source"] not in clusters[cluster_name]["sources"]:
                    clusters[cluster_name]["sources"].append(frag["source"])

        return clusters

    def discover_types(self) -> List[DiscoveredType]:
        """
        从未匹配片段中发现新类型

        Returns:
            发现的新类型列表
        """
        if len(self.unmatched_fragments) < self.min_samples:
            return []

        # 关键词聚类
        keyword_clusters = self._cluster_by_keywords()

        # 生成类型候选
        for cluster_name, cluster_data in keyword_clusters.items():
            if cluster_data["count"] >= self.min_samples:
                type_obj = DiscoveredType(
                    name=cluster_name,
                    category=self._get_type_category(),
                    keywords=cluster_data["keywords"],
                    sample_count=cluster_data["count"],
                    sample_sources=cluster_data["sources"][:5],
                    confidence=min(cluster_data["count"] / 100, 1.0),
                )
                self.discovered_types.append(type_obj)

        # 按置信度排序
        self.discovered_types.sort(key=lambda x: x.confidence, reverse=True)

        return self.discovered_types

    def approve_type(self, type_name: str) -> bool:
        """审批确认类型"""
        for type_obj in self.discovered_types:
            if type_obj.name == type_name:
                type_obj.status = "approved"
                self.save_discovered()
                return True
        return False

    def reject_type(self, type_name: str) -> bool:
        """拒绝类型"""
        for type_obj in self.discovered_types:
            if type_obj.name == type_name:
                type_obj.status = "rejected"
                self.save_discovered()
                return True
        return False

    def save_discovered(self) -> Path:
        """保存发现的类型"""
        config_path = self._get_config_path()
        discovered_path = (
            config_path.parent / f"discovered_{self._get_type_category()}.json"
        )

        discovered_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "updated_at": datetime.now().isoformat(),
            "total_fragments": len(self.unmatched_fragments),
            "discovered_types": [asdict(t) for t in self.discovered_types],
        }

        with open(discovered_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return discovered_path

    def load_discovered(self) -> List[DiscoveredType]:
        """加载已发现的类型"""
        config_path = self._get_config_path()
        discovered_path = (
            config_path.parent / f"discovered_{self._get_type_category()}.json"
        )

        if not discovered_path.exists():
            return []

        with open(discovered_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.discovered_types = [
            DiscoveredType(**t) for t in data.get("discovered_types", [])
        ]
        return self.discovered_types

    def sync_to_config(self, types: Optional[List[DiscoveredType]] = None) -> int:
        """
        同步到配置文件

        Args:
            types: 要同步的类型列表，默认为已批准的类型

        Returns:
            成功同步的数量
        """
        types = types or [t for t in self.discovered_types if t.status == "approved"]
        if not types:
            return 0

        config_path = self._get_config_path()

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 根据类别选择字段名
        type_field_map = {
            "power": "power_types",
            "faction": "faction_types",
            "technique": "technique_types",
            "scene": "scene_types",
        }

        type_key = type_field_map.get(self._get_type_category(), "types")
        type_dict = config.get(type_key, {})

        synced = 0
        for type_obj in types:
            if type_obj.name in self.existing_types:
                continue

            # 添加到配置
            type_dict[type_obj.name] = type_obj.to_config()
            self.existing_types.add(type_obj.name)
            synced += 1

        # 更新配置
        config[type_key] = type_dict
        config["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return synced

    def get_status(self) -> Dict[str, Any]:
        """获取发现器状态"""
        return {
            "category": self._get_type_category(),
            "existing_types": len(self.existing_types),
            "unmatched_fragments": len(self.unmatched_fragments),
            "discovered_types": len(self.discovered_types),
            "pending": sum(1 for t in self.discovered_types if t.status == "pending"),
            "approved": sum(1 for t in self.discovered_types if t.status == "approved"),
            "rejected": sum(1 for t in self.discovered_types if t.status == "rejected"),
        }


# ==================== 场景类型发现（复用现有 scene_discoverer.py）====================


def get_scene_discoverer():
    """
    获取场景发现器实例（复用现有的 scene_discoverer.py）

    不在此模块重新实现场景发现逻辑，而是导入现有的 SceneDiscoverer。
    """
    try:
        # 尝试导入现有的 SceneDiscoverer
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "scene_discoverer", SCENE_DISCOVERER_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.SceneDiscoverer
    except Exception as e:
        print(f"无法加载 scene_discoverer: {e}")
        return None
