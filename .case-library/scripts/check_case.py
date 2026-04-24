import json
from pathlib import Path

# Read the case index
index_path = Path("D:/动画/众生界/.case-library/case_index.json")
with open(index_path, "r", encoding="utf-8") as f:
    index = json.load(f)

# Read first case JSON
first_case = index[0]
with open(first_case["json_path"], "r", encoding="utf-8") as f:
    case_data = json.load(f)

print(f"Case ID: {case_data['case_id']}")
print(f"Novel: {case_data['source']['novel_name']}")
print(f"Scene: {case_data['scene']['type']}")
print(f"Quality: {case_data['quality_score']}")
print(f"Word count: {case_data['scene']['word_count']}")
print("\nContent preview:")
print(case_data["content"][:600])
