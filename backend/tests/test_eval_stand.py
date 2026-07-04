"""Юнит-тесты для compute_metrics (backend/scripts/eval_stand.py).

Чистая функция, без БД/сети — подаём готовые (expected, predicted) пары.
"""

import sys
from pathlib import Path

# scripts/ не пакет — добавляем в sys.path, как и test_fix_step_answer_leaks.py.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from eval_stand import EvalOutcome, compute_metrics  # noqa: E402


def test_empty_set() -> None:
    """Пустой набор — метрики не падают, всё n/a (None), счётчики нулевые."""
    m = compute_metrics([])

    assert m.n_total == 0
    assert m.n_scored == 0
    assert m.n_skipped == 0
    assert m.accuracy is None
    assert m.false_reject_rate is None
    assert m.false_accept_rate is None
    assert m.unsure_rate is None
    assert m.confusion == {}


def test_all_unsure() -> None:
    """Все примеры дали unsure — accuracy n/a (нет match/mismatch-предсказаний),
    но false_reject/false_accept вычисляются (0.0), unsure_rate=1.0."""
    outcomes = [
        EvalOutcome(expected="match", predicted="unsure", confidence=0.3),
        EvalOutcome(expected="match", predicted="unsure", confidence=0.4),
        EvalOutcome(expected="mismatch", predicted="unsure", confidence=0.2),
    ]
    m = compute_metrics(outcomes)

    assert m.n_total == 3
    assert m.n_scored == 3
    assert m.n_skipped == 0
    assert m.accuracy is None
    assert m.false_reject_rate == 0.0
    assert m.false_accept_rate == 0.0
    assert m.unsure_rate == 1.0
    assert m.confusion[("match", "unsure")] == 2
    assert m.confusion[("mismatch", "unsure")] == 1
    assert abs(m.confusion_confidence[("match", "unsure")] - 0.35) < 1e-9


def test_accuracy_excludes_unsure() -> None:
    """accuracy считается только среди match/mismatch-предсказаний."""
    outcomes = [
        EvalOutcome(expected="match", predicted="match", confidence=0.9),
        EvalOutcome(expected="match", predicted="match", confidence=0.8),
        EvalOutcome(expected="match", predicted="unsure", confidence=0.3),
        EvalOutcome(expected="mismatch", predicted="mismatch", confidence=0.7),
    ]
    m = compute_metrics(outcomes)

    # decided = 3 (2 match->match + 1 mismatch->mismatch), все верны -> accuracy=1.0
    assert m.n_scored == 4
    assert m.accuracy == 1.0
    assert m.unsure_rate == 0.25


def test_false_reject_rate() -> None:
    """false_reject_rate = P(pred=mismatch | expected=match)."""
    outcomes = [
        EvalOutcome(expected="match", predicted="match"),
        EvalOutcome(expected="match", predicted="mismatch"),   # false reject
        EvalOutcome(expected="match", predicted="match"),
        EvalOutcome(expected="match", predicted="mismatch"),   # false reject
        EvalOutcome(expected="mismatch", predicted="mismatch"),
    ]
    m = compute_metrics(outcomes)

    assert m.false_reject_rate == 0.5  # 2 из 4 expected=match
    assert m.false_accept_rate == 0.0


def test_false_accept_rate() -> None:
    """false_accept_rate = P(pred=match | expected=mismatch)."""
    outcomes = [
        EvalOutcome(expected="mismatch", predicted="match"),   # false accept
        EvalOutcome(expected="mismatch", predicted="mismatch"),
        EvalOutcome(expected="mismatch", predicted="mismatch"),
        EvalOutcome(expected="mismatch", predicted="mismatch"),
        EvalOutcome(expected="match", predicted="match"),
    ]
    m = compute_metrics(outcomes)

    assert m.false_accept_rate == 0.25  # 1 из 4 expected=mismatch
    assert m.false_reject_rate == 0.0


def test_skipped_excluded_from_all_metrics() -> None:
    """predicted=None (skip) — исключается из n_scored и всех rate-метрик."""
    outcomes = [
        EvalOutcome(expected="match", predicted="match"),
        EvalOutcome(expected="match", predicted=None),   # skip
        EvalOutcome(expected="mismatch", predicted=None),  # skip
    ]
    m = compute_metrics(outcomes)

    assert m.n_total == 3
    assert m.n_scored == 1
    assert m.n_skipped == 2
    assert m.accuracy == 1.0
    assert m.false_reject_rate == 0.0   # 1 expected=match, единственный scored -> match
    assert m.false_accept_rate is None  # 0 scored expected=mismatch


def test_confusion_matrix_shape() -> None:
    """Confusion — 2 (expected) x 3 (predicted), считает count корректно."""
    outcomes = [
        EvalOutcome(expected="match", predicted="match"),
        EvalOutcome(expected="match", predicted="mismatch"),
        EvalOutcome(expected="match", predicted="unsure"),
        EvalOutcome(expected="mismatch", predicted="match"),
        EvalOutcome(expected="mismatch", predicted="mismatch"),
        EvalOutcome(expected="mismatch", predicted="unsure"),
    ]
    m = compute_metrics(outcomes)

    for expected in ("match", "mismatch"):
        for predicted in ("match", "mismatch", "unsure"):
            assert m.confusion.get((expected, predicted), 0) == 1
