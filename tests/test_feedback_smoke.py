"""[N20 2026-04-18] modules/feedback 冒烟测试"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def test_conflict_detector_import():
    from modules.feedback.conflict_detector import ConflictDetector

    assert ConflictDetector is not None


def test_influence_analyzer_import():
    from modules.feedback.influence_analyzer import InfluenceAnalyzer

    assert InfluenceAnalyzer is not None


def test_intent_recognizer_import():
    from modules.feedback.intent_recognizer import IntentRecognizer

    assert IntentRecognizer is not None


def test_tracking_syncer_import():
    from modules.feedback.tracking_syncer import TrackingSyncer

    assert TrackingSyncer is not None


def test_feedback_types_import():
    from modules.feedback import types

    assert types is not None
