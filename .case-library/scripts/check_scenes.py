#!/usr/bin/env python3
import re
from pathlib import Path

# 检查unified_case_extractor.py中的场景定义
content = Path("unified_case_extractor.py").read_text(encoding="utf-8")

# 查找所有场景类型名
scenes = re.findall(r'"([^"]+)":\s*\{[^}]*"keywords":', content)

print("SCENE_TYPES中定义的场景类型:")
for s in scenes:
    print(f"  - {s}")

print()
if "打脸场景" in scenes:
    print("✅ 打脸场景已在SCENE_TYPES中定义")
else:
    print("❌ 打脸场景未在SCENE_TYPES中定义")

if "高潮场景" in scenes:
    print("✅ 高潮场景已在SCENE_TYPES中定义")
else:
    print("❌ 高潮场景未在SCENE_TYPES中定义")
