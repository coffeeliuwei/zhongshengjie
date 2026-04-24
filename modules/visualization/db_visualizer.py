#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库可视化模块
提供向量数据库的数据查看和分析功能

功能:
    - ChromaDB/Qdrant 数据查看
    - 技法库和知识库统计
    - 数据质量分析
    - 支持 Streamlit Web UI 和命令行输出
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from qdrant_client import QdrantClient
except ImportError:
    QdrantClient = None

# [N14 2026-04-18] 改为 core 包内的 config_loader
try:
    import sys

    _project_root = Path(__file__).parent.parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    from core.config_loader import get_project_root, get_qdrant_url
except ImportError:
    import os

    def get_project_root():
        return Path.cwd()

    def get_qdrant_url():
        return os.environ.get("QDRANT_URL", "http://localhost:6333")


# ============================================================
# 数据库可视化类
# ============================================================


class DBVisualizer:
    """数据库可视化器

    支持功能:
        - 连接 ChromaDB 和 Qdrant
        - 查询数据库内容
        - 统计数据分布
        - 分析数据质量
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化

        Args:
            project_root: 项目根目录，默认从配置自动获取
        """
        self.project_root = project_root or get_project_root()
        self.vectorstore_dir = self.project_root / ".vectorstore"
        self.chroma_client = None
        self.qdrant_client = None

    def _connect_chroma(self) -> Optional[Any]:
        """连接 ChromaDB"""
        if chromadb is None:
            print("警告: chromadb 未安装")
            return None

        chroma_path = self.vectorstore_dir / "chroma"
        if not chroma_path.exists():
            print(f"ChromaDB 目录不存在: {chroma_path}")
            return None

        try:
            client = chromadb.PersistentClient(path=str(chroma_path))
            print(f"连接: ChromaDB {chroma_path}")
            return client
        except Exception as e:
            print(f"连接失败: {e}")
            return None

    def _connect_qdrant(self) -> Optional[Any]:
        """连接 Qdrant"""
        if QdrantClient is None:
            print("警告: qdrant_client 未安装")
            return None

        # 从配置获取 URL
        qdrant_url = get_qdrant_url()

        # 尝试 Docker 连接
        try:
            client = QdrantClient(url=qdrant_url)
            client.get_collections()
            print(f"连接: Qdrant ({qdrant_url})")
            return client
        except Exception as e:
            print(f"Qdrant连接失败: {e}")
            pass

        # 回退到本地文件
        qdrant_path = self.vectorstore_dir / "qdrant"
        if qdrant_path.exists():
            client = QdrantClient(path=str(qdrant_path))
            print(f"连接: 本地 Qdrant {qdrant_path}")
            return client

        return None

    def get_collection_stats(
        self, collection_name: str, db_type: str = "qdrant"
    ) -> Dict:
        """
        获取集合统计信息

        Args:
            collection_name: 集合名称
            db_type: 数据库类型 (qdrant/chroma)

        Returns:
            统计信息字典
        """
        stats = {
            "collection": collection_name,
            "total": 0,
            "types": {},
            "lengths": {"<100": 0, "100-300": 0, "300-1000": 0, ">1000": 0},
            "sources": {},
            "quality": {"missing_content": 0, "empty_metadata": 0},
        }

        if db_type == "qdrant":
            client = self._connect_qdrant()
            if client is None:
                return stats

            try:
                points = client.scroll(
                    collection_name=collection_name,
                    limit=5000,
                    with_payload=True,
                    with_vectors=False,
                )[0]

                stats["total"] = len(points)

                for point in points:
                    payload = point.payload

                    # 类型统计
                    type_key = payload.get("type", payload.get("维度", "未知"))
                    stats["types"][type_key] = stats["types"].get(type_key, 0) + 1

                    # 内容长度
                    content = payload.get("content", payload.get("description", ""))
                    length = len(content)
                    if length < 100:
                        stats["lengths"]["<100"] += 1
                    elif length < 300:
                        stats["lengths"]["100-300"] += 1
                    elif length < 1000:
                        stats["lengths"]["300-1000"] += 1
                    else:
                        stats["lengths"][">1000"] += 1

                    # 来源统计
                    source = payload.get("source", payload.get("来源文件", "未知"))
                    stats["sources"][source] = stats["sources"].get(source, 0) + 1

                    # 质量检查
                    if not content:
                        stats["quality"]["missing_content"] += 1
                    if not payload:
                        stats["quality"]["empty_metadata"] += 1

            except Exception as e:
                print(f"查询失败: {e}")

        elif db_type == "chroma":
            client = self._connect_chroma()
            if client is None:
                return stats

            try:
                collection = client.get_collection(collection_name)
                all_data = collection.get()

                stats["total"] = len(all_data["ids"])

                for i in range(len(all_data["ids"])):
                    meta = all_data["metadatas"][i]
                    doc = all_data["documents"][i]

                    # 类型统计
                    type_key = meta.get("类型", meta.get("维度", "未知"))
                    stats["types"][type_key] = stats["types"].get(type_key, 0) + 1

                    # 内容长度
                    length = len(doc)
                    if length < 100:
                        stats["lengths"]["<100"] += 1
                    elif length < 300:
                        stats["lengths"]["100-300"] += 1
                    elif length < 1000:
                        stats["lengths"]["300-1000"] += 1
                    else:
                        stats["lengths"][">1000"] += 1

                    # 来源统计
                    source = meta.get("来源文件", meta.get("source", "未知"))
                    stats["sources"][source] = stats["sources"].get(source, 0) + 1

                    # 质量检查
                    if not doc:
                        stats["quality"]["missing_content"] += 1

            except Exception as e:
                print(f"查询失败: {e}")

        return stats

    def list_collections(self, db_type: str = "qdrant") -> List[str]:
        """
        列出所有集合

        Args:
            db_type: 数据库类型

        Returns:
            集合名称列表
        """
        if db_type == "qdrant":
            client = self._connect_qdrant()
            if client:
                try:
                    collections = client.get_collections()
                    return [c.name for c in collections.collections]
                except Exception as e:
                    print(f"获取Qdrant集合失败: {e}")
                    return []

        elif db_type == "chroma":
            client = self._connect_chroma()
            if client:
                try:
                    collections = client.list_collections()
                    return [c.name for c in collections]
                except Exception as e:
                    print(f"获取Chroma集合失败: {e}")
                    return []

        return []

    def generate_report(
        self, db_type: str = "qdrant", output: Optional[Path] = None
    ) -> Dict:
        """
        生成数据库报告

        Args:
            db_type: 数据库类型
            output: 输出文件路径

        Returns:
            报告数据
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "database": db_type,
            "collections": {},
        }

        collections = self.list_collections(db_type)

        for collection_name in collections:
            print(f"统计集合: {collection_name}")
            stats = self.get_collection_stats(collection_name, db_type)
            report["collections"][collection_name] = stats

        # 保存报告
        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"报告已保存: {output}")

        return report

    def print_summary(self, report: Dict):
        """
        打印报告摘要

        Args:
            report: 报告数据
        """
        print("\n" + "=" * 60)
        print(f"数据库报告 - {report['database']}")
        print("=" * 60)
        print(f"生成时间: {report['timestamp']}")

        for collection_name, stats in report["collections"].items():
            print(f"\n【{collection_name}】")
            print(f"  总记录: {stats['total']}")

            print(f"\n  类型分布:")
            for type_name, count in sorted(stats["types"].items(), key=lambda x: -x[1]):
                print(f"    {type_name}: {count}")

            print(f"\n  内容长度分布:")
            for length_range, count in stats["lengths"].items():
                print(f"    {length_range}: {count}")

            print(f"\n  数据质量:")
            print(f"    缺失内容: {stats['quality']['missing_content']}")
            print(f"    空元数据: {stats['quality']['empty_metadata']}")

    def check_data_integrity(
        self, collection_name: str, db_type: str = "qdrant"
    ) -> Dict:
        """
        检查数据完整性

        Args:
            collection_name: 集合名称
            db_type: 数据库类型

        Returns:
            完整性检查结果
        """
        integrity = {
            "collection": collection_name,
            "issues": [],
            "warnings": [],
            "passed": [],
        }

        stats = self.get_collection_stats(collection_name, db_type)

        # 检查问题
        if stats["quality"]["missing_content"] > 0:
            integrity["issues"].append(
                f"{stats['quality']['missing_content']} 条记录缺失内容"
            )

        if stats["quality"]["empty_metadata"] > 0:
            integrity["issues"].append(
                f"{stats['quality']['empty_metadata']} 条记录元数据为空"
            )

        # 检查警告
        if stats["total"] == 0:
            integrity["warnings"].append("集合为空")

        if stats["lengths"]["<100"] > stats["total"] * 0.5:
            integrity["warnings"].append("超过 50% 的记录内容少于 100 字")

        # 检查通过
        if stats["total"] > 0:
            integrity["passed"].append(f"包含 {stats['total']} 条记录")

        if len(integrity["issues"]) == 0:
            integrity["passed"].append("所有记录都有内容")

        return integrity


# ============================================================
# 命令行入口
# ============================================================


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="数据库可视化")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--report", action="store_true", help="生成完整报告")
    parser.add_argument(
        "--db", choices=["qdrant", "chroma"], default="qdrant", help="数据库类型"
    )
    parser.add_argument("--output", type=str, help="输出文件路径")

    args = parser.parse_args()

    viz = DBVisualizer()

    if args.stats:
        collections = viz.list_collections(args.db)
        for collection in collections:
            stats = viz.get_collection_stats(collection, args.db)
            print(f"\n【{collection}】总记录: {stats['total']}")

    if args.report:
        output = Path(args.output) if args.output else None
        report = viz.generate_report(args.db, output)
        viz.print_summary(report)

    if not args.stats and not args.report:
        print("请指定 --stats 或 --report")


if __name__ == "__main__":
    main()
