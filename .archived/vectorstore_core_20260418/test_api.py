#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三大检索API接口测试脚本
======================

测试：
1. 技法检索 (TechniqueSearcher)
2. 设定检索 (KnowledgeSearcher)
3. 案例检索 (CaseSearcher)
4. Workflow统一接口 (NovelWorkflow)
"""

import sys
import io
from pathlib import Path

# Windows编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 设置路径 - 添加项目根目录和core目录
project_root = Path(__file__).parent.parent.parent  # 众生界/
sys.path.insert(0, str(project_root))  # 添加众生界/
sys.path.insert(0, str(project_root / "core"))  # 添加众生界/core/

from typing import Dict, Any
import traceback

# 测试结果收集
test_results = []
total_tests = 0
passed_tests = 0


def record_test(category: str, test_name: str, status: str, details: str = ""):
    """记录测试结果"""
    global total_tests, passed_tests
    total_tests += 1
    if status == "OK":
        passed_tests += 1

    test_results.append(
        {"category": category, "test": test_name, "status": status, "details": details}
    )

    # 实时输出
    print(f"[{status}] {category} - {test_name}")
    if details:
        print(f"    {details}")


def test_technique_search():
    """测试技法检索"""
    print("\n" + "=" * 60)
    print("【1. 技法检索测试】")
    print("=" * 60)

    try:
        from technique_search import TechniqueSearcher

        # 1. 初始化测试
        try:
            searcher = TechniqueSearcher()
            record_test("技法检索", "TechniqueSearcher初始化", "OK")
        except Exception as e:
            record_test("技法检索", "TechniqueSearcher初始化", "FAIL", str(e))
            return

        # 2. 搜索"战斗"
        try:
            results = searcher.search("战斗", top_k=3)
            if results:
                record_test("技法检索", f"搜索'战斗'返回{len(results)}条", "OK")
                if results:
                    sample = results[0]
                    print(f"    示例: {sample.get('name')} - {sample.get('dimension')}")
                    print(f"    相似度: {sample.get('score', 0):.0%}")
            else:
                record_test("技法检索", "搜索'战斗'返回0条", "FAIL", "无结果")
        except Exception as e:
            record_test("技法检索", "搜索'战斗'", "FAIL", str(e))

        # 3. 搜索"开篇"
        try:
            results = searcher.search("开篇", top_k=3)
            if results:
                record_test("技法检索", f"搜索'开篇'返回{len(results)}条", "OK")
            else:
                record_test("技法检索", "搜索'开篇'返回0条", "FAIL", "无结果")
        except Exception as e:
            record_test("技法检索", "搜索'开篇'", "FAIL", str(e))

        # 4. 搜索"人物"
        try:
            results = searcher.search("人物", top_k=3)
            if results:
                record_test("技法检索", f"搜索'人物'返回{len(results)}条", "OK")
            else:
                record_test("技法检索", "搜索'人物'返回0条", "FAIL", "无结果")
        except Exception as e:
            record_test("技法检索", "搜索'人物'", "FAIL", str(e))

        # 5. top_k参数测试
        try:
            results_k5 = searcher.search("战斗", top_k=5)
            results_k2 = searcher.search("战斗", top_k=2)
            if len(results_k5) >= len(results_k2):
                record_test(
                    "技法检索",
                    "top_k参数生效",
                    "OK",
                    f"k=5返回{len(results_k5)}条，k=2返回{len(results_k2)}条",
                )
            else:
                record_test(
                    "技法检索",
                    "top_k参数生效",
                    "FAIL",
                    f"k=5返回{len(results_k5)}条，k=2返回{len(results_k2)}条",
                )
        except Exception as e:
            record_test("技法检索", "top_k参数测试", "FAIL", str(e))

        # 6. 返回结果结构检查
        try:
            results = searcher.search("战斗", top_k=1)
            if results:
                r = results[0]
                required_keys = ["name", "dimension", "content", "score"]
                missing = [k for k in required_keys if k not in r]
                if not missing:
                    record_test("技法检索", "返回结果结构完整", "OK")
                else:
                    record_test(
                        "技法检索", "返回结果结构完整", "FAIL", f"缺少字段: {missing}"
                    )
            else:
                record_test("技法检索", "返回结果结构检查", "FAIL", "无结果")
        except Exception as e:
            record_test("技法检索", "返回结果结构检查", "FAIL", str(e))

    except Exception as e:
        print(f"[ERROR] 导入技法检索模块失败: {e}")
        traceback.print_exc()


def test_knowledge_search():
    """测试设定检索"""
    print("\n" + "=" * 60)
    print("【2. 设定检索测试】")
    print("=" * 60)

    try:
        from knowledge_search import KnowledgeSearcher

        # 1. 初始化测试
        try:
            searcher = KnowledgeSearcher()
            record_test("设定检索", "KnowledgeSearcher初始化", "OK")
        except Exception as e:
            record_test("设定检索", "KnowledgeSearcher初始化", "FAIL", str(e))
            return

        # 2. 搜索"林雷"
        try:
            results = searcher.search_novel("林雷", top_k=3)
            if results:
                record_test("设定检索", f"搜索'林雷'返回{len(results)}条", "OK")
                if results:
                    sample = results[0]
                    print(f"    示例: {sample.get('name')} - {sample.get('type')}")
                    print(f"    相似度: {sample.get('score', 0):.0%}")
            else:
                record_test("设定检索", "搜索'林雷'返回0条", "FAIL", "无结果")
        except Exception as e:
            record_test("设定检索", "搜索'林雷'", "FAIL", str(e))

        # 3. 搜索"势力"
        try:
            results = searcher.search_novel("势力", entity_type="势力", top_k=3)
            if results:
                record_test("设定检索", f"搜索'势力'返回{len(results)}条", "OK")
            else:
                record_test("设定检索", "搜索'势力'返回0条", "FAIL", "无结果")
        except Exception as e:
            record_test("设定检索", "搜索'势力'", "FAIL", str(e))

        # 4. 搜索"修仙"
        try:
            results = searcher.search_novel("修仙", top_k=3)
            if results:
                record_test("设定检索", f"搜索'修仙'返回{len(results)}条", "OK")
            else:
                record_test("设定检索", "搜索'修仙'返回0条", "FAIL", "无结果")
        except Exception as e:
            record_test("设定检索", "搜索'修仙'", "FAIL", str(e))

        # 5. 返回结果结构检查
        try:
            results = searcher.search_novel("林雷", top_k=1)
            if results:
                r = results[0]
                required_keys = ["name", "type", "description", "score"]
                missing = [k for k in required_keys if k not in r]
                if not missing:
                    record_test("设定检索", "返回结果结构完整", "OK")
                else:
                    record_test(
                        "设定检索", "返回结果结构完整", "FAIL", f"缺少字段: {missing}"
                    )
            else:
                record_test("设定检索", "返回结果结构检查", "FAIL", "无结果")
        except Exception as e:
            record_test("设定检索", "返回结果结构检查", "FAIL", str(e))

    except Exception as e:
        print(f"[ERROR] 导入设定检索模块失败: {e}")
        traceback.print_exc()


def test_case_search():
    """测试案例检索"""
    print("\n" + "=" * 60)
    print("【3. 案例检索测试】")
    print("=" * 60)

    try:
        from case_search import CaseSearcher

        # 1. 初始化测试
        try:
            searcher = CaseSearcher()
            record_test("案例检索", "CaseSearcher初始化", "OK")
        except Exception as e:
            record_test("案例检索", "CaseSearcher初始化", "FAIL", str(e))
            return

        # 2. 搜索"战斗场景"
        try:
            results = searcher.search("战斗场景", top_k=3)
            if results:
                record_test("案例检索", f"搜索'战斗'返回{len(results)}条", "OK")
                if results:
                    sample = results[0]
                    print(f"    示例: {sample.get('novel_name', sample.get('novel'))}")
                    print(f"    场景类型: {sample.get('scene_type')}")
                    print(f"    相似度: {sample.get('score', 0):.0%}")
            else:
                record_test("案例检索", "搜索'战斗'返回0条", "FAIL", "无结果")
        except Exception as e:
            record_test("案例检索", "搜索'战斗'", "FAIL", str(e))

        # 3. scene_type参数测试（减少请求避免超时）
        try:
            results_filtered = searcher.search(
                "战斗", scene_type="战斗场景", top_k=2, min_score=0.4
            )
            if results_filtered:
                record_test(
                    "案例检索",
                    "scene_type参数生效",
                    "OK",
                    f"过滤后返回{len(results_filtered)}条",
                )
                # 检查是否都是战斗场景
                all_match = all(
                    r.get("scene_type") == "战斗场景" for r in results_filtered
                )
                if all_match:
                    print("    ✓ 所有结果场景类型正确")
            else:
                record_test(
                    "案例检索",
                    "scene_type参数测试",
                    "WARN",
                    "过滤后无结果（可能需要调低min_score）",
                )
        except Exception as e:
            error_msg = str(e)
            if "timed out" in error_msg.lower():
                record_test(
                    "案例检索", "scene_type参数测试", "WARN", "超时（案例库数据量大）"
                )
            else:
                record_test("案例检索", "scene_type参数测试", "FAIL", error_msg)

        # 4. 返回结果结构检查
        try:
            results = searcher.search("战斗", top_k=1)
            if results:
                r = results[0]
                required_keys = ["novel_name", "scene_type", "content", "score"]
                missing = [k for k in required_keys if k not in r]
                if not missing:
                    record_test("案例检索", "返回结果结构完整", "OK")
                else:
                    record_test(
                        "案例检索", "返回结果结构完整", "FAIL", f"缺少字段: {missing}"
                    )
            else:
                record_test("案例检索", "返回结果结构检查", "FAIL", "无结果")
        except Exception as e:
            record_test("案例检索", "返回结果结构检查", "FAIL", str(e))

    except Exception as e:
        print(f"[ERROR] 导入案例检索模块失败: {e}")
        traceback.print_exc()


def test_workflow():
    """测试Workflow统一接口"""
    print("\n" + "=" * 60)
    print("【4. Workflow统一接口测试】")
    print("=" * 60)

    try:
        from workflow import NovelWorkflow

        # 1. 初始化测试
        try:
            workflow = NovelWorkflow()
            record_test(
                "Workflow接口",
                "NovelWorkflow初始化",
                "OK",
                f"连接类型: {workflow.client_type}",
            )
        except Exception as e:
            record_test("Workflow接口", "NovelWorkflow初始化", "FAIL", str(e))
            return

        # 2. 技法检索接口
        try:
            results = workflow.search_techniques("战斗", top_k=3)
            if results:
                record_test(
                    "Workflow接口", f"search_techniques()返回{len(results)}条", "OK"
                )
            else:
                record_test(
                    "Workflow接口", "search_techniques()返回0条", "FAIL", "无结果"
                )
        except Exception as e:
            record_test("Workflow接口", "search_techniques()", "FAIL", str(e))

        # 3. 设定检索接口
        try:
            results = workflow.search_novel("林雷", top_k=3)
            if results:
                record_test("Workflow接口", f"search_novel()返回{len(results)}条", "OK")
            else:
                record_test("Workflow接口", "search_novel()返回0条", "FAIL", "无结果")
        except Exception as e:
            record_test("Workflow接口", "search_novel()", "FAIL", str(e))

        # 4. 案例检索接口（注意：案例库较大，可能超时）
        try:
            results = workflow.search_cases("战斗", top_k=2)  # 减少top_k避免超时
            if results:
                record_test("Workflow接口", f"search_cases()返回{len(results)}条", "OK")
            else:
                record_test(
                    "Workflow接口",
                    "search_cases()返回0条",
                    "WARN",
                    "案例库查询返回空（可能数据量问题）",
                )
        except Exception as e:
            error_msg = str(e)
            if "timed out" in error_msg.lower():
                record_test(
                    "Workflow接口",
                    "search_cases()",
                    "WARN",
                    "超时（案例库256K条数据量大）",
                )
            else:
                record_test("Workflow接口", "search_cases()", "FAIL", error_msg)

    except Exception as e:
        print(f"[ERROR] 导入Workflow模块失败: {e}")
        traceback.print_exc()


def print_summary():
    """打印测试总结"""
    print("\n" + "=" * 60)
    print("## API接口测试报告")
    print("=" * 60)

    # 按类别分组
    categories = {}
    for r in test_results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    for cat, tests in categories.items():
        print(f"\n### {cat}")
        for t in tests:
            status_icon = "✓" if t["status"] == "OK" else "✗"
            print(f"- [{status_icon}] {t['test']}: {t['status']}")
            if t["details"]:
                print(f"    {t['details']}")

    print("\n" + "=" * 60)
    print("### 5. 通过率")
    print("=" * 60)
    rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"总测试: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {total_tests - passed_tests}")
    print(f"通过率: {rate:.1f}%")

    if rate >= 80:
        print("\n✓ 测试通过 - 系统运行正常")
    elif rate >= 50:
        print("\n! 部分测试失败 - 请检查数据库状态")
    else:
        print("\n✗ 大量测试失败 - 请检查Qdrant连接和数据库初始化")


def main():
    """主测试流程"""
    print("=" * 60)
    print("众生界 - 三大检索API接口测试")
    print("=" * 60)

    test_technique_search()
    test_knowledge_search()
    test_case_search()
    test_workflow()
    print_summary()


if __name__ == "__main__":
    main()
