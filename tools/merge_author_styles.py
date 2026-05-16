#!/usr/bin/env python3
"""
合并 docs/style_collection/ 下的所有 fragment YAML 文件
输出: docs/style_collection/author_styles.yaml
去重规则: 以 author id 为主键，保留第一次出现的条目
用法: python tools/merge_author_styles.py
"""
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("缺少 pyyaml，请先 pip install pyyaml")
    sys.exit(1)

REPO_ROOT = Path(__file__).parent.parent
COLLECTION_DIR = REPO_ROOT / "docs" / "style_collection"
OUTPUT_FILE = COLLECTION_DIR / "author_styles.yaml"

# 按顺序合并的 fragment 文件（顺序决定去重时哪个优先）
FRAGMENT_FILES = [
    "authors_jianchen.yaml",
    "authors_moyan_a.yaml",
    "authors_moyan_b.yaml",
    "authors_yunxi.yaml",
    "authors_xuanyi.yaml",
    "authors_canglan.yaml",
    "authors_cross.yaml",
]


def load_fragment(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data and "authors" in data:
        return data["authors"]
    return []


def merge_authors(fragment_files: list[Path]) -> list:
    seen_ids: set[str] = set()
    merged: list = []
    dup_log: list[tuple[str, str, str]] = []  # (id, name, file)

    for fpath in fragment_files:
        if not fpath.exists():
            print(f"  [SKIP] 文件不存在: {fpath.name}")
            continue
        authors = load_fragment(fpath)
        print(f"  [LOAD] {fpath.name}: {len(authors)} 位作家")
        for author in authors:
            aid = author.get("id", "")
            aname = author.get("name", "?")
            if aid in seen_ids:
                dup_log.append((aid, aname, fpath.name))
            else:
                seen_ids.add(aid)
                merged.append(author)

    if dup_log:
        print(f"\n  [重复去除 {len(dup_log)} 条]")
        for aid, aname, fname in dup_log:
            print(f"    - {aname} (id={aid}) in {fname}")

    return merged


def build_header(total: int) -> str:
    return f"""\
# 众生界 — 作家风格总档案
# 版本: 1.0.0
# 日期: 2026-05-16
# 总计: {total} 位作家
# 生成工具: tools/merge_author_styles.py
#
# 字段说明:
#   id               唯一标识（snake_case）
#   name             中文作家名
#   domains          适用写手列表: [剑尘|墨言|云溪|玄一|苍澜]
#   genres           代表风格/类型
#   signature_works  代表作
#   aws_profile      写作档案（8维）
#   behavior_constraints  行为约束（6-8条）
#   bad_habits       禁止习惯（3-4条）
#   ai_blacklist     AI套句黑名单（8-13条）
#   style_anchors    场景锚点（5-7条）
#
# 索引（按写手域）:
#   剑尘: jianchen.domains
#   墨言: moyan.domains
#   云溪: yunxi.domains
#   玄一: xuanyi.domains
#   苍澜: canglan.domains
"""


def main():
    print("=== 合并作家风格档案 ===\n")
    fragment_paths = [COLLECTION_DIR / f for f in FRAGMENT_FILES]
    merged = merge_authors(fragment_paths)

    output = {"authors": merged}
    header = build_header(len(merged))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n")
        yaml.dump(
            output,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=120,
        )

    size_kb = OUTPUT_FILE.stat().st_size // 1024
    print(f"\nOK 输出: {OUTPUT_FILE}")
    print(f"  总计: {len(merged)} 位作家  |  大小: {size_kb} KB")


if __name__ == "__main__":
    main()
