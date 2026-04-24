#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 添加项目根目录到 sys.path 以导入配置加载器
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import get_settings_dir

file_path = get_settings_dir() / "行为预判模板.md"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 检查核心场景类型部分
print("查找核心场景类型...")
scene_section = re.search(r"核心场景类型", content)
if scene_section:
    start = scene_section.start()
    print(f"找到位置: {start}")
    print("\n内容片段:")
    print(content[start : start + 800])
else:
    print("未找到核心场景类型")

print("\n" + "=" * 50)
print("查找情绪状态对照表...")
emotion_section = re.search(r"情绪状态对照表", content)
if emotion_section:
    start = emotion_section.start()
    print(f"找到位置: {start}")
    print("\n内容片段:")
    print(content[start : start + 600])
