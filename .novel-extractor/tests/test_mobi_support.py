import sys
from pathlib import Path

# Add the local .novel-extractor dir to path for imports
base_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base_dir))

import base_extractor as be


class DummyExtractor(be.BaseExtractor):
    def __init__(self):
        # Do not call super().__init__ to keep tests lightweight
        pass

    def extract_from_novel(self, content, novel_id, novel_path):
        return []

    def process_extracted(self, items):
        return items


def test_scan_novels_includes_mobi(tmp_path, monkeypatch):
    # Prepare a temporary directory with test files
    tdir = tmp_path
    (tdir / "a.txt").write_text("content")
    (tdir / "b.epub").write_text("content")
    (tdir / "c.mobi").write_text("content")

    # Patch NOVEL_SOURCE_DIR used by the extractor module
    monkeypatch.setattr(be, "NOVEL_SOURCE_DIR", tdir)

    extractor = DummyExtractor()
    paths = list(extractor._scan_novels())
    suffixes = {p.suffix for p in paths}

    assert ".txt" in suffixes
    assert ".epub" in suffixes
    assert ".mobi" in suffixes
    assert len(paths) == 3


def test_read_novel_mobi_returns_path():
    tmp = Path(__file__).resolve().parents[1]  # .novel-extractor
    # Create a fake mobi path in a temp dir
    mobi_path = Path(tmp, "temp_test.mobi")
    mobi_path.write_text("dummy")

    extractor = DummyExtractor()
    # Should return the path string as a fallback for mobi handling
    assert extractor._read_novel(mobi_path) == str(mobi_path)
