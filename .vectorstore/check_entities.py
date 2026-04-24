#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('knowledge_graph.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

entities = data.get('实体', {})

# 建立名称到ID的映射
name_to_id = {}
for eid, e in entities.items():
    name = e.get('名称', '')
    if name:
        name_to_id[name] = eid

# 检查力量体系是否存在
power_systems = ['修仙', '魔法', '神术', '武力', '商业', '军阵', '科技', '兽力', 'AI力', '异能', '数字', '分身']
print('力量体系检查:')
for ps in power_systems:
    found = ps in name_to_id
    status = "存在" if found else "缺失"
    print(f'  {ps}: {status}')

print()
# 检查角色是否存在
characters = ['林夕', '艾琳娜', '塞巴斯蒂安', '陈傲天', '洛影', '赵恒', '林正阳', '苏瑾', '鬼影', '白露', '李道远', 'K-7', '幽灵', '零', 'AI零', '虎啸', '月牙', '血牙', '花姬', '镜']
print('角色检查:')
for c in characters:
    found = c in name_to_id
    status = "存在" if found else "缺失"
    print(f'  {c}: {status}')

print()
# 检查来源是否存在
sources = ['李道远团队', 'AI零', 'The Consciousness AI', 'AI零自我发现', '远古实验室']
print('来源检查:')
for s in sources:
    found = s in name_to_id
    status = "存在" if found else "缺失"
    print(f'  {s}: {status}')

print()
# 列出所有力量体系类型实体
print('力量体系类型实体:')
for eid, e in entities.items():
    if e.get('类型') == '力量体系':
        print(f'  {e.get(\"名称\")}: {eid}')