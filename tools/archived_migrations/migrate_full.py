#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BGE-M3 完整迁移脚本 - 三向量存储版
分批流式处理，避免内存溢出

策略：
1. 逐条编码，立即上传
2. 不在内存中累积向量
3. 小批次上传到Qdrant
"""

import os
import sys
import json
import re
import gc
from pathlib import Path
from datetime import datetime

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / ".vectorstore"))


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def main():
    log("=" * 60)
    log("BGE-M3 完整迁移 - Dense + Sparse + ColBERT")
    log("=" * 60)

    # 加载模型
    log("[1/3] 加载模型...")
    from FlagEmbedding import BGEM3FlagModel

    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device="cpu")
    log("      完成")

    # 连接 Qdrant
    log("[2/3] 连接 Qdrant...")
    from qdrant_client import QdrantClient
    from qdrant_client import models
    from qdrant_client.http.models import PointStruct, SparseVector

    qdrant_path = PROJECT_DIR / ".vectorstore" / "qdrant"
    client = QdrantClient(path=str(qdrant_path))
    log(f"      本地存储: {qdrant_path}")

    # 同步数据
    log("[3/3] 同步数据...")

    novel_count = sync_novel_streaming(model, client)
    log(f"      小说设定: {novel_count} 条")

    gc.collect()  # 强制垃圾回收

    tech_count = sync_techniques_streaming(model, client)
    log(f"      创作技法: {tech_count} 条")

    log("=" * 60)
    log(f"完成! 总计: {novel_count + tech_count} 条")
    log("=" * 60)


def create_collection_with_colbert(client, name):
    """创建支持三向量的Collection"""
    from bge_m3_config import DENSE_VECTOR_SIZE
    from qdrant_client import models

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
            "colbert": models.VectorParams(
                size=1024,  # ColBERT 每个token的向量维度
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM
                ),
                # 关键：禁用HNSW索引节省内存
                hnsw_config=models.HnswConfigDiff(m=0),
            ),
        },
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
        # 优化配置
        optimizers_config=models.OptimizersConfigDiff(
            indexing_threshold=10000,
        ),
    )


def sync_novel_streaming(model, client):
    """流式同步小说设定 - 逐条处理"""
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import PointStruct, SparseVector

    collection_name = COLLECTION_NAMES["novel_settings"]

    # 读取知识图谱
    kg_file = PROJECT_DIR / ".vectorstore" / "knowledge_graph.json"
    with open(kg_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = list(data.get("实体", {}).items())
    total = len(entities)
    log(f"      小说设定: {total} 条")

    # 创建Collection
    create_collection_with_colbert(client, collection_name)

    # 逐条处理
    count = 0
    for i, (name, props) in enumerate(entities):
        # 显示进度
        if (i + 1) % 20 == 0:
            log(f"      进度: {i + 1}/{total}")

        # 编码单条
        text = build_entity_text(name, props)
        output = model.encode(
            [text],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=True,
        )

        # 提取向量
        dense_vec = output["dense_vecs"][0].tolist()
        sparse_dict = output["lexical_weights"][0]
        colbert_vecs = output["colbert_vecs"][0]

        # 处理ColBERT向量
        if isinstance(colbert_vecs, list):
            colbert_list = [
                v.tolist() if hasattr(v, "tolist") else list(v) for v in colbert_vecs
            ]
        else:
            colbert_list = (
                colbert_vecs.tolist()
                if hasattr(colbert_vecs, "tolist")
                else list(colbert_vecs)
            )

        # 构建Point
        point = PointStruct(
            id=i,
            vector={
                "dense": dense_vec,
                "colbert": colbert_list,
                "sparse": SparseVector(
                    indices=list(sparse_dict.keys()),
                    values=list(sparse_dict.values()),
                ),
            },
            payload={
                "name": name,
                "type": props.get("类型", "未知"),
                "description": str(props.get("描述", ""))[:2000],
                "properties": json.dumps(props, ensure_ascii=False)[:8000],
            },
        )

        # 立即上传（不累积）
        client.upsert(collection_name=collection_name, points=[point])
        count += 1

        # 每50条强制垃圾回收
        if (i + 1) % 50 == 0:
            gc.collect()

    return count


def sync_techniques_streaming(model, client):
    """流式同步创作技法 - 逐条处理"""
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import PointStruct, SparseVector

    collection_name = COLLECTION_NAMES["writing_techniques"]
    techniques_dir = PROJECT_DIR / "创作技法"

    # 维度映射
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

    # 收集技法
    skip = ["README.md", "01-创作检查清单.md", "00-学习路径规划.md"]
    md_files = [f for f in techniques_dir.rglob("*.md") if f.name not in skip]

    # 创建Collection
    create_collection_with_colbert(client, collection_name)

    # 逐文件处理
    count = 0
    for file_idx, md_file in enumerate(md_files):
        if (file_idx + 1) % 10 == 0:
            log(f"      文件进度: {file_idx + 1}/{len(md_files)}")

        try:
            dim = DIM_MAP.get(md_file.parent.name, "未知")
            writer = WRI_MAP.get(dim, "未知")

            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 提取章节
            sections = extract_sections(content)

            for section in sections:
                if len(section["content"]) < 100:
                    continue

                # 编码单条
                output = model.encode(
                    [section["content"][:500]],
                    return_dense=True,
                    return_sparse=True,
                    return_colbert_vecs=True,
                )

                # 提取向量
                dense_vec = output["dense_vecs"][0].tolist()
                sparse_dict = output["lexical_weights"][0]
                colbert_vecs = output["colbert_vecs"][0]

                if isinstance(colbert_vecs, list):
                    colbert_list = [
                        v.tolist() if hasattr(v, "tolist") else list(v)
                        for v in colbert_vecs
                    ]
                else:
                    colbert_list = (
                        colbert_vecs.tolist()
                        if hasattr(colbert_vecs, "tolist")
                        else list(colbert_vecs)
                    )

                # 构建Point
                point = PointStruct(
                    id=count,
                    vector={
                        "dense": dense_vec,
                        "colbert": colbert_list,
                        "sparse": SparseVector(
                            indices=list(sparse_dict.keys()),
                            values=list(sparse_dict.values()),
                        ),
                    },
                    payload={
                        "name": section["name"],
                        "dimension": dim,
                        "writer": writer,
                        "source_file": md_file.name,
                        "content": section["content"][:5000],
                        "word_count": len(section["content"]),
                    },
                )

                # 立即上传
                client.upsert(collection_name=collection_name, points=[point])
                count += 1

                # 每20条垃圾回收
                if count % 20 == 0:
                    gc.collect()

        except Exception as e:
            log(f"      错误 {md_file.name}: {e}")

    return count


def build_entity_text(name, props):
    """构建实体文本"""
    parts = [f"【{name}】", f"类型: {props.get('类型', '未知')}"]
    if props.get("描述"):
        parts.append(f"描述: {props['描述']}")
    for k, v in props.get("属性", {}).items():
        if v:
            parts.append(f"{k}: {str(v)[:300]}")
    return "\n".join(parts)


def extract_sections(content):
    """提取技法章节"""
    sections = []
    pattern = r"\n(?=## [一二三四五六七八九十]+、)"
    parts = re.split(pattern, content)

    for part in parts:
        if not part.strip():
            continue
        match = re.search(r"^## [一二三四五六七八九十]+、[^：]*：?(.+)$", part, re.M)
        if match:
            sections.append({"name": match.group(1).strip(), "content": part})
        else:
            sub_parts = re.split(r"\n(?=### )", part)
            for sub in sub_parts:
                if not sub.strip():
                    continue
                sub_match = re.search(r"^### (.+)$", sub, re.M)
                if sub_match:
                    sections.append(
                        {"name": sub_match.group(1).strip(), "content": sub}
                    )

    return sections


if __name__ == "__main__":
    main()
