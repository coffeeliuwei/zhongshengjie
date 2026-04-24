#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检索质量评估脚本
================

用于评估检索系统的 Recall@K 和 NDCG 指标。

用法:
    python tools/eval_retrieval_quality.py                     # 使用默认评估集
    python tools/eval_retrieval_quality.py --benchmark custom   # 使用自定义评估集
    python tools/eval_retrieval_quality.py --output report.json # 输出报告到文件

评估指标:
- Recall@K: 前 K 个结果中包含的相关结果比例
- NDCG: 考虑排序位置的归一化折扣累积增益

输出:
- 平均 Recall@10
- 平均 NDCG
- 各查询详细结果
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI


def calculate_recall_at_k(
    results: List[Dict], 
    expected: List[Dict], 
    k: int = 10,
    min_relevance: int = 2
) -> float:
    """计算 Recall@K
    
    Args:
        results: 检索结果列表 [{id, score, ...}]
        expected: 期望结果列表 [{id, relevance, ...}]
        k: 取前 K 个结果
        min_relevance: 最小相关性阈值（>=min_relevance 视为相关）
    
    Returns:
        Recall@K 值 (0-1)
    """
    # 期望的相关结果 ID
    expected_ids = {
        e["id"] for e in expected 
        if e.get("relevance", 0) >= min_relevance
    }
    
    if len(expected_ids) == 0:
        return 1.0  # 无期望相关结果，视为完美
    
    # 检索到的结果 ID（前 K 个）
    retrieved_ids = {r.get("id", r.get("name", "")) for r in results[:k]}
    
    # 计算交集比例
    hit_count = len(expected_ids & retrieved_ids)
    return hit_count / len(expected_ids)


def calculate_dcg(results: List[Dict], expected: List[Dict], k: int = 10) -> float:
    """计算 DCG (Discounted Cumulative Gain)
    
    Args:
        results: 检索结果列表
        expected: 期望结果列表
        k: 取前 K 个结果
    
    Returns:
        DCG 值
    """
    # 构建相关性映射
    relevance_map = {e["id"]: e.get("relevance", 0) for e in expected}
    
    dcg = 0.0
    for i, result in enumerate(results[:k]):
        result_id = result.get("id", result.get("name", ""))
        rel = relevance_map.get(result_id, 0)
        # DCG 公式: rel_i / log2(i+2)
        dcg += rel / (i + 2)  # log2(1)=0, 所以用 i+2
    
    return dcg


def calculate_idcg(expected: List[Dict], k: int = 10) -> float:
    """计算 Ideal DCG
    
    Args:
        expected: 期望结果列表（按相关性降序排列的理想情况）
        k: 取前 K 个
    
    Returns:
        IDCG 值
    """
    # 按相关性降序排列
    sorted_expected = sorted(
        expected, 
        key=lambda x: x.get("relevance", 0), 
        reverse=True
    )
    
    idcg = 0.0
    for i, e in enumerate(sorted_expected[:k]):
        rel = e.get("relevance", 0)
        idcg += rel / (i + 2)
    
    return idcg


def calculate_ndcg(
    results: List[Dict], 
    expected: List[Dict], 
    k: int = 10
) -> float:
    """计算 NDCG (Normalized DCG)
    
    Args:
        results: 检索结果列表
        expected: 期望结果列表
        k: 取前 K 个
    
    Returns:
        NDCG 值 (0-1)
    """
    dcg = calculate_dcg(results, expected, k)
    idcg = calculate_idcg(expected, k)
    
    if idcg == 0:
        return 0.0
    
    return dcg / idcg


def load_benchmark(benchmark_path: Path) -> Dict[str, Any]:
    """加载评估基准数据集
    
    Args:
        benchmark_path: 基准文件路径
    
    Returns:
        基准数据字典
    """
    if not benchmark_path.exists():
        raise FileNotFoundError(f"评估基准文件不存在: {benchmark_path}")
    
    with open(benchmark_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_retrieval(
    api: UnifiedRetrievalAPI,
    benchmark: Dict[str, Any],
    top_k: int = 10
) -> Dict[str, Any]:
    """执行检索评估
    
    Args:
        api: UnifiedRetrievalAPI 实例
        benchmark: 基准数据集
        top_k: 每个查询返回的结果数量
    
    Returns:
        评估结果字典
    """
    results = []
    total_recall = 0.0
    total_ndcg = 0.0
    
    queries = benchmark.get("queries", [])
    
    for query_data in queries:
        query_id = query_data.get("id", "unknown")
        query_text = query_data["query"]
        expected = query_data.get("expected_results", [])
        
        # 执行检索
        try:
            retrieved = api.search_techniques(query_text, top_k=top_k)
        except Exception as e:
            print(f"[ERROR] 查询 {query_id} 检索失败: {e}")
            retrieved = []
        
        # 计算指标
        recall = calculate_recall_at_k(retrieved, expected, k=top_k)
        ndcg = calculate_ndcg(retrieved, expected, k=top_k)
        
        total_recall += recall
        total_ndcg += ndcg
        
        results.append({
            "query_id": query_id,
            "query": query_text,
            "recall@10": round(recall, 3),
            "ndcg": round(ndcg, 3),
            "retrieved_count": len(retrieved),
            "expected_count": len(expected),
            "target": query_data.get("min_recall_target", 0.75),
            "passed": recall >= query_data.get("min_recall_target", 0.75)
        })
    
    # 计算平均值
    n = len(queries)
    avg_recall = total_recall / n if n > 0 else 0.0
    avg_ndcg = total_ndcg / n if n > 0 else 0.0
    
    return {
        "summary": {
            "total_queries": n,
            "avg_recall@10": round(avg_recall, 3),
            "avg_ndcg": round(avg_ndcg, 3),
            "pass_rate": sum(1 for r in results if r["passed"]) / n if n > 0 else 0,
            "evaluated_at": datetime.now().isoformat()
        },
        "details": results
    }


def print_report(report: Dict[str, Any]) -> None:
    """打印评估报告
    
    Args:
        report: 评估结果字典
    """
    summary = report["summary"]
    
    print("\n" + "=" * 60)
    print("检索质量评估报告")
    print("=" * 60)
    
    print(f"\n【汇总指标】")
    print(f"  · 评估查询数：{summary['total_queries']}")
    print(f"  · 平均 Recall@10：{summary['avg_recall@10']:.3f}")
    print(f"  · 平均 NDCG：{summary['avg_ndcg']:.3f}")
    print(f"  · 通过率：{summary['pass_rate']:.1%}")
    
    print(f"\n【各查询详情】")
    for detail in report["details"]:
        status = "✓" if detail["passed"] else "✗"
        print(f"  {status} {detail['query_id']}: Recall={detail['recall@10']:.3f}, NDCG={detail['ndcg']:.3f}")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="检索质量评估")
    parser.add_argument(
        "--benchmark", 
        default="benchmark_template.json",
        help="评估基准文件名（位于 .evaluation/retrieval_benchmark/）"
    )
    parser.add_argument(
        "--output", 
        help="输出报告文件路径（JSON格式）"
    )
    parser.add_argument(
        "--top-k", 
        type=int, 
        default=10,
        help="每个查询返回的结果数量"
    )
    
    args = parser.parse_args()
    
    # 路径设置
    project_root = Path(__file__).parent.parent
    benchmark_path = project_root / ".evaluation" / "retrieval_benchmark" / args.benchmark
    
    # 加载基准
    print(f"加载评估基准: {benchmark_path}")
    benchmark = load_benchmark(benchmark_path)
    
    # 初始化检索 API
    print("初始化检索 API...")
    api = UnifiedRetrievalAPI()
    
    # 执行评估
    print("执行评估...")
    report = evaluate_retrieval(api, benchmark, top_k=args.top_k)
    
    # 打印报告
    print_report(report)
    
    # 输出到文件
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"报告已保存: {output_path}")


if __name__ == "__main__":
    main()