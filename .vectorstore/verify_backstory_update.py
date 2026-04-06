#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证角色过往经历更新"""

import json
import sys
from pathlib import Path

# 添加项目根目录到 sys.path 以导入配置加载器
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import get_vectorstore_dir

KG_FILE = get_vectorstore_dir() / "knowledge_graph.json"

with open(KG_FILE, "r", encoding="utf-8") as f:
    kg = json.load(f)

chars_to_check = ["char_linxi", "char_xueya", "char_huxiao", "char_zero", "char_elena"]

for cid in chars_to_check:
    if cid in kg["实体"]:
        e = kg["实体"][cid]
        attrs = e.get("属性", {})
        name = e.get("名称", "?")
        backstory_count = len(attrs.get("过往经历", {}))
        emotion_count = len(attrs.get("情绪触发", {}))
        imprint_count = len(attrs.get("行为烙印", []))
        print(
            f"{name}: 过往经历={backstory_count}, 情绪触发={emotion_count}, 行为烙印={imprint_count}"
        )
    else:
        print(f"{cid}: NOT FOUND")
