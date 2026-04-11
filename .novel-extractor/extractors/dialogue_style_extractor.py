"""
势力对话风格提取器

从小说中提取各势力的对话风格特征：
- 用词特征
- 句式特征
- 语气特征

用于Generator生成符合势力风格的角色对话
"""

import sys
from pathlib import Path

# 导入原提取器
sys.path.insert(0, str(Path(__file__).parent.parent))
from dialogue_style_extractor import (
    DialogueStyleExtractor as _DialogueStyleExtractor,
    extract_dialogue_styles,
)


class DialogueStyleExtractor(_DialogueStyleExtractor):
    """势力对话风格提取器（代理）"""

    pass


__all__ = ["DialogueStyleExtractor", "extract_dialogue_styles"]
