"""
伏笔回收配对提取器

识别小说中伏笔设置与回收的配对关系：
- 伏笔设置位置
- 伏笔回收位置
- 两者间的距离
- 关联强度

用于学习伏笔设计技巧
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass

from base_extractor import BaseExtractor
from config import EXTRACTION_DIMENSIONS


@dataclass
class ForeshadowPair:
    """伏笔配对"""

    foreshadow_text: str  # 伏笔文本
    foreshadow_position: int  # 伏笔位置（字符索引）
    payoff_text: str  # 回收文本
    payoff_position: int  # 回收位置
    distance: int  # 距离（字符数）
    relation_type: str  # 关系类型
    confidence: float  # 置信度
    novel_id: str = ""


class ForeshadowPairExtractor(BaseExtractor):
    """伏笔回收配对提取器"""

    def __init__(self):
        super().__init__("foreshadow_pair")

        # 伏笔设置指示词
        self.foreshadow_indicators = [
            "似乎",
            "隐隐",
            "若隐若现",
            "暗中",
            "暗藏",
            "隐约",
            "仿佛",
            "好像",
            "像是",
            "隐秘",
            "不为人知",
            "无人知晓",
            "悄悄",
            "悄然",
        ]

        # 伏笔回收指示词
        self.payoff_indicators = [
            "原来",
            "竟",
            "真相",
            "早已",
            "早就",
            "果然",
            "难怪",
            "怪不得",
            "这就是",
            "终于明白",
            "恍然",
            "原来如此",
        ]

        # 悬念词
        self.suspense_words = [
            "秘密",
            "谜",
            "疑惑",
            "疑问",
            "不解",
            "未知",
            "奇怪",
            "异常",
            "古怪",
        ]

        # 揭示词
        self.reveal_words = [
            "揭示",
            "揭露",
            "真相",
            "秘密",
            "答案",
            "谜底",
            "解开",
            "真相大白",
        ]

    def _find_foreshadow_candidates(self, content: str) -> List[Dict]:
        """寻找伏笔候选"""
        candidates = []

        # 方法1：基于指示词
        for indicator in self.foreshadow_indicators:
            pattern = f"{indicator}[^。！？]{{5,50}}"
            matches = re.finditer(pattern, content)
            for match in matches:
                context_start = max(0, match.start() - 20)
                context_end = min(len(content), match.end() + 20)
                candidates.append(
                    {
                        "text": match.group(),
                        "position": match.start(),
                        "context": content[context_start:context_end],
                        "type": "indicator",
                        "indicator": indicator,
                    }
                )

        # 方法2：基于悬念词
        for word in self.suspense_words:
            pattern = f"[^。！？]{{0,30}}{word}[^。！？]{{0,30}}"
            matches = re.finditer(pattern, content)
            for match in matches:
                # 避免重复
                if not any(c["position"] == match.start() for c in candidates):
                    context_start = max(0, match.start() - 20)
                    context_end = min(len(content), match.end() + 20)
                    candidates.append(
                        {
                            "text": match.group(),
                            "position": match.start(),
                            "context": content[context_start:context_end],
                            "type": "suspense",
                            "indicator": word,
                        }
                    )

        return candidates

    def _find_payoff_candidates(self, content: str) -> List[Dict]:
        """寻找回收候选"""
        candidates = []

        # 方法1：基于指示词
        for indicator in self.payoff_indicators:
            pattern = f"{indicator}[^。！？]{{5,80}}"
            matches = re.finditer(pattern, content)
            for match in matches:
                context_start = max(0, match.start() - 20)
                context_end = min(len(content), match.end() + 20)
                candidates.append(
                    {
                        "text": match.group(),
                        "position": match.start(),
                        "context": content[context_start:context_end],
                        "type": "indicator",
                        "indicator": indicator,
                    }
                )

        # 方法2：基于揭示词
        for word in self.reveal_words:
            pattern = f"[^。！？]{{0,30}}{word}[^。！？]{{0,30}}"
            matches = re.finditer(pattern, content)
            for match in matches:
                if not any(c["position"] == match.start() for c in candidates):
                    context_start = max(0, match.start() - 20)
                    context_end = min(len(content), match.end() + 20)
                    candidates.append(
                        {
                            "text": match.group(),
                            "position": match.start(),
                            "context": content[context_start:context_end],
                            "type": "reveal",
                            "indicator": word,
                        }
                    )

        return candidates

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化版）"""
        # 提取关键词
        words1 = set(re.findall(r"[\u4e00-\u9fa5]{2,4}", text1))
        words2 = set(re.findall(r"[\u4e00-\u9fa5]{2,4}", text2))

        if not words1 or not words2:
            return 0.0

        # Jaccard相似度
        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def _match_pairs(
        self, foreshadows: List[Dict], payoffs: List[Dict], content: str
    ) -> List[ForeshadowPair]:
        """匹配伏笔-回收配对"""
        pairs = []
        max_distance = 100000  # 最大距离（约100k字符）

        for fs in foreshadows:
            fs_pos = fs["position"]
            fs_text = fs["text"]

            # 寻找可能的回收
            best_payoff = None
            best_score = 0.0

            for po in payoffs:
                po_pos = po["position"]
                po_text = po["text"]

                # 回收必须在伏笔之后
                if po_pos <= fs_pos:
                    continue

                distance = po_pos - fs_pos

                # 距离不能太远
                if distance > max_distance:
                    continue

                # 计算相似度
                similarity = self._calculate_similarity(fs["context"], po["context"])

                # 综合评分
                # 距离越近分数越高，相似度越高分数越高
                distance_score = 1.0 - (distance / max_distance)
                score = similarity * 0.7 + distance_score * 0.3

                if score > best_score:
                    best_score = score
                    best_payoff = po

            # 如果找到匹配
            if best_payoff and best_score > 0.1:
                pairs.append(
                    ForeshadowPair(
                        foreshadow_text=fs_text,
                        foreshadow_position=fs_pos,
                        payoff_text=best_payoff["text"],
                        payoff_position=best_payoff["position"],
                        distance=best_payoff["position"] - fs_pos,
                        relation_type=self._classify_relation(fs, best_payoff),
                        confidence=best_score,
                    )
                )

        return pairs

    def _classify_relation(self, foreshadow: Dict, payoff: Dict) -> str:
        """分类伏笔类型"""
        fs_text = foreshadow.get("text", "")
        po_text = payoff.get("text", "")

        # 基于内容分类
        if any(w in fs_text for w in ["身份", "血脉", "来历"]):
            return "身份揭示"
        if any(w in fs_text for w in ["秘密", "隐秘", "隐藏"]):
            return "秘密揭示"
        if any(w in fs_text for w in ["实力", "能力", "力量"]):
            return "实力揭露"
        if any(w in fs_text for w in ["预言", "预兆", "征兆"]):
            return "预言应验"
        if any(w in fs_text for w in ["关系", "恩怨", "仇恨"]):
            return "关系揭示"

        return "一般伏笔"

    def extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]:
        """从小说提取伏笔配对"""

        if len(content) < 50000:  # 太短，跳过
            return []

        # 找候选
        foreshadows = self._find_foreshadow_candidates(content)
        payoffs = self._find_payoff_candidates(content)

        if not foreshadows or not payoffs:
            return []

        # 匹配配对
        pairs = self._match_pairs(foreshadows, payoffs, content)

        # 转换
        results = []
        for pair in pairs:
            pair.novel_id = novel_id
            results.append(pair.__dict__)

        return results

    def process_extracted(self, items: List[dict]) -> List[dict]:
        """处理提取结果 - 按类型聚合"""
        # 按关系类型分组
        type_groups = defaultdict(list)

        for item in items:
            relation_type = item.get("relation_type", "一般伏笔")
            type_groups[relation_type].append(item)

        # 整合结果
        results = []
        for relation_type, pairs in type_groups.items():
            # 统计平均距离
            avg_distance = sum(p.get("distance", 0) for p in pairs) / len(pairs)

            # 典型示例
            examples = sorted(
                pairs, key=lambda x: x.get("confidence", 0), reverse=True
            )[:10]

            results.append(
                {
                    "relation_type": relation_type,
                    "pair_count": len(pairs),
                    "avg_distance": round(avg_distance),
                    "examples": [
                        {
                            "foreshadow": e.get("foreshadow_text", "")[:100],
                            "payoff": e.get("payoff_text", "")[:100],
                            "distance": e.get("distance", 0),
                            "confidence": round(e.get("confidence", 0), 2),
                        }
                        for e in examples
                    ],
                    "description": self._get_relation_description(relation_type),
                }
            )

        return results

    def _get_relation_description(self, relation_type: str) -> str:
        """获取关系类型描述"""
        descriptions = {
            "身份揭示": "伏笔暗示角色真实身份，后续揭示",
            "秘密揭示": "伏笔埋设秘密线索，后续揭露",
            "实力揭露": "伏笔暗示隐藏实力，后续展现",
            "预言应验": "伏笔设置预言，后续应验",
            "关系揭示": "伏笔暗示人物关系，后续揭示",
            "一般伏笔": "其他类型的伏笔配对",
        }
        return descriptions.get(relation_type, "伏笔配对")


def extract_foreshadow_pairs(limit: int = None):
    """提取伏笔配对"""
    extractor = ForeshadowPairExtractor()
    return extractor.run(limit=limit)


if __name__ == "__main__":
    import argparse
    from dataclasses import asdict

    parser = argparse.ArgumentParser(description="提取伏笔回收配对")
    parser.add_argument("--limit", type=int, help="限制处理小说数量")
    parser.add_argument("--status", action="store_true", help="查看状态")

    args = parser.parse_args()

    if args.status:
        status = ForeshadowPairExtractor().progress
        print(json.dumps(asdict(status), ensure_ascii=False, indent=2))
    else:
        extract_foreshadow_pairs(limit=args.limit)
