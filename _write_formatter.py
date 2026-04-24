#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

formatter_content = """
def format_start_response(result: dict, mode: str) -> str:
    if not result.get("started"):
        status = result.get("status", {})
        raw = status.get("raw", "").strip()
        return f"提炼正在进行中:\\n{raw}"

    if mode == "full":
        return "已启动全量提炼（强制重跑所有维度，忽略历史进度）。\\n提炼期间可以问我进展怎样。"
    return "已启动增量提炼，已完成的维度会自动跳过。\\n提炼期间可以问我进展怎样。"


def format_status_response(status: dict) -> str:
    raw = (status.get("raw") or "").strip()
    if not raw:
        return "状态获取失败，可能提炼工具未初始化，请检查 .novel-extractor/ 目录。"

    prefix = "提炼正在进行中:\\n" if status.get("running") else "提炼已结束，最终状态：\\n"
    return prefix + raw
"""

header = '"""将 ExtractionRunner 结果转换为中文对话回复"""\n\n'
full_content = header + formatter_content

target = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "core",
    "extraction",
    "extraction_formatter.py",
)
with open(target, "w", encoding="utf-8", newline="\n") as f:
    f.write(full_content)
print(f"Written: {target}")
