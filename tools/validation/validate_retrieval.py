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

        col_config = self._queries.get(collection_name, {})
        query_texts = col_config.get("queries", [])
        query_results = []
        all_judge_scores = []
        all_qdrant_scores = []

        for query_text in query_texts:
            vector = embed_query(query_text)
            hits = self._client.search(
                collection_name=collection_name,
                query_vector=vector,
                limit=5,
            )
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
