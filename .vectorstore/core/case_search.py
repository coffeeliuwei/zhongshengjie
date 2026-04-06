#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案例库检索接口 v3.0 (BGE-M3 + Qdrant)
=====================================

从 Qdrant 向量库中检索标杆案例片段
使用 BGE-M3 Dense 向量检索 (1024维)

使用方法：
    from case_search import CaseSearcher

    searcher = CaseSearcher()

    # 检索开篇案例
    cases = searcher.search("玄幻开篇 主角出场", scene_type="开篇场景")

    # 按题材过滤
    cases = searcher.search("战斗描写", genre="玄幻奇幻")
"""

import os
import sys
import io

os.environ["HF_HUB_OFFLINE"] = "1"

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

from core.config_loader import (
    get_qdrant_url,
    get_project_root,
    get_model_path,
    get_case_library_dir,
)

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
CASE_LIBRARY_DIR = get_case_library_dir()

# Collection 名称 (v2版本)
CASE_COLLECTION = "case_library_v2"

# Docker Qdrant配置
QDRANT_DOCKER_URL = get_qdrant_url()

# BGE-M3 模型路径
BGE_M3_MODEL_PATH = get_model_path()

# 向量维度
VECTOR_SIZE = 1024

# 场景类型
SCENE_TYPES = [
    "开篇场景",
    "人物出场",
    "战斗场景",
    "对话场景",
    "情感场景",
    "悬念场景",
    "转折场景",
    "结尾场景",
    "环境场景",
    "心理场景",
    "打脸场景",
    "高潮场景",
]

# 题材类型
GENRES = [
    "玄幻奇幻",
    "武侠仙侠",
    "现代都市",
    "历史军事",
    "科幻灵异",
    "青春校园",
    "游戏竞技",
    "女频言情",
]


# ============================================================
# 案例检索器 (Qdrant版)
# ============================================================


class CaseSearcher:
    """案例检索器 - BGE-M3 + Docker Qdrant版本"""

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
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        min_score: float = 0.3,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        语义检索案例

        Args:
            query: 查询文本
            scene_type: 场景类型过滤
            genre: 题材类型过滤
            min_score: 最低相似度
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        query_vector = self._get_embedding(query)

        # 构建过滤条件
        must_conditions = []
        if scene_type:
            must_conditions.append(
                models.FieldCondition(
                    key="scene_type", match=models.MatchValue(value=scene_type)
                )
            )
        if genre:
            must_conditions.append(
                models.FieldCondition(key="genre", match=models.MatchValue(value=genre))
            )

        query_filter = None
        if must_conditions:
            query_filter = models.Filter(must=must_conditions)

        try:
            # 使用query_points进行检索
            results = self.client.query_points(
                collection_name=CASE_COLLECTION,
                query=query_vector,
                using="dense",  # 使用dense向量
                query_filter=query_filter,
                limit=top_k,
                score_threshold=min_score,
                with_payload=True,
            )
        except Exception as e:
            print(f"[错误] 检索失败: {e}")
            return []

        # 格式化结果
        formatted_results = []
        for r in results.points:
            payload = r.payload or {}
            formatted_results.append(
                {
                    "id": str(r.id),
                    "novel": payload.get("novel", payload.get("novel_name", "未知")),
                    "novel_name": payload.get(
                        "novel", payload.get("novel_name", "未知")
                    ),
                    "scene_type": payload.get("scene_type", "未知"),
                    "genre": payload.get("genre", "未知"),
                    "quality_score": payload.get("quality_score", 0),
                    "word_count": payload.get("word_count", 0),
                    "content": payload.get("content", "")[:5000],
                    "score": r.score,
                    "metadata": payload,
                }
            )

        return formatted_results

    def get_by_scene(self, scene_type: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """按场景类型获取案例"""
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="scene_type", match=models.MatchValue(value=scene_type)
                )
            ]
        )

        try:
            results = self.client.scroll(
                collection_name=CASE_COLLECTION,
                scroll_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except Exception:
            return []

        formatted_results = []
        for point in results[0]:
            payload = point.payload or {}
            formatted_results.append(
                {
                    "id": str(point.id),
                    "novel": payload.get("novel", "未知"),
                    "novel_name": payload.get("novel", "未知"),
                    "scene_type": payload.get("scene_type", "未知"),
                    "genre": payload.get("genre", "未知"),
                    "quality_score": payload.get("quality_score", 0),
                    "content": payload.get("content", "")[:5000],
                    "metadata": payload,
                }
            )

        return formatted_results

    def get_by_genre(self, genre: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """按题材类型获取案例"""
        query_filter = models.Filter(
            must=[
                models.FieldCondition(key="genre", match=models.MatchValue(value=genre))
            ]
        )

        try:
            results = self.client.scroll(
                collection_name=CASE_COLLECTION,
                scroll_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except Exception:
            return []

        formatted_results = []
        for point in results[0]:
            payload = point.payload or {}
            formatted_results.append(
                {
                    "id": str(point.id),
                    "novel": payload.get("novel", "未知"),
                    "novel_name": payload.get("novel", "未知"),
                    "scene_type": payload.get("scene_type", "未知"),
                    "genre": payload.get("genre", "未知"),
                    "quality_score": payload.get("quality_score", 0),
                    "content": payload.get("content", "")[:5000],
                    "metadata": payload,
                }
            )

        return formatted_results

    def count(self) -> int:
        """获取案例总数"""
        try:
            info = self.client.get_collection(CASE_COLLECTION)
            return info.points_count
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self.count()
        if total == 0:
            return {"总数": 0}

        # 从统计文件读取
        stats_file = CASE_LIBRARY_DIR / "unified_stats.json"
        if stats_file.exists():
            stats = json.load(open(stats_file, encoding="utf-8"))
            return {
                "总数": stats.get("total_cases", total),
                "按场景": stats.get("by_scene", {}),
            }

        return {"总数": total}

    def list_scene_types(self) -> List[str]:
        """列出所有场景类型"""
        return SCENE_TYPES

    def list_genres(self) -> List[str]:
        """列出所有题材类型"""
        return GENRES


def format_case(
    case: Dict[str, Any], show_content: bool = True, content_len: int = 300
) -> str:
    """格式化输出案例"""
    lines = []
    lines.append(f"【{case.get('novel', case.get('novel_name', '未知'))}】")
    lines.append(f"  场景: {case.get('scene_type', '未知')}")
    lines.append(f"  题材: {case.get('genre', '未知')}")
    lines.append(f"  质量: {case.get('quality_score', 0)}/10")
    lines.append(f"  字数: {case.get('word_count', 0)}")
    lines.append(f"  相似度: {case.get('score', 0):.4f}")

    if show_content:
        content = case.get("content", "")
        if len(content) > content_len:
            content = content[:content_len] + "..."
        lines.append(f"\n  内容预览:\n{content}")

    return "\n".join(lines)


# ============================================================
# 命令行接口
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="案例库检索工具 v2.0 (Qdrant)")
    parser.add_argument("--query", "-q", type=str, help="查询文本")
    parser.add_argument("--scene", "-s", type=str, help="场景类型过滤")
    parser.add_argument("--genre", "-g", type=str, help="题材类型过滤")
    parser.add_argument("--min-score", "-m", type=float, default=0.3, help="最低相似度")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="返回数量")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--list-scenes", action="store_true", help="列出所有场景类型")
    parser.add_argument("--list-genres", action="store_true", help="列出所有题材类型")

    args = parser.parse_args()

    searcher = CaseSearcher()

    if args.stats:
        stats = searcher.get_stats()
        print("=" * 60)
        print("案例库统计")
        print("=" * 60)
        print(f"总数: {stats.get('总数', 0):,}")

        if "按场景" in stats:
            print("\n按场景分布:")
            for scene, count in sorted(stats["按场景"].items(), key=lambda x: -x[1]):
                if count > 0:
                    print(f"  {scene}: {count:,}")
        return

    if args.list_scenes:
        scenes = searcher.list_scene_types()
        print("场景类型:")
        for s in scenes:
            print(f"  - {s}")
        return

    if args.list_genres:
        genres = searcher.list_genres()
        print("题材类型:")
        for g in genres:
            print(f"  - {g}")
        return

    if not args.query:
        print("请提供查询文本 (--query) 或使用 --stats/--list-scenes/--list-genres")
        return

    print(f"查询: {args.query}")
    print(f"过滤: scene={args.scene}, genre={args.genre}, min_score={args.min_score}")
    print("\n" + "=" * 60 + "\n")

    cases = searcher.search(
        query=args.query,
        scene_type=args.scene,
        genre=args.genre,
        min_score=args.min_score,
        top_k=args.top_k,
    )

    if not cases:
        print("未找到匹配的案例")
        return

    for i, case in enumerate(cases, 1):
        print(f"[{i}] " + format_case(case))
        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    main()
