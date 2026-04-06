import json

d = json.load(open("knowledge_graph.json", "r", encoding="utf-8"))
print("旧格式血脉实体:")
for e in d["实体"]:
    if "血脉" in e:
        print(f"  - {e}")
print("\n新格式血脉实体:")
for e in d["实体"]:
    if e.startswith("bloodline_"):
        print(f"  - {e}")
