# -*- coding: utf-8 -*-
"""
作者风格指纹提取器 v2.0

改进版：提取真正的写作风格特征
- 句长分布
- 用词偏好
- 句式特征
- 修辞手法
"""

import re
import json
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass

from base_extractor import BaseExtractor
from config import EXTRACTION_DIMENSIONS


@dataclass
class StyleFingerprint:
    author: str
    features: Dict[str, float]
    samples: List[str]


class AuthorStyleExtractor(BaseExtractor):
    """作者风格指纹提取器 v2.0"""

    # 风格特征词
    DESCRIPTIVE_WORDS = ["仿佛", "似乎", "宛如", "如同", "好似", "宛若", "恰似"]
    EMOTION_WORDS = ["心中", "心头", "心间", "内心", "心底", "心下"]
    ACTION_INTENSIFIERS = ["猛然", "骤然", "突然", "陡然", "倏然", "蓦然"]

    # 句式标记
    Rhetorical_PATTERNS = {
        "比喻": r"(仿佛|似乎|宛如|如同|好似|宛若|恰似)[^。！？]{5,30}",
        "排比": r"([^。！？]{10,30})[,，]\s*([^。！？]{10,30})[,，]\s*([^。！？]{10,30})",
        "夸张": r"(极其|非常|十分|格外|特别|相当)[^。！？]{5,20}",
        "设问": r"[^。！？]{10,30}[？?]",
        "反问": r"(难道|怎会|怎能|怎敢)[^。！？]{5,30}[？?]",
    }

    def __init__(self):
        super().__init__("author_style")
        self.chinese_punctuation = "，。！？；："

    def _segment_sentences(self, content: str) -> List[str]:
        """分割句子"""
        sentences = re.split(r"[。！？]", content)
        return [s.strip() for s in sentences if s.strip()]

    def _count_chinese_chars(self, text: str) -> int:
        """统计汉字数"""
        return len(re.findall(r"[\u4e00-\u9fa5]", text))

    def _analyze_sentence_length(self, sentences: List[str]) -> Dict[str, float]:
        """分析句长分布"""
        lengths = [len(s) for s in sentences]
        if not lengths:
            return {}

        avg = sum(lengths) / len(lengths)
        variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)

        # 按长度区间统计
        short_ratio = sum(1 for l in lengths if l < 20) / len(lengths) * 100
        medium_ratio = sum(1 for l in lengths if 20 <= l < 50) / len(lengths) * 100
        long_ratio = sum(1 for l in lengths if l >= 50) / len(lengths) * 100

        return {
            "avg_sentence_length": round(avg, 1),
            "variance": round(variance, 1),
            "short_ratio": round(short_ratio, 1),
            "medium_ratio": round(medium_ratio, 1),
            "long_ratio": round(long_ratio, 1),
        }

    def _analyze_word_preference(self, content: str) -> Dict[str, Any]:
        """分析用词偏好"""
        # 统计风格词频次
        desc_count = sum(content.count(w) for w in self.DESCRIPTIVE_WORDS)
        emotion_count = sum(content.count(w) for w in self.EMOTION_WORDS)
        action_count = sum(content.count(w) for w in self.ACTION_INTENSIFIERS)

        # 高频2-4字词
        words = re.findall(r"[\u4e00-\u9fa5]{2,4}", content)
        word_freq = Counter(words)

        # 排除常用词
        common_words = {
            "的话",
            "只是",
            "一个",
            "不是",
            "没有",
            "这样",
            "什么",
            "怎么",
            "但是",
            "而且",
            "因为",
            "所以",
            "虽然",
            "如果",
            "还是",
            "已经",
            "正在",
            "可以",
            "可能",
            "应该",
            "必须",
        }
        top_words = [
            w for w, c in word_freq.most_common(50) if w not in common_words and c > 10
        ][:20]

        return {
            "descriptive_word_count": desc_count,
            "emotion_word_count": emotion_count,
            "action_intensifier_count": action_count,
            "top_words": top_words,
        }

    def _analyze_rhetoric(self, content: str) -> Dict[str, int]:
        """分析修辞手法使用"""
        rhetoric_counts = {}

        for rhetoric_type, pattern in self.Rhetorical_PATTERNS.items():
            matches = re.findall(pattern, content)
            rhetoric_counts[rhetoric_type] = len(matches)

        return rhetoric_counts

    def _identify_style_pattern(self, features: Dict) -> str:
        """识别风格模式"""
        sent_features = features.get("sentence_length", {})
        word_features = features.get("word_preference", {})
        rhetoric = features.get("rhetoric", {})

        # 基于特征判断风格
        avg_len = sent_features.get("avg_sentence_length", 30)
        desc_count = word_features.get("descriptive_word_count", 0)

        if avg_len > 40 and desc_count > 20:
            return "描写型 - 善用长句和比喻"
        elif avg_len < 20:
            return "简洁型 - 短句为主，节奏快"
        elif rhetoric.get("反问", 0) > 10:
            return "对话型 - 多用设问反问"
        elif sent_features.get("long_ratio", 0) > 30:
            return "叙事型 - 段落厚重"
        else:
            return "平衡型 - 中等句长"

    def extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]:
        """从小说提取风格特征"""
        sentences = self._segment_sentences(content)

        if len(sentences) < 100:
            return []

        # 分析各项特征
        sent_length = self._analyze_sentence_length(sentences)
        word_pref = self._analyze_word_preference(content)
        rhetoric = self._analyze_rhetoric(content)

        # 整合特征
        features = {
            "sentence_length": sent_length,
            "word_preference": word_pref,
            "rhetoric": rhetoric,
            "content_length": self._count_chinese_chars(content),
            "sentence_count": len(sentences),
        }

        # 识别风格模式
        style_pattern = self._identify_style_pattern(features)

        # 提取典型句子示例
        sample_sentences = sentences[:10] if len(sentences) >= 10 else sentences

        return [
            {
                "novel_id": novel_id,
                "novel_path": str(novel_path),
                "features": features,
                "style_pattern": style_pattern,
                "sample_sentences": sample_sentences,
            }
        ]

    def process_extracted(self, items: List[dict]) -> List[dict]:
        """处理提取结果 - 按风格模式聚合"""
        # 按风格模式分组
        style_groups = defaultdict(list)

        for item in items:
            pattern = item.get("style_pattern", "平衡型")
            style_groups[pattern].append(item)

        # 整合结果
        results = []
        for style_pattern, novels in style_groups.items():
            # 聚合特征
            avg_sentence_length = sum(
                n.get("features", {})
                .get("sentence_length", {})
                .get("avg_sentence_length", 0)
                for n in novels
            ) / len(novels)

            # 聚合修辞统计
            rhetoric_sum = defaultdict(int)
            for n in novels:
                for rhetoric_type, count in (
                    n.get("features", {}).get("rhetoric", {}).items()
                ):
                    rhetoric_sum[rhetoric_type] += count

            results.append(
                {
                    "style_pattern": style_pattern,
                    "novel_count": len(novels),
                    "avg_sentence_length": round(avg_sentence_length, 1),
                    "rhetoric_usage": dict(rhetoric_sum),
                    "sample_novels": [n.get("novel_id", "") for n in novels[:5]],
                    "description": self._get_style_description(style_pattern),
                }
            )

        return results

    def _get_style_description(self, style_pattern: str) -> str:
        """获取风格描述"""
        descriptions = {
            "描写型 - 善用长句和比喻": "长句铺陈，比喻丰富，适合场景描写和氛围营造",
            "简洁型 - 短句为主，节奏快": "短句为主，节奏明快，适合战斗和紧张情节",
            "对话型 - 多用设问反问": "对话生动，设问反问多，适合人物互动",
            "叙事型 - 段落厚重": "叙事详实，段落厚重，适合宏大背景展开",
            "平衡型 - 中等句长": "句长适中，节奏平衡，适合多种场景",
        }
        return descriptions.get(style_pattern, "综合风格")


def extract_author_styles(limit: int = None):
    extractor = AuthorStyleExtractor()
    return extractor.run(limit=limit)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        print("Status: OK")
    else:
        extract_author_styles(limit=args.limit)
