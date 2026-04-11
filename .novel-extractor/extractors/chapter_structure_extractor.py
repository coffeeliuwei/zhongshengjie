"""
章节结构模式提取器

分析章节的节奏模式：
- 章节长度分布
- 场景分布
- 开头结尾模式
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from base_extractor import BaseExtractor


class ChapterStructureExtractor(BaseExtractor):
    """章节结构模式提取器"""

    def __init__(self):
        super().__init__("chapter_structure")
        self._extracted = None
        self.novel_id = None

    def _split_into_chapters(self, content: str) -> List[Dict[str, Any]]:
        """分割章节"""
        if not content:
            return []

        markers = [
            r"(Chapter\s+\d+)",
            r"(第\d+章)",
            r"(第[一二三四五六七八九十百千万]+章)",
        ]

        pattern = "|".join(markers)
        parts = re.split(pattern, content)

        chapters = []
        buffer = []

        for chunk in parts:
            if not chunk:
                continue
            if re.match(pattern, chunk):
                if buffer:
                    chapters.append({"text": "".join(buffer).strip()})
                    buffer = []
                buffer.append(chunk.strip())
            else:
                buffer.append(chunk)

        if buffer:
            chapters.append({"text": "".join(buffer).strip()})

        cleaned = []
        for ch in chapters:
            text = ch.get("text", "").strip()
            if text:
                cleaned.append({"text": text})

        return cleaned or [{"text": content.strip()}]

    def extract_from_novel(self, content: str, novel_id: str, novel_path) -> List[dict]:
        """从小说提取章节结构"""
        self.novel_id = novel_id

        chapters = self._split_into_chapters(content)

        lengths = [len(ch["text"]) for ch in chapters]

        scene_counter = Counter()
        for ch in chapters:
            text = ch.get("text", "")
            # 简单场景识别
            for keyword in ["战斗", "对话", "情感", "悬念", "转折", "环境", "心理"]:
                if keyword in text[:200]:
                    scene_counter[keyword] += 1

        chapter_count = len(chapters)
        avg_chapter_length = sum(lengths) / chapter_count if chapter_count > 0 else 0.0

        total_scene = sum(scene_counter.values()) or 1
        scene_distribution = {
            k: round(v / total_scene, 3) for k, v in scene_counter.items()
        }

        record = {
            "novel_id": novel_id,
            "chapter_count": chapter_count,
            "avg_chapter_length": round(avg_chapter_length, 1),
            "scene_distribution": scene_distribution,
            "rhythm_pattern": self._identify_rhythm(lengths),
        }

        return [record]

    def process_extracted(self, items: List[dict]) -> List[dict]:
        """处理提取结果"""
        return items

    def _identify_rhythm(self, lengths: List[int]) -> str:
        """识别节奏模式"""
        n = len(lengths)
        if n < 2:
            return "insufficient_data"

        first, last = lengths[0], lengths[-1]

        # 检查单调性
        increasing = all(lengths[i] <= lengths[i + 1] for i in range(n - 1))
        decreasing = all(lengths[i] >= lengths[i + 1] for i in range(n - 1))

        if increasing and last > first * 1.2:
            return "gradual_acceleration"
        elif decreasing and last < first * 0.8:
            return "gradual_deceleration"
        elif increasing:
            return "increasing_pace"
        elif decreasing:
            return "decreasing_pace"
        else:
            avg_len = sum(lengths) / n
            std_dev = (sum((x - avg_len) ** 2 for x in lengths) / n) ** 0.5
            if std_dev > max(1, avg_len * 0.2):
                return "irregular_rhythm"
            else:
                return "moderate_rhythm"
