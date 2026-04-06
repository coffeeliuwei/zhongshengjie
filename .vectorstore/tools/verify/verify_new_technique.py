#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from technique_search import TechniqueSearcher

ts = TechniqueSearcher()

print("=== 检索新技法 ===")
print()

# 检索死亡场景技法
results = ts.search("死亡场景情感", dimension="情感", top_k=5)
print('搜索"死亡场景情感":')
for r in results:
    name = r.get("name", r.get("名称", "unknown"))
    dim = r.get("dimension", r.get("维度", "unknown"))
    print(f"  - {name} ({dim})")

print()

# 检索遗憾闭环
results = ts.search("遗憾闭环", top_k=3)
print('搜索"遗憾闭环":')
for r in results:
    name = r.get("name", r.get("名称", "unknown"))
    print(f"  - {name}")

print()

# 检索反向救赎
results = ts.search("反向救赎", top_k=3)
print('搜索"反向救赎":')
for r in results:
    name = r.get("name", r.get("名称", "unknown"))
    print(f"  - {name}")

print()

# 检索物是人非
results = ts.search("物是人非", top_k=3)
print('搜索"物是人非":')
for r in results:
    name = r.get("name", r.get("名称", "unknown"))
    print(f"  - {name}")

print()

# 统计
stats = ts.get_stats()
print(f"技法库总数: {stats['总数']}")
