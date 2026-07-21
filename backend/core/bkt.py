"""Bayesian Knowledge Tracing (BKT) engine.

After every student answer we update P(mastery) for the corresponding node
using the standard BKT formulas (Corbett & Anderson, 1995).

Parameters per node (stored in `nodes` table):
    P(T) — bkt_p_t — probability of learning on a single attempt
    P(G) — bkt_p_g — probability of guessing correctly
    P(S) — bkt_p_s — probability of slipping (careless error)

Mastery requires P(mastery) >= 0.85, at least three correct attempts and
accuracy >= 50%. The same contract is shared by practice, stats and graph.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Attempt, Mastery, Node, Problem, Student

MASTERY_THRESHOLD = 0.85
MASTERY_MIN_CORRECT = 3
MASTERY_MIN_ACCURACY = 0.5
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
    # Easy problems → higher guess (up to 3x base), lower slip (down to 0.5x base)
    # Hard problems → lower guess (down to 0.5x base), higher slip (up to 2.5x base)
    p_g = min(0.30, base_p_g * (3.0 * (1 - d) + 0.5 * d))
    p_s = min(0.25, base_p_s * (0.5 * (1 - d) + 2.5 * d))
    return p_g, p_s


# ── DB helpers ───────────────────────────────────────────────


async def get_or_create_mastery(
    session: AsyncSession,
    student_id: int,
    node_id: str,
    initial_p: float = 0.1,
    *,
    for_update: bool = False,
) -> Mastery:
    """Get existing mastery row or create one with *initial_p*.

    Uses INSERT ON CONFLICT DO NOTHING to avoid race conditions when
    two concurrent requests try to create the same mastery row.
    """
    query = select(Mastery).where(
        Mastery.student_id == student_id,
        Mastery.node_id == node_id,
    )
    if for_update:
        query = query.with_for_update()
    result = await session.execute(query.execution_options(populate_existing=True))
    mastery = result.scalar_one_or_none()
    if mastery is None:
        await session.execute(
            pg_insert(Mastery)
            .values(student_id=student_id, node_id=node_id, p_mastery=initial_p)
            .on_conflict_do_nothing(index_elements=["student_id", "node_id"])
        )
        await session.flush()
        query = select(Mastery).where(
            Mastery.student_id == student_id,
            Mastery.node_id == node_id,
        )
        if for_update:
            query = query.with_for_update()
        mastery = (
            await session.execute(query.execution_options(populate_existing=True))
        ).scalar_one()
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
    # 1. Fetch node BKT params before taking the per-skill row lock.
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

    # 2. Serialize every BKT read-modify-write for this student × skill.
    mastery = await get_or_create_mastery(
        session,
        student_id,
        problem.node_id,
        for_update=True,
    )

    # Закрытие recurring_error означает, что ребёнок подтвердил перенос навыка.
    # Любая более поздняя неверная попытка того же узла — новое доказательство
    # пробела, поэтому очередь и аналитический прогресс должны открыться снова.
    if not is_correct:
        await session.execute(
            text(
                "UPDATE recurring_errors SET resolved = false "
                "WHERE student_id = :sid AND node_id = :nid AND resolved = true"
            ),
            {"sid": student_id, "nid": problem.node_id},
        )

    # 3. BKT update
    now = datetime.now(timezone.utc)
    mastery.p_mastery = bkt_update(mastery.p_mastery, is_correct, p_t, p_g, p_s)
    mastery.attempts_total += 1
    if is_correct:
        mastery.attempts_correct += 1
    mastery.last_attempt_at = now

    # 4. Spaced repetition starts only after the complete mastery contract.
    if is_mastered(mastery):
        _SR_INTERVALS = [1, 3, 7, 21, 60]  # days
        # Count consecutive correct answers (most recent first)
        from sqlalchemy import select as _sel
        recent = await session.execute(
            _sel(Attempt.is_correct).where(
                Attempt.student_id == student_id,
                Attempt.node_id == problem.node_id,
            ).order_by(Attempt.created_at.desc()).limit(10)
        )
        # Start with current answer; the Attempt row is added after this query.
        consec = 1 if is_correct else 0
        if is_correct:
            for (ok,) in recent.all():
                if ok:
                    consec += 1
                else:
                    break
        interval_idx = min(max(consec - 1, 0), len(_SR_INTERVALS) - 1)
        days = _SR_INTERVALS[interval_idx]
        mastery.next_review_at = now + timedelta(days=days)
    elif mastery.next_review_at is not None:
        # Lost mastery → clear scheduled review, needs immediate work
        mastery.next_review_at = None

    # 5. Serialize streak updates across attempts for different skills too.
    today = now.strftime('%Y-%m-%d')
    student = (
        await session.execute(
            select(Student).where(Student.id == student_id).with_for_update()
        )
    ).scalar_one_or_none()
    if student is not None:
        yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        if student.last_active_date != today:
            if student.last_active_date == yesterday:
                student.current_streak = (student.current_streak or 0) + 1
            elif student.last_active_date is None or student.last_active_date < yesterday:
                student.current_streak = 1
            student.last_active_date = today
            if (student.current_streak or 0) > (student.longest_streak or 0):
                student.longest_streak = student.current_streak

    # 6. Save the attempt after all reads so it cannot be counted twice in SR.
    attempt = Attempt(
        student_id=student_id,
        problem_id=problem.id,
        node_id=problem.node_id,
        answer_given=answer_given,
        is_correct=is_correct,
        response_time_ms=response_time_ms,
        source=source,
    )
    attempt.p_mastery_after = mastery.p_mastery
    session.add(attempt)

    await session.flush()
    return mastery


def is_mastered(mastery: Mastery) -> bool:
    """Check if the skill is considered mastered.

    Requires:
    1. BKT p_mastery >= threshold (0.85)
    2. At least 3 correct answers
    3. Overall accuracy >= 50% (prevents guessers from mastering)
    """
    if mastery.p_mastery < MASTERY_THRESHOLD:
        return False
    if mastery.attempts_correct < MASTERY_MIN_CORRECT:
        return False
    total = mastery.attempts_total
    if total > 0 and mastery.attempts_correct / total < MASTERY_MIN_ACCURACY:
        return False
    return True


def mastery_reached_clause():
    """SQL predicate equivalent to :func:`is_mastered`."""
    return and_(
        Mastery.p_mastery >= MASTERY_THRESHOLD,
        Mastery.attempts_correct >= MASTERY_MIN_CORRECT,
        Mastery.attempts_correct >= Mastery.attempts_total * MASTERY_MIN_ACCURACY,
    )
