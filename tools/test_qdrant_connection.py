#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qdrant向量数据库连接和数据完整性测试
=======================================

测试内容：
1. Docker Qdrant连接
2. Collection数据量检查
3. 数据完整性测试（向量维度、sparse向量、payload完整性）
4. 检索功能测试
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Optional

sys.stdout.reconfigure(encoding="utf-8")

# 从统一配置获取 Qdrant URL
_project_root = Path(__file__).parent.parent if 'Path' in dir() else __import__('pathlib').Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))
try:
    from core.config_loader import get_qdrant_url
    _QDRANT_URL = get_qdrant_url()
except ImportError:
    _QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")

# ==================== 测试结果收集 ====================

test_results = {
    "connection": {"status": "FAIL", "url": _QDRANT_URL, "error": None},
    "collections": {},
    "integrity": {
        "vector_dimension": {"expected": 1024, "actual": None, "status": "FAIL"},
        "sparse_vector": {"status": "FAIL", "details": None},
        "payload_integrity": {"rate": 0, "status": "FAIL", "details": []},
    },
    "retrieval": {},
    "errors": [],
}

# ==================== 1. 连接测试 ====================


def test_connection() -> bool:
    """测试Qdrant连接"""
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=_QDRANT_URL, timeout=10)

        # 测试 get_collections()
        start_time = time.time()
        collections_response = client.get_collections()
        latency = (time.time() - start_time) * 1000

        test_results["connection"]["status"] = "OK"
        test_results["connection"]["latency_ms"] = round(latency, 2)
        test_results["connection"]["collections_count"] = len(
            collections_response.collections
        )

        return True

    except Exception as e:
        test_results["connection"]["status"] = "FAIL"
        test_results["connection"]["error"] = str(e)
        test_results["errors"].append(f"连接错误: {e}")
        return False


# ==================== 2. Collection测试 ====================


def test_collections(client) -> Dict[str, Dict]:
    """测试各Collection数据量"""
    collections_to_test = {
        "case_library_v2": "案例库",
        "writing_techniques_v2": "技法库",
        "novel_settings_v2": "设定库",
    }

    results = {}

    for collection_name, description in collections_to_test.items():
        try:
            info = client.get_collection(collection_name)
            points_count = info.points_count

            # 检查向量配置
            vectors_config = info.config.params.vectors
            vector_size = None

            # 处理不同的向量配置格式
            if hasattr(vectors_config, "size"):
                vector_size = vectors_config.size
            elif isinstance(vectors_config, dict):
                # 可能是named vectors
                for vec_name, vec_config in vectors_config.items():
                    if hasattr(vec_config, "size"):
                        vector_size = vec_config.size
                        break

            results[collection_name] = {
                "description": description,
                "points": points_count,
                "status": "OK" if points_count > 0 else "FAIL",
                "vector_size": vector_size,
            }

        except Exception as e:
            results[collection_name] = {
                "description": description,
                "points": 0,
                "status": "FAIL",
                "error": str(e),
            }
            test_results["errors"].append(f"{collection_name} 错误: {e}")

    test_results["collections"] = results
    return results


# ==================== 3. 数据完整性测试 ====================


def test_data_integrity(client, collections: Dict) -> Dict:
    """测试数据完整性"""
    integrity_results = test_results["integrity"]

    # 检查向量维度
    vector_sizes_found = []
    for collection_name, data in collections.items():
        if data.get("vector_size"):
            vector_sizes_found.append(data["vector_size"])

    if vector_sizes_found:
        # 所有collection应该都是1024
        all_1024 = all(v == 1024 for v in vector_sizes_found)
        integrity_results["vector_dimension"]["actual"] = (
            vector_sizes_found[0]
            if len(set(vector_sizes_found)) == 1
            else vector_sizes_found
        )
        integrity_results["vector_dimension"]["status"] = "OK" if all_1024 else "FAIL"

    # 抽样检查数据完整性
    total_checked = 0
    total_complete = 0
    sparse_found = 0
    payload_issues = []

    for collection_name in [
        "case_library_v2",
        "writing_techniques_v2",
        "novel_settings_v2",
    ]:
        try:
            # 滚动获取样本数据
            points, _ = client.scroll(
                collection_name=collection_name,
                limit=5,  # 每个 collection 抽取5条
                with_payload=True,
                with_vectors=True,  # 获取向量数据
            )

            for point in points:
                total_checked += 1

                # 检查payload完整性
                payload = point.payload or {}
                has_required_fields = len(payload) > 0

                # 检查向量
                vector = point.vector

                # 检查dense向量
                has_dense_vector = False
                dense_dim = None

                if vector:
                    # 处理不同向量格式
                    from qdrant_client.http.models import SparseVector

                    if isinstance(vector, dict):
                        # named vectors - 检查是否有default或其他
                        for vec_name, vec_data in vector.items():
                            if isinstance(vec_data, SparseVector):
                                # Sparse向量
                                has_sparse_vector = True
                                sparse_found += 1
                            elif vec_data and not isinstance(vec_data, SparseVector):
                                try:
                                    vec_len = len(vec_data)
                                    has_dense_vector = True
                                    dense_dim = vec_len
                                except TypeError:
                                    pass
                    elif isinstance(vector, list):
                        has_dense_vector = len(vector) == 1024
                        dense_dim = len(vector) if has_dense_vector else None
                    elif not isinstance(vector, SparseVector):
                        # 尝试获取长度
                        try:
                            vec_len = len(vector)
                            has_dense_vector = vec_len == 1024
                            dense_dim = vec_len
                        except TypeError:
                            pass

                # 更新向量维度检查结果
                if dense_dim == 1024:
                    integrity_results["vector_dimension"]["actual"] = 1024
                    integrity_results["vector_dimension"]["status"] = "OK"

                # 检查payload必要字段
                if has_required_fields and has_dense_vector:
                    total_complete += 1
                else:
                    issue = {
                        "collection": collection_name,
                        "id": str(point.id),
                        "missing": [],
                    }
                    if not has_required_fields:
                        issue["missing"].append("payload")
                    if not has_dense_vector:
                        issue["missing"].append("dense_vector")
                    payload_issues.append(issue)

        except Exception as e:
            test_results["errors"].append(f"数据完整性检查 {collection_name}: {e}")

    # 计算完整性率
    if total_checked > 0:
        integrity_results["payload_integrity"]["rate"] = round(
            total_complete / total_checked * 100, 1
        )
        integrity_results["payload_integrity"]["status"] = (
            "OK" if integrity_results["payload_integrity"]["rate"] >= 95 else "FAIL"
        )
        integrity_results["payload_integrity"]["details"] = payload_issues

    # Sparse向量状态
    integrity_results["sparse_vector"]["status"] = "OK" if sparse_found > 0 else "FAIL"
    integrity_results["sparse_vector"]["details"] = f"发现 {sparse_found} 条sparse向量"

    return integrity_results


# ==================== 4. 检索功能测试 ====================


def test_retrieval(client) -> Dict:
    """测试scroll检索功能"""
    retrieval_results = {}

    for collection_name in [
        "case_library_v2",
        "writing_techniques_v2",
        "novel_settings_v2",
    ]:
        try:
            # 执行scroll检索
            points, next_offset = client.scroll(
                collection_name=collection_name,
                limit=3,
                with_payload=True,
                with_vectors=False,
            )

            # 检查返回数据结构
            data_structure_valid = True
            sample_payloads = []

            for point in points:
                if not hasattr(point, "id") or not hasattr(point, "payload"):
                    data_structure_valid = False
                else:
                    sample_payloads.append(
                        {
                            "id": str(point.id),
                            "payload_keys": list(point.payload.keys())
                            if point.payload
                            else [],
                        }
                    )

            retrieval_results[collection_name] = {
                "status": "OK" if data_structure_valid and len(points) > 0 else "FAIL",
                "points_returned": len(points),
                "has_next_offset": next_offset is not None,
                "sample_payload_keys": sample_payloads[0]["payload_keys"]
                if sample_payloads
                else [],
            }

        except Exception as e:
            retrieval_results[collection_name] = {"status": "FAIL", "error": str(e)}
            test_results["errors"].append(f"检索测试 {collection_name}: {e}")

    test_results["retrieval"] = retrieval_results
    return retrieval_results


# ==================== 主测试流程 ====================


def run_all_tests():
    """运行全部测试"""
    print("## 向量数据库测试报告")
    print()

    # 1. 连接测试
    print("### 1. 连接状态")
    connection_ok = test_connection()

    if connection_ok:
        print(f"- [OK] Docker Qdrant连接")
        print(f"- URL: {test_results['connection']['url']}")
        print(f"- 响应时间: {test_results['connection']['latency_ms']}ms")
        print(f"- Collections总数: {test_results['connection']['collections_count']}")
    else:
        print(f"- [FAIL] Docker Qdrant连接")
        print(f"- URL: {test_results['connection']['url']}")
        if test_results["connection"]["error"]:
            print(f"- 错误: {test_results['connection']['error']}")
        # 连接失败则终止测试
        print_test_summary()
        return
    print()

    # 创建客户端
    from qdrant_client import QdrantClient

    client = QdrantClient(url=_QDRANT_URL, timeout=10)

    # 2. Collection测试
    print("### 2. Collections状态")
    collections = test_collections(client)

    print("| Collection | Points | Status |")
    print("|------------|--------|--------|")
    for collection_name, data in collections.items():
        status_mark = "✅" if data["status"] == "OK" else "❌"
        print(f"| {collection_name} | {data['points']} | {status_mark} |")
    print()

    # 3. 数据完整性测试
    print("### 3. 数据完整性")
    integrity = test_data_integrity(client, collections)

    # 向量维度
    vec_dim = integrity["vector_dimension"]
    dim_mark = "✅" if vec_dim["status"] == "OK" else "❌"
    print(
        f"- 向量维度: {vec_dim['actual'] or 'N/A'} [{vec_dim['status']}] (期望: {vec_dim['expected']})"
    )

    # Sparse向量
    sparse = integrity["sparse_vector"]
    sparse_mark = "✅" if sparse["status"] == "OK" else "❌"
    print(f"- Sparse向量: [{sparse['status']}] {sparse['details'] or '未发现'}")

    # Payload完整性
    payload = integrity["payload_integrity"]
    payload_mark = "✅" if payload["status"] == "OK" else "❌"
    print(f"- Payload完整率: {payload['rate']}% [{payload['status']}]")

    if payload["details"]:
        print(f"  - 不完整数据数: {len(payload['details'])}")
    print()

    # 4. 检索功能测试
    print("### 4. 检索功能测试")
    retrieval = test_retrieval(client)

    for collection_name, data in retrieval.items():
        status_mark = "✅" if data["status"] == "OK" else "❌"
        print(
            f"- {collection_name}: [{data['status']}] 返回{data.get('points_returned', 0)}条"
        )
        if data.get("sample_payload_keys"):
            print(f"  - Payload字段: {', '.join(data['sample_payload_keys'][:5])}")
    print()

    # 5. 错误详情
    print_test_summary()


def print_test_summary():
    """打印测试总结"""
    if test_results["errors"]:
        print("### 5. 错误详情")
        for error in test_results["errors"]:
            print(f"- {error}")
        print()

    # 统计测试结果
    total_tests = 0
    passed_tests = 0

    # 连接测试
    total_tests += 1
    if test_results["connection"]["status"] == "OK":
        passed_tests += 1

    # Collection测试
    for collection_name, data in test_results["collections"].items():
        total_tests += 1
        if data["status"] == "OK":
            passed_tests += 1

    # 完整性测试
    for key in ["vector_dimension", "sparse_vector", "payload_integrity"]:
        total_tests += 1
        if test_results["integrity"][key]["status"] == "OK":
            passed_tests += 1

    # 检索测试
    for collection_name, data in test_results["retrieval"].items():
        total_tests += 1
        if data["status"] == "OK":
            passed_tests += 1

    print("---")
    print(f"测试总计: {passed_tests}/{total_tests} 通过")


# ==================== 执行测试 ====================

if __name__ == "__main__":
    run_all_tests()
