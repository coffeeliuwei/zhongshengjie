"""
作者风格指纹提取器
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from author_style_extractor import (
    AuthorStyleExtractor as _AuthorStyleExtractor,
    extract_author_styles,
)


class AuthorStyleExtractor(_AuthorStyleExtractor):
    """作者风格指纹提取器（代理）"""

    pass


__all__ = ["AuthorStyleExtractor", "extract_author_styles"]
