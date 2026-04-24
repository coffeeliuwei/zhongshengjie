#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BGE-M3 轻量迁移脚本 - 仅 Dense + Sparse (无 ColBERT)
避免内存不足问题
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 设置离线模式
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / ".vectorstore"))
sys.path.insert(0, str(PROJECT_DIR / "modules" / "knowledge_base"))


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def main():
    log("=" * 60)
    log("BGE-M3 轻量迁移 (Dense + Sparse, 无 ColBERT)")
    log("=" * 60)

    # 加载模型
    log("[1/4] 加载 BGE-M3 模型...")
    from FlagEmbedding import BGEM3FlagModel

    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device="cpu")
    log("      完成!")

    # 连接 Qdrant
    log("[2/4] 连接 Qdrant...")
    from qdrant_client import QdrantClient
    from qdrant_client import models
    from qdrant_client.http.models import PointStruct, SparseVector

    # 使用本地存储避免网络问题
    qdrant_path = PROJECT_DIR / ".vectorstore" / "qdrant"
    client = QdrantClient(path=str(qdrant_path))
    log(f"      使用本地存储: {qdrant_path}")

    # 同步小说设定
    log("[3/4] 同步小说设定...")
    novel_count = sync_novel(model, client)
    log(f"      完成: {novel_count} 条")

    # 同步创作技法
    log("[4/4] 同步创作技法...")
    tech_count = sync_techniques(model, client)
    log(f"      完成: {tech_count} 条")

    log("=" * 60)
    log(f"迁移完成! 总计: {novel_count + tech_count} 条")
    log("=" * 60)


def sync_novel(model, client):
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import PointStruct, SparseVector

    collection_name = COLLECTION_NAMES["novel_settings"]

    # 读取数据
    kg_file = PROJECT_DIR / ".vectorstore" / "knowledge_graph.json"
    with open(kg_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    entities = list(data.get("实体", {}).items())
    total = len(entities)
    log(f"      {total} 个实体")

    # 创建 Collection (仅 Dense + Sparse)
    create_collection(client, collection_name)

    # 编码
    log(f"      编码...")
    texts = [
        f"【{n}】类型:{p.get('类型', '')} 描述:{p.get('描述', '')}" for n, p in entities
    ]
    output = model.encode(texts, return_dense=True, return_sparse=True)

    # 上传 (小批次)
    log(f"      上传...")
    for i, (name, props) in enumerate(entities):
        if (i + 1) % 50 == 0:
            log(f"      进度: {i + 1}/{total}")

        point = PointStruct(
            id=i,
            vector={
                "dense": output["dense_vecs"][i].tolist(),
                "sparse": SparseVector(
                    indices=list(output["lexical_weights"][i].keys()),
                    values=list(output["lexical_weights"][i].values()),
                ),
            },
            payload={
                "name": name,
                "type": props.get("类型", "未知"),
                "description": str(props.get("描述", ""))[:2000],
            },
        )
        client.upsert(collection_name=collection_name, points=[point])

    return total


def sync_techniques(model, client):
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import PointStruct, SparseVector

    collection_name = COLLECTION_NAMES["writing_techniques"]
    techniques_dir = PROJECT_DIR / "创作技法"

    # 收集技法
    skip = ["README.md", "01-创作检查清单.md", "00-学习路径规划.md"]
    md_files = [f for f in techniques_dir.rglob("*.md") if f.name not in skip]
    log(f"      {len(md_files)} 个文件")

    create_collection(client, collection_name)

    # 提取技法
    DIM_MAP = {
        "01-世界观维度": "世界观维度",
        "02-剧情维度": "剧情维度",
        "03-人物维度": "人物维度",
        "04-战斗冲突维度": "战斗冲突维度",
        "05-氛围意境维度": "氛围意境维度",
        "06-叙事维度": "叙事维度",
        "07-主题维度": "主题维度",
        "08-情感维度": "情感维度",
        "09-读者体验维度": "读者体验维度",
        "10-元维度": "元维度",
        "11-节奏维度": "节奏维度",
    }
    WRI_MAP = {
        "世界观维度": "苍澜",
        "剧情维度": "玄一",
        "人物维度": "墨言",
        "战斗冲突维度": "剑尘",
        "氛围意境维度": "云溪",
        "叙事维度": "玄一",
        "主题维度": "玄一",
        "情感维度": "墨言",
        "读者体验维度": "云溪",
        "元维度": "全部",
        "节奏维度": "玄一",
    }

    import re

    techniques = []
    for f in md_files:
        try:
            dim = DIM_MAP.get(f.parent.name, "未知")
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
            # 提取章节
            for m in re.finditer(
                r"^## [一二三四五六七八九十]+、[^：]*：?(.+)$", content, re.M
            ):
                start = m.start()
                # 找下一个章节或文件结尾
                next_m = re.search(
                    r"^## [一二三四五六七八九十]+、", content[start + 10 :], re.M
                )
                end = next_m.start() + start + 10 if next_m else len(content)
                tech_content = content[start:end]
                if len(tech_content) >= 100:
                    techniques.append(
                        {
                            "name": m.group(1).strip(),
                            "dimension": dim,
                            "writer": WRI_MAP.get(dim, "未知"),
                            "content": tech_content[:5000],
                        }
                    )
        except:
            pass

    total = len(techniques)
    log(f"      {total} 条技法")

    if not total:
        return 0

    # 编码
    log(f"      编码...")
    texts = [t["content"][:500] for t in techniques]
    output = model.encode(texts, return_dense=True, return_sparse=True)

    # 上传
    log(f"      上传...")
    for i, tech in enumerate(techniques):
        if (i + 1) % 100 == 0:
            log(f"      进度: {i + 1}/{total}")

        point = PointStruct(
            id=i,
            vector={
                "dense": output["dense_vecs"][i].tolist(),
                "sparse": SparseVector(
                    indices=list(output["lexical_weights"][i].keys()),
                    values=list(output["lexical_weights"][i].values()),
                ),
            },
            payload={
                "name": tech["name"],
                "dimension": tech["dimension"],
                "writer": tech["writer"],
                "content": tech["content"],
            },
        )
        client.upsert(collection_name=collection_name, points=[point])

    return total


def create_collection(client, name):
    from qdrant_client import models
    from bge_m3_config import DENSE_VECTOR_SIZE

    try:
        client.delete_collection(name)
    except:
        pass

    client.create_collection(
        collection_name=name,
        vectors_config={
            "dense": models.VectorParams(
                size=DENSE_VECTOR_SIZE, distance=models.Distance.COSINE
            ),
        },
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )
    log(f"      创建: {name}")


if __name__ == "__main__":
    main()
