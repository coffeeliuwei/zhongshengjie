#!/usr/bin/env python3
"""批量转换所有题材目录"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from convert_format import FormatConverter


def main():
    converter = FormatConverter()

    # 待转换目录列表 - 剩余目录
    dirs_to_convert = [
        ("游戏竞技", "E:/小说资源/游戏竞技"),
        ("女频言情", "E:/小说资源/女频言情"),
    ]

    for name, path in dirs_to_convert:
        print(f"\n{'=' * 50}")
        print(f"开始转换: {name}")
        print(f"{'=' * 50}")

        if not Path(path).exists():
            print(f"目录不存在: {path}")
            continue

        result = converter.convert_directory(Path(path), ["epub"], True)
        print(f"\n{name} 完成: 成功 {result['success']}, 失败 {result['failed']}")


if __name__ == "__main__":
    main()
