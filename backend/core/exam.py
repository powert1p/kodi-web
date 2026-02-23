"""Exam mode engine — top-down adaptive test for strong students.

Two-phase approach:
  Phase A: test 15 cluster-head topics (top of the knowledge graph).
  Phase B: directly test the 5 most uncertain subtopics remaining.

Scoring models (each used where it fits):
  Directly tested topics: additive mastery (L1=15%, L2=25%, L3=30%, L4=30%).
  Subtopics (indirect): weighted accuracy — order-independent, proportional
    to correct/total ratio among parent answers that touch the subtopic.
    p = PRIOR + (accuracy - PRIOR) * SUBTOPIC_REACH * confidence
  Phase B selection: BKT uncertainty for finding the most ambiguous subtopics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.diagnostic import (
    _compute_additive_mastery,
    _compute_downstream_counts,
    _get_all_prereqs_recursive,
    _load_node_tags,
    _next_sub_difficulty,
    _pick_problem,
    _reconstruct_levels,
    _should_ask_again,
)
from db.models import Mastery, Node, Problem

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────

EXAM_HEADS = [
    "PC06", "GE07", "AL04", "EQ06", "WP03", "WP05", "EQ03",
    "PR06", "MD03", "LG03", "CB07", "WP10", "DC05", "GE08", "LG04",
]

PHASE_A_TOPICS = 15
PHASE_B_TOPICS = 5

PRIOR = 0.30

SLIP = {1: 0.05, 2: 0.10, 3: 0.15, 4: 0.20}
GUESS = {1: 0.30, 2: 0.20, 3: 0.10, 4: 0.05}

SUBTOPIC_REACH = 0.70
SUBTOPIC_FULL_EVIDENCE = 5

CERTAIN_HIGH = 0.80
CERTAIN_LOW = 0.30


# ── Exam session state ───────────────────────────────────────


@dataclass
class ExamState:
    student_id: int = 0
    phase: int = 4  # always 4 — distinguishes exam from diagnostic phases 1/2/3
    current_phase: str = "A"

    heads_queue: list[str] = field(default_factory=list)
    targets_queue: list[str] = field(default_factory=list)

    evidence: dict[str, float] = field(default_factory=dict)
    subtrees: dict[str, list[str]] = field(default_factory=dict)
    pre_exam_mastery: dict[str, float] = field(default_factory=dict)

    node_answers: dict[str, list[list]] = field(default_factory=dict)
    node_tags: dict[str, str] = field(default_factory=dict)
    tested_nodes: set[str] = field(default_factory=set)
    sub_hits: dict[str, list[int]] = field(default_factory=dict)  # {node_id: [correct, total]}

    questions_asked: int = 0
    topics_tested: int = 0
    max_topics: int = PHASE_A_TOPICS + PHASE_B_TOPICS
    correct_count: int = 0
    phase_just_changed: bool = False

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "phase": self.phase,
            "current_phase": self.current_phase,
            "heads_queue": self.heads_queue,
            "targets_queue": self.targets_queue,
            "evidence": self.evidence,
            "subtrees": self.subtrees,
            "pre_exam_mastery": self.pre_exam_mastery,
            "node_answers": self.node_answers,
            "node_tags": self.node_tags,
            "tested_nodes": list(self.tested_nodes),
            "sub_hits": self.sub_hits,
            "questions_asked": self.questions_asked,
            "topics_tested": self.topics_tested,
            "max_topics": self.max_topics,
            "correct_count": self.correct_count,
            "phase_just_changed": self.phase_just_changed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ExamState:
        return cls(
            student_id=d["student_id"],
            phase=d.get("phase", 4),
            current_phase=d.get("current_phase", "A"),
            heads_queue=d.get("heads_queue", []),
            targets_queue=d.get("targets_queue", []),
            evidence=d.get("evidence", {}),
            subtrees=d.get("subtrees", {}),
            pre_exam_mastery=d.get("pre_exam_mastery", {}),
            node_answers=d.get("node_answers", {}),
            node_tags=d.get("node_tags", {}),
            tested_nodes=set(d.get("tested_nodes", [])),
            sub_hits=d.get("sub_hits", {}),
            questions_asked=d.get("questions_asked", 0),
            topics_tested=d.get("topics_tested", 0),
            max_topics=d.get("max_topics", PHASE_A_TOPICS + PHASE_B_TOPICS),
            correct_count=d.get("correct_count", 0),
            phase_just_changed=d.get("phase_just_changed", False),
        )


# ── Initialization ───────────────────────────────────────────


async def init_exam(session: AsyncSession, student_id: int) -> ExamState:
    """Create a new exam session for the student."""
    node_tags = await _load_node_tags(session)

    mastery_result = await session.execute(
        select(Mastery.node_id, Mastery.p_mastery).where(
            Mastery.student_id == student_id
        )
    )
    mastery_map = {row.node_id: row.p_mastery for row in mastery_result.all()}

    evidence: dict[str, float] = {}
    pre_exam: dict[str, float] = {}
    for nid in node_tags:
        val = mastery_map.get(nid, PRIOR)
        evidence[nid] = val
        pre_exam[nid] = val

    subtrees: dict[str, list[str]] = {}
    for head_id in EXAM_HEADS:
        if head_id in node_tags:
            prereqs = await _get_all_prereqs_recursive(session, head_id)
            subtrees[head_id] = prereqs

    sorted_heads = sorted(
        [h for h in EXAM_HEADS if h in node_tags],
        key=lambda h: len(subtrees.get(h, [])),
        reverse=True,
    )

    return ExamState(
        student_id=student_id,
        heads_queue=sorted_heads,
        evidence=evidence,
        pre_exam_mastery=pre_exam,
        subtrees=subtrees,
        node_tags=node_tags,
    )


# ── BKT evidence update ──────────────────────────────────────


def _bkt_update(p: float, correct: bool, slip: float, guess: float) -> float:
    """Standard Bayesian Knowledge Tracing update."""
    p = max(0.001, min(0.999, p))
    if correct:
        numerator = p * (1.0 - slip)
        denominator = numerator + (1.0 - p) * guess
    else:
        numerator = p * slip
        denominator = numerator + (1.0 - p) * (1.0 - guess)
    if denominator < 1e-12:
        return p
    return numerator / denominator


def _update_subtopic_evidence(
    state: ExamState,
    node_id: str,
    correct: bool,
    difficulty: int,
) -> None:
    """Weighted accuracy update for all subtopics in node_id's subtree.

    Order-independent: tracks hit/total counts per subtopic, then computes
    mastery = PRIOR + (accuracy - PRIOR) * SUBTOPIC_REACH * confidence
    where confidence = min(total / SUBTOPIC_FULL_EVIDENCE, 1.0).
    """
    subtree = state.subtrees.get(node_id, [])
    if not subtree:
        return

    for s in subtree:
        hits = state.sub_hits.get(s)
        if hits is None:
            hits = [0, 0]
            state.sub_hits[s] = hits
        hits[1] += 1
        if correct:
            hits[0] += 1

        accuracy = hits[0] / hits[1]
        confidence = min(hits[1] / SUBTOPIC_FULL_EVIDENCE, 1.0)
        state.evidence[s] = max(0.01, PRIOR + (accuracy - PRIOR) * SUBTOPIC_REACH * confidence)


def _update_direct_evidence(
    state: ExamState,
    node_id: str,
    correct: bool,
    difficulty: int,
) -> None:
    """Full BKT update for the directly tested node."""
    p = state.evidence.get(node_id, PRIOR)
    slip = SLIP.get(difficulty, 0.15)
    guess = GUESS.get(difficulty, 0.10)
    state.evidence[node_id] = _bkt_update(p, correct, slip, guess)


# ── Question selection ───────────────────────────────────────


async def exam_next_question(
    session: AsyncSession, state: ExamState
) -> Problem | None:
    """Get the next question, handling phase transitions."""
    state.phase_just_changed = False
    if state.current_phase == "A":
        prob = await _phase_a_next(session, state)
        if prob is not None:
            return prob
        state.current_phase = "B"
        state.phase_just_changed = True
        await _select_phase_b_targets(session, state)
        return await _phase_b_next(session, state)

    return await _phase_b_next(session, state)


async def _phase_a_next(
    session: AsyncSession, state: ExamState
) -> Problem | None:
    """Pick next question from Phase A (cluster heads)."""
    while state.heads_queue:
        node_id = state.heads_queue.pop(0)

        if node_id in state.node_answers and len(state.node_answers[node_id]) > 0:
            if not _should_ask_again(state, node_id):
                continue
            sub_diff = _next_sub_difficulty(state, node_id)
            problem = await _pick_problem(
                session, node_id, sub_diff, state.student_id
            )
            if problem is None:
                continue
            state.questions_asked += 1
            return problem

        if node_id in state.tested_nodes:
            continue

        sub_diff = 3
        problem = await _pick_problem(
            session, node_id, sub_diff, state.student_id
        )
        if problem is None:
            logger.warning("No problems for exam head %s — skipping", node_id)
            continue

        state.tested_nodes.add(node_id)
        state.topics_tested += 1
        state.questions_asked += 1
        return problem

    return None


async def _phase_b_next(
    session: AsyncSession, state: ExamState
) -> Problem | None:
    """Pick next question from Phase B (uncertain subtopics)."""
    while state.targets_queue:
        node_id = state.targets_queue.pop(0)

        if node_id in state.node_answers and len(state.node_answers[node_id]) > 0:
            if not _should_ask_again(state, node_id):
                continue
            sub_diff = _next_sub_difficulty(state, node_id)
            problem = await _pick_problem(
                session, node_id, sub_diff, state.student_id
            )
            if problem is None:
                continue
            state.questions_asked += 1
            return problem

        if node_id in state.tested_nodes:
            continue

        p = state.evidence.get(node_id, 0.5)
        sub_diff = 3 if p >= 0.5 else 2
        problem = await _pick_problem(
            session, node_id, sub_diff, state.student_id
        )
        if problem is None:
            logger.warning("No problems for Phase B target %s — skipping", node_id)
            continue

        state.tested_nodes.add(node_id)
        state.topics_tested += 1
        state.questions_asked += 1
        return problem

    return None


# ── Phase B target selection ─────────────────────────────────


async def _select_phase_b_targets(
    session: AsyncSession, state: ExamState
) -> None:
    """Select the 5 most uncertain + impactful subtopics for Phase B."""
    downstream = await _compute_downstream_counts(session)
    max_downstream = max(downstream.values()) if downstream else 1

    candidates: list[tuple[float, str]] = []
    for nid, p in state.evidence.items():
        if nid in state.tested_nodes:
            continue
        if not (CERTAIN_LOW < p < CERTAIN_HIGH):
            continue
        uncertainty = 1.0 - abs(p - 0.5) * 2.0
        impact = downstream.get(nid, 0) / max_downstream
        score = uncertainty * 0.6 + impact * 0.4
        candidates.append((score, nid))

    candidates.sort(key=lambda x: -x[0])
    targets = [nid for _, nid in candidates[:PHASE_B_TOPICS]]

    for t in targets:
        if t not in state.subtrees:
            prereqs = await _get_all_prereqs_recursive(session, t)
            state.subtrees[t] = prereqs

    state.targets_queue = targets
    logger.info(
        "Phase B targets (%d): %s",
        len(targets),
        [(t, round(state.evidence.get(t, 0), 2)) for t in targets],
    )


# ── Answer processing ────────────────────────────────────────


async def exam_handle_answer(
    session: AsyncSession,
    state: ExamState,
    node_id: str,
    correct: bool,
    elapsed: float,
    difficulty: int,
) -> None:
    """Process an exam answer: update evidence + write to DB immediately."""
    if correct:
        state.correct_count += 1

    state.node_answers.setdefault(node_id, []).append([correct, elapsed])

    _update_subtopic_evidence(state, node_id, correct, difficulty)
    _update_direct_evidence(state, node_id, correct, difficulty)

    changed = {node_id}
    changed.update(state.subtrees.get(node_id, []))
    await _write_interim_mastery(session, state, changed)

    if _should_ask_again(state, node_id):
        if state.current_phase == "A":
            state.heads_queue.insert(0, node_id)
        else:
            state.targets_queue.insert(0, node_id)


async def _write_interim_mastery(
    session: AsyncSession, state: ExamState, changed_nodes: set[str]
) -> None:
    """Write mastery for changed nodes only (live graph update).

    Directly tested nodes: additive model (understands L1-L4 levels).
    Subtopics (no direct answers): BKT evidence (indirect signals).
    """
    for node_id in changed_nodes:
        p_evidence = state.evidence.get(node_id)
        if p_evidence is None:
            continue

        if node_id in state.tested_nodes and node_id in state.node_answers:
            p_value = _compute_additive_mastery(state.node_answers[node_id])
        else:
            p_value = p_evidence

        existing = await session.execute(
            select(Mastery).where(
                Mastery.student_id == state.student_id,
                Mastery.node_id == node_id,
            )
        )
        mastery = existing.scalar_one_or_none()

        if mastery is None:
            mastery = Mastery(
                student_id=state.student_id,
                node_id=node_id,
                p_mastery=round(p_value, 3),
                attempts_total=0,
                attempts_correct=0,
            )
            session.add(mastery)
        else:
            mastery.p_mastery = round(p_value, 3)

    await session.flush()
    await session.commit()


# ── Finish exam ──────────────────────────────────────────────


async def finish_exam(
    session: AsyncSession, state: ExamState
) -> dict:
    """Final mastery write: blend direct scores for tested nodes, commit."""
    for node_id, p_evidence in state.evidence.items():
        if node_id in state.tested_nodes:
            answers = state.node_answers.get(node_id, [])
            p_final = _compute_additive_mastery(answers) if answers else p_evidence
        else:
            p_final = p_evidence

        old_p = state.pre_exam_mastery.get(node_id)

        existing = await session.execute(
            select(Mastery).where(
                Mastery.student_id == state.student_id,
                Mastery.node_id == node_id,
            )
        )
        mastery = existing.scalar_one_or_none()

        if mastery is None:
            mastery = Mastery(
                student_id=state.student_id,
                node_id=node_id,
                p_mastery=round(p_final, 3),
                attempts_total=1 if node_id in state.tested_nodes else 0,
                attempts_correct=(
                    1 if node_id in state.tested_nodes and p_final >= 0.7 else 0
                ),
            )
            session.add(mastery)
        else:
            has_real_history = mastery.attempts_total > 0
            if has_real_history:
                mastery.p_mastery = round(p_final * 0.7 + old_p * 0.3, 3)
            else:
                mastery.p_mastery = round(p_final, 3)
            if node_id in state.tested_nodes:
                mastery.attempts_total += 1
                if p_final >= 0.7:
                    mastery.attempts_correct += 1

    await session.flush()
    await session.commit()

    mastered = sum(1 for p in state.evidence.values() if p >= 0.7)
    partial = sum(1 for p in state.evidence.values() if 0.3 <= p < 0.7)
    failed = sum(1 for p in state.evidence.values() if p < 0.3)
    total = len(state.evidence)

    head_results = await _build_head_results(session, state)
    target_results = await _build_target_results(session, state)

    return {
        "phase": 4,
        "score": f"{state.correct_count}/{state.questions_asked}",
        "topics_tested": state.topics_tested,
        "mastered_count": mastered,
        "partial_count": partial,
        "failed_count": failed,
        "total_nodes": total,
        "head_results": head_results,
        "target_results": target_results,
    }


async def _build_head_results(
    session: AsyncSession, state: ExamState
) -> list[dict]:
    """Build per-head summary for display."""
    node_rows = (await session.execute(
        select(Node).where(Node.id.in_(EXAM_HEADS))
    )).scalars().all()
    node_map = {n.id: n for n in node_rows}

    results: list[dict] = []
    for head_id in EXAM_HEADS:
        node = node_map.get(head_id)
        if not node:
            continue
        answers = state.node_answers.get(head_id, [])
        levels = _reconstruct_levels(answers) if answers else []

        level_marks: list[str] = []
        for lvl, ans in zip(levels, answers):
            mark = "✓" if ans[0] else "✗"
            level_marks.append(f"L{lvl}{mark}")

        p = state.evidence.get(head_id, 0.5)
        if p >= 0.7:
            status = "mastered"
        elif p >= 0.3:
            status = "partial"
        else:
            status = "failed"

        subtree_mastered = sum(
            1 for s in state.subtrees.get(head_id, [])
            if state.evidence.get(s, 0) >= 0.7
        )
        subtree_total = len(state.subtrees.get(head_id, []))

        results.append({
            "id": head_id,
            "name": node.name_ru,
            "status": status,
            "evidence": round(p, 2),
            "levels": " ".join(level_marks),
            "subtree_mastered": subtree_mastered,
            "subtree_total": subtree_total,
        })
    return results


async def _build_target_results(
    session: AsyncSession, state: ExamState
) -> list[dict]:
    """Build per-target summary for Phase B display."""
    target_ids = [nid for nid in state.tested_nodes if nid not in EXAM_HEADS]
    if not target_ids:
        return []

    node_rows = (await session.execute(
        select(Node).where(Node.id.in_(target_ids))
    )).scalars().all()
    node_map = {n.id: n for n in node_rows}

    results: list[dict] = []
    for nid in target_ids:
        node = node_map.get(nid)
        if not node:
            continue
        answers = state.node_answers.get(nid, [])
        levels = _reconstruct_levels(answers) if answers else []

        level_marks: list[str] = []
        for lvl, ans in zip(levels, answers):
            mark = "✓" if ans[0] else "✗"
            level_marks.append(f"L{lvl}{mark}")

        p = state.evidence.get(nid, 0.5)
        if p >= 0.7:
            status = "mastered"
        elif p >= 0.3:
            status = "partial"
        else:
            status = "failed"

        results.append({
            "id": nid,
            "name": node.name_ru,
            "status": status,
            "evidence": round(p, 2),
            "levels": " ".join(level_marks),
        })
    return results
