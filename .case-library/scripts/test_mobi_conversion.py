#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试mobi -> epub -> txt转换流程"""

from mobi import extract
from ebooklib import epub
from pathlib import Path
import os
import re
import html as html_module
import shutil


def html_to_text(html_content):
    """HTML到文本转换"""
    html_content = re.sub(
        r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL
    )
    html_content = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<br\s*/?>", "\n", html_content)
    html_content = re.sub(r"<p[^>]*>", "\n", html_content)
    html_content = re.sub(r"</p>", "\n", html_content)
    html_content = re.sub(r"</div>", "\n", html_content)
    html_content = re.sub(r"<[^>]+>", "", html_content)
    html_content = html_module.unescape(html_content)
    html_content = re.sub(r"\n\s*\n\s*\n", "\n\n", html_content)
    html_content = re.sub(r"[ \t]+", " ", html_content)
    return html_content.strip()


def test_mobi_conversion(mobi_path):
    """测试单个mobi文件的转换"""
    result = {
        "file": mobi_path.name,
        "success": False,
        "error": None,
        "text_length": 0,
        "preview": "",
    }

    temp_dir = None
    try:
        # Step 1: mobi -> epub
        print(f"  Step 1: 提取mobi到epub...")
        result_tuple = extract(str(mobi_path))

        # extract返回元组 (directory_path, epub_path)
        if isinstance(result_tuple, tuple):
            temp_dir, epub_path = result_tuple
        else:
            epub_path = result_tuple
        print(f"  生成epub: {epub_path}")

        # Step 2: epub -> text
        print(f"  Step 2: 解析epub...")
        book = epub.read_epub(epub_path)

        text_content = []
        for item in book.get_items():
            if item.get_type() == 9:  # ITEM_DOCUMENT
                content = item.get_content()
                decoded = None
                for encoding in ["utf-8", "gb18030", "gbk", "gb2312"]:
                    try:
                        decoded = content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue

                if decoded is None:
                    decoded = content.decode("utf-8", errors="replace")

                text = html_to_text(decoded)
                if len(text) > 100:
                    text_content.append(text)

        full_text = "\n\n".join(text_content)

        result["success"] = True
        result["text_length"] = len(full_text)
        result["preview"] = full_text[:500]

        print(f"  OK - 文本长度: {len(full_text)} 字符")

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:100]}"
        print(f"  ERR - 错误: {result['error']}")

    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

    return result


def main():
    base_path = Path(r"E:\小说资源\第二批资源")
    mobi_files = list(base_path.rglob("*.mobi"))[:5]

    total = len(list(base_path.rglob("*.mobi")))
    print(f"找到 {total} 个mobi文件")
    print(f"测试前5个文件...\n")

    results = []
    for i, mobi_file in enumerate(mobi_files, 1):
        print(f"[{i}/{len(mobi_files)}] {mobi_file.name}")
        result = test_mobi_conversion(mobi_file)
        results.append(result)
        print()

    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)

    success_count = sum(1 for r in results if r["success"])
    print(f"成功: {success_count}/{len(results)}")

    for r in results:
        if r["success"]:
            print(f"  OK {r['file']}: {r['text_length']} 字符")
        else:
            print(f"  ERR {r['file']}: {r['error'][:50] if r['error'] else 'unknown'}")

    # 显示成功案例预览
    success_results = [r for r in results if r["success"]]
    if success_results:
        print(f"\n示例预览 ({success_results[0]['file']}):")
        print("-" * 60)
        print(success_results[0]["preview"][:500])
        print("-" * 60)


if __name__ == "__main__":
    main()
