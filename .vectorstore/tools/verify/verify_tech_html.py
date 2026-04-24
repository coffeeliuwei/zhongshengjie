import re

with open("technique_graph.html", "r", encoding="utf-8") as f:
    content = f.read()

# 检查技法数据是否包含
if "const techniques = [" in content:
    # 提取技法数量
    match = re.search(r"共 (\d+) 条技法", content)
    if match:
        print(f"Techniques: {match.group(1)}")

    # 检查是否有技法内容
    if "technique-card" in content:
        print("[OK] Has technique cards")

    # 检查详情模态框
    if "modal-content" in content:
        print("[OK] Has detail modal")

    # 检查搜索功能
    if "searchInput" in content:
        print("[OK] Has search function")

    # 检查维度筛选
    if "filterByDimension" in content:
        print("[OK] Has dimension filter")

    # 检查作家筛选
    if "filterByWriter" in content:
        print("[OK] Has writer filter")

    # 文件大小
    print(f"File size: {len(content) / 1024:.1f} KB")

    # 检查时间戳
    match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", content)
    if match:
        print(f"Timestamp: {match.group(1)}")
else:
    print("[ERROR] No technique data found")
