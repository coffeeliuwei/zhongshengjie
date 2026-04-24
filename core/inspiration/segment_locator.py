# core/inspiration/segment_locator.py
"""自然语言定位段落

把作者的"第2章末尾那段"、"屋檐滴水那句"等表述转化为具体文本片段。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §7
"""

from pathlib import Path
from typing import Optional, Dict, Any, List


POSITION_KEYWORDS = {
    "开头": "beginning",
    "开始": "beginning",
    "起始": "beginning",
    "中间": "middle",
    "中部": "middle",
    "末尾": "end",
    "结尾": "end",
    "最后": "end",
    "结束": "end",
}


def _split_paragraphs(text: str) -> List[str]:
    """按双空行或单空行分段，过滤空段"""
    raw = text.replace("\r\n", "\n")
    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        # 退化为按单换行分段
        paragraphs = [p.strip() for p in raw.split("\n") if p.strip()]
    return paragraphs


def locate_segment(
    chapter_file: Path,
    location_hint: Optional[str] = None,
    keyword: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """定位章节中的段落

    Strategy:
    1. 若同时提供 keyword 和 location_hint，优先 keyword 命中后再校验位置区间
    2. 仅 keyword：找首个含该 keyword 的段
    3. 仅 location_hint：按位置（开头/中间/末尾）取段
    4. 都没有：返回 None

    Returns:
        {
            "segment_text": str,
            "segment_scope": "paragraph",
            "position_hint": {"paragraph_index": int}
        }
        或 None
    """
    if not chapter_file.exists():
        return None

    text = chapter_file.read_text(encoding="utf-8")
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return None

    n = len(paragraphs)

    # 关键词命中
    if keyword:
        # 关键词预处理：去掉常见后缀如"那句"、"那段"
        clean = keyword.rstrip("那句那段那个").strip()
        if not clean:
            clean = keyword
        for i, para in enumerate(paragraphs):
            if clean in para:
                # 若有 location_hint，校验是否在合理区间
                if location_hint and not _in_position_range(i, n, location_hint):
                    continue
                return {
                    "segment_text": para,
                    "segment_scope": "paragraph",
                    "position_hint": {"paragraph_index": i},
                }
        return None

    # 仅位置 hint
    if location_hint:
        idx = _hint_to_index(location_hint, n)
        if idx is None:
            return None
        return {
            "segment_text": paragraphs[idx],
            "segment_scope": "paragraph",
            "position_hint": {"paragraph_index": idx},
        }

    return None


def _hint_to_index(hint: str, total: int) -> Optional[int]:
    """位置词转换为段落索引"""
    pos = None
    for k, v in POSITION_KEYWORDS.items():
        if k in hint:
            pos = v
            break
    if pos is None:
        return None
    if pos == "beginning":
        return 0
    if pos == "end":
        return total - 1
    if pos == "middle":
        return total // 2
    return None


def _in_position_range(index: int, total: int, hint: str) -> bool:
    """判断索引是否落在 hint 描述的区间"""
    pos = None
    for k, v in POSITION_KEYWORDS.items():
        if k in hint:
            pos = v
            break
    if pos is None:
        return True  # 无法识别就不限制
    third = max(1, total // 3)
    if pos == "beginning":
        return index < third
    if pos == "middle":
        return third <= index < 2 * third
    if pos == "end":
        return index >= 2 * third
    return True
