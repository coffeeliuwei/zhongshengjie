"""
小说提炼系统 - 基础提取器

所有提取器的基类，提供：
- 进度追踪
- 增量提炼
- 批量处理
- 错误恢复
"""

import json
import hashlib
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator
from dataclasses import dataclass, field, asdict
from datetime import datetime

# 导入配置
import sys

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    PROJECT_DIR,
    NOVEL_SOURCE_DIR,
    OUTPUT_DIR,
    PROGRESS_DIR,
    EXTRACTION_DIMENSIONS,
    MOBI_TEMP_DIR,
    get_output_path,
    get_progress_path,
    Priority,
    ExtractionDimension,
)


@dataclass
class ExtractionProgress:
    """提炼进度"""

    dimension_id: str
    status: str = "pending"  # pending, running, completed, failed
    total_novels: int = 0
    processed_novels: int = 0
    total_items: int = 0
    extracted_items: int = 0
    last_novel_id: str = ""
    last_update: str = ""
    errors: List[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""


class BaseExtractor(ABC):
    """
    提取器基类

    子类需要实现：
    - extract_from_novel(novel_path, novel_id) -> List[dict]
    - process_extracted(items) -> List[dict]
    """

    def __init__(self, dimension_id: str):
        self.dimension_id = dimension_id
        self.config = EXTRACTION_DIMENSIONS[dimension_id]
        self.progress = self._load_progress()
        self.output_dir = get_output_path(dimension_id)
        self.results: List[dict] = []

    def _load_progress(self) -> ExtractionProgress:
        """加载进度"""
        progress_path = get_progress_path(self.dimension_id)
        if progress_path.exists():
            with open(progress_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ExtractionProgress(**data)
        return ExtractionProgress(dimension_id=self.dimension_id)

    def _save_progress(self):
        """保存进度"""
        progress_path = get_progress_path(self.dimension_id)
        progress_path.parent.mkdir(parents=True, exist_ok=True)

        self.progress.last_update = datetime.now().isoformat()

        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self.progress), f, ensure_ascii=False, indent=2)

    def _get_novel_id(self, novel_path: Path) -> str:
        """生成小说唯一ID（基于路径hash）"""
        try:
            relative_path = str(novel_path.relative_to(NOVEL_SOURCE_DIR))
        except ValueError:
            relative_path = novel_path.stem
        return hashlib.md5(relative_path.encode()).hexdigest()[:12]

    def _scan_novels(self) -> Generator[Path, None, None]:
        """扫描所有小说文件
        
        优先使用已转换的txt文件，其次源目录txt，最后 epub/mobi/pdf/docx。
        用 seen_stems 防止同一本书被多路径重复 yield。
        """
        from config import CONVERTED_DIR

        seen_stems: set = set()

        # 1. 优先使用 converted 目录中的已转换 txt
        if CONVERTED_DIR.exists():
            for converted_file in sorted(CONVERTED_DIR.glob("*.txt")):
                seen_stems.add(converted_file.stem)
                yield converted_file

        # 2. 源目录中的原始 txt（排除已在 converted 中的）
        for novel_path in NOVEL_SOURCE_DIR.rglob("*.txt"):
            if novel_path.stem not in seen_stems:
                seen_stems.add(novel_path.stem)
                yield novel_path

        # 3. epub / mobi / pdf / docx（排除已有同名 txt 的）
        for ext in [".epub", ".mobi", ".pdf", ".docx"]:
            for novel_path in NOVEL_SOURCE_DIR.rglob(f"*{ext}"):
                if novel_path.stem not in seen_stems:
                    seen_stems.add(novel_path.stem)
                    yield novel_path

    def _read_novel(self, novel_path: Path) -> Optional[str]:
        """读取小说内容"""
        try:
            if novel_path.suffix == ".txt":
                # 尝试多种编码
                for encoding in ["utf-8", "gbk", "gb2312", "utf-16"]:
                    try:
                        with open(novel_path, "r", encoding=encoding) as f:
                            content = f.read()
                        return content
                    except UnicodeDecodeError:
                        continue
                return None
            elif novel_path.suffix == ".epub":
                return self._read_epub(novel_path)
            elif novel_path.suffix == ".mobi":
                return self._read_mobi(novel_path)
            elif novel_path.suffix == ".pdf":
                return self._read_pdf(novel_path)
            elif novel_path.suffix == ".docx":
                return self._read_docx(novel_path)
        except Exception as e:
            print(f"[WARN] Failed to read {novel_path}: {e}")
            return None

    def _read_epub(self, novel_path: Path) -> Optional[str]:
        """读取 epub 文件内容"""
        try:
            from ebooklib import epub

            book = epub.read_epub(str(novel_path), options={"ignore_ncx": True})
            content_parts = []
            for item in book.get_items():
                # Check if item is an HTML document (chapter content)
                # EpubHtml items have get_body_content() or get_content()
                if hasattr(item, "get_body_content"):
                    try:
                        html_content = item.get_body_content()
                        if isinstance(html_content, bytes):
                            html_content = html_content.decode("utf-8", errors="ignore")
                        import re

                        text = re.sub(r"<[^>]+>", "", html_content)
                        text = re.sub(r"\s+", " ", text)
                        if text.strip():
                            content_parts.append(text.strip())
                    except:
                        pass
                elif (
                    hasattr(item, "get_content")
                    and hasattr(item, "media_type")
                    and item.media_type
                    and "html" in item.media_type.lower()
                ):
                    try:
                        html_content = item.get_content()
                        if isinstance(html_content, bytes):
                            html_content = html_content.decode("utf-8", errors="ignore")
                        import re

                        text = re.sub(r"<[^>]+>", "", html_content)
                        text = re.sub(r"\s+", " ", text)
                        if text.strip():
                            content_parts.append(text.strip())
                    except:
                        pass
            return "\n\n".join(content_parts) if content_parts else None
        except Exception as e:
            print(f"[WARN] Failed to read epub {novel_path}: {e}")
            return None

    def _read_mobi(self, novel_path: Path) -> Optional[str]:
        """读取 mobi 文件内容"""
        import tempfile, shutil, os

        # mobi 解压临时目录：从 config.json paths.mobi_temp_dir 读取，默认 E:\tmp_mobi
        # 不能放 C 盘（mobi 解压体积大，会把系统盘塞满）
        _MOBI_TMPDIR = MOBI_TEMP_DIR
        _MOBI_TMPDIR.mkdir(parents=True, exist_ok=True)

        old_tempdir = tempfile.tempdir
        try:
            from mobi import extract

            tempfile.tempdir = str(_MOBI_TMPDIR)
            result = extract(str(novel_path))
            # mobi.extract 可能返回 (tmpdir, epub_path) 元组，也可能直接返回路径字符串
            if isinstance(result, tuple):
                tmpdir, epub_path = result[0], result[1] if len(result) > 1 else result[0]
            else:
                epub_path = result
                tmpdir = None
            epub_path = Path(epub_path)
            if epub_path.exists():
                try:
                    return self._read_epub(epub_path)
                finally:
                    clean_dir = Path(tmpdir) if tmpdir else epub_path.parent
                    if clean_dir.exists() and str(clean_dir).startswith(str(_MOBI_TMPDIR)):
                        shutil.rmtree(clean_dir, ignore_errors=True)
            return None
        except Exception as e:
            print(f"[WARN] Failed to read mobi {novel_path}: {e}")
            return None
        finally:
            tempfile.tempdir = old_tempdir

    def _read_pdf(self, novel_path: Path) -> Optional[str]:
        """读取 PDF 文件内容（可选依赖 pdfminer.six）"""
        try:
            from pdfminer.high_level import extract_text
            content = extract_text(str(novel_path))
            # 清理提取的文本
            content = content.replace('\x00', '')  # 移除空字节
            content = '\n'.join(line.strip() for line in content.splitlines() if line.strip())
            return content if content.strip() else None
        except ImportError:
            print(f"[WARN] pdfminer.six not installed, skipping PDF: {novel_path}")
            return None
        except Exception as e:
            print(f"[WARN] Failed to read PDF {novel_path}: {e}")
            return None

    def _read_docx(self, novel_path: Path) -> Optional[str]:
        """读取 DOCX 文件内容（可选依赖 python-docx）"""
        try:
            from docx import Document
            doc = Document(str(novel_path))
            content_parts = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    content_parts.append(text)
            return '\n\n'.join(content_parts) if content_parts else None
        except ImportError:
            print(f"[WARN] python-docx not installed, skipping DOCX: {novel_path}")
            return None
        except Exception as e:
            print(f"[WARN] Failed to read DOCX {novel_path}: {e}")
            return None

    def run(self, limit: int = None, resume: bool = True) -> Dict[str, Any]:
        """
        运行提取

        Args:
            limit: 限制处理小说数量（用于测试）
            resume: 是否从上次中断处继续

        Returns:
            提取结果统计
        """
        print(f"\n{'=' * 60}")
        print(f"[Extractor] {self.config.name}")
        print(f"Priority: {self.config.priority.value}")
        print(f"{'=' * 60}")

        # 先扫描小说（获取total_novels）
        novels = list(self._scan_novels())
        self.progress.total_novels = len(novels)

        print(f"[INFO] Found {len(novels)} novels to process")

        # 初始化进度（扫描完成后再设置状态）
        self.progress.status = "running"
        self.progress.started_at = datetime.now().isoformat()
        self._save_progress()

        print(f"[INFO] Found {len(novels)} novels to process")

        # 处理小说
        processed = 0
        extracted_count = 0

        for novel_path in novels:
            if limit and processed >= limit:
                print(f"[INFO] Reached limit: {limit}")
                break

            novel_id = self._get_novel_id(novel_path)

            # 增量处理：跳过已处理的
            if resume and self._is_novel_processed(novel_id):
                processed += 1
                continue

            try:
                # 读取内容
                content = self._read_novel(novel_path)
                if not content:
                    continue

                # 提取
                items = self.extract_from_novel(content, novel_id, novel_path)

                # 处理提取结果
                if items:
                    # Ensure we always work with a list from process_extracted
                    processed_items = self.process_extracted(items) or []
                    self._save_extracted_items(processed_items, novel_id)
                    extracted_count += len(processed_items)

                # 更新进度
                processed += 1
                self.progress.processed_novels = processed
                self.progress.extracted_items = extracted_count
                self.progress.last_novel_id = novel_id

                if processed % 10 == 0:
                    self._save_progress()
                    print(
                        f"[PROGRESS] {processed}/{len(novels)} novels, {extracted_count} items"
                    )

            except Exception as e:
                error_msg = f"{novel_id}: {str(e)[:100]}"
                self.progress.errors.append(error_msg)
                print(f"[ERROR] {error_msg}")

        # 完成
        self.progress.status = "completed"
        self.progress.completed_at = datetime.now().isoformat()
        self._save_progress()

        # 保存最终结果
        self._save_final_results()

        print(f"\n[DONE] {self.config.name}")
        print(f"  Novels processed: {processed}")
        print(f"  Items extracted: {extracted_count}")
        print(f"  Output: {self.output_dir}")

        return {
            "dimension": self.dimension_id,
            "status": "completed",
            "novels_processed": processed,
            "items_extracted": extracted_count,
            "output_dir": str(self.output_dir),
        }

    def _is_novel_processed(self, novel_id: str) -> bool:
        """检查小说是否已处理"""
        processed_file = self.output_dir / f".processed_{novel_id}"
        return processed_file.exists()

    def _save_extracted_items(self, items: List[dict], novel_id: str):
        """保存提取结果"""
        if not items:
            return

        # 追加到结果文件
        output_file = self.output_dir / f"{self.dimension_id}_items.jsonl"
        with open(output_file, "a", encoding="utf-8") as f:
            for item in items:
                item["_novel_id"] = novel_id
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        # 标记已处理
        processed_file = self.output_dir / f".processed_{novel_id}"
        processed_file.touch()

        # 添加到内存结果
        self.results.extend(items)

    def _save_final_results(self):
        """保存最终结果"""
        # 合并所有结果
        output_file = self.output_dir / f"{self.dimension_id}_all.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"[SAVED] {output_file} ({len(self.results)} items)")

    @abstractmethod
    def extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]:
        """
        从单本小说提取数据

        Args:
            content: 小说内容
            novel_id: 小说ID
            novel_path: 小说路径

        Returns:
            提取的数据项列表
        """
        pass

    @abstractmethod
    def process_extracted(self, items: List[dict]) -> List[dict]:
        """
        处理提取结果（去重、过滤、标注等）

        Args:
            items: 原始提取结果

        Returns:
            处理后的结果
        """
        pass


class BatchExtractor:
    """批量提取管理器"""

    def __init__(self):
        self.extractors: Dict[str, BaseExtractor] = {}

    def register(self, extractor: BaseExtractor):
        """注册提取器"""
        self.extractors[extractor.dimension_id] = extractor

    def run_all(self, priorities: List[Priority] = None, limit: int = None):
        """
        运行所有提取器

        Args:
            priorities: 只运行指定优先级的提取器
            limit: 每个提取器处理的小说数量限制
        """
        results = {}

        for dim_id, dim_config in EXTRACTION_DIMENSIONS.items():
            # 优先级过滤
            if priorities and dim_config.priority not in priorities:
                continue

            # 获取提取器
            extractor = self.extractors.get(dim_id)
            if not extractor:
                print(f"[SKIP] No extractor registered for {dim_id}")
                continue

            # 运行
            result = extractor.run(limit=limit)
            results[dim_id] = result

        return results

    def get_status(self) -> Dict[str, Dict]:
        """获取所有提取器状态"""
        status = {}

        for dim_id in EXTRACTION_DIMENSIONS:
            progress_path = get_progress_path(dim_id)
            if progress_path.exists():
                with open(progress_path, "r", encoding="utf-8") as f:
                    status[dim_id] = json.load(f)
            else:
                status[dim_id] = {"status": "not_started", "dimension_id": dim_id}

        return status
