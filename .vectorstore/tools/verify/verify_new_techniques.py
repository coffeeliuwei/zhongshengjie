#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证新入库的技法"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from workflow import NovelWorkflow

workflow = NovelWorkflow()

print("=" * 60)
print("创作技法入库验证")
print("=" * 60)

# 统计信息
stats = workflow.get_stats()
print(f"\n技法库总数：{stats['创作技法库']['总数']条")
print(f"维度数量：{len(stats['创作技法库']['维度'])}个")

# 检索测试
tests = [
    ("外貌描写", "人物"),
    ("眼睛描写", "人物"),
    ("情感描写", "人物"),
    ("性格描写", "人物"),
    ("战斗公式", "战斗"),
    ("自然风景", "氛围"),
    ("古代兵器", "世界观"),
    ("计时法", "世界观"),
    ("十二时辰", "世界观"),
]

print("\n" + "=" * 60)
print("检索测试")
print("=" * 60)

for query, dim in tests:
    results = workflow.search_techniques(query, dimension=dim, top_k=2)
    status = "[OK]" if results else "[FAIL]"
    print(f"\n{status} 检索 \"{query}\" (维度：{dim})")
    if results:
        for r in results[:2]:
            name = r.get('name', r.get('名称', 'unknown'))
            print(f"    - {name}")
    else:
        print(f"    未找到结果")

print("\n" + "=" * 60)
print("维度分布统计")
print("=" * 60)

from technique_search import TechniqueSearcher
ts = TechniqueSearcher()
stats_full = ts.get_stats()

for dim, count in sorted(stats_full['按维度'].items(), key=lambda x: -x[1]):
    print(f"  {dim}: {count}条")

print("\n" + "=" * 60)
print("验证完成！")
print("=" * 60)