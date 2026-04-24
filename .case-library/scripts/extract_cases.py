#!/usr/bin/env python3
"""
案例提取主脚本：整合格式转换、场景识别、案例入库
提供完整的案例提取工作流
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime
import uuid

# 导入子模块
from convert_format import FormatConverter
from scene_recognition import SceneRecognizer

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CaseExtractor:
    """案例提取器：整合完整提取流程"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.case_library_path = Path(self.config.get("case_library_path", "."))

        self.converter = FormatConverter(config_path)
        self.recognizer = SceneRecognizer(config_path)

        self.case_counter = 0
        self.metadata_index = []

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

    def _get_scene_dir(self, scene_type: str, genre: str) -> Path:
        """获取场景存储目录"""
        # 场景类型映射
        scene_map = {
            "开篇": "01-开篇场景",
            "人物出场": "02-人物出场",
            "战斗": "03-战斗场景",
            "对话": "04-对话场景",
            "情感": "05-情感场景",
            "悬念": "06-悬念场景",
            "转折": "07-转折场景",
            "结尾": "08-结尾场景",
            "环境": "09-环境场景",
            "心理": "10-心理场景",
        }

        scene_dir = scene_map.get(scene_type, f"{scene_type}")
        return self.case_library_path / scene_dir / genre

    def _generate_case_id(self) -> str:
        """生成案例ID"""
        self.case_counter += 1
        return f"case_{self.case_counter:04d}"

    def _quality_score(self, scene_data: Dict) -> float:
        """评估案例质量"""
        score = 10.0

        # AI味扣分
        if scene_data.get("has_ai_taste"):
            ai_words = scene_data.get("ai_expressions", [])
            score -= min(len(ai_words) * 0.5, 3.0)

        # 字数限制
        word_count = scene_data.get("word_count", 0)
        if word_count < 200:
            score -= 1.0
        elif word_count > 1500:
            score -= 0.5

        # 完整性检查（简化版）
        content = scene_data.get("content", "")
        if content.endswith("...") or content.endswith("……"):
            score -= 1.0

        return max(0, min(10, score))

    def save_case(self, scene_data: Dict, genre: str = "玄幻奇幻") -> Dict:
        """保存单个案例"""
        case_id = self._generate_case_id()
        scene_type = scene_data.get("scene_type", "开篇")
        novel_name = scene_data.get("novel_name", "未知")

        # 获取存储目录
        save_dir = self._get_scene_dir(scene_type, genre)
        save_dir.mkdir(parents=True, exist_ok=True)

        # 计算质量分数
        quality_score = self._quality_score(scene_data)

        # 文件名
        txt_filename = f"{case_id}_{novel_name}_{scene_type}.txt"
        json_filename = f"{case_id}_{novel_name}_{scene_type}.json"

        # 保存内容
        txt_path = save_dir / txt_filename
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(scene_data.get("content", ""))

        # 构建元数据
        metadata = {
            "case_id": case_id,
            "source": {
                "path": scene_data.get("novel_path", ""),
                "novel_name": novel_name,
                "author": "",  # 需要额外识别
                "genre": genre,
                "sub_genre": "",
            },
            "scene": {
                "type": scene_type,
                "position": f"chapter_{scene_data.get('chapter_index', 1)}",
                "word_count": scene_data.get("word_count", 0),
            },
            "content": scene_data.get("content", "")[:500],  # 摘要
            "techniques": [],  # 需要额外识别
            "quality_score": quality_score,
            "has_ai_taste": scene_data.get("has_ai_taste", False),
            "extract_time": datetime.now().isoformat(),
        }

        # 保存元数据
        json_path = save_dir / json_filename
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # 添加到索引
        self.metadata_index.append(
            {
                "case_id": case_id,
                "scene_type": scene_type,
                "genre": genre,
                "novel_name": novel_name,
                "quality_score": quality_score,
                "txt_path": str(txt_path),
                "json_path": str(json_path),
            }
        )

        logger.info(
            f"案例保存: {case_id} - {novel_name} - {scene_type} - 分数 {quality_score:.1f}"
        )

        return {
            "case_id": case_id,
            "txt_path": str(txt_path),
            "json_path": str(json_path),
            "quality_score": quality_score,
        }

    def extract_from_source(
        self,
        source_id: str,
        sources_path: str = None,
        genres: List[str] = None,
        max_cases: int = 100,
    ) -> Dict:
        """从指定数据源提取案例"""
        # 加载数据源配置
        sources_config = self._load_sources(sources_path)

        target_source = None
        for source in sources_config.get("sources", []):
            if source["id"] == source_id:
                target_source = source
                break

        if not target_source:
            logger.error(f"未找到数据源: {source_id}")
            return {"error": "source_not_found"}

        source_path = Path(target_source["path"])
        if not source_path.exists():
            logger.error(f"数据源路径不存在: {source_path}")
            return {"error": "path_not_found"}

        # 获取题材（使用数据源配置或默认）
        genres = genres or target_source.get("genres", ["玄幻奇幻"])
        primary_genre = genres[0]

        results = {
            "source_id": source_id,
            "source_name": target_source["name"],
            "start_time": datetime.now().isoformat(),
            "cases_extracted": 0,
            "cases_saved": 0,
            "cases": [],
        }

        # 格式转换（如果需要）
        if target_source.get("format") == "mixed":
            logger.info(f"检测到混合格式，启动格式转换...")
            convert_result = self.converter.convert_directory(source_path)
            results["conversion"] = convert_result

        # 场景识别
        logger.info(f"启动场景识别...")
        analysis_results = self.recognizer.batch_analyze(source_path)

        # 保存案例
        for analysis in analysis_results:
            if analysis.get("error"):
                continue

            extracted_scenes = analysis.get("extracted_scenes", [])
            for scene_data in extracted_scenes:
                if results["cases_extracted"] >= max_cases:
                    break

                # 质量过滤
                quality_score = self._quality_score(scene_data)
                min_score = self.config.get("quality_threshold", {}).get(
                    "min_score", 6.0
                )

                if quality_score >= min_score:
                    case_info = self.save_case(scene_data, primary_genre)
                    results["cases"].append(case_info)
                    results["cases_saved"] += 1

                results["cases_extracted"] += 1

        # 保存索引
        self._save_index()

        # 更新数据源提取时间
        self._update_source_extract_time(source_id, sources_path)

        results["end_time"] = datetime.now().isoformat()

        logger.info(f"提取完成: {results['cases_saved']} 个案例入库")
        return results

    def _load_sources(self, sources_path: str) -> Dict:
        """加载数据源配置"""
        if sources_path and Path(sources_path).exists():
            with open(sources_path, "r", encoding="utf-8") as f:
                return json.load(f)

        default_path = self.case_library_path / "sources.json"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return {"sources": []}

    def _save_index(self):
        """保存案例索引"""
        index_path = self.case_library_path / "case_index.json"

        # 合并已有索引
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            self.metadata_index = existing + self.metadata_index

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata_index, f, ensure_ascii=False, indent=2)

        logger.info(f"索引已保存: {len(self.metadata_index)} 条")

    def _update_source_extract_time(self, source_id: str, sources_path: str):
        """更新数据源提取时间"""
        sources_path = sources_path or str(self.case_library_path / "sources.json")

        with open(sources_path, "r", encoding="utf-8") as f:
            sources_config = json.load(f)

        for source in sources_config.get("sources", []):
            if source["id"] == source_id:
                source["last_extract"] = datetime.now().isoformat()
                break

        with open(sources_path, "w", encoding="utf-8") as f:
            json.dump(sources_config, f, ensure_ascii=False, indent=2)

    def get_statistics(self) -> Dict:
        """获取案例库统计"""
        stats = {
            "total_cases": 0,
            "by_scene_type": {},
            "by_genre": {},
            "quality_distribution": {
                "excellent": 0,
                "good": 0,
                "acceptable": 0,
                "low": 0,
            },
        }

        # 遍历场景目录
        for scene_dir in self.case_library_path.iterdir():
            if scene_dir.is_dir() and scene_dir.name.startswith(
                ("01", "02", "03", "04", "05", "06", "07", "08", "09", "10")
            ):
                scene_type = (
                    scene_dir.name.split("-", 1)[1]
                    if "-" in scene_dir.name
                    else scene_dir.name
                )

                for genre_dir in scene_dir.iterdir():
                    if genre_dir.is_dir():
                        genre = genre_dir.name

                        # 统计案例文件
                        json_files = list(genre_dir.glob("*.json"))
                        count = len(json_files)

                        stats["total_cases"] += count
                        stats["by_scene_type"][scene_type] = (
                            stats["by_scene_type"].get(scene_type, 0) + count
                        )
                        stats["by_genre"][genre] = (
                            stats["by_genre"].get(genre, 0) + count
                        )

        return stats


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="案例提取工具")
    parser.add_argument("--source", type=str, help="数据源ID (如 source_001)")
    parser.add_argument("--dir", type=str, help="直接指定小说目录")
    parser.add_argument(
        "--genres", type=str, nargs="+", default=["玄幻奇幻"], help="题材类型"
    )
    parser.add_argument("--max", type=int, default=100, help="最大提取数量")
    parser.add_argument("--stats", action="store_true", help="显示案例库统计")
    parser.add_argument("--config", type=str, help="配置文件路径")

    args = parser.parse_args()

    extractor = CaseExtractor(args.config)

    if args.stats:
        stats = extractor.get_statistics()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return

    if args.source:
        result = extractor.extract_from_source(
            args.source, genres=args.genres, max_cases=args.max
        )
    elif args.dir:
        # 直接处理目录
        result = extractor.recognizer.batch_analyze(Path(args.dir))
        for analysis in result:
            if not analysis.get("error"):
                for scene in analysis.get("extracted_scenes", []):
                    extractor.save_case(scene, args.genres[0])
        extractor._save_index()
        result = {"cases_saved": extractor.case_counter}
    else:
        print("请指定 --source, --dir 或 --stats 参数")
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
