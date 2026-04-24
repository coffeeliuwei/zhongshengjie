#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二批资源处理脚本 v1.0
=====================================

功能：
1. 从converted目录读取第二批资源转换后的txt文件
2. 过滤非小说内容（教辅资料、历史版本等）
3. 识别题材类型
4. 识别场景类型（22种）
5. 提取案例片段
6. 保存到案例库

使用方法：
    python process_batch2.py --scan       # 扫描并分析
    python process_batch2.py --extract    # 提取案例
    python process_batch2.py --stats      # 查看统计
"""

import os
import sys
import json
import re
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import logging

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from genre_classifier import GenreClassifier
from enhanced_scene_recognizer import EnhancedSceneRecognizer, SceneType

# 配置日志
# 确保logs目录存在
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "batch2_process.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class NovelInfo:
    """小说信息"""

    file_path: str
    novel_name: str
    file_size: int
    word_count: int
    genre: str
    genre_confidence: float
    is_novel: bool
    novel_type: str  # novel, teaching, history, other
    chapters_count: int
    scenes_found: List[str]
    cases_extracted: int
    quality_score: float


@dataclass
class CaseInfo:
    """案例信息"""

    case_id: str
    source_file: str
    novel_name: str
    genre: str
    scene_type: str
    content: str
    word_count: int
    chapter_index: int
    confidence: float
    quality_score: float
    has_ai_taste: bool
    ai_expressions: List[Tuple[str, int]]
    extract_time: str


class Batch2Processor:
    """第二批资源处理器"""

    # 非小说关键词（用于过滤）
    NON_NOVEL_KEYWORDS = [
        # 教辅资料
        "教材",
        "教程",
        "教案",
        "讲义",
        "课件",
        "习题",
        "答案",
        "解析",
        "考试",
        "高考",
        "中考",
        "考研",
        "考级",
        "题库",
        "试卷",
        "教学",
        "课程",
        "学习",
        "培训",
        "辅导",
        "复习",
        "备考",
        # 学术论文
        "论文",
        "研究",
        "报告",
        "分析",
        "综述",
        "摘要",
        "关键词",
        "参考文献",
        "基金项目",
        "作者简介",
        # 技术/工具书
        "手册",
        "指南",
        "工具书",
        "词典",
        "字典",
        "百科",
        "技术",
        "编程",
        "代码",
        "开发",
        "架构",
        "设计模式",
        # 历史/传记（非小说）
        "传记",
        "回忆录",
        "纪实",
        "史料",
        "档案",
        "年谱",
        # 其他非小说
        "期刊",
        "杂志",
        "报纸",
        "新闻",
        "评论",
        "专栏",
    ]

    # 小说特征关键词（用于确认是小说）
    NOVEL_KEYWORDS = [
        # 章节结构
        "第一章",
        "第二章",
        "第三章",
        "第十章",
        "第一百章",
        "第一节",
        "引子",
        "序章",
        "楔子",
        "尾声",
        "终章",
        # 小说元素
        "修炼",
        "境界",
        "功法",
        "灵气",
        "丹药",
        "法宝",
        "内力",
        "武功",
        "江湖",
        "门派",
        "剑法",
        "刀法",
        "总裁",
        "豪门",
        "都市",
        "重生",
        "穿越",
        "星际",
        "机甲",
        "末世",
        "丧尸",
        "异能",
        # 叙事特征
        "心想",
        "说道",
        "笑道",
        "叹道",
        "低声",
        "沉声",
        "看了一眼",
        "点了点头",
        "摇了摇头",
        "眉头一皱",
    ]

    # 场景类型映射到目录名
    SCENE_DIR_MAP = {
        "开篇场景": "01-开篇场景",
        "人物出场": "02-人物出场",
        "战斗场景": "03-战斗场景",
        "对话场景": "04-对话场景",
        "情感场景": "05-情感场景",
        "悬念场景": "06-悬念场景",
        "转折场景": "07-转折场景",
        "结尾场景": "08-结尾场景",
        "环境场景": "09-环境场景",
        "心理场景": "10-心理场景",
        "修炼突破": "11-修炼突破",
        "势力登场": "12-势力登场",
        "资源获取": "13-资源获取",
        "探索发现": "14-探索发现",
        "伏笔回收": "15-伏笔回收",
        "危机降临": "16-危机降临",
        "成长蜕变": "17-成长蜕变",
        "情报揭示": "18-情报揭示",
        "社交场景": "19-社交场景",
        "阴谋揭露": "20-阴谋揭露",
        "冲突升级": "21-冲突升级",
        "团队组建": "22-团队组建",
    }

    def __init__(self):
        self.case_library = Path(r"D:\动画\众生界\.case-library")
        self.converted_dir = self.case_library / "converted"
        self.cases_dir = self.case_library / "cases"
        self.logs_dir = self.case_library / "logs"
        self.index_file = self.case_library / "batch2_index.json"
        self.stats_file = self.case_library / "batch2_stats.json"

        # 确保目录存在
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.classifier = GenreClassifier()
        self.recognizer = EnhancedSceneRecognizer()

        # 加载已有索引
        self.index = self._load_index()
        self.stats = self._load_stats()

        # 案例计数器
        self.case_counter = self.stats.get("total_cases", 0)

    def _load_index(self) -> Dict:
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"novels": {}, "cases": []}

    def _save_index(self):
        """保存索引"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def _load_stats(self) -> Dict:
        """加载统计"""
        if self.stats_file.exists():
            with open(self.stats_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "total_files": 0,
            "novels_found": 0,
            "non_novels": 0,
            "total_cases": 0,
            "by_genre": {},
            "by_scene": {},
            "last_update": None,
        }

    def _save_stats(self):
        """保存统计"""
        self.stats["last_update"] = datetime.now().isoformat()
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    def _read_file(self, file_path: Path) -> Optional[str]:
        """读取文件内容"""
        encodings = ["utf-8", "gb18030", "gbk", "gb2312", "big5"]

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                    # 验证内容有效性
                    if content and len(content) > 500:
                        # 检查中文字符比例
                        chinese_chars = len(
                            re.findall(r"[\u4e00-\u9fff]", content[:2000])
                        )
                        if chinese_chars > 100:
                            return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"读取文件失败: {file_path.name} - {e}")

        return None

    def _is_novel(self, content: str, file_path: Path) -> Tuple[bool, str]:
        """
        判断是否为小说

        Returns:
            (是否小说, 内容类型)
        """
        filename = file_path.name.lower()
        sample = content[:5000]

        # 1. 文件名特征判断
        non_novel_filename_keywords = [
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
        ]
        for kw in non_novel_filename_keywords:
            if kw in filename:
                return False, "non_novel_filename"

        # 2. 非小说关键词检测
        non_novel_count = sum(1 for kw in self.NON_NOVEL_KEYWORDS if kw in sample)
        if non_novel_count > 5:
            return False, "teaching_material"

        # 3. 小说特征关键词检测
        novel_count = sum(1 for kw in self.NOVEL_KEYWORDS if kw in sample)

        # 4. 章节结构检测
        chapter_patterns = [
            r"第[一二三四五六七八九十百千万零\d]+[章节回]",
            r"Chapter\s*\d+",
        ]
        chapter_matches = 0
        for pattern in chapter_patterns:
            chapter_matches += len(re.findall(pattern, content[:10000]))

        # 5. 对话标记检测
        dialogue_markers = ['"', '"', "「", "」", "『", "』", """, """]
        dialogue_count = sum(content[:5000].count(m) for m in dialogue_markers)

        # 综合判断
        is_novel = False
        novel_type = "unknown"

        if chapter_matches >= 3:
            is_novel = True
            novel_type = "novel_chapters"
        elif novel_count >= 5 and dialogue_count > 20:
            is_novel = True
            novel_type = "novel_dialogue"
        elif novel_count >= 3 and len(content) > 10000:
            is_novel = True
            novel_type = "novel_long"
        elif non_novel_count == 0 and novel_count >= 2:
            is_novel = True
            novel_type = "novel_likely"

        return is_novel, novel_type

    def _split_chapters(self, content: str) -> List[Dict]:
        """分割章节"""
        chapters = []

        # 章节标题模式
        patterns = [
            r"第[一二三四五六七八九十百千万零\d]+[章节回部卷][^\n]*",
            r"Chapter\s*\d+[^\n]*",
            r"CHAPTER\s*\d+[^\n]*",
        ]

        combined_pattern = "|".join(patterns)
        matches = list(re.finditer(combined_pattern, content))

        if not matches:
            # 没有章节标记，视为单章
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

    def _quality_score(self, content: str, has_ai: bool, ai_words: List) -> float:
        """计算案例质量分数"""
        score = 10.0

        # AI味扣分
        if has_ai:
            score -= min(len(ai_words) * 0.5, 3.0)

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

        # 断裂检查
        if content.startswith("，") or content.startswith("。"):
            score -= 0.5

        return max(0, min(10, score))

    def analyze_novel(self, file_path: Path) -> Optional[NovelInfo]:
        """分析单本小说"""
        # 检查是否已处理
        file_str = str(file_path)
        if file_str in self.index["novels"]:
            logger.info(f"已处理过: {file_path.name}")
            return None

        # 读取内容
        content = self._read_file(file_path)
        if not content:
            logger.warning(f"无法读取: {file_path.name}")
            return None

        # 判断是否为小说
        is_novel, novel_type = self._is_novel(content, file_path)
        if not is_novel:
            logger.info(f"非小说内容: {file_path.name} ({novel_type})")
            return None

        # 分类题材
        genre, basis = self.classifier.classify(file_path, content)
        confidence = (
            self.classifier.get_genre_confidence(content, genre) if content else 0.5
        )

        # 分割章节
        chapters = self._split_chapters(content)

        # 创建小说信息
        info = NovelInfo(
            file_path=file_str,
            novel_name=file_path.stem,
            file_size=file_path.stat().st_size,
            word_count=len(content),
            genre=genre,
            genre_confidence=confidence,
            is_novel=True,
            novel_type=novel_type,
            chapters_count=len(chapters),
            scenes_found=[],
            cases_extracted=0,
            quality_score=0.0,
        )

        logger.info(
            f"分析完成: {info.novel_name} - {genre} ({confidence:.0%}) - {len(chapters)}章"
        )

        return info

    def extract_cases(self, novel_info: NovelInfo, content: str) -> List[CaseInfo]:
        """从小说中提取案例"""
        cases = []

        # 分割章节
        chapters = self._split_chapters(content)
        if not chapters:
            return cases

        # 只处理前5章和最后1章（提高效率）
        chapters_to_process = chapters[:5] + (
            chapters[-1:] if len(chapters) > 5 else []
        )

        for chapter in chapters_to_process:
            chapter_content = chapter["content"]
            chapter_index = chapter["index"]

            # 计算位置比例
            position_ratio = 0.0
            if chapter_index == 1:
                position_ratio = 0.0
            elif chapter_index == len(chapters):
                position_ratio = 1.0
            else:
                position_ratio = chapter_index / len(chapters)

            # 场景识别
            scenes = self.recognizer.analyze_segment(
                chapter_content[:2000],
                chapter_index=chapter_index,
                position_ratio=position_ratio,
            )

            for scene in scenes:
                # 提取场景内容
                scene_content = self._extract_scene_content(
                    chapter_content, scene.scene_type, position_ratio
                )

                if not scene_content or len(scene_content) < 300:
                    continue

                # AI味检测
                has_ai, ai_count, ai_words = self.recognizer.detect_ai_taste(
                    scene_content
                )

                # 质量评分
                quality = self._quality_score(scene_content, has_ai, ai_words)

                # 过滤低质量案例
                if quality < 6.0:
                    continue

                # 生成案例ID
                self.case_counter += 1
                case_id = f"batch2_{self.case_counter:05d}"

                # 创建案例
                case = CaseInfo(
                    case_id=case_id,
                    source_file=novel_info.file_path,
                    novel_name=novel_info.novel_name,
                    genre=novel_info.genre,
                    scene_type=scene.scene_type,
                    content=scene_content,
                    word_count=len(scene_content),
                    chapter_index=chapter_index,
                    confidence=scene.confidence,
                    quality_score=quality,
                    has_ai_taste=has_ai,
                    ai_expressions=ai_words[:5],
                    extract_time=datetime.now().isoformat(),
                )

                cases.append(case)
                novel_info.scenes_found.append(scene.scene_type)

        novel_info.cases_extracted = len(cases)
        novel_info.quality_score = (
            sum(c.quality_score for c in cases) / len(cases) if cases else 0
        )

        return cases

    def _extract_scene_content(
        self, chapter_content: str, scene_type: str, position_ratio: float
    ) -> Optional[str]:
        """提取场景内容"""
        if scene_type == "开篇场景":
            # 提取章节开头800-1500字
            return chapter_content[:1500]

        elif scene_type == "结尾场景":
            # 提取章节结尾400-800字
            return chapter_content[-800:]

        elif scene_type == "战斗场景":
            # 尝试找到战斗片段
            battle_keywords = ["战斗", "打斗", "厮杀", "交锋", "对决"]
            for kw in battle_keywords:
                if kw in chapter_content:
                    # 找到关键词位置，提取前后500字
                    idx = chapter_content.find(kw)
                    start = max(0, idx - 200)
                    end = min(len(chapter_content), idx + 800)
                    return chapter_content[start:end]
            return chapter_content[:1000]

        elif scene_type == "对话场景":
            # 提取对话密集部分
            return chapter_content[:1200]

        elif scene_type == "情感场景":
            # 提取情感表达部分
            return chapter_content[:1000]

        else:
            # 默认提取开头部分
            return chapter_content[:1000]

    def save_case(self, case: CaseInfo) -> Tuple[Path, Path]:
        """保存案例"""
        # 获取场景目录
        scene_dir_name = self.SCENE_DIR_MAP.get(case.scene_type, case.scene_type)
        scene_dir = self.cases_dir / scene_dir_name / case.genre
        scene_dir.mkdir(parents=True, exist_ok=True)

        # 文件名
        txt_filename = f"{case.scene_type}_{case.genre}_{case.novel_name}.txt"
        json_filename = f"{case.scene_type}_{case.genre}_{case.novel_name}.json"

        # 保存txt
        txt_path = scene_dir / txt_filename
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(case.content)

        # 保存json元数据
        json_path = scene_dir / json_filename
        metadata = {
            "case_id": case.case_id,
            "source": {
                "path": case.source_file,
                "novel_name": case.novel_name,
                "genre": case.genre,
            },
            "scene": {
                "type": case.scene_type,
                "chapter_index": case.chapter_index,
                "word_count": case.word_count,
            },
            "content_preview": case.content[:500],
            "quality": {
                "score": case.quality_score,
                "confidence": case.confidence,
                "has_ai_taste": case.has_ai_taste,
                "ai_expressions": case.ai_expressions,
            },
            "extract_time": case.extract_time,
            "batch": "batch2",
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return txt_path, json_path

    def scan_and_analyze(self, limit: int = None) -> Dict:
        """扫描并分析所有文件"""
        logger.info("开始扫描converted目录...")

        # 获取所有txt文件
        txt_files = list(self.converted_dir.glob("*.txt"))
        total = len(txt_files)

        if limit:
            txt_files = txt_files[:limit]

        logger.info(f"找到 {total} 个txt文件，处理 {len(txt_files)} 个")

        results = {
            "total_files": len(txt_files),
            "novels_found": 0,
            "non_novels": 0,
            "cases_extracted": 0,
            "errors": [],
        }

        for i, txt_file in enumerate(txt_files, 1):
            print(
                f"\r[{i}/{len(txt_files)}] 处理: {txt_file.name[:30]:<30}",
                end="",
                flush=True,
            )

            try:
                # 分析小说
                novel_info = self.analyze_novel(txt_file)

                if novel_info is None:
                    # 非小说或已处理
                    if str(txt_file) not in self.index["novels"]:
                        results["non_novels"] += 1
                        self.index["novels"][str(txt_file)] = {"is_novel": False}
                    continue

                # 读取内容
                content = self._read_file(txt_file)

                # 提取案例
                cases = self.extract_cases(novel_info, content)

                # 保存案例
                for case in cases:
                    txt_path, json_path = self.save_case(case)
                    self.index["cases"].append(
                        {
                            "case_id": case.case_id,
                            "novel_name": case.novel_name,
                            "scene_type": case.scene_type,
                            "genre": case.genre,
                            "quality_score": case.quality_score,
                            "txt_path": str(txt_path),
                            "json_path": str(json_path),
                        }
                    )

                # 更新索引
                self.index["novels"][str(txt_file)] = asdict(novel_info)

                # 更新统计
                results["novels_found"] += 1
                results["cases_extracted"] += len(cases)

                # 更新题材统计
                genre = novel_info.genre
                self.stats["by_genre"][genre] = self.stats["by_genre"].get(
                    genre, 0
                ) + len(cases)

                # 更新场景统计
                for case in cases:
                    scene = case.scene_type
                    self.stats["by_scene"][scene] = (
                        self.stats["by_scene"].get(scene, 0) + 1
                    )

            except Exception as e:
                logger.error(f"处理失败: {txt_file.name} - {e}")
                results["errors"].append(f"{txt_file.name}: {str(e)}")

        # 更新统计
        self.stats["total_files"] = len(self.index["novels"])
        self.stats["novels_found"] = results["novels_found"]
        self.stats["non_novels"] = results["non_novels"]
        self.stats["total_cases"] = self.case_counter

        # 保存
        self._save_index()
        self._save_stats()

        print(f"\n\n扫描完成!")
        print(f"  总文件数: {results['total_files']}")
        print(f"  识别为小说: {results['novels_found']}")
        print(f"  非小说内容: {results['non_novels']}")
        print(f"  提取案例数: {results['cases_extracted']}")
        print(f"  错误数: {len(results['errors'])}")

        return results

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "总文件数": self.stats.get("total_files", 0),
            "识别为小说": self.stats.get("novels_found", 0),
            "非小说内容": self.stats.get("non_novels", 0),
            "案例总数": self.stats.get("total_cases", 0),
            "按题材分布": self.stats.get("by_genre", {}),
            "按场景分布": self.stats.get("by_scene", {}),
            "最后更新": self.stats.get("last_update", "未知"),
        }


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="第二批资源处理工具")
    parser.add_argument("--scan", action="store_true", help="扫描并分析所有文件")
    parser.add_argument("--limit", type=int, default=None, help="处理文件数量限制")
    parser.add_argument("--stats", action="store_true", help="查看统计信息")

    args = parser.parse_args()

    processor = Batch2Processor()

    if args.scan:
        processor.scan_and_analyze(args.limit)
    elif args.stats:
        stats = processor.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
