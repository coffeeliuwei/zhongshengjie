#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试mobi库解析能力"""

import mobi
from pathlib import Path

# 查找mobi文件
base_path = Path(r"E:\小说资源\第二批资源")
mobi_files = list(base_path.rglob("*.mobi"))[:3]

if not mobi_files:
    print("未找到mobi文件")
else:
    for mobi_file in mobi_files:
        print(f"\n{'=' * 50}")
        print(f"测试文件: {mobi_file.name}")
        print(f"{'=' * 50}")

        try:
            # 方式1: 使用mobi.read_mobi()
            with open(mobi_file, "rb") as f:
                data = f.read()

            result = mobi.read_mobi(data)
            print(f"解析结果类型: {type(result)}")
            print(f"结果属性: {dir(result)}")

            # 尝试获取HTML内容
            if hasattr(result, "html"):
                html = result.html
                print(f"\nHTML长度: {len(html)} 字符")
                print(f"前500字符:\n{html[:500]}")
            elif hasattr(result, "markup"):
                print(f"\nMarkup长度: {len(result.markup)} 字符")
                print(f"前500字符:\n{result.markup[:500]}")

        except Exception as e:
            print(f"错误: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
