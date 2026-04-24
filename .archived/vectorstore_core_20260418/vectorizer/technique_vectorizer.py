#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技法笔记向量化脚本
将创作技法笔记分块、向量化并存入 ChromaDB

使用方法：
    python technique_vectorizer.py [--rebuild]

参数：
    --rebuild: 重建向量数据库（删除现有数据）
"""

import os
import re
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("请安装 chromadb: pip install chromadb")
    exit(1)

# 添加项目根目录到 sys.path
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import get_project_root, get_vectorstore_dir, get_techniques_dir

# 配置
TECHNIQUE_DIR = get_techniques_dir()
VECTORSTORE_DIR = get_vectorstore_dir()
COLLECTION_NAME = "novelist_techniques"

# 维度映射
DIMENSION_MAP = {
    "01-世界观维度": "世界观",
    "02-剧情维度": "剧情",
    "03-人物维度": "人物",
    "04-战斗冲突维度": "战斗",
    "05-氛围意境维度": "氛围",
    "06-叙事维度": "叙事",
    "07-主题维度": "主题",
    "08-情感维度": "情感",
    "09-读者体验维度": "读者体验",
    "10-元维度": "元维度",
}

# 作家映射
WRITER_MAP = {
    "世界观": "苍澜",
    "剧情": "玄一",
    "人物": "墨言",
    "战斗": "剑尘",
    "氛围": "云溪",
    "叙事": "玄一",
    "主题": "玄一",
    "情感": "墨言",
    "读者体验": "云溪",
    "元维度": "全部",
}


@dataclass
class TechniqueChunk:
    """技法分块"""

    id: str
    content: str
    metadata: Dict[str, Any]


def extract_technique_name(content: str) -> str:
    """从内容中提取技法名称"""
    # 尝试匹配标题
    h2_match = re.search(
        r"^## (二|三|四|五|六|七|八|九|十)、技法[^：]*：(.+)$", content, re.MULTILINE
    )
    if h2_match:
        return h2_match.group(2).strip()

    h3_match = re.search(r"^### 技法\d?：?(.+)$", content, re.MULTILINE)
    if h3_match:
        return h3_match.group(1).strip()

    h3_match2 = re.search(r"^#### 技法\d?：?(.+)$", content, re.MULTILINE)
    if h3_match2:
        return h3_match2.group(1).strip()

    return ""


def extract_keywords(content: str) -> List[str]:
    """从内容中提取关键词"""
    keywords = []

    # 提取加粗的关键词
    bold_matches = re.findall(r"\*\*([^*]+)\*\*", content)
    keywords.extend(bold_matches)

    # 提取表格中的关键词
    table_matches = re.findall(r"\| \*\*([^*]+)\*\* \|", content)
    keywords.extend(table_matches)

    # 去重并清理
    keywords = list(set(k.strip() for k in keywords if len(k.strip()) > 1))

    return keywords[:10]  # 最多10个关键词


def determine_applicable_scenarios(content: str, dimension: str) -> List[str]:
    """确定适用场景"""
    scenarios = []

    # 基于维度
    dimension_scenarios = {
        "世界观": ["世界观展开", "势力介绍", "设定说明"],
        "剧情": ["剧情推进", "伏笔埋设", "悬念设计", "章节结尾"],
        "人物": ["人物出场", "人物成长", "情感场景", "矛盾展示"],
        "战斗": ["战斗场景", "代价描写", "胜利场景"],
        "氛围": ["场景描写", "情感渲染", "意境营造", "章节润色"],
        "叙事": ["POV切换", "时间处理", "开篇设计"],
        "主题": ["主题深化", "困境设计"],
        "情感": ["情感场景", "克制表达"],
        "读者体验": ["沉浸感设计", "节奏控制"],
        "元维度": ["创作指导", "信念支撑"],
    }

    scenarios = dimension_scenarios.get(dimension, [])

    # 基于内容关键词
    if "战斗" in content or "代价" in content:
        scenarios.append("战斗场景")
    if "伏笔" in content or "悬念" in content:
        scenarios.append("伏笔埋设")
    if "人物" in content and ("矛盾" in content or "成长" in content):
        scenarios.append("人物成长")
    if "氛围" in content or "意境" in content:
        scenarios.append("氛围渲染")

    return list(set(scenarios))


def split_technique_file(file_path: Path) -> List[TechniqueChunk]:
    """将技法文件分割成多个技法单元"""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    chunks = []

    # 获取维度信息
    parent_dir = file_path.parent.name
    dimension = DIMENSION_MAP.get(parent_dir, "未知")
    writer = WRITER_MAP.get(dimension, "未知")

    # 按二级标题分割（## 二、技法一：XXX）
    # 每个 ## 开头到下一个 ## 之前的内容作为一个技法单元
    sections = re.split(r"\n(?=## [一二三四五六七八九十]、)", content)

    # 如果没有按二级标题分割成功，尝试按三级标题分割
    if len(sections) == 1:
        sections = re.split(r"\n(?=### 技法)", content)

    # 如果还是只有一个，按 ### 分割
    if len(sections) == 1:
        sections = re.split(r"\n(?=### )", content)

    chunk_id = 0
    for section in sections:
        if not section.strip():
            continue

        # 提取技法名称
        technique_name = extract_technique_name(section)
        if not technique_name:
            # 尝试从标题提取
            title_match = re.search(r"^##\s+(.+)$", section, re.MULTILINE)
            if title_match:
                technique_name = title_match.group(1).strip()
            else:
                technique_name = f"技法单元{chunk_id}"

        # 提取关键词
        keywords = extract_keywords(section)

        # 确定适用场景
        scenarios = determine_applicable_scenarios(section, dimension)

        # 确定适用阶段
        stages = []
        if any(kw in section for kw in ["检查", "检测", "评分", "标准"]):
            stages.append("Evaluator")
        stages.append("Generator")  # 所有技法都可用于Generator参考

        # 确定重要性
        priority = "P1"
        if "P0" in section or "核心" in section:
            priority = "P0"
        elif "P2" in section:
            priority = "P2"

        # 创建分块ID - 包含来源文件名确保唯一性
        file_prefix = file_path.stem  # 文件名不带扩展名
        chunk_id_str = f"{dimension}_{file_prefix}_{chunk_id}"
        # 清理ID，只保留字母、数字、下划线、中文
        chunk_id_str = re.sub(r"[^\w\u4e00-\u9fff]", "_", chunk_id_str)
        # 确保ID不以数字开头
        if chunk_id_str[0].isdigit():
            chunk_id_str = f"t_{chunk_id_str}"

        # ChromaDB不支持空列表，转换为字符串
        keywords_str = ",".join(keywords) if keywords else ""
        scenarios_str = ",".join(scenarios) if scenarios else ""
        stages_str = ",".join(stages) if stages else ""

        chunk = TechniqueChunk(
            id=chunk_id_str,
            content=section.strip(),
            metadata={
                "维度": dimension,
                "技法名称": technique_name,
                "来源文件": file_path.name,
                "来源路径": str(file_path.relative_to(TECHNIQUE_DIR.parent)),
                "关键词": keywords_str,
                "适用场景": scenarios_str,
                "适用阶段": stages_str,
                "适用作家": writer,
                "重要性": priority,
                "字数": len(section),
            },
        )
        chunks.append(chunk)
        chunk_id += 1

    return chunks


def process_all_techniques() -> List[TechniqueChunk]:
    """处理所有技法文件"""
    all_chunks = []
    seen_ids = set()
    duplicate_count = 0

    # 遍历所有md文件
    for md_file in TECHNIQUE_DIR.rglob("*.md"):
        # 跳过README和检查清单
        if md_file.name in ["README.md", "01-创作检查清单.md", "00-学习路径规划.md"]:
            continue

        print(f"处理: {md_file.relative_to(TECHNIQUE_DIR)}")
        chunks = split_technique_file(md_file)

        # 检查并处理重复ID
        for chunk in chunks:
            if chunk.id in seen_ids:
                # 添加后缀确保唯一
                original_id = chunk.id
                suffix = 1
                while chunk.id in seen_ids:
                    chunk.id = f"{original_id}_{suffix}"
                    suffix += 1
                duplicate_count += 1
            seen_ids.add(chunk.id)

        all_chunks.extend(chunks)
        print(f"  -> 生成 {len(chunks)} 个技法单元")

    if duplicate_count > 0:
        print(f"\n注意: 处理了 {duplicate_count} 个重复ID")

    return all_chunks


def create_vectorstore(chunks: List[TechniqueChunk], rebuild: bool = False):
    """创建向量数据库"""

    # 初始化 ChromaDB
    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))

    # 如果需要重建，先删除现有集合
    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"已删除现有集合: {COLLECTION_NAME}")
        except:
            pass

    # 创建或获取集合
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"description": "众生界创作技法向量数据库"}
    )

    # 批量添加
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]

        collection.add(
            ids=[chunk.id for chunk in batch],
            documents=[chunk.content for chunk in batch],
            metadatas=[chunk.metadata for chunk in batch],
        )

        print(f"已添加 {min(i + batch_size, len(chunks))}/{len(chunks)} 个技法单元")

    print(f"\n向量数据库创建完成！")
    print(f"路径: {VECTORSTORE_DIR}")
    print(f"集合: {COLLECTION_NAME}")
    print(f"总技法单元数: {len(chunks)}")

    return collection


def verify_collection():
    """验证集合"""
    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))

    try:
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        print(f"\n集合验证:")
        print(f"  名称: {COLLECTION_NAME}")
        print(f"  技法单元数: {count}")

        # 显示一个示例
        if count > 0:
            result = collection.get(limit=1)
            print(f"\n示例条目:")
            print(f"  ID: {result['ids'][0]}")
            print(f"  元数据: {result['metadatas'][0]}")
            print(f"  内容预览: {result['documents'][0][:100]}...")

        return True
    except Exception as e:
        print(f"验证失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="技法笔记向量化脚本")
    parser.add_argument("--rebuild", action="store_true", help="重建向量数据库")
    args = parser.parse_args()

    print("=" * 60)
    print("众生界创作技法向量化")
    print("=" * 60)

    # 处理所有技法文件
    print("\n[1/3] 处理技法文件...")
    chunks = process_all_techniques()
    print(f"\n共生成 {len(chunks)} 个技法单元")

    # 创建向量数据库
    print("\n[2/3] 创建向量数据库...")
    create_vectorstore(chunks, rebuild=args.rebuild)

    # 验证
    print("\n[3/3] 验证...")
    verify_collection()

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
