#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test FeedbackProcessor with dynamic loading
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "core" / "feedback"))

from feedback_processor import FeedbackProcessor


def test_feedback_processor():
    """Test FeedbackProcessor with dynamic loader"""
    print("=" * 60)
    print("FeedbackProcessor Test (Dynamic Loading)")
    print("=" * 60)

    processor = FeedbackProcessor()

    # Test 1: AI flavor detection
    print("\n[1] AI Flavor Detection")
    test_feedback = {
        "raw_input": "林夕眼中闪过一丝冷意，心中涌起一股怒火。",
        "original": "",
    }

    forbidden = processor._extract_forbidden_items(test_feedback)
    print(f"  Input: {test_feedback['raw_input']}")
    print(f"  Detected: {forbidden}")

    # Test 2: Clean text
    print("\n[2] Clean Text")
    clean_feedback = {
        "raw_input": "林夕静静地站在山巅，望着远方的云海。",
        "original": "",
    }

    forbidden_clean = processor._extract_forbidden_items(clean_feedback)
    print(f"  Input: {clean_feedback['raw_input']}")
    print(f"  Detected: {forbidden_clean}")

    # Test 3: Full feedback processing
    print("\n[3] Full Feedback Processing")
    full_feedback = {
        "raw_input": "战斗场面写得太热血了，但节奏有点慢。",
        "original": "",
        "score": 8.5,
        "context": "战斗场景",
    }

    result = processor.process_feedback(full_feedback)
    print(f"  Processed: {result.get('processed', False)}")
    print(f"  Improvement points: {len(result.get('improvement_points', []))}")

    print("\n" + "=" * 60)
    print("Test PASS")
    print("=" * 60)


if __name__ == "__main__":
    test_feedback_processor()
