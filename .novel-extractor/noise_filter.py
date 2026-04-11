"""
噪音过滤脚本
=============

过滤已提取JSONL文件中的噪音数据：
- worldview_element: 对话词噪音（说道/笑道等）
- character_relation: 占位符噪音（~~~）
- 其他维度: 目录页噪音

使用方法:
    python noise_filter.py --dimension worldview_element
    python noise_filter.py --all
    python noise_filter.py --status
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
EXTRACTED_DIR = PROJECT_ROOT / ".novel-extractor" / "extracted"
OUTPUT_DIR = PROJECT_ROOT / ".novel-extractor" / "filtered"

# 噪音特征定义
NOISE_FEATURES = {
    "worldview_element": {
        # 对话词噪音（89%噪音来源）
        "dialogue_words": [
            "说道",
            "笑道",
            "问道",
            "答道",
            "叫道",
            "喊道",
            "嚷道",
            "惊道",
            "怒道",
            "冷道",
            "叹道",
            "喝道",
            "吼道",
            "骂道",
            "骂道",
            "哼道",
            "哼了一声",
            "冷笑道",
            "脱口道",
            "失声道",
            "沉声道",
            "轻声道",
        ],
        # 单字噪音
        "single_char": True,
        # 占位符噪音
        "placeholders": ["~~~", "---", "***"],
        # 目录页噪音
        "catalog_words": ["目录", "Content", "第1节", "第2节"],
        # 有效元素模式（反向过滤）
        "valid_patterns": [
            r"[\u4e00-\u9fa5]{2,4}(城|宗|门|派|山|谷|殿|宫|国|盟|府|岛|州|湾)$",
        ],
    },
    "character_relation": {
        "placeholders": ["~~~", "---", "***"],
        "single_char": True,
        # 有效关系需要两个不同的人物名
        "require_different_names": True,
    },
    "power_vocabulary": {
        # 过滤空词汇
        "min_length": 2,
        # 过滤纯数字
        "no_pure_numbers": True,
    },
    "dialogue_style": {
        # 有效数据，不需要过滤
        "skip": True,
    },
    "emotion_arc": {
        "skip": True,
    },
    "author_style": {
        "skip": True,
    },
    "foreshadow_pair": {
        "skip": True,
    },
    "power_cost": {
        "skip": True,
    },
}


def filter_worldview_element(item: Dict) -> Dict:
    """过滤世界观元素噪音"""
    features = NOISE_FEATURES["worldview_element"]
    element_name = item.get("element_name", "")

    # 空元素
    if not element_name or len(element_name) < 2:
        return {"is_noise": True, "reason": "too_short"}

    # 对话词噪音检测
    for word in features["dialogue_words"]:
        if element_name == word or word in element_name:
            return {"is_noise": True, "reason": f"dialogue_word:{word}"}

    # 占位符噪音
    for placeholder in features["placeholders"]:
        if placeholder in element_name:
            return {"is_noise": True, "reason": f"placeholder:{placeholder}"}

    # 目录页噪音
    for catalog in features["catalog_words"]:
        if catalog in element_name:
            return {"is_noise": True, "reason": f"catalog:{catalog}"}

    # 有效模式检测
    valid = False
    for pattern in features["valid_patterns"]:
        if re.match(pattern, element_name):
            valid = True
            break

    # 不是有效模式，可能是噪音
    if not valid:
        # 检查是否是常见人名（可能是误提取）
        if len(element_name) == 2 and not re.search(
            r"(城|宗|门|山|谷|殿|宫)", element_name
        ):
            return {"is_noise": True, "reason": "invalid_pattern"}

    return {"is_noise": False, "reason": "valid"}


def filter_character_relation(item: Dict) -> Dict:
    """过滤人物关系噪音"""
    features = NOISE_FEATURES["character_relation"]

    char1 = item.get("character1", "")
    char2 = item.get("character2", "")

    # 空人物名
    if not char1 or not char2:
        return {"is_noise": True, "reason": "empty_character"}

    # 占位符噪音
    for placeholder in features["placeholders"]:
        if placeholder in char1 or placeholder in char2:
            return {"is_noise": True, "reason": f"placeholder:{placeholder}"}

    # 单字人物名（通常是噪音）
    if len(char1) < 2 or len(char2) < 2:
        return {"is_noise": True, "reason": "too_short"}

    # 两个相同人物名
    if char1 == char2 and features["require_different_names"]:
        return {"is_noise": True, "reason": "same_character"}

    return {"is_noise": False, "reason": "valid"}


def filter_generic(item: Dict, dimension: str) -> Dict:
    """通用噪音过滤"""
    features = NOISE_FEATURES.get(dimension, {})

    if features.get("skip"):
        return {"is_noise": False, "reason": "skip_filter"}

    # 获取主要内容字段
    content_fields = ["element_name", "term", "vocabulary", "content", "name"]
    content = ""
    for field in content_fields:
        if field in item:
            content = item[field]
            break

    # 空内容
    if not content:
        return {"is_noise": True, "reason": "empty_content"}

    # 最小长度检查
    min_length = features.get("min_length", 0)
    if min_length > 0 and len(content) < min_length:
        return {"is_noise": True, "reason": "too_short"}

    # 纯数字检查
    if features.get("no_pure_numbers") and content.isdigit():
        return {"is_noise": True, "reason": "pure_number"}

    return {"is_noise": False, "reason": "valid"}


def filter_dimension(dimension: str) -> Dict:
    """过滤单个维度的噪音"""
    input_file = EXTRACTED_DIR / dimension / f"{dimension}_items.jsonl"

    if not input_file.exists():
        return {"status": "error", "reason": f"file_not_found: {input_file}"}

    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{dimension}_filtered.jsonl"

    # 选择过滤函数
    filter_funcs = {
        "worldview_element": filter_worldview_element,
        "character_relation": filter_character_relation,
    }
    filter_func = filter_funcs.get(dimension, lambda x: filter_generic(x, dimension))

    # 统计
    stats = {
        "total": 0,
        "valid": 0,
        "noise": 0,
        "noise_reasons": {},
    }

    # 过滤噪音
    valid_items = []

    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            stats["total"] += 1
            try:
                item = json.loads(line.strip())
                result = filter_func(item)

                if result["is_noise"]:
                    stats["noise"] += 1
                    reason = result["reason"]
                    stats["noise_reasons"][reason] = (
                        stats["noise_reasons"].get(reason, 0) + 1
                    )
                else:
                    stats["valid"] += 1
                    valid_items.append(item)
            except Exception as e:
                stats["noise"] += 1
                stats["noise_reasons"]["parse_error"] = (
                    stats["noise_reasons"].get("parse_error", 0) + 1
                )

    # 写入过滤后的数据
    with open(output_file, "w", encoding="utf-8") as f:
        for item in valid_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 计算噪音比例
    noise_ratio = stats["noise"] / stats["total"] if stats["total"] > 0 else 0
    stats["noise_ratio"] = round(noise_ratio, 4)
    stats["input_file"] = str(input_file)
    stats["output_file"] = str(output_file)

    return {"status": "success", "stats": stats}


def filter_all() -> Dict:
    """过滤所有维度"""
    results = {}

    for dimension in NOISE_FEATURES.keys():
        print(f"[处理] {dimension}...")
        result = filter_dimension(dimension)
        results[dimension] = result

        if result["status"] == "success":
            stats = result["stats"]
            print(f"  - 总数: {stats['total']}")
            print(f"  - 有效: {stats['valid']}")
            print(f"  - 噪音: {stats['noise']} ({stats['noise_ratio']:.2%})")
        else:
            print(f"  - 错误: {result['reason']}")

    return results


def get_status() -> Dict:
    """获取噪音过滤状态"""
    status = {}

    for dimension in NOISE_FEATURES.keys():
        input_file = EXTRACTED_DIR / dimension / f"{dimension}_items.jsonl"
        output_file = OUTPUT_DIR / f"{dimension}_filtered.jsonl"

        if input_file.exists():
            # 统计输入文件
            with open(input_file, "r", encoding="utf-8") as f:
                input_count = sum(1 for _ in f)

            status[dimension] = {
                "input_exists": True,
                "input_count": input_count,
                "filtered_exists": output_file.exists(),
                "filtered_count": sum(
                    1 for _ in open(output_file, "r", encoding="utf-8")
                )
                if output_file.exists()
                else 0,
            }
        else:
            status[dimension] = {"input_exists": False}

    return status


def print_status():
    """打印状态"""
    status = get_status()

    print("=" * 60)
    print("噪音过滤状态")
    print("=" * 60)

    for dimension, info in status.items():
        print(f"\n{dimension}:")
        if info["input_exists"]:
            print(f"  - 输入文件: {info['input_count']} 条")
            if info["filtered_exists"]:
                print(f"  - 过滤后: {info['filtered_count']} 条")
                reduction = info["input_count"] - info["filtered_count"]
                ratio = (
                    reduction / info["input_count"] if info["input_count"] > 0 else 0
                )
                print(f"  - 减少: {reduction} 条 ({ratio:.2%})")
            else:
                print(f"  - 过滤后: 未处理")
        else:
            print(f"  - 输入文件: 不存在")

    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="噪音过滤脚本")
    parser.add_argument("--dimension", help="过滤指定维度")
    parser.add_argument("--all", action="store_true", help="过滤所有维度")
    parser.add_argument("--status", action="store_true", help="查看状态")

    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.all:
        print("=" * 60)
        print("开始噪音过滤")
        print("=" * 60)
        results = filter_all()

        # 汇总统计
        total_input = sum(
            r["stats"]["total"] for r in results.values() if r["status"] == "success"
        )
        total_valid = sum(
            r["stats"]["valid"] for r in results.values() if r["status"] == "success"
        )

        print()
        print("=" * 60)
        print("过滤完成")
        print("=" * 60)
        print(f"总输入: {total_input} 条")
        print(f"总有效: {total_valid} 条")
        print(f"总噪音: {total_input - total_valid} 条")
        print(f"噪音比例: {(total_input - total_valid) / total_input:.2%}")
    elif args.dimension:
        result = filter_dimension(args.dimension)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
