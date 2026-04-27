#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""同步高级写作技法到向量库"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

# 加载配置
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import (
    get_project_root,
    get_model_path,
    get_techniques_dir,
    get_qdrant_url,
)

PROJECT_DIR = get_project_root()
TECHNIQUE_FILE = get_techniques_dir() / "99-外部资源" / "高级写作技法大全.md"


def parse_techniques(content):
    """解析技法文件"""
    techniques = []
    current_dimension = None

    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # 检测维度标题
        if line.startswith("## "):
            dim_match = re.match(r"## (.+维度)", line)
            if dim_match:
                current_dimension = dim_match.group(1)
            i += 1
            continue

        # 检测技法标题
        if line.startswith("### 技法"):
            tech_match = re.match(r"### 技法(\d+)：(.+?)(?: - (.+))?$", line)
            if tech_match:
                tech_num = tech_match.group(1)
                tech_name = tech_match.group(2).strip()
                tech_subtitle = tech_match.group(3) or ""

                # 提取技法内容
                tech_content = {
                    "id": f"tech_{tech_num}",
                    "name": tech_name,
                    "dimension": current_dimension,
                    "subtitle": tech_subtitle,
                    "content": "",
                    "scenes": [],
                    "principle": "",
                    "example": "",
                    "notes": [],
                }

                # 解析技法详情
                j = i + 1
                while (
                    j < len(lines)
                    and not lines[j].startswith("### 技法")
                    and not lines[j].startswith("## ")
                ):
                    detail_line = lines[j]

                    if detail_line.startswith("**技法名称**"):
                        tech_content["name"] = detail_line.split("：")[-1].strip()
                    elif detail_line.startswith("**适用场景**"):
                        # 收集场景
                        j += 1
                        while j < len(lines) and lines[j].startswith("- "):
                            tech_content["scenes"].append(lines[j][2:].strip())
                            j += 1
                        continue
                    elif detail_line.startswith("**核心原理**"):
                        j += 1
                        principle_lines = []
                        while (
                            j < len(lines)
                            and not lines[j].startswith("**")
                            and not lines[j].startswith("---")
                        ):
                            if lines[j].strip():
                                principle_lines.append(lines[j].strip())
                            j += 1
                        tech_content["principle"] = " ".join(principle_lines)
                        continue
                    elif detail_line.startswith("**具体示例**"):
                        j += 1
                        example_lines = []
                        while (
                            j < len(lines)
                            and not lines[j].startswith("**注意事项**")
                            and not lines[j].startswith("---")
                        ):
                            example_lines.append(lines[j])
                            j += 1
                        tech_content["example"] = "\n".join(example_lines)
                        continue
                    elif detail_line.startswith("**注意事项**"):
                        j += 1
                        while j < len(lines) and (
                            lines[j].startswith("1.")
                            or lines[j].startswith("2.")
                            or lines[j].startswith("3.")
                            or lines[j].startswith("4.")
                            or lines[j].startswith("5.")
                        ):
                            tech_content["notes"].append(lines[j].strip())
                            j += 1
                        continue

                    j += 1

                # 构建完整内容
                tech_content["content"] = f"""
{tech_content["name"]} - {tech_content["subtitle"]}

适用场景：
{chr(10).join(tech_content["scenes"])}

核心原理：
{tech_content["principle"]}

注意事项：
{chr(10).join(tech_content["notes"])}
""".strip()

                techniques.append(tech_content)
                i = j
                continue

        i += 1

    return techniques


def main():
    print("=" * 60)
    print("同步高级写作技法到向量库")
    print("=" * 60)

    # 读取技法文件
    print("\n[1] 读取技法文件...")
    content = open(TECHNIQUE_FILE, encoding="utf-8").read()
    techniques = parse_techniques(content)
    print(f"    解析到 {len(techniques)} 种技法")

    # 维度映射 (保留"维度"后缀以匹配技能期望)
    dimension_map = {
        "世界观维度": "世界观维度",
        "剧情维度": "剧情维度",
        "人物维度": "人物维度",
        "战斗维度": "战斗冲突维度",
        "氛围维度": "氛围意境维度",
        "情感维度": "情感维度",
        "叙事维度": "叙事维度",
    }

    # 连接Qdrant
    print("\n[2] 连接Qdrant...")
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        PointStruct,
        VectorParams,
        Distance,
        SparseVectorParams,
    )

    client = QdrantClient(url=get_qdrant_url())

    # 检查collection
    try:
        client.get_collection("writing_techniques_v2")
        print("    writing_techniques_v2 已存在")
    except:
        print("    创建 writing_techniques_v2...")
        client.create_collection(
            collection_name="writing_techniques_v2",
            vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams()},
        )

    # 加载模型
    print("\n[3] 加载BGE-M3模型...")
    from FlagEmbedding import BGEM3FlagModel
    from core.config_loader import get_device

    model_path = get_model_path()
    model = BGEM3FlagModel(model_path or "BAAI/bge-m3", use_fp16=True, device=get_device())
    print("    模型加载完成")

    # 同步技法
    print(f"\n[4] 同步技法到向量库...")

    for i, tech in enumerate(techniques):
        # 生成向量
        out = model.encode([tech["content"]], return_dense=True, return_sparse=True)

        # 维度映射
        dimension = dimension_map.get(tech["dimension"], tech["dimension"])

        # 创建点
        point = PointStruct(
            id=1000 + i,  # 使用1000+作为ID避免与现有技法冲突
            vector={
                "dense": out["dense_vecs"][0].tolist(),
                "sparse": {
                    "indices": list(out["lexical_weights"][0].keys()),
                    "values": list(out["lexical_weights"][0].values()),
                },
            },
            payload={
                "name": tech["name"],
                "dimension": dimension,
                "writer": "外部资源整合",
                "content": tech["content"][:3000],
                "word_count": len(tech["content"]),
                "source": "高级写作技法大全",
                "scenes": tech["scenes"],
                "principle": tech["principle"],
                "notes": tech["notes"],
            },
        )

        client.upsert("writing_techniques_v2", [point])

        if (i + 1) % 5 == 0:
            print(f"    已同步 {i + 1}/{len(techniques)}")

    print(f"\n[5] 验证...")
    info = client.get_collection("writing_techniques_v2")
    print(f"    writing_techniques_v2: {info.points_count:,} 条")

    print("\n" + "=" * 60)
    print("同步完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
