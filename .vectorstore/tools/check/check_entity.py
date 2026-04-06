import json

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 检查力量体系实体结构
power = data["实体"].get("power_cultivation", {})
print("力量体系实体结构:")
print(f"  类型: {power.get('类型')}")
attrs = power.get("属性", {})
print(f"  属性名称: {attrs.get('名称')}")

# 检查时代实体结构
era = data["实体"].get("era_awakening", {})
print("\n时代实体结构:")
print(f"  类型: {era.get('类型')}")
attrs = era.get("属性", {})
print(f"  属性名称: {attrs.get('名称')}")

# 检查角色实体结构（有名称的）
char = data["实体"].get("char_xueya", {})
print("\n角色实体结构:")
print(f"  类型: {char.get('类型')}")
print(f"  名称: {char.get('名称')}")
