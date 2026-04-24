#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正血牙势力设定"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path 以导入配置加载器
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import get_project_root, get_vectorstore_dir

PROJECT_DIR = get_project_root()
VECTORSTORE_DIR = get_vectorstore_dir()
GRAPH_FILE = VECTORSTORE_DIR / "knowledge_graph.json"


def main():
    # 加载图谱
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=== 修正前 ===")
    for eid, entity in data["实体"].items():
        if entity.get("名称") == "血牙":
            print(f"血牙势力: {entity.get('属性', {}).get('势力', '未设定')}")

    # 修正实体
    modified = False
    for eid, entity in data["实体"].items():
        if entity.get("名称") == "血牙":
            entity["属性"]["势力"] = "兽族文明"
            entity["属性"]["力量体系"] = "兽力"
            modified = True
            print(f"\n已修正: 血牙 → 兽族文明")

    # 修正关系
    rel_modified = 0
    for rel in data["关系"]:
        # 属于势力
        if rel.get("源实体") == "血牙" and rel.get("关系类型") == "属于势力":
            if rel.get("目标实体") != "兽族文明":
                print(f"修正关系: {rel['目标实体']} → 兽族文明")
                rel["目标实体"] = "兽族文明"
                rel_modified += 1

        # 使用力量
        if rel.get("源实体") == "血牙" and rel.get("关系类型") == "使用力量":
            if rel.get("目标实体") != "兽力":
                print(f"修正力量: {rel['目标实体']} → 兽力")
                rel["目标实体"] = "兽力"
                rel_modified += 1

    if modified or rel_modified > 0:
        data["元数据"]["更新时间"] = datetime.now().isoformat()

        # 保存
        with open(GRAPH_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n已保存图谱，修正 {rel_modified} 条关系")

    # 验证
    print("\n=== 修正后验证 ===")
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for eid, entity in data["实体"].items():
        if entity.get("名称") == "血牙":
            print(f"血牙势力: {entity.get('属性', {}).get('势力')}")
            print(f"血牙力量: {entity.get('属性', {}).get('力量体系')}")

    for rel in data["关系"]:
        if rel.get("源实体") == "血牙":
            print(f"{rel['源实体']} --[{rel['关系类型']}]--> {rel['目标实体']}")


if __name__ == "__main__":
    main()
