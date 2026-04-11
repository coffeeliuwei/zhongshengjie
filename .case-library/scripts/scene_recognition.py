#!/usr/bin/env python3
"""
场景识别脚本：分析小说文本，识别关键场景类型
使用 LLM Agent 进行场景识别和质量评估
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SceneRecognizer:
    """场景识别器：分析小说文本，识别关键场景"""

    # 场景识别关键词
    SCENE_KEYWORDS = {
        "开篇": ["第一章", "第一节", "开篇", "序幕", "引子"],
        "人物出场": ["出现", "登场", "首次", "第一次见到", "走进", "踏入"],
        "战斗": [
            "战斗",
            "打斗",
            "厮杀",
            "交锋",
            "拳",
            "剑",
            "刀",
            "招",
            "功法",
            "法术",
        ],
        "对话": ['"', "「", "『", "说道", "问道", "回答", "回应"],
        "情感": ["心", "泪", "哭", "笑", "悲", "喜", "怒", "爱", "恨", "思念", "怀念"],
        "悬念": ["?", "疑问", "谜", "秘密", "隐藏", "未知", "究竟", "为何"],
        "转折": ["突然", "忽然", "意外", "没想到", "想不到", "转折", "变故"],
        "结尾": ["章末", "结尾", "本章完", "下章预告", "待续"],
        "环境": [
            "山",
            "水",
            "树",
            "花",
            "风",
            "雨",
            "雪",
            "月",
            "日",
            "天",
            "地",
            "景",
        ],
        "心理": ["心想", "心中", "内心", "暗想", "沉思", "思索", "思考", "念头"],
    }

    # 禁止项检测关键词（AI味表达）
    AI_EXPRESSIONS = [
        "一股",
        "一种",
        "仿佛",
        "宛如",
        "似乎",
        "好像",
        "不言而喻",
        "可想而知",
        "显而易见",
        "令人",
        "让人",
        "使人",
        "倍感",
        "不由得",
        "忍不住",
        "情不自禁",
        "恍若",
        "犹如",
        "恰似",
        "某种",
        "某种意义上",
    ]

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.case_library_path = Path(self.config.get("case_library_path", "."))
        self.output_dir = self.case_library_path / "extracted"
        self._ensure_dirs()

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        if config_path and Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)

        default_path = Path(__file__).parent.parent / "config.json"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return {}

    def _ensure_dirs(self):
        """确保必要目录存在"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def read_novel(self, novel_path: Path) -> str:
        """读取小说文件"""
        try:
            # 中文小说优先使用中文编码
            encodings = ["gb18030", "gbk", "gb2312", "utf-8", "big5"]

            for encoding in encodings:
                try:
                    with open(novel_path, "r", encoding=encoding) as f:
                        content = f.read()
                        # 验证是否成功读取且内容有效
                        if len(content) > 1000:
                            # 检查是否有有效的中文字符
                            import re

                            chinese_chars = re.findall(
                                r"[\u4e00-\u9fff]", content[:2000]
                            )
                            if len(chinese_chars) > 100:  # 至少有100个中文字符
                                logger.info(
                                    f"成功读取文件: {novel_path.name} (编码: {encoding})"
                                )
                                return content
                except UnicodeDecodeError:
                    continue

            logger.error(f"无法解码文件: {novel_path.name}")
            return None

        except Exception as e:
            logger.error(f"读取文件失败: {novel_path.name} - {e}")
            return None

    def split_chapters(self, content: str) -> List[Dict]:
        """分割章节"""
        chapters = []

        # 章节分割模式
        chapter_patterns = [
            r"第[一二三四五六七八九十百千万零\d]+[章节篇部回][^\n]*",
            r"[章节篇部回]\s*[一二三四五六七八九十百千万零\d]+[^\n]*",
            r"Chapter\s*\d+",
            r"CHAPTER\s*\d+",
            r"\d+\.\s*[^\n]+",
        ]

        # 找到所有章节标题
        chapter_positions = []
        for pattern in chapter_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                chapter_positions.append((match.start(), match.group()))

        # 按位置排序
        chapter_positions.sort(key=lambda x: x[0])

        # 分割章节内容
        for i, (pos, title) in enumerate(chapter_positions):
            # 确定章节结束位置
            if i < len(chapter_positions) - 1:
                end_pos = chapter_positions[i + 1][0]
            else:
                end_pos = len(content)

            chapter_content = content[pos:end_pos].strip()

            chapters.append(
                {
                    "index": i + 1,
                    "title": title,
                    "start_pos": pos,
                    "end_pos": end_pos,
                    "content": chapter_content,
                    "word_count": len(chapter_content),
                }
            )

        logger.info(f"分割完成: 共 {len(chapters)} 章")
        return chapters

    def detect_scene_type(self, text: str, position: str = None) -> List[str]:
        """检测文本片段的场景类型"""
        detected_types = []

        for scene_type, keywords in self.SCENE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    detected_types.append(scene_type)
                    break

        # 根据位置判断
        if position == "start":
            detected_types.append("开篇")
        elif position == "end":
            detected_types.append("结尾")

        return detected_types

    def detect_ai_expressions(self, text: str) -> Tuple[bool, List[str]]:
        """检测AI味表达"""
        found = []

        for expr in self.AI_EXPRESSIONS:
            count = text.count(expr)
            if count > 0:
                found.append((expr, count))

        # 如果高频出现AI味词汇
        total_count = sum(c for _, c in found)
        has_ai_taste = total_count > 5

        return has_ai_taste, found

    def extract_opening(self, chapter: Dict, max_words: int = 1000) -> Optional[Dict]:
        """提取开篇场景"""
        content = chapter.get("content", "")

        if len(content) < 200:
            return None

        # 提取开头部分
        opening = content[:max_words]

        # 检测AI味
        has_ai, ai_words = self.detect_ai_expressions(opening)

        return {
            "scene_type": "开篇",
            "content": opening,
            "word_count": len(opening),
            "chapter_index": chapter["index"],
            "chapter_title": chapter["title"],
            "has_ai_taste": has_ai,
            "ai_expressions": ai_words,
        }

    def extract_ending(self, chapter: Dict, max_words: int = 500) -> Optional[Dict]:
        """提取结尾场景"""
        content = chapter.get("content", "")

        if len(content) < 300:
            return None

        # 提取结尾部分
        ending = content[-max_words:]

        # 检测AI味
        has_ai, ai_words = self.detect_ai_expressions(ending)

        return {
            "scene_type": "结尾",
            "content": ending,
            "word_count": len(ending),
            "chapter_index": chapter["index"],
            "chapter_title": chapter["title"],
            "has_ai_taste": has_ai,
            "ai_expressions": ai_words,
        }

    def detect_character_appearance(self, content: str) -> List[Dict]:
        """检测人物出场"""
        appearances = []

        # 人物出场模式（简化版，实际需要更复杂的NLP）
        patterns = [
            r"([^\s]{2,4})[首次第一次](出现登场见到)",
            r"([^\s]{2,4})[走进踏入走进](房间门殿厅)",
            r"([^\s]{2,4})[身穿着装披挂]",
        ]

        # 这里简化处理，实际应用中应该使用更精确的人物识别
        return appearances

    def detect_battle_scene(self, content: str) -> List[Dict]:
        """检测战斗场景"""
        battle_scenes = []

        # 战斗关键词密度检测
        battle_keywords = self.SCENE_KEYWORDS["战斗"]
        keyword_count = sum(content.count(kw) for kw in battle_keywords)

        if keyword_count > 10:
            # 找到战斗片段的边界（简化版）
            # 实际应用中应该更精确地定位战斗开始和结束
            battle_scenes.append(
                {
                    "scene_type": "战斗",
                    "keyword_density": keyword_count / len(content) * 1000,
                    "detected": True,
                }
            )

        return battle_scenes

    def analyze_novel(self, novel_path: Path, extract_scenes: List[str] = None) -> Dict:
        """分析单本小说"""
        extract_scenes = extract_scenes or ["开篇", "结尾"]

        result = {
            "novel_path": str(novel_path),
            "novel_name": novel_path.stem,
            "analyze_time": datetime.now().isoformat(),
            "chapters": [],
            "extracted_scenes": [],
        }

        # 读取小说
        content = self.read_novel(novel_path)
        if not content:
            result["error"] = "无法读取文件"
            return result

        # 分割章节
        chapters = self.split_chapters(content)
        result["chapters"] = [
            {"index": c["index"], "title": c["title"], "word_count": c["word_count"]}
            for c in chapters
        ]

        # 提取场景
        for chapter in chapters:
            # 开篇：仅第一章
            if "开篇" in extract_scenes and chapter["index"] == 1:
                opening = self.extract_opening(chapter)
                if opening:
                    opening["novel_name"] = novel_path.stem
                    result["extracted_scenes"].append(opening)

            # 结尾：仅第一章结尾（钩子效果）和最后一章结尾
            if "结尾" in extract_scenes:
                last_chapter_idx = len(chapters)
                if chapter["index"] == 1 or chapter["index"] == last_chapter_idx:
                    ending = self.extract_ending(chapter)
                    if ending:
                        ending["novel_name"] = novel_path.stem
                        result["extracted_scenes"].append(ending)

        # 检测其他场景（简化版）
        for chapter in chapters[:10]:  # 只分析前10章
            battle_scenes = self.detect_battle_scene(chapter["content"])
            for bs in battle_scenes:
                if "战斗" in extract_scenes and bs.get("detected"):
                    result["extracted_scenes"].append(
                        {
                            "scene_type": "战斗",
                            "chapter_index": chapter["index"],
                            "chapter_title": chapter["title"],
                            "novel_name": novel_path.stem,
                        }
                    )

        logger.info(
            f"分析完成: {novel_path.stem} - 提取 {len(result['extracted_scenes'])} 个场景"
        )
        return result

    def batch_analyze(self, source_dir: Path, max_novels: int = 50) -> List[Dict]:
        """批量分析目录中的小说"""
        results = []

        # 获取txt文件
        txt_files = list(source_dir.glob("*.txt"))
        txt_files.extend(list(source_dir.glob("*.TXT")))

        # 限制数量
        txt_files = txt_files[:max_novels]

        logger.info(f"开始批量分析: {len(txt_files)} 个文件")

        for novel_path in txt_files:
            try:
                result = self.analyze_novel(novel_path)
                results.append(result)
            except Exception as e:
                logger.error(f"分析失败: {novel_path.name} - {e}")
                results.append({"novel_path": str(novel_path), "error": str(e)})

        return results

    def save_analysis(self, results: List[Dict], output_file: str = None) -> Path:
        """保存分析结果"""
        if not output_file:
            output_file = (
                self.output_dir
                / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"结果已保存: {output_file}")
        return Path(output_file)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="小说场景识别工具")
    parser.add_argument("--novel", type=str, help="单本小说路径")
    parser.add_argument("--dir", type=str, help="小说目录路径")
    parser.add_argument(
        "--scenes",
        type=str,
        nargs="+",
        default=["开篇", "结尾"],
        help="要提取的场景类型",
    )
    parser.add_argument("--max", type=int, default=50, help="最大处理数量")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--config", type=str, help="配置文件路径")

    args = parser.parse_args()

    recognizer = SceneRecognizer(args.config)

    if args.novel:
        result = recognizer.analyze_novel(Path(args.novel), args.scenes)
        results = [result]
    elif args.dir:
        results = recognizer.batch_analyze(Path(args.dir), args.max)
    else:
        print("请指定 --novel 或 --dir 参数")
        return

    output_path = recognizer.save_analysis(results, args.output)

    # 输出统计
    total_scenes = sum(len(r.get("extracted_scenes", [])) for r in results)
    print(f"\n分析完成:")
    print(f"  小说数量: {len(results)}")
    print(f"  提取场景: {total_scenes}")
    print(f"  结果文件: {output_path}")


if __name__ == "__main__":
    main()
