#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间线数据修复与中文化脚本
1. 将时间线数据从 setting 改为 event
2. 将所有字段名改为中文
3. 创建主时间线管理维度
"""

import chromadb
from pathlib import Path
from datetime import datetime
import re

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
PROJECT_DIR = Path(r"D:\动画\众生界")

# 连接数据库
client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
collection = client.get_collection("novelist_knowledge")

print("=" * 70)
print("时间线数据修复与中文化")
print("=" * 70)

# ============================================================
# 步骤1：修复时间线分类
# ============================================================
print("\n[步骤1] 修复时间线分类 (setting → event)")

# 获取所有 setting 类型数据
all_data = collection.get()
timeline_keywords = [
    "时间线",
    "时代",
    "觉醒时代",
    "蛰伏时代",
    "风暴时代",
    "变革时代",
    "终局时代",
    "转折点",
]

timeline_ids = []
timeline_docs = []
timeline_metas = []

for i, (id_, doc, meta) in enumerate(
    zip(all_data["ids"], all_data["documents"], all_data["metadatas"])
):
    if meta.get("类型") == "setting":
        # 检查是否是时间线相关
        name = meta.get("名称", "")
        if any(kw in name or kw in doc[:500] for kw in timeline_keywords):
            timeline_ids.append(id_)
            timeline_docs.append(doc)
            timeline_metas.append(meta)
            print(f"  发现时间线数据: {name}")

print(f"\n  共发现 {len(timeline_ids)} 条时间线数据")

# 更新类型为 event
for id_, meta in zip(timeline_ids, timeline_metas):
    new_meta = meta.copy()
    new_meta["类型"] = "事件"
    new_meta["时间线类型"] = "世界时间线"

    collection.update(ids=[id_], metadatas=[new_meta])
    print(f"  已更新: {id_} → 类型=事件")

# ============================================================
# 步骤2：中文化所有字段名
# ============================================================
print("\n[步骤2] 中文化所有字段名")

# 字段映射表（英文→中文）
FIELD_MAP = {
    "type": "类型",
    "name": "名称",
    "source_file": "来源文件",
    "source_section": "来源章节",
    "faction": "势力",
    "identity": "身份",
    "invasion_status": "入侵状态",
    "dimension": "维度",
    "writer": "适用作家",
    "technique_name": "技法名称",
    "importance": "重要性",
    "stage": "适用阶段",
    "race": "种族",
    "role": "角色定位",
}

all_data = collection.get()
updated_count = 0

for i, (id_, meta) in enumerate(zip(all_data["ids"], all_data["metadatas"])):
    new_meta = {}
    changed = False

    for key, value in meta.items():
        if key in FIELD_MAP:
            new_meta[FIELD_MAP[key]] = value
            changed = True
        else:
            new_meta[key] = value

    # 同时更新内容中的字段名（如果是JSON格式）

    if changed:
        collection.update(ids=[id_], metadatas=[new_meta])
        updated_count += 1

print(f"  已更新 {updated_count} 条记录的字段名")

# ============================================================
# 步骤3：创建主时间线管理维度
# ============================================================
print("\n[步骤3] 创建主时间线管理维度")

# 定义主时间线结构
MAIN_TIMELINE = {
    "世界时间线": {
        "时间范围": "第1-100年",
        "时代划分": ["觉醒时代", "蛰伏时代", "风暴时代", "变革时代", "终局时代"],
        "描述": "《众生界》百年史诗时间线",
    }
}

# 创建时代事件条目
eras = [
    {
        "id": "event_era_awakening",
        "名称": "觉醒时代",
        "类型": "时代",
        "时间范围": "第1-10年",
        "核心事件": ["觉醒之夜", "血脉觉醒", "部落灭亡"],
        "时代特点": "震惊、迷茫、愤怒、绝望",
        "色调": "血红、暗灰",
        "代表意象": "屠杀、血、火",
    },
    {
        "id": "event_era_dormant",
        "名称": "蛰伏时代",
        "类型": "时代",
        "时间范围": "第11-30年",
        "核心事件": ["势力冲突", "血脉修炼"],
        "时代特点": "隐忍、积累、希望、暗流",
        "色调": "灰蓝、暗绿",
        "代表意象": "雨、雾、山",
    },
    {
        "id": "event_era_storm",
        "名称": "风暴时代",
        "类型": "时代",
        "时间范围": "第31-50年",
        "核心事件": ["全面战争", "英雄辈出"],
        "时代特点": "激烈、悲壮、英雄、热血",
        "色调": "血红、金色",
        "代表意象": "战火、旗帜、血",
    },
    {
        "id": "event_era_change",
        "名称": "变革时代",
        "类型": "时代",
        "时间范围": "第51-70年",
        "核心事件": ["势力重组", "传承确立"],
        "时代特点": "沉静、传承、新生、希望",
        "色调": "金色、白色",
        "代表意象": "新芽、晨光、传承",
    },
    {
        "id": "event_era_finale",
        "名称": "终局时代",
        "类型": "时代",
        "时间范围": "第71-100年",
        "核心事件": ["最终入侵", "命运终结"],
        "时代特点": "史诗、命运、终章、新生",
        "色调": "金色、血红",
        "代表意象": "夕阳、星辰、命运",
    },
]

# 添加时代条目
now = datetime.now().isoformat()
for era in eras:
    era_id = era["id"]
    era_name = era["名称"]

    # 构建内容
    content = f"""# {era_name}

**时间范围**: {era["时间范围"]}
**时代特点**: {era["时代特点"]}
**色调**: {era["色调"]}
**代表意象**: {era["代表意象"]}

## 核心事件
"""
    for event in era["核心事件"]:
        content += f"- {event}\n"

    # 检查是否已存在
    existing = collection.get(ids=[era_id])
    if existing["ids"]:
        # 更新
        collection.update(
            ids=[era_id],
            documents=[content],
            metadatas=[
                {
                    "类型": "时代",
                    "名称": era_name,
                    "时间范围": era["时间范围"],
                    "来源文件": "时间线.md",
                    "更新时间": now,
                }
            ],
        )
        print(f"  更新时代: {era_name}")
    else:
        # 新建
        collection.add(
            ids=[era_id],
            documents=[content],
            metadatas=[
                {
                    "类型": "时代",
                    "名称": era_name,
                    "时间范围": era["时间范围"],
                    "来源文件": "时间线.md",
                }
            ],
        )
        print(f"  创建时代: {era_name}")

# ============================================================
# 步骤4：验证结果
# ============================================================
print("\n[步骤4] 验证结果")

all_data = collection.get()
type_counts = {}
for meta in all_data["metadatas"]:
    t = meta.get("类型", "未知")
    type_counts[t] = type_counts.get(t, 0) + 1

print("\n各类型统计:")
for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {count}")

print("\n完成！")
