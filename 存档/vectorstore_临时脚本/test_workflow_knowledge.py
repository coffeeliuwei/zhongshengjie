#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试工作流调用知识检索功能
验证：
1. 章节大纲获取
2. 角色设定获取
3. 势力设定获取
4. 统一检索
"""

import sys
from pathlib import Path

# 添加路径
VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
sys.path.insert(0, str(VECTORSTORE_DIR))

from knowledge_search import KnowledgeSearcher


def test_chapter_outline():
    """测试获取章节大纲"""
    print("\n" + "=" * 60)
    print("测试1：获取第一章大纲")
    print("=" * 60)

    searcher = KnowledgeSearcher()
    outline = searcher.get_outline(chapter=1)

    if outline:
        print(f"\n章节信息:")
        if outline["info"]:
            print(f"  ID: {outline['info']['id']}")
            print(f"  名称: {outline['info']['name']}")
            print(f"  内容摘要: {outline['info']['content'][:200]}...")

        print(f"\n场景列表 ({len(outline['scenes'])} 个):")
        for scene in outline["scenes"]:
            print(f"  - {scene['name']}")
            print(f"    ID: {scene['id']}")
            print(f"    内容: {scene['content'][:100]}...")

        return True
    else:
        print("❌ 未找到第一章大纲")
        return False


def test_character_setting():
    """测试获取角色设定"""
    print("\n" + "=" * 60)
    print("测试2：获取角色设定（血牙）")
    print("=" * 60)

    searcher = KnowledgeSearcher()
    character = searcher.get_character("血牙")

    if character:
        print(f"\n角色信息:")
        print(f"  ID: {character['id']}")
        print(f"  名称: {character['name']}")
        print(f"  类型: {character['type']}")
        print(f"  来源: {character['source_file']}")
        print(f"  内容摘要: {character['content'][:300]}...")
        return True
    else:
        print("❌ 未找到角色'血牙'")
        return False


def test_faction_setting():
    """测试获取势力设定"""
    print("\n" + "=" * 60)
    print("测试3：获取势力设定（佣兵联盟）")
    print("=" * 60)

    searcher = KnowledgeSearcher()
    faction = searcher.get_faction("佣兵联盟")

    if faction:
        print(f"\n势力信息:")
        print(f"  ID: {faction['id']}")
        print(f"  名称: {faction['name']}")
        print(f"  类型: {faction['type']}")
        print(f"  来源: {faction['source_file']}")
        print(f"  内容摘要: {faction['content'][:300]}...")
        return True
    else:
        print("❌ 未找到势力'佣兵联盟'")
        return False


def test_power_setting():
    """测试获取力量体系"""
    print("\n" + "=" * 60)
    print("测试4：获取力量体系（血脉）")
    print("=" * 60)

    searcher = KnowledgeSearcher()
    power = searcher.get_power("血脉")

    if power:
        print(f"\n力量体系信息:")
        print(f"  ID: {power['id']}")
        print(f"  名称: {power['name']}")
        print(f"  类型: {power['type']}")
        print(f"  内容摘要: {power['content'][:300]}...")
        return True
    else:
        print("❌ 未找到力量体系'血脉'")
        return False


def test_unified_search():
    """测试统一检索"""
    print("\n" + "=" * 60)
    print("测试5：统一检索（林远 战斗）")
    print("=" * 60)

    searcher = KnowledgeSearcher()
    results = searcher.search("林远 战斗", data_type=None, top_k=5)

    for source, items in results.items():
        print(f"\n【{source}】")
        for item in items:
            print(f"  - {item['name']}")
            print(f"    相关性: {item['distance']:.3f}")

    return len(results) > 0


def test_workflow_scenario():
    """测试工作流场景模拟"""
    print("\n" + "=" * 60)
    print("测试6：工作流场景模拟（第一章战斗场景）")
    print("=" * 60)

    searcher = KnowledgeSearcher()

    # Step 1: 获取章节大纲
    outline = searcher.get_outline(chapter=1)
    if not outline:
        print("❌ 无法获取章节大纲")
        return False

    print(f"\n[准备阶段] 获取章节大纲")
    print(f"  章节: 第一章")
    print(f"  场景数: {len(outline['scenes'])}")

    # Step 2: 分析场景涉及的角色
    # 从大纲内容中提取角色名
    scene_content = outline["scenes"][0]["content"] if outline["scenes"] else ""

    # 搜索涉及的角色
    print(f"\n[任务分解] 搜索涉及角色")
    characters = searcher.search_knowledge("林远", data_type="character", top_k=3)
    for char in characters:
        print(f"  - {char['name']}")

    # Step 3: 搜索涉及的势力
    print(f"\n[任务分解] 搜索涉及势力")
    factions = searcher.search_knowledge("佣兵", data_type="faction", top_k=3)
    for faction in factions:
        print(f"  - {faction['name']}")

    # Step 4: 搜索相关技法
    print(f"\n[Evaluator准备] 搜索相关技法")
    techniques = searcher.search_techniques("战斗 代价", dimension="战斗", top_k=3)
    for tech in techniques:
        print(f"  - {tech['name']} ({tech['dimension']})")

    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("工作流知识检索集成测试")
    print("=" * 60)

    # 显示数据库统计
    searcher = KnowledgeSearcher()
    stats = searcher.get_stats()
    print("\n数据库状态:")
    for source, info in stats.items():
        print(f"  {source}:")
        if isinstance(info, dict):
            for key, value in info.items():
                print(f"    {key}: {value}")

    # 运行测试
    tests = [
        test_chapter_outline,
        test_character_setting,
        test_faction_setting,
        test_power_setting,
        test_unified_search,
        test_workflow_scenario,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"❌ {test.__name__} 失败: {e}")
            results.append((test.__name__, False))

    # 输出总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")

    print(f"\n总计: {passed}/{total} 测试通过")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
