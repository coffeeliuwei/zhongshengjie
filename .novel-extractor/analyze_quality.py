"""数据质量分析脚本"""

import json
from pathlib import Path

print("=" * 70)
print("数据质量深度分析")
print("=" * 70)

# 1. character_relation 噪声分析
print()
print("[character_relation] 人物关系噪声分析...")
path = Path("extracted/character_relation/character_relation_items.jsonl")
noise_count = 0
valid_count = 0
total = 0
valid_examples = []
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            item = json.loads(line)
            total += 1
            c1 = item.get("character1", "")
            c2 = item.get("character2", "")
            if c1 == "~~~" or len(c1) < 2 or c1.startswith("~"):
                noise_count += 1
            else:
                valid_count += 1
                if len(valid_examples) < 10:
                    valid_examples.append(f"{c1} <-> {c2}")

print(f"  总量: {total}")
print(f"  有效: {valid_count}")
print(f"  噪声: {noise_count}")
print(f"  噪声比例: {round(noise_count / total * 100, 2)}%")
if valid_examples:
    print("  有效示例:")
    for ex in valid_examples:
        print(f"    {ex}")

# 2. power_vocabulary 检查噪声
print()
print("[power_vocabulary] 力量词汇质量...")
path = Path("extracted/power_vocabulary/power_vocabulary_items.jsonl")
noise_count = 0
valid_count = 0
total = 0
noise_words = set()
valid_examples = []
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            item = json.loads(line)
            total += 1
            term = item.get("term", "")
            pt = item.get("power_type", "")
            # 检查是否是噪声词
            if (
                len(term) < 2
                or term.isdigit()
                or term in ["一", "二", "三", "十", "百", "千"]
            ):
                noise_count += 1
                noise_words.add(term)
            else:
                valid_count += 1
                if len(valid_examples) < 10:
                    valid_examples.append(f"{term} [{pt}]")

print(f"  总量: {total}")
print(f"  有效: {valid_count}")
print(f"  噪声: {noise_count}")
if noise_words:
    print(f"  噪声词示例: {list(noise_words)[:10]}")
if valid_examples:
    print("  有效示例:")
    for ex in valid_examples:
        print(f"    {ex}")

# 3. worldview_element
print()
print("[worldview_element] 世界观元素...")
valid_suffixes = [
    "城",
    "市",
    "山",
    "峰",
    "宗",
    "门",
    "派",
    "国",
    "帝国",
    "学院",
    "盟",
    "楼",
    "阁",
    "会",
    "教",
    "殿",
    "宫",
    "谷",
    "洞",
    "港",
    "湾",
    "府",
    "岛",
    "州",
    "都",
]
path = Path("extracted/worldview_element/worldview_element_items.jsonl")
total = sum(1 for _ in open(path, "r", encoding="utf-8"))
valid = 0
valid_examples = []
with open(path, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if line.strip():
            item = json.loads(line)
            name = item.get("element_name", "")
            et = item.get("element_type", "")
            if any(name.endswith(s) for s in valid_suffixes):
                valid += 1
                if len(valid_examples) < 10:
                    valid_examples.append(f"{name} [{et}]")

print(f"  总量: {total}")
print(f"  有效: {valid}")
print(f"  噪声: {total - valid}")
print(f"  噪声比例: {round((total - valid) / total * 100, 2)}%")
if valid_examples:
    print("  有效示例:")
    for ex in valid_examples:
        print(f"    {ex}")

# 4. 其他小维度快速检查
print()
print("[其他维度快速检查]")
for dim in [
    "emotion_arc",
    "dialogue_style",
    "foreshadow_pair",
    "power_cost",
    "author_style",
]:
    path = Path(f"extracted/{dim}/{dim}_items.jsonl")
    if not path.exists():
        print(f"  {dim}: 文件不存在")
        continue
    total = sum(1 for _ in open(path, "r", encoding="utf-8"))
    print(f"  {dim}: {total} 条")

print()
print("=" * 70)
print("总结")
print("=" * 70)
