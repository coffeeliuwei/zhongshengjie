#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证新接口"""

import sys
import os

# 添加core目录到路径
core_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core")
sys.path.insert(0, core_dir)

from workflow import NovelWorkflow

workflow = NovelWorkflow()

print("=" * 60)
print("验证角色深度设定接口")
print("=" * 60)

# 测试角色
roles = ["林夕", "血牙", "零"]

for role in roles:
    print(f"\n【{role}】")

    # 获取过往经历
    backstory = workflow.get_character_backstory(role)
    print(f"  过往经历: {len(backstory)} 项")
    if backstory:
        for k, v in list(backstory.items())[:2]:
            if isinstance(v, dict):
                print(f"    - {k}: {v.get('内容', v)[:50]}...")
            else:
                print(f"    - {k}: {str(v)[:50]}...")

    # 获取情绪触发
    emotions = workflow.get_character_emotion_triggers(role)
    print(f"  情绪触发: {len(emotions)} 种")
    if emotions:
        for k, v in list(emotions.items())[:2]:
            if isinstance(v, dict):
                print(f"    - {k}: {v.get('触发条件', v)[:40]}...")

    # 获取行为烙印
    imprints = workflow.get_character_behavior_imprints(role)
    print(f"  行为烙印: {len(imprints)} 条")
    if imprints:
        for imp in imprints[:2]:
            if isinstance(imp, dict):
                print(
                    f"    - {imp.get('触发情境', '?')}: {imp.get('行为反应', '?')[:30]}..."
                )

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
