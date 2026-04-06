#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证小说结构十法入库"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from workflow import NovelWorkflow

wf = NovelWorkflow()
stats = wf.get_stats()

print("=" * 60)
print("小说结构十法 入库验证")
print("=" * 60)
print("技法库总数:", stats["创作技法库"]["总数"], "条（原 363 条，+11 条）")
print()

# 测试检索
tests = [
    ("悬念 倒叙", "叙事"),
    ("意料之外", "剧情"),
    ("形散神聚", "叙事"),
    ("一箭双雕", "叙事"),
    ("偶然必然", "剧情"),
    ("明线暗线", "叙事"),
    ("欲扬先抑", "人物"),
    ("以小见大", "主题"),
    ("余音绕梁", "叙事"),
]
print("检索测试:")
for query, dim in tests:
    results = wf.search_techniques(query, dimension=dim, top_k=2)
    status = "[OK]" if results else "[FAIL]"
    print(f'  {status} "{query}" ({dim}): {len(results)} 条命中')
    if results:
        for r in results[:1]:
            name = r.get("name", r.get("名称", "N/A"))
            print(f"      - {name}")

print()
print("维度分布（更新后）:")
from technique_search import TechniqueSearcher

ts = TechniqueSearcher()
stats_full = ts.get_stats()
for dim, count in sorted(stats_full["按维度"].items(), key=lambda x: -x[1]):
    print(f"  {dim}: {count}条")

print()
print("完成！")
