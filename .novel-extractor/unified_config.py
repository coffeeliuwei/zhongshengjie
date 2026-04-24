"""
众生界 - 完整小说提炼系统配置

整合所有提炼维度：
1. 核心维度 - 场景案例提取（原.case-library）
2. 扩展维度 - 高中低价值提炼（原.novel-extractor）

使用方法：
    python run.py --all              # 提炼所有维度
    python run.py --priority high     # 只提炼高价值
    python run.py --dimension case    # 只提取场景案例
"""

from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import sys

# ==================== 路径配置 ====================

PROJECT_DIR = Path(r"D:\动画\众生界")


def _get_novel_source_dir() -> Path:
    """从配置加载小说资源目录"""
    try:
        if str(PROJECT_DIR) not in sys.path:
            sys.path.insert(0, str(PROJECT_DIR))

        from core.config_loader import get_config

        config = get_config()
        novel_sources = config.get("novel_sources", {})
        directories = novel_sources.get("directories", [])

        if directories:
            # 返回第一个配置的目录
            return Path(directories[0])

        # 如果未配置，返回默认路径（兼容旧版）
        return Path(r"E:\小说资源")
    except Exception:
        # 如果加载失败，返回默认路径
        return Path(r"E:\小说资源")


NOVEL_SOURCE_DIR = _get_novel_source_dir()

# 案例库路径（核心维度）
CASE_LIBRARY_DIR = PROJECT_DIR / ".case-library"
CASE_OUTPUT_DIR = CASE_LIBRARY_DIR / "cases"
CONVERTED_DIR = CASE_LIBRARY_DIR / "converted"

# 扩展提炼路径
EXTRACTOR_DIR = PROJECT_DIR / ".novel-extractor"
EXTENDED_OUTPUT_DIR = EXTRACTOR_DIR / "extracted"
PROGRESS_DIR = EXTRACTOR_DIR / "progress"

# 向量库路径
VECTORSTORE_DIR = PROJECT_DIR / ".vectorstore"


# ==================== 维度分类 ====================


class DimensionCategory(Enum):
    """维度类别"""

    CORE = "core"  # 核心维度 - 场景案例
    HIGH = "high"  # 高价值扩展
    MEDIUM = "medium"  # 中价值扩展
    LOW = "low"  # 低价值扩展


# ==================== 维度定义 ====================


@dataclass
class ExtractionDimension:
    """提炼维度定义"""

    id: str
    name: str
    description: str
    category: DimensionCategory
    output_path: Path = None
    dependencies: List[str] = field(default_factory=list)
    incremental: bool = True
    enabled: bool = True

    # 提取器配置
    extractor_module: str = ""
    extractor_class: str = ""
    config: Dict[str, Any] = field(default_factory=dict)


# ==================== 所有提炼维度 ====================

EXTRACTION_DIMENSIONS = {
    # ========== 核心维度 - 场景案例提取 ==========
    "case": ExtractionDimension(
        id="case",
        name="场景案例库",
        description="提取22种场景类型的标杆案例（打脸/高潮/战斗/对话等）",
        category=DimensionCategory.CORE,
        output_path=CASE_OUTPUT_DIR,
        extractor_module="extractors.case_extractor",
        extractor_class="CaseExtractor",
        config={
            "scene_types": [
                "开篇场景",
                "人物出场",
                "战斗场景",
                "对话场景",
                "情感场景",
                "悬念场景",
                "转折场景",
                "结尾场景",
                "环境场景",
                "心理场景",
                "修炼突破",
                "势力登场",
                "资源获取",
                "探索发现",
                "伏笔回收",
                "危机降临",
                "成长蜕变",
                "情报揭示",
                "社交场景",
                "阴谋揭露",
                "冲突升级",
                "团队组建",
                "打脸场景",
                "高潮场景",
                "反派出场",
                "恢复休养",
                "回忆场景",
                "伏笔设置",
            ],
            "min_quality_score": 6.0,
            "max_cases_per_chapter": 3,
            "genres": [
                "玄幻奇幻",
                "武侠仙侠",
                "现代都市",
                "历史军事",
                "科幻灵异",
                "青春校园",
                "游戏竞技",
                "女频言情",
            ],
        },
    ),
    # ========== 高价值扩展 ==========
    "dialogue_style": ExtractionDimension(
        id="dialogue_style",
        name="势力对话风格库",
        description="为10大势力提取专属对话风格特征（用词、句式、语气）",
        category=DimensionCategory.HIGH,
        output_path=EXTENDED_OUTPUT_DIR / "dialogue_style",
        dependencies=["case"],
        extractor_module="extractors.dialogue_style_extractor",
        extractor_class="DialogueStyleExtractor",
        config={
            "faction_mapping": {
                "玄幻奇幻": ["东方修仙", "西方魔法"],
                "武侠仙侠": ["东方修仙"],
                "现代都市": ["世俗帝国", "商盟"],
                "历史军事": ["世俗帝国"],
                "科幻灵异": ["科技文明", "AI文明"],
                "游戏竞技": ["佣兵联盟"],
                "青春校园": ["世俗帝国"],
                "女频言情": ["商盟", "神殿/教会"],
            }
        },
    ),
    "power_cost": ExtractionDimension(
        id="power_cost",
        name="力量体系代价库",
        description="提取各力量体系使用代价的具体描写方式",
        category=DimensionCategory.HIGH,
        output_path=EXTENDED_OUTPUT_DIR / "power_cost",
        dependencies=["case"],
        extractor_module="extractors.power_cost_extractor",
        extractor_class="PowerCostExtractor",
        config={
            "power_types": ["修仙", "魔法", "神术", "科技", "兽力", "AI力", "异能"],
        },
    ),
    "character_relation": ExtractionDimension(
        id="character_relation",
        name="人物关系图谱",
        description="提取人物共现关系，构建关系网络",
        category=DimensionCategory.HIGH,
        output_path=EXTENDED_OUTPUT_DIR / "character_relation",
        dependencies=["case"],
        extractor_module="extractors.character_relation_extractor",
        extractor_class="CharacterRelationExtractor",
        config={
            "min_cooccurrence": 3,
            "use_ner": True,
        },
    ),
    # ========== 中价值扩展 ==========
    "emotion_arc": ExtractionDimension(
        id="emotion_arc",
        name="情感曲线模板",
        description="提取章节/卷的情感变化曲线，识别6种基本形状",
        category=DimensionCategory.MEDIUM,
        output_path=EXTENDED_OUTPUT_DIR / "emotion_arc",
        extractor_module="extractors.emotion_arc_extractor",
        extractor_class="EmotionArcExtractor",
    ),
    "power_vocabulary": ExtractionDimension(
        id="power_vocabulary",
        name="力量体系词汇库",
        description="提取修仙/魔法/科技等专有名词",
        category=DimensionCategory.MEDIUM,
        output_path=EXTENDED_OUTPUT_DIR / "power_vocabulary",
        extractor_module="extractors.vocabulary_extractor",
        extractor_class="VocabularyExtractor",
    ),
    "chapter_structure": ExtractionDimension(
        id="chapter_structure",
        name="章节结构模式",
        description="分析章节长度分布、场景分布、节奏模式",
        category=DimensionCategory.MEDIUM,
        output_path=EXTENDED_OUTPUT_DIR / "chapter_structure",
        extractor_module="extractors.chapter_structure_extractor",
        extractor_class="ChapterStructureExtractor",
    ),
    # ========== 低价值扩展 ==========
    "author_style": ExtractionDimension(
        id="author_style",
        name="作者风格指纹",
        description="提取作者写作风格特征，用于风格模仿",
        category=DimensionCategory.LOW,
        output_path=EXTENDED_OUTPUT_DIR / "author_style",
        extractor_module="extractors.author_style_extractor",
        extractor_class="AuthorStyleExtractor",
    ),
    "foreshadow_pair": ExtractionDimension(
        id="foreshadow_pair",
        name="伏笔回收配对",
        description="识别伏笔设置与回收的配对关系",
        category=DimensionCategory.LOW,
        output_path=EXTENDED_OUTPUT_DIR / "foreshadow_pair",
        extractor_module="extractors.foreshadow_pair_extractor",
        extractor_class="ForeshadowPairExtractor",
    ),
    "worldview_element": ExtractionDimension(
        id="worldview_element",
        name="世界观元素",
        description="提取地点、组织、势力命名规律",
        category=DimensionCategory.LOW,
        output_path=EXTENDED_OUTPUT_DIR / "worldview_element",
        extractor_module="extractors.worldview_element_extractor",
        extractor_class="WorldviewElementExtractor",
    ),
    # ========== 技法精炼 ==========
    "technique": ExtractionDimension(
        id="technique",
        name="创作技法精炼",
        description="从原始小说中精炼提取创作技法，合并到现有技法库",
        category=DimensionCategory.LOW,
        output_path=EXTENDED_OUTPUT_DIR / "technique",
        extractor_module="extractors.technique_extractor",
        extractor_class="TechniqueExtractor",
        config={
            "output_to_library": True,  # 保存到创作技法目录
        },
    ),
}


# ==================== 数据源配置 ====================

DATA_SOURCES = {
    "primary": {
        "path": NOVEL_SOURCE_DIR,
        "description": "主小说库",
        "total_files": 6245,
        "total_size_gb": 15.68,
    },
    "converted": {
        "path": CONVERTED_DIR,
        "description": "已转换格式",
    },
}


# ==================== 势力设定 ====================

FACTIONS = [
    "东方修仙",
    "西方魔法",
    "神殿/教会",
    "佣兵联盟",
    "商盟",
    "世俗帝国",
    "科技文明",
    "兽族文明",
    "AI文明",
    "异化人文明",
]

FACTION_DIALOGUE_TRAITS = {
    "东方修仙": {
        "用词特征": ["道友", "师尊", "师弟", "本座", "贫道", "在下"],
        "句式特征": ["倒装句", "文言色彩", "省略主语"],
        "语气特征": ["淡然", "内敛", "点到为止"],
    },
    "西方魔法": {
        "用词特征": ["阁下", "先生", "女士", "导师", "学徒"],
        "句式特征": ["学术表达", "逻辑推理", "辩论式"],
        "语气特征": ["理性", "好奇", "探索"],
    },
    # ... 其他势力见完整配置
}

POWER_COST_EXPRESSIONS = {
    "修仙": ["真气耗尽", "经脉剧痛", "神识涣散", "脸色苍白", "喷血"],
    "魔法": ["魔力枯竭", "精神萎靡", "流鼻血", "反噬", "昏迷"],
    "神术": ["信仰动摇", "圣光灼烧", "灵魂疲惫"],
    "科技": ["能源耗尽", "设备过载", "身体麻木"],
    "兽力": ["血脉燃烧", "骨骼崩解", "失去理智"],
    "AI力": ["算力耗尽", "系统过载", "反应变慢"],
    "异能": ["基因不稳定", "身体异变", "精神创伤"],
}


# ==================== 输出路径函数 ====================


def get_output_path(dimension_id: str, filename: str = None) -> Path:
    """获取输出路径"""
    dim = EXTRACTION_DIMENSIONS.get(dimension_id)
    if not dim:
        raise ValueError(f"Unknown dimension: {dimension_id}")

    output_dir = dim.output_path or EXTENDED_OUTPUT_DIR / dimension_id
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        return output_dir / filename
    return output_dir


def get_progress_path(dimension_id: str) -> Path:
    """获取进度文件路径"""
    return PROGRESS_DIR / f"{dimension_id}_progress.json"


# ==================== 初始化 ====================


def init_system():
    """初始化系统"""
    # 创建核心目录
    CASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CONVERTED_DIR.mkdir(parents=True, exist_ok=True)

    # 创建扩展目录
    EXTENDED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

    # 创建各维度输出目录
    for dim_id, dim in EXTRACTION_DIMENSIONS.items():
        if dim.output_path:
            dim.output_path.mkdir(parents=True, exist_ok=True)

    print(f"[OK] 小说提炼系统初始化完成")
    print(f"     数据源: {NOVEL_SOURCE_DIR}")
    print(f"     案例输出: {CASE_OUTPUT_DIR}")
    print(f"     扩展输出: {EXTENDED_OUTPUT_DIR}")
    print(f"     维度数量: {len(EXTRACTION_DIMENSIONS)}")


# ==================== 维度统计 ====================


def get_dimension_stats() -> Dict[str, int]:
    """获取各类别维度数量"""
    stats = {
        "core": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "total": len(EXTRACTION_DIMENSIONS),
    }

    for dim in EXTRACTION_DIMENSIONS.values():
        stats[dim.category.value] += 1

    return stats


if __name__ == "__main__":
    init_system()

    stats = get_dimension_stats()
    print(f"\n维度统计:")
    print(f"  核心: {stats['core']}")
    print(f"  高价值: {stats['high']}")
    print(f"  中价值: {stats['medium']}")
    print(f"  低价值: {stats['low']}")
    print(f"  总计: {stats['total']}")
