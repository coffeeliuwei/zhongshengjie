#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检索基准集交互式标注工具
=========================

工作流程：
  1. 从 seed_queries.json（或 benchmark.json）加载查询列表
  2. 对每条查询运行实际检索，展示 Top-N 结果
  3. 你对每个结果打分：0=无关 1=低相关 2=中相关 3=高相关
  4. 打分结果自动追加写入 benchmark_annotated.json（支持断点续标）

用法：
    python tools/annotate_benchmark.py              # 标准模式（每查询看10条结果）
    python tools/annotate_benchmark.py --top-k 5   # 每查询只看5条
    python tools/annotate_benchmark.py --source case  # 只标注案例库

评分说明：
    3 = 高度相关：直接命中，正是需要的内容
    2 = 中度相关：有帮助，但不是最精准的匹配
    1 = 低度相关：边缘相关，有一点用
    0 = 无关：与查询意图无关
    Enter（直接回车）= 0（无关）
    s = skip 跳过整条查询（不标注）
    q = quit 保存并退出
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Windows cmd 默认 GBK，强制改成 UTF-8，否则打印中文会静默崩溃
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────── 路径 ───────────────────────────

ROOT = Path(__file__).parent.parent
EVAL_DIR = ROOT / ".evaluation" / "retrieval_benchmark"
SEED_FILE = EVAL_DIR / "benchmark.json"           # 种子查询（待标注）
OUTPUT_FILE = EVAL_DIR / "benchmark_annotated.json"  # 标注结果（eval脚本用）


# ─────────────────────────── 加载/保存 ───────────────────────────

def load_seeds(source_filter: str = None) -> list:
    """从 benchmark.json 加载种子查询"""
    with open(SEED_FILE, encoding="utf-8") as f:
        data = json.load(f)
    queries = data.get("queries", [])
    if source_filter:
        queries = [q for q in queries if q.get("source") == source_filter]
    return queries


def load_annotated() -> dict:
    """加载已有标注结果（支持续标）"""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "version": "1.0",
        "description": "人工标注检索基准集，用于 eval_retrieval_quality.py",
        "annotated_at": datetime.now().isoformat(),
        "queries": []
    }


def save_annotated(data: dict) -> None:
    """保存标注结果"""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    data["total_queries"] = len(data["queries"])
    data["last_updated"] = datetime.now().isoformat()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  [已保存] {OUTPUT_FILE} ({len(data['queries'])} 条)")


# ─────────────────────────── 检索 ───────────────────────────

def run_search(api, query: str, source: str, top_k: int) -> list:
    """根据 source 调用对应检索接口，返回结果列表"""
    try:
        if source == "technique":
            results = api.search_techniques(query, top_k=top_k)
        elif source == "case":
            results = api.search_cases(query, top_k=top_k)
        elif source == "novel":
            results = api.search_novel(query, top_k=top_k)
        else:
            results = api.search_techniques(query, top_k=top_k)
        return results or []
    except Exception as e:
        print(f"  [检索失败] {e}")
        return []


def extract_id(result: dict) -> str:
    """从检索结果中提取 ID"""
    return str(result.get("id", result.get("name", result.get("point_id", "unknown"))))


def extract_preview(result: dict, max_len: int = 120) -> str:
    """从检索结果中提取预览文本"""
    payload = result.get("payload", result)
    # 尝试常见字段
    for field in ["content", "text", "description", "title", "name", "技法名称", "场景描述"]:
        val = payload.get(field)
        if val and isinstance(val, str) and len(val) > 5:
            return val[:max_len] + ("…" if len(val) > max_len else "")
    # 兜底：把 payload 转成字符串
    raw = str(payload)
    return raw[:max_len] + ("…" if len(raw) > max_len else "")


# ─────────────────────────── 交互标注 ───────────────────────────

def annotate_one(query_text: str, source: str, results: list) -> Optional[List[dict]]:
    """
    对一条查询的检索结果进行交互式打分。

    返回：
        list  — 标注后的 expected_results
        None  — 用户选择 skip
        "quit" — 用户选择退出
    """
    scored = []

    for i, result in enumerate(results, 1):
        rid = extract_id(result)
        preview = extract_preview(result)
        score_val = result.get("score", 0)

        print(f"\n  [{i:02d}] score={score_val:.3f}")
        print(f"       ID: {rid}")
        print(f"       预览: {preview}")
        print(f"       打分 [0无关/1低/2中/3高/s跳过查询/q退出]: ", end="", flush=True)

        raw = input().strip().lower()

        if raw == "q":
            return "quit"
        if raw == "s":
            return None
        if raw in ("1", "2", "3"):
            relevance = int(raw)
        else:
            relevance = 0  # 空输入或0均视为无关

        if relevance > 0:
            scored.append({"id": rid, "relevance": relevance})

    return scored


def already_annotated(annotated_data: dict, query_text: str) -> bool:
    """检查该查询是否已标注过"""
    return any(q["query"] == query_text for q in annotated_data.get("queries", []))


# ─────────────────────────── 主流程 ───────────────────────────

def main():
    print("=== annotate_benchmark.py starting ===", flush=True)
    parser = argparse.ArgumentParser(description="检索基准集交互式标注工具")
    parser.add_argument("--top-k", type=int, default=10, help="每条查询展示结果数（默认10）")
    parser.add_argument("--source", choices=["technique", "case", "novel"],
                        help="只标注指定数据源（不填则全部）")
    parser.add_argument("--recall-target", type=float, default=0.75,
                        help="每条查询的 Recall 目标阈值（默认0.75）")
    args = parser.parse_args()

    # 加载种子查询
    seeds = load_seeds(args.source)
    if not seeds:
        print("没有找到种子查询，请检查 .evaluation/retrieval_benchmark/benchmark.json")
        return

    # 加载已有标注（续标支持）
    annotated = load_annotated()
    done_count = len(annotated["queries"])

    print("=" * 60)
    print("  检索基准集标注工具")
    print("=" * 60)
    print(f"  种子查询总数：{len(seeds)}")
    print(f"  已标注：{done_count} 条（断点续标自动跳过）")
    print(f"  数据源过滤：{args.source or '全部'}")
    print(f"  每查询展示：Top-{args.top_k}")
    print()
    print("  评分：3=高相关  2=中相关  1=低相关  0/Enter=无关")
    print("        s=跳过这条查询  q=保存并退出")
    print("=" * 60)

    # 初始化检索 API
    print("\n初始化检索 API...", flush=True)
    try:
        from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI
        api = UnifiedRetrievalAPI()
    except ImportError as e:
        print(f"[错误] 导入检索模块失败：{e}")
        print("请确认依赖已安装：pip install -r requirements.txt")
        return
    except Exception as e:
        print(f"[错误] 检索 API 初始化失败：{e}")
        return

    new_count = 0

    for idx, seed in enumerate(seeds, 1):
        query_text = seed["query"]
        source = seed.get("source", "technique")

        # 已标注则跳过
        if already_annotated(annotated, query_text):
            print(f"\n[{idx}/{len(seeds)}] 跳过（已标注）：{query_text}")
            continue

        print(f"\n{'─' * 60}")
        print(f"[{idx}/{len(seeds)}] 查询：「{query_text}」  数据源：{source}")
        print("─" * 60)

        # 运行检索
        results = run_search(api, query_text, source, args.top_k)
        if not results:
            print("  （无检索结果，跳过）")
            continue

        # 交互打分
        outcome = annotate_one(query_text, source, results)

        if outcome == "quit":
            save_annotated(annotated)
            print("\n已退出标注，进度已保存。")
            return

        if outcome is None:
            print(f"  （已跳过：{query_text}）")
            continue

        # 存入结果
        annotated["queries"].append({
            "id": f"q_{len(annotated['queries']) + 1:03d}",
            "query": query_text,
            "source": source,
            "expected_results": outcome,
            "min_recall_target": args.recall_target,
            "annotated_at": datetime.now().isoformat()
        })
        new_count += 1

        # 每5条自动保存一次
        if new_count % 5 == 0:
            save_annotated(annotated)

    # 全部完成，最终保存
    save_annotated(annotated)
    print(f"\n标注完成！新增 {new_count} 条，共 {len(annotated['queries'])} 条。")
    print(f"评估命令：python tools/eval_retrieval_quality.py --benchmark benchmark_annotated.json")


if __name__ == "__main__":
    main()
