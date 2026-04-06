#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从实体属性中提取隐含关系
"""

import json
from pathlib import Path
from datetime import datetime

VECTORSTORE_DIR = Path(__file__).parent
JSON_FILE = VECTORSTORE_DIR / "knowledge_graph.json"

# 定义可以从属性中提取的关系字段
RELATION_FIELD_MAPPING = {
    # 字段名: (关系类型, 是否是列表)
    "来源": ("来源于", False),
    "所属势力": ("属于势力", False),
    "势力": ("属于势力", False),
    "力量体系": ("使用力量体系", False),
    "涉及势力": ("涉及势力", True),
    "主要势力": ("主要势力", True),
    "文明": ("涉及势力", False),
    "技术领域": ("涉及领域", False),
}


def extract_relations():
    """从实体属性中提取隐含关系"""
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data.get("实体", {})
    existing_relations = data.get("关系", [])

    # 建立名称到ID的映射
    name_to_id = {}
    for eid, e in entities.items():
        name = e.get("名称", "")
        if name:
            name_to_id[name] = eid

    # 建立现有关系集合（用于去重）
    existing_set = set()
    for r in existing_relations:
        key = (r.get("源实体", ""), r.get("关系类型", ""), r.get("目标实体", ""))
        existing_set.add(key)

    # 提取新关系
    new_relations = []
    stats = {}

    for eid, e in entities.items():
        entity_name = e.get("名称", eid)
        attrs = e.get("属性", {})

        for field, (rel_type, is_list) in RELATION_FIELD_MAPPING.items():
            if field not in attrs:
                continue

            value = attrs[field]
            if not value:
                continue

            # 处理列表或单个值
            values = value if is_list and isinstance(value, list) else [value]

            for v in values:
                if not v or not isinstance(v, str):
                    continue

                # 检查是否已存在
                key = (entity_name, rel_type, v)
                if key in existing_set:
                    continue

                # 验证目标实体是否存在
                if v not in name_to_id:
                    print(f"  警告: 目标实体不存在: {v} (来自 {entity_name}.{field})")
                    continue

                # 添加新关系
                new_relations.append(
                    {
                        "源实体": entity_name,
                        "关系类型": rel_type,
                        "目标实体": v,
                        "属性": {"来源字段": field},
                    }
                )
                existing_set.add(key)

                # 统计
                stats[rel_type] = stats.get(rel_type, 0) + 1

    # 合并关系
    all_relations = existing_relations + new_relations

    # 更新元数据
    metadata = data.get("元数据", {})
    metadata["更新时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata["关系统计"] = {}

    # 统计所有关系类型
    for r in all_relations:
        rt = r.get("关系类型", "未知")
        metadata["关系统计"][rt] = metadata["关系统计"].get(rt, 0) + 1

    # 保存
    data["关系"] = all_relations
    data["元数据"] = metadata

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 输出统计
    print("=" * 60)
    print("关系提取完成")
    print("=" * 60)
    print(f"原有关系: {len(existing_relations)}")
    print(f"新增关系: {len(new_relations)}")
    print(f"总关系数: {len(all_relations)}")
    print()
    print("新增关系统计:")
    for rt, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {rt}: {count}")

    return len(new_relations)


if __name__ == "__main__":
    extract_relations()
