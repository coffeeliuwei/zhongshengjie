import json
with open(r"D:\动画\众生界\.vectorstore\knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)
print("Keys:", list(data.keys()))
entities = data.get("实体", {})
print("Entities:", len(entities))
relations = data.get("关系", [])
print("Relations:", len(relations))
print("Entity Types:", set(e.get("类型") for e in entities.values() if e.get("类型")))

