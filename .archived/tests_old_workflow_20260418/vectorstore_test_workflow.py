#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流完整性测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录路径
PROJECT_ROOT = Path(__file__).parent.parent
VECTORSTORE_CORE = PROJECT_ROOT / '.vectorstore' / 'core'
sys.path.insert(0, str(VECTORSTORE_CORE))


def test_workflow():
    """测试 NovelWorkflow"""
    print("=" * 60)
    print("测试 NovelWorkflow")
    print("=" * 60)

    from workflow import NovelWorkflow

    workflow = NovelWorkflow()

    # 测试统计
    print("\n[1] 测试 get_stats():")
    stats = workflow.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 测试小说设定检索
    print("\n[2] 测试 get_character('林夕'):")
    char = workflow.get_character("林夕")
    if char:
        print(f"  找到: {char['名称']}")
        print(f"  类型: {char['类型']}")
    else:
        print("  未找到")

    # 测试势力
    print("\n[3] 测试 get_faction('东方修仙'):")
    faction = workflow.get_faction("东方修仙")
    if faction:
        print(f"  找到: {faction['名称']}")
    else:
        print("  未找到")

    # 测试力量派别
    print("\n[4] 测试 get_power_branch('剑修'):")
    power = workflow.get_power_branch("剑修")
    if power:
        print(f"  找到: {power['名称']}")
    else:
        print("  未找到")

    # 测试技法检索
    print("\n[5] 测试 search_techniques('战斗代价'):")
    techs = workflow.search_techniques("战斗代价", top_k=3)
    print(f"  找到 {len(techs)} 条")
    for t in techs:
        print(f"  - {t['名称']} ({t['维度']})")

    # 测试知识图谱
    print("\n[6] 测试 get_knowledge_graph():")
    graph = workflow.get_knowledge_graph()
    print(f"  实体数: {len(graph['实体'])}")
    print(f"  关系数: {len(graph['关系'])}")

    # 测试图谱统计
    print("\n[7] 测试 get_graph_stats():")
    graph_stats = workflow.get_graph_stats()
    print(f"  总实体: {graph_stats['总实体数']}")
    print(f"  总关系: {graph_stats['总关系数']}")
    print(f"  实体类型分布:")
    for t, c in sorted(graph_stats["实体类型分布"].items(), key=lambda x: -x[1])[:5]:
        print(f"    {t}: {c}")

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)
    return True


def test_knowledge_search():
    """测试 knowledge_search"""
    print("\n" + "=" * 60)
    print("测试 KnowledgeSearcher")
    print("=" * 60)

    from knowledge_search import KnowledgeSearcher

    searcher = KnowledgeSearcher()

    # 测试统计
    print("\n[1] 测试 get_stats():")
    stats = searcher.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 测试小说设定检索
    print("\n[2] 测试 search_novel('林夕'):")
    results = searcher.search_novel("林夕", entity_type="角色")
    print(f"  找到 {len(results)} 条")
    for r in results[:2]:
        print(f"  - {r['名称']} ({r['类型']})")

    # 测试技法检索
    print("\n[3] 测试 search_techniques('战斗代价'):")
    techs = searcher.search_techniques("战斗代价", dimension="战斗")
    print(f"  找到 {len(techs)} 条")
    for t in techs[:2]:
        print(f"  - {t['名称']} ({t['维度']})")

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)
    return True


def test_technique_search():
    """测试 technique_search"""
    print("\n" + "=" * 60)
    print("测试 TechniqueSearcher")
    print("=" * 60)

    from technique_search import TechniqueSearcher

    searcher = TechniqueSearcher()

    # 测试统计
    print("\n[1] 测试 get_stats():")
    stats = searcher.get_stats()
    print(f"  总技法数: {stats['总技法数']}")
    print(f"  各维度数量:")
    for dim, count in sorted(stats["各维度数量"].items(), key=lambda x: -x[1]):
        print(f"    {dim}: {count}")

    # 测试检索
    print("\n[2] 测试 search('战斗代价'):")
    results = searcher.search("战斗代价", top_k=3)
    print(f"  找到 {len(results)} 条")
    for r in results:
        print(f"  - {r['name']} ({r['dimension']})")

    # 测试维度列表
    print("\n[3] 测试 list_all_dimensions():")
    dims = searcher.list_all_dimensions()
    print(f"  维度: {dims}")

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)
    return True


def check_file_configs():
    """检查文件配置一致性"""
    print("\n" + "=" * 60)
    print("检查配置一致性")
    print("=" * 60)

    import re

    files_to_check = [
        (PROJECT_ROOT / ".vectorstore" / "core" / "workflow.py", "workflow.py"),
        (
            PROJECT_ROOT / ".vectorstore" / "core" / "knowledge_search.py",
            "knowledge_search.py",
        ),
        (
            PROJECT_ROOT / ".vectorstore" / "core" / "technique_search.py",
            "technique_search.py",
        ),
        (
            PROJECT_ROOT / ".vectorstore" / "sync" / "sync_to_vectorstore_v3.py",
            "sync_to_vectorstore_v3.py",
        ),
        (
            PROJECT_ROOT / ".vectorstore" / "sync" / "rebuild_knowledge_graph_v2.py",
            "rebuild_knowledge_graph_v2.py",
        ),
    ]

    configs = {}

    for filepath, filename in files_to_check:
        if not filepath.exists():
            print(f"  [警告] {filename} 不存在: {filepath}")
            continue

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # 提取关键配置
        novel_collection = re.search(
            r'["\']novel_settings["\']|NOVEL_COLLECTION\s*=\s*["\']([^"\']+)["\']',
            content,
        )
        tech_collection = re.search(
            r'["\']writing_techniques["\']|TECHNIQUE_COLLECTION\s*=\s*["\']([^"\']+)["\']',
            content,
        )
        chroma_dir = re.search(r"CHROMA_DIR\s*=\s*[^#\n]+", content)

        configs[filename] = {
            "novel_collection": novel_collection.group(1)
            if novel_collection and novel_collection.group(1)
            else "novel_settings"
            if novel_collection
            else None,
            "tech_collection": tech_collection.group(1)
            if tech_collection and tech_collection.group(1)
            else "writing_techniques"
            if tech_collection
            else None,
            "chroma_dir": "chroma" in (chroma_dir.group(0) if chroma_dir else ""),
        }

    print("\n配置检查结果:")
    for filename, config in configs.items():
        print(f"\n  {filename}:")
        print(f"    novel_collection: {config['novel_collection']}")
        print(f"    tech_collection: {config['tech_collection']}")
        print(f"    chroma_dir: {config['chroma_dir']}")

    # 检查一致性
    novel_names = set(
        c["novel_collection"] for c in configs.values() if c["novel_collection"]
    )
    tech_names = set(
        c["tech_collection"] for c in configs.values() if c["tech_collection"]
    )

    issues = []
    if len(novel_names) > 1:
        issues.append(f"小说设定集合名称不一致: {novel_names}")
    if len(tech_names) > 1:
        issues.append(f"创作技法集合名称不一致: {tech_names}")

    if issues:
        print("\n[问题] 发现配置不一致:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\n[OK] 所有配置一致")
        return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("众生界工作流完整性测试")
    print("=" * 60)

    results = []

    # 检查配置
    try:
        results.append(("配置一致性", check_file_configs()))
    except Exception as e:
        results.append(("配置一致性", False))
        print(f"错误: {e}")

    # 测试工作流
    try:
        results.append(("NovelWorkflow", test_workflow()))
    except Exception as e:
        results.append(("NovelWorkflow", False))
        print(f"错误: {e}")

    # 测试知识检索
    try:
        results.append(("KnowledgeSearcher", test_knowledge_search()))
    except Exception as e:
        results.append(("KnowledgeSearcher", False))
        print(f"错误: {e}")

    # 测试技法检索
    try:
        results.append(("TechniqueSearcher", test_technique_search()))
    except Exception as e:
        results.append(("TechniqueSearcher", False))
        print(f"错误: {e}")

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n所有测试通过!")
    else:
        print("\n存在失败的测试，请检查!")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
