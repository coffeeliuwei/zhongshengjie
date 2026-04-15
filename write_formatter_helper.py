#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Helper to write extraction_formatter.py with correct encoding"""

import os

content = '''"""将 ExtractionRunner 结果转换为中文对话回复"""


def format_start_response(result: dict, mode: str) -> str:
    """格式化启动结果

    Args:
        result: ExtractionRunner.start() 的返回值
        mode: "full" | "incremental"
    """
    if not result.get("started"):
        status = result.get("status", {})
        raw = status.get("raw", "").strip()
        return f"提炼正在进行中:\\n{raw}"

    if mode == "full":
        return (
            "已启动全量提炼（强制重跑所有维度，忽略历史进度）。\\n"
            "提炼期间可以问我"进展怎样"。"
        )
    return (
        "已启动增量提炼，已完成的维度会自动跳过。\\n"
        "提炼期间可以问我"进展怎样"。"
    )


def format_status_response(status: dict) -> str:
    """格式化状态查询结果"""
    raw = (status.get("raw") or "").strip()
    if not raw:
        return "状态获取失败，可能提炼工具未初始化，请检查 .novel-extractor/ 目录。"

    prefix = "提炼正在进行中:\\n" if status.get("running") else "提炼已结束，最终状态：\\n"
    return prefix + raw
'''

target_path = os.path.join(
    os.path.dirname(__file__), "core", "extraction", "extraction_formatter.py"
)
with open(target_path, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Written to {target_path}")
