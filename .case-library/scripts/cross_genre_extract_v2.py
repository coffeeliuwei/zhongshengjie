#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨题材批量提取脚本 v1.1
=====================================

功能：
1. 从converted目录中提取案例
2. 按场景类型组织，而非题材
3. 标注来源题材，便于跨题材借鉴
4. 支持优先级配置

使用方法：
    python cross_genre_extract_v2.py --scan-all       # 扫描所有文件
    python cross_genre_extract_v2.py --extract        # 执行提取
    python cross_genre_extract_v2.py --stats          # 查看统计
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import random

# 导入现有模块
from genre_classifier import GenreClassifier
from enhanced_scene_recognizer import EnhancedSceneRecognizer, SceneType


@dataclass
class CrossGenreCase:
    """跨题材案例"""

    case_id: str
    scene_type: str
    source_genre: str
    novel_name: str
    file_path: str
    content: str
    confidence: float
    word_count: int
    extract_time: str
    cross_genre_value: str  # 跨题材价值说明


class CrossGenreExtractor:
    """跨题材案例提取器"""

    def __init__(self):
        self.converted_path = Path("D:\\动画\\众生界\\.case-library\\converted")
        self.output_path = Path("D:\\动画\\众生界\\.case-library")
        self.strategy_path = self.output_path / "cross_genre_strategy.json"

        # 加载策略
        self.strategy = self._load_strategy()

        # 初始化组件
        self.classifier = GenreClassifier()
        self.recognizer = EnhancedSceneRecognizer()

        # 加载已有索引
        self.case_index = self._load_case_index()

    def _load_strategy(self) -> Dict:
        """加载跨题材策略"""
        try:
            with open(self.strategy_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return self._create_default_strategy()

    def _create_default_strategy(self) -> Dict:
        """创建默认策略"""
        return {
            "scene_extraction_matrix": {
                "开篇场景": {
                    "最佳来源": ["玄幻奇幻", "科幻灵异", "悬疑推理"],
                    "跨题材价值": "不同开篇风格多样性",
                },
                "战斗场景": {
                    "最佳来源": ["玄幻奇幻", "武侠仙侠", "历史军事"],
                    "跨题材价值": "武侠招式提升玄幻战斗细腻度",
                },
                "对话场景": {
                    "最佳来源": ["现代都市", "女频言情", "历史军事"],
                    "跨题材价值": "都市对话技巧提升互动质量",
                },
                "情感场景": {
                    "最佳来源": ["女频言情", "青春校园", "现代都市"],
                    "跨题材价值": "言情情感细腻提升玄幻情感线",
                },
                "悬念场景": {
                    "最佳来源": ["悬疑推理", "科幻灵异", "玄幻奇幻"],
                    "跨题材价值": "悬疑技法是玄幻剧情张力核心",
                },
            }
        }

    def _load_case_index(self) -> Dict:
        """加载案例索引"""
        index_path = self.output_path / "case_index.json"
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"cases": [], "stats": {}}

    def _save_case_index(self):
        """保存案例索引"""
        index_path = self.output_path / "case_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(self.case_index, f, ensure_ascii=False, indent=2)

    def scan_all_files(self) -> Dict[str, int]:
        """扫描converted目录中的所有文件"""
        if not self.converted_path.exists():
            return {}

        txt_files = list(self.converted_path.glob("*.txt"))
        return {"total": len(txt_files)}

    def classify_novel_genre(self, novel_name: str, content_sample: str) -> str:
        """根据小说名和内容判断题材"""
        # 基于小说名关键词判断
        name_lower = novel_name.lower()

        # 关键词映射
        genre_keywords = {
            "玄幻奇幻": [
                "玄幻",
                "异世",
                "大陆",
                "龙王",
                "帝尊",
                "神帝",
                "修仙",
                "仙帝",
                "仙王",
                "武帝",
            ],
            "武侠仙侠": [
                "武侠",
                "仙侠",
                "江湖",
                "武林",
                "剑客",
                "侠客",
                "门派",
                "宗门",
            ],
            "现代都市": ["都市", "总裁", "豪门", "明星", "娱乐", "重生之都市"],
            "历史军事": ["历史", "三国", "大明", "大唐", "大宋", "战争", "军旅"],
            "科幻灵异": ["科幻", "末世", "丧尸", "异能", "灵异", "鬼", "恐怖"],
            "游戏竞技": ["游戏", "网游", "电竞", "LOL", "DNF", "DOTA", "王者"],
            "女频言情": ["王爷", "王妃", "皇后", "宫斗", "宅斗", "甜宠", "霸总"],
            "青春校园": ["校园", "青春", "校草", "校花", "学生", "高中", "大学"],
        }

        for genre, keywords in genre_keywords.items():
            for kw in keywords:
                if kw in novel_name:
                    return genre

        # 基于内容判断
        content_lower = content_sample[:2000]
        for genre, keywords in genre_keywords.items():
            matches = sum(1 for kw in keywords if kw in content_lower)
            if matches >= 2:
                return genre

        return "玄幻奇幻"  # 默认

    def extract_all_scenes(self, limit_per_scene: int = 30) -> Dict:
        """
        提取所有场景类型

        Args:
            limit_per_scene: 每种场景总提取限制
        """
        results = {
            "total_extracted": 0,
            "by_scene_type": {},
            "by_genre": defaultdict(int),
            "errors": [],
        }

        # 获取所有txt文件
        txt_files = list(self.converted_path.glob("*.txt"))
        random.shuffle(txt_files)  # 随机打乱以获取多样性

        # 场景类型列表（22种已启用）
        scene_types = [
            "开篇场景",
            "结尾场景",
            "战斗场景",
            "对话场景",
            "情感场景",
            "悬念场景",
            "转折场景",
            "心理场景",
            "环境场景",
            "人物出场",
        ]

        scene_counts = {st: 0 for st in scene_types}

        for txt_file in txt_files:
            # 检查是否所有场景都已达标
            if all(c >= limit_per_scene for c in scene_counts.values()):
                break

            try:
                # 读取内容
                content = self._read_file_safe(txt_file)
                if not content or len(content) < 1000:
                    continue

                # 分类题材
                genre = self.classify_novel_genre(txt_file.stem, content)

                # 分析场景
                detected_scenes = self.recognizer.analyze_segment(content[:5000])

                for scene in detected_scenes:
                    scene_type = scene.scene_type
                    if scene_type not in scene_counts:
                        continue
                    if scene_counts[scene_type] >= limit_per_scene:
                        continue

                    # 创建案例
                    case = CrossGenreCase(
                        case_id=f"{scene_type}_{genre}_{txt_file.stem[:20]}",
                        scene_type=scene_type,
                        source_genre=genre,
                        novel_name=txt_file.stem,
                        file_path=str(txt_file),
                        content=scene.content[:1500]
                        if len(scene.content) > 1500
                        else scene.content,
                        confidence=scene.confidence,
                        word_count=len(scene.content),
                        extract_time=datetime.now().isoformat(),
                        cross_genre_value=self._get_cross_genre_value(scene_type),
                    )

                    # 保存案例
                    self._save_case(case)
                    scene_counts[scene_type] += 1
                    results["by_genre"][genre] += 1
                    results["total_extracted"] += 1

            except Exception as e:
                results["errors"].append(f"{txt_file.name}: {str(e)}")

        results["by_scene_type"] = scene_counts

        # 更新统计
        self._update_stats(results)
        self._save_case_index()

        return results

    def _get_cross_genre_value(self, scene_type: str) -> str:
        """获取跨题材价值说明"""
        matrix = self.strategy.get("scene_extraction_matrix", {})
        return matrix.get(scene_type, {}).get("跨题材价值", "跨题材借鉴价值")

    def _save_case(self, case: CrossGenreCase):
        """保存案例到文件"""
        # 创建场景目录
        scene_dir = self.output_path / "cases" / case.scene_type
        scene_dir.mkdir(parents=True, exist_ok=True)

        # 保存案例文件
        case_file = scene_dir / f"{case.case_id}.txt"
        with open(case_file, "w", encoding="utf-8") as f:
            f.write(case.content)

        # 保存元数据
        meta_file = scene_dir / f"{case.case_id}.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(asdict(case), f, ensure_ascii=False, indent=2)

        # 更新索引
        self.case_index["cases"].append(
            {
                "case_id": case.case_id,
                "scene_type": case.scene_type,
                "source_genre": case.source_genre,
                "novel_name": case.novel_name,
                "confidence": case.confidence,
                "word_count": case.word_count,
            }
        )

    def _read_file_safe(self, file_path: Path) -> Optional[str]:
        """安全读取文件"""
        encodings = ["utf-8", "gb18030", "gbk", "gb2312", "big5"]

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                    if content and len(content) > 500:
                        return content
            except UnicodeDecodeError:
                continue
            except Exception:
                continue

        return None

    def _update_stats(self, results: Dict):
        """更新统计信息"""
        stats = self.case_index.get("stats", {})

        stats["total_cases"] = len(self.case_index["cases"])
        stats["last_extract"] = datetime.now().isoformat()
        stats["by_scene_type"] = results.get("by_scene_type", {})
        stats["by_genre"] = dict(results.get("by_genre", {}))

        self.case_index["stats"] = stats

    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = self.case_index.get("stats", {})

        # 按场景类型统计
        by_scene = defaultdict(int)
        for case in self.case_index.get("cases", []):
            by_scene[case.get("scene_type", "未知")] += 1

        # 按题材统计
        by_genre = defaultdict(int)
        for case in self.case_index.get("cases", []):
            by_genre[case.get("source_genre", "未知")] += 1

        return {
            "total_cases": len(self.case_index.get("cases", [])),
            "by_scene_type": dict(by_scene),
            "by_genre": dict(by_genre),
            "last_extract": stats.get("last_extract", "未提取"),
        }


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="跨题材案例提取")
    parser.add_argument("--scan-all", action="store_true", help="扫描所有文件")
    parser.add_argument("--extract", action="store_true", help="执行提取")
    parser.add_argument("--stats", action="store_true", help="查看统计")
    parser.add_argument("--limit", type=int, default=30, help="提取数量限制")

    args = parser.parse_args()

    extractor = CrossGenreExtractor()

    if args.scan_all:
        print("扫描converted目录...")
        counts = extractor.scan_all_files()
        print(f"\n总计: {counts.get('total', 0)} 个txt文件")

    elif args.extract:
        print("提取所有场景类型...")
        results = extractor.extract_all_scenes(args.limit)
        print(f"\n提取完成: {results['total_extracted']} 个案例")
        print(f"\n按场景类型:")
        for scene, count in sorted(results["by_scene_type"].items()):
            print(f"  {scene}: {count}")
        print(f"\n按题材:")
        for genre, count in sorted(results["by_genre"].items(), key=lambda x: -x[1]):
            print(f"  {genre}: {count}")

    elif args.stats:
        stats = extractor.get_stats()
        print(f"案例库统计：")
        print(f"  总计: {stats['total_cases']} 个案例")
        print(f"  最后提取: {stats['last_extract']}")
        print(f"\n按场景类型:")
        for scene, count in sorted(stats["by_scene_type"].items(), key=lambda x: -x[1]):
            print(f"  {scene}: {count}")
        print(f"\n按题材:")
        for genre, count in sorted(stats["by_genre"].items(), key=lambda x: -x[1]):
            print(f"  {genre}: {count}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
