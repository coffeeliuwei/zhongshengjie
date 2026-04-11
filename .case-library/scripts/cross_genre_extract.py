#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨题材批量提取脚本 v1.0
=====================================

功能：
1. 从所有题材目录中提取案例
2. 按场景类型组织，而非题材
3. 标注来源题材，便于跨题材借鉴
4. 支持优先级配置

使用方法：
    python cross_genre_extract.py --scan-all       # 扫描所有题材
    python cross_genre_extract.py --extract        # 执行提取
    python cross_genre_extract.py --extract --scene-type "战斗场景"  # 提取特定场景
    python cross_genre_extract.py --stats          # 查看统计
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

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

    def __init__(self, novel_path: str = None):
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

        self.novel_path = Path(novel_path)
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
            return {}

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

    def scan_all_genres(self) -> Dict[str, int]:
        """扫描所有题材目录"""
        genre_counts = {}

        # 题材目录映射
        genre_dirs = {
            "玄幻奇幻": ["玄幻奇幻", "起点爆款小说合集", "起点精选"],
            "武侠仙侠": ["武侠仙侠"],
            "现代都市": ["现代都市"],
            "历史军事": ["历史军事"],
            "科幻灵异": ["科幻灵异"],
            "青春校园": ["青春校园"],
            "游戏竞技": ["游戏竞技"],
            "女频言情": ["女频言情"],
        }

        for genre, dirs in genre_dirs.items():
            total = 0
            for dir_name in dirs:
                genre_path = self.novel_path / dir_name
                if genre_path.exists():
                    txt_files = list(genre_path.glob("*.txt"))
                    total += len(txt_files)
            genre_counts[genre] = total

        return genre_counts

    def get_extraction_plan(self) -> Dict:
        """获取提取计划"""
        target = self.strategy.get("target_distribution", {})
        by_scene = target.get("by_scene_type", {})
        by_genre = target.get("by_genre", {})

        return {
            "scene_targets": by_scene,
            "genre_targets": by_genre,
            "total_target": target.get("total_cases", 1000),
        }

    def extract_by_scene(
        self, scene_type: str, limit_per_genre: int = 10
    ) -> List[CrossGenreCase]:
        """
        按场景类型提取案例

        Args:
            scene_type: 场景类型
            limit_per_genre: 每个题材提取数量限制
        """
        cases = []

        # 获取该场景的最佳来源题材
        matrix = self.strategy.get("scene_extraction_matrix", {})
        scene_info = matrix.get(scene_type, {})
        best_sources = scene_info.get("最佳来源", [])

        # 如果没有指定，则从所有题材提取
        if not best_sources:
            best_sources = list(self.strategy.get("cross_genre_strategy", {}).keys())

        # 题材目录映射
        genre_dirs = {
            "玄幻奇幻": ["玄幻奇幻", "起点爆款小说合集", "起点精选"],
            "武侠仙侠": ["武侠仙侠"],
            "现代都市": ["现代都市"],
            "历史军事": ["历史军事"],
            "科幻灵异": ["科幻灵异"],
            "青春校园": ["青春校园"],
            "游戏竞技": ["游戏竞技"],
            "女频言情": ["女频言情"],
        }

        for genre in best_sources:
            if genre not in genre_dirs:
                continue

            genre_cases = []
            for dir_name in genre_dirs[genre]:
                genre_path = self.novel_path / dir_name
                if not genre_path.exists():
                    continue

                for txt_file in list(genre_path.glob("*.txt"))[:limit_per_genre]:
                    # 检查是否已提取
                    case_key = f"{scene_type}_{txt_file.stem}"
                    if any(
                        c.get("case_id", "").startswith(case_key)
                        for c in self.case_index.get("cases", [])
                    ):
                        continue

                    # 读取内容
                    content = self._read_file_safe(txt_file)
                    if not content:
                        continue

                    # 分析场景
                    detected_scenes = self.recognizer.analyze_segment(content[:3000])

                    # 查找目标场景
                    for scene in detected_scenes:
                        if scene.scene_type == scene_type:
                            case = CrossGenreCase(
                                case_id=f"{scene_type}_{genre}_{txt_file.stem}",
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
                                cross_genre_value=scene_info.get("跨题材价值", ""),
                            )
                            genre_cases.append(case)
                            break

                    if len(genre_cases) >= limit_per_genre:
                        break

                if len(genre_cases) >= limit_per_genre:
                    break

            cases.extend(genre_cases)

        return cases

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
        ]

        for scene_type in scene_types:
            try:
                # 计算每个题材的提取限制
                limit_per_genre = max(3, limit_per_scene // 6)

                cases = self.extract_by_scene(scene_type, limit_per_genre)

                # 保存案例
                for case in cases:
                    self._save_case(case)
                    results["by_genre"][case.source_genre] += 1

                results["by_scene_type"][scene_type] = len(cases)
                results["total_extracted"] += len(cases)

                print(f"  {scene_type}: {len(cases)} 个案例")

            except Exception as e:
                results["errors"].append(f"{scene_type}: {str(e)}")

        # 更新统计
        self._update_stats(results)
        self._save_case_index()

        return results

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

    def get_cross_genre_recommendations(self, scene_type: str) -> Dict:
        """获取跨题材推荐"""
        matrix = self.strategy.get("scene_extraction_matrix", {})
        scene_info = matrix.get(scene_type, {})

        return {
            "scene_type": scene_type,
            "best_sources": scene_info.get("最佳来源", []),
            "borrow_points": scene_info.get("借鉴要点", ""),
            "cross_value": scene_info.get("跨题材价值", ""),
        }


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="跨题材案例提取")
    parser.add_argument("--scan-all", action="store_true", help="扫描所有题材")
    parser.add_argument("--extract", action="store_true", help="执行提取")
    parser.add_argument("--scene-type", type=str, help="指定场景类型")
    parser.add_argument("--stats", action="store_true", help="查看统计")
    parser.add_argument("--plan", action="store_true", help="查看提取计划")
    parser.add_argument("--recommend", type=str, help="获取跨题材推荐")
    parser.add_argument("--limit", type=int, default=30, help="提取数量限制")

    args = parser.parse_args()

    extractor = CrossGenreExtractor()

    if args.scan_all:
        print("扫描所有题材目录...")
        counts = extractor.scan_all_genres()
        total = sum(counts.values())
        print(f"\n题材分布：")
        for genre, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {genre}: {count} 本")
        print(f"\n总计: {total} 本小说")

    elif args.extract:
        if args.scene_type:
            print(f"提取场景: {args.scene_type}")
            cases = extractor.extract_by_scene(args.scene_type, args.limit)
            print(f"提取完成: {len(cases)} 个案例")
            for case in cases[:5]:
                print(f"  [{case.source_genre}] {case.novel_name}")
        else:
            print("提取所有场景类型...")
            results = extractor.extract_all_scenes(args.limit)
            print(f"\n提取完成: {results['total_extracted']} 个案例")
            print(f"\n按场景类型:")
            for scene, count in sorted(results["by_scene_type"].items()):
                print(f"  {scene}: {count}")
            print(f"\n按题材:")
            for genre, count in sorted(
                results["by_genre"].items(), key=lambda x: -x[1]
            ):
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

    elif args.plan:
        plan = extractor.get_extraction_plan()
        print("提取计划：")
        print(f"  总目标: {plan['total_target']} 个案例")
        print(f"\n场景目标:")
        for scene, target in sorted(plan["scene_targets"].items(), key=lambda x: -x[1]):
            print(f"  {scene}: {target}")
        print(f"\n题材目标:")
        for genre, target in sorted(plan["genre_targets"].items(), key=lambda x: -x[1]):
            print(f"  {genre}: {target}")

    elif args.recommend:
        rec = extractor.get_cross_genre_recommendations(args.recommend)
        print(f"场景: {rec['scene_type']}")
        print(f"最佳来源: {', '.join(rec['best_sources'])}")
        print(f"借鉴要点: {rec['borrow_points']}")
        print(f"跨题材价值: {rec['cross_value']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
