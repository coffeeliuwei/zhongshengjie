"""
伏笔回收配对提取器
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from foreshadow_pair_extractor import (
    ForeshadowPairExtractor as _ForeshadowPairExtractor,
    extract_foreshadow_pairs,
)


class ForeshadowPairExtractor(_ForeshadowPairExtractor):
    """伏笔回收配对提取器（代理）"""

    pass


__all__ = ["ForeshadowPairExtractor", "extract_foreshadow_pairs"]
