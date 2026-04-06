#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BGE-M3 可暂停迁移脚本

特性：
1. 进度保存到文件，支持断点续传
2. Ctrl+C 优雅暂停，下次继续
3. 实时进度显示

使用方法：
  # 首次执行或继续迁移
  python migrate_resumable.py

  # 强制重新开始
  python migrate_resumable.py --reset

  # 查看进度
  python migrate_resumable.py --status
"""

import os
import sys
import json
import re
import gc
import signal
import time
from pathlib import Path
from datetime import datetime

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / ".vectorstore"))

# 进度文件路径
PROGRESS_FILE = PROJECT_DIR / ".vectorstore" / "migration_progress.json"

# 全局暂停标志
paused = False


def signal_handler(signum, frame):
    """处理 Ctrl+C 信号"""
    global paused
    print("\n\n[!] 收到暂停信号，正在保存进度...")
    paused = True


signal.signal(signal.SIGINT, signal_handler)


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_progress():
    """加载迁移进度"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "novel_settings": {
            "completed": [],
            "last_id": -1,
            "total": 0,
            "status": "pending",
        },
        "writing_techniques": {
            "completed": [],
            "last_id": -1,
            "total": 0,
            "status": "pending",
        },
        "case_library": {
            "completed": [],
            "last_id": -1,
            "total": 0,
            "status": "pending",
        },
        "start_time": None,
        "last_update": None,
    }


def save_progress(progress):
    """保存迁移进度"""
    progress["last_update"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def reset_progress():
    """重置进度"""
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
    log("进度已重置")


def show_status():
    """显示当前进度"""
    progress = load_progress()

    print("\n" + "=" * 60)
    print("迁移进度状态")
    print("=" * 60)

    for name, info in progress.items():
        if name in ["start_time", "last_update"]:
            continue

        status = info.get("status", "pending")
        completed = len(info.get("completed", []))
        total = info.get("total", 0)
        last_id = info.get("last_id", -1)

        if total > 0:
            pct = (completed / total) * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"\n{name}:")
            print(f"  [{bar}] {pct:.1f}%")
            print(f"  已完成: {completed}/{total}")
            print(f"  最后ID: {last_id}")
            print(f"  状态: {status}")
        else:
            print(f"\n{name}: 未开始")

    print("\n" + "=" * 60)
    print(f"开始时间: {progress.get('start_time', 'N/A')}")
    print(f"最后更新: {progress.get('last_update', 'N/A')}")
    print("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="BGE-M3 可暂停迁移")
    parser.add_argument("--reset", action="store_true", help="重置进度")
    parser.add_argument("--status", action="store_true", help="查看进度")
    parser.add_argument(
        "--collection",
        choices=["novel", "technique", "case", "all"],
        default="all",
        help="指定迁移的库",
    )
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.reset:
        reset_progress()
        return

    log("=" * 60)
    log("BGE-M3 可暂停迁移")
    log("按 Ctrl+C 可随时暂停，下次执行自动继续")
    log("=" * 60)

    # 加载进度
    progress = load_progress()

    if progress.get("start_time") is None:
        progress["start_time"] = datetime.now().isoformat()

    # 加载模型
    log("[1/4] 加载模型...")
    from FlagEmbedding import BGEM3FlagModel

    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device="cpu")
    log("      完成")

    # 连接 Qdrant
    log("[2/4] 连接 Qdrant...")
    from qdrant_client import QdrantClient
    from qdrant_client import models
    from qdrant_client.http.models import PointStruct, SparseVector

    qdrant_path = PROJECT_DIR / ".vectorstore" / "qdrant"
    client = QdrantClient(path=str(qdrant_path))
    log(f"      完成")

    # 迁移各库
    total_synced = 0

    if args.collection in ["novel", "all"]:
        log("[3/4] 迁移小说设定...")
        count, progress = sync_novel_resumable(model, client, progress)
        total_synced += count
        log(f"      完成: {count} 条")
        if paused:
            save_progress(progress)
            log("\n[!] 已暂停，进度已保存。下次执行将自动继续。")
            return

    if args.collection in ["technique", "all"]:
        log("[4/4] 迁移创作技法...")
        count, progress = sync_techniques_resumable(model, client, progress)
        total_synced += count
        log(f"      完成: {count} 条")
        if paused:
            save_progress(progress)
            log("\n[!] 已暂停，进度已保存。下次执行将自动继续。")
            return

    if args.collection in ["case", "all"]:
        log("[5/4] 迁移案例库...")
        count, progress = sync_cases_resumable(model, client, progress)
        total_synced += count
        log(f"      完成: {count} 条")
        if paused:
            save_progress(progress)
            log("\n[!] 已暂停，进度已保存。下次执行将自动继续。")
            return

    # 清理进度文件
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()

    log("=" * 60)
    log(f"全部完成! 总计: {total_synced} 条")
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
                size=1024,
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM
                ),
                hnsw_config=models.HnswConfigDiff(m=0),
            ),
        },
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
        optimizers_config=models.OptimizersConfigDiff(indexing_threshold=10000),
    )


def sync_novel_resumable(model, client, progress):
    """可恢复的小说设定迁移"""
    global paused
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import PointStruct, SparseVector

    collection_name = COLLECTION_NAMES["novel_settings"]
    key = "novel_settings"

    # 读取数据
    kg_file = PROJECT_DIR / ".vectorstore" / "knowledge_graph.json"
    with open(kg_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = list(data.get("实体", {}).items())
    total = len(entities)

    # 初始化进度
    if progress[key]["total"] == 0:
        progress[key]["total"] = total
        progress[key]["status"] = "in_progress"
        create_collection_with_colbert(client, collection_name)

    last_id = progress[key]["last_id"]
    completed = progress[key]["completed"]

    log(f"      总数: {total}, 已完成: {len(completed)}, 从ID {last_id + 1} 继续")

    count = 0
    for i, (name, props) in enumerate(entities):
        # 跳过已完成的
        if i <= last_id:
            continue

        if paused:
            return count, progress

        # 显示进度
        if (i + 1) % 20 == 0 or i == total - 1:
            pct = (i + 1) / total * 100
            log(f"      进度: {i + 1}/{total} ({pct:.1f}%)")

        # 编码
        text = f"【{name}】类型:{props.get('类型', '')} 描述:{props.get('描述', '')}"
        output = model.encode(
            [text], return_dense=True, return_sparse=True, return_colbert_vecs=True
        )

        # 构建Point
        point = build_point(
            i,
            output,
            {
                "name": name,
                "type": props.get("类型", "未知"),
                "description": str(props.get("描述", ""))[:2000],
            },
        )

        # 上传
        client.upsert(collection_name=collection_name, points=[point])

        # 更新进度
        progress[key]["last_id"] = i
        progress[key]["completed"].append(i)
        count += 1

        # 定期保存进度
        if count % 50 == 0:
            save_progress(progress)
            gc.collect()

    progress[key]["status"] = "completed"
    save_progress(progress)
    return count, progress


def sync_techniques_resumable(model, client, progress):
    """可恢复的创作技法迁移"""
    global paused
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import PointStruct, SparseVector

    collection_name = COLLECTION_NAMES["writing_techniques"]
    key = "writing_techniques"

    techniques_dir = PROJECT_DIR / "创作技法"

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

    # 收集所有技法
    skip = ["README.md", "01-创作检查清单.md", "00-学习路径规划.md"]
    md_files = list(techniques_dir.rglob("*.md"))
    md_files = [f for f in md_files if f.name not in skip]

    # 收集所有技法条目
    all_techniques = []
    for md_file in md_files:
        dim = DIM_MAP.get(md_file.parent.name, "未知")
        writer = WRI_MAP.get(dim, "未知")
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
        for section in extract_sections(content):
            if len(section["content"]) >= 100:
                all_techniques.append(
                    {
                        "name": section["name"],
                        "dimension": dim,
                        "writer": writer,
                        "source_file": md_file.name,
                        "content": section["content"][:5000],
                    }
                )

    total = len(all_techniques)

    # 初始化进度
    if progress[key]["total"] == 0:
        progress[key]["total"] = total
        progress[key]["status"] = "in_progress"
        create_collection_with_colbert(client, collection_name)

    last_id = progress[key]["last_id"]

    log(
        f"      总数: {total}, 已完成: {last_id + 1 if last_id >= 0 else 0}, 从ID {last_id + 1} 继续"
    )

    count = 0
    for i, tech in enumerate(all_techniques):
        if i <= last_id:
            continue

        if paused:
            return count, progress

        if (i + 1) % 50 == 0 or i == total - 1:
            pct = (i + 1) / total * 100
            log(f"      进度: {i + 1}/{total} ({pct:.1f}%)")

        # 编码
        output = model.encode(
            [tech["content"][:500]],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=True,
        )

        # 构建Point
        point = build_point(
            i,
            output,
            {
                "name": tech["name"],
                "dimension": tech["dimension"],
                "writer": tech["writer"],
                "source_file": tech["source_file"],
                "content": tech["content"],
                "word_count": len(tech["content"]),
            },
        )

        client.upsert(collection_name=collection_name, points=[point])

        progress[key]["last_id"] = i
        count += 1

        if count % 30 == 0:
            save_progress(progress)
            gc.collect()

    progress[key]["status"] = "completed"
    save_progress(progress)
    return count, progress


def sync_cases_resumable(model, client, progress):
    """可恢复的案例库迁移"""
    global paused
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import PointStruct, SparseVector

    collection_name = COLLECTION_NAMES["case_library"]
    key = "case_library"

    cases_dir = PROJECT_DIR / ".case-library" / "cases"

    # 收集所有案例
    all_cases = []
    for scene_dir in cases_dir.iterdir():
        if not scene_dir.is_dir():
            continue
        scene_type = scene_dir.name
        for json_file in scene_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    case_data = json.load(f)
                parts = json_file.stem.split("_")
                case_data["scene_type"] = case_data.get("scene_type", scene_type)
                case_data["genre"] = case_data.get(
                    "genre", parts[1] if len(parts) >= 2 else "未知"
                )
                case_data["novel_name"] = case_data.get(
                    "novel_name", "_".join(parts[2:]) if len(parts) >= 3 else "未知"
                )
                all_cases.append(case_data)
            except:
                pass

    total = len(all_cases)

    # 初始化进度
    if progress[key]["total"] == 0:
        progress[key]["total"] = total
        progress[key]["status"] = "in_progress"
        create_collection_with_colbert(client, collection_name)

    last_id = progress[key]["last_id"]

    log(f"      总数: {total}, 已完成: {last_id + 1 if last_id >= 0 else 0}")
    log(f"      预计时间: ~{total * 0.5 / 60:.0f} 分钟")

    count = 0
    for i, case in enumerate(all_cases):
        if i <= last_id:
            continue

        if paused:
            return count, progress

        if (i + 1) % 500 == 0 or i == total - 1:
            pct = (i + 1) / total * 100
            eta = (total - i - 1) * 0.5 / 60
            log(f"      进度: {i + 1}/{total} ({pct:.1f}%) | 剩余约 {eta:.0f} 分钟")

        content = case.get("content", "")[:1000]
        if len(content) < 50:
            progress[key]["last_id"] = i
            continue

        # 编码
        output = model.encode(
            [content], return_dense=True, return_sparse=True, return_colbert_vecs=True
        )

        # 构建Point
        point = build_point(
            i,
            output,
            {
                "novel_name": case.get("novel_name", "未知"),
                "scene_type": case.get("scene_type", "未知"),
                "genre": case.get("genre", "未知"),
                "quality_score": case.get(
                    "quality_score", case.get("confidence", 0) * 10
                ),
                "word_count": case.get("word_count", len(case.get("content", ""))),
                "content": case.get("content", "")[:2000],
            },
        )

        client.upsert(collection_name=collection_name, points=[point])

        progress[key]["last_id"] = i
        count += 1

        if count % 100 == 0:
            save_progress(progress)
            gc.collect()

    progress[key]["status"] = "completed"
    save_progress(progress)
    return count, progress


def build_point(idx, output, payload):
    """构建Point"""
    from qdrant_client.http.models import PointStruct, SparseVector

    dense_vec = output["dense_vecs"][0].tolist()
    sparse_dict = output["lexical_weights"][0]
    colbert_vecs = output["colbert_vecs"][0]

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

    return PointStruct(
        id=idx,
        vector={
            "dense": dense_vec,
            "colbert": colbert_list,
            "sparse": SparseVector(
                indices=list(sparse_dict.keys()),
                values=list(sparse_dict.values()),
            ),
        },
        payload=payload,
    )


def extract_sections(content):
    """提取章节"""
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
