#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二批资源完整批量转换脚本
转换所有2,280个mobi文件到txt格式
"""

import sys

sys.path.insert(0, r"D:\动画\众生界\.case-library\scripts")

from convert_format import FormatConverter
from pathlib import Path
import time


def main():
    base_path = Path(r"E:\小说资源\第二批资源")

    if not base_path.exists():
        print(f"错误: 目录不存在 {base_path}")
        return

    # 统计
    mobi_files = list(base_path.rglob("*.mobi"))
    total = len(mobi_files)
    print(f"找到 {total} 个mobi文件")

    # 创建转换器
    converter = FormatConverter()

    # 已转换的文件（检查converted目录）
    converted_dir = converter.converted_dir
    existing_txts = set(f.stem for f in converted_dir.glob("*.txt"))

    print(f"已转换文件数: {len(existing_txts)}")

    # 过滤已转换的文件
    to_convert = [f for f in mobi_files if f.stem not in existing_txts]
    print(f"待转换文件数: {len(to_convert)}")

    if not to_convert:
        print("所有文件已转换完成!")
        return

    print(f"\n开始批量转换...")
    print(f"预计耗时: {len(to_convert) * 0.3 / 60:.1f} 分钟")
    print("=" * 60)

    start_time = time.time()
    success = 0
    failed = 0

    for i, mobi_file in enumerate(to_convert, 1):
        # 进度显示
        elapsed = time.time() - start_time
        if i > 1:
            avg_time = elapsed / (i - 1)
            remaining = (len(to_convert) - i + 1) * avg_time
            eta = f"ETA: {remaining / 60:.1f}分钟"
        else:
            eta = "ETA: 计算中..."

        print(
            f"\r[{i}/{len(to_convert)}] {mobi_file.name[:35]:<35} {eta}",
            end="",
            flush=True,
        )

        result = converter.convert_mobi_to_txt(mobi_file)
        if result:
            success += 1
        else:
            failed += 1

    elapsed = time.time() - start_time

    print(f"\n\n" + "=" * 60)
    print("转换完成!")
    print("=" * 60)
    print(f"总文件数: {len(to_convert)}")
    print(f"成功: {success}")
    print(f"失败: {failed}")
    print(f"耗时: {elapsed / 60:.1f} 分钟")
    print(f"转换后文件保存在: {converted_dir}")


if __name__ == "__main__":
    main()
