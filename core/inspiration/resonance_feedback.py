# core/inspiration/resonance_feedback.py
"""读者反馈处理器

入参为意图分类器识别后的反馈类自然语言。
负责：解析情绪信号 → 定位段落 → 提取结构特征 → 写入记忆点库。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §5
"""

import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Callable, Optional, List

from core.inspiration.memory_point_sync import MemoryPointSync
from core.inspiration.segment_locator import locate_segment
from core.inspiration.structural_analyzer import analyze
from core.inspiration.embedder import embed_text


# 情绪类型识别词典
POSITIVE_TYPE_KEYWORDS = {
    "震撼": ["震撼", "炸", "炸裂", "猛"],
    "感动": ["感动", "泪", "暖", "动人", "酸"],
    "爽快": ["解气", "爽", "燃", "痛快", "畅快", "狠"],
    "好笑": ["好笑", "笑", "幽默", "逗"],
}
NEGATIVE_TYPE_KEYWORDS = {
    "出戏": ["出戏", "尬", "突兀", "违和"],
    "乏味": ["乏味", "拖", "无聊", "枯燥", "平淡", "跳着", "跳过"],
}

INTENSITY_STRONG = ["很", "太", "极", "非常", "特别"]
INTENSITY_WEAK = ["有点", "稍微", "一点点"]


def _extract_signal(user_input: str) -> Dict[str, Any]:
    """从自然语言提取情绪信号

    Returns:
        {
            "polarity": "+"|"-",
            "resonance_type": str,
            "intensity": 1-3,
            "chapter_ref": str|None,
            "location_hint": str|None,
            "keyword": str|None,
            "note": str,
        }
    """
    polarity = None
    resonance_type = None

    # 检测情绪类型
    for rt, kws in POSITIVE_TYPE_KEYWORDS.items():
        if any(k in user_input for k in kws):
            polarity = "+"
            resonance_type = rt
            break
    if polarity is None:
        for rt, kws in NEGATIVE_TYPE_KEYWORDS.items():
            if any(k in user_input for k in kws):
                polarity = "-"
                resonance_type = rt
                break
    if polarity is None:
        # 默认按通用褒贬词
        if any(w in user_input for w in ["好", "妙", "漂亮", "棒", "对味", "舒服"]):
            polarity = "+"
            resonance_type = "爽快"
        elif any(w in user_input for w in ["差", "弱", "不行", "别扭", "假"]):
            polarity = "-"
            resonance_type = "乏味"
        else:
            polarity = "+"
            resonance_type = "震撼"

    # 强度计算
    strong_count = sum(1 for w in INTENSITY_STRONG if w in user_input)
    weak_count = sum(1 for w in INTENSITY_WEAK if w in user_input)
    if strong_count >= 2:
        intensity = 3
    elif strong_count == 1 and weak_count == 0:
        intensity = 2
    elif weak_count > 0:
        intensity = 1
    else:
        intensity = 2

    # 提取章节
    chapter_match = re.search(r"第([零一二三四五六七八九十百千\d]+)章", user_input)
    chapter_ref = chapter_match.group(0) if chapter_match else None

    # 提取位置 hint
    location_hint = None
    for pos in ["开头", "开始", "中间", "末尾", "结尾", "最后"]:
        if pos in user_input:
            location_hint = pos
            break

    # 提取关键词（"X那句/那段"中的 X）
    keyword = None
    kw_match = re.search(r"['\"\"\u201c\u201d](.+?)['\"\"\u201c\u201d]", user_input)
    if kw_match:
        keyword = kw_match.group(1)
    else:
        # 尝试匹配"X那句"
        kw_match = re.search(
            r"(?:那个|那句|那段|这个|这句|这段)([^那这，。,]+?)(?:那句|那段|很|真|写)",
            user_input,
        )
        if kw_match:
            keyword = kw_match.group(1).strip()
        else:
            # 简单的具象词提取
            for w in ["屋檐滴水", "反打", "屋檐", "滴水"]:
                if w in user_input:
                    keyword = w
                    break

    return {
        "polarity": polarity,
        "resonance_type": resonance_type,
        "intensity": intensity,
        "chapter_ref": chapter_ref,
        "location_hint": location_hint,
        "keyword": keyword,
        "note": _extract_note(user_input),
    }


def _extract_note(user_input: str) -> str:
    """保留原话作为备注"""
    return user_input.strip()


def _resolve_chapter_path(chapter_ref: str) -> Optional[Path]:
    """章节引用解析为文件路径

    本函数依赖项目"正文/"目录结构。若不匹配，返回 None。
    """
    if not chapter_ref:
        return None
    candidates = [
        Path("正文") / f"{chapter_ref}.md",
        Path("正文") / f"{chapter_ref}.txt",
        Path("chapters") / f"{chapter_ref}.md",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def handle_reader_feedback(
    user_input: str,
    scene_type_lookup: Callable[[str], str],
    sync: Optional[MemoryPointSync] = None,
    is_overturn: bool = False,
) -> Dict[str, Any]:
    """处理 reader_moment_feedback 意图

    Args:
        user_input: 作者原话
        scene_type_lookup: 给定章节引用返回该章节的场景类型
        sync: 记忆点库实例（测试可注入 mock）

    Returns:
        {
            "status": "ok" | "needs_clarification",
            "memory_point_ids": List[str],
            "message": str,  # 给作者的回复
        }
    """
    if sync is None:
        sync = MemoryPointSync()

    signal = _extract_signal(user_input)

    if not signal["chapter_ref"]:
        return {
            "status": "needs_clarification",
            "memory_point_ids": [],
            "message": "你说的是哪一章？或者直接粘文本给我也行。",
        }

    chapter_path = _resolve_chapter_path(signal["chapter_ref"])
    if not chapter_path:
        return {
            "status": "needs_clarification",
            "memory_point_ids": [],
            "message": f"我没找到 {signal['chapter_ref']} 的文件。粘给我原文我直接记？",
        }

    located = locate_segment(
        chapter_file=chapter_path,
        location_hint=signal["location_hint"],
        keyword=signal["keyword"],
    )
    if not located:
        return {
            "status": "needs_clarification",
            "memory_point_ids": [],
            "message": f"我在 {signal['chapter_ref']} 里没找到匹配段落，粘给我具体内容？",
        }

    scene_type = scene_type_lookup(signal["chapter_ref"])
    structural = analyze(located["segment_text"])

    # 生成真实 embedding（用于记忆点相似度检索）
    try:
        embedding = embed_text(located["segment_text"])
    except Exception:
        embedding = None  # 模型不可用时降级为 None（sync.create 内部处理零向量）

    payload = {
        "segment_text": located["segment_text"],
        "segment_scope": located["segment_scope"],
        "position_hint": located["position_hint"],
        "chapter_ref": signal["chapter_ref"],
        "resonance_type": signal["resonance_type"],
        "polarity": signal["polarity"],
        "intensity": signal["intensity"],
        "note": signal["note"],
        "scene_type": scene_type,
        "structural_features": structural,
    }

    if is_overturn:
        payload["overturn_event"] = {
            "rater_selected": None,
            "rater_reason": None,
            "rater_confidence": None,
            "evaluator_approved": None,
            "evaluator_scores": {},
            "user_overturn_at": datetime.now(timezone.utc).isoformat(),
            "conflict_type": "user_overturn",
        }

    mp_ids: List[str] = [sync.create(payload, embedding=embedding)]

    # 若关键词独立出现，再单独入一条句子级记忆点
    if signal["keyword"] and signal["keyword"] in located["segment_text"]:
        sent_payload = dict(payload)
        sent_payload["segment_text"] = signal["keyword"]
        sent_payload["segment_scope"] = "sentence"
        sent_payload["structural_features"] = analyze(signal["keyword"])
        try:
            sent_embedding = embed_text(signal["keyword"])
        except Exception:
            sent_embedding = None
        mp_ids.append(sync.create(sent_payload, embedding=sent_embedding))

    return {
        "status": "ok",
        "memory_point_ids": mp_ids,
        "message": (
            f"已记下 {len(mp_ids)} 条记忆点："
            f"[{signal['polarity']}{signal['intensity']} {signal['resonance_type']}]"
            f"  {signal['chapter_ref']}"
        ),
    }
