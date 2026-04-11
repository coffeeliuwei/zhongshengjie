"""
小说清洗流程入口脚本
====================

整合清洗模块，执行完整清洗流程：
1. 语言检测（NovelValidator）
2. 内容验证（NovelValidator）
3. 深度清洗（DeepCleaner）
4. 质量评分（QualityScorer）
5. 输出到clean目录

使用方法:
    python run_clean.py --help
    python run_clean.py --limit 100  # 测试模式，只处理100本
    python run_clean.py --all        # 全量处理
    python run_clean.py --status     # 查看状态
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from tqdm import tqdm

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "core"))
sys.path.insert(0, str(PROJECT_ROOT / ".novel-extractor"))

# 导入清洗模块
try:
    from validators.novel_validator import NovelValidator, validate_novel
    from cleaners.deep_cleaner import DeepCleaner, deep_clean
    from scorers.quality_scorer import QualityScorer, score_text

    # 导入配置加载器
    from config_loader import (
        get_config,
        get_project_root,
        get_quality_thresholds,
        get_clean_dir,
        get_case_library_dir,
    )

    CONFIG_LOADED = True
except ImportError as e:
    print(f"[警告] 无法导入模块: {e}")
    print("[提示] 请确保已安装所有依赖: pip install lz4 jieba")
    CONFIG_LOADED = False

    # 使用默认配置
    def get_quality_thresholds():
        return {
            "chinese_ratio_min": 0.6,
            "novel_features_min": 10,
            "quality_score_min": 0.6,
            "noise_ratio_max": 0.10,
        }

    def get_clean_dir():
        return PROJECT_ROOT / ".case-library" / "clean"

    def get_case_library_dir():
        return PROJECT_ROOT / ".case-library"


class NovelCleanPipeline:
    """小说清洗流程管道"""

    def __init__(self):
        """初始化清洗管道"""
        # 初始化各模块
        self.validator = NovelValidator()
        self.cleaner = DeepCleaner()
        self.scorer = QualityScorer()

        # 获取配置
        self.thresholds = get_quality_thresholds()
        self.clean_dir = get_clean_dir()
        self.case_library_dir = get_case_library_dir()
        self.converted_dir = self.case_library_dir / "converted"

        # 确保输出目录存在
        self.clean_dir.mkdir(parents=True, exist_ok=True)

        # 统计数据
        self.stats = {
            "total": 0,
            "valid": 0,
            "filtered_chinese": 0,
            "filtered_non_novel": 0,
            "filtered_quality": 0,
            "filtered_retention": 0,
            "errors": 0,
        }

        # 清洗日志
        self.log_file = self.clean_dir / "clean_log.json"
        self.logs: List[Dict] = []

    def clean_single(self, file_path: Path) -> Dict[str, Any]:
        """
        清洗单个小说文件

        Args:
            file_path: 小说文件路径

        Returns:
            清洗结果字典
        """
        result = {
            "file": file_path.name,
            "status": "unknown",
            "reason": "",
            "chinese_ratio": 0.0,
            "feature_count": 0,
            "quality_score": 0.0,
            "retention_rate": 1.0,
            "original_size": 0,
            "cleaned_size": 0,
        }

        try:
            # Step 1: 读取文件
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            result["original_size"] = len(content)

            if not content.strip():
                result["status"] = "rejected"
                result["reason"] = "empty_content"
                return result

            # Step 2: 语言检测 + 内容验证
            validation = self.validator.validate(content)
            result["chinese_ratio"] = validation.chinese_ratio
            result["feature_count"] = validation.feature_count

            if not validation.is_valid:
                result["status"] = "rejected"
                if validation.chinese_ratio < self.thresholds.get(
                    "chinese_ratio_min", 0.6
                ):
                    result["reason"] = "chinese_ratio_low"
                else:
                    result["reason"] = "non_novel_content"
                return result

            # Step 3: 深度清洗
            cleaned = self.cleaner.clean(content)
            result["retention_rate"] = cleaned.get("retention_rate", 1.0)
            result["cleaned_size"] = len(cleaned.get("text", ""))

            # 检查保留率
            if result["retention_rate"] < 0.5:
                result["status"] = "rejected"
                result["reason"] = "retention_rate_low"
                return result

            # Step 4: 质量评分
            quality = self.scorer.score(cleaned.get("text", ""))
            result["quality_score"] = quality.get("score", 0)

            if quality.get("score", 0) < self.thresholds.get("quality_score_min", 0.6):
                result["status"] = "rejected"
                result["reason"] = "quality_score_low"
                return result

            # Step 5: 保存清洗后的文件
            clean_file = self.clean_dir / file_path.name
            clean_file.write_text(cleaned.get("text", ""), encoding="utf-8")

            result["status"] = "accepted"
            result["reason"] = "cleaned"

        except Exception as e:
            result["status"] = "error"
            result["reason"] = str(e)

        return result

    def run(self, limit: int = None, verbose: bool = True) -> Dict[str, Any]:
        """
        执行清洗流程

        Args:
            limit: 处理文件数量限制（用于测试）
            verbose: 是否显示进度

        Returns:
            统计结果
        """
        # 获取待处理文件
        files = list(self.converted_dir.glob("*.txt"))

        if limit:
            files = files[:limit]

        self.stats["total"] = len(files)

        # 显示开始信息
        if verbose:
            print("=" * 60)
            print("小说清洗流程")
            print("=" * 60)
            print(f"输入目录: {self.converted_dir}")
            print(f"输出目录: {self.clean_dir}")
            print(f"待处理文件: {self.stats['total']}")
            print(f"阈值配置:")
            print(f"  - 中文比例: {self.thresholds.get('chinese_ratio_min', 0.6):.0%}")
            print(f"  - 特征词数: {self.thresholds.get('novel_features_min', 10)}")
            print(f"  - 质量评分: {self.thresholds.get('quality_score_min', 0.6)}")
            print("=" * 60)
            print()

        # 处理文件
        iterator = tqdm(files, desc="清洗进度") if verbose else files

        for file_path in iterator:
            result = self.clean_single(file_path)
            self.logs.append(result)

            # 更新统计
            if result["status"] == "accepted":
                self.stats["valid"] += 1
            elif result["status"] == "rejected":
                reason = result["reason"]
                if reason == "chinese_ratio_low":
                    self.stats["filtered_chinese"] += 1
                elif reason == "non_novel_content":
                    self.stats["filtered_non_novel"] += 1
                elif reason == "quality_score_low":
                    self.stats["filtered_quality"] += 1
                elif reason == "retention_rate_low":
                    self.stats["filtered_retention"] += 1
            else:
                self.stats["errors"] += 1

        # 保存日志
        self._save_log()

        # 显示统计结果
        if verbose:
            self._print_stats()

        return self.stats

    def _save_log(self):
        """保存清洗日志"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "thresholds": self.thresholds,
            "logs": self.logs,
        }

        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

    def _print_stats(self):
        """打印统计结果"""
        print()
        print("=" * 60)
        print("清洗统计")
        print("=" * 60)
        print(f"总文件数: {self.stats['total']}")
        print(
            f"有效文件: {self.stats['valid']} ({self.stats['valid'] / self.stats['total']:.1%})"
        )
        print()
        print("过滤统计:")
        print(f"  - 中文比例过低: {self.stats['filtered_chinese']}")
        print(f"  - 非小说内容: {self.stats['filtered_non_novel']}")
        print(f"  - 质量评分过低: {self.stats['filtered_quality']}")
        print(f"  - 保留率过低: {self.stats['filtered_retention']}")
        print(f"  - 处理错误: {self.stats['errors']}")
        print()
        print(f"日志文件: {self.log_file}")
        print("=" * 60)

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        converted_count = len(list(self.converted_dir.glob("*.txt")))
        clean_count = len(list(self.clean_dir.glob("*.txt")))

        # 检查是否有清洗日志
        if self.log_file.exists():
            with open(self.log_file, "r", encoding="utf-8") as f:
                log_data = json.load(f)
            last_clean_time = log_data.get("timestamp", "未知")
            last_stats = log_data.get("stats", {})
        else:
            last_clean_time = "未执行"
            last_stats = {}

        return {
            "converted_count": converted_count,
            "clean_count": clean_count,
            "last_clean_time": last_clean_time,
            "last_stats": last_stats,
            "clean_dir": str(self.clean_dir),
        }


def print_status():
    """打印当前状态"""
    pipeline = NovelCleanPipeline()
    status = pipeline.get_status()

    print("=" * 60)
    print("清洗流程状态")
    print("=" * 60)
    print(f"转换目录文件数: {status['converted_count']}")
    print(f"清洗目录文件数: {status['clean_count']}")
    print(f"上次清洗时间: {status['last_clean_time']}")
    print(f"清洗目录: {status['clean_dir']}")

    if status["last_stats"]:
        print()
        print("上次清洗统计:")
        stats = status["last_stats"]
        print(f"  - 总处理: {stats.get('total', 0)}")
        print(f"  - 有效: {stats.get('valid', 0)}")
        print(f"  - 过滤: {stats.get('total', 0) - stats.get('valid', 0)}")

    print("=" * 60)


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="小说清洗流程入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="处理文件数量限制（测试模式）",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="全量处理所有文件",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="查看清洗状态",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式（不显示进度）",
    )

    args = parser.parse_args()

    # 查看状态
    if args.status:
        print_status()
        return

    # 执行清洗
    pipeline = NovelCleanPipeline()

    limit = None if args.all else args.limit

    if limit is None and not args.all:
        # 默认测试模式，处理10个文件
        print("[提示] 未指定 --all 或 --limit，默认测试模式处理10个文件")
        print("[提示] 使用 --all 全量处理，或 --limit N 处理指定数量")
        print()
        limit = 10

    pipeline.run(limit=limit, verbose=not args.quiet)


if __name__ == "__main__":
    main()
