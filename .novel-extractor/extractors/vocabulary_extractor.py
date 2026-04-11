"""
力量体系词汇提取器
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from vocabulary_extractor import (
    VocabularyExtractor as _VocabularyExtractor,
    extract_vocabulary,
)


class VocabularyExtractor(_VocabularyExtractor):
    """力量体系词汇提取器（代理）"""

    pass


__all__ = ["VocabularyExtractor", "extract_vocabulary"]
