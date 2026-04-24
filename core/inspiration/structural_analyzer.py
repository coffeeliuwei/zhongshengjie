# core/inspiration/structural_analyzer.py
"""段落结构特征自动提取

V1 求"能跑、特征可解释"，不求精确。
后续可由专门的 NLP 模块替换实现，接口保持。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §6
"""

import re
import statistics
from typing import Dict, Any, List


# 预定义节奏模板
RHYTHM_TEMPLATES = [
    "紧-松-紧",
    "松-紧-松",
    "渐强",
    "渐弱",
    "均匀",
    "骤变",
    "呼吸型",
    "碎片型",
]

# 意象关键词（具象名词）
IMAGERY_KEYWORDS = {
    # 自然
    "山",
    "水",
    "风",
    "雨",
    "雪",
    "云",
    "雷",
    "光",
    "影",
    "月",
    "日",
    "星",
    "屋檐",
    "瓦",
    "砖",
    "墙",
    "门",
    "窗",
    "灯",
    "烛",
    "烟",
    "火",
    # 物件
    "刀",
    "剑",
    "枪",
    "鞭",
    "甲",
    "袍",
    "杯",
    "酒",
    "茶",
    # 动物
    "鸦",
    "鹰",
    "马",
    "鹿",
    "鱼",
    "蛇",
    "虫",
    # 身体局部
    "手",
    "指",
    "眼",
    "唇",
    "发",
    "肩",
    "脚",
    # 自然现象
    "雾",
    "霜",
    "霞",
    "夜",
    "晨",
    "暮",
}

# 第一/第三人称代词
FIRST_PERSON = {"我", "我们", "咱", "咱们"}
THIRD_PERSON = {"他", "她", "它", "他们", "她们", "它们"}


def analyze(text: str) -> Dict[str, Any]:
    """提取段落结构特征

    Returns dict with required keys:
        sentence_length_avg: float
        sentence_length_variance: float
        imagery_density: "low" | "medium" | "high"
        perspective: "主角" | "旁观" | "全知" | "物件" | "败者" | "第三人称"
        rhythm_pattern: one of RHYTHM_TEMPLATES
        verb_density: float (0-1, 粗略估算)
        adjective_ratio: float (0-1, 粗略估算)
    """
    if not text or not text.strip():
        return _safe_defaults()

    sentences = _split_sentences(text)
    if not sentences:
        return _safe_defaults()

    lens = [len(s) for s in sentences]
    avg = statistics.mean(lens)
    var = statistics.pvariance(lens) if len(lens) > 1 else 0.0

    return {
        "sentence_length_avg": round(avg, 2),
        "sentence_length_variance": round(var, 2),
        "imagery_density": _imagery_density(text),
        "perspective": _perspective(text),
        "rhythm_pattern": _rhythm_pattern(lens),
        "verb_density": _verb_density(text),
        "adjective_ratio": _adjective_ratio(text),
    }


def _safe_defaults() -> Dict[str, Any]:
    return {
        "sentence_length_avg": 0,
        "sentence_length_variance": 0,
        "imagery_density": "low",
        "perspective": "未知",
        "rhythm_pattern": "均匀",
        "verb_density": 0.0,
        "adjective_ratio": 0.0,
    }


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"[。！？!?]+", text)
    return [p.strip() for p in parts if p.strip()]


def _imagery_density(text: str) -> str:
    """统计意象关键词密度，分桶为 low/medium/high"""
    if not text:
        return "low"
    hits = sum(1 for w in IMAGERY_KEYWORDS if w in text)
    chars = len(text)
    if chars == 0:
        return "low"
    ratio = hits / max(1, chars / 50)  # 每 50 字一个意象算 1.0 密度
    if ratio < 0.5:
        return "low"
    if ratio < 1.5:
        return "medium"
    return "high"


def _perspective(text: str) -> str:
    """粗略判断视角"""
    first_count = sum(text.count(w) for w in FIRST_PERSON)
    third_count = sum(text.count(w) for w in THIRD_PERSON)
    if first_count > third_count and first_count > 0:
        return "主角"
    if third_count > 0:
        return "第三人称"
    return "旁观"


def _rhythm_pattern(lens: List[int]) -> str:
    """根据句长序列匹配节奏模板"""
    if len(lens) < 2:
        return "均匀"

    avg = statistics.mean(lens)
    if max(lens) - min(lens) < 3:
        return "均匀"

    # 标记每句相对均值
    marks = ["L" if x > avg * 1.3 else ("S" if x < avg * 0.7 else "M") for x in lens]

    # 渐强 / 渐弱
    if all(lens[i] <= lens[i + 1] for i in range(len(lens) - 1)):
        return "渐强"
    if all(lens[i] >= lens[i + 1] for i in range(len(lens) - 1)):
        return "渐弱"

    # 紧-松-紧 / 松-紧-松
    if len(marks) >= 3:
        if marks[0] == "S" and marks[-1] == "S" and "L" in marks[1:-1]:
            return "紧-松-紧"
        if marks[0] == "L" and marks[-1] == "L" and "S" in marks[1:-1]:
            return "松-紧-松"

    # 大跳变（极端值反复出现）
    if marks.count("L") + marks.count("S") > len(marks) * 0.6:
        return "骤变"

    # 短句多
    if marks.count("S") >= len(marks) * 0.5:
        return "碎片型"

    return "呼吸型"


def _verb_density(text: str) -> float:
    """粗略动词密度（仅基于常见动词词典）"""
    common_verbs = {
        "是",
        "有",
        "去",
        "来",
        "走",
        "看",
        "说",
        "想",
        "做",
        "起",
        "落",
        "抬",
        "举",
        "握",
        "推",
        "拉",
        "踏",
        "挥",
        "刺",
        "斩",
        "砍",
        "击",
        "打",
        "笑",
        "哭",
        "怒",
        "叹",
        "呼",
        "吸",
        "回",
        "转",
        "跳",
        "跑",
        "停",
    }
    if not text:
        return 0.0
    hits = sum(text.count(v) for v in common_verbs)
    return round(hits / max(1, len(text)), 3)


def _adjective_ratio(text: str) -> float:
    """粗略形容词比例（仅基于常见形容词词典）"""
    common_adj = {
        "冷",
        "热",
        "暖",
        "凉",
        "黑",
        "白",
        "红",
        "黄",
        "青",
        "紫",
        "高",
        "低",
        "深",
        "浅",
        "大",
        "小",
        "长",
        "短",
        "厚",
        "薄",
        "快",
        "慢",
        "急",
        "缓",
        "硬",
        "软",
        "重",
        "轻",
        "明",
        "暗",
        "美",
        "丑",
        "新",
        "旧",
        "强",
        "弱",
        "干",
        "湿",
        "粗",
        "细",
    }
    if not text:
        return 0.0
    hits = sum(text.count(a) for a in common_adj)
    return round(hits / max(1, len(text)), 3)
