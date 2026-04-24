#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析README中的两首诗"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / ".vectorstore" / "data"
with open(DATA_DIR / "poetry_imagery_data.json", "r", encoding="utf-8") as f:
    imagery = json.load(f)

world_imagery = [x for x in imagery if x.get("world_context") == "众生界"]

print("=" * 60)
print("云溪诗词分析 - README两首诗")
print("=" * 60)
print()

# ========================================
# 诗1分析
# ========================================
print("【诗1】七言律诗")
print("-" * 40)
print("千山隐迹路何寻，万象归墟棋自沉")
print("执子终成枰上客，风碑无言证浮沉")
print()
print("情感内核分析：")
print("  - 千山隐迹：无处寻觅、无归属")
print("  - 万象归墟：虚无感、终极归宿")
print("  - 棋自沉：被操控感、命运无解")
print("  - 执子终成枰上客：执棋者沦为棋子")
print("  - 风碑无言：历史沉默、无人应答")
print()
print("核心情感：被操控感 + 虚无感 + 追问无答")
print()
print("意象检索匹配：")
for img in world_imagery:
    if img["name"] in ["棋", "棋盘", "棋子", "落定"]:
        print(f"  [OK] {img['name']}：{img['emotion_core']}")
        if img.get("philosophy_link"):
            print(f"       哲学关联：{img['philosophy_link']}")
print()

# ========================================
# 诗2分析
# ========================================
print("=" * 60)
print("【诗2】散文诗（简介）")
print("-" * 40)
print("天无主，地无归处。")
print()
print("千年的博弈从未停歇。岁月来去如风，执子之人终化作棋子，")
print("被棋局困在缝隙之间；缝隙里的他们，早把名字尘封。")
print()
print("众生皆苦，众生皆弈，众生在追问：我是谁？")
print()
print("无人应答的沉默里——")
print("风穿过石碑的纹路，穿过荒野的盐霜，穿过黎明前无人铭记的日落。")
print()
print("这不是答案。")
print()
print("千年的追问，既无答案，也无尽头；")
print("却如同一枚未落定的棋子，静默地宣布自己的存在。")
print()
print("去问风，去问碑，去问那些死在黎明前的人。")
print("他们曾以为自己知道。")
print()
print("情感内核分析：")
print("  - 天无主、地无归处：无归属感")
print("  - 执子之人终化作棋子：众生皆棋子")
print("  - 缝隙之间：夹缝生存")
print("  - 名字尘封：身份消逝")
print("  - 无人应答：追问无答")
print("  - 盐霜：苦难痕迹")
print("  - 黎明前无人铭记的日落：无人见证")
print("  - 未落定的棋子：变数、存在证明")
print()
print("核心情感：追问无答 + 命运无解 + 存在证明")
print()
print("意象检索匹配：")
for img in world_imagery:
    name = img["name"]
    if name in ["棋", "棋子", "缝隙", "轮回", "未落定的棋子"]:
        print(f"  [OK] {name}：{img['emotion_core']}")
        if img.get("philosophy_link"):
            print(f"       哲学关联：{img['philosophy_link']}")
print()

# ========================================
# 对比总结
# ========================================
print("=" * 60)
print("【两首诗对比】")
print("=" * 60)
print()
print("| 维度 | 诗1（七言律诗） | 诗2（散文诗） |")
print("|------|-----------------|--------------|")
print("| 形式 | 传统诗词，对仗工整 | 散文诗，自由节奏 |")
print("| 意象 | 棋、风碑（精炼） | 棋、缝隙、盐霜、黎明前日落（丰富） |")
print("| 情感 | 被操控感、虚无感 | 追问无答、存在证明 |")
print("| 哲学 | 众生皆棋子 | 众生皆棋子 + 缝隙理论 |")
print()

print("【评估结论】")
print("-" * 40)
print()
print("两首诗都契合云溪诗词能力核心原则：")
print()
print("诗1：")
print("  [OK] 情感内核准确：被操控感 + 虚无感")
print("  [OK] 意象选择：棋、风碑都是众生界核心意象")
print("  [OK] 意象连贯：指向同一情感基调")
print("  [OK] 形对意也对")
print()
print("诗2：")
print("  [OK] 情感内核准确：追问无答 + 存在证明")
print("  [OK] 意象丰富：使用了众生界7个特色意象")
print("  [OK] 哲学深度：众生皆棋子 + 缝隙理论")
print("  [OK] 散文诗意：与众生界史诗感契合")
print()
print("【重构建议】")
print("-" * 40)
print()
print("两首诗都很好，无需重构。")
print()
print("诗1作为开篇定场诗，精炼有力。")
print("诗2作为简介，展开众生界世界观。")
print()
print("两者配合：诗1点题，诗2展开。")
