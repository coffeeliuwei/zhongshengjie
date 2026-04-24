#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""诊断 unified_extractor 测试失败原因"""
from unittest.mock import patch
from pathlib import Path
import tempfile

from tools.unified_extractor import UnifiedExtractor, HAS_CONFIG_LOADER
print(f"HAS_CONFIG_LOADER={HAS_CONFIG_LOADER}")

td = tempfile.mkdtemp()
tdp = Path(td)
(tdp / ".novel-extractor").mkdir(exist_ok=True)

with patch("tools.unified_extractor.PROJECT_ROOT", tdp), \
     patch("tools.unified_extractor.HAS_CONFIG_LOADER", False):
    e = UnifiedExtractor()
    print(f"progress_file={e.progress_file}")
    print(f"expected={tdp / '.novel-extractor' / 'unified_progress.json'}")
    print(f"match={e.progress_file == tdp / '.novel-extractor' / 'unified_progress.json'}")

# 测试2: 模拟没有patch HAS_CONFIG_LOADER
with patch("tools.unified_extractor.PROJECT_ROOT", tdp):
    e2 = UnifiedExtractor()
    print(f"\nWithout HAS_CONFIG_LOADER patch:")
    print(f"progress_file={e2.progress_file}")

import shutil
shutil.rmtree(td)
