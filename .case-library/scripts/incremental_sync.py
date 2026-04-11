#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量同步系统 v1.0
=====================================

功能：
1. 自动检测新加入的小说文件
2. 自动识别题材类型（含新题材检测）
3. 自动提取案例片段
4. 自动同步到向量数据库

新题材处理流程：
- 当题材置信度低于阈值时，标记为"未知题材"
- 自动提取内容特征词作为新题材候选特征
- 提示用户确认新题材名称
- 确认后自动更新 config.json

使用方法：
    python incremental_sync.py --scan
    python incremental_sync.py --process-new
    python incremental_sync.py --register-genre "悬疑推理" --features "推理,破案,侦探,线索"
"""

import json
import re
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict

# 导入现有模块
from genre_classifier import GenreClassifier
from enhanced_scene_recognizer import EnhancedSceneRecognizer


@dataclass
class NovelRecord:
    """小说记录"""

    file_path: str
    novel_name: str
    file_size: int
    file_hash: str
    genre: str
    genre_confidence: float
    genre_basis: str
    is_new_genre: bool
    suggested_genre: Optional[str]
    suggested_features: List[str]
    processed: bool
    case_count: int
    added_time: str
    processed_time: Optional[str]


@dataclass
class NewGenreCandidate:
    """新题材候选"""

    suggested_name: str
    extracted_features: List[str]
    sample_files: List[str]
    confidence: float
    confirmed: bool
    added_time: str


class NewGenreDetector:
    """新题材检测器"""

    # 已知题材的特征词集合（用于对比）
    KNOWN_GENRE_WORDS = set()

    # 新题材检测阈值
    UNKNOWN_THRESHOLD = 0.15  # 最高题材得分低于此值时认为是未知题材
    MIN_FEATURE_COUNT = 5  # 新题材至少需要5个特征词

    def __init__(self, classifier: GenreClassifier):
        self.classifier = classifier

        # 从分类器提取已知题材特征词
        for genre, keywords in classifier.GENRE_KEYWORDS.items():
            self.KNOWN_GENRE_WORDS.update(keywords.get("核心词", []))
            self.KNOWN_GENRE_WORDS.update(keywords.get("文件名特征", []))

    def detect_new_genre(
        self, content: str, file_path: Path
    ) -> Tuple[bool, Optional[NewGenreCandidate]]:
        """
        检测是否为新题材

        Returns:
            (是否新题材, 新题材候选信息)
        """
        if not content or len(content) < 5000:
            return False, None

        # 获取各题材得分
        _, scores = self.classifier.classify_by_content(content)

        # 最高得分
        max_score = max(scores.values()) if scores else 0
        max_genre = max(scores, key=scores.get) if scores else None

        # 计算相对置信度
        total_matches = sum(scores.values())
        relative_confidence = max_score / total_matches if total_matches > 0 else 0

        # 判断是否为未知题材
        if max_score < len(content[:3000]) * self.UNKNOWN_THRESHOLD / 100:
            # 提取特征词
            features = self._extract_genre_features(content)

            if len(features) >= self.MIN_FEATURE_COUNT:
                # 建议题材名称
                suggested_name = self._suggest_genre_name(file_path, features)

                candidate = NewGenreCandidate(
                    suggested_name=suggested_name,
                    extracted_features=features[:20],
                    sample_files=[str(file_path)],
                    confidence=1.0 - relative_confidence,
                    confirmed=False,
                    added_time=datetime.now().isoformat(),
                )

                return True, candidate

        return False, None

    def _extract_genre_features(self, content: str) -> List[str]:
        """
        从内容中提取潜在题材特征词

        策略：
        1. 提取高频名词/动词
        2. 排除已知题材特征词
        3. 排除通用词
        """
        # 通用词列表（不作为题材特征）
        COMMON_WORDS = {
            "的",
            "是",
            "在",
            "有",
            "和",
            "了",
            "不",
            "这",
            "那",
            "他",
            "她",
            "我",
            "你",
            "它",
            "们",
            "着",
            "过",
            "就",
            "都",
            "也",
            "又",
            "说",
            "道",
            "看",
            "想",
            "走",
            "来",
            "去",
            "做",
            "能",
            "会",
            "人",
            "事",
            "物",
            "时",
            "地",
            "方",
            "手",
            "眼",
            "头",
            "身",
        }

        # 使用简单的词频统计
        sample = content[:10000]

        # 提取2-4字的词语
        pattern = r'[^\s\d，。！？；："\'（）【】《》]{2,4}'
        words = re.findall(pattern, sample)

        # 统计词频
        from collections import Counter

        word_freq = Counter(words)

        # 筛选特征词
        features = []
        for word, freq in word_freq.most_common(50):
            if freq >= 3:  # 至少出现3次
                if word not in self.KNOWN_GENRE_WORDS:
                    if word not in COMMON_WORDS:
                        features.append(word)

        return features

    def _suggest_genre_name(self, file_path: Path, features: List[str]) -> str:
        """
        建议新题材名称

        策略：
        1. 从文件名/目录名推断
        2. 从特征词组合推断
        """
        path_str = str(file_path).lower()

        # 从路径推断
        path_keywords = {
            "悬疑": ["悬疑", "推理", "侦探", "破案"],
            "恐怖": ["恐怖", "惊悚", "鬼故事", "吓人"],
            "二次元": ["二次元", "动漫", "轻小说", "同人"],
            "体育": ["体育", "足球", "篮球", "运动"],
            "美食": ["美食", "烹饪", "厨师", "料理"],
            "音乐": ["音乐", "歌手", "乐队", "演奏"],
        }

        for name, keywords in path_keywords.items():
            for kw in keywords:
                if kw in path_str:
                    return name

        # 从特征词推断
        feature_set = set(features)
        for name, keywords in path_keywords.items():
            if len(feature_set & set(keywords)) >= 2:
                return name

        # 默认使用特征词组合
        if len(features) >= 3:
            return f"新题材-{features[0]}系"

        return "未知题材"


class IncrementalSyncManager:
    """增量同步管理器"""

    def __init__(self, config_path: str = None, novel_path: str = None):
        self.config_path = config_path or "D:\\动画\\众生界\\.case-library\\config.json"

        # 从配置加载小说资源目录
        if novel_path is None:
            try:
                import sys
                from pathlib import Path

                project_dir = Path(__file__).parent.parent.parent
                if str(project_dir) not in sys.path:
                    sys.path.insert(0, str(project_dir))

                from core.config_loader import get_config

                config = get_config()
                novel_sources = config.get("novel_sources", {})
                directories = novel_sources.get("directories", [])

                if directories:
                    novel_path = directories[0]
                else:
                    novel_path = r"E:\小说资源"  # 默认值
            except Exception:
                novel_path = r"E:\小说资源"  # 默认值

        self.novel_path = novel_path
        self.index_path = "D:\\动画\\众生界\\.case-library\\novel_index.json"
        self.new_genre_path = "D:\\动画\\众生界\\.case-library\\new_genres.json"

        # 加载配置
        self.config = self._load_config()

        # 初始化组件
        self.classifier = GenreClassifier()
        self.recognizer = EnhancedSceneRecognizer()
        self.new_genre_detector = NewGenreDetector(self.classifier)

        # 加载索引
        self.novel_index = self._load_novel_index()
        self.new_genres = self._load_new_genres()

    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"genres": []}

    def _load_novel_index(self) -> Dict:
        """加载小说索引"""
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"novels": {}, "stats": {"total": 0, "processed": 0}}

    def _load_new_genres(self) -> Dict:
        """加载新题材候选列表"""
        try:
            with open(self.new_genre_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"candidates": [], "confirmed": []}

    def _save_novel_index(self):
        """保存小说索引"""
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self.novel_index, f, ensure_ascii=False, indent=2)

    def _save_new_genres(self):
        """保存新题材列表"""
        with open(self.new_genre_path, "w", encoding="utf-8") as f:
            json.dump(self.new_genres, f, ensure_ascii=False, indent=2)

    def _save_config(self):
        """保存配置文件"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def scan_novels(self) -> List[NovelRecord]:
        """
        扫描小说目录，发现新文件

        Returns:
            新发现的小说列表
        """
        novel_dir = Path(self.novel_path)
        new_novels = []

        # 遍历所有txt文件
        for txt_file in novel_dir.rglob("*.txt"):
            file_path = str(txt_file)

            # 检查是否已处理
            if file_path in self.novel_index["novels"]:
                continue

            # 获取文件信息
            file_size = txt_file.stat().st_size

            # 计算文件hash（用于检测重复）
            file_hash = self._compute_file_hash(txt_file)

            # 检查hash是否已存在（防止重复文件）
            existing_hash = None
            for path, info in self.novel_index["novels"].items():
                if info.get("file_hash") == file_hash:
                    existing_hash = path
                    break

            if existing_hash:
                continue  # 跳过重复文件

            # 读取内容（用于题材检测）
            content = self._read_file_safe(txt_file)

            # 分类题材
            genre, basis = self.classifier.classify(txt_file, content)
            confidence = (
                self.classifier.get_genre_confidence(content, genre) if content else 0.5
            )

            # 检测是否为新题材
            is_new_genre, candidate = self.new_genre_detector.detect_new_genre(
                content, txt_file
            )

            # 创建记录
            record = NovelRecord(
                file_path=file_path,
                novel_name=txt_file.stem,
                file_size=file_size,
                file_hash=file_hash,
                genre=genre,
                genre_confidence=confidence,
                genre_basis=basis,
                is_new_genre=is_new_genre,
                suggested_genre=candidate.suggested_name if candidate else None,
                suggested_features=candidate.extracted_features if candidate else [],
                processed=False,
                case_count=0,
                added_time=datetime.now().isoformat(),
                processed_time=None,
            )

            new_novels.append(record)

            # 如果是新题材，记录候选
            if is_new_genre and candidate:
                self.new_genres["candidates"].append(asdict(candidate))

        # 更新索引
        for record in new_novels:
            self.novel_index["novels"][record.file_path] = asdict(record)

        self.novel_index["stats"]["total"] = len(self.novel_index["novels"])
        self._save_novel_index()
        self._save_new_genres()

        return new_novels

    def _compute_file_hash(self, file_path: Path) -> str:
        """计算文件MD5哈希"""
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                # 只读取前1MB计算hash（提高速度）
                hasher.update(f.read(1024 * 1024))
        except:
            pass
        return hasher.hexdigest()

    def _read_file_safe(self, file_path: Path) -> Optional[str]:
        """安全读取文件内容"""
        encodings = ["utf-8", "gb18030", "gbk", "gb2312", "big5"]

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                    # 检测乱码
                    if content and len(content) > 100:
                        return content
            except UnicodeDecodeError:
                continue
            except Exception:
                continue

        return None

    def register_new_genre(self, genre_name: str, features: List[str]) -> bool:
        """
        注册新题材

        Args:
            genre_name: 新题材名称
            features: 特征词列表（逗号分隔的字符串或列表）

        Returns:
            是否成功
        """
        if isinstance(features, str):
            features = [f.strip() for f in features.split(",")]

        # 检查题材是否已存在
        existing_names = [g["name"] for g in self.config.get("genres", [])]
        if genre_name in existing_names:
            print(f"题材 '{genre_name}' 已存在")
            return False

        # 生成题材ID
        genre_id = genre_name.lower().replace(" ", "_")

        # 添加到配置
        new_genre = {
            "id": genre_id,
            "name": genre_name,
            "sub_genres": [],
            "features": features,
            "added_time": datetime.now().isoformat(),
            "status": "active",
        }

        self.config["genres"].append(new_genre)
        self._save_config()

        # 更新分类器关键词
        self.classifier.GENRE_KEYWORDS[genre_name] = {
            "核心词": features[:15],
            "文件名特征": [genre_name],
        }

        # 标记候选为已确认
        for candidate in self.new_genres["candidates"]:
            if candidate["suggested_name"] == genre_name:
                candidate["confirmed"] = True
                self.new_genres["confirmed"].append(candidate)

        self._save_new_genres()

        # 更新已识别为该题材的小说记录
        for path, info in self.novel_index["novels"].items():
            if info.get("suggested_genre") == genre_name:
                info["genre"] = genre_name
                info["is_new_genre"] = False

        self._save_novel_index()

        print(f"新题材 '{genre_name}' 已注册，特征词：{features[:5]}...")
        return True

    def process_new_novels(self, limit: int = 50) -> Dict:
        """
        处理新小说，提取案例

        Args:
            limit: 最大处理数量

        Returns:
            处理结果统计
        """
        unprocessed = [
            NovelRecord(**info)
            for path, info in self.novel_index["novels"].items()
            if not info.get("processed", False)
        ]

        # 按置信度排序（高置信度优先）
        unprocessed.sort(key=lambda x: -x.genre_confidence)

        # 限制数量
        to_process = unprocessed[:limit]

        results = {
            "total": len(unprocessed),
            "processed": 0,
            "cases_extracted": 0,
            "new_genres_found": 0,
            "errors": [],
        }

        for record in to_process:
            try:
                # 读取内容
                content = self._read_file_safe(Path(record.file_path))

                if not content:
                    results["errors"].append(f"{record.novel_name}: 无法读取")
                    continue

                # 提取案例
                cases = self._extract_cases_from_novel(content, record)

                # 更新记录
                record.processed = True
                record.case_count = len(cases)
                record.processed_time = datetime.now().isoformat()

                self.novel_index["novels"][record.file_path] = asdict(record)

                results["processed"] += 1
                results["cases_extracted"] += len(cases)

                if record.is_new_genre:
                    results["new_genres_found"] += 1

            except Exception as e:
                results["errors"].append(f"{record.novel_name}: {str(e)}")

        # 更新统计
        self.novel_index["stats"]["processed"] = sum(
            1
            for info in self.novel_index["novels"].values()
            if info.get("processed", False)
        )

        self._save_novel_index()

        return results

    def _extract_cases_from_novel(
        self, content: str, record: NovelRecord
    ) -> List[Dict]:
        """
        从小说内容提取案例

        简化版：只提取开篇和结尾
        """
        cases = []

        # 按章节分割（简化）
        chapters = self._split_chapters(content)

        if not chapters:
            return cases

        # 提取第一章开篇
        if len(chapters) >= 1:
            first_chapter = chapters[0]["content"]
            if len(first_chapter) >= 500:
                # 分析场景
                scenes = self.recognizer.analyze_segment(
                    first_chapter[:1500], chapter_index=1
                )

                # 找到开篇场景
                for scene in scenes:
                    if scene.scene_type == "开篇场景":
                        case = {
                            "source": {
                                "path": record.file_path,
                                "novel_name": record.novel_name,
                                "genre": record.genre,
                            },
                            "scene_type": "开篇场景",
                            "content": first_chapter[:1000],
                            "confidence": scene.confidence,
                            "extract_time": datetime.now().isoformat(),
                        }
                        cases.append(case)
                        break

        # 提取最后一章结尾
        if len(chapters) >= 2:
            last_chapter = chapters[-1]["content"]
            if len(last_chapter) >= 300:
                scenes = self.recognizer.analyze_segment(
                    last_chapter[-500:], chapter_index=len(chapters), position_ratio=0.9
                )

                for scene in scenes:
                    if scene.scene_type == "结尾场景":
                        case = {
                            "source": {
                                "path": record.file_path,
                                "novel_name": record.novel_name,
                                "genre": record.genre,
                            },
                            "scene_type": "结尾场景",
                            "content": last_chapter[-400:],
                            "confidence": scene.confidence,
                            "extract_time": datetime.now().isoformat(),
                        }
                        cases.append(case)
                        break

        return cases

    def _split_chapters(self, content: str) -> List[Dict]:
        """分割章节（简化版）"""
        chapters = []

        # 章节标题模式
        patterns = [
            r"第[一二三四五六七八九十百千万零\d]+[章节回部卷]",
            r"Chapter\s*\d+",
            r"CHAPTER\s*\d+",
        ]

        combined_pattern = "|".join(patterns)
        matches = list(re.finditer(combined_pattern, content))

        if not matches:
            # 没有章节标记，视为单章
            chapters.append(
                {
                    "index": 1,
                    "title": "全文",
                    "content": content[:5000],  # 只取前5000字
                }
            )
        else:
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(content)

                chapters.append(
                    {
                        "index": i + 1,
                        "title": match.group(),
                        "content": content[start:end][:3000],  # 每章最多3000字
                    }
                )

        return chapters

    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            "config": {
                "genres_count": len(self.config.get("genres", [])),
                "scene_types_count": len(self.config.get("scene_types", [])),
            },
            "novel_index": {
                "total": self.novel_index["stats"]["total"],
                "processed": self.novel_index["stats"]["processed"],
                "unprocessed": self.novel_index["stats"]["total"]
                - self.novel_index["stats"]["processed"],
            },
            "new_genres": {
                "candidates": len(self.new_genres.get("candidates", [])),
                "confirmed": len(self.new_genres.get("confirmed", [])),
                "pending": len(
                    [
                        c
                        for c in self.new_genres.get("candidates", [])
                        if not c.get("confirmed", False)
                    ]
                ),
            },
        }

    def list_new_genre_candidates(self) -> List[Dict]:
        """列出待确认的新题材候选"""
        pending = [
            c
            for c in self.new_genres.get("candidates", [])
            if not c.get("confirmed", False)
        ]
        return pending


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="增量同步系统")
    parser.add_argument("--scan", action="store_true", help="扫描新小说")
    parser.add_argument("--process", action="store_true", help="处理新小说")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--limit", type=int, default=50, help="处理数量限制")
    parser.add_argument("--register-genre", type=str, help="注册新题材名称")
    parser.add_argument("--features", type=str, help="新题材特征词（逗号分隔）")
    parser.add_argument("--list-candidates", action="store_true", help="列出新题材候选")

    args = parser.parse_args()

    manager = IncrementalSyncManager()

    if args.scan:
        print("扫描小说目录...")
        new_novels = manager.scan_novels()
        print(f"发现 {len(new_novels)} 本新小说")

        new_genre_count = sum(1 for n in new_novels if n.is_new_genre)
        if new_genre_count > 0:
            print(f"其中 {new_genre_count} 本可能是新题材")

    elif args.process:
        print("处理新小说...")
        results = manager.process_new_novels(args.limit)
        print(f"处理完成：{results['processed']} 本")
        print(f"提取案例：{results['cases_extracted']} 个")
        if results["errors"]:
            print(f"错误：{len(results['errors'])} 个")

    elif args.status:
        status = manager.get_status()
        print("系统状态：")
        print(f"  已定义题材：{status['config']['genres_count']}")
        print(f"  小说总数：{status['novel_index']['total']}")
        print(f"  已处理：{status['novel_index']['processed']}")
        print(f"  待处理：{status['novel_index']['unprocessed']}")
        print(f"  新题材候选：{status['new_genres']['pending']}")

    elif args.register_genre and args.features:
        success = manager.register_new_genre(args.register_genre, args.features)
        if success:
            print(f"新题材 '{args.register_genre}' 已注册成功")

    elif args.list_candidates:
        candidates = manager.list_new_genre_candidates()
        print(f"待确认新题材候选：{len(candidates)}")
        for c in candidates[:10]:
            print(f"\n  建议名称：{c['suggested_name']}")
            print(f"  特征词：{c['extracted_features'][:5]}")
            print(f"  样本文件：{c['sample_files'][0] if c['sample_files'] else '无'}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
