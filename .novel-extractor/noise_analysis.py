"""噪音来源分析"""

import json
from pathlib import Path
from collections import Counter

fp = Path(".novel-extractor/extracted/worldview_element/worldview_element_items.jsonl")
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

noise_suffixes = Counter()
noise_words = Counter()
noise_examples = []

with open(fp, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if line.strip():
            item = json.loads(line)
            name = item.get("element_name", "")
            if not any(name.endswith(s) for s in valid_suffixes):
                if name:
                    last_char = name[-1]
                    noise_suffixes[last_char] += 1
                    noise_words[name] += 1
                    if len(noise_examples) < 20:
                        noise_examples.append(name)

print("=" * 70)
print("噪音来源分析")
print("=" * 70)

print()
print("噪音词尾字符统计（Top 10）:")
for suffix, count in noise_suffixes.most_common(10):
    print(f'  "{suffix}": {count} 次')

print()
print("高频噪音词（Top 20）:")
for word, count in noise_words.most_common(20):
    print(f'  "{word}": {count} 次')

print()
print("噪音示例:")
for ex in noise_examples[:10]:
    print(f'  "{ex}"')

print()
print("结论:")
print('  主要噪音: "道"结尾的对话词（说道、笑道、问道等）')
print("  次要噪音: 传音、心中暗道等描述性短语")
print('  原因: 正则匹配了"道"作为组织后缀')
