#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试修复后的 get_character 方法"""

import sys
from pathlib import Path

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
sys.path.insert(0, str(VECTORSTORE_DIR))

from knowledge_search import KnowledgeSearcher

s = KnowledgeSearcher()

print("=" * 70)
print("测试 get_character() 方法修复")
print("=" * 70)

# 测试血牙
print("\n[get_character('血牙')]")
result = s.get_character("血牙")
if result:
    print(f"  名称: {result['name']}")
    print(f"  ID: {result['id']}")
    print(f"  内容长度: {len(result['content'])} 字符")
    print(f"  内容:\n{result['content']}")
else:
    print("  未找到")

# 测试虎啸
print("\n[get_character('虎啸')]")
result = s.get_character("虎啸")
if result:
    print(f"  名称: {result['name']}")
    print(f"  内容长度: {len(result['content'])} 字符")
    print(f"  内容:\n{result['content']}")
else:
    print("  未找到")

# 测试佣兵联盟
print("\n[get_faction('佣兵联盟')]")
result = s.get_faction("佣兵联盟")
if result:
    print(f"  名称: {result['name']}")
    print(f"  内容长度: {len(result['content'])} 字符")
    print(f"  内容预览:\n{result['content'][:400]}...")
else:
    print("  未找到")

# 关键词检查
print("\n" + "=" * 70)
print("关键词检查")
print("=" * 70)

xueya = s.get_character("血牙")
if xueya:
    content = xueya["content"]
    keywords = ["异化人", "领袖", "彼岸", "被遗弃者", "归处"]
    print("\n血牙设定关键词:")
    for kw in keywords:
        status = "FOUND" if kw in content else "MISSING"
        print(f"  {kw}: {status}")

mercenary = s.get_faction("佣兵联盟")
if mercenary:
    content = mercenary["content"]
    keywords = ["修仙者", "魔法师", "科技战士", "教廷骑士", "佣兵"]
    print("\n佣兵联盟设定关键词:")
    for kw in keywords:
        status = "FOUND" if kw in content else "MISSING"
        print(f"  {kw}: {status}")
