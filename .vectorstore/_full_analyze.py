import json
from collections import Counter

with open(r"D:\动画\众生界\.vectorstore\knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})
relations = data.get("关系", [])

print("=" * 60)
print("knowledge_graph.json 完整分析报告")
print("=" * 60)

print("\n1. 顶层结构:")
for k in data.keys():
    print(f"  - {k}")

print(f"\n2. 实体总数：{len(entities)}")
print(f"3. 关系总数：{len(relations)}")

print("\n4. 实体类型分布:")
type_counts = Counter(e.get("类型", "未知") for e in entities.values())
for t, c in type_counts.most_common():
    print(f"  {t}: {c}")

print("\n5. 实体 ID 命名模式 (前 10 个):")
for eid in list(entities.keys())[:10]:
    print(f"  {eid}")

print("\n6. 关系结构分析:")
rel_patterns = Counter(r.get("关系", "未知") for r in relations)
print("  关系类型分布:")
for rel, c in rel_patterns.most_common(10):
    print(f"    {rel}: {c}")

print("\n7. 单个实体完整示例:")
sample_id = list(entities.keys())[0]
sample = entities[sample_id]
print(f"  ID: {sample_id}")
print(f"  类型：{sample.get('类型')}")
print(f"  属性数量：{len(sample.get('属性', {}))}")
if sample.get("属性"):
    sample_attrs = sample["属性"]
    for k, v in list(sample_attrs.items())[:8]:
        dtype = type(v).__name__
        if isinstance(v, str) and len(v) > 50:
            v_show = v[:50] + "..."
        else:
            v_show = v
        print(f"    {k} ({dtype}): {v_show}")

print("\n8. 关系结构示例 (前 3 个):")
for r in relations[:3]:
    print(f"  {r}")
