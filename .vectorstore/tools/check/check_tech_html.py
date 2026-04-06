import re

with open("technique_graph.html", "r", encoding="utf-8") as f:
    content = f.read()

# 查找统计
stats = re.findall(r'总(.+?): <span class="stats-value">(\d+)</span>', content)
print("技法图谱统计:")
for name, value in stats:
    print(f"  总{name}: {value}")

# 查找时间戳
timestamp = re.search(r"众生界 - (.+?)</title>", content)
if timestamp:
    print(f"\n时间戳: {timestamp.group(1)}")
