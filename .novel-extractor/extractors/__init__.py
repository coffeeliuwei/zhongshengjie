"""
提取器模块

包含所有提炼维度的提取器：
- case_extractor: 场景案例提取（核心维度）
- dialogue_style_extractor: 势力对话风格
- power_cost_extractor: 力量体系代价
- character_relation_extractor: 人物关系图谱
- emotion_arc_extractor: 情感曲线
- vocabulary_extractor: 力量词汇
- chapter_structure_extractor: 章节结构模式
- author_style_extractor: 作者风格指纹
- foreshadow_pair_extractor: 伏笔配对
- worldview_element_extractor: 世界观元素
- technique_extractor: 创作技法精炼
"""

from .case_extractor import CaseExtractor
from .dialogue_style_extractor import DialogueStyleExtractor
from .power_cost_extractor import PowerCostExtractor
from .character_relation_extractor import CharacterRelationExtractor
from .emotion_arc_extractor import EmotionArcExtractor
from .vocabulary_extractor import VocabularyExtractor
from .chapter_structure_extractor import ChapterStructureExtractor
from .author_style_extractor import AuthorStyleExtractor
from .foreshadow_pair_extractor import ForeshadowPairExtractor
from .worldview_element_extractor import WorldviewElementExtractor
from .technique_extractor import TechniqueExtractor

__all__ = [
    "CaseExtractor",
    "DialogueStyleExtractor",
    "PowerCostExtractor",
    "CharacterRelationExtractor",
    "EmotionArcExtractor",
    "VocabularyExtractor",
    "ChapterStructureExtractor",
    "AuthorStyleExtractor",
    "ForeshadowPairExtractor",
    "WorldviewElementExtractor",
    "TechniqueExtractor",
]
