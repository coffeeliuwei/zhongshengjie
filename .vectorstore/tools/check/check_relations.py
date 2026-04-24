import json

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

relations = data.get("关系", [])

print("关系格式示例:")
for rel in relations[:5]:
    source = rel.get("源实体", "")
    target = rel.get("目标实体", "")
    rel_type = rel.get("关系类型", "")
    print(f"  源: {source} | 关系: {rel_type} | 目标: {target}")

# 检查是否源实体是entity_id
char_relations = [r for r in relations if r.get("源实体", "").startswith("char_")]
print(f"\n以char_开头的源实体数: {len(char_relations)}")
if char_relations:
    print(f"示例: {char_relations[0]}")

# 检查是否源实体是中文名称
name_relations = [
    r
    for r in relations
    if not r.get("源实体", "").startswith("char_")
    and not r.get("源实体", "").startswith("faction_")
]
print(f"\n源实体是中文名称的关系数: {len(name_relations)}")
if name_relations:
    print(f"示例: {name_relations[0]}")
