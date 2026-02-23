"""Bayesian Knowledge Tracing (BKT) engine.

After every student answer we update P(mastery) for the corresponding node
using the standard BKT formulas (Corbett & Anderson, 1995).

Parameters per node (stored in `nodes` table):
    P(T) — bkt_p_t — probability of learning on a single attempt
    P(G) — bkt_p_g — probability of guessing correctly
    P(S) — bkt_p_s — probability of slipping (careless error)

Mastery threshold: P(mastery) >= 0.7 → skill is considered mastered.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Attempt, Mastery, Node, Problem, Student

MASTERY_THRESHOLD = 0.7
MASTERY_ALGO_VERSION = 1  # bump when BKT/exam mastery logic changes


# ── BKT math ────────────────────────────────────────────────


def _posterior(p_l: float, is_correct: bool, p_g: float, p_s: float) -> float:
    """P(L_n | observation) — posterior after observing one answer."""
    if is_correct:
        num = p_l * (1 - p_s)
        den = p_l * (1 - p_s) + (1 - p_l) * p_g
    else:
        num = p_l * p_s
        den = p_l * p_s + (1 - p_l) * (1 - p_g)
    if den == 0:
        return p_l
    return num / den


def bkt_update(p_l: float, is_correct: bool, p_t: float, p_g: float, p_s: float) -> float:
    """Return new P(mastery) after one observation.

    P(L_{n+1}) = P(L_n|obs) + (1 - P(L_n|obs)) * P(T)
    """
    p_l = max(0.001, min(0.999, p_l))
    p_post = _posterior(p_l, is_correct, p_g, p_s)
    return max(0.001, min(0.999, p_post + (1 - p_post) * p_t))


def difficulty_adjusted_params(
    raw_score: float, node_min: float, node_max: float,
    base_p_g: float, base_p_s: float,
) -> tuple[float, float]:
    """Scale P(G) and P(S) by relative problem difficulty within the node.

    Easy problems → higher guess chance, lower slip chance.
    Hard problems → lower guess chance, higher slip chance.
    Returns (p_g, p_s).
    """
    span = max(node_max - node_min, 0.1)
    d = max(0.0, min(1.0, (raw_score - node_min) / span))
    p_g = 0.25 * (1 - d) + 0.05 * d
    p_s = 0.05 * (1 - d) + 0.20 * d
    return p_g, p_s


# ── DB helpers ───────────────────────────────────────────────


async def get_or_create_mastery(
    session: AsyncSession,
    student_id: int,
    node_id: str,
    initial_p: float = 0.0,
) -> Mastery:
    """Get existing mastery row or create one with *initial_p*.

    Uses INSERT ON CONFLICT DO NOTHING to avoid race conditions when
    two concurrent requests try to create the same mastery row.
    """
    result = await session.execute(
        select(Mastery).where(
            Mastery.student_id == student_id,
            Mastery.node_id == node_id,
        )
    )
    mastery = result.scalar_one_or_none()
    if mastery is None:
        await session.execute(
            pg_insert(Mastery)
            .values(student_id=student_id, node_id=node_id, p_mastery=initial_p)
            .on_conflict_do_nothing(index_elements=["student_id", "node_id"])
        )
        await session.flush()
        mastery = (await session.execute(
            select(Mastery).where(
                Mastery.student_id == student_id,
                Mastery.node_id == node_id,
            )
        )).scalar_one()
    return mastery


async def record_attempt(
    session: AsyncSession,
    student_id: int,
    problem: Problem,
    answer_given: str,
    is_correct: bool,
    response_time_ms: int | None = None,
    source: str | None = None,
) -> Mastery:
    """Record an attempt and update BKT mastery for the node.

    Returns the updated Mastery row.
    """
    # 1. Save attempt
    attempt = Attempt(
        student_id=student_id,
        problem_id=problem.id,
        node_id=problem.node_id,
        answer_given=answer_given,
        is_correct=is_correct,
        response_time_ms=response_time_ms,
        source=source,
    )
    session.add(attempt)

    # 2. Fetch node BKT params
    node = await session.get(Node, problem.node_id)
    p_t = max(0.001, min(0.999, node.bkt_p_t if node else 0.3))
    p_g = max(0.001, min(0.5, node.bkt_p_g if node else 0.05))
    p_s = max(0.001, min(0.5, node.bkt_p_s if node else 0.1))

    # 2b. Difficulty-aware P(G)/P(S) when raw_score is available
    if problem.raw_score is not None:
        row = await session.execute(
            select(
                func.min(Problem.raw_score),
                func.max(Problem.raw_score),
            ).where(
                Problem.node_id == problem.node_id,
                Problem.raw_score.isnot(None),
            )
        )
        node_min, node_max = row.one()
        if node_min is not None and node_max is not None:
            p_g, p_s = difficulty_adjusted_params(
                problem.raw_score, node_min, node_max, p_g, p_s,
            )

    # 3. Get / create mastery row
    mastery = await get_or_create_mastery(session, student_id, problem.node_id)

    # 4. BKT update
    mastery.p_mastery = bkt_update(mastery.p_mastery, is_correct, p_t, p_g, p_s)
    mastery.attempts_total += 1
    if is_correct:
        mastery.attempts_correct += 1
    mastery.last_attempt_at = datetime.utcnow()

    # 4b. Spaced repetition: compute next_review_at
    if mastery.p_mastery >= 0.7:  # mastered → schedule review
        _SR_INTERVALS = [1, 3, 7, 21, 60]  # days
        # Count consecutive correct answers (most recent first)
        from sqlalchemy import select as _sel
        recent = await session.execute(
            _sel(Attempt.is_correct).where(
                Attempt.student_id == student_id,
                Attempt.node_id == problem.node_id,
            ).order_by(Attempt.created_at.desc()).limit(10)
        )
        consec = 0
        for (ok,) in recent.all():
            if ok:
                consec += 1
            else:
                break
        interval_idx = min(max(consec - 1, 0), len(_SR_INTERVALS) - 1)
        days = _SR_INTERVALS[interval_idx]
        mastery.next_review_at = datetime.utcnow() + timedelta(days=days)
    elif mastery.next_review_at is not None:
        # Lost mastery → clear scheduled review, needs immediate work
        mastery.next_review_at = None

    # 5. Update daily streak
    today = datetime.utcnow().strftime('%Y-%m-%d')
    student = await session.get(Student, student_id)
    if student is not None:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        if student.last_active_date != today:
            if student.last_active_date == yesterday:
                student.current_streak = (student.current_streak or 0) + 1
            elif student.last_active_date is None or student.last_active_date < yesterday:
                student.current_streak = 1
            student.last_active_date = today
            if (student.current_streak or 0) > (student.longest_streak or 0):
                student.longest_streak = student.current_streak

    # 6. Snapshot mastery after this attempt
    attempt.p_mastery_after = mastery.p_mastery

    await session.flush()
    return mastery


def is_mastered(mastery: Mastery) -> bool:
    """Check if the skill is considered mastered.
    
    Requires:
    1. BKT p_mastery >= threshold (0.7)
    2. At least 3 correct answers
    3. Overall accuracy >= 50% (prevents guessers from mastering)
    """
    if mastery.p_mastery < MASTERY_THRESHOLD:
        return False
    if mastery.attempts_correct < 3:
        return False
    total = mastery.attempts_total
    if total > 0 and mastery.attempts_correct / total < 0.5:
        return False
    return True
