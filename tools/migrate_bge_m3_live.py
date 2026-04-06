#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BGE-M3 混合检索迁移脚本 - 实时进度版
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

# 添加项目路径
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / ".vectorstore"))
sys.path.insert(0, str(PROJECT_DIR / "modules" / "knowledge_base"))

# 加载配置
from core.config_loader import get_qdrant_url

QDRANT_URL = get_qdrant_url()


def log(msg):
    """带时间戳的日志输出"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def main():
    log("=" * 60)
    log("BGE-M3 混合检索迁移 - 实时进度版")
    log("=" * 60)

    # 步骤1: 加载模型
    log("[1/5] 加载 BGE-M3 模型...")
    try:
        from FlagEmbedding import BGEM3FlagModel

        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device="cpu")
        log("      模型加载成功!")
    except Exception as e:
        log(f"      错误: {e}")
        return

    # 步骤2: 连接 Qdrant
    log("[2/5] 连接 Qdrant...")
    try:
        from qdrant_client import QdrantClient
        from qdrant_client import models
        from qdrant_client.http.models import PointStruct, SparseVector

        client = QdrantClient(url=QDRANT_URL)
        collections = client.get_collections()
        log(f"      已连接，当前 {len(collections.collections)} 个 Collection")
    except Exception as e:
        log(f"      错误: {e}")
        return

    # 步骤3: 同步小说设定
    log("[3/5] 同步小说设定...")
    try:
        count = sync_novel_settings(model, client)
        log(f"      完成: {count} 条")
    except Exception as e:
        log(f"      错误: {e}")
        import traceback

        traceback.print_exc()

    # 步骤4: 同步创作技法
    log("[4/5] 同步创作技法...")
    try:
        count = sync_techniques(model, client)
        log(f"      完成: {count} 条")
    except Exception as e:
        log(f"      错误: {e}")
        import traceback

        traceback.print_exc()

    # 步骤5: 验证检索
    log("[5/5] 验证检索...")
    try:
        validate_search(model, client)
        log("      验证完成")
    except Exception as e:
        log(f"      错误: {e}")

    log("=" * 60)
    log("迁移完成!")
    log("=" * 60)


def sync_novel_settings(model, client):
    """同步小说设定"""
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client import models
    from qdrant_client.http.models import PointStruct, SparseVector

    collection_name = COLLECTION_NAMES["novel_settings"]

    # 读取知识图谱
    kg_file = PROJECT_DIR / ".vectorstore" / "knowledge_graph.json"
    with open(kg_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data.get("实体", {})
    entity_list = list(entities.items())
    total = len(entity_list)
    log(f"      发现 {total} 个实体")

    # 创建 Collection
    create_hybrid_collection(client, collection_name)

    # 编码
    log(f"      编码中...")
    texts = [build_entity_text(name, props) for name, props in entity_list]
    output = model.encode(
        texts, return_dense=True, return_sparse=True, return_colbert_vecs=True
    )

    # 构建 Points
    log(f"      构建 Points...")
    points = []
    for i, ((name, props), idx) in enumerate(zip(entity_list, range(total))):
        if (i + 1) % 50 == 0:
            log(f"      处理进度: {i + 1}/{total}")

        dense_vec = output["dense_vecs"][i].tolist()
        sparse_dict = output["lexical_weights"][i]
        colbert_vecs = output["colbert_vecs"][i]

        sparse_indices = list(sparse_dict.keys())
        sparse_values = list(sparse_dict.values())

        if isinstance(colbert_vecs, list):
            colbert_list = [
                v.tolist() if hasattr(v, "tolist") else v for v in colbert_vecs
            ]
        else:
            colbert_list = (
                colbert_vecs.tolist()
                if hasattr(colbert_vecs, "tolist")
                else colbert_vecs
            )

        point = PointStruct(
            id=i,
            vector={
                "dense": dense_vec,
                "colbert": colbert_list,
                "sparse": SparseVector(indices=sparse_indices, values=sparse_values),
            },
            payload={
                "name": name,
                "type": props.get("类型", "未知"),
                "description": props.get("描述", "")[:2000]
                if props.get("描述")
                else "",
                "properties": json.dumps(props, ensure_ascii=False)[:8000],
                "source": "knowledge_graph.json",
            },
        )
        points.append(point)

    # 上传
    log(f"      上传到 Qdrant...")
    batch_size = 100
    for j in range(0, len(points), batch_size):
        batch = points[j : j + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
        log(f"      上传进度: {min(j + batch_size, len(points))}/{len(points)}")

    return len(points)


def sync_techniques(model, client):
    """同步创作技法"""
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import PointStruct, SparseVector

    collection_name = COLLECTION_NAMES["writing_techniques"]
    techniques_dir = PROJECT_DIR / "创作技法"

    # 收集技法
    skip_files = [
        "README.md",
        "01-创作检查清单.md",
        "00-学习路径规划.md",
        "创作技法速查表.md",
    ]
    md_files = [f for f in techniques_dir.rglob("*.md") if f.name not in skip_files]
    log(f"      发现 {len(md_files)} 个技法文件")

    # 创建 Collection
    create_hybrid_collection(client, collection_name)

    # 提取技法
    techniques = []
    DIMENSION_MAP = {
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
    WRITER_MAP = {
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

    for md_file in md_files:
        try:
            parent_dir = md_file.parent.name
            dimension = DIMENSION_MAP.get(parent_dir, "未知")
            writer = WRITER_MAP.get(dimension, "未知")

            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            sections = extract_sections(content)
            for section in sections:
                if len(section["content"]) >= 100:
                    techniques.append(
                        {
                            "name": section["name"],
                            "dimension": dimension,
                            "writer": writer,
                            "source_file": md_file.name,
                            "content": section["content"][:500],
                            "full_content": section["content"][:5000],
                        }
                    )
        except Exception:
            pass

    log(f"      提取技法条目: {len(techniques)} 条")

    if not techniques:
        return 0

    # 编码
    log(f"      编码中...")
    texts = [t["content"] for t in techniques]
    output = model.encode(
        texts, return_dense=True, return_sparse=True, return_colbert_vecs=True
    )

    # 构建 Points
    points = []
    for i, tech in enumerate(techniques):
        if (i + 1) % 100 == 0:
            log(f"      处理进度: {i + 1}/{len(techniques)}")

        dense_vec = output["dense_vecs"][i].tolist()
        sparse_dict = output["lexical_weights"][i]
        colbert_vecs = output["colbert_vecs"][i]

        sparse_indices = list(sparse_dict.keys())
        sparse_values = list(sparse_dict.values())

        if isinstance(colbert_vecs, list):
            colbert_list = [
                v.tolist() if hasattr(v, "tolist") else v for v in colbert_vecs
            ]
        else:
            colbert_list = (
                colbert_vecs.tolist()
                if hasattr(colbert_vecs, "tolist")
                else colbert_vecs
            )

        point = PointStruct(
            id=i,
            vector={
                "dense": dense_vec,
                "colbert": colbert_list,
                "sparse": SparseVector(indices=sparse_indices, values=sparse_values),
            },
            payload={
                "name": tech["name"],
                "dimension": tech["dimension"],
                "writer": tech["writer"],
                "source_file": tech["source_file"],
                "content": tech["full_content"],
                "word_count": len(tech["full_content"]),
            },
        )
        points.append(point)

    # 上传
    log(f"      上传到 Qdrant...")
    batch_size = 100
    for j in range(0, len(points), batch_size):
        batch = points[j : j + batch_size]
        client.upsert(collection_name=collection_name, points=batch)

    return len(points)


def create_hybrid_collection(client, collection_name):
    """创建混合检索 Collection"""
    from qdrant_client import models
    from bge_m3_config import DENSE_VECTOR_SIZE, COLBERT_VECTOR_SIZE

    # 删除旧 Collection
    collections = [c.name for c in client.get_collections().collections]
    if collection_name in collections:
        log(f"      删除旧 Collection: {collection_name}")
        client.delete_collection(collection_name=collection_name)

    # 创建新 Collection
    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": models.VectorParams(
                size=DENSE_VECTOR_SIZE, distance=models.Distance.COSINE
            ),
            "colbert": models.VectorParams(
                size=COLBERT_VECTOR_SIZE,
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM
                ),
                hnsw_config=models.HnswConfigDiff(m=0),
            ),
        },
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )
    log(f"      创建 Collection: {collection_name}")


def build_entity_text(name, props):
    """构建实体文本"""
    parts = [f"【{name}】", f"类型: {props.get('类型', '未知')}"]
    if props.get("描述"):
        parts.append(f"描述: {props['描述']}")
    for key, value in props.get("属性", {}).items():
        if value:
            parts.append(f"{key}: {str(value)[:500]}")
    return "\n".join(parts)


def extract_sections(content):
    """提取章节"""
    import re

    sections = []
    pattern = r"\n(?=## [一二三四五六七八九十]+、)"
    parts = re.split(pattern, content)
    for part in parts:
        if not part.strip():
            continue
        match = re.search(
            r"^## [一二三四五六七八九十]+、[^：]*：?(.+)$", part, re.MULTILINE
        )
        if match:
            sections.append({"name": match.group(1).strip(), "content": part})
        else:
            sub_parts = re.split(r"\n(?=### )", part)
            for sub in sub_parts:
                if not sub.strip():
                    continue
                sub_match = re.search(r"^### (.+)$", sub, re.MULTILINE)
                if sub_match:
                    sections.append(
                        {"name": sub_match.group(1).strip(), "content": sub}
                    )
    return sections


def validate_search(model, client):
    """验证检索"""
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import SparseVector

    collection_name = COLLECTION_NAMES["writing_techniques"]

    test_queries = ["战斗代价", "人物出场", "氛围渲染"]

    for query in test_queries:
        output = model.encode([query], return_dense=True, return_sparse=True)

        dense_vec = output["dense_vecs"][0].tolist()
        sparse_dict = output["lexical_weights"][0]

        results = client.query_points(
            collection_name=collection_name,
            query=dense_vec,
            using="dense",
            limit=3,
            with_payload=True,
        )

        if results.points:
            top = results.points[0]
            log(
                f"      查询 '{query}': Top-1 = {top.payload.get('name', 'N/A')} (score: {top.score:.4f})"
            )


if __name__ == "__main__":
    main()
