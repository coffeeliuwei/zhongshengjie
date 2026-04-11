#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证更新后的工作流读取"""

import sys
from pathlib import Path

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
sys.path.insert(0, str(VECTORSTORE_DIR))

from knowledge_search import KnowledgeSearcher

s = KnowledgeSearcher()

print("=" * 70)
print("更新后的工作流读取验证")
print("=" * 70)

# 测试血牙
print("\n[血牙设定]")
result = s.search_knowledge("血牙", data_type="character", top_k=3)
for r in result:
    print(f"  名称: {r['name']}")
    print(f"  ID: {r['id']}")
    print(f"  内容长度: {len(r['content'])} 字符")
    print(f"  内容预览:\n{r['content'][:400]}...")
    print()

# 测试虎啸
print("\n[虎啸设定]")
result = s.search_knowledge("虎啸", data_type="character", top_k=3)
for r in result:
    print(f"  名称: {r['name']}")
    print(f"  内容长度: {len(r['content'])} 字符")
    print(f"  内容预览:\n{r['content'][:400]}...")

# 测试佣兵联盟
print("\n[佣兵联盟设定]")
result = s.search_knowledge("佣兵联盟", data_type="faction", top_k=1)
if result:
    r = result[0]
    print(f"  名称: {r['name']}")
    print(f"  内容长度: {len(r['content'])} 字符")
    print(f"  内容预览:\n{r['content'][:400]}...")

# 检查关键词
print("\n" + "=" * 70)
print("关键词检查")
print("=" * 70)

xueya = s.search_knowledge("血牙", data_type="character", top_k=1)
if xueya:
    content = xueya[0]["content"]
    keywords = ["异化人", "领袖", "彼岸", "被遗弃者"]
    print("\n血牙设定关键词:")
    for kw in keywords:
        status = "FOUND" if kw in content else "MISSING"
        print(f"  {kw}: {status}")

mercenary = s.search_knowledge("佣兵联盟", data_type="faction", top_k=1)
if mercenary:
    content = mercenary[0]["content"]
    keywords = ["修仙者", "魔法师", "科技战士", "教廷骑士"]
    print("\n佣兵联盟设定关键词:")
    for kw in keywords:
        status = "FOUND" if kw in content else "MISSING"
        print(f"  {kw}: {status}")
