import pytest


def test_evaluation_criteria_loader_class_exists():
    """EvaluationCriteriaLoader 类可被导入"""
    from core.evaluation_criteria_loader import EvaluationCriteriaLoader

    assert EvaluationCriteriaLoader is not None


def test_evaluation_criteria_loader_has_executable_prohibitions():
    """EvaluationCriteriaLoader 暴露硬编码禁止项"""
    from core.evaluation_criteria_loader import EvaluationCriteriaLoader

    assert hasattr(EvaluationCriteriaLoader, "EXECUTABLE_PROHIBITIONS")
    assert isinstance(EvaluationCriteriaLoader.EXECUTABLE_PROHIBITIONS, dict)
    assert len(EvaluationCriteriaLoader.EXECUTABLE_PROHIBITIONS) > 0


def test_feedback_processor_loads():
    """FeedbackProcessor 可从新路径导入并实例化"""
    from core.feedback.feedback_processor import FeedbackProcessor

    fp = FeedbackProcessor()
    # 验证核心方法存在
    assert hasattr(fp, "process_feedback")
    assert hasattr(fp, "get_improvement_summary")
