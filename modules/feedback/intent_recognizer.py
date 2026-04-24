# -*- coding: utf-8 -*-
"""
意图识别器 - 识别用户修改/重写意图
"""

import re
from typing import Dict, Any, List, Tuple
from .types import IntentResult, ModificationLevel, RewriteMode


class IntentRecognizer:
    """意图识别器"""

    # 重写关键词
    REWRITE_KEYWORDS = [
        "重写",
        "重新写",
        "再写一遍",
        "完全重新",
        "推翻重写",
        "从头写",
        "重新创作",
        "重做",
    ]

    # 修改层级关键词映射
    LEVEL_KEYWORDS = {
        ModificationLevel.WORD_POLISH: [
            "润色",
            "修改表达",
            "改写",
            "太AI味",
            "AI感",
            "不自然",
            "换个说法",
            "改一下",
            "调整一下",
            "优化一下",
        ],
        ModificationLevel.CONTENT_TWEAK: [
            "细节",
            "具体",
            "补充",
            "扩展",
            "删减",
            "调整细节",
            "加一点",
            "减少一点",
            "改细节",
        ],
        ModificationLevel.PLOT_CHANGE: [
            "剧情",
            "情节",
            "结局",
            "改结局",
            "改剧情",
            "改情节",
            "伏笔",
            "反转",
            "事件",
            "改变发展",
        ],
        ModificationLevel.SETTING_CHANGE: [
            "设定",
            "世界观",
            "人物设定",
            "势力",
            "血脉",
            "力量体系",
            "改设定",
            "设定调整",
            "修改设定",
        ],
    }

    # 章节匹配模式
    CHAPTER_PATTERN = r"第[一二三四五六七八九十百千万\d]+章"

    def recognize(
        self, user_input: str, context: Dict[str, Any] = None
    ) -> IntentResult:
        """
        识别用户意图

        Args:
            user_input: 用户输入文本
            context: 当前上下文（可选）

        Returns:
            IntentResult: 意图识别结果
        """
        context = context or {}

        # 1. 检测是否是重写请求
        is_rewrite = self._detect_rewrite(user_input)

        # 2. 检测修改层级
        modification_level = self._detect_modification_level(user_input)

        # 3. 检测重写模式
        rewrite_mode = None
        if is_rewrite:
            rewrite_mode = self._detect_rewrite_mode(user_input)

        # 4. 提取目标章节
        target_chapter = self._extract_chapter(user_input)

        # 5. 提取关键词
        keywords = self._extract_keywords(user_input)

        # 6. 计算置信度
        confidence = self._calculate_confidence(
            user_input, is_rewrite, modification_level, rewrite_mode
        )

        # 7. 确定路由
        routing = self._determine_routing(is_rewrite, modification_level)

        return IntentResult(
            is_rewrite=is_rewrite,
            modification_level=modification_level,
            rewrite_mode=rewrite_mode,
            confidence=confidence,
            routing=routing,
            target_chapter=target_chapter,
            keywords=keywords,
        )

    def _detect_rewrite(self, user_input: str) -> bool:
        """检测是否是重写请求"""
        for keyword in self.REWRITE_KEYWORDS:
            if keyword in user_input:
                return True
        return False

    def _detect_modification_level(self, user_input: str) -> ModificationLevel:
        """检测修改层级"""
        scores = {level: 0 for level in ModificationLevel}

        for level, keywords in self.LEVEL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in user_input:
                    scores[level] += 1

        # 返回得分最高的层级，默认为文字润色
        max_level = ModificationLevel.WORD_POLISH
        max_score = 0

        for level, score in scores.items():
            if score > max_score:
                max_score = score
                max_level = level

        return max_level

    def _detect_rewrite_mode(self, user_input: str) -> RewriteMode:
        """检测重写模式"""
        # 模式C：完全重新创作
        complete_keywords = ["完全重新", "从头", "推翻", "彻底"]
        for keyword in complete_keywords:
            if keyword in user_input:
                return RewriteMode.FULL_RECREATE

        # 模式D：参考原稿
        reference_keywords = ["参考", "保留好的", "改掉不好的"]
        for keyword in reference_keywords:
            if keyword in user_input:
                return RewriteMode.REFERENCE_BASED

        # 模式B：剧情调整
        adjust_keywords = ["调整", "修改剧情", "改剧情"]
        for keyword in adjust_keywords:
            if keyword in user_input:
                return RewriteMode.PLOT_ADJUST

        # 模式A：剧情保留（默认）
        return RewriteMode.PLOT_PRESERVE

    def _extract_chapter(self, user_input: str) -> str:
        """提取目标章节"""
        match = re.search(self.CHAPTER_PATTERN, user_input)
        if match:
            return match.group(0)
        return None

    def _extract_keywords(self, user_input: str) -> List[str]:
        """提取关键词"""
        keywords = []

        # 常见修改关键词
        common_keywords = [
            "AI味",
            "润色",
            "战斗",
            "代价",
            "伏笔",
            "人物",
            "情感",
            "氛围",
            "节奏",
            "开头",
            "结尾",
            "过渡",
            "冲突",
        ]

        for keyword in common_keywords:
            if keyword in user_input:
                keywords.append(keyword)

        return keywords

    def _calculate_confidence(
        self,
        user_input: str,
        is_rewrite: bool,
        modification_level: ModificationLevel,
        rewrite_mode: RewriteMode,
    ) -> float:
        """计算置信度"""
        confidence = 0.5  # 基础置信度

        # 有关键词匹配增加置信度
        if self._extract_keywords(user_input):
            confidence += 0.1

        # 有章节信息增加置信度
        if self._extract_chapter(user_input):
            confidence += 0.1

        # 重写意图明确增加置信度
        if is_rewrite and rewrite_mode:
            confidence += 0.15

        # 修改层级明确增加置信度
        if modification_level != ModificationLevel.WORD_POLISH:
            confidence += 0.1

        return min(confidence, 1.0)

    def _determine_routing(
        self, is_rewrite: bool, modification_level: ModificationLevel
    ) -> str:
        """确定路由目标"""
        if is_rewrite:
            return "rewrite_handler"

        if modification_level == ModificationLevel.SETTING_CHANGE:
            return "setting_handler"
        elif modification_level == ModificationLevel.PLOT_CHANGE:
            return "plot_handler"
        elif modification_level == ModificationLevel.CONTENT_TWEAK:
            return "content_handler"
        else:
            return "polish_handler"


def recognize_intent(user_input: str, context: Dict[str, Any] = None) -> IntentResult:
    """
    识别用户意图（便捷函数）

    Args:
        user_input: 用户输入
        context: 当前上下文

    Returns:
        意图识别结果
    """
    recognizer = IntentRecognizer()
    return recognizer.recognize(user_input, context)
