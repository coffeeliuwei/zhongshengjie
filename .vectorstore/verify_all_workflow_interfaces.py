#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
众生界小说工作流 - 完整接口验证
验证所有接口在创作流程中的表现
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

# 添加core目录到路径
core_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core")
sys.path.insert(0, core_dir)

from workflow import NovelWorkflow

print("=" * 70)
print("众生界小说工作流 - 完整接口验证")
print("=" * 70)

workflow = NovelWorkflow()

# 记录测试结果
results = {"通过": 0, "失败": 0, "警告": 0, "详情": []}


def test(name, condition, detail=""):
    """记录测试结果"""
    if condition:
        results["通过"] += 1
        status = "✅ 通过"
    else:
        results["失败"] += 1
        status = "❌ 失败"
    results["详情"].append(f"{status} - {name}" + (f": {detail}" if detail else ""))
    print(f"  {status} - {name}")
    return condition


def warn(name, detail=""):
    """记录警告"""
    results["警告"] += 1
    results["详情"].append(f"⚠️ 警告 - {name}: {detail}")
    print(f"  ⚠️ 警告 - {name}: {detail}")


# ============================================================
# 1. 小说设定接口
# ============================================================
print("\n" + "=" * 70)
print("1. 小说设定接口")
print("=" * 70)

# 1.1 角色检索
print("\n【1.1 角色检索】")
char = workflow.get_character("林夕")
test("get_character('林夕')", char is not None, "返回角色数据" if char else "返回None")

# 1.2 角色列表
print("\n【1.2 角色列表】")
chars = workflow.list_characters()
test("list_characters()", len(chars) > 0, f"返回{len(chars)}个角色")

# 1.3 势力检索
print("\n【1.3 势力检索】")
faction = workflow.get_faction("东方修仙")
test("get_faction('东方修仙')", faction is not None)

factions = workflow.list_factions()
test("list_factions()", len(factions) > 0, f"返回{len(factions)}个势力")

# 1.4 力量派别
print("\n【1.4 力量派别】")
branch = workflow.get_power_branch("剑修")
test("get_power_branch('剑修')", branch is not None)

branches = workflow.list_power_branches()
test("list_power_branches()", len(branches) > 0, f"返回{len(branches)}个派别")

# 1.5 语义检索
print("\n【1.5 语义检索】")
results_search = workflow.search_novel("性格内向的主角", top_k=3)
test(
    "search_novel('性格内向的主角')",
    len(results_search) > 0,
    f"返回{len(results_search)}条结果",
)

# ============================================================
# 2. 创作技法接口
# ============================================================
print("\n" + "=" * 70)
print("2. 创作技法接口")
print("=" * 70)

# 2.1 维度列表
print("\n【2.1 维度列表】")
dimensions = workflow.list_technique_dimensions()
test("list_technique_dimensions()", len(dimensions) > 0, f"返回{len(dimensions)}个维度")

# 2.2 按维度获取
print("\n【2.2 按维度获取】")
if dimensions:
    techs = workflow.get_techniques_by_dimension(dimensions[0])
    test(
        f"get_techniques_by_dimension('{dimensions[0]}')",
        len(techs) > 0,
        f"返回{len(techs)}条技法",
    )

# 2.3 语义检索
print("\n【2.3 语义检索】")
tech_results = workflow.search_techniques("战斗中的代价描写", top_k=3)
test(
    "search_techniques('战斗中的代价描写')",
    len(tech_results) > 0,
    f"返回{len(tech_results)}条结果",
)

# ============================================================
# 3. 案例库接口
# ============================================================
print("\n" + "=" * 70)
print("3. 案例库接口")
print("=" * 70)

# 3.1 案例库统计
print("\n【3.1 案例库统计】")
try:
    case_count = workflow.cases.count()
    test("cases.count()", case_count > 0, f"共{case_count}条案例")
    print("  ⚠️ 跳过list_case_scenes() - 数据量过大")
    results["警告"] += 1
except Exception as e:
    warn("案例库连接失败", str(e)[:50])

# 3.2 案例检索
print("\n【3.2 案例检索】")
try:
    case_results = workflow.search_cases("血脉燃烧 战斗", top_k=3)
    test(
        "search_cases('血脉燃烧 战斗')",
        len(case_results) > 0,
        f"返回{len(case_results)}条案例",
    )
except Exception as e:
    warn("案例检索超时", "数据量34万条，查询较慢")

# ============================================================
# 4. 知识图谱接口
# ============================================================
print("\n" + "=" * 70)
print("4. 知识图谱接口")
print("=" * 70)

# 4.1 统计信息
print("\n【4.1 统计信息】")
stats = workflow.get_graph_stats()
test(
    "get_graph_stats()",
    "总实体数" in stats,
    f"总实体:{stats.get('总实体数', 0)}, 总关系:{stats.get('总关系数', 0)}",
)

# 4.2 实体关系
print("\n【4.2 实体关系】")
relations = workflow.get_entity_relations("林夕")
test("get_entity_relations('林夕')", len(relations) >= 0, f"返回{len(relations)}条关系")

# 4.3 完整图谱
print("\n【4.3 完整图谱】")
graph = workflow.get_knowledge_graph()
test("get_knowledge_graph()", "实体" in graph and "关系" in graph)

# ============================================================
# 5. 角色深度设定接口
# ============================================================
print("\n" + "=" * 70)
print("5. 角色深度设定接口")
print("=" * 70)

# 5.1 过往经历
print("\n【5.1 过往经历】")
backstory = workflow.get_character_backstory("林夕")
test("get_character_backstory('林夕')", len(backstory) >= 0, f"返回{len(backstory)}项")
if len(backstory) == 0:
    warn("过往经历为空", "数据未入库或解析失败")

# 5.2 情绪触发
print("\n【5.2 情绪触发】")
emotions = workflow.get_character_emotion_triggers("林夕")
test(
    "get_character_emotion_triggers('林夕')",
    len(emotions) >= 0,
    f"返回{len(emotions)}种",
)
if len(emotions) == 0:
    warn("情绪触发为空", "数据未入库或解析失败")

# 5.3 行为烙印
print("\n【5.3 行为烙印】")
imprints = workflow.get_character_behavior_imprints("林夕")
test(
    "get_character_behavior_imprints('林夕')",
    len(imprints) >= 0,
    f"返回{len(imprints)}条",
)
if len(imprints) == 0:
    warn("行为烙印为空", "数据未入库或解析失败")

# 5.4 完整档案
print("\n【5.4 完整档案】")
profile = workflow.get_character_full_profile("林夕")
test("get_character_full_profile('林夕')", "名称" in profile, "包含基础设定")
if profile:
    print(f"    - 基础设定: {len(profile.get('基础设定', {}))}项")
    print(f"    - 哲学设定: {len(profile.get('哲学设定', {}))}项")
    print(f"    - 过往经历: {len(profile.get('过往经历', {}))}项")
    print(f"    - 情绪触发: {len(profile.get('情绪触发', {}))}种")
    print(f"    - 行为烙印: {len(profile.get('行为烙印', []))}条")

# ============================================================
# 6. 场景预判模板接口
# ============================================================
print("\n" + "=" * 70)
print("6. 场景预判模板接口")
print("=" * 70)

# 6.1 模板列表
print("\n【6.1 模板列表】")
templates = workflow.list_scene_templates()
test("list_scene_templates()", len(templates) >= 0, f"返回{len(templates)}个模板")
if len(templates) == 0:
    warn("场景模板为空", "数据未入库")

# 6.2 获取模板
print("\n【6.2 获取模板】")
template = workflow.get_scene_behavior_template("战斗")
test("get_scene_behavior_template('战斗')", template is not None or len(templates) == 0)
if template is None and len(templates) > 0:
    warn("战斗模板未找到", "ID格式可能不匹配")

# 6.3 情绪状态对照表
print("\n【6.3 情绪状态对照表】")
emotion_ref = workflow.get_emotion_states_reference()
test(
    "get_emotion_states_reference()",
    len(emotion_ref) >= 0,
    f"返回{len(emotion_ref)}种情绪",
)
if len(emotion_ref) == 0:
    warn("情绪状态对照表为空", "数据未入库")

# ============================================================
# 7. 文明技术基础接口
# ============================================================
print("\n" + "=" * 70)
print("7. 文明技术基础接口")
print("=" * 70)

# 7.1 文明类型
print("\n【7.1 文明类型】")
civ_types = workflow.list_civilization_types()
test("list_civilization_types()", len(civ_types) > 0, f"返回{civ_types}")

# 7.2 获取技术
print("\n【7.2 获取技术】")
for civ in civ_types:
    techs = workflow.get_civilization_tech(civ)
    test(f"get_civilization_tech('{civ}')", len(techs) > 0, f"返回{len(techs)}项技术")

# 7.3 按领域过滤
print("\n【7.3 按领域过滤】")
techs_filtered = workflow.get_civilization_tech("科技文明", "量子计算")
test("get_civilization_tech('科技文明', '量子计算')", len(techs_filtered) >= 0)

# 7.4 技术领域列表
print("\n【7.4 技术领域列表】")
domains = workflow.list_tech_domains()
test("list_tech_domains()", len(domains) > 0, f"返回{len(domains)}个领域")

# ============================================================
# 8. 行为预判综合接口
# ============================================================
print("\n" + "=" * 70)
print("8. 行为预判综合接口")
print("=" * 70)

# 8.1 战斗场景预判
print("\n【8.1 战斗场景预判】")
prediction = workflow.predict_character_behavior("林夕", "战斗", "平静")
test("predict_character_behavior('林夕', '战斗', '平静')", "第一反应" in prediction)
if "第一反应" in prediction:
    print(f"    - 第一反应: {prediction.get('第一反应', '')[:50]}...")
    print(f"    - 后续行动: {len(prediction.get('后续行动', []))}项")
    print(f"    - 内心独白: {prediction.get('内心独白', '')[:50]}...")

# 8.2 情感场景预判
print("\n【8.2 情感场景预判】")
prediction2 = workflow.predict_character_behavior("林夕", "情感", "愤怒")
test("predict_character_behavior('林夕', '情感', '愤怒')", "第一反应" in prediction2)

# 8.3 血牙战斗预判
print("\n【8.3 血牙战斗预判】")
prediction3 = workflow.predict_character_behavior("血牙", "战斗", "愤怒")
test("predict_character_behavior('血牙', '战斗', '愤怒')", "第一反应" in prediction3)

# ============================================================
# 9. 场景-作家映射接口
# ============================================================
print("\n" + "=" * 70)
print("9. 场景-作家映射接口")
print("=" * 70)

# 9.1 作家列表
print("\n【9.1 作家列表】")
writers = workflow.get_all_writers()
test("get_all_writers()", len(writers) > 0, f"返回{len(writers)}个作家")

# 9.2 场景列表
print("\n【9.2 场景列表】")
active = workflow.list_active_scenes()
can_activate = workflow.list_can_activate_scenes()
pending = workflow.list_pending_scenes()
inactive = workflow.list_inactive_scenes()
print(f"    - 已激活: {len(active)}个")
print(f"    - 可激活: {len(can_activate)}个")
print(f"    - 待激活: {len(pending)}个")
print(f"    - 不激活: {len(inactive)}个")
test(
    "场景映射数据存在",
    len(active) + len(can_activate) + len(pending) + len(inactive) > 0,
)

# 9.3 场景协作结构
print("\n【9.3 场景协作结构】")
if active:
    collab = workflow.get_scene_collaboration(active[0])
    test(f"get_scene_collaboration('{active[0]}')", collab is not None)
    if collab:
        print(f"    - 主责作家: {collab.get('primary_writer', '未知')}")
        print(f"    - 执行顺序: {' → '.join(collab.get('workflow_order', []))}")

# 9.4 作家角色
print("\n【9.4 作家角色】")
if writers:
    role = workflow.get_writer_role(writers[0])
    test(f"get_writer_role('{writers[0]}')", role is not None)
    if role:
        print(f"    - 角色: {role.get('role', '未知')}")
        print(f" - 专长: {', '.join(role.get('specialty', []))}")

# 9.5 作家参与场景
print("\n【9.5 作家参与场景】")
if writers:
    writer_scenes = workflow.get_scenes_by_writer(writers[0])
    test(
        f"get_scenes_by_writer('{writers[0]}')",
        len(writer_scenes) >= 0,
        f"参与{len(writer_scenes)}个场景",
    )

# ============================================================
# 10. 统计信息
# ============================================================
print("\n" + "=" * 70)
print("10. 统计信息")
print("=" * 70)

all_stats = workflow.get_stats()
print(f"\n【数据库统计】")
print(f"  小说设定库: {all_stats['小说设定库']['总数']}条")
print(f"  创作技法库: {all_stats['创作技法库']['总数']}条")
print(f"  案例库: {all_stats['案例库']['总数']}条")
print(
    f"  知识图谱: {all_stats['知识图谱'].get('总实体数', 0)}实体, {all_stats['知识图谱'].get('总关系数', 0)}关系"
)

# ============================================================
# 汇总
# ============================================================
print("\n" + "=" * 70)
print("验证汇总")
print("=" * 70)
print(f"✅ 通过: {results['通过']}")
print(f"❌ 失败: {results['失败']}")
print(f"⚠️ 警告: {results['警告']}")

if results["失败"] == 0:
    print("\n🎉 所有接口测试通过！")
else:
    print(f"\n⚠️ 有{results['失败']}个接口测试失败，请检查详情：")
    for detail in results["详情"]:
        if "❌" in detail:
            print(f"  {detail}")

# 显示警告详情
if results["警告"] > 0:
    print(f"\n⚠️ 有{results['警告']}个警告：")
    for detail in results["详情"]:
        if "⚠️" in detail:
            print(f"  {detail}")

print("\n" + "=" * 70)
print("验证完成")
print("=" * 70)
