#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置系统测试脚本
验证所有配置API函数正常工作
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 导入配置加载器
from core.config_loader import (
    get_config,
    get_project_root,
    get_config_path,
    get_settings_dir,
    get_techniques_dir,
    get_vectorstore_dir,
    get_case_library_dir,
    get_logs_dir,
    get_qdrant_url,
    get_collection_name,
    get_model_path,
    get_hf_cache_dir,
    get_novel_sources,
    reset_config,
)

# 测试结果存储
test_results = {"passed": [], "failed": [], "details": {}}


def _check_api(api_name: str, func, expected_type=None, path_check=False):
    """通用API检查函数（非pytest测试）"""
    try:
        result = func()

        # 类型检查
        type_ok = True
        if expected_type:
            type_ok = isinstance(result, expected_type)

        # 路径存在检查（如果是路径且需要检查）
        path_exists = True
        if path_check and isinstance(result, Path):
            path_exists = result.exists()

        # 判断是否通过
        passed = type_ok and path_exists

        if passed:
            test_results["passed"].append(api_name)
            test_results["details"][api_name] = {
                "status": "OK",
                "result": str(result),
                "type": type(result).__name__,
                "path_exists": path_exists if isinstance(result, Path) else "N/A",
            }
        else:
            test_results["failed"].append(api_name)
            test_results["details"][api_name] = {
                "status": "FAIL",
                "result": str(result),
                "type": type(result).__name__,
                "type_expected": expected_type.__name__ if expected_type else "N/A",
                "path_exists": path_exists if isinstance(result, Path) else "N/A",
                "error": f"Type mismatch or path not exists",
            }

        print(
            f"  [{passed and 'OK' or 'FAIL'}] {api_name}() -> {type(result).__name__}: {result}"
        )

    except Exception as e:
        test_results["failed"].append(api_name)
        test_results["details"][api_name] = {
            "status": "FAIL",
            "result": "ERROR",
            "error": str(e),
        }
        print(f"  [FAIL] {api_name}() -> ERROR: {e}")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("众生界配置系统测试")
    print("=" * 60)

    # 重置配置确保干净状态
    reset_config()

    # ==================== 1. 基础配置 ====================
    print("\n### 1. 基础配置")

    _check_api("get_config", get_config, dict)
    _check_api("get_project_root", get_project_root, Path, path_check=True)
    _check_api("get_config_path", get_config_path, Path)

    # ==================== 2. 路径API ====================
    print("\n### 2. 路径API")

    _check_api("get_settings_dir", get_settings_dir, Path)
    _check_api("get_techniques_dir", get_techniques_dir, Path)
    _check_api("get_vectorstore_dir", get_vectorstore_dir, Path, path_check=True)
    _check_api("get_case_library_dir", get_case_library_dir, Path)
    _check_api("get_logs_dir", get_logs_dir, Path)

    # ==================== 3. 数据库API ====================
    print("\n### 3. 数据库API")

    _check_api("get_qdrant_url", get_qdrant_url, str)

    # 测试collection_name (需要参数)
    try:
        result = get_collection_name("novel_settings")
        expected = "novel_settings_v2"
        passed = result == expected

        if passed:
            test_results["passed"].append("get_collection_name")
            test_results["details"]["get_collection_name"] = {
                "status": "OK",
                "result": result,
                "expected": expected,
            }
        else:
            test_results["failed"].append("get_collection_name")
            test_results["details"]["get_collection_name"] = {
                "status": "FAIL",
                "result": result,
                "expected": expected,
                "error": f"Expected {expected}, got {result}",
            }
        print(
            f"  [{passed and 'OK' or 'FAIL'}] get_collection_name('novel_settings') -> {result}"
        )
    except Exception as e:
        test_results["failed"].append("get_collection_name")
        test_results["details"]["get_collection_name"] = {
            "status": "FAIL",
            "error": str(e),
        }
        print(f"  [FAIL] get_collection_name() -> ERROR: {e}")

    # ==================== 4. 模型API ====================
    print("\n### 4. 模型API")

    # model_path可能返回None或字符串
    try:
        result = get_model_path()
        type_ok = result is None or isinstance(result, str)

        if type_ok:
            test_results["passed"].append("get_model_path")
            test_results["details"]["get_model_path"] = {
                "status": "OK",
                "result": str(result) if result else "None (auto-download)",
                "type": type(result).__name__,
            }
            print(f"  [OK] get_model_path() -> {result or 'None (auto-download)'}")
        else:
            test_results["failed"].append("get_model_path")
            test_results["details"]["get_model_path"] = {
                "status": "FAIL",
                "result": str(result),
                "error": f"Expected None or str, got {type(result).__name__}",
            }
            print(f"  [FAIL] get_model_path() -> {result}")
    except Exception as e:
        test_results["failed"].append("get_model_path")
        test_results["details"]["get_model_path"] = {"status": "FAIL", "error": str(e)}
        print(f"  [FAIL] get_model_path() -> ERROR: {e}")

    # hf_cache_dir可能返回None或字符串
    try:
        result = get_hf_cache_dir()
        type_ok = result is None or isinstance(result, str)

        if type_ok:
            test_results["passed"].append("get_hf_cache_dir")
            test_results["details"]["get_hf_cache_dir"] = {
                "status": "OK",
                "result": str(result) if result else "None (use default)",
                "type": type(result).__name__,
            }
            print(f"  [OK] get_hf_cache_dir() -> {result or 'None (use default)'}")
        else:
            test_results["failed"].append("get_hf_cache_dir")
            test_results["details"]["get_hf_cache_dir"] = {
                "status": "FAIL",
                "result": str(result),
                "error": f"Expected None or str, got {type(result).__name__}",
            }
            print(f"  [FAIL] get_hf_cache_dir() -> {result}")
    except Exception as e:
        test_results["failed"].append("get_hf_cache_dir")
        test_results["details"]["get_hf_cache_dir"] = {
            "status": "FAIL",
            "error": str(e),
        }
        print(f"  [FAIL] get_hf_cache_dir() -> ERROR: {e}")

    # ==================== 5. 数据源API ====================
    print("\n### 5. 数据源API")

    try:
        result = get_novel_sources()
        type_ok = isinstance(result, list)

        # 检查列表内容是否为Path对象
        content_ok = True
        if result:
            content_ok = all(isinstance(p, Path) for p in result)

        if type_ok:
            test_results["passed"].append("get_novel_sources")
            test_results["details"]["get_novel_sources"] = {
                "status": "OK",
                "result": f"{len(result)} sources",
                "type": "list[Path]",
                "sources": [str(p) for p in result],
            }
            print(f"  [OK] get_novel_sources() -> {len(result)} sources: {result}")
        else:
            test_results["failed"].append("get_novel_sources")
            test_results["details"]["get_novel_sources"] = {
                "status": "FAIL",
                "result": str(result),
                "error": f"Expected list, got {type(result).__name__}",
            }
            print(f"  [FAIL] get_novel_sources() -> {type(result).__name__}")
    except Exception as e:
        test_results["failed"].append("get_novel_sources")
        test_results["details"]["get_novel_sources"] = {
            "status": "FAIL",
            "error": str(e),
        }
        print(f"  [FAIL] get_novel_sources() -> ERROR: {e}")

    # ==================== 6. 验证路径实际存在性 ====================
    print("\n### 6. 路径存在性验证")

    # 核心路径应该存在
    paths_to_check = {
        "project_root": get_project_root(),
        "vectorstore_dir": get_vectorstore_dir(),
    }

    # 可选路径（可能不存在）
    optional_paths = {
        "settings_dir": get_settings_dir(),
        "techniques_dir": get_techniques_dir(),
        "case_library_dir": get_case_library_dir(),
        "logs_dir": get_logs_dir(),
    }

    for name, path in paths_to_check.items():
        exists = path.exists()
        status = exists and "OK" or "FAIL"
        print(f"  [{status}] {name}: {path} - exists: {exists}")

    print("\n  (可选路径，可能尚未创建)")
    for name, path in optional_paths.items():
        exists = path.exists()
        status = exists and "OK" or "-"
        print(f"  [{status}] {name}: {path} - exists: {exists}")


def generate_report():
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("## 配置系统测试报告")
    print("=" * 60)

    total = len(test_results["passed"]) + len(test_results["failed"])

    print(f"\n### 统计")
    print(f"- Total: {len(test_results['passed'])}/{total} passed")
    print(f"- Passed: {len(test_results['passed'])}")
    print(f"- Failed: {len(test_results['failed'])}")

    if test_results["failed"]:
        print(f"\n### 失败详情")
        for api_name in test_results["failed"]:
            detail = test_results["details"][api_name]
            print(f"\n**{api_name}**")
            for key, value in detail.items():
                print(f"  - {key}: {value}")

    print("\n### 全部结果")
    for api_name, detail in test_results["details"].items():
        status = detail["status"]
        result = detail.get("result", "N/A")
        print(f"- [{status}] {api_name}: {result}")

    # 返回是否全部通过
    return len(test_results["failed"]) == 0


if __name__ == "__main__":
    run_tests()
    all_passed = generate_report()

    if all_passed:
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    else:
        print("\n[FAILED] Some tests failed")
        sys.exit(1)
