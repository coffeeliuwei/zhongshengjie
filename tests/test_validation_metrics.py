import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.validation.validate_retrieval import ndcg_at_5, precision_at_5


def test_ndcg_perfect_ranking():
    assert ndcg_at_5([2, 2, 2, 2, 2]) == 1.0


def test_ndcg_worst_ranking():
    ideal = [2, 2, 0, 0, 0]
    worst = [0, 0, 2, 2, 0]
    assert ndcg_at_5(worst) < ndcg_at_5(ideal)


def test_ndcg_all_zeros():
    assert ndcg_at_5([0, 0, 0, 0, 0]) == 0.0


def test_ndcg_mixed_grades():
    scores = [2, 1, 0, 1, 0]
    result = ndcg_at_5(scores)
    dcg = 2/math.log2(2) + 1/math.log2(3) + 0 + 1/math.log2(5) + 0
    idcg = 2/math.log2(2) + 1/math.log2(3) + 1/math.log2(4)
    assert result == round(dcg / idcg, 4)


def test_precision_at_5_all_relevant():
    assert precision_at_5([2, 1, 2, 1, 2]) == 1.0


def test_precision_at_5_none_relevant():
    assert precision_at_5([0, 0, 0, 0, 0]) == 0.0


def test_precision_at_5_partial():
    assert precision_at_5([2, 0, 1, 0, 0]) == 0.4


def test_precision_at_5_boundary():
    assert precision_at_5([1, 1, 0, 0, 0]) == 0.4
