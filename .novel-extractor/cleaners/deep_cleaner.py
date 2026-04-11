# -*- coding: utf-8 -*-
"""
深度清洗器模块 (Deep Cleaner Module)

功能：
- HTML标签清理
- 广告内容过滤
- 防盗版内容清理
- 章节标题格式化
- 段落整理

返回结果包含清洗后的文本、保留率和统计信息。

保留率目标：>50% 才算有效清洗
"""

import re
import html
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class CleanStats:
    """清洗统计信息数据类"""

    original_length: int = 0
    cleaned_length: int = 0
    html_tags_removed: int = 0
    ads_removed: int = 0
    antipiracy_removed: int = 0
    chapters_formatted: int = 0
    paragraphs_aligned: int = 0

    @property
    def retention_rate(self) -> float:
        """计算保留率"""
        if self.original_length == 0:
            return 0.0
        return (self.cleaned_length / self.original_length) * 100


class DeepCleaner:
    """
    深度清洗器类

    用于清洗小说文本中的HTML标签、广告、防盗版内容等，
    同时保持章节结构和核心内容完整性。
    """

    # 广告关键词列表
    AD_KEYWORDS = [
        "下载更多",
        "更多小说",
        "请访问",
        "www.",
        ".com",
        ".cn",
        ".net",
        "点击阅读",
        "免费下载",
        "小说网",
        "阅读网",
        "书友群",
        "QQ群",
        "微信群",
        "关注公众号",
        "扫码阅读",
        "手机阅读",
        "APP下载",
        "收藏本站",
        "加入书架",
        "推荐票",
        "月票",
        "打赏",
        "最新章节",
        "全文阅读",
        "无弹窗",
        "无广告",
    ]

    # 防盗版特征列表
    ANTIPIRACY_PATTERNS = [
        r"本章未完.*?(?:下一章|继续阅读|$)",
        r"由于版权问题.*?(?:无法显示|已删除|$)",
        r"版权所有.*?(?:不得转载|违者必究|$)",
        r"正版.*?(?:订阅|支持|唯一授权|$)",
        r"防盗.*?(?:章节|内容|已开启|$)",
    ]

    # 章节标题匹配模式
    CHAPTER_PATTERNS = [
        r"^第[一二三四五六七八九十百千万零\d]+章[：:\s]*(.+)$",
        r"^第[\d]+章[：:\s]*(.+)$",
        r"^[\d]+[、.\s]+(.+)$",
        r"^(?:Chapter|CH)[\s]*[\d]+[：:\s]*(.+)$",
    ]

    def __init__(
        self,
        min_paragraph_length: int = 10,
        max_pinyin_ratio: float = 0.3,
        retention_threshold: float = 50.0,
    ):
        """
        初始化深度清洗器

        Args:
            min_paragraph_length: 最小段落长度，小于此值的段落将被过滤
            max_pinyin_ratio: 最大拼音比例，超过此比例的段落将被过滤（防盗版检测）
            retention_threshold: 保留率阈值，低于此值将发出警告
        """
        self.min_paragraph_length = min_paragraph_length
        self.max_pinyin_ratio = max_pinyin_ratio
        self.retention_threshold = retention_threshold
        self.stats = CleanStats()

    def clean(self, text: str) -> Dict[str, Any]:
        """
        主清洗方法

        按顺序执行所有清洗步骤：
        1. 移除HTML标签
        2. 过滤广告内容
        3. 清理防盗版内容
        4. 格式化章节标题
        5. 段落整理

        Args:
            text: 原始文本内容

        Returns:
            包含清洗后文本、保留率和统计信息的字典
            {
                'text': str,          # 清洗后的文本
                'retention_rate': float,  # 保留率（百分比）
                'stats': CleanStats,  # 详细统计信息
                'is_valid': bool,     # 是否有效清洗（保留率>阈值）
                'warnings': List[str] # 警告信息列表
            }
        """
        if not text or not isinstance(text, str):
            return {
                "text": "",
                "retention_rate": 0.0,
                "stats": CleanStats(),
                "is_valid": False,
                "warnings": ["输入文本为空或类型错误"],
            }

        self.stats = CleanStats()
        self.stats.original_length = len(text)
        warnings = []

        # 步骤1: 移除HTML标签
        text = self._remove_html(text)

        # 步骤2: 过滤广告内容
        text = self._filter_ads(text)

        # 步骤3: 清理防盗版内容
        text = self._clean_antipiracy(text)

        # 步骤4: 格式化章节标题
        text = self._format_chapters(text)

        # 步骤5: 段落整理
        text = self._align_paragraphs(text)

        self.stats.cleaned_length = len(text)

        # 检查保留率
        is_valid = self.stats.retention_rate >= self.retention_threshold
        if not is_valid:
            warnings.append(
                f"保留率过低：{self.stats.retention_rate:.1f}% < {self.retention_threshold}%"
            )

        return {
            "text": text,
            "retention_rate": self.stats.retention_rate,
            "stats": self.stats,
            "is_valid": is_valid,
            "warnings": warnings,
        }

    def _remove_html(self, text: str) -> str:
        """
        清理HTML标签和HTML实体

        使用正则表达式移除HTML标签，并将HTML实体转换为普通字符。
        不依赖第三方库如BeautifulSoup。

        Args:
            text: 包含HTML标签的文本

        Returns:
            清理后的纯文本
        """
        if not text:
            return text

        original_length = len(text)

        # 1. 移除script和style标签及其内容
        text = re.sub(
            r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(
            r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE
        )

        # 2. 移除HTML注释
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

        # 3. 将<br>, <p>等标签替换为换行符
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<p[^>]*>", "", text, flags=re.IGNORECASE)

        # 4. 移除所有其他HTML标签
        text = re.sub(r"<[^>]+>", "", text)

        # 5. 解码HTML实体（如 &lt; -> <, &amp; -> &）
        text = html.unescape(text)

        # 统计移除的标签数量（估算）
        self.stats.html_tags_removed = original_length - len(text)

        return text.strip()

    def _filter_ads(self, text: str) -> str:
        """
        过滤广告推广内容

        识别并移除包含广告关键词的行或段落。

        Args:
            text: 原始文本

        Returns:
            过滤广告后的文本
        """
        if not text:
            return text

        lines = text.split("\n")
        filtered_lines = []
        ads_removed = 0

        for line in lines:
            line_stripped = line.strip()
            is_ad = False

            # 检查是否包含广告关键词
            for keyword in self.AD_KEYWORDS:
                if keyword.lower() in line_stripped.lower():
                    is_ad = True
                    ads_removed += 1
                    break

            # 检查是否为纯URL行
            if re.match(r"^[\s]*https?://[^\s]+[\s]*$", line_stripped):
                is_ad = True
                ads_removed += 1

            if not is_ad:
                filtered_lines.append(line)

        self.stats.ads_removed = ads_removed
        return "\n".join(filtered_lines)

    def _clean_antipiracy(self, text: str) -> str:
        """
        清理防盗版内容

        识别并移除防盗版提示、大段拼音替换的内容等。

        Args:
            text: 原始文本

        Returns:
            清理防盗版内容后的文本
        """
        if not text:
            return text

        original_text = text
        antipiracy_removed = 0

        # 1. 移除防盗版模式匹配的内容
        for pattern in self.ANTIPIRACY_PATTERNS:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            antipiracy_removed += len(matches)
            text = re.sub(pattern, "", text, flags=re.MULTILINE | re.IGNORECASE)

        # 2. 检测并标记包含大量拼音的段落
        lines = text.split("\n")
        filtered_lines = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                filtered_lines.append(line)
                continue

            # 计算拼音比例（连续拼音字符）
            pinyin_chars = len(re.findall(r"[a-zA-Z]{2,}", line_stripped))
            total_chars = len(line_stripped)

            if total_chars > 0:
                pinyin_ratio = pinyin_chars / total_chars
                if pinyin_ratio > self.max_pinyin_ratio:
                    antipiracy_removed += 1
                    continue  # 跳过包含大量拼音的行

            filtered_lines.append(line)

        text = "\n".join(filtered_lines)
        self.stats.antipiracy_removed = antipiracy_removed

        return text.strip()

    def _format_chapters(self, text: str) -> str:
        """
        格式化章节标题

        统一章节标题格式，确保标题清晰可见。
        支持的格式：第一章、第1章、Chapter 1等

        Args:
            text: 原始文本

        Returns:
            格式化章节标题后的文本
        """
        if not text:
            return text

        lines = text.split("\n")
        formatted_lines = []
        chapters_formatted = 0

        for line in lines:
            line_stripped = line.strip()
            is_chapter = False

            for pattern in self.CHAPTER_PATTERNS:
                match = re.match(pattern, line_stripped)
                if match:
                    # 标准化章节标题格式
                    chapter_title = match.group(1).strip() if match.groups() else ""
                    if chapter_title:
                        formatted_lines.append(f"## {line_stripped}")
                    else:
                        formatted_lines.append(f"## {line_stripped}")
                    chapters_formatted += 1
                    is_chapter = True
                    break

            if not is_chapter:
                formatted_lines.append(line)

        self.stats.chapters_formatted = chapters_formatted
        return "\n".join(formatted_lines)

    def _align_paragraphs(self, text: str) -> str:
        """
        段落整理

        统一段落格式，处理缩进、空行等，使文本更易读。

        Args:
            text: 原始文本

        Returns:
            整理后的文本
        """
        if not text:
            return text

        lines = text.split("\n")
        aligned_lines = []
        paragraphs_aligned = 0
        prev_was_empty = True

        for line in lines:
            line_stripped = line.strip()

            # 跳过空行但保留一个
            if not line_stripped:
                if not prev_was_empty:
                    aligned_lines.append("")
                    prev_was_empty = True
                continue

            # 检查是否为章节标题（已在_format_chapters中标记）
            if line_stripped.startswith("##"):
                if not prev_was_empty and aligned_lines:
                    aligned_lines.append("")  # 章节前添加空行
                aligned_lines.append(line_stripped)
                aligned_lines.append("")  # 章节后添加空行
                prev_was_empty = True
                continue

            # 过滤过短的段落（可能是广告或乱码）
            if len(line_stripped) < self.min_paragraph_length:
                # 但不过滤对话内容（以引号开头）
                if not re.match(r'^["""「『]', line_stripped):
                    continue

            # 添加段落缩进（如果需要）
            aligned_lines.append(line_stripped)
            prev_was_empty = False
            paragraphs_aligned += 1

        # 移除末尾的空行
        while aligned_lines and aligned_lines[-1] == "":
            aligned_lines.pop()

        self.stats.paragraphs_aligned = paragraphs_aligned
        return "\n".join(aligned_lines)


# 便捷函数，用于快速清洗
def deep_clean(text: str, **kwargs) -> Dict[str, Any]:
    """
    便捷函数：快速清洗文本

    Args:
        text: 原始文本
        **kwargs: 传递给DeepCleaner的初始化参数

    Returns:
        清洗结果字典

    Example:
        >>> result = deep_clean("<p>第一章 开始</p><br>这是内容")
        >>> print(result['text'])
        ## 第一章 开始
        这是内容
        >>> print(f"保留率: {result['retention_rate']:.1f}%")
    """
    cleaner = DeepCleaner(**kwargs)
    return cleaner.clean(text)


if __name__ == "__main__":
    # 测试示例
    test_text = """
    <html>
    <body>
    <p>第一章 测试章节</p>
    <br>
    这是正文内容，包含一些文字。
    <script>alert('广告')</script>
    请访问 www.example.com 下载更多小说。
    本章未完，请订阅后阅读下一章。
    <p>第二章 下一章</p>
    zhe shi yi duan pin yin nei rong。
    这是正常段落。
    </body>
    </html>
    """

    result = deep_clean(test_text)
    print("=" * 50)
    print("清洗结果：")
    print("=" * 50)
    print(result["text"])
    print("=" * 50)
    print(f"保留率: {result['retention_rate']:.1f}%")
    print(f"是否有效: {result['is_valid']}")
    print(f"HTML标签移除: {result['stats'].html_tags_removed} 字符")
    print(f"广告移除: {result['stats'].ads_removed} 处")
    print(f"防盗版移除: {result['stats'].antipiracy_removed} 处")
    print(f"章节格式化: {result['stats'].chapters_formatted} 处")
    print(f"段落整理: {result['stats'].paragraphs_aligned} 处")
