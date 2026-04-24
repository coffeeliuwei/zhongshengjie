#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创作技法检索工具 v4.0 (BGE-M3 + Qdrant)
=====================================

从创作技法向量库中检索相关技法

使用方法：
    python technique_search.py --query "战斗代价描写" --top-k 5
"""

import sys
import io

# Windows PowerShell 编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.config_loader import get_qdrant_url, get_project_root, get_model_path

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
except ImportError:
    print("请安装 qdrant-client: pip install qdrant-client")
    exit(1)


# 配置
PROJECT_DIR = get_project_root()
VECTORSTORE_DIR = PROJECT_DIR / ".vectorstore"
COLLECTION_NAME = "writing_techniques_v2"
VECTOR_SIZE = 1024  # BGE-M3 向量维度

# Docker Qdrant配置
QDRANT_DOCKER_URL = get_qdrant_url()

# BGE-M3 模型路径
BGE_M3_MODEL_PATH = get_model_path()


class TechniqueSearcher:
    """技法检索器 (BGE-M3 + Docker Qdrant版)"""

    def __init__(self):
        self.client = QdrantClient(url=QDRANT_DOCKER_URL)
        self._model = None

    def _load_model(self):
        """懒加载BGE-M3模型"""
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel

                self._model = BGEM3FlagModel(
                    BGE_M3_MODEL_PATH, use_fp16=True, device="cpu"
                )
            except ImportError:
                print("请安装 FlagEmbedding: pip install FlagEmbedding")
            except Exception as e:
                print(f"加载BGE-M3模型失败: {e}")
        return self._model

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入 (BGE-M3 dense向量)"""
        model = self._load_model()
        if model is None:
            return [0.0] * VECTOR_SIZE

        try:
            out = model.encode([text], return_dense=True)
            return out["dense_vecs"][0].tolist()
        except Exception as e:
            print(f"生成嵌入失败: {e}")
            return [0.0] * VECTOR_SIZE

    def search(
        self,
        query: str,
        top_k: int = 5,
        dimension: Optional[str] = None,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        语义检索技法

        Args:
            query: 查询文本
            top_k: 返回数量
            dimension: 维度过滤 (如"世界观维度")
            min_score: 最低相似度

        Returns:
            检索结果列表
        """
        query_vector = self._get_embedding(query)

        # 构建过滤条件
        query_filter = None
        if dimension:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="dimension", match=models.MatchValue(value=dimension)
                    )
                ]
            )

        # 使用named vector "dense" 检索
        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            using="dense",  # 使用dense向量
            query_filter=query_filter,
            limit=top_k,
            score_threshold=min_score,
            with_payload=True,
        )

        formatted = []
        for p in results.points:
            formatted.append(
                {
                    "id": p.id,
                    "name": p.payload.get("name", "未知"),
                    "title": p.payload.get("name", "未知"),  # 兼容旧代码
                    "dimension": p.payload.get("dimension", "未知"),
                    "writer": p.payload.get("writer", "未知"),
                    "source": p.payload.get("source", ""),
                    "file": p.payload.get("source", ""),  # 兼容旧代码
                    "content": p.payload.get("content", ""),
                    "word_count": p.payload.get("word_count", 0),
                    "scenes": p.payload.get("scenes", []),
                    "principle": p.payload.get("principle", ""),
                    "notes": p.payload.get("notes", []),
                    "score": p.score,
                }
            )

        return formatted

    def get_by_dimension(self, dimension: str, top_k: int = 50) -> List[Dict[str, Any]]:
        """按维度检索所有技法"""
        results = self.client.scroll(
            collection_name=COLLECTION_NAME,
            with_payload=True,
            with_vectors=False,
            limit=1000,
        )[0]

        formatted = []
        for p in results:
            if p.payload.get("dimension") == dimension:
                formatted.append(
                    {
                        "id": p.id,
                        "name": p.payload.get("name", "未知"),
                        "title": p.payload.get("name", "未知"),
                        "dimension": p.payload.get("dimension", "未知"),
                        "content": p.payload.get("content", ""),
                        "source": p.payload.get("source", ""),
                    }
                )
                if len(formatted) >= top_k:
                    break

        return formatted

    def list_all_dimensions(self) -> List[str]:
        """列出所有维度"""
        results = self.client.scroll(
            collection_name=COLLECTION_NAME,
            with_payload=True,
            with_vectors=False,
            limit=1000,
        )[0]

        dimensions = set()
        for p in results:
            dim = p.payload.get("dimension", "")
            if dim:
                dimensions.add(dim)

        return sorted(list(dimensions))

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        info = self.client.get_collection(COLLECTION_NAME)

        results = self.client.scroll(
            collection_name=COLLECTION_NAME,
            with_payload=True,
            with_vectors=False,
            limit=1000,
        )[0]

        dimension_counts = {}
        for p in results:
            dim = p.payload.get("dimension", "未知")
            dimension_counts[dim] = dimension_counts.get(dim, 0) + 1

        return {
            "总技法数": info.points_count,
            "各维度数量": dimension_counts,
            "状态": info.status.value,
        }


def format_result(result: Dict[str, Any], show_content: bool = True) -> str:
    """格式化输出结果"""
    lines = []
    lines.append(f"【{result.get('name', '未知')}】")
    lines.append(f"  维度: {result.get('dimension', '未知')}")
    lines.append(f"  作者: {result.get('writer', '未知')}")
    lines.append(f"  来源: {result.get('source', '未知')}")
    lines.append(f"  相似度: {result.get('score', 0):.0%}")

    if show_content:
        content = result.get("content", "")
        if len(content) > 500:
            content = content[:500] + "..."
        lines.append(f"\n  内容预览:\n{content}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="创作技法检索工具 v4.0 (BGE-M3)")
    parser.add_argument("--query", "-q", type=str, help="查询文本")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="返回数量")
    parser.add_argument("--dimension", "-d", type=str, help="维度过滤")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--list-dimensions", action="store_true", help="列出所有维度")

    args = parser.parse_args()

    searcher = TechniqueSearcher()

    if args.stats:
        stats = searcher.get_stats()
        print("=" * 60)
        print("创作技法库统计 (BGE-M3 + Qdrant)")
        print("=" * 60)
        print(f"总技法数: {stats['总技法数']}")
        print(f"状态: {stats['状态']}")
        print("\n各维度数量:")
        for dim, count in sorted(stats["各维度数量"].items(), key=lambda x: -x[1]):
            print(f"  {dim}: {count}")
        return

    if args.list_dimensions:
        dimensions = searcher.list_all_dimensions()
        print("所有维度:")
        for dim in dimensions:
            print(f"  - {dim}")
        return

    if not args.query:
        print("请提供查询文本 (--query)")
        return

    print(f"查询: {args.query}")
    print(f"参数: top_k={args.top_k}, dimension={args.dimension}")
    print("\n" + "=" * 60 + "\n")

    results = searcher.search(
        query=args.query,
        top_k=args.top_k,
        dimension=args.dimension,
    )

    if not results:
        print("未找到匹配的技法")
        return

    for i, result in enumerate(results, 1):
        print(f"[{i}] " + format_result(result))
        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    main()
