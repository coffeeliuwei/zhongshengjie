#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
司法案例自动过滤器
==================

读取 scrape_thepaper.py 爬取的文章，按关键词打分，自动分类：
  - 高分（≥6）→ reviewed/    （犯罪/司法内容，可入库）
  - 中分（3-5）→ uncertain/   （边缘内容，可人工复查）
  - 低分（<3） → rejected/    （无关内容，直接丢弃）

用法：
    python tools/filter_judicial_cases.py               # 处理默认目录
    python tools/filter_judicial_cases.py --dry-run     # 只打印不移动
    python tools/filter_judicial_cases.py --threshold 5 # 调整保留阈值
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from core.config_loader import get_judicial_cases_dir
    BASE_DIR = get_judicial_cases_dir()
except Exception:
    BASE_DIR = Path("E:/司法案例")

# ── 关键词评分规则 ────────────────────────────────────────────────────────────

# 强正向：每命中一词 +3（确定是案件内容）
STRONG_POSITIVE = [
    "杀人", "凶杀", "命案", "故意伤害",
    "强奸", "性侵", "猥亵",
    "抢劫", "绑架", "拘禁",
    "诈骗", "电信诈骗", "网络诈骗",
    "盗窃", "入室", "入户",
    "毒品", "贩毒", "走私",
    "黑社会", "恶势力", "黑恶",
    "死刑", "无期徒刑", "有期徒刑",
    "被告人", "公诉人", "辩护人",
    "庭审", "当庭", "宣判",
    "冤案", "错案", "平反昭雪",
    "在逃", "通缉", "潜逃",
    "嫌疑人落网", "嫌犯", "主犯", "从犯",
    "受害者", "被害人", "遇难",
]

# 弱正向：每命中一词 +1
WEAK_POSITIVE = [
    "刑事", "案件", "案情", "罪", "审判", "判决",
    "法院", "检察院", "警方", "公安",
    "侦查", "破案", "立案", "结案",
    "拘留", "逮捕", "羁押", "取保候审",
    "被告", "原告", "起诉", "上诉",
    "量刑", "定罪", "无罪",
    "证据", "证人", "口供", "作案",
    "警察", "刑警", "法官", "检察官",
    "犯罪", "违法", "非法",
    "受害", "伤亡", "死亡",
    "事发", "现场", "行凶",
]

# 强负向：命中则 -4（明确无关）
STRONG_NEGATIVE = [
    "股票", "A股", "上证", "深证", "创业板", "基金",
    "GDP", "CPI", "PMI", "汇率", "外汇", "美元",
    "乒乓球", "篮球", "足球", "羽毛球", "世锦赛", "奥运",
    "高考", "考研", "大学", "教育", "课程",
    "演唱会", "明星", "娱乐",
    "产品召回", "质量投诉",
    "疫情", "新冠", "病毒",
]

# ── 评分函数 ──────────────────────────────────────────────────────────────────

def score_article(text: str) -> tuple[int, list[str], list[str]]:
    """
    返回 (分数, 命中的正向词, 命中的负向词)
    """
    hit_pos = []
    hit_neg = []
    score = 0

    for kw in STRONG_POSITIVE:
        count = text.count(kw)
        if count > 0:
            score += min(count, 3) * 3  # 单词最多贡献 9 分，防止堆砌
            hit_pos.append(f"{kw}×{count}")

    for kw in WEAK_POSITIVE:
        count = text.count(kw)
        if count > 0:
            score += min(count, 5)
            hit_pos.append(f"{kw}×{count}")

    for kw in STRONG_NEGATIVE:
        count = text.count(kw)
        if count > 0:
            score -= count * 4
            hit_neg.append(f"{kw}×{count}")

    return score, hit_pos, hit_neg


def parse_article(filepath: Path) -> dict:
    text = filepath.read_text(encoding="utf-8", errors="replace")
    meta = {}
    content = text

    if "===CONTENT===" in text:
        parts = text.split("===CONTENT===", 1)
        meta_block = parts[0]
        content = parts[1].strip()
        for line in meta_block.splitlines():
            if ": " in line and not line.startswith("==="):
                key, val = line.split(": ", 1)
                meta[key.strip()] = val.strip()

    return {
        "filepath": filepath,
        "title": meta.get("标题", filepath.stem),
        "url": meta.get("URL", ""),
        "channel": meta.get("栏目", ""),
        "content": content,
        "full_text": text,
    }


# ── 主流程 ───────────────────────────────────────────────────────────────────

def run(base_dir: Path, threshold_keep: int, threshold_uncertain: int, dry_run: bool):
    # 扫描所有子来源目录（thepaper/ spp/ 等）
    src_dir = base_dir
    reviewed_dir = base_dir / "reviewed"
    uncertain_dir = base_dir / "uncertain"
    rejected_dir = base_dir / "rejected"

    if not dry_run:
        for d in [reviewed_dir, uncertain_dir, rejected_dir]:
            d.mkdir(parents=True, exist_ok=True)

    files = list(src_dir.rglob("*.txt"))
    # 跳过进度文件
    files = [f for f in files if not f.name.startswith(".")]

    print(f"[i] 共 {len(files)} 篇待过滤\n")
    print(f"{'分数':>5}  {'类别':^6}  标题")
    print("-" * 70)

    stats = {"reviewed": 0, "uncertain": 0, "rejected": 0}
    results = []

    for f in sorted(files):
        art = parse_article(f)
        score, hits_pos, hits_neg = score_article(art["full_text"])

        if score >= threshold_keep:
            category = "保留"
            dest_dir = reviewed_dir
            stats["reviewed"] += 1
        elif score >= threshold_uncertain:
            category = "待查"
            dest_dir = uncertain_dir
            stats["uncertain"] += 1
        else:
            category = "丢弃"
            dest_dir = rejected_dir
            stats["rejected"] += 1

        title_short = art["title"][:45].encode('gbk', errors='replace').decode('gbk')
        print(f"{score:>5}  [{category}]  {title_short}")
        if hits_pos:
            print(f"       命中: {', '.join(hits_pos[:6])}")
        if hits_neg:
            print(f"       排除: {', '.join(hits_neg[:4])}")

        results.append({
            "score": score,
            "category": category,
            "title": art["title"],
            "url": art["url"],
            "file": str(f),
        })

        if not dry_run:
            dest = dest_dir / f.name
            if not dest.exists():
                shutil.move(str(f), str(dest))

    print("\n" + "=" * 70)
    print(f"[完成] 保留: {stats['reviewed']}  待查: {stats['uncertain']}  丢弃: {stats['rejected']}")
    print(f"  保留目录: {reviewed_dir}")
    print(f"  待查目录: {uncertain_dir}")
    print(f"  丢弃目录: {rejected_dir}")

    # 保存分类报告
    if not dry_run:
        report_path = base_dir / "filter_report.json"
        report_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"  分类报告: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="司法案例自动过滤器")
    parser.add_argument("--dir", default=str(BASE_DIR), help="司法案例根目录")
    parser.add_argument("--threshold", type=int, default=6, help="保留阈值（默认6）")
    parser.add_argument("--uncertain", type=int, default=3, help="待查阈值（默认3）")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不移动文件")
    args = parser.parse_args()

    run(
        base_dir=Path(args.dir),
        threshold_keep=args.threshold,
        threshold_uncertain=args.uncertain,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
