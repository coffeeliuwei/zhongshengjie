#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
力量类型发现器
=============

从小说中自动发现新的力量体系类型。

例如：发现"血脉"、"灵魂"、"命运"、"因果"等新力量体系。

配置文件：config/dimensions/power_types.json
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional

from .type_discoverer import TypeDiscoverer, DiscoveredType


class PowerTypeDiscoverer(TypeDiscoverer):
    """力量类型发现器"""

    # 力量体系关键词映射（用于识别现有类型）
    POWER_KEYWORDS = {
        "修仙": [
            "灵气",
            "境界",
            "丹田",
            "经脉",
            "真气",
            "修仙",
            "筑基",
            "金丹",
            "元婴",
        ],
        "魔法": ["魔力", "魔法", "元素", "禁咒", "火球", "冰刃", "雷击"],
        "神术": ["圣光", "神恩", "信仰", "审判", "祈祷", "神术"],
        "科技": ["机甲", "激光", "芯片", "改造", "科技", "能源", "系统"],
        "兽力": ["血脉", "兽化", "图腾", "觉醒", "兽力"],
        "AI力": ["黑客", "控制", "入侵", "数据", "AI", "算力"],
        "异能": ["基因", "超感知", "异能", "再生", "精神控制"],
    }

    # 力量代价关键词
    COST_KEYWORDS = [
        "耗尽",
        "枯竭",
        "透支",
        "反噬",
        "崩溃",
        "代价",
        "燃烧",
        "消耗",
        "虚弱",
        "萎靡",
        "苍白",
        "剧痛",
        "昏迷",
    ]

    # 力量恢复关键词
    RECOVERY_KEYWORDS = [
        "恢复",
        "调息",
        "打坐",
        "冥想",
        "修炼",
        "吸纳",
        "充能",
        "休息",
        "丹药",
        "药剂",
        "治疗",
    ]

    def _load_existing_types(self) -> Set[str]:
        """加载现有力量类型"""
        config_path = self._get_config_path()

        if not config_path.exists():
            # 使用默认关键词映射
            return set(self.POWER_KEYWORDS.keys())

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        return set(config.get("power_types", {}).keys())

    def _get_config_path(self) -> Path:
        """获取配置文件路径"""
        from .type_discoverer import CONFIG_DIMENSIONS_DIR

        return CONFIG_DIMENSIONS_DIR / "power_types.json"

    def _get_type_category(self) -> str:
        """获取类型类别"""
        return "power"

    def _match_existing(self, text: str) -> bool:
        """匹配现有力量类型"""
        # 检查是否包含任何现有力量体系关键词
        for power_type, keywords in self.POWER_KEYWORDS.items():
            if power_type in self.existing_types:
                match_count = sum(1 for kw in keywords if kw in text)
                if match_count >= 2:
                    return True

        # 检查代价关键词（可能是力量体系描述）
        cost_count = sum(1 for kw in self.COST_KEYWORDS if kw in text)
        recovery_count = sum(1 for kw in self.RECOVERY_KEYWORDS if kw in text)

        if cost_count >= 2 or recovery_count >= 2:
            return True

        return False

    def _generate_type_name(self, kw1: str, kw2: str) -> str:
        """根据关键词生成力量类型名称"""
        # 力量类型命名规则
        name_patterns = {
            # 常见力量体系关键词组合
            ("血脉", "觉醒"): "血脉力量",
            ("灵魂", "力量"): "灵魂力量",
            ("命运", "掌控"): "命运力量",
            ("因果", "法则"): "因果力量",
            ("时间", "控制"): "时间力量",
            ("空间", "撕裂"): "空间力量",
            ("暗影", "潜行"): "暗影力量",
            ("光明", "净化"): "光明力量",
            ("元素", "掌控"): "元素力量",
        }

        pair = tuple(sorted([kw1, kw2]))
        if pair in name_patterns:
            return name_patterns[pair]

        # 自动生成名称
        power_suffixes = ["力量", "之力", "体系", "能量"]
        for suffix in power_suffixes:
            if kw1.endswith(suffix) or kw2.endswith(suffix):
                return f"{kw1}{kw2}"

        # 默认命名
        if any(
            w in kw1 + kw2
            for w in ["血", "魂", "命", "因", "果", "时", "空", "暗", "光", "元"]
        ):
            return f"{kw1}{kw2}力量"

        return f"{kw1}{kw2}体系"

    def discover_power_types(self, novels: List[str]) -> List[DiscoveredType]:
        """
        从小说中发现新的力量体系类型

        Args:
            novels: 小说文本列表

        Returns:
            发现的新力量类型列表
        """
        # 收集未匹配片段
        for i, novel in enumerate(novels):
            # 按段落分割
            paragraphs = re.split(r"\n\s*\n", novel)
            paragraphs = [
                p.strip() for p in paragraphs if 100 <= len(p.strip()) <= 3000
            ]

            self.collect_unmatched(paragraphs, f"小说_{i}")

        # 发现新类型
        return self.discover_types()

    def _extract_power_features(self, text: str) -> Dict:
        """从文本中提取力量特征"""
        features = {
            "skills": [],
            "costs": {"身体代价": [], "精神代价": [], "能量代价": [], "其他代价": []},
            "recovery": [],
        }

        # 提取技能关键词（动词+名词组合）
        skill_patterns = [
            r"施展[了](\w+)",
            r"释放[了](\w+)",
            r"激发[了](\w+)",
            r"催动[了](\w+)",
            r"运转[了](\w+)",
            r"召唤[了](\w+)",
        ]

        for pattern in skill_patterns:
            matches = re.findall(pattern, text)
            features["skills"].extend(matches[:5])

        # 提取代价关键词
        cost_keywords = {
            "身体代价": ["鲜血", "剧痛", "苍白", "虚弱", "崩溃", "麻木"],
            "精神代价": ["涣散", "分裂", "萎靡", "模糊", "创伤"],
            "能量代价": ["耗尽", "枯竭", "透支", "空虚"],
            "其他代价": ["反噬", "过载", "损坏", "警告"],
        }

        for cost_type, keywords in cost_keywords.items():
            for kw in keywords:
                if kw in text:
                    features["costs"][cost_type].append(kw)

        # 提取恢复关键词
        recovery_keywords = ["恢复", "调息", "打坐", "冥想", "充能", "丹药", "药剂"]
        for kw in recovery_keywords:
            if kw in text:
                features["recovery"].append(kw)

        return features

    def sync_to_config(self, types: Optional[List[DiscoveredType]] = None) -> int:
        """
        同步到 power_types.json

        同步时会自动填充力量体系的完整结构：
        - skills: 技能列表
        - costs: 各类代价
        - recovery: 恢复方式
        """
        types = types or [t for t in self.discovered_types if t.status == "approved"]
        if not types:
            return 0

        config_path = self._get_config_path()

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        power_types = config.get("power_types", {})

        synced = 0
        for type_obj in types:
            if type_obj.name in self.existing_types:
                continue

            # 从样本中提取力量特征
            sample_features = self._extract_power_features(
                type_obj.keywords[0] if type_obj.keywords else ""
            )

            # 构建完整的力量类型配置
            power_types[type_obj.name] = {
                "description": type_obj.description or f"自动发现的力量体系",
                "skills": type_obj.keywords[:10],
                "costs": sample_features["costs"],
                "recovery": sample_features["recovery"],
                "auto_discovered": True,
                "discovered_at": type_obj.created_at,
            }

            self.existing_types.add(type_obj.name)
            synced += 1

        # 更新配置
        config["power_types"] = power_types
        config["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return synced
