#!/usr/bin/env python3
"""
格式转换脚本：将 epub/mobi 文件转换为 txt 格式
支持批量处理和编码统一
"""

import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FormatConverter:
    """格式转换器：epub/mobi → txt"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.converted_dir = (
            Path(self.config.get("case_library_path", ".")) / "converted"
        )
        self.failed_log = self.converted_dir / "failed_conversions.json"
        self._ensure_dirs()

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        if config_path and Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)

        # 默认配置路径
        default_path = Path(__file__).parent.parent / "config.json"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return {}

    def _ensure_dirs(self):
        """确保必要目录存在"""
        self.converted_dir.mkdir(parents=True, exist_ok=True)

    def convert_epub_to_txt(self, epub_path: Path) -> Optional[Path]:
        """转换 epub 到 txt（带编码验证）"""
        try:
            # 尝试使用 ebooklib
            import ebooklib
            from ebooklib import epub

            book = epub.read_epub(str(epub_path))
            text_content = []

            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content = item.get_content()
                    # 尝试多种编码解码
                    decoded = None
                    for encoding in ["utf-8", "gb18030", "gbk", "gb2312"]:
                        try:
                            decoded = content.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue

                    if decoded is None:
                        decoded = content.decode("utf-8", errors="replace")

                    # HTML 到文本转换
                    text = self._html_to_text(decoded)

                    # 验证文本有效性
                    if self._validate_chinese_text(text):
                        text_content.append(text)

            # 组合文本
            full_text = "\n\n".join(text_content)

            # 保存
            txt_path = self.converted_dir / f"{epub_path.stem}.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            logger.info(f"转换成功: {epub_path.name} -> {txt_path.name}")
            return txt_path

        except ImportError:
            logger.warning("ebooklib 未安装，尝试使用 calibre")
            return self._convert_with_calibre(epub_path)
        except Exception as e:
            logger.error(f"转换失败: {epub_path.name} - {e}")
            self._log_failed(epub_path, "epub", str(e))
            return None

    def _validate_chinese_text(self, text: str) -> bool:
        """验证中文文本有效性"""
        if not text or len(text) < 100:
            return False

        # 检查中文字符比例
        import re

        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(text.strip())

        if total_chars == 0:
            return False

        chinese_ratio = chinese_chars / total_chars

        # 中文小说应该有较高的中文比例
        if chinese_ratio < 0.3:
            logger.warning(f"中文比例过低: {chinese_ratio:.1%}")
            return False

        # 检查是否有过多的乱码字符
        garbage_chars = len(re.findall(r"[□○●☆★]", text))
        if garbage_chars > total_chars * 0.05:
            logger.warning(f"乱码字符过多: {garbage_chars}")
            return False

        return True

    def convert_mobi_to_txt(self, mobi_path: Path) -> Optional[Path]:
        """转换 mobi 到 txt (使用mobi库)"""
        try:
            # 尝试使用mobi库
            from mobi import extract
            from ebooklib import epub
            import shutil

            # Step 1: mobi -> epub
            result_tuple = extract(str(mobi_path))

            # extract返回元组 (directory_path, epub_path)
            if isinstance(result_tuple, tuple):
                temp_dir, epub_path = result_tuple
            else:
                temp_dir = None
                epub_path = result_tuple

            # Step 2: 使用ebooklib解析epub
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

                    text = self._html_to_text(decoded)
                    if self._validate_chinese_text(text):
                        text_content.append(text)

            # 合并文本
            full_text = "\n\n".join(text_content)

            # 保存
            txt_path = self.converted_dir / f"{mobi_path.stem}.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            logger.info(f"mobi转换成功: {mobi_path.name} -> {txt_path.name}")

            # 清理临时文件
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

            return txt_path

        except ImportError:
            logger.warning("mobi库未安装，尝试使用calibre")
            return self._convert_with_calibre(mobi_path)
        except Exception as e:
            logger.error(f"mobi转换失败: {mobi_path.name} - {e}")
            self._log_failed(mobi_path, "mobi", str(e))
            return None

    def _convert_with_calibre(self, file_path: Path) -> Optional[Path]:
        """使用 calibre 的 ebook-convert 命令"""
        try:
            txt_path = self.converted_dir / f"{file_path.stem}.txt"

            # 尝试调用 calibre
            result = subprocess.run(
                ["ebook-convert", str(file_path), str(txt_path)],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                logger.info(f"Calibre转换成功: {file_path.name} -> {txt_path.name}")
                return txt_path
            else:
                logger.error(f"Calibre转换失败: {result.stderr}")
                self._log_failed(file_path, file_path.suffix, result.stderr)
                return None

        except FileNotFoundError:
            logger.error("calibre 未安装，无法转换 mobi/epub")
            self._log_failed(file_path, file_path.suffix, "calibre未安装")
            return None
        except subprocess.TimeoutExpired:
            logger.error(f"转换超时: {file_path.name}")
            self._log_failed(file_path, file_path.suffix, "转换超时")
            return None

    def _html_to_text(self, html: str) -> str:
        """HTML到文本转换（清理HTML实体和标签）"""
        import re
        import html as html_module

        # 移除脚本和样式
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)

        # 处理常见标签
        html = re.sub(r"<br\s*/?>", "\n", html)
        html = re.sub(r"<p[^>]*>", "\n", html)
        html = re.sub(r"</p>", "\n", html)
        html = re.sub(r"</div>", "\n", html)
        html = re.sub(r"</section>", "\n", html)
        html = re.sub(r"</article>", "\n", html)
        html = re.sub(r"<[^>]+>", "", html)

        # 解码HTML实体
        html = html_module.unescape(html)

        # 清理特殊字符
        html = re.sub(r"&#13;", "", html)  # 回车符
        html = re.sub(r"&#10;", "\n", html)  # 换行符
        html = re.sub(r"&#9;", " ", html)  # 制表符
        html = re.sub(r"&nbsp;", " ", html)
        html = re.sub(r"&amp;", "&", html)
        html = re.sub(r"&lt;", "<", html)
        html = re.sub(r"&gt;", ">", html)
        html = re.sub(r"&quot;", '"', html)
        html = re.sub(r"&apos;", "'", html)

        # 清理空白
        html = re.sub(r"\n\s*\n\s*\n", "\n\n", html)
        html = re.sub(r"[ \t]+", " ", html)
        html = re.sub(r"^\s+", "", html, flags=re.MULTILINE)

        return html.strip()

    def _log_failed(self, file_path: Path, format_type: str, error: str):
        """记录失败的转换"""
        failed_list = []
        if self.failed_log.exists():
            with open(self.failed_log, "r", encoding="utf-8") as f:
                failed_list = json.load(f)

        failed_list.append(
            {
                "file": str(file_path),
                "format": format_type,
                "error": error,
                "time": str(Path(__file__).parent.parent.parent / "timestamp"),
            }
        )

        with open(self.failed_log, "w", encoding="utf-8") as f:
            json.dump(failed_list, f, ensure_ascii=False, indent=2)

    def convert_directory(
        self, source_dir: Path, formats: List[str] = None, recursive: bool = True
    ) -> Dict:
        """批量转换目录中的文件（支持递归）"""
        formats = formats or ["epub", "mobi"]
        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "converted_files": [],
            "failed_files": [],
        }

        # 递归或非递归搜索
        for ext in formats:
            if recursive:
                files = list(source_dir.rglob(f"*.{ext}"))
                files.extend(list(source_dir.rglob(f"*.{ext.upper()}")))
            else:
                files = list(source_dir.glob(f"*.{ext}"))
                files.extend(list(source_dir.glob(f"*.{ext.upper()}")))

            results["total"] += len(files)

            for i, file_path in enumerate(files):
                print(
                    f"\r转换中 [{i + 1}/{len(files)}]: {file_path.name[:30]}...",
                    end="",
                    flush=True,
                )

                if ext.lower() == "epub":
                    txt_path = self.convert_epub_to_txt(file_path)
                else:
                    txt_path = self.convert_mobi_to_txt(file_path)

                if txt_path:
                    results["success"] += 1
                    results["converted_files"].append(
                        {"original": str(file_path), "converted": str(txt_path)}
                    )
                else:
                    results["failed"] += 1
                    results["failed_files"].append(str(file_path))

        print()  # 换行

        # 检查已有的 txt 文件
        if recursive:
            txt_files = list(source_dir.rglob("*.txt"))
            txt_files.extend(list(source_dir.rglob("*.TXT")))
        else:
            txt_files = list(source_dir.glob("*.txt"))
            txt_files.extend(list(source_dir.glob("*.TXT")))
        results["skipped"] = len(txt_files)

        logger.info(
            f"转换完成: 成功 {results['success']}, 失败 {results['failed']}, 已有txt {results['skipped']}"
        )
        return results

    def process_source(self, source_id: str, sources_path: str = None) -> Dict:
        """处理指定数据源"""
        sources_config = self._load_sources(sources_path)

        for source in sources_config.get("sources", []):
            if source["id"] == source_id:
                source_path = Path(source["path"])
                if source_path.exists():
                    return self.convert_directory(source_path)
                else:
                    logger.error(f"数据源路径不存在: {source_path}")
                    return {"error": "path_not_found"}

        logger.error(f"未找到数据源: {source_id}")
        return {"error": "source_not_found"}

    def _load_sources(self, sources_path: str) -> Dict:
        """加载数据源配置"""
        if sources_path and Path(sources_path).exists():
            with open(sources_path, "r", encoding="utf-8") as f:
                return json.load(f)

        default_path = Path(__file__).parent.parent / "sources.json"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return {"sources": []}


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="小说格式转换工具 - epub/mobi → txt")
    parser.add_argument("--source", type=str, help="数据源ID")
    parser.add_argument("--dir", type=str, help="直接指定目录")
    parser.add_argument(
        "--formats", type=str, nargs="+", default=["epub", "mobi"], help="要转换的格式"
    )
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--no-recursive", action="store_true", help="不递归处理子目录")
    parser.add_argument("--limit", type=int, default=0, help="限制转换数量（0=不限制）")

    args = parser.parse_args()

    converter = FormatConverter(args.config)
    recursive = not args.no_recursive

    if args.source:
        result = converter.process_source(args.source)
    elif args.dir:
        source_dir = Path(args.dir)
        if not source_dir.exists():
            print(f"错误: 目录不存在 {args.dir}")
            return

        print(f"开始转换: {args.dir}")
        print(f"格式: {args.formats}")
        print(f"递归: {'是' if recursive else '否'}")
        print("-" * 50)

        result = converter.convert_directory(source_dir, args.formats, recursive)
    else:
        # 默认处理小说资源目录
        default_dir = Path("E:/小说资源")
        if default_dir.exists():
            print(f"开始转换默认目录: {default_dir}")
            print(f"格式: {args.formats}")
            print(f"递归: 是")
            print("-" * 50)
            result = converter.convert_directory(
                default_dir, args.formats, recursive=True
            )
        else:
            print("请指定 --source 或 --dir 参数")
            return

    print("\n" + "=" * 50)
    print("转换结果:")
    print(f"  总文件数: {result.get('total', 0)}")
    print(f"  成功转换: {result.get('success', 0)}")
    print(f"  转换失败: {result.get('failed', 0)}")
    print(f"  已有txt: {result.get('skipped', 0)}")

    if result.get("failed_files"):
        print(f"\n失败文件 (前10个):")
        for f in result["failed_files"][:10]:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
