#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查技法中的特殊字符"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from technique_search import TechniqueSearcher

ts = TechniqueSearcher()
results = ts.search("战斗代价", top_k=3)

print("检查技法内容中的特殊字符:")
print("=" * 50)

for r in results:
    print(f"\n名称: {r['名称']}")
    print(f"维度: {r['维度']}")

    content = r["内容"]
    # 找出非中文字符
    special_chars = []
    for c in content[:500]:
        code = ord(c)
        # 非ASCII且非中文
        if code > 127 and not (0x4E00 <= code <= 0x9FFF):
            if c not in ["\n", "\r", "\t"]:
                special_chars.append((c, hex(code)))

    if special_chars:
        print(f"发现特殊字符: {special_chars[:5]}")
    else:
        print("无特殊字符")
