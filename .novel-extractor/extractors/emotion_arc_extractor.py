"""
情感曲线提取器
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from emotion_arc_extractor import (
    EmotionArcExtractor as _EmotionArcExtractor,
    extract_emotion_arcs,
)


class EmotionArcExtractor(_EmotionArcExtractor):
    """情感曲线提取器（代理）"""

    pass


__all__ = ["EmotionArcExtractor", "extract_emotion_arcs"]
