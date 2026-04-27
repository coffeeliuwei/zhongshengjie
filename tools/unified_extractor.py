#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一提炼引擎（UnifiedExtractor）
================================

单一入口的统一提炼引擎，支持：
1. 11维度并行提取
2. 统一进度追踪
3. 场景自动发现
4. 统一入库Qdrant

使用方法：
    # 默认增量提炼
    python tools/unified_extractor.py

    # 强制全量提炼
    python tools/unified_extractor.py --force

    # 查看状态
    python tools/unified_extractor.py --status

    # 只提炼特定维度
    python tools/unified_extractor.py --dimensions case,technique

    # 并行数控制
    python tools/unified_extractor.py --workers 4
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import traceback

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入配置加载器
try:
    from core.config_loader import (
        get_config,
        get_project_root,
        get_qdrant_url,
        get_novel_sources,
        get_novel_extractor_dir,
        get_vectorstore_dir,
    )

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False

# 从配置加载路径
if HAS_CONFIG_LOADER:
    sys.path.insert(0, str(get_novel_extractor_dir()))
else:
    sys.path.insert(0, str(PROJECT_ROOT / ".novel-extractor"))

try:
    from config import (
        EXTRACTION_DIMENSIONS,
        DimensionCategory,
        init_system,
        get_output_path,
        get_progress_path,
        NOVEL_SOURCE_DIR,
        CASE_OUTPUT_DIR,
        EXTENDED_OUTPUT_DIR,
    )

    HAS_UNIFIED_CONFIG = True
except ImportError:
    HAS_UNIFIED_CONFIG = False

try:
    from incremental_sync import IncrementalSyncManager

    HAS_INCREMENTAL_SYNC = True
except ImportError:
    HAS_INCREMENTAL_SYNC = False

try:
    from tools.scene_discoverer import SceneDiscoverer

    HAS_SCENE_DISCOVERER = True
except ImportError:
    HAS_SCENE_DISCOVERER = False


# ==================== 维度定义 ====================

# 维度到Collection的映射
DIMENSION_COLLECTION_MAP = {
    "case": "case_library_v2",
    "technique": "writing_techniques_v2",
    "dialogue_style": "dialogue_style_v1",
    "power_cost": "power_cost_v1",
    "emotion_arc": "emotion_arc_v1",
    "power_vocabulary": "power_vocabulary_v1",
    "character_relation": "novel_settings_v2",
    "chapter_structure": None,  # 不入库
    "author_style": None,  # 不入库
    "foreshadow_pair": "foreshadow_pair_v1",
    "worldview_element": "novel_settings_v2",
}

# 维度优先级（用于并行提取的调度顺序）
DIMENSION_PRIORITY = {
    "case": 1,  # 最高优先级
    "technique": 2,
    "dialogue_style": 3,
    "power_cost": 3,
    "character_relation": 3,
    "emotion_arc": 4,
    "power_vocabulary": 4,
    "chapter_structure": 5,
    "author_style": 5,
    "foreshadow_pair": 5,
    "worldview_element": 5,
}


# ==================== 数据类定义 ====================


@dataclass
class ExtractionTask:
    """提取任务"""

    dimension_id: str
    status: str = "pending"  # pending, running, completed, failed, skipped
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    items_extracted: int = 0
    novels_processed: int = 0
    error: Optional[str] = None


@dataclass
class UnifiedProgress:
    """统一进度"""

    started_at: str = ""
    finished_at: str = ""
    status: str = "idle"  # idle, running, completed, partial, failed
    force_mode: bool = False
    dimensions: Dict[str, ExtractionTask] = field(default_factory=dict)
    novels_scanned: int = 0
    novels_new: int = 0
    novels_modified: int = 0
    total_items_extracted: int = 0
    scene_discovery_count: int = 0

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "force_mode": self.force_mode,
            "dimensions": {k: asdict(v) for k, v in self.dimensions.items()},
            "novels_scanned": self.novels_scanned,
            "novels_new": self.novels_new,
            "novels_modified": self.novels_modified,
            "total_items_extracted": self.total_items_extracted,
            "scene_discovery_count": self.scene_discovery_count,
        }


# ==================== 统一提炼引擎 ====================


class UnifiedExtractor:
    """
    统一提炼引擎

    单一入口启动所有提取，支持：
    - 11维度并行提取
    - 统一进度追踪
    - 场景自动发现
    - 统一入库Qdrant
    """

    def __init__(self, config: Optional[Dict] = None):
        """初始化统一提炼引擎"""
        self.config = config or {}
        self.project_root = PROJECT_ROOT

        # 从配置加载路径
        if HAS_CONFIG_LOADER:
            self.progress_file = get_novel_extractor_dir() / "unified_progress.json"
        else:
            self.progress_file = (
                self.project_root / ".novel-extractor" / "unified_progress.json"
            )

        self.progress = self._load_progress()
        self._lock = Lock()

        # 初始化子模块
        self._init_submodules()

    def _init_submodules(self):
        """初始化子模块"""
        # 增量同步管理器
        if HAS_INCREMENTAL_SYNC:
            try:
                self.sync_manager = IncrementalSyncManager()
            except Exception as e:
                print(f"[WARN] 无法初始化增量同步管理器: {e}")
                self.sync_manager = None
        else:
            self.sync_manager = None

        # 场景发现器
        if HAS_SCENE_DISCOVERER:
            try:
                self.scene_discoverer = SceneDiscoverer()
            except Exception as e:
                print(f"[WARN] 无法初始化场景发现器: {e}")
                self.scene_discoverer = None
        else:
            self.scene_discoverer = None

    def _load_progress(self) -> UnifiedProgress:
        """加载统一进度"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                progress = UnifiedProgress()
                progress.started_at = data.get("started_at", "")
                progress.finished_at = data.get("finished_at", "")
                progress.status = data.get("status", "idle")
                progress.force_mode = data.get("force_mode", False)
                progress.novels_scanned = data.get("novels_scanned", 0)
                progress.novels_new = data.get("novels_new", 0)
                progress.novels_modified = data.get("novels_modified", 0)
                progress.total_items_extracted = data.get("total_items_extracted", 0)
                progress.scene_discovery_count = data.get("scene_discovery_count", 0)

                for dim_id, task_data in data.get("dimensions", {}).items():
                    progress.dimensions[dim_id] = ExtractionTask(
                        dimension_id=dim_id,
                        status=task_data.get("status", "pending"),
                        start_time=task_data.get("start_time"),
                        end_time=task_data.get("end_time"),
                        items_extracted=task_data.get("items_extracted", 0),
                        novels_processed=task_data.get("novels_processed", 0),
                        error=task_data.get("error"),
                    )
                return progress
            except Exception as e:
                print(f"[WARN] 无法加载进度文件: {e}")

        return UnifiedProgress()

    def _save_progress(self):
        """保存统一进度"""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(self.progress.to_dict(), f, ensure_ascii=False, indent=2)

    def _create_extractor(self, dimension_id: str):
        """创建提取器实例"""
        extractors_map = {
            "case": ("extractors.case_extractor", "CaseExtractor"),
            "dialogue_style": (
                "extractors.dialogue_style_extractor",
                "DialogueStyleExtractor",
            ),
            "power_cost": ("extractors.power_cost_extractor", "PowerCostExtractor"),
            "character_relation": (
                "extractors.character_relation_extractor",
                "CharacterRelationExtractor",
            ),
            "emotion_arc": ("extractors.emotion_arc_extractor", "EmotionArcExtractor"),
            "power_vocabulary": (
                "extractors.vocabulary_extractor",
                "VocabularyExtractor",
            ),
            "chapter_structure": (
                "extractors.chapter_structure_extractor",
                "ChapterStructureExtractor",
            ),
            "author_style": (
                "extractors.author_style_extractor",
                "AuthorStyleExtractor",
            ),
            "foreshadow_pair": (
                "extractors.foreshadow_pair_extractor",
                "ForeshadowPairExtractor",
            ),
            "worldview_element": (
                "extractors.worldview_element_extractor",
                "WorldviewElementExtractor",
            ),
            "technique": ("extractors.technique_extractor", "TechniqueExtractor"),
        }

        if dimension_id not in extractors_map:
            return None

        module_name, class_name = extractors_map[dimension_id]
        try:
            module = __import__(module_name, fromlist=[class_name])
            return getattr(module, class_name)()
        except Exception as e:
            print(f"[ERROR] 无法创建提取器 {dimension_id}: {e}")
            return None

    def extract(
        self,
        dimensions: Optional[List[str]] = None,
        force: bool = False,
        workers: int = 4,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        单一入口启动所有提取

        Args:
            dimensions: 要提取的维度列表，None表示所有维度
            force: 是否强制全量重新提取
            workers: 并行工作线程数
            limit: 每个维度处理的小说数量限制

        Returns:
            提取结果统计
        """
        print("\n" + "=" * 60)
        print("  统一提炼引擎 - UnifiedExtractor")
        print("=" * 60)
        print(f"模式: {'全量强制' if force else '增量同步'}")
        print(f"并行数: {workers}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # 初始化进度
        self.progress.started_at = datetime.now().isoformat()
        self.progress.status = "running"
        self.progress.force_mode = force
        self._save_progress()

        # 1. 增量同步：检测新小说
        print("\n[1/4] 增量同步 - 检测新小说...")
        new_novels = []
        if self.sync_manager and not force:
            scan_result = self.sync_manager.scan_new_novels()
            new_novels = scan_result.get("new", [])
            modified_novels = scan_result.get("modified", [])
            self.progress.novels_scanned = scan_result.get("existing", 0)
            self.progress.novels_new = len(new_novels)
            self.progress.novels_modified = len(modified_novels)
            print(f"  新增小说: {len(new_novels)}")
            print(f"  修改小说: {len(modified_novels)}")
        elif force:
            print("  全量模式：将处理所有小说")

        # 2. 确定要提取的维度
        if dimensions:
            dimensions_to_run = [d for d in dimensions if d in EXTRACTION_DIMENSIONS]
        else:
            dimensions_to_run = list(EXTRACTION_DIMENSIONS.keys())

        print(f"\n[2/4] 准备提取 - {len(dimensions_to_run)} 个维度")
        for dim_id in dimensions_to_run:
            dim = EXTRACTION_DIMENSIONS.get(dim_id)
            if dim:
                self.progress.dimensions[dim_id] = ExtractionTask(dimension_id=dim_id)
                print(f"  - {dim.name} ({dim.category.value})")
        self._save_progress()

        # 3. 并行提取
        print(f"\n[3/4] 并行提取 - 启动 {workers} 个工作线程...")
        extraction_results = self._run_parallel_extraction(
            dimensions_to_run,
            workers=workers,
            force=force,
            limit=limit,
        )

        # 4. 场景发现
        print("\n[4/4] 场景发现 - 自动发现新场景类型...")
        if self.scene_discoverer and "case" in dimensions_to_run:
            discovered = self._run_scene_discovery()
            self.progress.scene_discovery_count = len(discovered)
        else:
            self.progress.scene_discovery_count = 0

        # 5. 统一入库
        print("\n[5/5] 统一入库 - 同步到Qdrant...")
        sync_results = self._sync_to_qdrant(dimensions_to_run)

        # 更新最终状态
        self.progress.finished_at = datetime.now().isoformat()
        self.progress.status = self._determine_final_status(extraction_results)
        self._save_progress()

        # 打印汇总
        self._print_summary(extraction_results, sync_results)

        return {
            "status": self.progress.status,
            "dimensions": len(dimensions_to_run),
            "dimensions_completed": sum(
                1 for r in extraction_results.values() if r.get("status") == "completed"
            ),
            "total_items": self.progress.total_items_extracted,
            "new_novels": self.progress.novels_new,
            "discovered_scenes": self.progress.scene_discovery_count,
            "duration": self._calculate_duration(),
        }

    def _run_parallel_extraction(
        self,
        dimensions: List[str],
        workers: int,
        force: bool,
        limit: Optional[int],
    ) -> Dict[str, Dict]:
        """并行执行多个维度的提取"""
        results = {}

        # 按优先级排序
        sorted_dimensions = sorted(
            dimensions, key=lambda d: DIMENSION_PRIORITY.get(d, 99)
        )

        # 创建线程池
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # 提交任务
            future_to_dim = {}
            for dim_id in sorted_dimensions:
                # 更新任务状态
                with self._lock:
                    if dim_id in self.progress.dimensions:
                        self.progress.dimensions[dim_id].status = "running"
                        self.progress.dimensions[
                            dim_id
                        ].start_time = datetime.now().isoformat()

                # 提交提取任务
                future = executor.submit(
                    self.extract_dimension,
                    dim_id,
                    force=force,
                    limit=limit,
                )
                future_to_dim[future] = dim_id

            # 收集结果
            for future in as_completed(future_to_dim):
                dim_id = future_to_dim[future]
                try:
                    result = future.result()
                    results[dim_id] = result

                    # 更新进度
                    with self._lock:
                        if dim_id in self.progress.dimensions:
                            self.progress.dimensions[dim_id].status = result.get(
                                "status", "completed"
                            )
                            self.progress.dimensions[
                                dim_id
                            ].end_time = datetime.now().isoformat()
                            self.progress.dimensions[
                                dim_id
                            ].items_extracted = result.get("items_extracted", 0)
                            self.progress.dimensions[
                                dim_id
                            ].novels_processed = result.get("novels_processed", 0)
                            if result.get("error"):
                                self.progress.dimensions[dim_id].error = result.get(
                                    "error"
                                )

                        self.progress.total_items_extracted += result.get(
                            "items_extracted", 0
                        )

                    self._save_progress()
                    print(f"  [完成] {dim_id}: {result.get('items_extracted', 0)} 条")

                except Exception as e:
                    error_msg = str(e)
                    results[dim_id] = {
                        "status": "failed",
                        "error": error_msg,
                    }

                    with self._lock:
                        if dim_id in self.progress.dimensions:
                            self.progress.dimensions[dim_id].status = "failed"
                            self.progress.dimensions[dim_id].error = error_msg
                            self.progress.dimensions[
                                dim_id
                            ].end_time = datetime.now().isoformat()
                    self._save_progress()
                    print(f"  [失败] {dim_id}: {error_msg}")

        return results

    def extract_dimension(
        self,
        dimension_id: str,
        force: bool = False,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        单个维度提取

        Args:
            dimension_id: 维度ID
            force: 是否强制重新提取
            limit: 处理小说数量限制

        Returns:
            提取结果
        """
        # 获取维度配置
        dim_config = EXTRACTION_DIMENSIONS.get(dimension_id)
        if not dim_config:
            return {
                "status": "failed",
                "error": f"未知维度: {dimension_id}",
            }

        # 创建提取器
        extractor = self._create_extractor(dimension_id)
        if not extractor:
            return {
                "status": "skipped",
                "error": f"无法创建提取器: {dimension_id}",
            }

        # 如果强制模式，清除进度
        if force:
            progress_path = get_progress_path(dimension_id)
            if progress_path.exists():
                progress_path.unlink()

        # 运行提取
        try:
            result = extractor.run(limit=limit, resume=not force)
            return {
                "status": "completed",
                "dimension_id": dimension_id,
                "items_extracted": result.get("items_extracted", 0),
                "novels_processed": result.get("novels_processed", 0),
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "dimension_id": dimension_id,
            }

    def _run_scene_discovery(self) -> List:
        """运行场景发现"""
        if not self.scene_discoverer:
            return []

        try:
            # 加载已发现的场景
            discovered = self.scene_discoverer.load_discovered()

            # 发现新场景
            if not discovered:
                discovered = self.scene_discoverer.discover_scenes()

            if discovered:
                print(f"  发现 {len(discovered)} 个新场景类型")
                for scene in discovered[:5]:
                    print(f"    - {scene.name} (样本: {scene.sample_count})")
            else:
                print("  未发现新的场景类型")

            return discovered
        except Exception as e:
            print(f"  [WARN] 场景发现失败: {e}")
            return []

    def _sync_to_qdrant(self, dimensions: List[str]) -> Dict[str, Any]:
        """同步到Qdrant向量数据库"""
        results = {}

        for dim_id in dimensions:
            collection = DIMENSION_COLLECTION_MAP.get(dim_id)
            if not collection:
                continue

            # 检查是否有数据需要同步
            output_dir = get_output_path(dim_id)
            if not output_dir.exists():
                continue

            # 查找输出文件
            output_file = output_dir / f"{dim_id}_all.json"
            if not output_file.exists():
                output_file = output_dir / f"{dim_id}_items.jsonl"

            if output_file.exists():
                results[dim_id] = {
                    "collection": collection,
                    "status": "pending",
                    "file": str(output_file),
                }
                print(f"  {dim_id} -> {collection}: 待同步")
            else:
                results[dim_id] = {
                    "collection": collection,
                    "status": "no_data",
                }

        # 实际同步需要调用迁移脚本
        if results:
            print("\n  提示：运行以下命令同步到Qdrant:")
            print("    python tools/migrate_lite_resumable.py --collection case")
            print("    python tools/migrate_lite_resumable.py --collection technique")

        return results

    def _determine_final_status(self, results: Dict[str, Dict]) -> str:
        """确定最终状态"""
        if not results:
            return "failed"

        statuses = [r.get("status") for r in results.values()]

        if all(s == "completed" for s in statuses):
            return "completed"
        elif any(s == "completed" for s in statuses):
            return "partial"
        else:
            return "failed"

    def _calculate_duration(self) -> str:
        """计算执行时长"""
        if not self.progress.started_at or not self.progress.finished_at:
            return "unknown"

        try:
            start = datetime.fromisoformat(self.progress.started_at)
            end = datetime.fromisoformat(self.progress.finished_at)
            duration = end - start

            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            seconds = duration.seconds % 60

            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        except:
            return "unknown"

    def _print_summary(self, extraction_results: Dict, sync_results: Dict):
        """打印汇总"""
        print("\n" + "=" * 60)
        print("  提炼完成汇总")
        print("=" * 60)

        # 维度统计
        completed = sum(
            1 for r in extraction_results.values() if r.get("status") == "completed"
        )
        failed = sum(
            1 for r in extraction_results.values() if r.get("status") == "failed"
        )
        skipped = sum(
            1 for r in extraction_results.values() if r.get("status") == "skipped"
        )

        print(f"\n维度统计:")
        print(f"  完成: {completed}")
        print(f"  失败: {failed}")
        print(f"  跳过: {skipped}")

        # 数据统计
        print(f"\n数据统计:")
        print(f"  新增小说: {self.progress.novels_new}")
        print(f"  修改小说: {self.progress.novels_modified}")
        print(f"  提取条目: {self.progress.total_items_extracted}")
        print(f"  发现场景: {self.progress.scene_discovery_count}")

        # 执行时长
        print(f"\n执行时长: {self._calculate_duration()}")

        # 状态
        print(f"\n最终状态: {self.progress.status}")
        print("=" * 60)

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        status = {
            "progress": self.progress.to_dict(),
            "dimensions": {},
            "sync_status": {},
        }

        # 获取各维度状态
        for dim_id, dim_config in EXTRACTION_DIMENSIONS.items():
            progress_path = get_progress_path(dim_id)
            if progress_path.exists():
                try:
                    with open(progress_path, "r", encoding="utf-8") as f:
                        dim_progress = json.load(f)
                    status["dimensions"][dim_id] = {
                        "name": dim_config.name,
                        "category": dim_config.category.value,
                        "status": dim_progress.get("status", "unknown"),
                        "items": dim_progress.get("extracted_items", 0),
                        "novels": dim_progress.get("processed_novels", 0),
                    }
                except:
                    status["dimensions"][dim_id] = {
                        "name": dim_config.name,
                        "status": "error",
                    }
            else:
                status["dimensions"][dim_id] = {
                    "name": dim_config.name,
                    "status": "not_started",
                    "items": 0,
                    "novels": 0,
                }

        # 增量同步状态
        if self.sync_manager:
            status["sync_status"] = self.sync_manager.get_status()

        return status

    def print_status(self):
        """打印当前状态"""
        print("\n" + "=" * 60)
        print("  统一提炼引擎状态")
        print("=" * 60)

        # 上次运行状态
        if self.progress.started_at:
            print(f"\n上次运行:")
            print(f"  开始时间: {self.progress.started_at}")
            print(f"  结束时间: {self.progress.finished_at or '进行中'}")
            print(f"  状态: {self.progress.status}")
            print(f"  模式: {'全量强制' if self.progress.force_mode else '增量同步'}")

        # 各维度状态
        print(f"\n维度状态:")
        categories = {
            DimensionCategory.CORE: "核心",
            DimensionCategory.HIGH: "高价值",
            DimensionCategory.MEDIUM: "中价值",
            DimensionCategory.LOW: "低价值",
        }

        for category, cat_name in categories.items():
            print(f"\n  [{cat_name}]")
            for dim_id, dim_config in EXTRACTION_DIMENSIONS.items():
                if dim_config.category != category:
                    continue

                task = self.progress.dimensions.get(dim_id)
                if task:
                    status_icon = {
                        "completed": "✓",
                        "running": "⋯",
                        "pending": "○",
                        "failed": "✗",
                        "skipped": "—",
                    }.get(task.status, "?")
                    print(
                        f"    {status_icon} {dim_config.name}: {task.items_extracted} 条"
                    )
                else:
                    print(f"    ○ {dim_config.name}: 未开始")

        # 增量同步状态
        if self.sync_manager:
            sync_status = self.sync_manager.get_status()
            print(f"\n增量同步:")
            print(f"  总小说数: {sync_status.get('total_novels', 0)}")
            print(f"  已处理: {sync_status.get('processed', 0)}")
            print(f"  待处理: {sync_status.get('pending', 0)}")

        print("=" * 60)


# ==================== 命令行接口 ====================


def main():
    parser = argparse.ArgumentParser(
        description="统一提炼引擎 - 单一入口启动所有维度提取",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 默认增量提炼
  python tools/unified_extractor.py

  # 强制全量提炼
  python tools/unified_extractor.py --force

  # 查看状态
  python tools/unified_extractor.py --status

  # 只提炼特定维度
  python tools/unified_extractor.py --dimensions case,technique

  # 控制并行数
  python tools/unified_extractor.py --workers 8
        """,
    )

    parser.add_argument(
        "--force", action="store_true", help="强制全量重新提炼（忽略已有进度）"
    )
    parser.add_argument("--status", action="store_true", help="查看当前状态")
    parser.add_argument(
        "--dimensions", type=str, help="只提炼特定维度（逗号分隔，如: case,technique）"
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="并行工作线程数（默认4）"
    )
    parser.add_argument(
        "--limit", type=int, help="每个维度处理的小说数量限制（用于测试）"
    )
    parser.add_argument("--list-scenes", action="store_true", help="列出新发现的场景")
    parser.add_argument("--approve-scene", type=str, help="批准指定场景")
    parser.add_argument(
        "--apply-scenes", action="store_true", help="应用所有已批准的场景"
    )

    args = parser.parse_args()

    # 创建统一提炼引擎
    extractor = UnifiedExtractor()

    # 初始化系统
    if HAS_UNIFIED_CONFIG:
        init_system()

    if args.status:
        extractor.print_status()

    elif args.list_scenes:
        if extractor.scene_discoverer:
            extractor.scene_discoverer.load_discovered()
            scenes = extractor.scene_discoverer.discovered_scenes
            if scenes:
                print("\n发现的场景:")
                for scene in scenes:
                    status_icon = {
                        "pending": "⏳",
                        "approved": "✅",
                        "rejected": "❌",
                    }.get(scene.status, "?")
                    print(f"  {status_icon} {scene.name}")
                    print(f"      样本数: {scene.sample_count}")
                    print(f"      置信度: {scene.confidence:.0%}")
            else:
                print("\n未发现新场景")
        else:
            print("[ERROR] 场景发现器不可用")

    elif args.approve_scene:
        if extractor.scene_discoverer:
            extractor.scene_discoverer.load_discovered()
            extractor.scene_discoverer.approve_scene(args.approve_scene)
        else:
            print("[ERROR] 场景发现器不可用")

    elif args.apply_scenes:
        if extractor.scene_discoverer:
            extractor.scene_discoverer.load_discovered()
            approved = [
                s
                for s in extractor.scene_discoverer.discovered_scenes
                if s.status == "approved"
            ]
            if approved:
                extractor.scene_discoverer.sync_all(approved)
            else:
                print("没有已批准的场景需要应用")
        else:
            print("[ERROR] 场景发现器不可用")

    else:
        # 解析维度列表
        dimensions = None
        if args.dimensions:
            dimensions = [d.strip() for d in args.dimensions.split(",")]

        # 执行提取
        result = extractor.extract(
            dimensions=dimensions,
            force=args.force,
            workers=args.workers,
            limit=args.limit,
        )

        print(f"\n最终结果: {result}")


if __name__ == "__main__":
    main()
