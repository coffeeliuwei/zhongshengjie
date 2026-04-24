#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一知识检索工具 v4.0 (BGE-M3 + Qdrant)
=====================================

三大数据库：
- novel_settings_v2：小说设定
- writing_techniques_v2：创作技法
- case_library_v2：标杆案例

使用方法：
    from knowledge_search import KnowledgeSearcher

    searcher = KnowledgeSearcher()

    # 检索小说设定
    results = searcher.search_novel("林夕", entity_type="角色")

    # 检索创作技法
    techniques = searcher.search_techniques("战斗代价", dimension="战斗冲突维度")
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
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.config_loader import get_qdrant_url, get_project_root, get_model_path

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
except ImportError:
    print("请安装 qdrant-client: pip install qdrant-client")
    exit(1)


# ============================================================
# 配置
# ============================================================

PROJECT_DIR = get_project_root()
VECTORSTORE_DIR = PROJECT_DIR / ".vectorstore"

# Docker Qdrant URL (统一数据源)
QDRANT_DOCKER_URL = get_qdrant_url()

# 集合名称 (v2版本)
NOVEL_COLLECTION = "novel_settings_v2"  # 小说设定
TECHNIQUE_COLLECTION = "writing_techniques_v2"  # 创作技法
CASE_COLLECTION = "case_library_v2"  # 标杆案例

# 向量维度 (BGE-M3)
VECTOR_SIZE = 1024

# BGE-M3 模型路径
BGE_M3_MODEL_PATH = get_model_path()

# 实体类型
ENTITY_TYPES = ["势力", "派系", "角色", "力量体系", "力量派别", "时代", "事件"]

# 技法维度
TECHNIQUE_DIMENSIONS = [
    "世界观维度",
    "剧情维度",
    "人物维度",
    "战斗冲突维度",
    "氛围意境维度",
    "叙事维度",
    "主题维度",
    "情感维度",
    "读者体验维度",
    "元维度",
    "节奏维度",
]


# ============================================================
# 检索器
# ============================================================


class KnowledgeSearcher:
    """统一知识检索器 (BGE-M3 + Qdrant Docker版)"""

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

    # ============================================================
    # 小说设定检索
    # ============================================================

    def search_novel(
        self,
        query: str,
        entity_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        检索小说设定

        Args:
            query: 查询文本
            entity_type: 实体类型过滤
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        query_vector = self._get_embedding(query)

        # 构建过滤条件
        query_filter = None
        if entity_type:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="type", match=models.MatchValue(value=entity_type)
                    )
                ]
            )

        try:
            results = self.client.query_points(
                collection_name=NOVEL_COLLECTION,
                query=query_vector,
                using="dense",  # 使用dense向量
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except Exception as e:
            print(f"[警告] 小说设定检索失败: {e}")
            return []

        formatted = []
        for p in results.points:
            formatted.append(
                {
                    "id": p.id,
                    "name": p.payload.get("name", "未知"),
                    "type": p.payload.get("type", "未知"),
                    "description": p.payload.get("description", ""),
                    "score": p.score,
                }
            )

        return formatted

    def get_character(self, name: str) -> Optional[Dict[str, Any]]:
        """获取角色设定"""
        results = self.search_novel(name, entity_type="角色", top_k=10)
        for r in results:
            if name in r.get("name", ""):
                return r
        return None

    def get_faction(self, name: str) -> Optional[Dict[str, Any]]:
        """获取势力设定"""
        results = self.search_novel(name, entity_type="势力", top_k=10)
        for r in results:
            if name in r.get("name", ""):
                return r
        return None

    def get_power_branch(self, name: str) -> Optional[Dict[str, Any]]:
        """获取力量派别"""
        results = self.search_novel(name, entity_type="力量派别", top_k=10)
        for r in results:
            if name in r.get("name", ""):
                return r
        return None

    def list_characters(self) -> List[str]:
        """列出所有角色"""
        try:
            results = self.client.scroll(
                collection_name=NOVEL_COLLECTION,
                with_payload=True,
                with_vectors=False,
                limit=1000,
            )[0]

            return [
                p.payload.get("name", "未知")
                for p in results
                if p.payload.get("type") == "角色"
            ]
        except Exception:
            return []

    def list_factions(self) -> List[str]:
        """列出所有势力"""
        try:
            results = self.client.scroll(
                collection_name=NOVEL_COLLECTION,
                with_payload=True,
                with_vectors=False,
                limit=1000,
            )[0]

            return [
                p.payload.get("name", "未知")
                for p in results
                if p.payload.get("type") == "势力"
            ]
        except Exception:
            return []

    # ============================================================
    # 创作技法检索
    # ============================================================

    def search_techniques(
        self,
        query: str,
        dimension: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        检索创作技法

        Args:
            query: 查询文本
            dimension: 维度过滤 (如"战斗冲突维度")
            top_k: 返回数量

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

        try:
            results = self.client.query_points(
                collection_name=TECHNIQUE_COLLECTION,
                query=query_vector,
                using="dense",  # 使用dense向量
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except Exception as e:
            print(f"[警告] 技法检索失败: {e}")
            return []

        formatted = []
        for p in results.points:
            formatted.append(
                {
                    "id": p.id,
                    "name": p.payload.get("name", "未知"),
                    "title": p.payload.get("name", "未知"),  # 兼容
                    "dimension": p.payload.get("dimension", "未知"),
                    "writer": p.payload.get("writer", "未知"),
                    "source": p.payload.get("source", ""),
                    "file": p.payload.get("source", ""),  # 兼容
                    "content": p.payload.get("content", ""),
                    "word_count": p.payload.get("word_count", 0),
                    "score": p.score,
                }
            )

        return formatted

    def list_technique_dimensions(self) -> List[str]:
        """列出所有技法维度"""
        return TECHNIQUE_DIMENSIONS

    # ============================================================
    # 案例检索
    # ============================================================

    def search_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        检索标杆案例

        Args:
            query: 查询文本
            scene_type: 场景类型过滤
            genre: 题材过滤
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        query_vector = self._get_embedding(query)

        # 构建过滤条件
        filter_conditions = []
        if scene_type:
            filter_conditions.append(
                models.FieldCondition(
                    key="scene_type", match=models.MatchValue(value=scene_type)
                )
            )
        if genre:
            filter_conditions.append(
                models.FieldCondition(key="genre", match=models.MatchValue(value=genre))
            )

        query_filter = None
        if filter_conditions:
            query_filter = models.Filter(must=filter_conditions)

        try:
            results = self.client.query_points(
                collection_name=CASE_COLLECTION,
                query=query_vector,
                using="dense",  # 使用dense向量
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except Exception as e:
            print(f"[警告] 案例检索失败: {e}")
            return []

        formatted = []
        for p in results.points:
            formatted.append(
                {
                    "id": p.id,
                    "novel_name": p.payload.get("novel_name", "未知"),
                    "scene_type": p.payload.get("scene_type", "未知"),
                    "genre": p.payload.get("genre", "未知"),
                    "quality_score": p.payload.get("quality_score", 0),
                    "content": p.payload.get("content", ""),
                    "score": p.score,
                }
            )

        return formatted

    # ============================================================
    # 统计
    # ============================================================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {}

        # 小说设定库
        try:
            novel_info = self.client.get_collection(NOVEL_COLLECTION)
            stats["小说设定库"] = {
                "总数": novel_info.points_count,
                "状态": novel_info.status.value,
            }
        except Exception:
            stats["小说设定库"] = {"总数": 0, "状态": "不存在"}

        # 创作技法库
        try:
            tech_info = self.client.get_collection(TECHNIQUE_COLLECTION)
            stats["创作技法库"] = {
                "总数": tech_info.points_count,
                "状态": tech_info.status.value,
            }
        except Exception:
            stats["创作技法库"] = {"总数": 0, "状态": "不存在"}

        # 案例库
        try:
            case_info = self.client.get_collection(CASE_COLLECTION)
            stats["案例库"] = {
                "总数": case_info.points_count,
                "状态": case_info.status.value,
            }
        except Exception:
            stats["案例库"] = {"总数": 0, "状态": "不存在"}

        return stats


# ============================================================
# 命令行接口
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="统一知识检索工具 v4.0 (BGE-M3)")
    parser.add_argument("--query", "-q", type=str, help="查询文本")
    parser.add_argument("--type", "-t", type=str, help="实体类型")
    parser.add_argument("--dimension", "-d", type=str, help="技法维度")
    parser.add_argument("--scene", "-s", type=str, help="场景类型")
    parser.add_argument("--genre", "-g", type=str, help="题材类型")
    parser.add_argument("--source", type=str, help="数据源(novel/technique/case)")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="返回数量")
    parser.add_argument("--stats", action="store_true", help="显示统计")
    parser.add_argument("--list", type=str, help="列出某类型的所有条目")

    args = parser.parse_args()

    searcher = KnowledgeSearcher()

    if args.stats:
        stats = searcher.get_stats()
        print("=" * 60)
        print("Qdrant 数据库统计 (BGE-M3)")
        print("=" * 60)
        for source, info in stats.items():
            print(f"\n【{source}】")
            for k, v in info.items():
                print(f"  {k}: {v}")
        return

    if args.list:
        if args.list == "角色":
            names = searcher.list_characters()
        elif args.list == "势力":
            names = searcher.list_factions()
        elif args.list == "维度":
            names = searcher.list_technique_dimensions()
        else:
            names = []

        print(f"{args.list} 共 {len(names)} 条:")
        for name in names:
            print(f"  - {name}")
        return

    if not args.query:
        print("请提供查询文本 (--query)")
        return

    print(f"查询: {args.query}")
    print(f"参数: 类型={args.type}, 维度={args.dimension}, 场景={args.scene}")
    print("\n" + "=" * 60)

    # 根据source决定搜索哪个库
    if args.source == "novel" or (args.source is None and args.type):
        results = searcher.search_novel(args.query, args.type, args.top_k)
        if results:
            print("\n【小说设定】")
            for i, r in enumerate(results, 1):
                print(f"\n[{i}] {r['name']} ({r['type']}) - 相似度: {r['score']:.0%}")
                desc = r.get("description", "")[:150]
                if desc:
                    print(f"    {desc}...")

    if args.source == "technique" or (args.source is None and args.dimension):
        results = searcher.search_techniques(args.query, args.dimension, args.top_k)
        if results:
            print("\n【创作技法】")
            for i, r in enumerate(results, 1):
                print(
                    f"\n[{i}] {r['name']} ({r['dimension']}) - 相似度: {r['score']:.0%}"
                )
                content = r.get("content", "")[:150]
                if content:
                    print(f"    {content}...")

    if args.source == "case" or (args.source is None and args.scene):
        results = searcher.search_cases(args.query, args.scene, args.genre, args.top_k)
        if results:
            print("\n【标杆案例】")
            for i, r in enumerate(results, 1):
                print(
                    f"\n[{i}] {r['novel_name']} ({r['scene_type']}) - 相似度: {r['score']:.0%}"
                )
                content = r.get("content", "")[:150]
                if content:
                    print(f"    {content}...")


if __name__ == "__main__":
    main()
