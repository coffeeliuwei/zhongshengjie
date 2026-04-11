#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第一章定稿评估测试
测试工作流调用技法检索和评估功能
"""

import sys

sys.path.insert(0, r"D:\动画\众生界\.vectorstore")
from technique_search import TechniqueSearcher

# 初始化检索器
searcher = TechniqueSearcher()

print("=" * 60)
print("第一章定稿评估测试")
print("=" * 60)
print()

# ============================================
# Step 1: 技法检索测试
# ============================================
print("【Step 1】技法检索测试")
print("-" * 40)

scene_type = "战斗"
evaluation_dimensions = ["有代价胜利", "群体牺牲有姓名", "群像塑造", "选择代价"]

dimension_map = {
    "有代价胜利": "战斗",
    "群体牺牲有姓名": "战斗",
    "群像塑造": "人物",
    "选择代价": "人物",
}

standards = []
for dim in evaluation_dimensions:
    print(f"\n检索维度: {dim}")
    results = searcher.search(
        query=f"{scene_type} {dim} 标准",
        dimension=dimension_map.get(dim, ""),
        top_k=2,
        min_length=100,
    )

    if results:
        for r in results:
            name = r.get("name", "未知")
            distance = r.get("distance", 0)
            source = r.get("source", "未知")
            print(f"  - {name} (相关性: {distance:.3f})")
            print(f"    来源: {source}")
            standards.append(
                {
                    "评估维度": dim,
                    "技法名称": name,
                    "来源": source,
                    "相关性": distance,
                }
            )
    else:
        print(f"  未找到相关技法")

print()
print(f"共检索到 {len(standards)} 条评估标准")

# ============================================
# Step 2: 禁止项检测测试
# ============================================
print()
print("=" * 60)
print("【Step 2】禁止项检测测试")
print("-" * 40)

# 读取第一章内容
with open(r"D:\动画\众生界\正文\第一章-天裂.md", encoding="utf-8") as f:
    content = f.read()

# 禁止项检测
forbidden_items = {
    "AI味表达": ["眼中闪过一丝", "心中涌起一股", "嘴角勾起一抹", "不禁"],
    "时间连接词": ["然后", "就在这时", "过了一会儿"],
    "抽象统计词": ["无数", "成千上万"],
    "精确年龄": ["岁的"],
}

forbidden_results = {}
for item_type, patterns in forbidden_items.items():
    count = 0
    examples = []
    for pattern in patterns:
        # 统计出现次数
        occurrences = content.count(pattern)
        if occurrences > 0:
            count += occurrences
            # 找到上下文
            idx = content.find(pattern)
            if idx != -1:
                start = max(0, idx - 20)
                end = min(len(content), idx + len(pattern) + 20)
                context = content[start:end].replace("\n", " ")
                examples.append(f"...{context}...")

    forbidden_results[item_type] = {"数量": count, "示例": examples[:3]}
    status = "FAIL" if count > 0 else "PASS"
    print(f"[{status}] {item_type}: {count}个")
    if examples:
        for ex in examples[:2]:
            print(f"      {ex}")

# ============================================
# Step 3: 技法评估测试
# ============================================
print()
print("=" * 60)
print("【Step 3】技法评估测试")
print("-" * 40)

# 模拟评估（实际需要 LLM 判断）
print("基于检索到的技法标准，进行评估：")
print()

for s in standards:
    print(f"【{s['评估维度']}】")
    print(f"  参考技法: {s['技法名称']}")
    print(f"  相关性: {s['相关性']:.3f}")
    print(f"  评估: [需要 LLM 基于技法内容进行评分]")
    print()

# ============================================
# Step 4: 反馈生成测试
# ============================================
print("=" * 60)
print("【Step 4】反馈生成测试")
print("-" * 40)

print("基于禁止项检测结果，生成反馈：")
print()

if any(r["数量"] > 0 for r in forbidden_results.values()):
    print("P0需修改:")
    for item_type, result in forbidden_results.items():
        if result["数量"] > 0:
            print(f"  - {item_type}: 发现 {result['数量']} 处")
            print(f"    建议: 删除或替换这些表达")
else:
    print("禁止项检测: 全部通过")

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
print()
print("结论:")
print("1. 技法检索: 正常工作，可根据场景类型检索评估标准")
print("2. 禁止项检测: 正常工作，可检测 AI 味表达等问题")
print("3. 技法评估: 需要调用 LLM 进行评分")
print("4. 反馈生成: 可基于检测结果生成修改建议")
