"""
众生界 - 完整小说提炼系统 v2.0

统一入口，整合所有提炼维度：
1. 核心维度 - 场景案例提取（22种场景）
2. 扩展维度 - 高中低价值提炼（6种）

使用方法:
    # 查看系统状态
    python run.py --status

    # 提炼所有维度
    python run.py --all

    # 按类别提炼
    python run.py --category core     # 只提炼核心（场景案例）
    python run.py --category high     # 只提炼高价值

    # 提炼特定维度
    python run.py --dimension case
    python run.py --dimension dialogue_style

    # 增量同步
    python run.py --sync

    # 生成报告
    python run.py --report
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from unified_config import (
    init_system,
    EXTRACTION_DIMENSIONS,
    DimensionCategory,
    get_output_path,
    get_progress_path,
    NOVEL_SOURCE_DIR,
)


def create_extractor(dim_id: str):
    """创建提取器实例（延迟导入避免循环依赖）"""
    extractors = {
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
        "power_vocabulary": ("extractors.vocabulary_extractor", "VocabularyExtractor"),
        "chapter_structure": (
            "extractors.chapter_structure_extractor",
            "ChapterStructureExtractor",
        ),
        "author_style": ("extractors.author_style_extractor", "AuthorStyleExtractor"),
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

    if dim_id not in extractors:
        return None

    module_name, class_name = extractors[dim_id]
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)()


def print_banner():
    """打印横幅"""
    # 动态获取小说资源目录
    try:
        from unified_config import NOVEL_SOURCE_DIR

        source_dir = str(NOVEL_SOURCE_DIR)
    except Exception:
        source_dir = "配置文件中指定的目录"

    print(f"""
================================================================
       众生界 - 完整小说提炼系统 v2.0
================================================================

数据源: {source_dir}

提炼维度:
  [核心] 场景案例库 - 22种场景类型标杆案例
  
  [高价值]
    - 势力对话风格库 - 10大势力对话特征
    - 力量体系代价库 - 7大力量代价表现
    - 人物关系图谱 - 人物共现关系网络
  
  [中价值]
    - 情感曲线模板 - 6种叙事弧线
    - 力量体系词汇库 - 境界/功法/物品词汇
    - 章节结构模式 - 章节节奏分析
  
  [低价值]
    - 作者风格指纹 - 风格特征向量
    - 伏笔回收配对 - 伏笔配对示例

================================================================
""")


def print_status():
    """打印系统状态"""
    print("\n[系统状态]")
    print("-" * 60)

    # 按类别分组显示
    categories = {
        DimensionCategory.CORE: "核心",
        DimensionCategory.HIGH: "高价值",
        DimensionCategory.MEDIUM: "中价值",
        DimensionCategory.LOW: "低价值",
    }

    for category, cat_name in categories.items():
        print(f"\n[{cat_name}]")

        for dim_id, dim in EXTRACTION_DIMENSIONS.items():
            if dim.category != category:
                continue

            # 获取进度
            progress_path = get_progress_path(dim_id)
            if progress_path.exists():
                with open(progress_path, "r", encoding="utf-8") as f:
                    progress = json.load(f)
                status = progress.get("status", "unknown")
                items = progress.get("extracted_items", 0) or progress.get(
                    "total_cases", 0
                )
            else:
                status = "未开始"
                items = 0

            status_icon = {
                "completed": "[OK]",
                "running": "[..]",
                "pending": "[  ]",
                "未开始": "[  ]",
            }.get(status, "[?]")

            print(f"  {status_icon} {dim.name}: {items} 条")

    # 显示案例库统计
    print(f"\n[场景案例库]")
    case_extractor = create_extractor("case")
    if case_extractor:
        stats = case_extractor.get_status()

        by_scene = stats.get("by_scene", {})
        top_scenes = sorted(by_scene.items(), key=lambda x: -x[1])[:5]
        for scene, count in top_scenes:
            if count > 0:
                print(f"  {scene}: {count}")
    else:
        print("  [未加载] 案例提取器")

    print("-" * 60)


def run_extraction(
    dimension: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None,
    resume: bool = True,
):
    """运行提炼"""

    init_system()

    # 确定要运行的维度
    dimensions_to_run = []

    if dimension:
        if dimension not in EXTRACTION_DIMENSIONS:
            print(f"[错误] 未知维度: {dimension}")
            print(f"可用维度: {list(EXTRACTION_DIMENSIONS.keys())}")
            return
        dimensions_to_run = [dimension]
    elif category:
        category_map = {
            "core": DimensionCategory.CORE,
            "high": DimensionCategory.HIGH,
            "medium": DimensionCategory.MEDIUM,
            "low": DimensionCategory.LOW,
        }
        target_category = category_map.get(category.lower())
        if not target_category:
            print(f"[错误] 未知类别: {category}")
            return
        dimensions_to_run = [
            dim_id
            for dim_id, dim in EXTRACTION_DIMENSIONS.items()
            if dim.category == target_category
        ]
    else:
        dimensions_to_run = list(EXTRACTION_DIMENSIONS.keys())

    # 运行提取
    results = {}

    for dim_id in dimensions_to_run:
        dim = EXTRACTION_DIMENSIONS.get(dim_id)
        if not dim or not dim.enabled:
            continue

        print(f"\n{'=' * 60}")
        print(f"[维度] {dim.name}")
        print(f"类别: {dim.category.value}")
        print(f"描述: {dim.description}")
        print(f"{'=' * 60}")

        extractor = create_extractor(dim_id)
        if not extractor:
            print(f"[跳过] 无提取器: {dim_id}")
            continue

        try:
            result = extractor.run(limit=limit, resume=resume)
            results[dim_id] = result
        except Exception as e:
            print(f"[错误] {dim_id}: {e}")
            results[dim_id] = {"status": "failed", "error": str(e)}

    # 打印汇总
    print("\n" + "=" * 60)
    print("提炼完成汇总")
    print("=" * 60)

    for dim_id, result in results.items():
        status = result.get("status", "unknown")
        dim = EXTRACTION_DIMENSIONS.get(dim_id)
        print(f"  {dim.name if dim else dim_id}: {status}")

    return results


def run_sync():
    """运行增量同步"""
    print("\n[增量同步]")
    print("-" * 60)

    # 使用案例库的增量同步
    from incremental_sync import IncrementalSyncManager

    manager = IncrementalSyncManager()

    # 扫描新小说
    scan_result = manager.scan_new_novels()

    if scan_result["new"] or scan_result["modified"]:
        print(f"\n发现 {len(scan_result['new'])} 本新小说")
        print(f"发现 {len(scan_result['modified'])} 本修改的小说")

        # 询问是否处理
        print("\n运行以下命令处理新小说:")
        print("  python run.py --all")
    else:
        print("没有发现新小说")


def generate_report():
    """生成提炼报告"""
    report_path = Path(__file__).parent / "extraction_report.md"

    # 动态获取小说资源目录
    try:
        from unified_config import NOVEL_SOURCE_DIR

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
        "- 案例库: `D:\\动画\\众生界\\.case-library\\cases\\`",
        "- 扩展提炼: `D:\\动画\\众生界\\.novel-extractor\\extracted\\`",
        "",
        "## 核心维度",
        "",
        "场景案例库：22种场景类型标杆案例",
        "",
        "| 场景类型 | 案例数 |",
        "|----------|--------|",
    ]

    categories = {
        DimensionCategory.CORE: ("核心维度", "直接用于创作"),
        DimensionCategory.HIGH: ("高价值", "直接用于创作"),
        DimensionCategory.MEDIUM: ("中价值", "需适配后使用"),
        DimensionCategory.LOW: ("低价值", "长期有益"),
    }

    for category, (cat_name, cat_desc) in categories.items():
        report_lines.append(f"### {cat_name}")
        report_lines.append("")
        report_lines.append(f"*{cat_desc}*")
        report_lines.append("")
        report_lines.append("| 维度 | 说明 | 状态 | 数量 |")
        report_lines.append("|------|------|------|------|")

        for dim_id, dim in EXTRACTION_DIMENSIONS.items():
            if dim.category != category:
                continue

            # 获取进度
            progress_path = get_progress_path(dim_id)
            if progress_path.exists():
                with open(progress_path, "r", encoding="utf-8") as f:
                    progress = json.load(f)
                status = progress.get("status", "unknown")
                items = progress.get("extracted_items", 0) or progress.get(
                    "total_cases", 0
                )
            else:
                status = "未开始"
                items = 0

            report_lines.append(
                f"| {dim.name} | {dim.description[:20]}... | {status} | {items} |"
            )

        report_lines.append("")

    # 写入文件
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"[OK] 报告已生成: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="众生界完整小说提炼系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--status", action="store_true", help="查看系统状态")
    parser.add_argument("--all", action="store_true", help="提炼所有维度")
    parser.add_argument(
        "--category", choices=["core", "high", "medium", "low"], help="按类别提炼"
    )
    parser.add_argument("--dimension", type=str, help="提炼特定维度")
    parser.add_argument("--limit", type=int, help="限制处理小说数量")
    parser.add_argument("--sync", action="store_true", help="增量同步")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--no-resume", action="store_true", help="从头开始")

    args = parser.parse_args()

    print_banner()

    if args.status:
        print_status()
    elif args.report:
        generate_report()
    elif args.sync:
        run_sync()
    elif args.all or args.category or args.dimension:
        run_extraction(
            dimension=args.dimension,
            category=args.category,
            limit=args.limit,
            resume=not args.no_resume,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
