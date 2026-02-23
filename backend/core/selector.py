"""Task selector — picks the next problem for a student.

Interleaved practice (2+2 cycle):
    positions 0,1 → weak EXAM_HEADS (untested first, then lowest mastery)
    positions 2,3 → outer fringe gaps (untested first, then lowest mastery)

When all EXAM_HEADS >= 0.85 → only outer fringe.
Fallback: if one source is empty, use the other.

When both heads and fringe are empty (everything mastered):
    Phase C → review: topics with p_mastery >= 0.70 sorted by staleness
    Phase D → challenge: hardest unsolved problems (top 20% raw_score)

Within a chosen node we pick a problem whose raw_score is closest to
the student's mastery-proportional target.  Falls back to sub_difficulty
levels if raw_score is not available.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exam import EXAM_HEADS
from core.graph import get_outer_fringe
from db.models import Attempt, Mastery, Problem

HEAD_MASTERY_THRESHOLD = 0.85
_EXAM_HEADS_SET = set(EXAM_HEADS)

_nis_first = case(
    (Problem.source.isnot(None) & (Problem.source != "generated"), 0),
    else_=1,
)

_REVIEW_STALE_DAYS = 7


async def _pick_problem_for_node(
    session: AsyncSession,
    student_id: int,
    node_id: str,
) -> Problem | None:
    """Choose a problem for *node_id* using raw_score proximity cascade.

    Cascade:
      Tier 1 — unanswered, closest to target raw_score (top 3 → random)
      Tier 2 — answered incorrectly, closest to target
      Tier 3 — not attempted in 7+ days
      Tier 4 — oldest attempted

    Falls back to sub_difficulty-based selection when raw_score is absent.
    """
    mastery = (
        await session.execute(
            select(Mastery).where(
                Mastery.student_id == student_id, Mastery.node_id == node_id
            )
        )
    ).scalar_one_or_none()

    p_m = mastery.p_mastery if mastery else 0.0

    answered_sub = select(Attempt.problem_id).where(
        Attempt.student_id == student_id, Attempt.node_id == node_id
    )

    # Check if raw_score data exists for this node
    score_row = (await session.execute(
        select(
            func.min(Problem.raw_score),
            func.max(Problem.raw_score),
        ).where(Problem.node_id == node_id, Problem.raw_score.isnot(None))
    )).one()
    node_min, node_max = score_row

    has_scores = node_min is not None and node_max is not None

    if has_scores:
        target = node_min + min(p_m + 0.1, 1.0) * (node_max - node_min)
        return await _pick_by_raw_score(
            session, student_id, node_id, target, answered_sub,
        )

    return await _pick_by_sub_difficulty(
        session, student_id, node_id, mastery, answered_sub,
    )


async def _pick_by_raw_score(
    session: AsyncSession,
    student_id: int,
    node_id: str,
    target: float,
    answered_sub,
) -> Problem | None:
    """Cascade selection using raw_score proximity."""
    # Tier 1: unanswered, closest to target
    rows = (await session.execute(
        select(Problem)
        .where(
            Problem.node_id == node_id,
            Problem.raw_score.isnot(None),
            Problem.id.not_in(answered_sub),
        )
        .order_by(func.abs(Problem.raw_score - target))
        .limit(3)
    )).scalars().all()
    if rows:
        return random.choice(rows)

    # Tier 2: answered incorrectly, closest to target
    wrong_ids = select(Attempt.problem_id).where(
        Attempt.student_id == student_id,
        Attempt.node_id == node_id,
        Attempt.is_correct == False,
    )
    rows = (await session.execute(
        select(Problem)
        .where(
            Problem.node_id == node_id,
            Problem.raw_score.isnot(None),
            Problem.id.in_(wrong_ids),
        )
        .order_by(func.abs(Problem.raw_score - target))
        .limit(3)
    )).scalars().all()
    if rows:
        return random.choice(rows)

    # Tier 3: not attempted in 7+ days
    stale_cutoff = datetime.utcnow() - timedelta(days=_REVIEW_STALE_DAYS)
    latest_attempt = (
        select(func.max(Attempt.created_at))
        .where(
            Attempt.student_id == student_id,
            Attempt.problem_id == Problem.id,
        )
        .correlate(Problem)
        .scalar_subquery()
    )
    result = await session.execute(
        select(Problem)
        .where(
            Problem.node_id == node_id,
            latest_attempt < stale_cutoff,
        )
        .order_by(func.abs(Problem.raw_score - target))
        .limit(3)
    )
    rows = result.scalars().all()
    if rows:
        return random.choice(rows)

    # Tier 4: oldest attempted problem
    result = await session.execute(
        select(Problem)
        .where(Problem.node_id == node_id)
        .order_by(latest_attempt.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _pick_by_sub_difficulty(
    session: AsyncSession,
    student_id: int,
    node_id: str,
    mastery: Mastery | None,
    answered_sub,
) -> Problem | None:
    """Fallback: select by sub_difficulty levels when raw_score is absent."""
    target = 1 if mastery is None else min(mastery.attempts_correct + 1, 4)

    for level in [target, target - 1, target + 1, target - 2, target + 2]:
        if level < 1 or level > 4:
            continue
        result = await session.execute(
            select(Problem)
            .where(
                Problem.node_id == node_id,
                Problem.sub_difficulty == level,
                Problem.id.not_in(answered_sub),
            )
            .order_by(_nis_first, func.random())
            .limit(1)
        )
        problem = result.scalar_one_or_none()
        if problem is not None:
            return problem

    result = await session.execute(
        select(Problem)
        .where(Problem.node_id == node_id, Problem.id.not_in(answered_sub))
        .order_by(_nis_first, func.random())
        .limit(1)
    )
    problem = result.scalar_one_or_none()
    if problem is not None:
        return problem

    result = await session.execute(
        select(Problem)
        .where(Problem.node_id == node_id)
        .order_by(_nis_first, func.random())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_weak_exam_heads(
    session: AsyncSession,
    student_id: int,
) -> list[str]:
    """Return EXAM_HEADS with p_mastery < 0.85, untested first, then by weakness."""
    mastery_rows = (
        await session.execute(
            select(Mastery.node_id, Mastery.p_mastery).where(
                Mastery.student_id == student_id,
                Mastery.node_id.in_(EXAM_HEADS),
            )
        )
    ).all()
    mastery_map = {row.node_id: row.p_mastery for row in mastery_rows}

    untested: list[str] = []
    weak: list[tuple[float, str]] = []
    for head in EXAM_HEADS:
        p = mastery_map.get(head)
        if p is None:
            untested.append(head)
        elif p < HEAD_MASTERY_THRESHOLD:
            weak.append((p, head))

    weak.sort(key=lambda x: x[0])
    return untested + [nid for _, nid in weak]


async def _get_weak_fringe(
    session: AsyncSession,
    student_id: int,
) -> list[str]:
    """Return outer fringe nodes (excluding EXAM_HEADS), untested first, then by weakness."""
    fringe = await get_outer_fringe(session, student_id)
    fringe = [nid for nid in fringe if nid not in _EXAM_HEADS_SET]
    if not fringe:
        return []

    mastery_rows = (
        await session.execute(
            select(Mastery.node_id, Mastery.p_mastery).where(
                Mastery.student_id == student_id,
                Mastery.node_id.in_(fringe),
            )
        )
    ).all()
    mastery_map = {row.node_id: row.p_mastery for row in mastery_rows}

    untested: list[str] = []
    tested: list[tuple[float, str]] = []
    for nid in fringe:
        p = mastery_map.get(nid)
        if p is None:
            untested.append(nid)
        else:
            tested.append((p, nid))

    tested.sort(key=lambda x: x[0])
    return untested + [nid for _, nid in tested]


async def _pick_from_list(
    session: AsyncSession,
    student_id: int,
    node_ids: list[str],
) -> tuple[Problem | None, str | None]:
    """Try to pick a problem from the first few candidates (with randomness among top-3)."""
    top = node_ids[: min(3, len(node_ids))]
    random.shuffle(top)
    for nid in top:
        problem = await _pick_problem_for_node(session, student_id, nid)
        if problem is not None:
            return problem, nid
    for nid in node_ids[3:]:
        problem = await _pick_problem_for_node(session, student_id, nid)
        if problem is not None:
            return problem, nid
    return None, None


async def _get_review_topics(
    session: AsyncSession,
    student_id: int,
) -> list[str]:
    """Phase C: mastered topics sorted by staleness (oldest practice first)."""
    rows = (await session.execute(
        select(Mastery.node_id, Mastery.last_attempt_at).where(
            Mastery.student_id == student_id,
            Mastery.p_mastery >= 0.70,
        ).order_by(Mastery.last_attempt_at.asc())
    )).all()
    return [r.node_id for r in rows]


async def _get_challenge_topics(
    session: AsyncSession,
    student_id: int,
) -> list[str]:
    """Phase D: topics that have unsolved hard problems (top 20% raw_score)."""
    answered_sub = select(Attempt.problem_id).where(
        Attempt.student_id == student_id,
    )

    # Find nodes with unsolved problems in the top 20% of their raw_score range
    # We look for problems where raw_score > node_min + 0.8*(node_max-node_min)
    hard_nodes = (await session.execute(
        select(Problem.node_id).where(
            Problem.raw_score.isnot(None),
            Problem.id.not_in(answered_sub),
        ).group_by(Problem.node_id)
    )).scalars().all()

    if not hard_nodes:
        return []

    # Sort by mastery descending (strongest students get challenged on their best topics)
    mastery_rows = (await session.execute(
        select(Mastery.node_id, Mastery.p_mastery).where(
            Mastery.student_id == student_id,
            Mastery.node_id.in_(hard_nodes),
        )
    )).all()
    mastery_map = {r.node_id: r.p_mastery for r in mastery_rows}
    hard_nodes_sorted = sorted(hard_nodes, key=lambda nid: mastery_map.get(nid, 0), reverse=True)
    return hard_nodes_sorted



async def _get_due_reviews(
    session: AsyncSession,
    student_id: int,
) -> list[str]:
    """Spaced repetition: topics where next_review_at <= now."""
    rows = (await session.execute(
        select(Mastery.node_id).where(
            Mastery.student_id == student_id,
            Mastery.next_review_at.isnot(None),
            Mastery.next_review_at <= datetime.utcnow(),
        ).order_by(Mastery.next_review_at.asc())
    )).scalars().all()
    return list(rows)


async def select_next_problem(
    session: AsyncSession,
    student_id: int,
    practice_count: int = 1,
) -> tuple[Problem | None, str | None]:
    """Select the best next problem using interleaved 2+2 strategy.

    Cycle of 4:
        positions 0,1 → weak EXAM_HEADS (untested → weakest)
        positions 2,3 → outer fringe gaps (untested → weakest, excluding heads)

    When all heads >= 0.85 → only fringe.
    Fallback: if primary source is empty, use the other.

    Endgame (both empty):
        Phase C → review stale mastered topics
        Phase D → challenge with hardest unsolved problems
    """
    # ── Spaced repetition: due reviews get priority ──
    due_reviews = await _get_due_reviews(session, student_id)
    if due_reviews and (practice_count - 1) % 3 == 0:
        # Every 3rd problem slot → review due topic
        result = await _pick_from_list(session, student_id, due_reviews)
        if result[0] is not None:
            return result

    cycle_pos = (practice_count - 1) % 4
    want_heads = cycle_pos in (0, 1)

    heads = await _get_weak_exam_heads(session, student_id)
    fringe = await _get_weak_fringe(session, student_id)

    if want_heads and heads:
        result = await _pick_from_list(session, student_id, heads)
        if result[0] is not None:
            return result
        return await _pick_from_list(session, student_id, fringe)

    if fringe:
        result = await _pick_from_list(session, student_id, fringe)
        if result[0] is not None:
            return result
        return await _pick_from_list(session, student_id, heads)

    if heads:
        return await _pick_from_list(session, student_id, heads)

    # ── Endgame: everything mastered ──
    # Phase C: review — stale topics
    review = await _get_review_topics(session, student_id)
    if review:
        result = await _pick_from_list(session, student_id, review)
        if result[0] is not None:
            return result

    # Phase D: challenge — hardest unsolved problems
    challenge = await _get_challenge_topics(session, student_id)
    if challenge:
        result = await _pick_from_list(session, student_id, challenge)
        if result[0] is not None:
            return result

    return None, None
