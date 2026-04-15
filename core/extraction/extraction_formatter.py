"""将 ExtractionRunner 结果转换为中文对话回复"""


def format_start_response(result: dict, mode: str) -> str:
    if not result.get("started"):
        status = result.get("status", {})
        raw = status.get("raw", "").strip()
        return f"提炼正在进行中:\n{raw}"

    if mode == "full":
        return "已启动全量提炼（强制重跑所有维度，忽略历史进度）。\n提炼期间可以问我进展怎样。"
    return "已启动增量提炼，已完成的维度会自动跳过。\n提炼期间可以问我进展怎样。"


def format_status_response(status: dict) -> str:
    raw = (status.get("raw") or "").strip()
    if not raw:
        return "状态获取失败，可能提炼工具未初始化，请检查 .novel-extractor/ 目录。"

    prefix = "提炼正在进行中:\n" if status.get("running") else "提炼已结束，最终状态：\n"
    return prefix + raw
