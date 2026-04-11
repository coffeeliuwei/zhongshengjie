#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pathlib

file_path = pathlib.Path(
    r"D:\动画\众生界\.case-library\scripts\enhanced_scene_recognizer.py"
)

content = file_path.read_text(encoding="utf-8")

# Fix line 134 - replace problematic Chinese quotes in regex
# Original: r"["「『"]([^"」』"]+)["」』"]"
# Fixed: Use unicode escapes
old_line = """r"["「『"]([^"」』"]+)["」』"]",  # 引号内容"""
new_line = """r'["\u300c\u300e]([^"\u300d\u300f]+)["\u300d\u300f]',  # 引号内容"""

content = content.replace(old_line, new_line)

file_path.write_text(content, encoding="utf-8")
print("Fixed enhanced_scene_recognizer.py")
