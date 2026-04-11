#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从总大纲提取完整角色设定并更新数据库
修复：角色内容太简短的问题
"""

import re
import sys
from pathlib import Path
from datetime import datetime
import hashlib

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
PROJECT_DIR = Path(r"D:\动画\众生界")
sys.path.insert(0, str(VECTORSTORE_DIR))

try:
    import chromadb
except ImportError:
    print("请安装 chromadb: pip install chromadb")
    exit(1)

# ============================================================
# 配置
# ============================================================

COLLECTION_NAME = "novelist_knowledge"

# 拼音映射
PINYIN_MAP = {
    "血牙": "xueya",
    "铁牙": "tieya",
    "林夕": "linxi",
    "艾琳娜": "elina",
    "塞巴斯蒂安": "sebastian",
    "陈傲天": "chenotian",
    "洛影": "luoying",
    "赵恒": "zhaoheng",
    "林正阳": "linzhengyang",
    "苏瑾": "sujin",
    "鬼影": "guiying",
    "白露": "bailu",
    "李道远": "lidaoyuan",
    "K-7": "k7",
    "幽灵": "youling",
    "零": "ling",
    "虎啸": "huxiao",
    "月牙": "yueya",
    "花姬": "huaji",
    "镜": "jing",
    "小蝶": "xiaodie",
}

# ============================================================
# 从总大纲提取角色详细设定
# ============================================================


def extract_character_details(outline_content: str) -> dict:
    """从总大纲提取角色详细设定"""

    characters = {}

    # 模式：### 角色名（身份）
    pattern = r"###\s+(.+?)（(.+?)）\s*\n\n\| 维度 \| 内容 \|\s*\n\|------\|------\|\s*\n((?:\| .+? \| .+? \|\s*\n)+)"

    for match in re.finditer(pattern, outline_content, re.DOTALL):
        name = match.group(1).strip()
        identity = match.group(2).strip()
        details_raw = match.group(3).strip()

        # 解析详情表格
        details = {}
        for line in details_raw.split("\n"):
            if line.startswith("|") and "维度" not in line and "------" not in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    key = parts[1].strip().replace("**", "")
                    value = parts[2].strip().replace("**", "")
                    details[key] = value

        # 构建完整内容
        content_parts = [f"# {name}", f"身份：{identity}"]

        if "核心矛盾" in details:
            content_parts.append(f"\n## 核心矛盾\n{details['核心矛盾']}")
        if "经历痛苦" in details:
            content_parts.append(f"\n## 经历痛苦\n{details['经历痛苦']}")
        if "彼岸" in details:
            content_parts.append(f"\n## 彼岸\n{details['彼岸']}")
        if "彼岸含义" in details:
            content_parts.append(f"\n## 彼岸含义\n{details['彼岸含义']}")
        if "结局形态" in details:
            content_parts.append(f"\n## 结局形态\n{details['结局形态']}")

        content = "\n".join(content_parts)

        characters[name] = {
            "identity": identity,
            "details": details,
            "content": content,
        }

    return characters


def extract_character_relationships(outline_content: str) -> dict:
    """提取角色关系"""

    relationships = {}

    # 模式：三角关系
    triangle_pattern = r"\*\*三角\*\*\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
    for match in re.finditer(triangle_pattern, outline_content):
        triangle = match.group(1).strip()
        theme = match.group(2).strip()
        status = match.group(3).strip()

        # 解析角色
        for name in re.findall(r"[\u4e00-\u9fa5]+", triangle):
            if name not in relationships:
                relationships[name] = []
            relationships[name].append(
                {"type": "三角关系", "content": f"{triangle}，{theme}，{status}"}
            )

    return relationships


def update_database(characters: dict):
    """更新数据库中的角色设定"""

    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    collection = client.get_collection(COLLECTION_NAME)

    updated = 0
    created = 0

    now = datetime.now().isoformat()

    for name, data in characters.items():
        char_id = f"char_{PINYIN_MAP.get(name, name.lower())}"

        # 检查是否已存在
        existing = collection.get(ids=[char_id])

        if existing["ids"]:
            # 更新
            collection.update(
                ids=[char_id],
                documents=[data["content"]],
                metadatas=[
                    {
                        "类型": "character",
                        "名称": name,
                        "身份": data["identity"],
                        "来源文件": "总大纲.md",
                        "来源章节": "角色详细设定",
                        "更新时间": now,
                    }
                ],
            )
            updated += 1
            print(f"  更新: {name} ({len(data['content'])} 字符)")
        else:
            # 新建
            collection.add(
                ids=[char_id],
                documents=[data["content"]],
                metadatas=[
                    {
                        "类型": "character",
                        "名称": name,
                        "身份": data["identity"],
                        "来源文件": "总大纲.md",
                        "来源章节": "角色详细设定",
                    }
                ],
            )
            created += 1
            print(f"  新建: {name} ({len(data['content'])} 字符)")

    return updated, created


def main():
    print("=" * 70)
    print("从总大纲提取完整角色设定")
    print("=" * 70)

    # 读取总大纲
    outline_file = PROJECT_DIR / "总大纲.md"
    outline_content = outline_file.read_text(encoding="utf-8")

    print(f"\n总大纲大小: {len(outline_content)} 字符")

    # 提取角色详细设定
    print("\n[步骤1] 提取角色详细设定...")
    characters = extract_character_details(outline_content)
    print(f"  找到 {len(characters)} 个角色的详细设定")

    # 显示提取的角色
    for name, data in characters.items():
        print(f"    - {name}: {len(data['content'])} 字符")

    # 更新数据库
    print("\n[步骤2] 更新数据库...")
    updated, created = update_database(characters)

    print(f"\n完成: 更新 {updated} 条, 新建 {created} 条")

    # 验证
    print("\n[步骤3] 验证更新结果...")
    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    collection = client.get_collection(COLLECTION_NAME)

    # 检查血牙
    test_names = ["血牙", "林夕", "虎啸"]
    for name in test_names:
        char_id = f"char_{PINYIN_MAP.get(name, name.lower())}"
        result = collection.get(ids=[char_id])
        if result["ids"]:
            content = result["documents"][0]
            print(f"\n  {name}:")
            print(f"    ID: {char_id}")
            print(f"    内容长度: {len(content)} 字符")
            print(f"    内容预览: {content[:200]}...")
        else:
            print(f"  {name}: 未找到")


if __name__ == "__main__":
    main()
