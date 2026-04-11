#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量转换第二批资源"""

import sys

sys.path.insert(0, r"D:\动画\众生界\.case-library\scripts")

from convert_format import FormatConverter
from pathlib import Path


def main():
    # 第二批资源路径
    base_path = Path(r"E:\小说资源\第二批资源")

    # 检查目录
    if not base_path.exists():
        print(f"错误: 目录不存在 {base_path}")
        return

    # 统计
    mobi_files = list(base_path.rglob("*.mobi"))
    print(f"找到 {len(mobi_files)} 个mobi文件")

    # 创建转换器
    converter = FormatConverter()

    # 先测试转换10个文件
    test_files = mobi_files[:10]
    print(f"\n开始测试转换 {len(test_files)} 个文件...")
    print("-" * 60)

    success = 0
    failed = 0

    for i, mobi_file in enumerate(test_files, 1):
        print(f"[{i}/{len(test_files)}] {mobi_file.name[:40]}")
        result = converter.convert_mobi_to_txt(mobi_file)
        if result:
            success += 1
            print(f"  -> OK: {result.name}")
        else:
            failed += 1
            print(f"  -> FAILED")

    print("\n" + "=" * 60)
    print(f"测试结果: 成功 {success}, 失败 {failed}")

    if success > 0:
        print(f"\n转换后的文件保存在: {converter.converted_dir}")


if __name__ == "__main__":
    main()
