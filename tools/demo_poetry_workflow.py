#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云溪诗词创作流程演示 - 重构README诗词

流程说明：
1. 情感内核分析 - 分析场景深层情感
2. 众生界意象检索 - 从数据检索契合意象
3. 创作指导生成 - 生成完整指导
4. 诗词重构 - 基于指导创作
"""

import json
from pathlib import Path

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / ".vectorstore" / "data"

print("=" * 60)
print("云溪诗词创作流程 - 重构README诗词")
print("=" * 60)
print()

# ========================================
# 原诗分析
# ========================================
print("【原诗】")
print("千山隐迹路何寻，万象归墟棋自沉")
print("执子终成枰上客，风碑无言证浮沉")
print()

# ========================================
# 步骤1：情感内核分析
# ========================================
print("=" * 60)
print("【步骤1：情感内核分析】")
print("=" * 60)
print()
print("场景：众生界核心诗句，展现世界观")
print("表面情绪：孤独、追问")
print()
print("深层分析：")
print("  - 千山隐迹 → 无处寻觅、无归属感")
print("  - 万象归墟 → 虚无感、终极归宿")
print("  - 棋自沉 → 被操控感、命运无解")
print("  - 执子终成枰上客 → 执棋者沦为棋子")
print("  - 风碑无言 → 历史沉默、无人应答")
print()
print("情感内核：被操控感 + 虚无感 + 追问无答")
print("哲学层面：众生皆棋子，无人是棋手")
print()

# ========================================
# 步骤2：众生界意象检索
# ========================================
print("=" * 60)
print("【步骤2：众生界意象检索】")
print("=" * 60)
print()

# 加载意象数据
imagery_path = DATA_DIR / "poetry_imagery_data.json"
if imagery_path.exists():
    with open(imagery_path, "r", encoding="utf-8") as f:
        imagery_data = json.load(f)

    # 筛选众生界意象
    world_imagery = [x for x in imagery_data if x.get("world_context") == "众生界"]

    print(f"众生界特色意象共 {len(world_imagery)} 条：")
    for i, img in enumerate(world_imagery):
        print(f"\n  {i + 1}. {img['name']}")
        print(f"     情感内核：{img['emotion_core']}")
        print(f"     情感标签：{', '.join(img['emotion_tags'])}")
        if img.get("philosophy_link"):
            print(f"     哲学关联：{img['philosophy_link']}")
else:
    print("意象数据文件不存在")

# ========================================
# 步骤3：诗词重构分析
# ========================================
print()
print("=" * 60)
print("【步骤3：诗词重构分析】")
print("=" * 60)
print()
print("原诗意象组合：")
print("  - 棋（枰、棋子）→ 众生皆弈的核心意象")
print("  - 风碑 → 历史沉默的见证者")
print("  - 千山/万象 → 宏大背景")
print()
print("意象契合度分析：")
print("  [OK] 棋意象契合「众生皆棋子」哲学")
print("  [OK] 风碑契合「无人应答」的沉默")
print("  [OK] 意象指向同一情感基调：被操控+虚无")
print()

# ========================================
# 步骤4：结论
# ========================================
print("=" * 60)
print("【步骤4：重构结论】")
print("=" * 60)
print()
print("原诗评估：")
print("  [OK] 情感内核准确：被操控感 + 虚无感 + 追问无答")
print("  [OK] 意象选择正确：棋、风碑都是众生界核心意象")
print("  [OK] 哲学关联契合：众生皆棋子，执棋者终成棋子")
print("  [OK] 意象连贯性：所有意象指向同一情感")
print()
print("结论：原诗已经很好，体现了云溪诗词能力的核心原则")
print("      无需重构，可作为众生界标志性诗句")
print()
print("=" * 60)
print("【云溪诗词创作流程总结】")
print("=" * 60)
print()
print("1. 情感内核分析")
print("   - 不看表面情绪，找深层情感")
print("   - 例：战斗惨胜 → 不是悲伤，是虚无感")
print()
print("2. 意象检索（众生界模式）")
print("   - world_context='众生界'")
print("   - 返回众生界特色意象 + 哲学关联")
print()
print("3. 意象选择原则")
print("   - 契合情感内核")
print("   - 意象之间有内在关联")
print("   - 指向同一情感基调")
print()
print("4. 诗词生成")
print("   - 意象组合 + 情感内核 + 哲学关联")
print("   - 确保形对意也对")
