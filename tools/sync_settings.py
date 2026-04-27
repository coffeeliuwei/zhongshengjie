#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
同步小说设定到向量库
====================

将设定目录中的MD文件同步到Qdrant向量库，支持语义检索。

用法：
    python sync_settings.py --config config.json
    python sync_settings.py --path "D:/小说数据/设定"
"""

import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def parse_markdown_setting(file_path: Path) -> Dict[str, Any]:
    """解析设定MD文件"""
    content = file_path.read_text(encoding="utf-8")

    # 提取标题
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else file_path.stem

    # 提取章节/段落
    sections = []
    section_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)

    matches = list(section_pattern.finditer(content))
    for i, match in enumerate(matches):
        section_title = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start:end].strip()

        sections.append(
            {
                "title": section_title,
                "content": section_content,
                "word_count": len(section_content),
            }
        )

    # 提取关键词标签
    tags = []
    tag_pattern = re.compile(r"-\s+([^：:]+)[：:]\s+")
    for m in tag_pattern.finditer(content):
        potential_tag = m.group(1).strip()
        if len(potential_tag) <= 10:  # 只取短标签
            tags.append(potential_tag)

    # 自动分类
    category = classify_setting(file_path.name, title, content)

    return {
        "id": file_path.stem,
        "title": title,
        "file": str(file_path),
        "category": category,
        "content": content,
        "content_preview": content[:500],
        "sections": sections,
        "tags": tags,
        "word_count": len(content),
        "source": file_path.name,
        "updated": datetime.now().strftime("%Y-%m-%d"),
    }


def classify_setting(filename: str, title: str, content: str) -> str:
    """自动分类设定"""
    filename_lower = filename.lower()
    title_lower = title.lower()
    content_lower = content.lower()

    # 关键词分类
    categories = {
        "世界观": ["世界", "世界观", "力量体系", "势力", "规则", "体系"],
        "人物": ["人物", "角色", "主角", "配角", "人物谱", "性格"],
        "剧情": ["大纲", "剧情", "主线", "转折", "章节"],
        "地点": ["地点", "地点设定", "地图", "场景"],
        "物品": ["物品", "道具", "装备", "法宝"],
        "时间线": ["时间", "时间线", "历程"],
        "其他": [],
    }

    for category, keywords in categories.items():
        if category == "其他":
            continue
        for kw in keywords:
            if kw in filename_lower or kw in title_lower:
                return category
            if kw in content_lower[:500]:
                return category

    return "其他"


def load_config(config_path: Path) -> Dict[str, Any]:
    """加载配置文件"""
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def sync_settings_to_qdrant(
    settings: List[Dict[str, Any]],
    qdrant_url: str,
    collection_name: str,
    model_path: str = None,
    batch_size: int = 20,
):
    """同步设定到Qdrant"""
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        PointStruct,
        VectorParams,
        Distance,
        SparseVectorParams,
    )
    from FlagEmbedding import BGEM3FlagModel

    print(f"\n[连接Qdrant] {qdrant_url}")
    client = QdrantClient(url=qdrant_url)

    # 检查/创建collection
    try:
        client.get_collection(collection_name)
        print(f"    {collection_name} 已存在")
    except:
        print(f"    创建 {collection_name}...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams()},
        )

    # 加载模型
    print(f"\n[加载模型] BGE-M3")
    if model_path:
        model = BGEM3FlagModel(model_path, use_fp16=True)
    else:
        # 尝试从缓存加载
        import os

        cache_path = os.environ.get("BGE_M3_MODEL_PATH")
        if cache_path:
            model = BGEM3FlagModel(cache_path, use_fp16=True)
        else:
            model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
    print("    模型加载完成")

    # 分批同步
    print(f"\n[同步设定] {len(settings)} 条")

    for i in range(0, len(settings), batch_size):
        batch = settings[i : i + batch_size]

        # 批量编码
        texts = [s["content"] for s in batch]
        out = model.encode(texts, return_dense=True, return_sparse=True)

        # 创建点
        points = []
        for j, setting in enumerate(batch):
            point = PointStruct(
                id=int(hash(setting["id"]) % (2**31)),  # 生成唯一ID
                vector={
                    "dense": out["dense_vecs"][j].tolist(),
                    "sparse": {
                        "indices": list(out["lexical_weights"][j].keys()),
                        "values": list(out["lexical_weights"][j].values()),
                    },
                },
                payload={
                    "name": setting["title"],
                    "category": setting["category"],
                    "content": setting["content_preview"],
                    "word_count": setting["word_count"],
                    "file": setting["source"],
                    "tags": setting["tags"],
                    "sections_count": len(setting["sections"]),
                    "updated": setting["updated"],
                },
            )
            points.append(point)

        client.upsert(collection_name, points)
        print(f"    已同步 {i + len(batch)}/{len(settings)}")

    # 验证
    info = client.get_collection(collection_name)
    print(f"\n[完成] {collection_name}: {info.points_count:,} 条")


def main():
    parser = argparse.ArgumentParser(description="同步小说设定到向量库")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--path", help="设定目录路径（覆盖config）")
    parser.add_argument(
        "--collection", default="novel_settings_v2", help="collection名称"
    )
    parser.add_argument(
        "--qdrant-url",
        default=os.environ.get("QDRANT_URL"),
        help="Qdrant地址（默认从 QDRANT_URL 环境变量或 core.config_loader 获取）"
    )
    parser.add_argument("--model-path", help="BGE-M3模型路径")
    parser.add_argument("--batch-size", type=int, default=20, help="批处理大小")

    args = parser.parse_args()

    # 确定设定目录
    if args.path:
        settings_dir = Path(args.path)
    elif args.config:
        config = load_config(Path(args.config))
        base_path = Path(config.get("paths", {}).get("data_base_path", "."))
        settings_dir = base_path / config.get("paths", {}).get("settings", "设定")
    else:
        print("错误: 需要指定 --config 或 --path")
        return

    if not settings_dir.exists():
        print(f"错误: 设定目录不存在 - {settings_dir}")
        return

    print("=" * 60)
    print("同步小说设定到向量库")
    print("=" * 60)

    # 解析设定文件
    print(f"\n[解析设定] {settings_dir}")
    settings = []
    for md_file in settings_dir.glob("*.md"):
        try:
            setting = parse_markdown_setting(md_file)
            settings.append(setting)
            print(f"    ✓ {md_file.name} ({setting['category']})")
        except Exception as e:
            print(f"    ✗ {md_file.name}: {e}")

    if not settings:
        print("未找到设定文件")
        return

    print(f"\n总计: {len(settings)} 条设定")

    # 同步到Qdrant
    sync_settings_to_qdrant(
        settings=settings,
        qdrant_url=args.qdrant_url,
        collection_name=args.collection,
        model_path=args.model_path,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
