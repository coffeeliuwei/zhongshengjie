#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技法类型发现器
=============

从案例中自动发现新的技法类型。

例如：发现"时间控制"、"空间撕裂"、"灵魂操控"等新技法。

配置文件：config/dimensions/technique_types.json
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional

from .type_discoverer import TypeDiscoverer, DiscoveredType


class TechniqueDiscoverer(TypeDiscoverer):
    """技法类型发现器"""

    # 技法维度映射（用于识别现有类型）
    TECHNIQUE_DIMENSIONS = {
        "开篇维度": ["开篇钩子", "世界观初现", "人物出场", "悬念设置"],
        "人物维度": ["人物出场", "性格刻画", "心理描写", "对话技巧", "人物成长"],
        "剧情维度": ["伏笔设计", "悬念布局", "反转策划", "节奏控制", "冲突升级"],
        "战斗冲突维度": ["功法体系", "战斗节奏", "力量代价", "胜利模式", "失败描写"],
        "氛围意境维度": ["环境描写", "氛围渲染", "诗意语言", "美学构建"],
        "情感维度": ["情感层次", "心理描写", "情感爆发", "情感转折"],
        "设定维度": ["力量体系", "势力架构", "规则设计", "历史背景"],
        "节奏维度": ["快慢节奏", "张弛搭配", "高潮设计", "余韵营造"],
        "悬念维度": ["悬念设置", "悬念延续", "悬念揭示", "信息控制"],
        "元维度": ["技法组合", "场景适配", "风格统一", "长篇一致性"],
        "成长维度": ["成长弧线", "蜕变描写", "觉悟时刻", "代价收获"],
    }

    # 技法关键词模式
    TECHNIQUE_PATTERNS = {
        "时间控制": ["时间", "暂停", "倒流", "加速", "减缓", "冻结"],
        "空间撕裂": ["空间", "撕裂", "破碎", "扭曲", "折叠", "传送"],
        "灵魂操控": ["灵魂", "操控", "控制", "侵蚀", "融合", "分离"],
        "命运干涉": ["命运", "干涉", "改变", "预知", "逆转", "因果"],
        "元素操控": ["元素", "火", "水", "风", "土", "雷", "冰"],
        "精神控制": ["精神", "控制", "操控", "催眠", "迷惑", "幻觉"],
        "肉体强化": ["肉体", "强化", "改造", "增强", "进化", "突破"],
        "能量操控": ["能量", "操控", "吸收", "转化", "释放", "凝聚"],
    }

    # 技法应用场景
    TECHNIQUE_SCENES = {
        "战斗场景": ["攻击", "防御", "反击", "闪避", "压制", "突破"],
        "打脸场景": ["嘲讽", "震惊", "震撼", "不可能", "废物", "跪下"],
        "高潮场景": ["决战", "爆发", "生死", "极限", "巅峰", "终极"],
        "人物出场": ["首次", "登场", "亮相", "出场", "介绍", "刻画"],
        "情感场景": ["感动", "震撼", "悲伤", "喜悦", "愤怒", "复杂"],
        "心理场景": ["心中", "内心", "思绪", "纠结", "挣扎", "沉思"],
        "成长蜕变": ["蜕变", "成长", "觉悟", "转变", "突破", "进化"],
        "悬念场景": ["谜团", "未知", "揭示", "真相", "意外", "反转"],
        "伏笔设置": ["暗示", "伏笔", "铺垫", "预兆", "隐喻", "线索"],
        "伏笔回收": ["呼应", "揭示", "回收", "答案", "揭晓", "解释"],
        "转折场景": ["突然", "意外", "反转", "转折", "不料", "没想到"],
        "阴谋揭露": ["阴谋", "揭露", "真相", "背叛", "诡计", "秘密"],
        "对话场景": ["说道", "问道", "答道", "笑道", "沉声道", "交谈"],
        "社交场景": ["社交", "交往", "关系", "人际", "权力", "势力"],
        "开篇场景": ["第一章", "开篇", "序章", "序幕", "开始", "开端"],
        "势力登场": ["势力", "登场", "组织", "门派", "集团", "家族"],
        "环境场景": ["山脉", "森林", "宫殿", "城池", "风景", "景色"],
        "修炼突破": ["突破", "境界", "修炼", "功法", "感悟", "进阶"],
        "资源获取": ["资源", "获取", "得到", "获得", "收获", "宝物"],
        "探索发现": ["探索", "发现", "寻找", "搜索", "冒险", "未知"],
        "情报揭示": ["情报", "揭示", "信息", "秘密", "消息", "线索"],
        "危机降临": ["危机", "降临", "危险", "威胁", "灾难", "紧迫"],
        "冲突升级": ["冲突", "升级", "矛盾", "对抗", "争执", "恶化"],
        "团队组建": ["团队", "组建", "成员", "合作", "同盟", "伙伴"],
        "反派出场": ["反派", "出场", "敌人", "对手", "恶人", "坏人"],
        "恢复休养": ["恢复", "休养", "休息", "疗伤", "调整", "喘息"],
        "回忆场景": ["回忆", "往事", "曾经", "过去", "记忆", "回想"],
        "结尾场景": ["结尾", "结束", "收尾", "落幕", "终章", "尾声"],
    }

    def _load_existing_types(self) -> Set[str]:
        """加载现有技法类型"""
        config_path = self._get_config_path()

        if not config_path.exists():
            # 使用默认维度映射
            return set(self.TECHNIQUE_DIMENSIONS.keys())

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        return set(config.get("technique_types", {}).keys())

    def _get_config_path(self) -> Path:
        """获取配置文件路径"""
        from .type_discoverer import CONFIG_DIMENSIONS_DIR

        return CONFIG_DIMENSIONS_DIR / "technique_types.json"

    def _get_type_category(self) -> str:
        """获取类型类别"""
        return "technique"

    def _match_existing(self, text: str) -> bool:
        """匹配现有技法类型"""
        # 检查是否包含任何现有技法维度关键词
        for dimension, techniques in self.TECHNIQUE_DIMENSIONS.items():
            if dimension in self.existing_types:
                match_count = sum(1 for tech in techniques if tech in text)
                if match_count >= 2:
                    return True

        # 检查技法关键词模式
        for pattern_type, keywords in self.TECHNIQUE_PATTERNS.items():
            match_count = sum(1 for kw in keywords if kw in text)
            if match_count >= 3:
                return True

        # 检查技法应用场景
        for scene, keywords in self.TECHNIQUE_SCENES.items():
            match_count = sum(1 for kw in keywords if kw in text)
            if match_count >= 2:
                return True

        return False

    def _generate_type_name(self, kw1: str, kw2: str) -> str:
        """根据关键词生成技法类型名称"""
        # 技法类型命名规则
        name_patterns = {
            # 常见技法关键词组合
            ("时间", "控制"): "时间控制技法",
            ("空间", "撕裂"): "空间撕裂技法",
            ("灵魂", "操控"): "灵魂操控技法",
            ("命运", "干涉"): "命运干涉技法",
            ("元素", "操控"): "元素操控技法",
            ("精神", "控制"): "精神控制技法",
            ("肉体", "强化"): "肉体强化技法",
            ("能量", "操控"): "能量操控技法",
        }

        pair = tuple(sorted([kw1, kw2]))
        if pair in name_patterns:
            return name_patterns[pair]

        # 自动生成名称
        technique_suffixes = ["技法", "技巧", "方法", "能力"]
        for suffix in technique_suffixes:
            if kw1.endswith(suffix) or kw2.endswith(suffix):
                return f"{kw1}{kw2}"

        # 默认命名
        if any(
            w in kw1 + kw2
            for w in ["时", "空", "魂", "命", "元", "精", "肉", "能", "素"]
        ):
            return f"{kw1}{kw2}技法"

        return f"{kw1}{kw2}技巧"

    def discover_techniques(self, cases: List[str]) -> List[DiscoveredType]:
        """
        从案例中发现新的技法类型

        Args:
            cases: 案例文本列表

        Returns:
            发现的新技法类型列表
        """
        # 收集未匹配片段
        for i, case in enumerate(cases):
            # 按段落分割
            paragraphs = re.split(r"\n\s*\n", case)
            paragraphs = [
                p.strip() for p in paragraphs if 100 <= len(p.strip()) <= 3000
            ]

            self.collect_unmatched(paragraphs, f"案例_{i}")

        # 发现新类型
        return self.discover_types()

    def _extract_technique_features(self, text: str) -> Dict:
        """从文本中提取技法特征"""
        features = {
            "dimension": "",
            "category": "",
            "techniques": [],
        }

        # 确定技法维度
        for dimension, keywords in self.TECHNIQUE_PATTERNS.items():
            if any(kw in text for kw in keywords):
                features["dimension"] = dimension
                break

        # 如果没有匹配到维度，根据关键词推断
        if not features["dimension"]:
            for kw in ["时间", "空间", "灵魂", "命运", "元素", "精神", "肉体", "能量"]:
                if kw in text:
                    features["dimension"] = f"{kw}操控"
                    break

        # 确定技法类别
        category_keywords = {
            "结构技法": ["伏笔", "悬念", "节奏", "转折", "反转"],
            "人物技法": ["心理", "性格", "成长", "蜕变"],
            "场景技法": ["战斗", "氛围", "环境", "情感"],
            "描写技法": ["渲染", "描写", "刻画", "营造"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in text for kw in keywords):
                features["category"] = category
                break

        if not features["category"]:
            features["category"] = "场景技法"

        # 提取技法关键词
        technique_keywords = []
        for pattern_type, keywords in self.TECHNIQUE_PATTERNS.items():
            for kw in keywords:
                if kw in text:
                    technique_keywords.append(kw)

        features["techniques"] = technique_keywords[:5]

        return features

    def sync_to_config(self, types: Optional[List[DiscoveredType]] = None) -> int:
        """
        同步到 technique_types.json

        同步时会自动填充技法的完整结构：
        - dimension: 技法维度
        - category: 技法类别
        - techniques: 具体技法列表
        """
        types = types or [t for t in self.discovered_types if t.status == "approved"]
        if not types:
            return 0

        config_path = self._get_config_path()

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        technique_types = config.get("technique_types", {})

        synced = 0
        for type_obj in types:
            if type_obj.name in self.existing_types:
                continue

            # 从样本中提取技法特征
            sample_features = self._extract_technique_features(
                type_obj.keywords[0] if type_obj.keywords else ""
            )

            # 构建完整的技法类型配置
            technique_types[type_obj.name] = {
                "dimension": sample_features["dimension"] or type_obj.name,
                "description": type_obj.description or f"自动发现的技法类型",
                "category": sample_features["category"] or "场景技法",
                "techniques": sample_features["techniques"]
                if sample_features["techniques"]
                else type_obj.keywords[:5],
                "auto_discovered": True,
                "discovered_at": type_obj.created_at,
            }

            self.existing_types.add(type_obj.name)
            synced += 1

        # 更新配置
        config["technique_types"] = technique_types
        config["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return synced
