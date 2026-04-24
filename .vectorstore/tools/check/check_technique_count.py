#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
import re

# 添加项目根目录到 sys.path 以导入配置加载器
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import get_techniques_dir

tech_dir = get_techniques_dir()

# 统计每个文件内的技法条目数
total_techniques = 0
file_details = []

for md_file in tech_dir.rglob("*.md"):
    try:
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 统计二级和三级标题
        h2_count = len(re.findall(r"^## [^#]", content, re.MULTILINE))
        h3_count = len(re.findall(r"^### [^#]", content, re.MULTILINE))

        file_details.append({"file": md_file.name, "h2": h2_count, "h3": h3_count})
        total_techniques += h2_count + h3_count
    except:
        pass

print(f"=== 技法文件内容分析 ===")
print(f"文件总数: {len(file_details)}")
print(f"二级+三级标题总数: {total_techniques}")
print()

# 显示标题最多的文件
file_details.sort(key=lambda x: x["h2"] + x["h3"], reverse=True)
print("标题最多的文件:")
for f in file_details[:15]:
    print(f"  {f['file']}: H2={f['h2']}, H3={f['h3']}")
