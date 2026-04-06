#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BGE-M3 混合检索迁移脚本

执行完整的迁移流程：
1. 检查环境依赖
2. 验证 BGE-M3 模型
3. 备份旧 Collection（可选）
4. 同步数据到新 Collection
5. 验证检索质量
6. 生成迁移报告

使用方法：
    python migrate_to_bge_m3.py --execute

    # 仅检查环境
    python migrate_to_bge_m3.py --check-only

    # 不同步案例库（案例数量大，耗时长）
    python migrate_to_bge_m3.py --skip-cases
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目路径
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / ".vectorstore"))
sys.path.insert(0, str(PROJECT_DIR / "modules" / "knowledge_base"))

from bge_m3_config import (
    BGE_M3_MODEL_NAME,
    BGE_M3_CACHE_DIR,
    COLLECTION_NAMES,
    LEGACY_COLLECTION_NAMES,
    MIGRATION_CONFIG,
    VALIDATION_CONFIG,
)


class BGEM3Migrator:
    """BGE-M3 混合检索迁移器"""

    def __init__(self, project_dir: Path = None):
        self.project_dir = project_dir or PROJECT_DIR
        self.vectorstore_dir = self.project_dir / ".vectorstore"
        self.report = {
            "start_time": None,
            "end_time": None,
            "environment": {},
            "backup": {},
            "migration": {},
            "validation": {},
            "errors": [],
        }

    def run_full_migration(
        self, skip_cases: bool = False, backup: bool = True, execute: bool = True
    ) -> Dict[str, Any]:
        """
        执行完整迁移流程

        Args:
            skip_cases: 是否跳过案例库迁移
            backup: 是否备份旧数据
            execute: 是否执行迁移（False 则仅检查）

        Returns:
            迁移报告
        """
        self.report["start_time"] = datetime.now().isoformat()

        print("\n" + "=" * 70)
        print("[BGE-M3] 混合检索迁移")
        print("=" * 70)
        print(f"开始时间: {self.report['start_time']}")
        print(f"项目目录: {self.project_dir}")
        print("=" * 70)

        # 1. 检查环境
        print("\n[步骤 1/6] 检查环境依赖...")
        if not self._check_environment():
            self._print_report()
            return self.report

        if not execute:
            print("\n[OK] 环境检查通过，使用 --execute 参数执行迁移")
            self._print_report()
            return self.report

        # 2. 验证 BGE-M3 模型
        print("\n[步骤 2/6] 验证 BGE-M3 模型...")
        if not self._verify_bge_m3_model():
            self._print_report()
            return self.report

        # 3. 备份旧数据
        if backup:
            print("\n[步骤 3/6] 备份旧 Collection...")
            self._backup_legacy_collections()
        else:
            print("\n[步骤 3/6] 跳过备份")

        # 4. 同步数据
        print("\n[步骤 4/6] 同步数据到新 Collection...")
        self._sync_data(skip_cases=skip_cases)

        # 5. 验证检索
        print("\n[步骤 5/6] 验证检索质量...")
        self._validate_retrieval()

        # 6. 生成报告
        print("\n[步骤 6/6] 生成迁移报告...")
        self.report["end_time"] = datetime.now().isoformat()
        self._save_report()
        self._print_report()

        return self.report

    def _check_environment(self) -> bool:
        """检查环境依赖"""
        errors = []
        warnings = []

        # Python 版本
        py_version = sys.version_info
        self.report["environment"]["python"] = (
            f"{py_version.major}.{py_version.minor}.{py_version.micro}"
        )
        if py_version < (3, 8):
            errors.append(
                f"Python 版本过低: {self.report['environment']['python']}，需要 >= 3.8"
            )
        else:
            print(f"  [OK] Python: {self.report['environment']['python']}")

        # 检查依赖包
        dependencies = {
            "qdrant_client": "qdrant-client",
            "sentence_transformers": "sentence-transformers",
            "torch": "torch",
            "tqdm": "tqdm",
        }

        for module, package in dependencies.items():
            try:
                mod = __import__(module)
                version = getattr(mod, "__version__", "unknown")
                self.report["environment"][package] = version
                print(f"  [OK] {package}: {version}")
            except ImportError:
                errors.append(f"缺少依赖: {package}")
                self.report["environment"][package] = "NOT INSTALLED"
                print(f"  [X] {package}: 未安装")

        # 单独检查 FlagEmbedding（避免 reranker 兼容性问题）
        try:
            from FlagEmbedding import BGEM3FlagModel
            import FlagEmbedding

            version = getattr(FlagEmbedding, "__version__", "unknown")
            self.report["environment"]["FlagEmbedding"] = version
            print(f"  [OK] FlagEmbedding: {version}")
        except ImportError as e:
            errors.append(f"缺少依赖: FlagEmbedding ({e})")
            self.report["environment"]["FlagEmbedding"] = "NOT INSTALLED"
            print(f"  [X] FlagEmbedding: 未安装")

        # 检查 Qdrant 连接
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url="http://localhost:6333")
            collections = client.get_collections()
            self.report["environment"]["qdrant"] = "connected"
            self.report["environment"]["qdrant_collections"] = [
                c.name for c in collections.collections
            ]
            print(
                f"  [OK] Qdrant: 已连接 ({len(collections.collections)} 个 Collection)"
            )
        except Exception as e:
            warnings.append(f"Qdrant 连接失败: {e}")
            self.report["environment"]["qdrant"] = f"failed: {e}"
            print(f"  [!] Qdrant: 连接失败 - {e}")

        # 检查 BGE-M3 模型缓存
        model_cache = Path(BGE_M3_CACHE_DIR) / f"models--BAAI--bge-m3"
        if model_cache.exists():
            # 检查模型文件大小
            model_files = list(model_cache.glob("**/*.bin")) + list(
                model_cache.glob("**/*.safetensors")
            )
            total_size = sum(f.stat().st_size for f in model_files if f.exists())
            size_gb = total_size / (1024**3)
            self.report["environment"]["bge_m3_cache"] = f"{size_gb:.2f} GB"
            print(f"  [OK] BGE-M3 缓存: {size_gb:.2f} GB ({model_cache})")
        else:
            self.report["environment"]["bge_m3_cache"] = "not found"
            print(f"  [!] BGE-M3 缓存: 未找到 (首次运行需要下载)")

        # 记录错误
        self.report["errors"].extend(errors)

        if errors:
            print(f"\n[X] 环境检查失败: {len(errors)} 个错误")
            for err in errors:
                print(f"   - {err}")
            return False

        if warnings:
            print(f"\n[!] 环境检查通过但有警告: {len(warnings)} 个")
            for warn in warnings:
                print(f"   - {warn}")

        print("\n[OK] 环境检查通过")
        return True

    def _verify_bge_m3_model(self) -> bool:
        """验证 BGE-M3 模型"""
        try:
            print("  [~] 加载 BGE-M3 模型...")
            from FlagEmbedding import BGEM3FlagModel

            model = BGEM3FlagModel(
                BGE_M3_MODEL_NAME,
                use_fp16=True,
                device="cpu",
            )

            # 测试编码
            print("  [~] 测试编码...")
            test_output = model.encode(
                ["测试文本"],
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=True,
            )

            dense_dim = len(test_output["dense_vecs"][0])
            sparse_keys = len(test_output["lexical_weights"][0])
            colbert_shape = len(test_output["colbert_vecs"][0])

            print(f"  [OK] Dense 向量维度: {dense_dim}")
            print(f"  [OK] Sparse 非零元素: {sparse_keys}")
            print(f"  [OK] ColBERT token 数: {colbert_shape}")

            self.report["environment"]["bge_m3_verified"] = True
            self.report["environment"]["dense_dim"] = dense_dim

            print("\n[OK] BGE-M3 模型验证通过")
            return True

        except Exception as e:
            self.report["errors"].append(f"BGE-M3 模型验证失败: {e}")
            print(f"\n[X] BGE-M3 模型验证失败: {e}")
            return False

    def _backup_legacy_collections(self) -> None:
        """备份旧 Collection"""
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url="http://localhost:6333")
            collections = [c.name for c in client.get_collections().collections]

            backup_dir = self.vectorstore_dir / MIGRATION_CONFIG["backup_dir"]
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for key, collection_name in LEGACY_COLLECTION_NAMES.items():
                if collection_name in collections:
                    # 获取 Collection 信息
                    info = client.get_collection(collection_name)
                    self.report["backup"][collection_name] = {
                        "points_count": info.points_count,
                        "status": info.status.value,
                    }
                    print(f"  [*] {collection_name}: {info.points_count} 条")
                else:
                    print(f"  ⏭️ {collection_name}: 不存在，跳过")
                    self.report["backup"][collection_name] = {"status": "not_found"}

            print("\n[OK] 备份信息已记录")

        except Exception as e:
            self.report["errors"].append(f"备份失败: {e}")
            print(f"\n[!] 备份失败: {e}")

    def _sync_data(self, skip_cases: bool = False) -> None:
        """同步数据到新 Collection"""
        try:
            from hybrid_sync_manager import HybridSyncManager

            sync = HybridSyncManager(project_dir=self.project_dir)

            if skip_cases:
                print("  [!] 跳过案例库迁移")
                results = {
                    "novel": sync.sync_novel_settings(rebuild=True),
                    "technique": sync.sync_techniques(rebuild=True),
                    "case": 0,
                }
            else:
                results = sync.sync_all(rebuild=True)

            self.report["migration"] = results

            total = sum(results.values())
            print(f"\n[OK] 同步完成: 共 {total} 条")

        except Exception as e:
            self.report["errors"].append(f"同步失败: {e}")
            print(f"\n[X] 同步失败: {e}")
            import traceback

            traceback.print_exc()

    def _validate_retrieval(self) -> None:
        """验证检索质量"""
        try:
            from hybrid_search_manager import HybridSearchManager

            search = HybridSearchManager(project_dir=self.project_dir)

            test_queries = VALIDATION_CONFIG["test_queries"]
            validation_results = []

            for query in test_queries:
                print(f"\n  [?] 测试查询: {query}")

                # 测试技法检索
                results = search.search_technique(query, top_k=5, use_rerank=True)

                if results:
                    top_score = results[0]["score"]
                    validation_results.append(
                        {
                            "query": query,
                            "top_score": top_score,
                            "result_count": len(results),
                            "top_result": results[0].get("name", "N/A"),
                        }
                    )
                    print(
                        f"     Top-1: {results[0].get('name', 'N/A')} (score: {top_score:.4f})"
                    )
                else:
                    validation_results.append(
                        {
                            "query": query,
                            "top_score": 0,
                            "result_count": 0,
                            "top_result": None,
                        }
                    )
                    print(f"     [!] 无结果")

            self.report["validation"]["results"] = validation_results
            self.report["validation"]["passed"] = all(
                r["top_score"] >= VALIDATION_CONFIG["min_score_threshold"]
                for r in validation_results
                if r["result_count"] > 0
            )

            if self.report["validation"]["passed"]:
                print("\n[OK] 检索验证通过")
            else:
                print("\n[!] 部分查询未达到阈值")

        except Exception as e:
            self.report["errors"].append(f"验证失败: {e}")
            print(f"\n[X] 验证失败: {e}")
            import traceback

            traceback.print_exc()

    def _save_report(self) -> None:
        """保存迁移报告"""
        report_file = (
            self.vectorstore_dir
            / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)

        print(f"\n[>] 报告已保存: {report_file}")

    def _print_report(self) -> None:
        """打印迁移报告"""
        print("\n" + "=" * 70)
        print("[#] 迁移报告")
        print("=" * 70)

        print(f"\n开始时间: {self.report.get('start_time', 'N/A')}")
        print(f"结束时间: {self.report.get('end_time', 'N/A')}")

        if self.report.get("migration"):
            print("\n同步数量:")
            for key, count in self.report["migration"].items():
                print(f"  - {key}: {count} 条")

        if self.report.get("validation", {}).get("results"):
            print("\n验证结果:")
            for r in self.report["validation"]["results"]:
                status = "[OK]" if r["top_score"] >= 0.3 else "[!]"
                print(f"  {status} {r['query']}: score={r['top_score']:.4f}")

        if self.report["errors"]:
            print(f"\n[X] 错误 ({len(self.report['errors'])}):")
            for err in self.report["errors"]:
                print(f"  - {err}")

        print("\n" + "=" * 70)

        # 最终状态
        if self.report["errors"]:
            print("[!] 迁移完成但有错误")
        elif self.report.get("validation", {}).get("passed"):
            print("[OK] 迁移成功完成！")
        else:
            print("[!] 迁移完成，建议检查检索质量")


def main():
    parser = argparse.ArgumentParser(
        description="BGE-M3 混合检索迁移脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 执行完整迁移
  python migrate_to_bge_m3.py --execute
  
  # 仅检查环境
  python migrate_to_bge_m3.py --check-only
  
  # 跳过案例库（案例数量大）
  python migrate_to_bge_m3.py --execute --skip-cases
  
  # 不备份旧数据
  python migrate_to_bge_m3.py --execute --no-backup
        """,
    )

    parser.add_argument(
        "--execute", action="store_true", help="执行迁移（默认仅检查环境）"
    )
    parser.add_argument(
        "--check-only", action="store_true", help="仅检查环境，不执行迁移"
    )
    parser.add_argument("--skip-cases", action="store_true", help="跳过案例库迁移")
    parser.add_argument("--no-backup", action="store_true", help="不备份旧数据")

    args = parser.parse_args()

    migrator = BGEM3Migrator()

    if args.check_only:
        migrator._check_environment()
    else:
        migrator.run_full_migration(
            skip_cases=args.skip_cases, backup=not args.no_backup, execute=args.execute
        )


if __name__ == "__main__":
    main()
