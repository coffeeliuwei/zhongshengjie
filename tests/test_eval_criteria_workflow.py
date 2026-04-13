#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试对话添加审核维度的完整流程
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.conversation.intent_classifier import IntentClassifier
from core.conversation.eval_criteria_extractor import EvaluationCriteriaExtractor


def test_intent_classification():
    """测试意图识别"""
    print("\n[1] Intent Classification")
    print("-" * 40)

    classifier = IntentClassifier()

    test_inputs = [
        ("这个表达很假", "add_evaluation_criteria"),
        ("嘴角勾起一抹感觉很假", "add_evaluation_criteria"),
        ("扫描文件正文/第一章.md找禁止项", "discover_prohibitions_from_file"),
        ("确认添加", "confirm_evaluation_criteria"),
    ]

    all_pass = True
    for input_text, expected in test_inputs:
        result = classifier.classify(input_text)
        status = "PASS" if result.intent == expected else "FAIL"
        if result.intent != expected:
            all_pass = False
        print(
            f"  {status}: '{input_text[:25]}...' -> {result.intent} (expected: {expected})"
        )

    return all_pass


def test_prohibition_extraction():
    """测试禁止项提取"""
    print("\n[2] Prohibition Extraction")
    print("-" * 40)

    extractor = EvaluationCriteriaExtractor()

    test_input = "嘴角勾起一抹感觉很假"
    candidate = extractor.extract_prohibition(test_input)

    print(f"  Input: '{test_input}'")
    print(f"  Extracted:")
    print(f"    Name: {candidate.name}")
    print(f"    Pattern: {candidate.pattern}")
    print(f"    Examples: {candidate.examples}")
    print(f"    Confidence: {candidate.confidence:.0%}")

    # 验证关键字段
    success = candidate.name and candidate.confidence > 0

    print(f"  Status: {'PASS' if success else 'FAIL'}")
    return success


def test_confirm_and_save():
    """测试确认入库"""
    print("\n[3] Confirm and Save")
    print("-" * 40)

    extractor = EvaluationCriteriaExtractor()

    # 先提取一个候选
    test_input = "测试禁止项：微微一笑"
    candidate = extractor.extract_prohibition(test_input)
    print(f"  Created candidate: {candidate.name}")

    # 模拟用户确认
    success = extractor.confirm_and_save()
    print(f"  Save result: {'SUCCESS' if success else 'FAIL'}")

    # 检查文件更新
    migrated_path = (
        Path(__file__).parent.parent / "tools" / "evaluation_criteria_migrated.json"
    )
    if migrated_path.exists():
        with open(migrated_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        total = data.get("count", 0)
        user_added = [
            c for c in data.get("criteria", []) if c.get("source") == "user_dialogue"
        ]

        print(f"  File updated:")
        print(f"    Total records: {total}")
        print(f"    User added via dialogue: {len(user_added)}")

        if user_added:
            latest = user_added[-1]
            print(f"    Latest: '{latest.get('name', 'unknown')}'")

    return success


def test_vector_retrieval():
    """测试向量检索"""
    print("\n[4] Vector Retrieval Test")
    print("-" * 40)

    try:
        from qdrant_client import QdrantClient
        from core.config_loader import get_qdrant_url

        client = QdrantClient(url=get_qdrant_url())
        collection_name = "evaluation_criteria_v1"

        # 检查Collection状态
        info = client.get_collection(collection_name)
        print(f"  Collection '{collection_name}':")
        print(f"    Points: {info.points_count}")

        # Scroll测试
        results, _ = client.scroll(
            collection_name=collection_name,
            limit=5,
            with_payload=True,
        )

        print(f"    Sample records:")
        for r in results[:3]:
            name = r.payload.get("name", "unknown")
            type_ = r.payload.get("dimension_type", "unknown")
            print(f"      - {name} ({type_})")

        # 检索测试（使用payload过滤）
        prohibition_results, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter={
                "must": [{"key": "dimension_type", "match": {"value": "prohibition"}}]
            },
            limit=10,
            with_payload=True,
        )

        print(f"    Prohibition items: {len(prohibition_results)}")

        print(f"  Status: PASS")
        return True

    except Exception as e:
        print(f"  Error: {e}")
        print(f"  Status: FAIL")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("End-to-End Test: Dialogue Add Evaluation Criteria")
    print("=" * 60)

    results = {
        "Intent Classification": test_intent_classification(),
        "Prohibition Extraction": test_prohibition_extraction(),
        "Confirm and Save": test_confirm_and_save(),
        "Vector Retrieval": test_vector_retrieval(),
    }

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_pass = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False

    print()
    print(f"Overall: {'ALL PASS' if all_pass else 'SOME FAILED'}")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
