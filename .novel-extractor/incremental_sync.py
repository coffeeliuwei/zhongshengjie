"""
增量同步系统

当 E:\小说资源 添加新小说时，自动检测并增量提炼

使用方法:
    # 扫描新小说
    python incremental_sync.py --scan

    # 处理新小说
    python incremental_sync.py --process

    # 查看状态
    python incremental_sync.py --status
"""

import sys
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    PROJECT_DIR,
    NOVEL_SOURCE_DIR,
    EXTRACTOR_DIR,
    PROGRESS_DIR,
    EXTRACTION_DIMENSIONS,
    Priority,
)


@dataclass
class NovelIndex:
    """小说索引"""

    novel_id: str
    path: str
    size: int
    modified_time: str
    format: str
    processed: bool = False
    processed_dimensions: List[str] = None

    def __post_init__(self):
        if self.processed_dimensions is None:
            self.processed_dimensions = []


class IncrementalSyncManager:
    """增量同步管理器"""

    def __init__(self):
        self.index_path = EXTRACTOR_DIR / "novel_index.json"
        self.index: Dict[str, NovelIndex] = self._load_index()

    def _load_index(self) -> Dict[str, NovelIndex]:
        """加载索引"""
        if self.index_path.exists():
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {k: NovelIndex(**v) for k, v in data.items()}
        return {}

    def _save_index(self):
        """保存索引"""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(
                {k: asdict(v) for k, v in self.index.items()},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _generate_novel_id(self, path: Path) -> str:
        """生成小说ID"""
        relative = str(path.relative_to(NOVEL_SOURCE_DIR))
        return hashlib.md5(relative.encode()).hexdigest()[:12]

    def scan_new_novels(self) -> Dict[str, List[Path]]:
        """扫描新小说"""
        # 动态获取小说资源目录
        try:
            from config import NOVEL_SOURCE_DIR

            source_dir = str(NOVEL_SOURCE_DIR)
        except Exception:
            source_dir = "配置文件中指定的目录"

        print(f"\n[扫描] 检查 {source_dir} ...")

        supported_formats = [".txt", ".epub", ".mobi"]

        new_novels = []
        modified_novels = []
        existing_count = 0

        for fmt in supported_formats:
            for novel_path in NOVEL_SOURCE_DIR.rglob(f"*{fmt}"):
                novel_id = self._generate_novel_id(novel_path)

                # 获取文件信息
                stat = novel_path.stat()
                size = stat.st_size
                modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()

                if novel_id in self.index:
                    # 检查是否修改
                    existing = self.index[novel_id]
                    if existing.modified_time != modified_time or existing.size != size:
                        modified_novels.append(novel_path)
                        # 更新索引
                        existing.size = size
                        existing.modified_time = modified_time
                        existing.processed = False
                        existing.processed_dimensions = []
                    else:
                        existing_count += 1
                else:
                    # 新小说
                    new_novels.append(novel_path)
                    # 添加到索引
                    self.index[novel_id] = NovelIndex(
                        novel_id=novel_id,
                        path=str(novel_path),
                        size=size,
                        modified_time=modified_time,
                        format=fmt,
                        processed=False,
                        processed_dimensions=[],
                    )

        # 保存索引
        self._save_index()

        print(f"[结果]")
        print(f"  已有小说: {existing_count}")
        print(f"  新增小说: {len(new_novels)}")
        print(f"  修改小说: {len(modified_novels)}")

        return {
            "new": new_novels,
            "modified": modified_novels,
            "existing": existing_count,
        }

    def get_pending_novels(self, dimension_id: str = None) -> List[Path]:
        """获取待处理的小说"""
        pending = []

        for novel_id, novel in self.index.items():
            if not novel.processed:
                pending.append(Path(novel.path))
            elif dimension_id and dimension_id not in novel.processed_dimensions:
                pending.append(Path(novel.path))

        return pending

    def mark_processed(self, novel_id: str, dimension_id: str):
        """标记已处理"""
        if novel_id in self.index:
            novel = self.index[novel_id]
            if dimension_id not in novel.processed_dimensions:
                novel.processed_dimensions.append(dimension_id)

            # 检查是否所有维度都处理完
            all_dimensions = list(EXTRACTION_DIMENSIONS.keys())
            if set(novel.processed_dimensions) == set(all_dimensions):
                novel.processed = True

            self._save_index()

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        total = len(self.index)
        processed = sum(1 for n in self.index.values() if n.processed)
        pending = total - processed

        # 按格式统计
        formats = {}
        for novel in self.index.values():
            fmt = novel.format
            formats[fmt] = formats.get(fmt, 0) + 1

        # 按维度统计处理进度
        dimension_progress = {}
        for dim_id in EXTRACTION_DIMENSIONS:
            processed_count = sum(
                1 for n in self.index.values() if dim_id in n.processed_dimensions
            )
            dimension_progress[dim_id] = {
                "processed": processed_count,
                "total": total,
                "percentage": round(processed_count / total * 100, 1)
                if total > 0
                else 0,
            }

        return {
            "total_novels": total,
            "processed": processed,
            "pending": pending,
            "by_format": formats,
            "dimension_progress": dimension_progress,
        }

    def process_new_novels(
        self, dimension_id: str = None, priority: str = None, limit: int = None
    ):
        """处理新小说"""
        from run_extractor import create_batch_extractor

        print("\n[处理] 开始增量提炼...")

        batch = create_batch_extractor()

        # 确定要运行的维度
        dimensions_to_run = []
        if dimension_id:
            dimensions_to_run = [dimension_id]
        elif priority:
            priority_map = {
                "high": Priority.HIGH,
                "medium": Priority.MEDIUM,
                "low": Priority.LOW,
            }
            target_priority = priority_map.get(priority.lower())
            dimensions_to_run = [
                dim_id
                for dim_id, dim in EXTRACTION_DIMENSIONS.items()
                if dim.priority == target_priority
            ]
        else:
            dimensions_to_run = list(EXTRACTION_DIMENSIONS.keys())

        # 对每个维度处理未处理的小说
        for dim_id in dimensions_to_run:
            extractor = batch.extractors.get(dim_id)
            if not extractor:
                continue

            print(f"\n[维度] {EXTRACTION_DIMENSIONS[dim_id].name}")

            # 获取待处理的小说
            pending = self.get_pending_novels(dim_id)

            if limit:
                pending = pending[:limit]

            print(f"  待处理: {len(pending)} 本")

            # 处理
            for i, novel_path in enumerate(pending):
                novel_id = self._generate_novel_id(novel_path)

                # 标记处理中
                self.mark_processed(novel_id, dim_id)

                if (i + 1) % 10 == 0:
                    print(f"  进度: {i + 1}/{len(pending)}")

        print("\n[完成] 增量提炼结束")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="增量同步系统")
    parser.add_argument("--scan", action="store_true", help="扫描新小说")
    parser.add_argument("--process", action="store_true", help="处理新小说")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--dimension", type=str, help="处理特定维度")
    parser.add_argument(
        "--priority", choices=["high", "medium", "low"], help="按优先级处理"
    )
    parser.add_argument("--limit", type=int, help="限制处理数量")
    parser.add_argument(
        "--discover-scenes",
        action="store_true",
        help="发现新场景类型（与--scan配合使用）",
    )

    args = parser.parse_args()

    manager = IncrementalSyncManager()

    if args.scan:
        result = manager.scan_new_novels()
        print(f"\n发现 {len(result['new'])} 本新小说")
        print(f"发现 {len(result['modified'])} 本修改的小说")

        # 新增：场景发现功能
        if args.discover_scenes and (result["new"] or result["modified"]):
            print("\n" + "=" * 60)
            print("场景发现")
            print("=" * 60)
            _run_scene_discovery(result["new"] + result["modified"])

    elif args.process:
        manager.process_new_novels(
            dimension_id=args.dimension, priority=args.priority, limit=args.limit
        )

    elif args.status:
        status = manager.get_status()
        print("\n[增量同步状态]")
        print("-" * 50)
        print(f"总小说数: {status['total_novels']}")
        print(f"已处理: {status['processed']}")
        print(f"待处理: {status['pending']}")
        print(f"\n按格式:")
        for fmt, count in status["by_format"].items():
            print(f"  {fmt}: {count}")
        print(f"\n各维度进度:")
        for dim_id, progress in status["dimension_progress"].items():
            dim_name = EXTRACTION_DIMENSIONS[dim_id].name
            print(
                f"  {dim_name}: {progress['processed']}/{progress['total']} ({progress['percentage']}%)"
            )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()


def _run_scene_discovery(novel_paths: List[Path]):
    """
    运行场景发现器

    Args:
        novel_paths: 新增/修改的小说路径列表
    """
    try:
        # 导入场景发现器
        sys.path.insert(0, str(PROJECT_DIR / "tools"))
        from scene_discoverer import SceneDiscoverer

        discoverer = SceneDiscoverer()

        print(f"分析 {len(novel_paths)} 本小说...")

        import re

        total_unclassified = 0

        for novel_path in novel_paths:
            try:
                from base_extractor import BaseExtractor
                content = BaseExtractor._read_txt_smart(novel_path) or ""
                paragraphs = re.split(r"\n\s*\n", content)
                paragraphs = [
                    p.strip() for p in paragraphs if 100 <= len(p.strip()) <= 5000
                ]

                unclassified = discoverer.collect_unclassified(
                    paragraphs, novel_path.stem
                )
                total_unclassified += len(unclassified)

                if total_unclassified % 100 == 0:
                    print(f"  已收集 {total_unclassified} 个未归类片段")
            except Exception as e:
                print(f"  [WARN] 读取 {novel_path.name} 失败: {e}")

        print(f"\n总计收集 {total_unclassified} 个未归类片段")

        # 发现新场景
        discovered = discoverer.discover_scenes()

        if discovered:
            discoverer.save_discovered()
            print("\n发现的潜在新场景类型:")
            for scene in discovered:
                print(
                    f"  - {scene.name} (样本: {scene.sample_count}, 置信度: {scene.confidence:.0%})"
                )
            print("\n使用以下命令审批和应用:")
            print("  python tools/scene_discoverer.py --list")
            print('  python tools/scene_discoverer.py --approve "场景名称"')
            print("  python tools/scene_discoverer.py --apply-all --sync-qdrant")
        else:
            print("\n未发现新的场景类型（样本不足或置信度过低）")

    except ImportError:
        print("[WARN] scene_discoverer 模块未找到")
    except Exception as e:
        print(f"[ERROR] 场景发现失败: {e}")
