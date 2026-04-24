#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例库存量去重清理工具
======================

对 .case-library/cases/ 下已有的 JSON 案例做 MinHash LSH 近重复检测，
把重复文件（及同名 .txt 兄弟）归档到 .case-library/cases/_duplicates_archive/。
构建的持久化 LSH 索引写入 .case-library/dedup_index.pkl，
供 tools/case_builder.py 增量提炼复用。

用法：
    python tools/dedup_case_library.py --dry-run     # 只报告，不移动文件
    python tools/dedup_case_library.py               # 实际归档
    python tools/dedup_case_library.py --archive-root /tmp/arch  # 自定义归档位置
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.dedup_utils import (  # noqa: E402
    compute_minhash, create_lsh, save_lsh,
)


DEFAULT_CASES_ROOT = Path(".case-library") / "cases"
DEFAULT_ARCHIVE_ROOT = Path(".case-library") / "cases" / "_duplicates_archive"
DEFAULT_INDEX_PATH = Path(".case-library") / "dedup_index.pkl"


def _read_content(json_file: Path) -> str:
    """从 JSON 文件读取 content；若 content 为空，回退读 .txt 兄弟。"""
    try:
        data = json.loads(json_file.read_text(encoding="utf-8"))
    except Exception:
        return ""
    content = data.get("content", "") or ""
    if not content:
        txt = json_file.with_suffix(".txt")
        if txt.exists():
            try:
                content = txt.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""
    return content


def _archive_file(json_file: Path, cases_root: Path, archive_root: Path) -> None:
    """把 json + 同名 txt 移动到归档目录，保留相对路径结构。"""
    rel = json_file.relative_to(cases_root)
    dest_json = archive_root / rel
    dest_json.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(json_file), str(dest_json))
    txt = json_file.with_suffix(".txt")
    if txt.exists():
        dest_txt = dest_json.with_suffix(".txt")
        shutil.move(str(txt), str(dest_txt))


def run_dedup(
    cases_root: Path,
    archive_root: Path,
    index_path: Path,
    dry_run: bool = False,
    progress_every: int = 10000,
) -> Dict[str, int]:
    """执行存量去重。返回统计 dict。"""
    cases_root = Path(cases_root)
    archive_root = Path(archive_root)
    index_path = Path(index_path)

    lsh, cache = create_lsh()

    # 扫描所有 JSON，排除归档目录本身
    all_json = [
        p for p in cases_root.rglob("*.json")
        if archive_root not in p.parents
    ]
    total = len(all_json)
    print(f"扫描到 {total:,} 个 JSON 案例文件")

    kept = 0
    duplicates = 0
    errors = 0

    for idx, json_file in enumerate(all_json, 1):
        try:
            content = _read_content(json_file)
            if not content or len(content) < 50:
                errors += 1
                continue

            m = compute_minhash(content)
            matches = lsh.query(m)
            if matches:
                duplicates += 1
                if not dry_run:
                    _archive_file(json_file, cases_root, archive_root)
            else:
                key = str(json_file.relative_to(cases_root))
                lsh.insert(key, m)
                cache[key] = m
                kept += 1
        except Exception as e:
            print(f"  [WARN] 处理失败: {json_file.name} - {e}")
            errors += 1

        if idx % progress_every == 0:
            print(
                f"  进度: {idx:,}/{total:,} | 保留 {kept:,} | 重复 {duplicates:,} | 错误 {errors:,}"
            )

    # 保存索引（dry-run 也保存，便于后续 case_builder 立即复用）
    save_lsh(lsh, cache, index_path)

    stats = {
        "total": total,
        "kept": kept,
        "duplicates": duplicates,
        "errors": errors,
    }
    print("=" * 60)
    print(f"去重完成 {'(DRY-RUN)' if dry_run else ''}")
    print(f"  总计: {stats['total']:,}")
    print(f"  保留: {stats['kept']:,}")
    print(f"  归档: {stats['duplicates']:,}")
    print(f"  错误: {stats['errors']:,}")
    print(f"  索引: {index_path}")
    return stats


def main():
    parser = argparse.ArgumentParser(description="案例库存量去重清理")
    parser.add_argument(
        "--cases-root", default=str(DEFAULT_CASES_ROOT),
        help=".case-library/cases/ 路径",
    )
    parser.add_argument(
        "--archive-root", default=str(DEFAULT_ARCHIVE_ROOT),
        help="归档目录",
    )
    parser.add_argument(
        "--index-path", default=str(DEFAULT_INDEX_PATH),
        help="持久化 LSH 索引路径",
    )
    parser.add_argument("--dry-run", action="store_true", help="只报告不移动")
    args = parser.parse_args()

    run_dedup(
        cases_root=Path(args.cases_root),
        archive_root=Path(args.archive_root),
        index_path=Path(args.index_path),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()