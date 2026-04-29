#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检索质量交叉验证工具"""

import math
import sys
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_DEFAULT_QUERIES_PATH = Path(__file__).parent / "queries.yaml"


def ndcg_at_5(scores: list[int]) -> float:
    """计算 nDCG@5，scores 为 [0,1,2] 列表，长度 5"""
    dcg = sum(s / math.log2(i + 2) for i, s in enumerate(scores))
    ideal = sorted(scores, reverse=True)
    idcg = sum(s / math.log2(i + 2) for i, s in enumerate(ideal))
    return round(dcg / idcg, 4) if idcg > 0 else 0.0


def precision_at_5(scores: list[int]) -> float:
    """Precision@5，得分 >= 1 视为相关"""
    return round(sum(1 for s in scores if s >= 1) / len(scores), 4)


def embed_query(text: str) -> list[float]:
    """封装 BGE-M3 嵌入，便于测试时 mock"""
    from core.inspiration.embedder import embed_text
    return embed_text(text)


def load_queries(override_path: str | None = None) -> dict:
    """加载查询文件，支持外部覆盖"""
    path = Path(override_path) if override_path else _DEFAULT_QUERIES_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("collections", {})
    except Exception as e:
        if override_path:
            print(f"[WARN] 外部查询文件加载失败（{e}），回退内置默认查询")
            return load_queries(None)
        raise


class CollectionValidator:
    """单个 collection 的检索质量验证器"""

    def __init__(self, qdrant_client, judge, queries: dict):
        self._client = qdrant_client
        self._judge = judge
        self._queries = queries

    def validate_collection(self, collection_name: str) -> dict:
        """验证单个 collection，返回结果字典"""
        try:
            info = self._client.get_collection(collection_name)
            point_count = info.points_count
        except Exception:
            return {"collection": collection_name, "status": "missing",
                    "point_count": 0, "avg_ndcg5": None, "precision5": None,
                    "avg_qdrant_score": None, "score_distribution": None, "queries": []}

        if point_count == 0:
            return {"collection": collection_name, "status": "empty",
                    "point_count": 0, "avg_ndcg5": None, "precision5": None,
                    "avg_qdrant_score": None, "score_distribution": None, "queries": []}

        # 检测向量名：有名向量取第一个，无名向量不传 using
        vectors_config = info.config.params.vectors
        if isinstance(vectors_config, dict):
            vector_name = "dense" if "dense" in vectors_config else next(iter(vectors_config))
        else:
            vector_name = None  # 无名向量

        col_config = self._queries.get(collection_name, {})
        query_texts = col_config.get("queries", [])
        query_results = []
        all_judge_scores = []
        all_qdrant_scores = []

        for query_text in query_texts:
            vector = embed_query(query_text)
            query_kwargs = dict(
                collection_name=collection_name,
                query=vector,
                limit=5,
            )
            if vector_name is not None:
                query_kwargs["using"] = vector_name
            resp = self._client.query_points(**query_kwargs)
            hits = resp.points
            result_items = []
            judge_scores = []
            for rank, hit in enumerate(hits[:5]):
                text = hit.payload.get("content", hit.payload.get("text", ""))
                qdrant_score = float(hit.score)
                all_qdrant_scores.append(qdrant_score)
                judge_score = self._judge.score(query_text, text, collection_name)
                judge_scores.append(judge_score)
                result_items.append({
                    "rank": rank + 1,
                    "score": round(qdrant_score, 4),
                    "judge_score": judge_score,
                    "text_preview": text[:200],
                })

            while len(judge_scores) < 5:
                judge_scores.append(0)

            valid_scores = [s if s is not None else 0 for s in judge_scores]
            all_judge_scores.extend(valid_scores)
            has_llm = any(s is not None for s in judge_scores)
            query_results.append({
                "query": query_text,
                "ndcg5": ndcg_at_5(valid_scores) if has_llm else None,
                "precision5": precision_at_5(valid_scores) if has_llm else None,
                "results": result_items,
            })

        ndcg_values = [r["ndcg5"] for r in query_results if r["ndcg5"] is not None]
        prec_values = [r["precision5"] for r in query_results if r["precision5"] is not None]

        dist = {0: 0, 1: 0, 2: 0}
        for s in all_judge_scores:
            if s in dist:
                dist[s] += 1
        total = sum(dist.values()) or 1

        return {
            "collection": collection_name,
            "status": "ok",
            "point_count": point_count,
            "avg_ndcg5": round(sum(ndcg_values) / len(ndcg_values), 4) if ndcg_values else None,
            "precision5": round(sum(prec_values) / len(prec_values), 4) if prec_values else None,
            "avg_qdrant_score": round(sum(all_qdrant_scores) / len(all_qdrant_scores), 4)
                                if all_qdrant_scores else None,
            "score_distribution": {str(k): round(v / total, 3) for k, v in dist.items()},
            "queries": query_results,
        }


import argparse
import json
import os
from datetime import datetime


_STATUS_EMOJI = {
    "empty":   "❌ 空集合",
    "missing": "❌ 不存在",
}


def _collection_status_emoji(result: dict) -> str:
    if result["status"] != "ok":
        return _STATUS_EMOJI.get(result["status"], "❌")
    ndcg = result.get("avg_ndcg5")
    if ndcg is None:
        return "—"
    if ndcg >= 0.6:
        return "✅"
    if ndcg >= 0.4:
        return "⚠️"
    return "❌"


def write_json_report(all_results: list[dict], judge_name: str, qdrant_url: str) -> Path:
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = logs_dir / f"retrieval_validation_{ts}.json"
    report = {
        "meta": {
            "date": datetime.now().isoformat(),
            "judge": judge_name,
            "qdrant_url": qdrant_url,
        },
        "collections": {r["collection"]: r for r in all_results},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def write_markdown_report(all_results: list[dict], judge_name: str) -> Path:
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = logs_dir / f"retrieval_validation_{ts}.md"

    lines = [
        "# 检索质量验证报告",
        f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}  Judge：{judge_name}",
        "",
        "| Collection | 点数 | avg nDCG@5 | Precision@5 | 分布(0/1/2) | 状态 |",
        "|------------|------|-----------|-------------|------------|------|",
    ]
    for r in all_results:
        name = r["collection"]
        pts = f"{r['point_count']:,}" if r["point_count"] else "0"
        ndcg = f"{r['avg_ndcg5']:.3f}" if r["avg_ndcg5"] is not None else "—"
        prec = f"{r['precision5']:.3f}" if r["precision5"] is not None else "—"
        dist = r.get("score_distribution") or {}
        dist_str = "/".join(
            f"{int(dist.get(k, 0) * 100)}%" for k in ("0", "1", "2")
        ) if dist else "—"
        emoji = _collection_status_emoji(r)
        lines.append(f"| {name} | {pts} | {ndcg} | {prec} | {dist_str} | {emoji} |")

    lines += [
        "",
        "## 阈值说明",
        "- ✅ nDCG@5 ≥ 0.6",
        "- ⚠️ nDCG@5 ∈ [0.4, 0.6)",
        "- ❌ nDCG@5 < 0.4 或集合为空/不存在",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main():
    parser = argparse.ArgumentParser(description="众生界检索质量交叉验证")
    parser.add_argument("--judge", default="skip",
                        choices=["skip", "manual", "openai", "claude", "compatible"],
                        help="LLM judge 类型（默认 skip）")
    parser.add_argument("--judge-model", default=None, help="模型名")
    parser.add_argument("--judge-api-key", default=None, help="API Key")
    parser.add_argument("--judge-base-url", default=None, help="兼容接口 base_url")
    parser.add_argument("--queries", default=None, help="自定义查询 YAML 文件路径")
    parser.add_argument("--collections", default=None,
                        help="逗号分隔的 collection 名，不填则验证全部")
    args = parser.parse_args()

    from qdrant_client import QdrantClient
    from core.config_loader import get_qdrant_url
    from tools.validation.judge import make_judge

    qdrant_url = get_qdrant_url()
    print(f"连接 Qdrant: {qdrant_url}")
    client = QdrantClient(url=qdrant_url, timeout=10)

    judge_kwargs = {}
    if args.judge_model:
        judge_kwargs["model"] = args.judge_model
    if args.judge_api_key:
        judge_kwargs["api_key"] = args.judge_api_key
    if args.judge_base_url:
        judge_kwargs["base_url"] = args.judge_base_url
    judge = make_judge(args.judge, **judge_kwargs)
    judge_name = args.judge if not args.judge_model else f"{args.judge}/{args.judge_model}"

    queries = load_queries(args.queries)

    if args.collections:
        target_collections = [c.strip() for c in args.collections.split(",")]
    else:
        target_collections = list(queries.keys())

    validator = CollectionValidator(
        qdrant_client=client,
        judge=judge,
        queries=queries,
    )

    all_results = []
    for i, col in enumerate(target_collections, 1):
        print(f"\n[{i}/{len(target_collections)}] {col}", end="  ", flush=True)
        result = validator.validate_collection(col)
        all_results.append(result)
        status = _collection_status_emoji(result)
        pts = result["point_count"]
        ndcg = f"nDCG={result['avg_ndcg5']:.3f}" if result["avg_ndcg5"] is not None else "nDCG=—"
        print(f"({pts:,} 点)  {ndcg}  {status}")

    json_path = write_json_report(all_results, judge_name, qdrant_url)
    md_path = write_markdown_report(all_results, judge_name)
    print(f"\n报告已保存：\n  {json_path}\n  {md_path}")


if __name__ == "__main__":
    main()
