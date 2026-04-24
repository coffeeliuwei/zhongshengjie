"""
小说提炼系统 - 主入口

使用方法:
    # 提炼所有维度
    python run_extractor.py --all

    # 只提炼高价值维度
    python run_extractor.py --priority high

    # 提炼特定维度
    python run_extractor.py --dimension dialogue_style

    # 查看系统状态
    python run_extractor.py --status

    # 继续上次中断的提炼
    python run_extractor.py --all --resume
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    init_extractor,
    EXTRACTION_DIMENSIONS,
    Priority,
    get_output_path,
    get_progress_path,
)
from base_extractor import BatchExtractor

# 高价值提取器
from dialogue_style_extractor import DialogueStyleExtractor
from power_cost_extractor import PowerCostExtractor

# 中价值提取器
from emotion_arc_extractor import EmotionArcExtractor
from vocabulary_extractor import VocabularyExtractor

# 低价值提取器
from author_style_extractor import AuthorStyleExtractor
from foreshadow_pair_extractor import ForeshadowPairExtractor


def print_banner():
    """打印横幅"""
    # 动态获取小说资源目录
    try:
        from config import NOVEL_SOURCE_DIR

        source_dir = str(NOVEL_SOURCE_DIR)
    except Exception:
        source_dir = "配置文件中指定的目录"

    print(f"""
================================================================
         众生界 - 小说提炼系统 v1.0
================================================================

数据源: {source_dir}
输出目录: D:\动画\众生界\.novel-extractor\extracted\

提炼维度:
  高价值:
    - dialogue_style   势力对话风格库
    - power_cost       力量体系代价库
    - character_relation 人物关系图谱
  
  中价值:
    - emotion_arc      情感曲线模板
    - power_vocabulary 力量体系词汇库
    - chapter_structure 章节结构模式
  
  低价值:
    - author_style     作者风格指纹
    - foreshadow_pair  伏笔回收配对
    - worldview_element 世界观元素

================================================================
""")


def print_status():
    """打印系统状态"""
    print("\n[系统状态]")
    print("-" * 60)

    for dim_id, dim_config in EXTRACTION_DIMENSIONS.items():
        progress_path = get_progress_path(dim_id)

        if progress_path.exists():
            with open(progress_path, "r", encoding="utf-8") as f:
                progress = json.load(f)

            status = progress.get("status", "unknown")
            processed = progress.get("processed_novels", 0)
            total = progress.get("total_novels", 0)
            items = progress.get("extracted_items", 0)

            status_icon = {
                "completed": "[OK]",
                "running": "[..]",
                "pending": "[  ]",
                "failed": "[X]",
            }.get(status, "[?]")

            priority_icon = {
                Priority.HIGH: "*",
                Priority.MEDIUM: "+",
                Priority.LOW: "-",
            }.get(dim_config.priority, " ")

            print(f"{status_icon} {priority_icon} {dim_config.name}")
            print(f"     小说: {processed}/{total} | 条目: {items}")
        else:
            priority_icon = {
                Priority.HIGH: "*",
                Priority.MEDIUM: "+",
                Priority.LOW: "-",
            }.get(dim_config.priority, " ")

            print(f"[  ] {priority_icon} {dim_config.name}")
            print(f"     未开始")

    print("-" * 60)
    print("优先级: *=高 +=中 -=低")
    print()


def create_batch_extractor() -> BatchExtractor:
    """创建批量提取器并注册所有提取器"""
    batch = BatchExtractor()

    # 注册高价值提取器
    batch.register(DialogueStyleExtractor())
    batch.register(PowerCostExtractor())

    # 注册中价值提取器
    batch.register(EmotionArcExtractor())
    batch.register(VocabularyExtractor())

    # 注册低价值提取器
    batch.register(AuthorStyleExtractor())
    batch.register(ForeshadowPairExtractor())

    return batch


def run_extraction(
    priority: Optional[str] = None,
    dimension: Optional[str] = None,
    limit: Optional[int] = None,
    resume: bool = True,
):
    """运行提炼"""

    init_extractor()

    batch = create_batch_extractor()

    # 确定要运行的维度
    priorities = None
    if priority:
        priority_map = {
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW,
        }
        priorities = [priority_map.get(priority.lower())]

    if dimension:
        # 只运行指定维度
        if dimension not in EXTRACTION_DIMENSIONS:
            print(f"[ERROR] Unknown dimension: {dimension}")
            print(f"Available: {list(EXTRACTION_DIMENSIONS.keys())}")
            return

        extractor = batch.extractors.get(dimension)
        if not extractor:
            print(f"[ERROR] No extractor registered for {dimension}")
            return

        extractor.run(limit=limit, resume=resume)
    else:
        # 运行批量提取
        results = batch.run_all(priorities=priorities, limit=limit)

        # 打印汇总
        print("\n" + "=" * 60)
        print("提炼完成汇总")
        print("=" * 60)

        for dim_id, result in results.items():
            status = result.get("status", "unknown")
            novels = result.get("novels_processed", 0)
            items = result.get("items_extracted", 0)
            print(f"  {dim_id}: {status} | {novels} novels | {items} items")


def generate_report():
    """生成提炼报告"""
    report_path = Path(__file__).parent / "extraction_report.md"

    # 动态获取小说资源目录
    try:
        from config import NOVEL_SOURCE_DIR

        source_dir = str(NOVEL_SOURCE_DIR)
    except Exception:
        source_dir = "配置文件中指定的目录"

    report_lines = [
        "# 小说提炼报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 数据源",
        "",
        f"- 原始小说库: `{source_dir}`",
        "- 提炼输出: `D:\\动画\\众生界\\.novel-extractor\\extracted\\`",
        "",
        "## 提炼维度",
        "",
    ]

    for priority in [Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
        priority_name = {
            Priority.HIGH: "高价值",
            Priority.MEDIUM: "中价值",
            Priority.LOW: "低价值",
        }.get(priority)

        report_lines.append(f"### {priority_name}")
        report_lines.append("")
        report_lines.append("| 维度 | 状态 | 小说数 | 条目数 |")
        report_lines.append("|------|------|--------|--------|")

        for dim_id, dim_config in EXTRACTION_DIMENSIONS.items():
            if dim_config.priority != priority:
                continue

            progress_path = get_progress_path(dim_id)
            if progress_path.exists():
                with open(progress_path, "r", encoding="utf-8") as f:
                    progress = json.load(f)
                status = progress.get("status", "unknown")
                novels = progress.get("processed_novels", 0)
                items = progress.get("extracted_items", 0)
            else:
                status = "未开始"
                novels = 0
                items = 0

            report_lines.append(
                f"| {dim_config.name} | {status} | {novels} | {items} |"
            )

        report_lines.append("")

    # 写入文件
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"[OK] 报告已生成: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="众生界小说提炼系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_extractor.py --all                    # 提炼所有维度
  python run_extractor.py --priority high           # 只提炼高价值
  python run_extractor.py --dimension dialogue_style # 提炼特定维度
  python run_extractor.py --status                  # 查看状态
  python run_extractor.py --report                  # 生成报告
  python run_extractor.py --all --limit 10          # 测试模式（每维度10本小说）
        """,
    )

    parser.add_argument("--all", action="store_true", help="提炼所有维度")
    parser.add_argument(
        "--priority", choices=["high", "medium", "low"], help="按优先级提炼"
    )
    parser.add_argument("--dimension", type=str, help="提炼特定维度")
    parser.add_argument("--limit", type=int, help="限制每个维度处理的小说数量")
    parser.add_argument("--status", action="store_true", help="查看系统状态")
    parser.add_argument("--report", action="store_true", help="生成提炼报告")
    parser.add_argument("--no-resume", action="store_true", help="从头开始，不续接")

    args = parser.parse_args()

    print_banner()

    if args.status:
        print_status()
    elif args.report:
        generate_report()
    elif args.all or args.priority or args.dimension:
        run_extraction(
            priority=args.priority,
            dimension=args.dimension,
            limit=args.limit,
            resume=not args.no_resume,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
