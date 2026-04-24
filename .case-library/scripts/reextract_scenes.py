#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Targeted re-extraction for specific scene types
Bypasses the index and extracts only specified scenes

Usage:
    python reextract_scenes.py --scenes "打脸场景,高潮场景"
"""

import os
import sys
import json
import re
import uuid
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
from collections import defaultdict

# Windows encoding fix
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configuration
PROJECT_DIR = Path(__file__).parent.parent.parent
CASE_LIBRARY_DIR = PROJECT_DIR / ".case-library"
CASES_DIR = CASE_LIBRARY_DIR / "cases"
LOGS_DIR = CASE_LIBRARY_DIR / "logs"
STATS_FILE = CASE_LIBRARY_DIR / "unified_stats.json"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "reextract.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# Source directories - use converted txt files
CONVERTED_DIR = CASE_LIBRARY_DIR / "converted"
SOURCE_DIRS = [str(CONVERTED_DIR)]

# Scene keywords (from unified_case_extractor.py - expanded versions)
SCENE_KEYWORDS = {
    "打脸场景": [
        "嘲讽",
        "看不起",
        "废物",
        "实力证明",
        "震惊",
        "目瞪口呆",
        "打脸",
        "狠狠打脸",
        "实力打脸",
        "当场打脸",
        "垃圾",
        "蝼蚁",
        "废柴",
        "废物一个",
        "不自量力",
        "不知死活",
        "不知天高地厚",
        "狂妄",
        "找死",
        "低估",
        "小看",
        "轻视",
        "看走眼",
        "有眼无珠",
        "啪啪",
        "打脸啪啪响",
        "狠狠",
        "后悔",
        "肠子都悔青",
        "悔不该",
        "跪下",
        "跪地求饶",
        "跪地认错",
        "傻眼",
        "惊呆",
        "傻了",
        "不敢相信",
        "狠狠教训",
        "给点颜色",
        "让你看看",
        "嚣张",
        "跋扈",
        "目中无人",
        "狂妄自大",
        "反转",
        "逆转",
        "反杀",
        "逆风翻盘",
        "没想到",
        "怎么可能",
        "不可能",
        "出乎意料",
    ],
    "高潮场景": [
        "决战",
        "最终",
        "生死",
        "巅峰",
        "极限",
        "全力以赴",
        "最后一战",
        "终极一战",
        "生死之战",
        "决一死战",
        "爆发",
        "燃烧",
        "燃烧生命",
        "孤注一掷",
        "绝境",
        "绝地",
        "背水一战",
        "破釜沉舟",
        "气势",
        "威压",
        "气势冲天",
        "战意",
        "最强",
        "最强一击",
        "必杀",
        "底牌",
        "惊天动地",
        "震撼",
        "天地变色",
        "风云变色",
        "生死关头",
        "关键时刻",
        "千钧一发",
        "热血沸腾",
        "沸腾",
        "燃烧起来",
    ],
}

# Genre keywords
GENRE_KEYWORDS = {
    "玄幻奇幻": ["修炼", "境界", "灵气", "丹药", "功法", "元婴", "金丹", "渡劫"],
    "武侠仙侠": ["武功", "内力", "江湖", "门派", "剑法", "轻功", "侠客"],
    "现代都市": ["总裁", "豪门", "都市", "公司", "商战", "白领"],
    "历史军事": ["朝代", "皇帝", "将军", "战争", "谋略", "战场"],
    "科幻灵异": ["星际", "机甲", "末世", "异能", "丧尸", "科技"],
    "青春校园": ["校园", "学生", "青春", "恋爱", "考试", "同学"],
    "游戏竞技": ["游戏", "副本", "装备", "等级", "PK", "公会"],
    "女频言情": ["公主", "王爷", "皇后", "宫斗", "嫡女", "甜宠"],
}


def detect_genre(text: str, path: str) -> str:
    """Detect genre from path and content"""
    # Check path first
    path_lower = path.lower()
    for genre, keywords in GENRE_KEYWORDS.items():
        if genre in path:
            return genre

    # Check content keywords
    scores = defaultdict(int)
    for genre, keywords in GENRE_KEYWORDS.items():
        for kw in keywords:
            if kw in text[:5000]:
                scores[genre] += 1

    if scores:
        return max(scores, key=scores.get)
    return "玄幻奇幻"


def find_scenes(text: str, scene_types: List[str], min_length: int = 300) -> List[Dict]:
    """Find scenes matching specified types"""
    scenes = []

    # Split into segments
    segments = re.split(r"\n{2,}", text)

    current_pos = 0
    for segment in segments:
        segment = segment.strip()
        if len(segment) < min_length:
            current_pos += len(segment) + 2
            continue

        # Check for each scene type
        for scene_type in scene_types:
            keywords = SCENE_KEYWORDS.get(scene_type, [])
            matches = sum(1 for kw in keywords if kw in segment)

            if matches >= 2:  # At least 2 keyword matches
                scenes.append(
                    {
                        "text": segment,
                        "scene_type": scene_type,
                        "keyword_matches": matches,
                        "start": current_pos,
                        "end": current_pos + len(segment),
                    }
                )

        current_pos += len(segment) + 2

    return scenes


def process_novel(file_path: str, scene_types: List[str]) -> List[Dict]:
    """Process a single novel and extract specified scenes"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception as e:
        logger.warning(f"Failed to read {file_path}: {e}")
        return []

    if len(text) < 10000:  # Skip very short files
        return []

    # Detect genre
    genre = detect_genre(text, file_path)

    # Find scenes
    scenes = find_scenes(text, scene_types)

    # Create case objects
    cases = []
    novel_name = Path(file_path).stem

    for i, scene in enumerate(scenes):
        case_id = f"{novel_name}_{scene['scene_type']}_{i:04d}"
        case = {
            "case_id": case_id,
            "source": {
                "path": file_path,
                "novel_name": novel_name,
                "genre": genre,
            },
            "scene": {
                "type": scene["scene_type"],
                "word_count": len(scene["text"]),
                "keyword_matches": scene["keyword_matches"],
            },
            "content": scene["text"][:3000],  # Limit content length
            "extract_time": datetime.now().isoformat(),
        }
        cases.append(case)

    return cases


def save_cases(cases: List[Dict]) -> Dict[str, int]:
    """Save cases to appropriate directories"""
    saved_counts = defaultdict(int)

    for case in cases:
        scene_type = case["scene"]["type"]
        scene_dir = CASES_DIR / scene_type
        scene_dir.mkdir(parents=True, exist_ok=True)

        case_file = scene_dir / f"{case['case_id']}.json"
        with open(case_file, "w", encoding="utf-8") as f:
            json.dump(case, f, ensure_ascii=False, indent=2)

        saved_counts[scene_type] += 1

    return dict(saved_counts)


def scan_and_extract(scene_types: List[str], limit: int = None) -> Dict:
    """Scan all source directories and extract specified scenes"""
    total_cases = []
    processed = 0
    errors = 0

    all_files = []
    for source_dir in SOURCE_DIRS:
        if not os.path.exists(source_dir):
            logger.warning(f"Source directory not found: {source_dir}")
            continue
        for root, dirs, files in os.walk(source_dir):
            for f in files:
                if f.endswith((".txt",)):
                    all_files.append(os.path.join(root, f))

    logger.info(f"Found {len(all_files)} files to process")

    if limit:
        all_files = all_files[:limit]

    for i, file_path in enumerate(all_files):
        if (i + 1) % 100 == 0:
            logger.info(f"Progress: {i + 1}/{len(all_files)}")

        try:
            cases = process_novel(file_path, scene_types)
            if cases:
                total_cases.extend(cases)
            processed += 1
        except Exception as e:
            errors += 1
            logger.error(f"Error processing {file_path}: {e}")

    # Save all cases
    saved_counts = save_cases(total_cases)

    # Update stats
    update_stats(saved_counts)

    return {
        "processed": processed,
        "total_cases": len(total_cases),
        "by_scene": saved_counts,
        "errors": errors,
    }


def update_stats(new_counts: Dict[str, int]):
    """Update unified_stats.json"""
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            stats = json.load(f)
    except:
        stats = {"total_cases": 0, "by_scene": {}}

    # Update scene counts
    for scene_type, count in new_counts.items():
        if scene_type in stats["by_scene"]:
            stats["by_scene"][scene_type] += count
        else:
            stats["by_scene"][scene_type] = count

    # Recalculate total
    stats["total_cases"] = sum(stats["by_scene"].values())

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Targeted scene re-extraction")
    parser.add_argument(
        "--scenes",
        type=str,
        default="打脸场景,高潮场景",
        help="Comma-separated list of scene types to extract",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of files to process"
    )
    args = parser.parse_args()

    scene_types = [s.strip() for s in args.scenes.split(",")]
    logger.info(f"Starting re-extraction for scenes: {scene_types}")

    result = scan_and_extract(scene_types, args.limit)

    print("\n" + "=" * 60)
    print("Re-extraction Complete!")
    print("=" * 60)
    print(f"Processed files: {result['processed']}")
    print(f"Total cases: {result['total_cases']}")
    print(f"Errors: {result['errors']}")
    print("\nBy scene type:")
    for scene_type, count in result["by_scene"].items():
        print(f"  {scene_type}: {count}")


if __name__ == "__main__":
    main()
