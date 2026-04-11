"""
质量评分器 - 压缩率检测、信息密度评分、结构完整性评分、语言质量评分

使用方式:
    from scorers.quality_scorer import QualityScorer

    scorer = QualityScorer()
    result = scorer.score(text)
    print(f"综合评分: {result['score']}")
    print(f"是否通过: {result['is_quality']}")
"""

import re
import zlib
from typing import Dict, List, Optional
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.config_loader import get_config

# 尝试导入 lz4，如果没有则使用 zlib 作为备选
try:
    import lz4.frame

    HAS_LZ4 = True
except ImportError:
    HAS_LZ4 = False


class QualityScorer:
    """质量评分器

    提供多维度质量评分:
    1. 压缩率评分 - 检测重复内容和噪音
    2. 信息密度评分 - 关键词密度评估
    3. 结构完整性评分 - 章节和段落结构
    4. 语言质量评分 - 中文比例和噪音检测

    综合评分使用加权平均，阈值从配置加载。
    """

    # 默认关键词列表（用于信息密度评分）
    DEFAULT_KEYWORDS = [
        # 战斗相关
        "战斗",
        "修炼",
        "突破",
        "力量",
        "境界",
        "功法",
        "法术",
        # 场景相关
        "宗门",
        "城池",
        "山谷",
        "宫殿",
        "秘境",
        "战场",
        # 人物相关
        "主角",
        "弟子",
        "长老",
        "宗主",
        "师兄",
        "师姐",
        # 情节相关
        "危机",
        "机遇",
        "挑战",
        "阴谋",
        "背叛",
        "复仇",
        # 情感相关
        "心中",
        "暗想",
        "震惊",
        "愤怒",
        "喜悦",
        "悲伤",
        # 叙事相关
        "忽然",
        "顿时",
        "瞬间",
        "目光",
        "身影",
        "气息",
    ]

    def __init__(self, keywords: Optional[List[str]] = None):
        """初始化评分器

        Args:
            keywords: 自定义关键词列表，为None使用默认列表
        """
        # 加载配置
        config = get_config()
        thresholds = config.get("quality_thresholds", {})

        # 从配置加载阈值，使用默认值兜底
        self.compression_min = thresholds.get("compression_ratio_min", 0.65)
        self.compression_max = thresholds.get("compression_ratio_max", 0.80)
        self.quality_min = thresholds.get("quality_score_min", 0.6)
        self.chinese_ratio_min = thresholds.get("chinese_ratio_min", 0.6)
        self.noise_ratio_max = thresholds.get("noise_ratio_max", 0.10)

        # 关键词配置
        self.keywords = keywords or self.DEFAULT_KEYWORDS

        # 权重配置（可从配置扩展）
        self.weights = {
            "compression": 0.25,
            "density": 0.25,
            "structure": 0.25,
            "language": 0.25,
        }

    def score(self, text: str) -> Dict:
        """计算综合质量评分

        Args:
            text: 待评分的文本内容

        Returns:
            包含评分结果的字典:
            - score: 综合评分 (0-1)
            - is_quality: 是否通过质量阈值
            - compression_ratio: 原始压缩率
            - details: 各维度详细评分
            - reason: 失败原因（如果未通过）
        """
        # 检查空文本
        if not text or not text.strip():
            return {
                "score": 0.0,
                "is_quality": False,
                "compression_ratio": 0.0,
                "details": {},
                "reason": "empty_text",
            }

        # 计算各维度评分
        scores = {}

        # 1. 压缩率评分
        compression_result = self._score_compression(text)
        scores["compression"] = compression_result["score"]
        scores["compression_raw"] = compression_result["ratio"]

        # 2. 信息密度评分
        scores["density"] = self._score_density(text)

        # 3. 结构完整性评分
        scores["structure"] = self._score_structure(text)

        # 4. 语言质量评分
        scores["language"] = self._score_language(text)

        # 综合评分（加权平均）
        total_weight = sum(self.weights.values())
        final_score = (
            sum(scores[k] * self.weights[k] for k in self.weights) / total_weight
        )

        # 判断是否通过质量阈值
        is_quality = final_score >= self.quality_min

        # 生成失败原因
        reason = None
        if not is_quality:
            reason = self._get_failure_reason(scores)

        return {
            "score": round(final_score, 4),
            "is_quality": is_quality,
            "compression_ratio": round(scores["compression_raw"], 4),
            "details": {
                "compression": round(scores["compression"], 4),
                "density": round(scores["density"], 4),
                "structure": round(scores["structure"], 4),
                "language": round(scores["language"], 4),
            },
            "reason": reason,
        }

    def _score_compression(self, text: str) -> Dict:
        """压缩率评分

        使用 LZ4（或备选 zlib）计算压缩率。
        最佳范围 0.65-0.80 得满分。
        过低表示重复内容太多，过高表示噪音太多。

        Args:
            text: 待评分的文本

        Returns:
            包含评分和原始压缩率的字典
        """
        try:
            text_bytes = text.encode("utf-8")
            original_len = len(text_bytes)

            if original_len == 0:
                return {"score": 0.0, "ratio": 0.0}

            # 使用 LZ4 或 zlib 压缩
            if HAS_LZ4:
                compressed = lz4.frame.compress(text_bytes)
            else:
                compressed = zlib.compress(text_bytes)

            compressed_len = len(compressed)
            ratio = compressed_len / original_len

            # 评分逻辑：最佳范围得满分
            if self.compression_min <= ratio <= self.compression_max:
                score = 1.0
            elif ratio < self.compression_min:
                # 过低（重复内容太多）- 线性递减
                score = ratio / self.compression_min
            else:
                # 过高（噪音太多）- 反比例递减
                score = self.compression_max / ratio

            return {
                "score": max(0.0, min(1.0, score)),
                "ratio": ratio,
            }

        except Exception:
            # 压缩失败时返回中等评分
            return {"score": 0.5, "ratio": 0.5}

    def _score_density(self, text: str) -> float:
        """信息密度评分

        基于关键词密度评估文本的信息丰富程度。
        每千字符应有适量关键词。

        Args:
            text: 待评分的文本

        Returns:
            密度评分 (0-1)
        """
        if not text:
            return 0.0

        text_len = len(text)
        if text_len == 0:
            return 0.0

        # 统计关键词出现次数
        keyword_count = 0
        for keyword in self.keywords:
            keyword_count += len(re.findall(re.escape(keyword), text))

        # 计算每千字符的关键词密度
        density = keyword_count / (text_len / 1000) if text_len > 0 else 0

        # 理想密度：每千字5-15个关键词
        if density < 5:
            # 密度过低
            score = density / 5
        elif density <= 15:
            # 理想范围
            score = 1.0
        else:
            # 密度过高（可能是关键词堆砌）
            score = max(0.5, 15 / density)

        return max(0.0, min(1.0, score))

    def _score_structure(self, text: str) -> float:
        """结构完整性评分

        评估章节结构和段落分布的合理性。

        Args:
            text: 待评分的文本

        Returns:
            结构评分 (0-1)
        """
        if not text:
            return 0.0

        # 检查章节结构（支持多种格式）
        chapter_patterns = [
            r"第[\d一二三四五六七八九十百千]+[章节回]",  # 第一章、第1章
            r"Chapter\s*\d+",  # Chapter 1
            r"^[\d]+[\.\s]",  # 1. 或 1 开头
        ]

        chapter_count = 0
        for pattern in chapter_patterns:
            chapter_count += len(re.findall(pattern, text, re.IGNORECASE))

        # 检查段落结构
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        paragraph_count = len(paragraphs)

        # 评分逻辑
        if chapter_count >= 1 and paragraph_count >= 10:
            # 有章节且有足够段落
            score = 1.0
        elif chapter_count >= 1:
            # 有章节但段落较少
            score = 0.7
        elif paragraph_count >= 20:
            # 无章节但段落丰富
            score = 0.6
        elif paragraph_count >= 10:
            # 段落较少
            score = 0.4
        else:
            # 结构太差
            score = 0.2

        return score

    def _score_language(self, text: str) -> float:
        """语言质量评分

        评估中文比例和噪音比例。

        Args:
            text: 待评分的文本

        Returns:
            语言评分 (0-1)
        """
        if not text:
            return 0.0

        text_len = len(text)
        if text_len == 0:
            return 0.0

        # 计算中文比例
        chinese_chars = len(re.findall(r"[\u4e00-\u9fa5]", text))
        chinese_ratio = chinese_chars / text_len

        # 计算噪音比例（过多数字、长串英文、特殊字符）
        noise_patterns = [
            r"[\d]{5,}",  # 5位以上数字
            r"[a-zA-Z]{10,}",  # 10位以上英文
            r"[!@#$%^&*]{3,}",  # 连续特殊字符
            r"[\x00-\x08\x0b-\x0c\x0e-\x1f]",  # 控制字符
        ]

        noise_count = 0
        for pattern in noise_patterns:
            noise_count += len(re.findall(pattern, text))

        noise_ratio = noise_count / text_len if text_len > 0 else 0

        # 评分逻辑
        if chinese_ratio >= 0.8 and noise_ratio < 0.01:
            # 高中文比例，低噪音
            score = 1.0
        elif chinese_ratio >= 0.6 and noise_ratio < self.noise_ratio_max:
            # 达标中文比例，噪音可控
            score = 0.7 + (chinese_ratio - 0.6) * 0.75
        elif chinese_ratio >= self.chinese_ratio_min:
            # 中文比例达标但噪音较高
            score = 0.5
        else:
            # 中文比例过低
            score = 0.3

        return max(0.0, min(1.0, score))

    def _get_failure_reason(self, scores: Dict) -> str:
        """生成失败原因

        Args:
            scores: 各维度评分

        Returns:
            失败原因描述
        """
        reasons = []

        if scores.get("compression", 1.0) < 0.5:
            reasons.append("compression_abnormal")
        if scores.get("density", 1.0) < 0.5:
            reasons.append("low_density")
        if scores.get("structure", 1.0) < 0.5:
            reasons.append("poor_structure")
        if scores.get("language", 1.0) < 0.5:
            reasons.append("language_issues")

        if reasons:
            return ",".join(reasons)
        return "below_threshold"

    def batch_score(self, texts: List[str]) -> List[Dict]:
        """批量评分

        Args:
            texts: 文本列表

        Returns:
            评分结果列表
        """
        return [self.score(text) for text in texts]

    def get_stats(self, results: List[Dict]) -> Dict:
        """统计批量评分结果

        Args:
            results: 评分结果列表

        Returns:
            统计数据字典
        """
        if not results:
            return {}

        scores = [r["score"] for r in results]
        quality_count = sum(1 for r in results if r["is_quality"])

        return {
            "total": len(results),
            "quality_count": quality_count,
            "quality_rate": round(quality_count / len(results), 4),
            "avg_score": round(sum(scores) / len(scores), 4),
            "min_score": round(min(scores), 4),
            "max_score": round(max(scores), 4),
        }


# 便捷函数
def score_text(text: str) -> Dict:
    """快速评分单个文本"""
    scorer = QualityScorer()
    return scorer.score(text)


def score_batch(texts: List[str]) -> List[Dict]:
    """快速批量评分"""
    scorer = QualityScorer()
    return scorer.batch_score(texts)


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("质量评分器测试")
    print("=" * 60)

    test_texts = [
        # 高质量文本
        "第一章 开篇\n\n林雷站在山巅，望着远方的玄武城。他心中暗想：这片天地，究竟隐藏着多少秘密？"
        * 50,
        # 低质量文本（英文太多）
        "This is English text with some 中文 mixed in. " * 20,
        # 低质量文本（重复内容）
        "重复重复重复重复重复" * 100,
        # 空文本
        "",
    ]

    scorer = QualityScorer()

    for i, text in enumerate(test_texts, 1):
        print(f"\n测试 {i}:")
        result = scorer.score(text)
        print(f"  评分: {result['score']}")
        print(f"  通过: {result['is_quality']}")
        print(f"  压缩率: {result['compression_ratio']}")
        print(f"  详情: {result['details']}")
        if result["reason"]:
            print(f"  原因: {result['reason']}")
