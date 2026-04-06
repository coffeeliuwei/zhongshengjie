#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证新入库的技法"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from workflow import NovelWorkflow

wf = NovelWorkflow()
stats = wf.get_stats()

print("=" * 60)
print("创作技法入库验证")
print("=" * 60)
print("技法库总数:", stats["创作技法库"]["总数"], "条（原 338 条）")
print("维度数量:", len(stats["创作技法库"]["维度"]), "个")
print()

# 测试检索
tests = [
    ("场景描写", "叙事"),
    ("对话技巧", "叙事"),
    ("主题确立", "主题"),
    ("语言铸造", "元维度"),
    ("叙事观点", "叙事"),
]
print("检索测试:")
for query, dim in tests:
    results = wf.search_techniques(query, dimension=dim, top_k=2)
    status = "[OK]" if results else "[FAIL]"
    print(f'  {status} "{query}" ({dim}): {len(results)} 条命中')

print()
print("完成！")
