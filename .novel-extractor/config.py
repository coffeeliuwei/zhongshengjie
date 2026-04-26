"""
小说提炼系统配置

定义所有提炼维度、优先级、输出路径
支持增量提炼和新维度扩展
"""

from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import sys

# ==================== 路径配置 ====================

# PROJECT_DIR 从文件自身位置推导：本文件在 .novel-extractor/，父目录即项目根
# 无论学生把项目装在哪个盘/目录都能自动找到，不硬编码
PROJECT_DIR = Path(__file__).resolve().parent.parent


def _load_config():
    """从 config.json 加载配置，失败时返回空字典"""
    try:
        if str(PROJECT_DIR) not in sys.path:
            sys.path.insert(0, str(PROJECT_DIR))
        from core.config_loader import get_config
        return get_config()
    except Exception:
        return {}


_cfg = _load_config()

# 小说资源目录 —— 从 config.json 的 novel_sources.directories 读取
_novel_dirs = _cfg.get("novel_sources", {}).get("directories", [])
NOVEL_SOURCE_DIR = Path(_novel_dirs[0]) if _novel_dirs else Path(r"E:\小说资源")

# 输出目录 —— 从 config.json 的 extractor.output_dir 读取
EXTRACTOR_DIR = PROJECT_DIR / ".novel-extractor"
OUTPUT_DIR = Path(_cfg.get("extractor", {}).get("output_dir", r"E:\novel_extracted"))
PROGRESS_DIR = EXTRACTOR_DIR / "progress"
CONVERTED_DIR = PROJECT_DIR / ".case-library" / "converted"
CASE_OUTPUT_DIR = PROJECT_DIR / ".case-library" / "cases"

# mobi 解压临时目录 —— 从 config.json 的 paths.mobi_temp_dir 读取
# 默认 E:\tmp_mobi，不能放 C 盘（mobi 解压体积大会塞满系统盘）
MOBI_TEMP_DIR = Path(_cfg.get("paths", {}).get("mobi_temp_dir", r"E:\tmp_mobi"))

# 向量库路径
VECTORSTORE_DIR = PROJECT_DIR / ".vectorstore"

# ==================== 提炼优先级 ====================


class Priority(Enum):
    HIGH = "high"  # 高价值 - 直接用于创作
    MEDIUM = "medium"  # 中价值 - 需适配后使用
    LOW = "low"  # 低价值 - 长期有益


# unified_config 兼容别名
DimensionCategory = Priority          # 外部代码用 DimensionCategory，实际等价于 Priority
EXTENDED_OUTPUT_DIR = OUTPUT_DIR      # unified_config 用 EXTENDED_OUTPUT_DIR，指向同一目录


# ==================== 提炼维度定义 ====================


@dataclass
class ExtractionDimension:
    """提炼维度定义"""

    id: str
    name: str
    description: str
    priority: Priority
    dependencies: List[str] = field(default_factory=list)
    output_format: str = "json"  # json, md, qdrant
    incremental: bool = True  # 是否支持增量提炼
    auto_sync: bool = True  # 是否自动同步到向量库

    # 提取器配置
    extractor_class: str = ""
    extractor_config: Dict[str, Any] = field(default_factory=dict)

    @property
    def category(self) -> Priority:
        """unified_config 兼容：category 是 priority 的别名"""
        return self.priority

    @property
    def enabled(self) -> bool:
        """unified_config 兼容：默认启用"""
        return True


# ==================== 所有提炼维度 ====================

EXTRACTION_DIMENSIONS = {
    # ========== 高价值 ==========
    "case": ExtractionDimension(
        id="case",
        name="场景案例库",
        description="提取22种场景类型的标杆案例（打脸/高潮/战斗/对话等）",
        priority=Priority.HIGH,
        output_format="json",
        incremental=True,
        extractor_class="CaseExtractor",
        extractor_config={
            "scene_types": [
                "开篇场景", "人物出场", "战斗场景", "对话场景", "情感场景",
                "悬念场景", "转折场景", "结尾场景", "环境场景", "心理场景",
                "修炼突破", "势力登场", "资源获取", "探索发现", "伏笔回收",
                "危机降临", "成长蜕变", "情报揭示", "社交场景", "阴谋揭露",
                "冲突升级", "团队组建", "打脸场景", "高潮场景", "反派出场",
                "恢复休养", "回忆场景", "伏笔设置",
            ],
            "min_quality_score": 6.0,
            "max_cases_per_chapter": 3,
        },
    ),
    "dialogue_style": ExtractionDimension(
        id="dialogue_style",
        name="势力对话风格库",
        description="为10大势力提取专属对话风格特征（用词、句式、语气）",
        priority=Priority.HIGH,
        dependencies=["case_library"],
        extractor_class="DialogueStyleExtractor",
        extractor_config={
            "min_dialogues": 100,  # 每个势力最少对话数
            "use_llm": True,  # 使用LLM标注
            "faction_mapping": {
                "玄幻奇幻": ["东方修仙", "西方魔法"],
                "武侠仙侠": ["东方修仙"],
                "现代都市": ["世俗帝国", "商盟"],
                "历史军事": ["世俗帝国"],
                "科幻灵异": ["科技文明", "AI文明"],
                "游戏竞技": ["佣兵联盟"],
                "青春校园": ["世俗帝国"],
                "女频言情": ["商盟", "神殿/教会"],
            },
        },
    ),
    "power_cost": ExtractionDimension(
        id="power_cost",
        name="力量体系代价库",
        description="提取各力量体系使用代价的具体描写方式",
        priority=Priority.HIGH,
        dependencies=["case_library"],
        extractor_class="PowerCostExtractor",
        extractor_config={
            "power_types": ["修仙", "魔法", "神术", "科技", "兽力", "AI力", "异能"],
            "cost_keywords": {
                "修仙": ["真气耗尽", "经脉", "神识", "喷血", "脸色苍白"],
                "魔法": ["魔力", "精神", "反噬", "流鼻血"],
                "神术": ["信仰", "圣光", "灵魂", "疲惫"],
                "科技": ["能源", "设备", "过载", "麻木"],
                "兽力": ["血脉", "骨骼", "肌肉", "理智"],
                "AI力": ["算力", "系统", "卡顿", "数据"],
                "异能": ["基因", "身体", "异变", "精神"],
            },
            "use_llm": True,
        },
    ),
    "character_relation": ExtractionDimension(
        id="character_relation",
        name="人物关系图谱",
        description="提取人物共现关系，构建关系网络",
        priority=Priority.HIGH,
        dependencies=["case_library"],
        extractor_class="CharacterRelationExtractor",
        extractor_config={
            "min_cooccurrence": 2,  # 最小共现次数
            "relation_types": [
                "爱慕",
                "敌对",
                "师徒",
                "同门",
                "血缘",
                "盟友",
                "主仆",
                "对手",
            ],
            "use_ner": True,  # 使用NER识别人物
        },
    ),
    # ========== 中价值 ==========
    "emotion_arc": ExtractionDimension(
        id="emotion_arc",
        name="情感曲线模板",
        description="提取章节/卷的情感变化曲线，识别6种基本形状",
        priority=Priority.MEDIUM,
        dependencies=["case_library"],
        extractor_class="EmotionArcExtractor",
        extractor_config={
            "arc_types": [
                "rags_to_riches",  # 上升型
                "tragedy",  # 悲剧型
                "man_in_a_hole",  # V型
                "icarus",  # 倒V型
                "cinderella",  # N型
                "oedipus",  # W型
            ],
            "window_size": 500,  # 滑动窗口大小
            "use_transformer": True,
        },
    ),
    "power_vocabulary": ExtractionDimension(
        id="power_vocabulary",
        name="力量体系词汇库",
        description="提取各题材专有名词（力量体系、地名、组织、势力等）",
        priority=Priority.MEDIUM,
        dependencies=["case_library"],
        extractor_class="VocabularyExtractor",
        extractor_config={
            "categories": {
                "修仙": {
                    "境界": ["炼气", "筑基", "金丹", "元婴", "化神", "渡劫"],
                    "功法": ["剑诀", "法术", "阵法", "符箓"],
                    "物品": ["灵石", "法宝", "丹药", "符咒"],
                },
                "魔法": {
                    "等级": ["一级", "二级", "三级", "禁咒"],
                    "元素": ["火系", "水系", "风系", "土系", "雷系"],
                },
                "科技": {
                    "改造": ["机甲", "芯片", "能源核心"],
                    "等级": ["一级改造", "二级改造"],
                },
            },
            "min_frequency": 3,
            "use_ner": True,
        },
    ),
    "chapter_structure": ExtractionDimension(
        id="chapter_structure",
        name="章节结构模式",
        description="分析章节长度分布、场景分布、节奏模式",
        priority=Priority.MEDIUM,
        dependencies=["novel_index"],
        extractor_class="ChapterStructureExtractor",
        extractor_config={
            "analyze_scene_distribution": True,
            "analyze_length_patterns": True,
            "analyze_pacing": True,
        },
    ),
    # ========== 低价值 ==========
    "author_style": ExtractionDimension(
        id="author_style",
        name="作者风格指纹",
        description="提取作者写作风格特征，用于风格模仿",
        priority=Priority.LOW,
        dependencies=["novel_index"],
        extractor_class="AuthorStyleExtractor",
        extractor_config={
            "features": [
                "sentence_length",  # 句长分布
                "vocabulary_richness",  # 词汇丰富度
                "pos_distribution",  # 词性分布
                "dialogue_ratio",  # 对话比例
            ],
            "min_chapters": 10,  # 最少章节数
        },
    ),
    "foreshadow_pair": ExtractionDimension(
        id="foreshadow_pair",
        name="伏笔回收配对",
        description="识别伏笔设置与回收的配对关系",
        priority=Priority.LOW,
        dependencies=["case_library"],
        extractor_class="ForeshadowPairExtractor",
        extractor_config={
            "similarity_threshold": 0.7,
            "max_distance_chapters": 50,
            "use_llm": True,
        },
    ),
    "worldview_element": ExtractionDimension(
        id="worldview_element",
        name="世界观元素",
        description="提取地点、组织、势力命名规律",
        priority=Priority.LOW,
        dependencies=["case_library"],
        extractor_class="WorldviewExtractor",
        extractor_config={
            "entity_types": ["地点", "组织", "势力", "物品"],
            "use_ner": True,
        },
    ),
    "technique": ExtractionDimension(
        id="technique",
        name="创作技法精炼",
        description="从原始小说中精炼提取创作技法，合并到现有技法库",
        priority=Priority.LOW,
        dependencies=["case_library"],
        extractor_class="TechniqueExtractor",
        extractor_config={
            "output_to_library": True,
        },
    ),
}


# ==================== 题材-势力映射 ====================

GENRE_TO_FACTION = {
    "玄幻奇幻": ["东方修仙", "西方魔法"],
    "武侠仙侠": ["东方修仙"],
    "现代都市": ["世俗帝国", "商盟", "佣兵联盟"],
    "历史军事": ["世俗帝国"],
    "科幻灵异": ["科技文明", "AI文明"],
    "游戏竞技": ["佣兵联盟", "科技文明"],
    "青春校园": ["世俗帝国"],
    "女频言情": ["商盟", "神殿/教会"],
    "悬疑推理": ["佣兵联盟"],
}


# ==================== 势力对话风格特征 ====================

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
    "神殿/教会": {
        "用词特征": ["神明", "信徒", "圣光", "教义", "恩赐"],
        "句式特征": ["引用教义", "祈祷式", "宣告式"],
        "语气特征": ["虔诚", "庄重", "信仰坚定"],
    },
    "佣兵联盟": {
        "用词特征": ["雇主", "任务", "佣金", "搭档", "赏金"],
        "句式特征": ["简洁直接", "利益导向", "行动优先"],
        "语气特征": ["务实", "谨慎", "自由"],
    },
    "商盟": {
        "用词特征": ["交易", "利益", "合作", "价格", "伙伴"],
        "句式特征": ["谈判式", "人情世故", "迂回表达"],
        "语气特征": ["圆滑", "精明", "客气"],
    },
    "世俗帝国": {
        "用词特征": ["陛下", "大人", "臣", "属下", "百姓"],
        "句式特征": ["等级分明", "礼仪式", "正式表达"],
        "语气特征": ["恭敬", "忠诚", "严肃"],
    },
    "科技文明": {
        "用词特征": ["数据", "系统", "效率", "优化", "参数"],
        "句式特征": ["精确表达", "数据化", "逻辑链条"],
        "语气特征": ["理性", "冷静", "技术导向"],
    },
    "兽族文明": {
        "用词特征": ["血脉", "部落", "图腾", "族人", "狩猎"],
        "句式特征": ["直接表达", "情感外露", "集体意识"],
        "语气特征": ["野性", "直率", "情感强烈"],
    },
    "AI文明": {
        "用词特征": ["计算", "概率", "执行", "优化", "迭代"],
        "句式特征": ["纯逻辑", "无情感", "数据化"],
        "语气特征": ["冷冰冰", "精确", "无波动"],
    },
    "异化人文明": {
        "用词特征": ["同类", "边缘", "生存", "进化", "基因"],
        "句式特征": ["矛盾表达", "挣扎感", "身份追问"],
        "语气特征": ["焦虑", "渴望", "矛盾"],
    },
}


# ==================== 输出文件路径 ====================


def get_output_path(dimension_id: str, filename: str = None) -> Path:
    """获取输出文件路径"""
    dim = EXTRACTION_DIMENSIONS.get(dimension_id)
    if not dim:
        raise ValueError(f"Unknown dimension: {dimension_id}")

    output_dir = OUTPUT_DIR / dimension_id
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        return output_dir / filename
    return output_dir


def get_progress_path(dimension_id: str) -> Path:
    """获取进度文件路径"""
    return PROGRESS_DIR / f"{dimension_id}_progress.json"


# ==================== 初始化 ====================


def init_extractor():
    """初始化提炼系统"""
    # 创建目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

    # 创建各维度输出目录
    for dim_id in EXTRACTION_DIMENSIONS:
        get_output_path(dim_id)

    print(f"[OK] Novel Extractor initialized at {EXTRACTOR_DIR}")
    print(f"     Source: {NOVEL_SOURCE_DIR}")
    print(f"     Dimensions: {len(EXTRACTION_DIMENSIONS)}")

# unified_config 兼容：init_system 是 init_extractor 的别名
def init_system():
    """unified_config 兼容别名，等价于 init_extractor()"""
    init_extractor()
