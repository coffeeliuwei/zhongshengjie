#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说工作流全面测试 - 第一章《天裂》
=====================================

测试覆盖：
1. 知识检索（角色、势力、力量派别）
2. 技法检索（战斗、人物、氛围维度）
3. 知识图谱（实体关系）
4. 统计信息

第一章涉及内容：
- 角色：血牙、铁牙（父亲）、母亲、爷爷、佣兵指挥官
- 势力：青岩部落、佣兵联盟、研究院
- 力量派别：血脉之力（兽族）
- 场景类型：战斗、人物、氛围
"""

import sys
from pathlib import Path

# 添加项目根目录路径
PROJECT_ROOT = Path(__file__).parent.parent
VECTORSTORE_CORE = PROJECT_ROOT / '.vectorstore' / 'core'
sys.path.insert(0, str(VECTORSTORE_CORE))

from workflow import NovelWorkflow


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_result(name: str, result, max_content: int = 200):
    """打印检索结果"""
    if result is None:
        print(f"  [{name}] 未找到")
        return

    if isinstance(result, list):
        print(f"  [{name}] 找到 {len(result)} 条")
        for i, r in enumerate(result[:3], 1):
            content = r.get("内容", "")[:max_content]
            # 替换特殊字符
            content = content.replace("\u2705", "[OK]").replace("\u274c", "[X]")
            print(
                f"    [{i}] {r.get('名称', '未知')} ({r.get('类型', r.get('维度', '未知'))})"
            )
            if content:
                # 只显示ASCII和中文
                safe_content = "".join(
                    c if ord(c) < 128 or 0x4E00 <= ord(c) <= 0x9FFF else " "
                    for c in content
                )
                print(f"        {safe_content}...")
    else:
        print(f"  [{name}] {result.get('名称', '未知')}")
        content = result.get("内容", "")[:max_content]
        if content:
            safe_content = "".join(
                c if ord(c) < 128 or 0x4E00 <= ord(c) <= 0x9FFF else " "
                for c in content
            )
            print(f"    {safe_content}...")


def test_stats(workflow: NovelWorkflow):
    """测试1：统计信息"""
    print_section("测试1：统计信息")

    stats = workflow.get_stats()

    print("\n【小说设定库】")
    print(f"  总数: {stats['小说设定库']['总数']}")

    print("\n【创作技法库】")
    print(f"  总数: {stats['创作技法库']['总数']}")
    print(f"  维度: {', '.join(stats['创作技法库']['维度'])}")

    print("\n【知识图谱】")
    graph_stats = stats["知识图谱"]
    print(f"  总实体: {graph_stats['总实体数']}")
    print(f"  总关系: {graph_stats['总关系数']}")

    print("\n  实体类型分布 (前5):")
    for t, c in sorted(graph_stats["实体类型分布"].items(), key=lambda x: -x[1])[:5]:
        print(f"    {t}: {c}")

    print("\n  关系类型分布 (前5):")
    for t, c in sorted(graph_stats["关系类型分布"].items(), key=lambda x: -x[1])[:5]:
        print(f"    {t}: {c}")

    return True


def test_character_search(workflow: NovelWorkflow):
    """测试2：角色检索"""
    print_section("测试2：角色检索（第一章角色）")

    # 第一章主要角色
    characters = ["血牙", "铁牙", "林夕", "陈傲天"]

    for char_name in characters:
        result = workflow.get_character(char_name)
        print_result(char_name, result, max_content=150)

    # 列出所有角色
    print("\n【所有角色列表】")
    all_chars = workflow.list_characters()
    print(f"  共 {len(all_chars)} 个角色")
    for char in all_chars[:10]:
        print(f"    - {char['名称']}")
    if len(all_chars) > 10:
        print(f"    ... 还有 {len(all_chars) - 10} 个")

    return True


def test_faction_search(workflow: NovelWorkflow):
    """测试3：势力检索"""
    print_section("测试3：势力检索")

    # 第一章涉及的势力
    factions = ["佣兵", "东方修仙", "西方魔法"]

    for faction_name in factions:
        result = workflow.get_faction(faction_name)
        print_result(faction_name, result, max_content=150)

    # 列出所有势力
    print("\n【所有势力列表】")
    all_factions = workflow.list_factions()
    print(f"  共 {len(all_factions)} 个势力")
    for faction in all_factions:
        print(f"    - {faction['名称']}")

    return True


def test_power_branch_search(workflow: NovelWorkflow):
    """测试4：力量派别检索"""
    print_section("测试4：力量派别检索")

    # 第一章涉及的力量
    powers = ["剑修", "血脉", "异能"]

    for power_name in powers:
        result = workflow.get_power_branch(power_name)
        print_result(power_name, result, max_content=150)

    # 列出所有力量派别
    print("\n【所有力量派别列表】")
    all_powers = workflow.list_power_branches()
    print(f"  共 {len(all_powers)} 个力量派别")
    for power in all_powers[:15]:
        print(f"    - {power['名称']}")
    if len(all_powers) > 15:
        print(f"    ... 还有 {len(all_powers) - 15} 个")

    return True


def test_novel_search(workflow: NovelWorkflow):
    """测试5：小说设定语义检索"""
    print_section("测试5：小说设定语义检索")

    queries = [
        ("血脉暴走", None),
        ("佣兵联盟", None),
        ("战斗", "事件"),
        ("修仙", "力量派别"),
    ]

    for query, entity_type in queries:
        results = workflow.search_novel(query, entity_type=entity_type)
        type_str = f"（类型:{entity_type}）" if entity_type else ""
        print_result(f"'{query}'{type_str}", results, max_content=100)

    return True


def test_technique_search(workflow: NovelWorkflow):
    """测试6：创作技法检索"""
    print_section("测试6：创作技法检索")

    # 第一章场景类型对应的技法
    queries = [
        ("战斗代价描写", "战斗"),
        ("人物心理刻画", "人物"),
        ("氛围营造", "氛围"),
        ("仇恨与复仇", None),
        ("群体牺牲", "战斗"),
    ]

    for query, dimension in queries:
        results = workflow.search_techniques(query, dimension=dimension, top_k=3)
        dim_str = f"（维度:{dimension}）" if dimension else ""
        print_result(f"'{query}'{dim_str}", results, max_content=150)

    # 列出所有维度
    print("\n【所有技法维度】")
    dimensions = workflow.list_technique_dimensions()
    print(f"  {', '.join(dimensions)}")

    return True


def test_knowledge_graph(workflow: NovelWorkflow):
    """测试7：知识图谱"""
    print_section("测试7：知识图谱")

    # 获取知识图谱
    graph = workflow.get_knowledge_graph()

    print(f"\n【图谱概览】")
    print(f"  实体数: {len(graph['实体'])}")
    print(f"  关系数: {len(graph['关系'])}")

    # 查找血牙相关的关系
    print("\n【血牙相关关系】")
    relations = workflow.get_entity_relations("血牙")
    print(f"  找到 {len(relations)} 条关系")
    for rel in relations[:5]:
        print(
            f"    {rel.get('源实体', '?')} --[{rel.get('关系类型', '?')}]--> {rel.get('目标实体', '?')}"
        )

    # 查找佣兵联盟相关的关系
    print("\n【佣兵联盟相关关系】")
    relations = workflow.get_entity_relations("佣兵联盟")
    print(f"  找到 {len(relations)} 条关系")
    for rel in relations[:5]:
        print(
            f"    {rel.get('源实体', '?')} --[{rel.get('关系类型', '?')}]--> {rel.get('目标实体', '?')}"
        )

    return True


def test_writer_specific_techniques(workflow: NovelWorkflow):
    """测试8：作家专属技法检索"""
    print_section("测试8：作家专属技法检索")

    # 根据第一章场景类型，检索对应作家的技法
    writer_tasks = [
        ("剑尘", "战斗", "战斗场景的代价描写"),
        ("墨言", "人物", "人物仇恨心理刻画"),
        ("云溪", "氛围", "悲壮氛围营造"),
        ("玄一", "剧情", "伏笔与悬念设计"),
    ]

    for writer, dimension, query in writer_tasks:
        results = workflow.search_techniques(
            query, dimension=dimension, writer=writer, top_k=2
        )
        print_result(f"{writer} - {query}", results, max_content=100)

    return True


def test_chapter_outline_retrieval(workflow: NovelWorkflow):
    """测试9：章节大纲检索"""
    print_section("测试9：章节大纲/事件检索")

    # 检索第一章相关事件
    queries = [
        ("天裂", "事件"),
        ("青岩部落", None),
        ("灭族", None),
    ]

    for query, entity_type in queries:
        results = workflow.search_novel(query, entity_type=entity_type)
        type_str = f"（类型:{entity_type}）" if entity_type else ""
        print_result(f"'{query}'{type_str}", results, max_content=150)

    return True


def test_graph_stats(workflow: NovelWorkflow):
    """测试10：图谱统计"""
    print_section("测试10：图谱统计")

    stats = workflow.get_graph_stats()

    print(f"\n【图谱统计】")
    print(f"  总实体: {stats['总实体数']}")
    print(f"  总关系: {stats['总关系数']}")

    print(f"\n【实体类型分布】")
    for t, c in sorted(stats["实体类型分布"].items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    print(f"\n【关系类型分布（前10）】")
    for t, c in sorted(stats["关系类型分布"].items(), key=lambda x: -x[1])[:10]:
        print(f"  {t}: {c}")

    return True


def main():
    print("=" * 60)
    print(" 小说工作流全面测试 - 第一章《天裂》")
    print("=" * 60)

    # 初始化工作流
    print("\n初始化工作流...")
    workflow = NovelWorkflow()
    print("工作流初始化成功！")

    # 执行测试
    tests = [
        ("统计信息", test_stats),
        ("角色检索", test_character_search),
        ("势力检索", test_faction_search),
        ("力量派别检索", test_power_branch_search),
        ("小说设定语义检索", test_novel_search),
        ("创作技法检索", test_technique_search),
        ("知识图谱", test_knowledge_graph),
        ("作家专属技法", test_writer_specific_techniques),
        ("章节大纲检索", test_chapter_outline_retrieval),
        ("图谱统计", test_graph_stats),
    ]

    results = {}
    for name, test_func in tests:
        try:
            success = test_func(workflow)
            results[name] = "通过" if success else "失败"
        except Exception as e:
            results[name] = f"错误: {str(e)[:50]}"

    # 打印测试结果
    print_section("测试结果汇总")
    print()
    for name, status in results.items():
        symbol = "[OK]" if status == "通过" else "[FAIL]"
        print(f"  {symbol} {name}: {status}")

    # 统计
    passed = sum(1 for s in results.values() if s == "通过")
    total = len(results)

    print(f"\n  总计: {passed}/{total} 通过")

    if passed == total:
        print("\n  所有测试通过! 工作流运行正常。")
    else:
        print("\n  部分测试失败，请检查相关功能。")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
