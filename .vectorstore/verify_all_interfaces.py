#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证所有新接口"""

import sys
import os

# 添加core目录到路径
core_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core")
sys.path.insert(0, core_dir)

from workflow import NovelWorkflow

workflow = NovelWorkflow()

print("=" * 60)
print("验证所有新接口")
print("=" * 60)

# 1. 验证场景模板
print("\n【场景预判模板】")
templates = workflow.list_scene_templates()
print(f"  模板数量: {len(templates)}")
if templates:
    print(f"  示例: {templates[0]}")

template = workflow.get_scene_behavior_template("战斗")
if template:
    print(f"  战斗模板核心要素: {template.get('属性', {}).get('核心要素', 'N/A')}")

# 2. 验证情绪状态
print("\n【情绪状态对照表】")
emotion_ref = workflow.get_emotion_states_reference()
print(f"  情绪类型: {len(emotion_ref)} 种")
if emotion_ref:
    print(f"  示例（愤怒）: {emotion_ref.get('愤怒', {}).get('行为倾向', 'N/A')}")

# 3. 验证文明技术
print("\n【文明技术基础】")
for civ in workflow.list_civilization_types():
    techs = workflow.get_civilization_tech(civ)
    print(f"  {civ}: {len(techs)} 项技术")

techs = workflow.get_civilization_tech("科技文明", "量子计算")
if techs:
    print(f"  科技文明·量子计算: {techs[0].get('名称', 'N/A')}")

# 4. 验证行为预判
print("\n【行为预判综合接口】")
prediction = workflow.predict_character_behavior("血牙", "战斗", "愤怒")
print(f"  血牙·战斗·愤怒")
print(f"    第一反应: {prediction.get('第一反应', 'N/A')[:50]}...")
print(f"    后续行动: {len(prediction.get('后续行动', []))} 项")

prediction2 = workflow.predict_character_behavior("林夕", "情感", "平静")
print(f"  林夕·情感·平静")
print(f"    第一反应: {prediction2.get('第一反应', 'N/A')[:50]}...")

# 5. 知识图谱统计
print("\n【知识图谱统计】")
stats = workflow.get_graph_stats()
print(f"  总实体: {stats.get('总实体数', 0)}")
print(f"  总关系: {stats.get('总关系数', 0)}")
type_dist = stats.get("实体类型分布", {})
for t, count in sorted(type_dist.items(), key=lambda x: -x[1])[:5]:
    print(f"    {t}: {count}")

print("\n" + "=" * 60)
print("所有接口验证完成!")
print("=" * 60)
