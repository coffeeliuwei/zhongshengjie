#!/usr/bin/env python
"""
检索质量评估测试集

测试维度:
1. 语义相关性 - Top-1/Top-3/Top-10命中率
2. 词汇召回 - 精确匹配召回率
3. 融合效果 - Dense vs ColBERT vs RRF对比
4. 响应速度 - P50/P95/P99延迟

使用方法:
    python retrieval_evaluation.py --run
    python retrieval_evaluation.py --report
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

try:
    from hybrid_retriever import HybridRetriever, SearchResult, MAIN_COLLECTIONS
except ImportError:
    raise ImportError("请先创建 hybrid_retriever.py")

# 测试集定义
EVALUATION_TEST_SET = {
    "semantic_queries": [
        # 语义查询 - 测试泛化能力（不精确匹配关键词）
        {
            "query": "主角突破境界时的心理变化",
            "expected_types": ["战斗", "心理", "成长"],
            "expected_keywords": ["突破", "境界", "成长", "心理"],
            "collections": ["writing_techniques_v2", "case_library_v2"],
        },
        {
            "query": "师徒传承的责任与代价",
            "expected_types": ["人物", "传承", "代价"],
            "expected_keywords": ["师徒", "传承", "责任", "代价"],
            "collections": ["writing_techniques_v2", "character_relation_v1"],
        },
        {
            "query": "战斗胜利后的反思",
            "expected_types": ["战斗", "代价", "反思"],
            "expected_keywords": ["战斗", "胜利", "代价", "反思"],
            "collections": ["writing_techniques_v2", "case_library_v2"],
        },
        {
            "query": "开篇场景如何建立世界观",
            "expected_types": ["开篇", "世界观", "铺垫"],
            "expected_keywords": ["开篇", "世界观", "铺垫", "建立"],
            "collections": ["writing_techniques_v2", "case_library_v2"],
        },
        {
            "query": "悬念如何吸引读者",
            "expected_types": ["悬念", "叙事", "张力"],
            "expected_keywords": ["悬念", "吸引", "张力", "好奇"],
            "collections": ["writing_techniques_v2"],
        },
    ],
    "keyword_queries": [
        # 词汇查询 - 测试精确匹配
        {
            "query": "剑法",
            "must_contain": ["剑法", "剑招", "剑道"],
            "collections": ["power_vocabulary_v1", "worldview_element_v1"],
        },
        {
            "query": "元婴期",
            "must_contain": ["元婴"],
            "collections": ["power_vocabulary_v1"],
        },
        {
            "query": "宗门",
            "must_contain": ["宗门", "门派"],
            "collections": ["worldview_element_v1"],
        },
        {
            "query": "师徒关系",
            "must_contain": ["师徒", "师父", "徒弟"],
            "collections": ["character_relation_v1"],
        },
        {
            "query": "突破",
            "must_contain": ["突破", "境界"],
            "collections": ["power_vocabulary_v1", "case_library_v2"],
        },
    ],
    "complex_queries": [
        # 混合查询 - 测试融合效果
        {
            "query": "主角突破金丹期时的战斗场景描写",
            "expected_mix": True,
            "collections": [
                "writing_techniques_v2",
                "case_library_v2",
                "power_vocabulary_v1",
            ],
        },
        {
            "query": "师徒传承中的情感冲突和矛盾",
            "expected_mix": True,
            "collections": ["writing_techniques_v2", "character_relation_v1"],
        },
        {
            "query": "开篇场景中人物出场的世界观铺垫",
            "expected_mix": True,
            "collections": [
                "writing_techniques_v2",
                "case_library_v2",
                "novel_settings_v2",
            ],
        },
    ],
}


@dataclass
class EvaluationResult:
    """评估结果"""

    query: str
    collection: str
    top_k: int
    hit_rate_top1: float
    hit_rate_top3: float
    hit_rate_top10: float
    keyword_match_rate: float
    avg_score: float
    latency_ms: float
    source: str  # dense/colbert/rrf_fusion
    details: List[Dict[str, Any]]


class RetrievalEvaluator:
    """检索质量评估器"""

    def __init__(self):
        self.retriever = HybridRetriever()
        self.results: List[EvaluationResult] = []

    def evaluate_hit_rate(
        self,
        results: List[SearchResult],
        expected_keywords: List[str],
        top_k: int = 10,
    ) -> Tuple[float, float, float]:
        """
        计算命中率

        Returns:
            (top1_hit, top3_hit, top10_hit)
        """

        def contains_keywords(payload: Dict, keywords: List[str]) -> bool:
            # 兼容不同payload字段名
            text = str(
                payload.get(
                    "content",
                    payload.get(
                        "text", payload.get("name", payload.get("技法名称", ""))
                    ),
                )
            )
            return any(kw in text for kw in keywords)

        hits = [contains_keywords(r.payload, expected_keywords) for r in results]

        top1_hit = 1.0 if hits[0] else 0.0 if hits else 0.0
        top3_hit = (
            sum(hits[:3]) / 3.0
            if len(hits) >= 3
            else sum(hits) / len(hits)
            if hits
            else 0.0
        )
        top10_hit = (
            sum(hits[:10]) / 10.0
            if len(hits) >= 10
            else sum(hits) / len(hits)
            if hits
            else 0.0
        )

        return top1_hit, top3_hit, top10_hit

    def evaluate_keyword_match(
        self,
        results: List[SearchResult],
        must_contain: List[str],
    ) -> float:
        """计算关键词匹配率"""

        def contains_any(payload: Dict, keywords: List[str]) -> bool:
            # 兼容不同payload字段名
            text = str(
                payload.get(
                    "content",
                    payload.get(
                        "text", payload.get("name", payload.get("技法名称", ""))
                    ),
                )
            )
            return any(kw in text for kw in keywords)

        matches = [contains_any(r.payload, must_contain) for r in results]
        return sum(matches) / len(matches) if matches else 0.0

    def run_single_test(
        self,
        test_case: Dict[str, Any],
        collection: str,
        top_k: int = 10,
    ) -> EvaluationResult:
        """运行单个测试"""
        query = test_case["query"]

        start_time = time.time()
        results = self.retriever.retrieve(query, collection, top_k=top_k, verbose=False)
        latency_ms = (time.time() - start_time) * 1000

        # 评估命中率
        if "expected_keywords" in test_case:
            top1, top3, top10 = self.evaluate_hit_rate(
                results, test_case["expected_keywords"], top_k
            )
        else:
            top1, top3, top10 = 0.0, 0.0, 0.0

        # 评估关键词匹配
        if "must_contain" in test_case:
            keyword_match = self.evaluate_keyword_match(
                results, test_case["must_contain"]
            )
        else:
            keyword_match = 0.0

        # 平均分数
        avg_score = sum(r.score for r in results) / len(results) if results else 0.0

        # 来源
        source = results[0].source if results else "none"

        # 详情
        details = [
            {
                "rank": i + 1,
                "score": r.score,
                "text": str(
                    r.payload.get(
                        "content",
                        r.payload.get(
                            "text", r.payload.get("name", r.payload.get("技法名称", ""))
                        ),
                    )
                )[:100],
                "dense_rank": r.dense_rank,
                "colbert_rank": r.colbert_rank,
            }
            for i, r in enumerate(results[:5])
        ]

        return EvaluationResult(
            query=query,
            collection=collection,
            top_k=top_k,
            hit_rate_top1=top1,
            hit_rate_top3=top3,
            hit_rate_top10=top10,
            keyword_match_rate=keyword_match,
            avg_score=avg_score,
            latency_ms=latency_ms,
            source=source,
            details=details,
        )

    def run_all_tests(self) -> Dict[str, Any]:
        """运行全部测试"""
        print("=" * 60)
        print("检索质量评估测试")
        print("=" * 60)

        all_results = []

        # 语义查询测试
        print("\n[语义查询测试]")
        for test_case in EVALUATION_TEST_SET["semantic_queries"]:
            for collection in test_case["collections"]:
                result = self.run_single_test(test_case, collection)
                all_results.append(result)
                print(f"  {test_case['query'][:30]} -> {collection}")
                print(
                    f"    Top-1命中: {result.hit_rate_top1:.2%}, Top-3: {result.hit_rate_top3:.2%}"
                )
                print(f"    延迟: {result.latency_ms:.1f}ms")

        # 词汇查询测试
        print("\n[词汇查询测试]")
        for test_case in EVALUATION_TEST_SET["keyword_queries"]:
            for collection in test_case["collections"]:
                result = self.run_single_test(test_case, collection)
                all_results.append(result)
                print(f"  {test_case['query'][:30]} -> {collection}")
                print(f"    关键词匹配: {result.keyword_match_rate:.2%}")
                print(f"    延迟: {result.latency_ms:.1f}ms")

        # 混合查询测试
        print("\n[混合查询测试]")
        for test_case in EVALUATION_TEST_SET["complex_queries"]:
            for collection in test_case["collections"]:
                result = self.run_single_test(test_case, collection)
                all_results.append(result)
                print(f"  {test_case['query'][:30]} -> {collection}")
                print(f"    Top-3命中: {result.hit_rate_top3:.2%}")

        self.results = all_results

        # 统计报告
        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """生成评估报告"""
        if not self.results:
            return {}

        # 按collection分组
        by_collection = defaultdict(list)
        for r in self.results:
            by_collection[r.collection].append(r)

        # 按查询类型分组
        semantic_results = [r for r in self.results if r.keyword_match_rate == 0.0]
        keyword_results = [r for r in self.results if r.keyword_match_rate > 0.0]

        report = {
            "summary": {
                "total_tests": len(self.results),
                "avg_latency_ms": sum(r.latency_ms for r in self.results)
                / len(self.results),
                "avg_top1_hit": sum(r.hit_rate_top1 for r in semantic_results)
                / len(semantic_results)
                if semantic_results
                else 0,
                "avg_top3_hit": sum(r.hit_rate_top3 for r in semantic_results)
                / len(semantic_results)
                if semantic_results
                else 0,
                "avg_keyword_match": sum(r.keyword_match_rate for r in keyword_results)
                / len(keyword_results)
                if keyword_results
                else 0,
            },
            "by_collection": {},
            "latency_stats": {},
        }

        # Collection统计
        for col, results in by_collection.items():
            report["by_collection"][col] = {
                "count": len(results),
                "avg_latency_ms": sum(r.latency_ms for r in results) / len(results),
                "avg_score": sum(r.avg_score for r in results) / len(results),
                "avg_hit_rate_top3": sum(r.hit_rate_top3 for r in results)
                / len(results),
            }

        # 延迟统计
        latencies = sorted([r.latency_ms for r in self.results])
        report["latency_stats"] = {
            "p50": latencies[len(latencies) // 2],
            "p95": latencies[int(len(latencies) * 0.95)]
            if len(latencies) > 20
            else latencies[-1],
            "p99": latencies[-1],
            "min": latencies[0],
            "max": latencies[-1],
        }

        return report

    def print_report(self):
        """打印评估报告"""
        report = self.generate_report()

        print("\n" + "=" * 60)
        print("评估报告")
        print("=" * 60)

        print("\n[总体统计]")
        print(f"  总测试数: {report['summary']['total_tests']}")
        print(f"  平均延迟: {report['summary']['avg_latency_ms']:.1f}ms")
        print(f"  Top-1命中率: {report['summary']['avg_top1_hit']:.2%}")
        print(f"  Top-3命中率: {report['summary']['avg_top3_hit']:.2%}")
        print(f"  关键词匹配率: {report['summary']['avg_keyword_match']:.2%}")

        print("\n[延迟分布]")
        stats = report["latency_stats"]
        print(f"  P50: {stats['p50']:.1f}ms")
        print(f"  P95: {stats['p95']:.1f}ms")
        print(f"  P99: {stats['p99']:.1f}ms")
        print(f"  Min: {stats['min']:.1f}ms, Max: {stats['max']:.1f}ms")

        print("\n[Collection统计]")
        for col, stats in report["by_collection"].items():
            print(f"  {col}:")
            print(f"    测试数: {stats['count']}")
            print(f"    平均延迟: {stats['avg_latency_ms']:.1f}ms")
            print(f"    Top-3命中率: {stats['avg_hit_rate_top3']:.2%}")

    def save_report(self, output_path: str = "evaluation_report.json"):
        """保存评估报告"""
        report = self.generate_report()

        # 添加详细结果
        report["detailed_results"] = [
            {
                "query": r.query,
                "collection": r.collection,
                "hit_rate_top1": r.hit_rate_top1,
                "hit_rate_top3": r.hit_rate_top3,
                "latency_ms": r.latency_ms,
                "source": r.source,
                "details": r.details,
            }
            for r in self.results
        ]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"[OK] 报告已保存: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="检索质量评估")
    parser.add_argument("--run", action="store_true", help="运行评估测试")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument(
        "--save", type=str, default="evaluation_report.json", help="保存报告路径"
    )

    args = parser.parse_args()

    evaluator = RetrievalEvaluator()

    if args.run:
        evaluator.run_all_tests()
        evaluator.print_report()

    if args.report:
        evaluator.print_report()

    if args.run or args.report:
        evaluator.save_report(args.save)
