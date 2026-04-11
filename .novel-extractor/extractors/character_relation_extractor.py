"""
Character relation extractor
Extracts co-occurrence relationships between characters from a novel/text.
Implements: extract_from_novel, process_extracted, and supports simple NER for PERSON names.
"""

from __future__ import annotations

import itertools
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from base_extractor import BaseExtractor


def _maybe_load_ner_model():
    # Try to use spaCy for robust NER if available; otherwise return None
    try:
        import spacy  # type: ignore

        # Try zh model first; fall back to English if not available
        try:
            model = spacy.load("zh_core_web_sm")
        except Exception:
            model = spacy.load("en_core_web_sm")
        return model
    except Exception:
        return None


_NER_MODEL = None  # Disabled by default - spacy NER too slow for large Chinese novels


def _detect_names(text: str) -> List[str]:
    """Detect person names in a text chunk.
    Priority: use a robust NER model if available, otherwise fall back to heuristic extract of 2-4 Chinese characters.
    """
    names = set()
    if _NER_MODEL is not None:
        try:
            doc = _NER_MODEL(text)
            for ent in doc.ents:
                if ent.label_ in {"PERSON", "PER"}:
                    nm = ent.text.strip()
                    if len(nm) >= 2:
                        names.add(nm)
        except Exception:
            pass

    # Fallback heuristic: two to four Chinese characters sequences
    if not names:
        for m in re.finditer(r"[\u4e00-\u9fa5]{2,4}(?:[\u4e00-\u9fa5]{1,2})?", text):
            tok = m.group(0).strip()
            if not tok:
                continue
            # filter obvious function words or noise
            if any(ch in tok for ch in ["的", "了", "与", "和"]):
                continue
            if len(tok) >= 2:
                names.add(tok)
    return sorted(names)


def _split_chapters(novel_text: str) -> Dict[int, str]:
    """Split the novel text into chapters and return a map {chapter_id: text}.
    Chapter boundaries are detected by lines containing patterns like '第X章' or 'Chapter N'.
    """
    chapters: Dict[int, str] = {}
    cur = 0
    buf: List[str] = []
    for line in novel_text.splitlines():
        if re.search(r"(第[一二三四五六七八九十百零]+章|Chapter\s*\d+)", line):
            if buf:
                chapters[cur] = "\n".join(buf).strip()
                buf = []
            cur += 1
        else:
            buf.append(line)
    if buf:
        chapters[cur] = "\n".join(buf).strip()
    return {k: v for k, v in chapters.items() if v}


def _sentences(text: str) -> List[str]:
    # Split by common sentence-ending punctuation, including Chinese ones
    parts = re.split(r"[。？！.!?]", text)
    return [p.strip() for p in parts if p.strip()]


def _contexts_for_pair(chunk: str, a: str, b: str, chapter_id: int) -> List[str]:
    sentences = _sentences(chunk)
    outs: List[str] = []
    for s in sentences:
        if a in s and b in s:
            outs.append(f"[Chapter {chapter_id}] {s.strip()}")
    return outs


class CharacterRelationExtractor(BaseExtractor):
    """Extractor that builds a simple character co-occurrence graph from a novel text."""

    name = "character_relation_extractor"

    def __init__(self):
        super().__init__("character_relation")

    def extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]:
        """Extract co-occurrence data from the given novel text.

        Args:
            content: 小说内容
            novel_id: 小说ID
            novel_path: 小说路径

        Returns:
            提取的人物共现关系列表
        """
        chapters = _split_chapters(content)
        cooc_map: Dict[Tuple[str, str], Dict[str, object]] = {}

        for cid, chunk in chapters.items():
            names_in_chunk = _detect_names(chunk)
            # Build pairwise co-occurrences among names detected in this chapter
            for i in range(len(names_in_chunk)):
                for j in range(i + 1, len(names_in_chunk)):
                    c1, c2 = sorted([names_in_chunk[i], names_in_chunk[j]])
                    key = (c1, c2)
                    if key not in cooc_map:
                        cooc_map[key] = {"count": 0, "contexts": []}
                    cooc_map[key]["count"] += 1
                    contexts = _contexts_for_pair(
                        chunk, names_in_chunk[i], names_in_chunk[j], cid
                    )
                    if contexts:
                        cooc_map[key]["contexts"].extend(contexts)

        # Normalize results into records
        records: List[Dict[str, object]] = []
        for (c1, c2), data in cooc_map.items():
            # Deduplicate contexts while preserving order
            seen = set()
            contexts_out: List[str] = []
            for ctxt in data["contexts"]:
                if ctxt not in seen:
                    contexts_out.append(ctxt)
                    seen.add(ctxt)
            records.append(
                {
                    "character1": c1,
                    "character2": c2,
                    "cooccurrence_count": int(data["count"]),
                    "cooccurrence_contexts": contexts_out,
                }
            )

        return records

    def process_extracted(self, items: List[dict]) -> List[dict]:
        # items is already in the format returned by extract_from_novel (list of records)
        return items if items else []
