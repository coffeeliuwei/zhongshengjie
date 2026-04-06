import json

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})
relations = data.get("关系", [])

# 构建name_to_id
name_to_id = {}
for eid, e in entities.items():
    name = e.get("名称") or e.get("属性", {}).get("名称", "")
    if name:
        name_to_id[name] = eid

# 收集所有关系中的实体名称
source_names = set()
target_names = set()
for rel in relations:
    source = rel.get("源实体", "")
    target = rel.get("目标实体", "")
    if source:
        source_names.add(source)
    if target:
        target_names.add(target)

# 找出缺失的名称
missing_sources = source_names - set(name_to_id.keys())
missing_targets = target_names - set(name_to_id.keys())

print(f"名称映射数: {len(name_to_id)}")
print(f"关系中的源实体数: {len(source_names)}")
print(f"关系中的目标实体数: {len(target_names)}")
print(f"\n缺失的源实体 ({len(missing_sources)}):")
for name in sorted(missing_sources)[:20]:
    print(f"  - {name}")

print(f"\n缺失的目标实体 ({len(missing_targets)}):")
for name in sorted(missing_targets)[:20]:
    print(f"  - {name}")
