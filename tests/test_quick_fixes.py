import pytest


def test_import_loader():
    import core.evaluation_criteria_loader as loader

    assert hasattr(loader, "load_criteria")


def test_feedback_processor_loads():
    from core.feedback_processor import FeedbackProcessor

    fp = FeedbackProcessor()
    c = fp.get_criteria()
    assert isinstance(c, dict)
