#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
势力类型发现器
=============

从对话中自动发现新的势力类型。

例如：发现"商会"、"宗门"、"学院"、"联盟"等新势力。

配置文件：config/dimensions/faction_types.json
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional

from .type_discoverer import TypeDiscoverer, DiscoveredType


class FactionDiscoverer(TypeDiscoverer):
    """势力类型发现器"""

    # 势力关键词映射（用于识别现有类型）
    FACTION_KEYWORDS = {
        "宗门": ["宗门", "派", "门", "宗", "阁", "殿", "峰", "院", "师徒", "弟子"],
        "家族": ["家族", "世家", "族", "府", "宅", "血脉", "嫡庶", "族规"],
        "商会": ["商会", "商盟", "楼", "阁", "行", "交易", "情报", "财富"],
        "朝廷": ["朝廷", "国", "朝", "廷", "宫", "皇帝", "军队", "法律"],
        "帮派": ["帮", "派", "会", "堂", "舵", "江湖", "义气", "地盘"],
        "联盟": ["联盟", "盟", "联合", "同盟", "合作", "共同利益"],
        "魔道": ["魔", "邪", "血", "鬼", "煞", "邪术", "掠夺", "颠覆"],
        "教派": ["教", "寺", "庙", "观", "殿", "信仰", "神术", "教义"],
        "学院": ["学院", "书院", "学府", "学宫", "培养", "学术", "竞技"],
        "组织": ["组织", "阁", "楼", "司", "部", "隐秘", "任务", "情报"],
    }

    # 势力特征关键词
    FACTION_FEATURES = {
        "师徒传承": ["师父", "师傅", "徒弟", "弟子", "传功", "授业"],
        "血脉传承": ["血脉", "祖先", "传承", "嫡系", "旁系"],
        "交易网络": ["交易", "买卖", "商路", "情报", "货物"],
        "政治权力": ["皇帝", "大臣", "将军", "军队", "法律", "命令"],
        "江湖义气": ["义气", "兄弟", "帮规", "地盘", "老大"],
        "多方合作": ["联盟", "联手", "合作", "共同", "协议"],
        "信仰传播": ["信仰", "信徒", "祈祷", "教义", "神恩"],
        "人才培养": ["学员", "学生", "导师", "课程", "考核"],
        "隐秘行动": ["隐秘", "暗杀", "情报", "任务", "代号"],
    }

    def _load_existing_types(self) -> Set[str]:
        """加载现有势力类型"""
        config_path = self._get_config_path()

        if not config_path.exists():
            # 使用默认关键词映射
            return set(self.FACTION_KEYWORDS.keys())

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        return set(config.get("faction_types", {}).keys())

    def _get_config_path(self) -> Path:
        """获取配置文件路径"""
        from .type_discoverer import CONFIG_DIMENSIONS_DIR

        return CONFIG_DIMENSIONS_DIR / "faction_types.json"

    def _get_type_category(self) -> str:
        """获取类型类别"""
        return "faction"

    def _match_existing(self, text: str) -> bool:
        """匹配现有势力类型"""
        # 检查是否包含任何现有势力关键词
        for faction_type, keywords in self.FACTION_KEYWORDS.items():
            if faction_type in self.existing_types:
                match_count = sum(1 for kw in keywords if kw in text)
                if match_count >= 2:
                    return True

        # 检查势力特征关键词
        for feature, keywords in self.FACTION_FEATURES.items():
            match_count = sum(1 for kw in keywords if kw in text)
            if match_count >= 2:
                return True

        return False

    def _generate_type_name(self, kw1: str, kw2: str) -> str:
        """根据关键词生成势力类型名称"""
        # 势力类型命名规则
        name_patterns = {
            # 常见势力关键词组合
            ("商会", "联盟"): "商业联盟",
            ("学院", "宗门"): "学院宗门",
            ("帮派", "联盟"): "帮派联盟",
            ("朝廷", "势力"): "朝廷势力",
            ("教派", "组织"): "教派组织",
            ("隐秘", "组织"): "隐秘组织",
            ("情报", "网络"): "情报网络",
            ("商业", "势力"): "商业势力",
        }

        pair = tuple(sorted([kw1, kw2]))
        if pair in name_patterns:
            return name_patterns[pair]

        # 自动生成名称
        faction_suffixes = ["势力", "组织", "联盟", "帮派", "团体"]
        for suffix in faction_suffixes:
            if kw1.endswith(suffix) or kw2.endswith(suffix):
                return f"{kw1}{kw2}"

        # 默认命名
        if any(
            w in kw1 + kw2 for w in ["商", "学", "帮", "朝", "教", "隐", "情", "联"]
        ):
            return f"{kw1}{kw2}势力"

        return f"{kw1}{kw2}组织"

    def discover_factions(self, dialogues: List[str]) -> List[DiscoveredType]:
        """
        从对话中发现新的势力类型

        Args:
            dialogues: 对话文本列表

        Returns:
            发现的新势力类型列表
        """
        # 收集未匹配片段
        for i, dialogue in enumerate(dialogues):
            # 提取对话中的势力相关信息
            # 查找势力名称模式：如"某某宗门"、"某某家族"等
            faction_patterns = [
                r"(\w+宗门)",
                r"(\w+家族)",
                r"(\w+派)",
                r"(\w+门)",
                r"(\w+教)",
                r"(\w+盟)",
                r"(\w+帮)",
                r"(\w+会)",
                r"(\w+学院)",
                r"(\w+组织)",
            ]

            factions_found = []
            for pattern in faction_patterns:
                matches = re.findall(pattern, dialogue)
                factions_found.extend(matches)

            if factions_found:
                self.collect_unmatched([dialogue], f"对话_{i}")

        # 发现新类型
        return self.discover_types()

    def _extract_faction_features(self, text: str) -> Dict:
        """从文本中提取势力特征"""
        features = {
            "keywords": [],
            "examples": [],
            "features": [],
        }

        # 提取势力关键词
        faction_keywords = [
            "宗门",
            "家族",
            "商会",
            "朝廷",
            "帮派",
            "联盟",
            "魔道",
            "教派",
            "学院",
            "组织",
            "派",
            "门",
            "盟",
        ]
        for kw in faction_keywords:
            if kw in text:
                features["keywords"].append(kw)

        # 提取势力名称示例
        example_patterns = [
            r"(\w+宗门)",
            r"(\w+家族)",
            r"(\w+派)",
            r"(\w+门)",
            r"(\w+教)",
        ]
        for pattern in example_patterns:
            matches = re.findall(pattern, text)
            features["examples"].extend(matches[:3])

        # 提取势力特征
        for feature, keywords in self.FACTION_FEATURES.items():
            if any(kw in text for kw in keywords):
                features["features"].append(feature)

        return features

    def sync_to_config(self, types: Optional[List[DiscoveredType]] = None) -> int:
        """
        同步到 faction_types.json

        同步时会自动填充势力的完整结构：
        - keywords: 关键词列表
        - examples: 势力名称示例
        - features: 势力特征
        """
        types = types or [t for t in self.discovered_types if t.status == "approved"]
        if not types:
            return 0

        config_path = self._get_config_path()

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        faction_types = config.get("faction_types", {})

        synced = 0
        for type_obj in types:
            if type_obj.name in self.existing_types:
                continue

            # 从样本中提取势力特征
            sample_features = self._extract_faction_features(
                type_obj.keywords[0] if type_obj.keywords else ""
            )

            # 构建完整的势力类型配置
            faction_types[type_obj.name] = {
                "description": type_obj.description or f"自动发现的势力类型",
                "keywords": type_obj.keywords[:10]
                if type_obj.keywords
                else sample_features["keywords"],
                "examples": sample_features["examples"][:3]
                if sample_features["examples"]
                else [],
                "features": sample_features["features"][:4]
                if sample_features["features"]
                else ["未知特征"],
                "auto_discovered": True,
                "discovered_at": type_obj.created_at,
            }

            self.existing_types.add(type_obj.name)
            synced += 1

        # 更新配置
        config["faction_types"] = faction_types
        config["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return synced
