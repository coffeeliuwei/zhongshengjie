#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOBI格式转换脚本 - 使用mobi库
"""

import os
import re
from pathlib import Path
from typing import Optional
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    import mobi
except ImportError:
    print("请安装mobi库: pip install mobi")
    exit(1)


def convert_mobi_to_txt(mobi_path: Path, output_dir: Path) -> Optional[Path]:
    """转换mobi到txt"""
    import shutil

    try:
        # 使用mobi.extract提取到临时目录
        # mobi.extract返回tuple: (temp_dir, epub_path)
        result = mobi.extract(str(mobi_path))

        if result is None:
            logger.error(f"无法提取: {mobi_path.name}")
            return None

        # 处理tuple返回值
        if isinstance(result, tuple):
            temp_dir = result[0]  # 临时目录路径
        else:
            temp_dir = result

        temp_path = Path(temp_dir)

        # 优先读取mobi7/book.html（简单格式）
        book_html = temp_path / "mobi7" / "book.html"

        if book_html.exists():
            html_files = [book_html]
        else:
            # 否则找所有HTML文件
            html_files = list(temp_path.rglob("*.html")) + list(
                temp_path.rglob("*.htm")
            )

        if not html_files:
            logger.error(f"未找到HTML文件: {mobi_path.name}")
            return None

        # 读取并合并所有HTML内容
        content_parts = []
        for html_file in html_files:
            try:
                with open(html_file, "r", encoding="utf-8", errors="replace") as f:
                    content_parts.append(f.read())
            except:
                with open(html_file, "r", encoding="gb18030", errors="replace") as f:
                    content_parts.append(f.read())

        content = "\n".join(content_parts)

        if not content:
            logger.error(f"内容为空: {mobi_path.name}")
            return None

        # HTML到文本转换
        text = html_to_text(content)

        # 清理临时目录
        try:
            shutil.rmtree(temp_path)
        except:
            pass

        if not text:
            logger.error(f"文本为空: {mobi_path.name}")
            return None

        # 验证中文内容
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(text)

        if total_chars == 0:
            logger.error(f"文本为空: {mobi_path.name}")
            return None

        chinese_ratio = chinese_chars / total_chars
        if chinese_ratio < 0.3:
            logger.warning(f"中文比例过低 {chinese_ratio:.1%}: {mobi_path.name}")
            return None

        # 保存txt文件
        txt_path = output_dir / f"{mobi_path.stem}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        logger.info(
            f"转换成功: {mobi_path.name} -> {txt_path.name} ({chinese_ratio:.0%} 中文)"
        )
        return txt_path

    except Exception as e:
        logger.error(f"转换失败: {mobi_path.name} - {e}")
        return None


def html_to_text(html: str) -> str:
    """HTML到文本转换"""
    # 移除脚本和样式
    html = re.sub(
        r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # 处理常见标签
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<p[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</div>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</section>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", "", html)

    # 解码HTML实体
    import html as html_module

    html = html_module.unescape(html)

    # 清理特殊字符
    html = re.sub(r"&#13;", "", html)
    html = re.sub(r"&#10;", "\n", html)
    html = re.sub(r"&#9;", " ", html)
    html = re.sub(r"&nbsp;", " ", html)

    # 清理空白
    html = re.sub(r"\n\s*\n\s*\n", "\n\n", html)
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"^\s+", "", html, flags=re.MULTILINE)

    return html.strip()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MOBI转TXT转换工具")
    parser.add_argument("--dir", type=str, help="源目录")
    parser.add_argument("--output", type=str, help="输出目录")
    parser.add_argument("--limit", type=int, default=0, help="限制转换数量")

    args = parser.parse_args()

    source_dir = Path(args.dir) if args.dir else Path("E:/小说资源/青春校园")
    output_dir = (
        Path(args.output)
        if args.output
        else Path("D:/动画/众生界/.case-library/converted")
    )

    if not source_dir.exists():
        print(f"源目录不存在: {source_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # 获取所有mobi文件
    mobi_files = list(source_dir.rglob("*.mobi"))
    mobi_files.extend(list(source_dir.rglob("*.MOBI")))

    print(f"开始转换: {source_dir}")
    print(f"找到 {len(mobi_files)} 个mobi文件")
    print("-" * 50)

    success = 0
    failed = 0
    limit = args.limit if args.limit > 0 else len(mobi_files)

    for i, mobi_file in enumerate(mobi_files[:limit]):
        print(
            f"\r转换中 [{i + 1}/{min(len(mobi_files), limit)}]: {mobi_file.name[:30]}...",
            end="",
            flush=True,
        )

        result = convert_mobi_to_txt(mobi_file, output_dir)
        if result:
            success += 1
        else:
            failed += 1

    print()
    print("-" * 50)
    print(f"转换完成: 成功 {success}, 失败 {failed}")


if __name__ == "__main__":
    main()
