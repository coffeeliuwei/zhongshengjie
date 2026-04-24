#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一案例提取脚本 v3.0 - Ex3语义分组版
=====================================

融合最佳实践：
- Ex3语义分组场景识别（使用sentence-transformers）
- 17种核心场景类型
- 多维度质量评分
- 完整元数据标注
- 情绪价值评分

使用方法：
    python unified_case_extractor.py --scan       # 扫描所有文件
    python unified_case_extractor.py --extract    # 提取案例
    python unified_case_extractor.py --extract --no-semantic  # 快速模式（不使用语义分组）
    python unified_case_extractor.py --stats      # 查看统计
"""

import os
import sys
import json
import re
import uuid
import hashlib
import logging
import warnings
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from collections import defaultdict

# 抑制警告
warnings.filterwarnings("ignore")

# Windows编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 配置
PROJECT_DIR = Path(__file__).parent.parent.parent
CASE_LIBRARY_DIR = PROJECT_DIR / ".case-library"
CONVERTED_DIR = CASE_LIBRARY_DIR / "converted"
CASES_DIR = CASE_LIBRARY_DIR / "cases"
LOGS_DIR = CASE_LIBRARY_DIR / "logs"
INDEX_FILE = CASE_LIBRARY_DIR / "unified_index.json"
STATS_FILE = CASE_LIBRARY_DIR / "unified_stats.json"
SOURCES_FILE = CASE_LIBRARY_DIR / "sources.json"


def _load_novel_directories() -> List[str]:
    """从配置加载小说资源目录"""
    try:
        # 添加项目根目录到路径
        if str(PROJECT_DIR) not in sys.path:
            sys.path.insert(0, str(PROJECT_DIR))

        from core.config_loader import get_config

        config = get_config()
        novel_sources = config.get("novel_sources", {})
        directories = novel_sources.get("directories", [])

        # 如果配置为空，返回空列表
        if not directories:
            logger.warning(
                "配置文件中未找到 novel_sources.directories，将只扫描 converted 目录"
            )
            return []

        return directories
    except Exception as e:
        # 如果加载失败，返回空列表
        if "logger" in globals():
            logger.warning(f"加载配置失败: {e}，将只扫描 converted 目录")
        return []


# 原始资源目录（从配置加载）
ORIGINAL_DIRS = _load_novel_directories()

# 确保目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "unified_extraction.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================
# Ex3语义分组模块
# ============================================


class SemanticSegmenter:
    """
    基于Ex3方法的语义分段器

    使用语义相似度识别场景边界：
    - 相邻段落语义相似度低 = 场景转换
    - 参考：Ex3论文使用CoSENT模型，余弦距离阈值0.6
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = None
        self.model_name = model_name
        self.similarity_threshold = 0.6  # Ex3论文阈值

    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(f"加载语义模型: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                logger.info("语义模型加载完成")
            except ImportError:
                logger.warning("未安装sentence-transformers，将使用关键词模式")
                return False
            except Exception as e:
                logger.warning(f"模型加载失败: {e}，将使用关键词模式")
                return False
        return True

    def segment_text(self, text: str, min_segment_length: int = 300) -> List[Dict]:
        """
        使用语义相似度分割文本为场景片段

        Args:
            text: 输入文本
            min_segment_length: 最小片段长度

        Returns:
            场景片段列表，每个片段包含 {text, start, end, boundary_score}
        """
        if not self._load_model():
            return self._fallback_segment(text, min_segment_length)

        # 1. 按段落分割（保留换行）
        paragraphs = self._split_paragraphs(text)
        if len(paragraphs) < 2:
            return [{"text": text, "start": 0, "end": len(text), "boundary_score": 0}]

        # 2. 计算段落嵌入（批量处理提高效率）
        try:
            para_texts = [p["text"][:500] for p in paragraphs]  # 限制长度
            embeddings = self.model.encode(para_texts, show_progress_bar=False)
        except Exception as e:
            logger.warning(f"嵌入计算失败: {e}")
            return self._fallback_segment(text, min_segment_length)

        # 3. 计算相邻段落语义相似度
        import numpy as np

        similarities = []
        for i in range(len(embeddings) - 1):
            # 余弦相似度
            sim = np.dot(embeddings[i], embeddings[i + 1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1]) + 1e-8
            )
            similarities.append(sim)

        # 4. 识别场景边界（相似度低于阈值）
        boundaries = [0]  # 起始位置
        boundary_scores = []

        for i, sim in enumerate(similarities):
            if sim < self.similarity_threshold:
                boundaries.append(i + 1)  # 段落索引
                boundary_scores.append(1 - sim)  # 边界强度
            else:
                boundary_scores.append(0)

        boundaries.append(len(paragraphs))  # 结束位置

        # 5. 合并片段
        segments = []
        for i in range(len(boundaries) - 1):
            start_para = boundaries[i]
            end_para = boundaries[i + 1]

            # 合并段落文本
            segment_text = ""
            char_start = paragraphs[start_para]["start"]
            char_end = paragraphs[end_para - 1]["end"]

            for j in range(start_para, end_para):
                segment_text += paragraphs[j]["text"] + "\n"

            # 过滤过短片段
            if len(segment_text) >= min_segment_length:
                # 计算边界强度（如果有）
                score = (
                    boundary_scores[start_para]
                    if start_para < len(boundary_scores)
                    else 0
                )

                segments.append(
                    {
                        "text": segment_text.strip(),
                        "start": char_start,
                        "end": char_end,
                        "boundary_score": round(float(score), 3),
                        "para_count": end_para - start_para,
                    }
                )

        return (
            segments
            if segments
            else [{"text": text, "start": 0, "end": len(text), "boundary_score": 0}]
        )

    def _split_paragraphs(self, text: str) -> List[Dict]:
        """分割段落，保留位置信息"""
        paragraphs = []

        # 按换行分割
        lines = text.split("\n")
        current_start = 0
        current_text = ""

        for line in lines:
            stripped = line.strip()

            # 空行视为段落分隔
            if not stripped:
                if current_text.strip():
                    paragraphs.append(
                        {
                            "text": current_text.strip(),
                            "start": current_start,
                            "end": current_start + len(current_text),
                        }
                    )
                current_start += len(current_text) + 1  # +1 for newline
                current_text = ""
            else:
                if not current_text:
                    current_start = text.find(stripped, current_start)
                current_text += line + "\n"

        # 最后一个段落
        if current_text.strip():
            paragraphs.append(
                {
                    "text": current_text.strip(),
                    "start": current_start,
                    "end": current_start + len(current_text),
                }
            )

        return paragraphs

    def _fallback_segment(self, text: str, min_length: int) -> List[Dict]:
        """回退方法：按章节分割"""
        # 按章节分割
        pattern = r"第[一二三四五六七八九十百千万零\d]+[章节回部卷]"
        matches = list(re.finditer(pattern, text))

        if not matches:
            return [{"text": text, "start": 0, "end": len(text), "boundary_score": 0}]

        segments = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            segment_text = text[start:end]

            if len(segment_text) >= min_length:
                segments.append(
                    {
                        "text": segment_text,
                        "start": start,
                        "end": end,
                        "boundary_score": 0.5,  # 章节边界标记
                    }
                )

        return (
            segments
            if segments
            else [{"text": text, "start": 0, "end": len(text), "boundary_score": 0}]
        )


# ============================================
# 场景类型定义（融合中西方法论）
# ============================================

SCENE_TYPES = {
    # 核心场景（决定读者留存）
    "开篇场景": {
        "keywords": ["第一章", "引子", "楔子", "序章", "开篇", "一切开始"],
        "position": [0, 0.05],
        "priority": 1,
        "description": "黄金三章关键，300字主角登场，3000字冲突爆发",
        "writers": ["云溪", "苍澜"],
        "emotion_base": 7.0,
    },
    "冲突升级": {
        "keywords": ["冲突", "矛盾", "对峙", "危机", "压力", "逼迫"],
        "position": [0.1, 0.9],
        "priority": 1,
        "description": "矛盾递进，推动情节发展",
        "writers": ["玄一", "剑尘"],
        "emotion_base": 6.5,
    },
    "转折场景": {
        "keywords": ["突然", "竟然", "没想到", "出乎意料", "反转", "真相"],
        "position": [0.2, 0.8],
        "priority": 1,
        "description": "反转/揭秘，改变故事走向",
        "writers": ["玄一"],
        "emotion_base": 7.5,
    },
    "高潮场景": {
        "keywords": [
            "决战",
            "最终",
            "生死",
            "巅峰",
            "极限",
            "全力以赴",
            "最后一战",
            "终极一战",
            "生死之战",
            "决一死战",
            "爆发",
            "燃烧",
            "燃烧生命",
            "孤注一掷",
            "绝境",
            "绝地",
            "背水一战",
            "破釜沉舟",
            "气势",
            "威压",
            "气势冲天",
            "战意",
            "最强",
            "最强一击",
            "必杀",
            "底牌",
            "惊天动地",
            "震撼",
            "天地变色",
            "风云变色",
            "生死关头",
            "关键时刻",
            "千钧一发",
            "热血沸腾",
            "沸腾",
            "燃烧起来",
        ],
        "position": [0.7, 0.95],
        "priority": 1,
        "description": "情绪爆发点，故事顶点",
        "writers": ["剑尘", "玄一"],
        "emotion_base": 9.0,
    },
    "结尾场景": {
        "keywords": ["终章", "尾声", "结局", "完结", "落幕"],
        "position": [0.95, 1.0],
        "priority": 1,
        "description": "钩子设置，余韵",
        "writers": ["云溪"],
        "emotion_base": 6.0,
    },
    # 功能场景（推动情节）
    "人物出场": {
        "keywords": ["登场", "出现", "第一次见", "新角色", "身影"],
        "position": [0, 0.5],
        "priority": 2,
        "description": "立人设，建立角色形象",
        "writers": ["墨言"],
        "emotion_base": 6.0,
    },
    "对话场景": {
        "keywords": ["说道", "问道", "笑道", "沉声道", "低声道"],
        "position": [0, 1.0],
        "priority": 2,
        "description": "信息传递+性格展现",
        "writers": ["墨言", "剑尘"],
        "emotion_base": 5.5,
    },
    "心理场景": {
        "keywords": ["心想", "心中", "暗想", "思索", "犹豫", "挣扎"],
        "position": [0, 1.0],
        "priority": 2,
        "description": "内心成长，情感转变",
        "writers": ["墨言"],
        "emotion_base": 5.5,
    },
    "环境场景": {
        "keywords": ["周围", "环境", "景象", "景色", "氛围", "空气中"],
        "position": [0, 1.0],
        "priority": 3,
        "description": "氛围营造，烘托情绪",
        "writers": ["云溪"],
        "emotion_base": 5.0,
    },
    "情感场景": {
        "keywords": ["感动", "温暖", "心痛", "不舍", "眷恋", "深情"],
        "position": [0, 1.0],
        "priority": 2,
        "description": "情感推进，人物关系变化",
        "writers": ["墨言"],
        "emotion_base": 6.5,
    },
    "悬念场景": {
        "keywords": ["究竟", "到底", "为何", "谜团", "疑惑", "不解"],
        "position": [0, 0.95],
        "priority": 2,
        "description": "期待感营造，钩子设置",
        "writers": ["玄一"],
        "emotion_base": 6.5,
    },
    # 网文特色场景（爽点驱动）
    "打脸场景": {
        "keywords": [
            "嘲讽",
            "看不起",
            "废物",
            "实力证明",
            "震惊",
            "目瞪口呆",
            "打脸",
            "狠狠打脸",
            "实力打脸",
            "当场打脸",
            "垃圾",
            "蝼蚁",
            "废柴",
            "废物一个",
            "不自量力",
            "不知死活",
            "不知天高地厚",
            "狂妄",
            "找死",
            "低估",
            "小看",
            "轻视",
            "看走眼",
            "有眼无珠",
            "啪啪",
            "打脸啪啪响",
            "狠狠",
            "后悔",
            "肠子都悔青",
            "悔不该",
            "跪下",
            "跪地求饶",
            "跪地认错",
            "傻眼",
            "惊呆",
            "傻了",
            "不敢相信",
            "狠狠教训",
            "给点颜色",
            "让你看看",
            "嚣张",
            "跋扈",
            "目中无人",
            "狂妄自大",
            "反转",
            "逆转",
            "反杀",
            "逆风翻盘",
            "没想到",
            "怎么可能",
            "不可能",
            "出乎意料",
        ],
        "position": [0.1, 0.9],
        "priority": 1,
        "description": "被看不起→证明实力",
        "writers": ["剑尘", "苍澜"],
        "emotion_base": 8.5,
    },
    "修炼突破": {
        "keywords": ["突破", "晋级", "提升", "进阶", "境界", "修炼"],
        "position": [0.1, 0.9],
        "priority": 2,
        "description": "实力提升的快感",
        "writers": ["苍澜", "剑尘"],
        "emotion_base": 7.0,
    },
    "战斗场景": {
        "keywords": ["战斗", "交手", "过招", "厮杀", "对拼", "剑光"],
        "position": [0, 1.0],
        "priority": 2,
        "description": "动作描写，力量体系展现",
        "writers": ["剑尘"],
        "emotion_base": 7.5,
    },
    "资源获取": {
        "keywords": ["获得", "得到", "收获", "宝物", "传承", "功法"],
        "position": [0.1, 0.9],
        "priority": 2,
        "description": "宝物/功法/传承获取",
        "writers": ["苍澜"],
        "emotion_base": 7.0,
    },
    "伏笔设置": {
        "keywords": ["似乎", "仿佛", "隐约", "某天", "日后", "将来"],
        "position": [0, 0.8],
        "priority": 3,
        "description": "埋设技巧，暗示未来",
        "writers": ["玄一"],
        "emotion_base": 5.5,
    },
    "伏笔回收": {
        "keywords": ["原来", "竟然是", "终于明白", "真相大白", "水落石出"],
        "position": [0.3, 1.0],
        "priority": 3,
        "description": "揭示技巧，呼应前文",
        "writers": ["玄一"],
        "emotion_base": 6.5,
    },
    # 新增场景类型（扩展到28种）
    "反派出场": {
        "keywords": [
            "反派",
            "恶人",
            "魔头",
            "敌人",
            "对手",
            " antagonist",
            "冷笑",
            "阴狠",
            "邪恶",
        ],
        "position": [0.1, 0.8],
        "priority": 2,
        "description": "反派角色首次亮相，建立威胁感",
        "writers": ["墨言", "玄一"],
        "emotion_base": 6.0,
    },
    "恢复休养": {
        "keywords": ["恢复", "休养", "疗伤", "调息", "闭关", "静养", "痊愈", "康复"],
        "position": [0.2, 0.9],
        "priority": 3,
        "description": "战斗后的恢复，节奏调节场景",
        "writers": ["云溪", "墨言"],
        "emotion_base": 4.5,
    },
    "回忆场景": {
        "keywords": ["回忆", "想起", "往事", "曾经", "当年", "记忆", "追溯", "回想"],
        "position": [0.1, 0.9],
        "priority": 3,
        "description": "插叙补充背景，揭示人物过往",
        "writers": ["墨言", "云溪"],
        "emotion_base": 5.5,
    },
    "势力登场": {
        "keywords": ["势力", "宗门", "家族", "联盟", "组织", "派系", "阵营", "崛起"],
        "position": [0.1, 0.8],
        "priority": 2,
        "description": "新势力首次出现，世界观扩展",
        "writers": ["苍澜"],
        "emotion_base": 6.5,
    },
    "成长蜕变": {
        "keywords": ["成长", "蜕变", "觉醒", "领悟", "改变", "成熟", "顿悟", "升华"],
        "position": [0.2, 0.9],
        "priority": 2,
        "description": "人物心智成长，性格转变",
        "writers": ["墨言", "玄一"],
        "emotion_base": 7.0,
    },
    "危机降临": {
        "keywords": ["危机", "危险", "绝境", "生死", "大祸", "劫难", "杀机", "威胁"],
        "position": [0.2, 0.9],
        "priority": 1,
        "description": "重大危机出现，紧迫感和压力",
        "writers": ["玄一", "剑尘"],
        "emotion_base": 8.0,
    },
    "探索发现": {
        "keywords": ["探索", "发现", "遗迹", "秘境", "寻宝", "探险", "未知", "神秘"],
        "position": [0.2, 0.9],
        "priority": 2,
        "description": "探索未知区域，发现秘密",
        "writers": ["苍澜", "玄一"],
        "emotion_base": 6.5,
    },
    "情报揭示": {
        "keywords": ["情报", "消息", "信息", "线索", "秘密", "真相", "内情", "透露"],
        "position": [0.1, 0.9],
        "priority": 2,
        "description": "关键信息披露，推动剧情发展",
        "writers": ["玄一", "墨言"],
        "emotion_base": 6.0,
    },
    "社交场景": {
        "keywords": ["宴会", "聚会", "交流", "结识", "拜访", "应酬", "交际", "联络"],
        "position": [0.1, 0.9],
        "priority": 3,
        "description": "人物关系建立，势力互动",
        "writers": ["墨言", "苍澜"],
        "emotion_base": 5.5,
    },
    "阴谋揭露": {
        "keywords": ["阴谋", "诡计", "算计", "陷害", "背叛", "出卖", "揭露", "识破"],
        "position": [0.3, 0.95],
        "priority": 1,
        "description": "阴谋被揭穿，真相大白",
        "writers": ["玄一"],
        "emotion_base": 7.5,
    },
    "团队组建": {
        "keywords": ["组队", "结盟", "伙伴", "同伴", "团队", "合作", "招募", "加入"],
        "position": [0.1, 0.8],
        "priority": 2,
        "description": "团队成员集结，建立伙伴关系",
        "writers": ["墨言", "剑尘"],
        "emotion_base": 6.5,
    },
}

# 题材分类关键词
GENRE_KEYWORDS = {
    "玄幻奇幻": ["修炼", "境界", "灵气", "丹药", "功法", "元婴", "金丹", "渡劫"],
    "武侠仙侠": ["武功", "内力", "江湖", "门派", "剑法", "轻功", "侠客"],
    "现代都市": ["总裁", "豪门", "都市", "公司", "商战", "白领"],
    "历史军事": ["朝代", "皇帝", "将军", "战争", "谋略", "战场"],
    "科幻灵异": ["星际", "机甲", "末世", "异能", "丧尸", "科技"],
    "青春校园": ["校园", "学生", "青春", "恋爱", "考试", "同学"],
    "游戏竞技": ["游戏", "副本", "装备", "等级", "PK", "公会"],
    "女频言情": ["公主", "王爷", "皇后", "宫斗", "嫡女", "甜宠"],
}

# AI味表达检测
AI_EXPRESSIONS = [
    "一种复杂的情绪",
    "心中的某个地方",
    "仿佛有什么在涌动",
    "不知为何",
    "莫名地",
    "一种说不出的感觉",
    "在这一刻",
    "这一刻，他明白了",
    "他的眼中闪过一丝",
    "嘴角微微上扬",
    "眼眸中闪过一丝",
    "一种前所未有的",
    "心中的那个念头",
    "某种难以言喻的",
    "似乎有什么改变了",
]

# 非小说关键词
NON_NOVEL_KEYWORDS = [
    "教材",
    "教程",
    "教案",
    "习题",
    "答案",
    "试卷",
    "考试",
    "论文",
    "研究报告",
    "技术手册",
    "编程",
    "开发指南",
    "词典",
    "字典",
    "百科",
    "期刊",
    "杂志",
]


@dataclass
class CaseInfo:
    """案例信息"""

    case_id: str
    source_id: str
    source_file: str
    novel_name: str
    genre: str
    scene_type: str
    content: str
    word_count: int
    chapter_index: int
    position_ratio: float
    confidence: float
    emotion_value: float
    quality_score: float
    techniques: List[str]
    keywords: List[str]
    is_novel: bool
    has_ai_taste: bool
    boundary_score: float = 0.0  # Ex3语义边界分数
    extract_time: str = ""


class UnifiedCaseExtractor:
    """统一案例提取器 - Ex3语义分组版"""

    def __init__(self, use_semantic: bool = True):
        self.use_semantic = use_semantic
        self.semantic_segmenter = SemanticSegmenter() if use_semantic else None
        self.index = self._load_index()
        self.stats = self._load_stats()
        self.case_counter = self.stats.get("total_cases", 0)
        self.processed_files = set(self.index.get("processed_files", []))

    def _load_index(self) -> Dict:
        if INDEX_FILE.exists():
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"novels": {}, "cases": [], "processed_files": []}

    def _save_index(self):
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def _load_stats(self) -> Dict:
        if STATS_FILE.exists():
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "total_files": 0,
            "novels_found": 0,
            "non_novels": 0,
            "total_cases": 0,
            "by_genre": {},
            "by_scene": {},
            "by_source": {},
            "extraction_mode": "semantic" if self.use_semantic else "keyword",
            "last_update": None,
        }

    def _save_stats(self):
        self.stats["last_update"] = datetime.now().isoformat()
        self.stats["extraction_mode"] = "semantic" if self.use_semantic else "keyword"
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    def _read_file(self, file_path: Path) -> Optional[str]:
        """读取文件内容"""
        encodings = ["utf-8", "gb18030", "gbk", "gb2312", "big5"]

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                    if content and len(content) > 500:
                        chinese_chars = len(
                            re.findall(r"[\u4e00-\u9fff]", content[:2000])
                        )
                        if chinese_chars > 100:
                            return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"读取失败: {file_path.name} - {e}")

        return None

    def _is_novel(self, content: str, file_path: Path) -> Tuple[bool, str]:
        """判断是否为小说"""
        filename = file_path.name.lower()
        sample = content[:5000]

        for kw in NON_NOVEL_KEYWORDS:
            if kw in filename:
                return False, "non_novel_filename"

        non_novel_count = sum(1 for kw in NON_NOVEL_KEYWORDS if kw in sample)
        if non_novel_count > 5:
            return False, "teaching_material"

        novel_count = 0
        for genre_keywords in GENRE_KEYWORDS.values():
            novel_count += sum(1 for kw in genre_keywords if kw in sample)

        chapter_patterns = [r"第[一二三四五六七八九十百千万零\d]+[章节回]"]
        chapter_matches = sum(
            len(re.findall(p, content[:10000])) for p in chapter_patterns
        )

        dialogue_markers = ['"', '"', "「", "」", "『", "』", """, """]
        dialogue_count = sum(sample.count(m) for m in dialogue_markers)

        if chapter_matches >= 3:
            return True, "novel_chapters"
        elif novel_count >= 5 and dialogue_count > 20:
            return True, "novel_dialogue"
        elif novel_count >= 3 and len(content) > 10000:
            return True, "novel_long"
        elif non_novel_count == 0 and novel_count >= 2:
            return True, "novel_likely"

        return False, "unknown"

    def _detect_genre(self, content: str) -> str:
        """检测题材"""
        scores = {}
        sample = content[:10000]

        for genre, keywords in GENRE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in sample)
            scores[genre] = score

        if scores:
            max_genre = max(scores, key=scores.get)
            if scores[max_genre] > 0:
                return max_genre

        return "玄幻奇幻"

    def _split_chapters(self, content: str) -> List[Dict]:
        """分割章节"""
        chapters = []
        pattern = r"第[一二三四五六七八九十百千万零\d]+[章节回部卷][^\n]*"
        matches = list(re.finditer(pattern, content))

        if not matches:
            chapters.append(
                {
                    "index": 1,
                    "title": "全文",
                    "content": content,
                    "start": 0,
                    "end": len(content),
                }
            )
        else:
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
                chapter_content = content[start:end]

                if len(chapter_content) > 500:
                    chapters.append(
                        {
                            "index": i + 1,
                            "title": match.group(),
                            "content": chapter_content,
                            "start": start,
                            "end": end,
                        }
                    )

        return chapters

    def _semantic_scene_detection(
        self, segment: Dict, chapter_index: int, total_chapters: int
    ) -> List[Tuple[str, float, float]]:
        """
        基于Ex3语义的场景检测

        Returns:
            List of (scene_type, confidence, boundary_score)
        """
        results = []
        content = segment["text"]
        boundary_score = segment.get("boundary_score", 0)
        position_ratio = chapter_index / total_chapters if total_chapters > 0 else 0

        sample = content[:3000]

        for scene_type, config in SCENE_TYPES.items():
            keyword_matches = 0

            # 关键词匹配
            for kw in config["keywords"]:
                if kw in sample:
                    keyword_matches += 1

            # 位置匹配
            pos_range = config["position"]
            position_match = 1 if pos_range[0] <= position_ratio <= pos_range[1] else 0

            # 语义边界加成（Ex3核心创新）
            boundary_bonus = boundary_score * 0.3

            # 综合评分
            if keyword_matches > 0:
                confidence = (
                    keyword_matches * 0.4 + position_match * 0.3 + boundary_bonus
                ) / len(config["keywords"])
                if confidence > 0.1:
                    results.append((scene_type, confidence, boundary_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:3]

    def _keyword_scene_detection(
        self, content: str, chapter_index: int, total_chapters: int
    ) -> List[Tuple[str, float]]:
        """关键词场景检测（快速模式）"""
        detected = []
        sample = content[:3000]
        position_ratio = chapter_index / total_chapters if total_chapters > 0 else 0

        for scene_type, config in SCENE_TYPES.items():
            keyword_matches = 0

            for kw in config["keywords"]:
                if kw in sample:
                    keyword_matches += 1

            pos_range = config["position"]
            position_match = 1 if pos_range[0] <= position_ratio <= pos_range[1] else 0

            if keyword_matches > 0:
                confidence = (keyword_matches * 0.3 + position_match * 0.7) / len(
                    config["keywords"]
                )
                if confidence > 0.1:
                    detected.append((scene_type, confidence))

        detected.sort(key=lambda x: x[1], reverse=True)
        return detected[:3]

    def _calculate_emotion_value(self, content: str, scene_type: str) -> float:
        """计算情绪价值分"""
        config = SCENE_TYPES.get(scene_type, {})
        score = config.get("emotion_base", 5.0)

        # 紧张词加成
        tension_words = ["突然", "竟然", "猛然", "瞬间", "轰", "炸", "震惊", "不可思议"]
        excitement = sum(1 for w in tension_words if w in content)
        score += min(excitement * 0.3, 1.5)

        # 对话密度加成
        dialogue_markers = ['"', '"', "「", "」"]
        dialogue_count = sum(content.count(m) for m in dialogue_markers)
        if dialogue_count > 20:
            score += 0.5

        return min(max(score, 1.0), 10.0)

    def _calculate_quality_score(
        self,
        content: str,
        has_ai: bool,
        scene_type: str,
        emotion_value: float,
        boundary_score: float = 0,
    ) -> float:
        """计算质量分数"""
        score = 10.0

        # AI味扣分
        if has_ai:
            ai_count = sum(1 for expr in AI_EXPRESSIONS if expr in content)
            score -= min(ai_count * 0.5, 3.0)

        # 字数检查
        word_count = len(content)
        if word_count < 300:
            score -= 2.0
        elif word_count < 500:
            score -= 1.0
        elif word_count > 3000:
            score -= 0.5

        # 完整性检查
        if content.endswith("...") or content.endswith("……"):
            score -= 1.0

        # 情绪价值加成
        if emotion_value >= 7.0:
            score += 0.5

        # Ex3语义边界加成（清晰的场景边界=更高质量）
        if boundary_score > 0.3:
            score += 0.3

        return max(0, min(10, score))

    def _detect_techniques(self, content: str, scene_type: str) -> List[str]:
        """检测写作技法"""
        techniques = []

        if "伏笔" in scene_type or "似乎" in content or "隐约" in content:
            techniques.append("伏笔设置")
        if "转折" in scene_type or "反转" in scene_type:
            techniques.append("反转技巧")
        if any(m in content for m in ['"', '"', "「", "」"]):
            techniques.append("对话描写")
        if re.search(r"[，。]{3,}", content):
            techniques.append("节奏控制")
        if len(re.findall(r"[！？]", content)) > 5:
            techniques.append("情绪强化")

        return techniques[:3]

    def _detect_ai_taste(self, content: str) -> Tuple[bool, int, List[str]]:
        """检测AI味"""
        found = [expr for expr in AI_EXPRESSIONS if expr in content]
        has_ai = len(found) >= 2
        return has_ai, len(found), found

    def _extract_scene_content(
        self, chapter_content: str, scene_type: str, segment: Dict = None
    ) -> str:
        """提取场景内容"""
        # 如果有语义分段结果，优先使用
        if segment and "text" in segment:
            return segment["text"][:1500]

        # 回退到关键词定位
        if scene_type == "开篇场景":
            return chapter_content[:1500]
        elif scene_type == "结尾场景":
            return chapter_content[-800:]
        elif scene_type in ["战斗场景", "打脸场景"]:
            keywords = SCENE_TYPES[scene_type]["keywords"]
            for kw in keywords:
                if kw in chapter_content:
                    idx = chapter_content.find(kw)
                    start = max(0, idx - 200)
                    end = min(len(chapter_content), idx + 800)
                    return chapter_content[start:end]
            return chapter_content[:1000]
        else:
            return chapter_content[:1000]

    def _get_source_id(self, file_path: Path) -> str:
        """获取来源ID"""
        path_str = str(file_path)

        if "converted" in path_str:
            for i in range(1, 11):
                if f"source_{i:03d}" in path_str:
                    return f"source_{i:03d}"
            return "source_converted"

        for i, orig_dir in enumerate(ORIGINAL_DIRS, 1):
            if orig_dir in path_str:
                return f"source_{i:03d}"

        return "source_unknown"

    def _collect_all_txt_files(self) -> List[Path]:
        """收集所有txt文件"""
        txt_files = []

        if CONVERTED_DIR.exists():
            txt_files.extend(CONVERTED_DIR.glob("*.txt"))

        for orig_dir in ORIGINAL_DIRS:
            orig_path = Path(orig_dir)
            if orig_path.exists():
                txt_files.extend(orig_path.rglob("*.txt"))

        return list(set(txt_files))

    def scan_files(self) -> Dict:
        """扫描所有文件"""
        logger.info("扫描所有txt文件...")

        txt_files = self._collect_all_txt_files()
        total = len(txt_files)

        converted_count = (
            len(list(CONVERTED_DIR.glob("*.txt"))) if CONVERTED_DIR.exists() else 0
        )
        original_count = total - converted_count

        mode = "语义分组模式" if self.use_semantic else "关键词快速模式"

        print(f"\n扫描结果 ({mode}):")
        print(f"  converted目录: {converted_count} 个文件")
        print(f"  原始目录: {original_count} 个文件")
        print(f"  总计: {total} 个文件")
        print(f"  已处理: {len(self.processed_files)} 个文件")
        print(f"  待处理: {total - len(self.processed_files)} 个文件")

        return {
            "total": total,
            "converted": converted_count,
            "original": original_count,
            "processed": len(self.processed_files),
            "pending": total - len(self.processed_files),
            "mode": mode,
        }

    def extract_cases(self, limit: int = None) -> Dict:
        """提取案例"""
        mode = "Ex3语义分组模式" if self.use_semantic else "关键词快速模式"
        print("=" * 60)
        print(f"统一案例提取 - {mode}")
        print("=" * 60)

        txt_files = self._collect_all_txt_files()
        pending_files = [f for f in txt_files if str(f) not in self.processed_files]

        if limit:
            pending_files = pending_files[:limit]

        total = len(pending_files)
        print(f"\n待处理文件: {total} 个")

        if total == 0:
            print("没有待处理的文件")
            return {"processed": 0, "cases": 0}

        results = {
            "processed": 0,
            "cases": 0,
            "novels": 0,
            "non_novels": 0,
            "errors": [],
        }

        for i, txt_file in enumerate(pending_files, 1):
            print(f"\r[{i}/{total}] 处理: {txt_file.name[:30]:<30}", end="", flush=True)

            try:
                content = self._read_file(txt_file)
                if not content:
                    continue

                is_novel, novel_type = self._is_novel(content, txt_file)
                if not is_novel:
                    results["non_novels"] += 1
                    self.processed_files.add(str(txt_file))
                    continue

                genre = self._detect_genre(content)
                source_id = self._get_source_id(txt_file)

                chapters = self._split_chapters(content)
                if not chapters:
                    continue

                chapters_to_process = chapters[:5] + (
                    chapters[-1:] if len(chapters) > 5 else []
                )
                novel_cases = []

                for chapter in chapters_to_process:
                    chapter_content = chapter["content"]
                    chapter_index = chapter["index"]
                    position_ratio = chapter_index / len(chapters)

                    # 使用语义分段或关键词检测
                    if self.use_semantic and self.semantic_segmenter:
                        # Ex3语义分段
                        segments = self.semantic_segmenter.segment_text(chapter_content)

                        for segment in segments:
                            scene_results = self._semantic_scene_detection(
                                segment, chapter_index, len(chapters)
                            )

                            for scene_type, confidence, boundary_score in scene_results:
                                scene_content = segment["text"][:1500]

                                if len(scene_content) < 300:
                                    continue

                                has_ai, ai_count, ai_exprs = self._detect_ai_taste(
                                    scene_content
                                )
                                emotion_value = self._calculate_emotion_value(
                                    scene_content, scene_type
                                )
                                quality_score = self._calculate_quality_score(
                                    scene_content,
                                    has_ai,
                                    scene_type,
                                    emotion_value,
                                    boundary_score,
                                )

                                if quality_score < 6.0:
                                    continue

                                techniques = self._detect_techniques(
                                    scene_content, scene_type
                                )
                                keywords = [
                                    kw
                                    for kw in SCENE_TYPES[scene_type]["keywords"]
                                    if kw in scene_content
                                ][:5]

                                self.case_counter += 1
                                case_id = f"case_{self.case_counter:06d}"

                                case = CaseInfo(
                                    case_id=case_id,
                                    source_id=source_id,
                                    source_file=str(txt_file),
                                    novel_name=txt_file.stem,
                                    genre=genre,
                                    scene_type=scene_type,
                                    content=scene_content,
                                    word_count=len(scene_content),
                                    chapter_index=chapter_index,
                                    position_ratio=round(position_ratio, 3),
                                    confidence=round(confidence, 3),
                                    emotion_value=round(emotion_value, 2),
                                    quality_score=round(quality_score, 2),
                                    techniques=techniques,
                                    keywords=keywords,
                                    is_novel=True,
                                    has_ai_taste=has_ai,
                                    boundary_score=round(boundary_score, 3),
                                    extract_time=datetime.now().isoformat(),
                                )

                                self._save_case(case)
                                novel_cases.append(case)

                                self.stats["by_genre"][genre] = (
                                    self.stats["by_genre"].get(genre, 0) + 1
                                )
                                self.stats["by_scene"][scene_type] = (
                                    self.stats["by_scene"].get(scene_type, 0) + 1
                                )
                                self.stats["by_source"][source_id] = (
                                    self.stats["by_source"].get(source_id, 0) + 1
                                )
                    else:
                        # 关键词快速模式
                        scene_results = self._keyword_scene_detection(
                            chapter_content, chapter_index, len(chapters)
                        )

                        for scene_type, confidence in scene_results:
                            scene_content = self._extract_scene_content(
                                chapter_content, scene_type
                            )

                            if len(scene_content) < 300:
                                continue

                            has_ai, ai_count, ai_exprs = self._detect_ai_taste(
                                scene_content
                            )
                            emotion_value = self._calculate_emotion_value(
                                scene_content, scene_type
                            )
                            quality_score = self._calculate_quality_score(
                                scene_content, has_ai, scene_type, emotion_value
                            )

                            if quality_score < 6.0:
                                continue

                            techniques = self._detect_techniques(
                                scene_content, scene_type
                            )
                            keywords = [
                                kw
                                for kw in SCENE_TYPES[scene_type]["keywords"]
                                if kw in scene_content
                            ][:5]

                            self.case_counter += 1
                            case_id = f"case_{self.case_counter:06d}"

                            case = CaseInfo(
                                case_id=case_id,
                                source_id=source_id,
                                source_file=str(txt_file),
                                novel_name=txt_file.stem,
                                genre=genre,
                                scene_type=scene_type,
                                content=scene_content,
                                word_count=len(scene_content),
                                chapter_index=chapter_index,
                                position_ratio=round(position_ratio, 3),
                                confidence=round(confidence, 3),
                                emotion_value=round(emotion_value, 2),
                                quality_score=round(quality_score, 2),
                                techniques=techniques,
                                keywords=keywords,
                                is_novel=True,
                                has_ai_taste=has_ai,
                                extract_time=datetime.now().isoformat(),
                            )

                            self._save_case(case)
                            novel_cases.append(case)

                            self.stats["by_genre"][genre] = (
                                self.stats["by_genre"].get(genre, 0) + 1
                            )
                            self.stats["by_scene"][scene_type] = (
                                self.stats["by_scene"].get(scene_type, 0) + 1
                            )
                            self.stats["by_source"][source_id] = (
                                self.stats["by_source"].get(source_id, 0) + 1
                            )

                self.index["novels"][str(txt_file)] = {
                    "source_id": source_id,
                    "novel_name": txt_file.stem,
                    "genre": genre,
                    "is_novel": True,
                    "word_count": len(content),
                    "chapters_count": len(chapters),
                    "cases_count": len(novel_cases),
                    "scenes_found": list(set(c.scene_type for c in novel_cases)),
                }

                self.processed_files.add(str(txt_file))
                results["processed"] += 1
                results["novels"] += 1
                results["cases"] += len(novel_cases)

            except Exception as e:
                logger.error(f"处理失败: {txt_file.name} - {e}")
                results["errors"].append(f"{txt_file.name}: {str(e)}")

        self.stats["total_files"] = len(self.processed_files)
        self.stats["novels_found"] = results["novels"]
        self.stats["non_novels"] = results["non_novels"]
        self.stats["total_cases"] = self.case_counter

        self.index["processed_files"] = list(self.processed_files)
        self._save_index()
        self._save_stats()

        print(f"\n\n处理完成!")
        print(f"  处理文件: {results['processed']}")
        print(f"  识别小说: {results['novels']}")
        print(f"  非小说: {results['non_novels']}")
        print(f"  提取案例: {results['cases']}")
        print(f"  错误: {len(results['errors'])}")

        return results

    def _save_case(self, case: CaseInfo):
        """保存案例"""
        scene_dir = CASES_DIR / case.scene_type / case.genre
        scene_dir.mkdir(parents=True, exist_ok=True)

        txt_path = scene_dir / f"{case.case_id}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(case.content)

        metadata = {
            "case_id": case.case_id,
            "source": {
                "source_id": case.source_id,
                "file": case.source_file,
                "novel_name": case.novel_name,
                "genre": case.genre,
            },
            "scene": {
                "type": case.scene_type,
                "chapter_index": case.chapter_index,
                "position_ratio": case.position_ratio,
                "word_count": case.word_count,
            },
            "quality": {
                "overall_score": case.quality_score,
                "emotion_value": case.emotion_value,
                "confidence": case.confidence,
                "has_ai_taste": case.has_ai_taste,
                "boundary_score": case.boundary_score,
            },
            "tags": {
                "techniques": case.techniques,
                "keywords": case.keywords,
                "recommended_writers": SCENE_TYPES.get(case.scene_type, {}).get(
                    "writers", []
                ),
            },
            "content_preview": case.content[:500],
            "extract_time": case.extract_time,
        }

        json_path = scene_dir / f"{case.case_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "已处理文件": self.stats.get("total_files", 0),
            "识别小说数": self.stats.get("novels_found", 0),
            "非小说数": self.stats.get("non_novels", 0),
            "案例总数": self.stats.get("total_cases", 0),
            "提取模式": self.stats.get("extraction_mode", "unknown"),
            "按题材分布": dict(
                sorted(
                    self.stats.get("by_genre", {}).items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ),
            "按场景分布": dict(
                sorted(
                    self.stats.get("by_scene", {}).items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ),
            "按来源分布": dict(
                sorted(
                    self.stats.get("by_source", {}).items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ),
            "最后更新": self.stats.get("last_update", "未知"),
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="统一案例提取工具 v3.0 - Ex3语义分组版"
    )
    parser.add_argument("--scan", action="store_true", help="扫描文件")
    parser.add_argument("--extract", action="store_true", help="提取案例")
    parser.add_argument("--limit", type=int, default=None, help="处理文件数量限制")
    parser.add_argument("--stats", action="store_true", help="查看统计")
    parser.add_argument(
        "--no-semantic", action="store_true", help="禁用语义分组（快速模式）"
    )
    parser.add_argument(
        "--source-dirs", type=str, nargs="+", help="覆盖配置的小说资源目录"
    )

    args = parser.parse_args()

    # 如果命令行指定了源目录，则覆盖配置
    if args.source_dirs:
        global ORIGINAL_DIRS
        ORIGINAL_DIRS = args.source_dirs
        print(f"使用命令行指定的源目录: {args.source_dirs}")

    use_semantic = not args.no_semantic
    extractor = UnifiedCaseExtractor(use_semantic=use_semantic)

    if args.scan:
        extractor.scan_files()
    elif args.extract:
        extractor.extract_cases(args.limit)
    elif args.stats:
        stats = extractor.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
