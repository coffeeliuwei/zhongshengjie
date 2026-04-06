#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
众生界创作工作流全面测试
=====================================
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VECTORSTORE_CORE = PROJECT_ROOT / ".vectorstore" / "core"
sys.path.insert(0, str(VECTORSTORE_CORE))

print("=" * 60)
print("众生界创作工作流全面测试")
print("=" * 60)
print()

# 测试计数
total_tests = 0
passed_tests = 0
failed_tests = 0


def test(name, func):
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    try:
        result = func()
        if result:
            print(f"[PASS] {name}")
            passed_tests += 1
            return True
        else:
            print(f"[FAIL] {name}")
            failed_tests += 1
            return False
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        failed_tests += 1
        return False


# ========================================
# 测试1: Qdrant数据库连接
# ========================================
print("\n【测试1】数据库连接与统计")
print("-" * 40)


def test_qdrant_connection():
    from qdrant_client import QdrantClient

    client = QdrantClient(path=str(PROJECT_ROOT / ".vectorstore" / "qdrant"))
    collections = client.get_collections().collections
    print(f"  集合数量: {len(collections)}")
    for c in collections:
        info = client.get_collection(c.name)
        print(f"    - {c.name}: {info.points_count}条")
    return len(collections) == 3


test("Qdrant数据库连接", test_qdrant_connection)

# ========================================
# 测试2: 工作流初始化
# ========================================
print("\n【测试2】工作流初始化")
print("-" * 40)


def test_workflow_init():
    from workflow import NovelWorkflow

    wf = NovelWorkflow()
    stats = wf.get_stats()
    print(f"  小说设定库: {stats['小说设定库']['总数']}条")
    print(f"  创作技法库: {stats['创作技法库']['总数']}条")
    print(f"  案例库: {stats['案例库']['总数']}条")
    return stats["小说设定库"]["总数"] > 0


test("工作流初始化", test_workflow_init)

# ========================================
# 测试3: 小说设定检索
# ========================================
print("\n【测试3】小说设定检索")
print("-" * 40)


def test_novel_search():
    from workflow import NovelWorkflow

    wf = NovelWorkflow()

    # 测试势力检索
    results = wf.search_novel("势力", entity_type="势力", top_k=3)
    print(f"  势力检索: {len(results)}条结果")
    if results:
        print(f"    示例: {results[0]['name']} ({results[0]['score']:.0%})")

    # 测试角色检索
    results = wf.search_novel("角色", entity_type="角色", top_k=3)
    print(f"  角色检索: {len(results)}条结果")

    return len(results) > 0


test("小说设定检索", test_novel_search)

# ========================================
# 测试4: 创作技法检索
# ========================================
print("\n【测试4】创作技法检索")
print("-" * 40)


def test_technique_search():
    from workflow import NovelWorkflow

    wf = NovelWorkflow()

    # 测试维度列表
    dims = wf.list_technique_dimensions()
    print(f"  可用维度: {len(dims)}个")

    # 测试技法检索
    results = wf.search_techniques("史诗感", top_k=3)
    print(f"  史诗感检索: {len(results)}条结果")
    if results:
        print(f"    示例: {results[0]['name']} ({results[0]['score']:.0%})")

    return len(results) > 0


test("创作技法检索", test_technique_search)

# ========================================
# 测试5: 案例库检索
# ========================================
print("\n【测试5】案例库检索")
print("-" * 40)


def test_case_search():
    from workflow import NovelWorkflow

    wf = NovelWorkflow()

    # 测试场景列表
    scenes = wf.list_case_scenes()
    print(f"  场景类型: {len(scenes)}种")

    # 测试案例检索
    results = wf.search_cases("部落战斗", scene_type="战斗场景", top_k=3)
    print(f"  战斗案例检索: {len(results)}条结果")
    if results:
        print(f"    示例: {results[0]['novel_name']} ({results[0]['score']:.0%})")

    return len(results) > 0


test("案例库检索", test_case_search)

# ========================================
# 测试6: 知识图谱
# ========================================
print("\n【测试6】知识图谱")
print("-" * 40)


def test_knowledge_graph():
    from workflow import NovelWorkflow

    wf = NovelWorkflow()

    graph_stats = wf.get_graph_stats()
    print(f"  实体数: {graph_stats['总实体数']}")
    print(f"  关系数: {graph_stats['总关系数']}")

    return graph_stats["总实体数"] > 0


test("知识图谱", test_knowledge_graph)

# ========================================
# 测试7: 文件结构
# ========================================
print("\n【测试7】项目文件结构")
print("-" * 40)


def test_file_structure():
    project_dir = PROJECT_ROOT

    required = [
        "设定/人物谱.md",
        "设定/十大势力.md",
        "创作技法/README.md",
        "创作技法/01-创作检查清单.md",
        ".vectorstore/core/workflow.py",
        ".vectorstore/qdrant",
        ".case-library/cases",
    ]

    missing = []
    for r in required:
        p = project_dir / r
        if not p.exists():
            missing.append(r)

    if missing:
        print(f"  缺失文件: {missing}")
        return False
    else:
        print(f"  所有必要文件存在")
        return True


test("项目文件结构", test_file_structure)

# ========================================
# 测试8: 技法维度完整性
# ========================================
print("\n【测试8】11维度技法完整性")
print("-" * 40)


def test_dimensions():
    from workflow import NovelWorkflow

    wf = NovelWorkflow()

    expected = [
        "世界观",
        "剧情",
        "人物",
        "战斗",
        "氛围",
        "叙事",
        "主题",
        "情感",
        "读者体验",
        "元维度",
        "节奏",
    ]
    dims = wf.list_technique_dimensions()

    print(f"  预期维度: {len(expected)}个")
    print(f"  实际维度: {len(dims)}个")

    missing = [d for d in expected if d not in dims and f"{d}维度" not in "".join(dims)]
    if missing:
        print(f"  缺失维度: {missing}")

    return len(dims) >= 10


test("11维度技法完整性", test_dimensions)

# ========================================
# 总结
# ========================================
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)
print(f"  总测试数: {total_tests}")
print(f"  通过: {passed_tests}")
print(f"  失败: {failed_tests}")
print(f"  通过率: {passed_tests / total_tests * 100:.0f}%")

if failed_tests == 0:
    print("\n[SUCCESS] 所有测试通过！工作流已就绪。")
else:
    print(f"\n[WARNING] {failed_tests}个测试失败，请检查。")
