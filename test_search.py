#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试检索功能"""

import sys

sys.path.insert(0, ".vectorstore")

print("=" * 60)
print("技法检索测试")
print("=" * 60)

from core.technique_search import TechniqueSearcher

searcher = TechniqueSearcher()
results = searcher.search("战斗代价描写", top_k=3)

print("查询: 战斗代价描写\n")
for r in results:
    print(f"技法: {r.get('name', '未知')}")
    print(f"维度: {r.get('dimension', '未知')}")
    print(f"相似度: {r.get('score', 0):.4f}")
    print()

print("=" * 60)
print("案例检索测试")
print("=" * 60)

from core.case_search import CaseSearcher

searcher2 = CaseSearcher()
results2 = searcher2.search("玄幻开篇", top_k=3)

print("查询: 玄幻开篇\n")
for r in results2[:3]:
    print(f"来源: {r.get('novel', '未知')}")
    print(f"场景: {r.get('scene_type', '未知')}")
    content = r.get("content", "")
    if content:
        print(f"内容: {content[:100]}...")
    print()
