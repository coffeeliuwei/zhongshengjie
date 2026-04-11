import json
from collections import Counter

file_path = "D:/动画/众生界/.novel-extractor/extracted/character_relation/character_relation_items.jsonl"

# Count unique characters and check quality
char1_names = Counter()
char2_names = Counter()
novel_ids = set()
total = 0

with open(file_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            data = json.loads(line)
            novel_ids.add(data["_novel_id"])
            char1_names[data["character1"]] += 1
            char2_names[data["character2"]] += 1
            total += 1

# Write results to UTF-8 file
with open(
    "D:/动画/众生界/.novel-extractor/check_results.txt", "w", encoding="utf-8"
) as out:
    out.write(f"总条数: {total}\n")
    out.write(f"唯一小说数: {len(novel_ids)}\n\n")

    out.write("Top 20 character1 (去除~~~):\n")
    for name, count in char1_names.most_common(30):
        if name != "~~~":
            out.write(f"  {name}: {count}\n")

    out.write("\nTop 20 character2:\n")
    for name, count in char2_names.most_common(20):
        out.write(f"  {name}: {count}\n")

print("Results written to check_results.txt")
