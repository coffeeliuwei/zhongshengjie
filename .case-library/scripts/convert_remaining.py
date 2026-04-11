#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from convert_format import FormatConverter

converter = FormatConverter()

# 游戏竞技
print("Converting: 游戏竞技")
result = converter.convert_directory(Path("E:/小说资源/游戏竞技"), ["epub"], True)
print("Done: success=%d, failed=%d" % (result["success"], result["failed"]))

# 女频言情
print("Converting: 女频言情")
result = converter.convert_directory(Path("E:/小说资源/女频言情"), ["epub"], True)
print("Done: success=%d, failed=%d" % (result["success"], result["failed"]))
