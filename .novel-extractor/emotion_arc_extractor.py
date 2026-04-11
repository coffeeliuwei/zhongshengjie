"""
情感曲线提取器

从小说中提取情感变化曲线，识别6种基本叙事形状：
1. rags_to_riches - 上升型
2. tragedy - 悲剧型
3. man_in_a_hole - V型
4. icarus - 倒V型
5. cinderella - N型
6. oedipus - W型

用于学习叙事节奏控制
"""

import re
import json
import math
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass

from base_extractor import BaseExtractor
from config import EXTRACTION_DIMENSIONS


@dataclass
class EmotionPoint:
    """情感数据点"""

    position: float  # 位置 (0-1)
    score: float  # 情感得分 (-1到1)
    text: str = ""  # 原文片段


class EmotionArcExtractor(BaseExtractor):
    """情感曲线提取器"""

    def __init__(self):
        super().__init__("emotion_arc")

        # 情感词汇表（简化版，实际应用可用情感词典）
        self.positive_words = [
            "喜",
            "乐",
            "欢",
            "笑",
            "幸福",
            "快乐",
            "开心",
            "兴奋",
            "胜利",
            "成功",
            "希望",
            "光明",
            "温暖",
            "爱",
            "美",
            "激动",
            "欣慰",
            "满足",
            "骄傲",
            "自豪",
            "感动",
        ]

        self.negative_words = [
            "悲",
            "哀",
            "痛",
            "哭",
            "泪",
            "苦",
            "绝望",
            "痛苦",
            "失败",
            "死亡",
            "黑暗",
            "寒冷",
            "恨",
            "丑",
            "恐惧",
            "愤怒",
            "仇恨",
            "委屈",
            "悔恨",
            "失落",
            "悲伤",
        ]

        # 程度副词
        self.intensifiers = {
            "很": 1.3,
            "非常": 1.5,
            "极其": 1.8,
            "十分": 1.4,
            "稍微": 0.7,
            "略微": 0.6,
            "一点": 0.5,
            "太": 1.6,
            "特别": 1.5,
            "相当": 1.3,
        }

        # 否定词
        self.negators = ["不", "没", "无", "非", "未"]

    def _calculate_emotion_score(self, text: str) -> float:
        """计算文本情感得分"""
        score = 0.0

        # 正面词
        for word in self.positive_words:
            count = text.count(word)
            # 检查程度副词
            for intensifier, mult in self.intensifiers.items():
                if intensifier + word in text:
                    score += mult
                    count -= 1
            score += count

        # 负面词
        for word in self.negative_words:
            count = text.count(word)
            for intensifier, mult in self.intensifiers.items():
                if intensifier + word in text:
                    score -= mult
                    count -= 1
            score -= count

        # 归一化到 -1 到 1
        text_len = len(text) / 1000  # 每千字
        if text_len > 0:
            score = max(-1, min(1, score / text_len))

        return score

    def _segment_text(self, content: str, num_segments: int = 20) -> List[str]:
        """将文本分成多个片段"""
        # 按章节分割优先
        chapter_pattern = r"第[一二三四五六七八九十百千万零\d]+[章节]"
        chapters = re.split(chapter_pattern, content)

        if len(chapters) >= num_segments // 2:
            # 用章节作为分割
            segments = chapters[: num_segments * 2]
        else:
            # 按长度均匀分割
            segment_len = len(content) // num_segments
            segments = [
                content[i * segment_len : (i + 1) * segment_len]
                for i in range(num_segments)
            ]

        return [s.strip() for s in segments if s.strip()]

    def _extract_arc(self, content: str) -> List[EmotionPoint]:
        """提取情感曲线"""
        segments = self._segment_text(content)

        if not segments:
            return []

        arc = []
        total = len(segments)

        for i, segment in enumerate(segments):
            score = self._calculate_emotion_score(segment)
            position = i / total

            arc.append(
                EmotionPoint(
                    position=position,
                    score=score,
                    text=segment[:100] if segment else "",
                )
            )

        return arc

    def _classify_arc_type(self, arc: List[EmotionPoint]) -> str:
        """分类情感曲线类型"""
        if len(arc) < 5:
            return "unknown"

        scores = [p.score for p in arc]

        # 计算关键指标
        start_score = sum(scores[:3]) / 3  # 开始均值
        end_score = sum(scores[-3:]) / 3  # 结束均值
        mid_score = (
            sum(scores[len(scores) // 2 - 1 : len(scores) // 2 + 2]) / 3
        )  # 中间均值
        min_score = min(scores)
        max_score = max(scores)
        min_pos = scores.index(min_score) / len(scores)
        max_pos = scores.index(max_score) / len(scores)

        # 分类规则
        # 上升型：低开高走
        if start_score < -0.2 and end_score > 0.2 and min_pos < 0.3:
            return "rags_to_riches"

        # 悲剧型：高开低走
        if start_score > 0.2 and end_score < -0.2 and max_pos < 0.3:
            return "tragedy"

        # V型：先降后升
        if min_pos > 0.3 and min_pos < 0.7:
            if min_score < start_score and min_score < end_score:
                if end_score > start_score:
                    return "man_in_a_hole"

        # 倒V型：先升后降
        if max_pos > 0.3 and max_pos < 0.7:
            if max_score > start_score and max_score > end_score:
                if end_score < start_score:
                    return "icarus"

        # N型：升降升
        peak_count = sum(
            1
            for i in range(1, len(scores) - 1)
            if scores[i] > scores[i - 1] and scores[i] > scores[i + 1]
        )
        valley_count = sum(
            1
            for i in range(1, len(scores) - 1)
            if scores[i] < scores[i - 1] and scores[i] < scores[i + 1]
        )

        if peak_count >= 2 and valley_count >= 1:
            if end_score > 0:
                return "cinderella"
            else:
                return "oedipus"

        # 默认
        if end_score > start_score:
            return "rags_to_riches"
        elif end_score < start_score:
            return "tragedy"
        else:
            return "unknown"

    def _calculate_arc_statistics(self, arc: List[EmotionPoint]) -> Dict[str, Any]:
        """计算曲线统计特征"""
        if not arc:
            return {}

        scores = [p.score for p in arc]

        return {
            "avg_score": round(sum(scores) / len(scores), 3),
            "max_score": round(max(scores), 3),
            "min_score": round(min(scores), 3),
            "variance": round(
                sum((s - sum(scores) / len(scores)) ** 2 for s in scores) / len(scores),
                3,
            ),
            "trend": "上升"
            if scores[-1] > scores[0]
            else "下降"
            if scores[-1] < scores[0]
            else "平稳",
            "turning_points": sum(
                1
                for i in range(1, len(scores) - 1)
                if (scores[i] > scores[i - 1]) != (scores[i] > scores[i + 1])
            ),
        }

    def extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]:
        """从小说提取情感曲线"""

        if len(content) < 10000:  # 太短，跳过
            return []

        # 提取曲线
        arc = self._extract_arc(content)

        if not arc:
            return []

        # 分类
        arc_type = self._classify_arc_type(arc)

        # 统计
        stats = self._calculate_arc_statistics(arc)

        return [
            {
                "novel_id": novel_id,
                "arc_type": arc_type,
                "arc_points": [(p.position, p.score) for p in arc],
                "statistics": stats,
                "content_length": len(content),
            }
        ]

    def process_extracted(self, items: List[dict]) -> List[dict]:
        """处理提取结果 - 按曲线类型聚合"""
        # 按类型分组
        type_groups = defaultdict(list)

        for item in items:
            arc_type = item.get("arc_type", "unknown")
            type_groups[arc_type].append(item)

        # 整合结果
        results = []
        for arc_type, arcs in type_groups.items():
            # 聚合统计
            avg_variance = sum(
                a.get("statistics", {}).get("variance", 0) for a in arcs
            ) / len(arcs)
            avg_turning_points = sum(
                a.get("statistics", {}).get("turning_points", 0) for a in arcs
            ) / len(arcs)

            # 典型曲线
            typical_arc = max(
                arcs, key=lambda a: a.get("statistics", {}).get("variance", 0)
            )

            results.append(
                {
                    "arc_type": arc_type,
                    "novel_count": len(arcs),
                    "avg_variance": round(avg_variance, 3),
                    "avg_turning_points": round(avg_turning_points, 1),
                    "typical_arc": typical_arc.get("arc_points", []),
                    "description": self._get_arc_description(arc_type),
                }
            )

        return results

    def _get_arc_description(self, arc_type: str) -> str:
        """获取曲线类型描述"""
        descriptions = {
            "rags_to_riches": "上升型：低谷开局，逐步攀升至高点",
            "tragedy": "悲剧型：高点开局，逐步跌落至低谷",
            "man_in_a_hole": "V型：从高点跌落，后回升",
            "icarus": "倒V型：从低点上升，后跌落",
            "cinderella": "N型：升降升的波浪形",
            "oedipus": "W型：多次起伏的复杂曲线",
            "unknown": "未分类曲线",
        }
        return descriptions.get(arc_type, "未知类型")


def extract_emotion_arcs(limit: int = None):
    """提取情感曲线"""
    extractor = EmotionArcExtractor()
    return extractor.run(limit=limit)


if __name__ == "__main__":
    import argparse
    from dataclasses import asdict

    parser = argparse.ArgumentParser(description="提取情感曲线")
    parser.add_argument("--limit", type=int, help="限制处理小说数量")
    parser.add_argument("--status", action="store_true", help="查看状态")

    args = parser.parse_args()

    if args.status:
        status = EmotionArcExtractor().progress
        print(json.dumps(asdict(status), ensure_ascii=False, indent=2))
    else:
        extract_emotion_arcs(limit=args.limit)
