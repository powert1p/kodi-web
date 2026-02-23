"""Two-phase adaptive diagnostic engine.

Phase 1 — "Тест на пробелы": quick scan via 5 anchor nodes, graph traversal.
Phase 2 — "Тест НИШ": deep scan of untested areas using Phase 1 results.

Both phases share the same traversal algorithm (next_question, handle_correct,
handle_incorrect). Only initialization and fill_gaps differ.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Attempt, Edge, Mastery, Node, Problem

_nis_first = case(
    (Problem.source.isnot(None) & (Problem.source != "generated"), 0),
    else_=1,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────

PHASE1_MAX_TOPICS = 10     # Phase 1: legacy (unused in new flow)
DIAG_MODE_TOPICS = 15      # Both exam & gaps modes: 15 topics
PHASE3_MAX_TOPICS = 40     # Phase 3+: 40 topics for repeat tests
DIAG_MASTERY_THRESHOLD = 0.5  # for outer-fringe in diagnostic context

PHASE1_ANCHORS = ["FR06", "EQ02", "PR02", "GE02", "CB01"]

PHASE1_GAP_NODES: dict[str, str] = {
    "arithmetic": "AR05",
    "fractions": "FR06",
    "decimals": "DC03",
    "divisibility": "DV02",
    "percent": "PC02",
    "proportion": "PR02",
    "equations": "EQ02",
    "algebra": "AL01",
    "numbers": "RN02",
    "geometry": "GE02",
    "conversion": "CV02",
    "word_problems": "WP02",
    "logic": "CB01",
    "sets": "ST01",
    "data": "DA01",
}

# Tags where difficulty is computational (up to 3 questions: easy→medium→hard)
COMPUTATIONAL_TAGS = frozenset({
    "arithmetic", "fractions", "decimals", "divisibility",
    "percent", "proportion", "conversion",
})

# ── Additive mastery scoring ──────────────────────────────────
LEVEL_WEIGHTS = {1: 0.15, 2: 0.25, 3: 0.30, 4: 0.30}
SPEED_THRESHOLDS = (25, 45, 65)   # < 25s fast, 25-45s, 45-65s, > 65s slow
L3_RETRY_PENALTY = 0.8            # L3 retry scored at 80% of weight


# ── Diagnostic session state ─────────────────────────────────


@dataclass
class DiagnosticState:
    student_id: int = 0
    phase: int = 1  # 1, 2, or 3+
    node_status: dict[str, str] = field(default_factory=dict)  # "mastered"/"failed"/"untested"/"partial"
    queue: list[str] = field(default_factory=list)
    tested_nodes: set[str] = field(default_factory=set)
    questions_asked: int = 0       # total individual questions
    topics_tested: int = 0         # unique topics tested (new topics only)
    max_topics: int = PHASE1_MAX_TOPICS  # stop after this many topics
    correct_count: int = 0
    # Multi-question tracking: {node_id: [[correct, elapsed_sec], ...]}
    node_answers: dict[str, list[list]] = field(default_factory=dict)
    # Cache: node_id → tag (loaded once on init)
    node_tags: dict[str, str] = field(default_factory=dict)

    def _is_computational(self, node_id: str) -> bool:
        """Check if a node belongs to a computational tag."""
        return self.node_tags.get(node_id, "") in COMPUTATIONAL_TAGS

    # ── serialization for FSM storage ──

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "phase": self.phase,
            "node_status": self.node_status,
            "queue": self.queue,
            "tested_nodes": list(self.tested_nodes),
            "questions_asked": self.questions_asked,
            "topics_tested": self.topics_tested,
            "max_topics": self.max_topics,
            "correct_count": self.correct_count,
            "node_answers": self.node_answers,
            "node_tags": self.node_tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DiagnosticState:
        return cls(
            student_id=data["student_id"],
            phase=data["phase"],
            node_status=data["node_status"],
            queue=data["queue"],
            tested_nodes=set(data["tested_nodes"]),
            questions_asked=data["questions_asked"],
            topics_tested=data.get("topics_tested", 0),
            max_topics=data.get("max_topics", data.get("max_questions", PHASE1_MAX_TOPICS)),
            correct_count=data["correct_count"],
            node_answers=data.get("node_answers", {}),
            node_tags=data.get("node_tags", {}),
        )


# ── Initialization ───────────────────────────────────────────


async def _load_node_tags(session: AsyncSession) -> dict[str, str]:
    """Load node_id → tag mapping from DB."""
    result = await session.execute(select(Node.id, Node.tag))
    return {row.id: (row.tag or "") for row in result.all()}


async def _compute_downstream_counts(session: AsyncSession) -> dict[str, int]:
    """For each node, count how many nodes depend on it (transitively).

    Higher count = more impactful to test first.
    """
    result = await session.execute(
        text("""
            WITH RECURSIVE all_deps AS (
                SELECT from_node AS root, to_node AS dep FROM edges
                UNION
                SELECT ad.root, e.to_node
                FROM all_deps ad
                JOIN edges e ON e.from_node = ad.dep
            )
            SELECT root, COUNT(DISTINCT dep) as cnt
            FROM all_deps
            GROUP BY root
        """)
    )
    counts = {row[0]: row[1] for row in result.all()}
    return counts


async def _build_sorted_queue(
    session: AsyncSession,
    node_ids: list[str],
    node_status: dict[str, str],
) -> list[str]:
    """Sort node_ids by downstream_count descending (most impactful first).

    Only includes untested nodes.
    """
    downstream = await _compute_downstream_counts(session)
    candidates = [
        (downstream.get(nid, 0), nid)
        for nid in node_ids
        if node_status.get(nid) == "untested"
    ]
    candidates.sort(key=lambda x: -x[0])
    return [nid for _, nid in candidates]


async def init_phase1(session: AsyncSession, student_id: int) -> DiagnosticState:
    """Phase 1: 'Тест на пробелы' — 10 topics, sorted by impact."""
    node_tags = await _load_node_tags(session)
    node_status = {nid: "untested" for nid in node_tags}

    # Build queue sorted by downstream count (most impactful first)
    # Start with anchors sorted by impact, then fill_gaps will add more
    sorted_queue = await _build_sorted_queue(
        session, list(PHASE1_ANCHORS), node_status
    )

    state = DiagnosticState(
        student_id=student_id,
        phase=1,
        node_status=node_status,
        queue=sorted_queue,
        tested_nodes=set(),
        questions_asked=0,
        topics_tested=0,
        max_topics=PHASE1_MAX_TOPICS,
        correct_count=0,
        node_tags=node_tags,
    )
    return state


async def init_exam(session: AsyncSession, student_id: int) -> DiagnosticState:
    """Exam prep mode: 15 topics, hardest first (by difficulty DESC)."""
    node_tags = await _load_node_tags(session)
    node_status = {nid: "untested" for nid in node_tags}

    # Load node difficulties
    result = await session.execute(select(Node.id, Node.difficulty))
    node_diff = {row.id: (row.difficulty or 1) for row in result.all()}

    # Sort by difficulty DESC (hardest topics first for exam prep)
    all_nodes = sorted(node_tags.keys(), key=lambda nid: -node_diff.get(nid, 1))

    state = DiagnosticState(
        student_id=student_id,
        phase=1,
        node_status=node_status,
        queue=all_nodes[:DIAG_MODE_TOPICS * 2],  # buffer for fill_gaps
        tested_nodes=set(),
        questions_asked=0,
        topics_tested=0,
        max_topics=DIAG_MODE_TOPICS,
        correct_count=0,
        node_tags=node_tags,
    )
    return state


async def init_gaps(session: AsyncSession, student_id: int) -> DiagnosticState:
    """Gaps mode: 15 topics, easiest first (by difficulty ASC)."""
    node_tags = await _load_node_tags(session)
    node_status = {nid: "untested" for nid in node_tags}

    # Load node difficulties
    result = await session.execute(select(Node.id, Node.difficulty))
    node_diff = {row.id: (row.difficulty or 1) for row in result.all()}

    # Sort by difficulty ASC (basic topics first for gap detection)
    all_nodes = sorted(node_tags.keys(), key=lambda nid: node_diff.get(nid, 1))

    state = DiagnosticState(
        student_id=student_id,
        phase=1,
        node_status=node_status,
        queue=all_nodes[:DIAG_MODE_TOPICS * 2],  # buffer for fill_gaps
        tested_nodes=set(),
        questions_asked=0,
        topics_tested=0,
        max_topics=DIAG_MODE_TOPICS,
        correct_count=0,
        node_tags=node_tags,
    )
    return state


async def _load_mastery_and_status(
    session: AsyncSession, student_id: int, node_tags: dict[str, str],
) -> tuple[dict[str, str], set[str]]:
    """Load mastery from DB and reconstruct node_status + tested_nodes.

    Shared by init_phase2 and init_phase3.
    """
    all_node_ids = list(node_tags.keys())

    mastery_result = await session.execute(
        select(Mastery.node_id, Mastery.p_mastery).where(
            Mastery.student_id == student_id
        )
    )
    mastery_map = {row.node_id: row.p_mastery for row in mastery_result.all()}

    node_status: dict[str, str] = {}
    for nid in all_node_ids:
        if nid in mastery_map:
            pm = mastery_map[nid]
            if pm >= 0.7:
                node_status[nid] = "mastered"
            elif pm >= 0.2:
                node_status[nid] = "partial"
            else:
                node_status[nid] = "failed"
        else:
            node_status[nid] = "untested"

    tested_result = await session.execute(
        select(Attempt.node_id).where(
            Attempt.student_id == student_id,
            Attempt.source.in_(["diagnostic", "skip", "exam"]),
        ).distinct()
    )
    tested_nodes = set(tested_result.scalars().all())

    return node_status, tested_nodes


async def init_phase2(session: AsyncSession, student_id: int) -> DiagnosticState:
    """Phase 2: 'Тест НИШ' — deep scan of ALL remaining untested nodes.

    No topic limit — covers everything Phase 1 missed.
    Queue sorted by downstream_count (most impactful first).
    """
    node_tags = await _load_node_tags(session)
    node_status, tested_nodes = await _load_mastery_and_status(
        session, student_id, node_tags
    )

    untested_count = sum(1 for s in node_status.values() if s == "untested")

    # Build queue sorted by downstream count — most impactful untested first
    untested_ids = [nid for nid, s in node_status.items() if s == "untested"]
    sorted_queue = await _build_sorted_queue(session, untested_ids, node_status)

    state = DiagnosticState(
        student_id=student_id,
        phase=2,
        node_status=node_status,
        queue=sorted_queue,
        tested_nodes=tested_nodes,
        questions_asked=0,
        topics_tested=0,
        max_topics=untested_count,  # no limit — cover all
        correct_count=0,
        node_tags=node_tags,
    )
    return state


async def init_phase3(session: AsyncSession, student_id: int) -> DiagnosticState:
    """Phase 3+: Repeat test — re-evaluate 40 topics.

    Prioritizes failed/partial nodes, then mastered nodes for reinforcement.
    Queue sorted by downstream_count (most impactful first).
    """
    node_tags = await _load_node_tags(session)
    node_status, tested_nodes = await _load_mastery_and_status(
        session, student_id, node_tags
    )

    # For Phase 3, ALL nodes start as "untested" so they can be re-tested
    # But we preserve the old status for mastery averaging later
    phase3_status: dict[str, str] = {nid: "untested" for nid in node_tags}

    # Build candidate list: prioritize weak nodes, then strong ones
    downstream = await _compute_downstream_counts(session)
    weak = []   # failed + partial — need re-evaluation
    strong = []  # mastered — reinforcement

    for nid in node_tags:
        old = node_status.get(nid, "untested")
        weight = downstream.get(nid, 0)
        if old in ("failed", "partial", "untested"):
            weak.append((weight, nid))
        else:
            strong.append((weight, nid))

    weak.sort(key=lambda x: -x[0])
    strong.sort(key=lambda x: -x[0])

    # Fill queue: weak first, then strong, up to PHASE3_MAX_TOPICS
    queue_ids = [nid for _, nid in weak]
    if len(queue_ids) < PHASE3_MAX_TOPICS:
        queue_ids.extend(nid for _, nid in strong)
    queue_ids = queue_ids[:PHASE3_MAX_TOPICS]

    state = DiagnosticState(
        student_id=student_id,
        phase=3,
        node_status=phase3_status,
        queue=queue_ids,
        tested_nodes=set(),  # fresh start for Phase 3
        questions_asked=0,
        topics_tested=0,
        max_topics=PHASE3_MAX_TOPICS,
        correct_count=0,
        node_tags=node_tags,
    )
    return state


# ── Main loop ────────────────────────────────────────────────


async def next_question(
    session: AsyncSession, state: DiagnosticState
) -> Problem | None:
    """Pop the next node from queue, find a problem, return it.

    Returns None when the diagnostic should finish.
    Termination is based on topics_tested (unique nodes), not total questions.
    """
    # Topic-based termination
    if state.topics_tested >= state.max_topics:
        return None

    filled_gaps = False

    while True:
        # Drain the queue looking for a valid node
        while state.queue:
            node_id = state.queue.pop(0)

            # Multi-question: node re-enqueued for follow-up
            if node_id in state.node_answers and len(state.node_answers[node_id]) > 0:
                # This is a follow-up question (node already tested once)
                # Follow-ups do NOT count toward topics_tested
                sub_diff = _next_sub_difficulty(state, node_id)
                problem = await _pick_problem(session, node_id, sub_diff, state.student_id)
                if problem is None:
                    # No problem at this sub_difficulty — decide with what we have
                    answers = state.node_answers[node_id]
                    levels = _reconstruct_levels(answers)
                    highest_correct = max(
                        (lvl for lvl, a in zip(levels, answers) if a[0]),
                        default=0,
                    )
                    if highest_correct >= 3:
                        state.node_status[node_id] = "mastered"
                    elif highest_correct > 0:
                        state.node_status[node_id] = "partial"
                    else:
                        state.node_status[node_id] = "failed"
                    continue
                state.questions_asked += 1
                return problem

            # Skip already tested or transitively marked
            if node_id in state.tested_nodes:
                continue
            if state.node_status.get(node_id) != "untested":
                continue

            # Check topic limit before starting a NEW topic
            if state.topics_tested >= state.max_topics:
                return None

            # First question for this node — start with hard (sub_difficulty=3)
            sub_diff = _next_sub_difficulty(state, node_id)
            problem = await _pick_problem(session, node_id, sub_diff, state.student_id)
            if problem is None:
                # No problems for this node — skip
                continue

            state.tested_nodes.add(node_id)
            state.topics_tested += 1
            state.questions_asked += 1
            return problem

        # Queue empty — try fill_gaps ONCE
        if filled_gaps:
            return None  # already tried, nothing left

        if state.phase == 1:
            await _fill_gaps_phase1(session, state)
        else:
            await _fill_gaps_phase2(session, state)
        filled_gaps = True

        if not state.queue:
            return None  # fill_gaps found nothing


async def _pick_problem(
    session: AsyncSession,
    node_id: str,
    sub_difficulty: int | None = None,
    student_id: int | None = None,
) -> Problem | None:
    """Pick a random problem for the given node that the student hasn't seen.

    Falls back to any unseen problem for this node if the exact sub_difficulty
    has no unseen problems. If ALL problems have been seen, allows repeats.
    """
    # Subquery: problem IDs this student already attempted
    seen_ids = set()
    if student_id:
        seen_result = await session.execute(
            select(Attempt.problem_id).where(
                Attempt.student_id == student_id,
                Attempt.node_id == node_id,
            )
        )
        seen_ids = {row[0] for row in seen_result.all()}

    # Try: exact sub_difficulty, excluding seen
    q = select(Problem).where(Problem.node_id == node_id)
    if sub_difficulty is not None:
        q = q.where(Problem.sub_difficulty == sub_difficulty)
    if seen_ids:
        q = q.where(Problem.id.notin_(seen_ids))
    result = await session.execute(q.order_by(_nis_first, func.random()).limit(1))
    prob = result.scalar_one_or_none()
    if prob is not None:
        return prob

    # Fallback 1: any sub_difficulty for this node, excluding seen
    if sub_difficulty is not None:
        q2 = select(Problem).where(Problem.node_id == node_id)
        if seen_ids:
            q2 = q2.where(Problem.id.notin_(seen_ids))
        result = await session.execute(q2.order_by(_nis_first, func.random()).limit(1))
        prob = result.scalar_one_or_none()
        if prob is not None:
            return prob

    # Fallback 2: allow repeats (all problems seen)
    q3 = select(Problem).where(Problem.node_id == node_id)
    if sub_difficulty is not None:
        q3 = q3.where(Problem.sub_difficulty == sub_difficulty)
    result = await session.execute(q3.order_by(_nis_first, func.random()).limit(1))
    prob = result.scalar_one_or_none()
    if prob is None and sub_difficulty is not None:
        result = await session.execute(
            select(Problem)
            .where(Problem.node_id == node_id)
            .order_by(_nis_first, func.random())
            .limit(1)
        )
        prob = result.scalar_one_or_none()
    return prob


def _reconstruct_levels(answers: list[list]) -> list[int]:
    """Reconstruct the sub_difficulty sequence from answer history.

    State-machine transition table (top-down with recovery):
      Q1: L3 (always)
        correct → Q2: L4
        wrong   → Q2: L1
      Q2 after L3-correct: L4 → STOP
      Q2 after L3-wrong: L1
        wrong  → STOP
        correct → Q3: L2
      Q3: L2
        wrong  → STOP
        correct → Q4: L3 (retry)
      Q4: L3 (retry)
        wrong  → STOP
        correct → Q5: L4 → STOP

    Returns list of levels for each answer, e.g. [3, 1, 2, 3, 4].
    """
    if not answers:
        return []

    levels = [3]  # Q1 is always L3
    for i in range(1, len(answers)):
        prev_level = levels[i - 1]
        prev_correct = answers[i - 1][0]

        if prev_level == 3 and i == 1:
            # After first L3
            levels.append(4 if prev_correct else 1)
        elif prev_level == 4:
            break  # L4 is always terminal
        elif prev_level == 1:
            if prev_correct:
                levels.append(2)  # L1 ok → L2
            else:
                break  # L1 fail → STOP
        elif prev_level == 2:
            if prev_correct:
                levels.append(3)  # L2 ok → L3 retry
            else:
                break  # L2 fail → STOP
        elif prev_level == 3 and i > 1:
            # L3 retry
            if prev_correct:
                levels.append(4)  # L3 retry ok → L4
            else:
                break  # L3 retry fail → STOP
        else:
            break

    return levels


def _next_sub_difficulty(state: DiagnosticState, node_id: str) -> int:
    """Determine which sub_difficulty to ask next for a node.

    Top-down with recovery path:
      L3 → (ok? L4 : L1 → ok? L2 → ok? L3_retry → ok? L4)
    """
    answers = state.node_answers.get(node_id, [])
    if not answers:
        return 3  # always start with L3 (hard)

    levels = _reconstruct_levels(answers)
    last_level = levels[-1]
    last_correct = answers[-1][0]

    if last_level == 3 and len(levels) == 1:
        return 4 if last_correct else 1
    if last_level == 1:
        return 2 if last_correct else 1  # fallback (shouldn't reach if STOP)
    if last_level == 2:
        return 3 if last_correct else 1
    if last_level == 3 and len(levels) > 1:
        return 4 if last_correct else 2
    return 4  # fallback


def _should_ask_again(state: DiagnosticState, node_id: str) -> bool:
    """Should we ask another question for this node?

    Top-down with recovery:
      L3 correct → ask L4               (continue)
      L3 wrong   → ask L1               (continue — recovery path)
      L4         → STOP                  (terminal — any result)
      L1 wrong   → STOP                  (failed)
      L1 correct → ask L2               (continue)
      L2 wrong   → STOP                  (knows basics)
      L2 correct → ask L3 retry         (continue)
      L3 retry wrong  → STOP            (knows medium)
      L3 retry correct → ask L4         (continue)
      L4 after retry   → STOP           (terminal)
    """
    answers = state.node_answers.get(node_id, [])
    n = len(answers)
    if n == 0:
        return False

    levels = _reconstruct_levels(answers)
    last_level = levels[-1]
    last_correct = answers[-1][0]

    # L4 is always terminal
    if last_level == 4:
        return False

    # After first L3
    if last_level == 3 and n == 1:
        return True  # always continue: correct → L4, wrong → L1

    # After L1
    if last_level == 1:
        return last_correct  # correct → L2; wrong → STOP

    # After L2
    if last_level == 2:
        return last_correct  # correct → L3 retry; wrong → STOP

    # After L3 retry (n > 1)
    if last_level == 3 and n > 1:
        return last_correct  # correct → L4; wrong → STOP

    return False


# ── Answer processing ────────────────────────────────────────


async def handle_correct(
    session: AsyncSession, state: DiagnosticState, node_id: str,
    elapsed: float = 0.0,
) -> None:
    """Correct answer in top-down with recovery flow (additive scoring).

    Score = sum of level weights (L1=15%, L2=25%, L3=30%, L4=30%).
    Status: >= 0.7 mastered, >= 0.2 partial, < 0.2 failed.
    Propagation: if highest_correct >= 3, prereqs auto-mastered.
    """
    state.correct_count += 1
    state.node_answers.setdefault(node_id, []).append([True, elapsed])

    # Should we ask another question? (e.g. L3 ok → L4)
    if _should_ask_again(state, node_id):
        state.queue.insert(0, node_id)
        return

    # Sequence is done — compute additive score and determine status
    answers = state.node_answers[node_id]
    levels = _reconstruct_levels(answers)
    score = _compute_additive_mastery(answers)

    # Find highest correct level (for propagation logic)
    highest_correct = 0
    for lvl, a in zip(levels, answers):
        if a[0] and lvl > highest_correct:
            highest_correct = lvl

    # Set status based on additive score
    if score >= 0.7:
        state.node_status[node_id] = "mastered"
    elif score >= 0.2:
        state.node_status[node_id] = "partial"
    else:
        state.node_status[node_id] = "failed"

    # Propagation: only if L3+ was correctly answered (knows the basics)
    if highest_correct < 3:
        return  # only L1/L2 correct — don't propagate

    # Propagate mastery downward (L3+ correct = prereqs are clearly known)

    # 1. Transitive prereqs down — auto-mark as mastered
    prereqs_below = await _get_all_prereqs_recursive(session, node_id)
    for prereq_id in prereqs_below:
        if state.node_status.get(prereq_id) == "untested":
            state.node_status[prereq_id] = "mastered"

    # 2. Add dependent nodes above (where ALL prereqs are now mastered)
    dependents = await session.execute(
        select(Edge.to_node).where(Edge.from_node == node_id)
    )
    for (dep_id,) in dependents.all():
        if dep_id in state.tested_nodes:
            continue
        if state.node_status.get(dep_id) != "untested":
            continue

        dep_prereqs = await session.execute(
            select(Edge.from_node).where(Edge.to_node == dep_id)
        )
        all_mastered = all(
            state.node_status.get(p) == "mastered"
            for (p,) in dep_prereqs.all()
        )
        if all_mastered:
            state.queue.append(dep_id)


async def handle_incorrect(
    session: AsyncSession, state: DiagnosticState, node_id: str,
    elapsed: float = 0.0,
) -> None:
    """Incorrect answer in top-down with recovery flow (additive scoring).

    Score = sum of level weights for correct answers.
    Status: >= 0.7 mastered, >= 0.2 partial, < 0.2 failed.
    Propagation: if highest_correct >= 3, prereqs auto-mastered (same as handle_correct).
    Failure propagation: if score < 0.2, dependents above marked failed.
    """
    state.node_answers.setdefault(node_id, []).append([False, elapsed])

    answers = state.node_answers[node_id]

    # Should we continue probing? (e.g. L3 wrong → try L1)
    if _should_ask_again(state, node_id):
        state.queue.insert(0, node_id)
        return

    # Sequence is done — compute score and determine status
    levels = _reconstruct_levels(answers)
    score = _compute_additive_mastery(answers)

    # Find highest correct level (for propagation logic)
    highest_correct = 0
    for lvl, a in zip(levels, answers):
        if a[0] and lvl > highest_correct:
            highest_correct = lvl

    # Set status based on additive score
    if score >= 0.7:
        state.node_status[node_id] = "mastered"
    elif score >= 0.2:
        state.node_status[node_id] = "partial"
    else:
        state.node_status[node_id] = "failed"

    # Propagate mastery downward if L3+ was correct (same as handle_correct)
    if highest_correct >= 3:
        prereqs_below = await _get_all_prereqs_recursive(session, node_id)
        for prereq_id in prereqs_below:
            if state.node_status.get(prereq_id) == "untested":
                state.node_status[prereq_id] = "mastered"

        dependents = await session.execute(
            select(Edge.to_node).where(Edge.from_node == node_id)
        )
        for (dep_id,) in dependents.all():
            if dep_id in state.tested_nodes:
                continue
            if state.node_status.get(dep_id) != "untested":
                continue
            dep_prereqs = await session.execute(
                select(Edge.from_node).where(Edge.to_node == dep_id)
            )
            all_mastered = all(
                state.node_status.get(p) == "mastered"
                for (p,) in dep_prereqs.all()
            )
            if all_mastered:
                state.queue.append(dep_id)
        return

    # score < 0.2 → failed — propagate failure UPWARD
    if score < 0.2:
        dependents_above = await _get_all_dependents_recursive(session, node_id)
        for dep_id in dependents_above:
            if state.node_status.get(dep_id) == "untested":
                state.node_status[dep_id] = "failed"
        logger.info(
            "Node %s failed → propagated failure to %d dependents above",
            node_id, len([d for d in dependents_above
                           if state.node_status.get(d) == "failed"]),
        )

        # Direct prereqs — insert at front (drill down to find the gap)
        prereqs = await session.execute(
            select(Edge.from_node).where(Edge.to_node == node_id)
        )
        insert_pos = 0
        for (prereq_id,) in prereqs.all():
            if prereq_id not in state.tested_nodes and state.node_status.get(prereq_id) == "untested":
                state.queue.insert(insert_pos, prereq_id)
                insert_pos += 1


async def _get_all_prereqs_recursive(
    session: AsyncSession, node_id: str
) -> list[str]:
    """All transitive prerequisites BELOW node_id via recursive CTE."""
    result = await session.execute(
        text("""
            WITH RECURSIVE prereqs AS (
                SELECT from_node FROM edges WHERE to_node = :node_id
                UNION
                SELECT e.from_node FROM edges e
                JOIN prereqs p ON e.to_node = p.from_node
            )
            SELECT from_node FROM prereqs
        """),
        {"node_id": node_id},
    )
    return [row[0] for row in result.all()]


async def _get_all_dependents_recursive(
    session: AsyncSession, node_id: str
) -> list[str]:
    """All transitive dependents ABOVE node_id via recursive CTE.

    If AR02 is failed, this returns everything that depends on AR02:
    AR03, AR05, FR01, EQ01, etc.
    """
    result = await session.execute(
        text("""
            WITH RECURSIVE deps AS (
                SELECT to_node FROM edges WHERE from_node = :node_id
                UNION
                SELECT e.to_node FROM edges e
                JOIN deps d ON e.from_node = d.to_node
            )
            SELECT to_node FROM deps
        """),
        {"node_id": node_id},
    )
    return [row[0] for row in result.all()]


# ── Fill gaps ────────────────────────────────────────────────


async def _fill_gaps_phase1(
    session: AsyncSession, state: DiagnosticState
) -> None:
    """Phase 1: add one representative from each uncovered category.

    Sorted by downstream_count (most impactful first).
    Only adds nodes whose prerequisites are NOT failed (no blocked branches).
    """
    # Which tags are already covered?
    node_tags: dict[str, str] = {}
    nodes_result = await session.execute(select(Node.id, Node.tag))
    for row in nodes_result.all():
        node_tags[row.id] = row.tag or ""

    covered_tags: set[str] = set()
    for nid, status in state.node_status.items():
        if status != "untested":
            covered_tags.add(node_tags.get(nid, ""))

    # Build prereq map for quick lookup
    edges_result = await session.execute(select(Edge.from_node, Edge.to_node))
    prereq_map: dict[str, list[str]] = {}
    for from_n, to_n in edges_result.all():
        prereq_map.setdefault(to_n, []).append(from_n)

    # Collect eligible gap nodes
    gap_candidates: list[str] = []
    for tag, gap_node in PHASE1_GAP_NODES.items():
        if tag not in covered_tags and gap_node not in state.tested_nodes:
            if state.node_status.get(gap_node) != "untested":
                continue
            direct_prereqs = prereq_map.get(gap_node, [])
            if any(state.node_status.get(p) == "failed" for p in direct_prereqs):
                continue
            gap_candidates.append(gap_node)

    # Sort by downstream impact and add to queue
    if gap_candidates:
        downstream = await _compute_downstream_counts(session)
        gap_candidates.sort(key=lambda nid: -downstream.get(nid, 0))
        for gap_node in gap_candidates[:5]:
            state.queue.append(gap_node)


async def _fill_gaps_phase2(
    session: AsyncSession, state: DiagnosticState
) -> None:
    """Phase 2/3: add remaining untested nodes sorted by downstream count.

    Only adds nodes whose prerequisites are NOT failed.
    """
    # Build prereq map
    edges_result = await session.execute(select(Edge.from_node, Edge.to_node))
    prereq_map: dict[str, list[str]] = {}
    for from_n, to_n in edges_result.all():
        prereq_map.setdefault(to_n, []).append(from_n)

    downstream = await _compute_downstream_counts(session)

    # Collect all eligible untested nodes
    candidates: list[tuple[int, str]] = []
    for nid, status in state.node_status.items():
        if nid in state.tested_nodes or status != "untested":
            continue
        direct_prereqs = prereq_map.get(nid, [])
        if any(state.node_status.get(p) == "failed" for p in direct_prereqs):
            continue
        candidates.append((downstream.get(nid, 0), nid))

    # Sort by downstream count descending (most impactful first)
    candidates.sort(key=lambda x: -x[0])
    for _, nid in candidates[:10]:
        state.queue.append(nid)


# ── Write results to DB ──────────────────────────────────────


def _speed_factor(elapsed: float) -> float:
    """Per-answer speed factor based on response time.

    < 25s → 1.0  (fast — full 30% bonus)
    25-45s → 0.67
    45-65s → 0.33
    > 65s → 0.0  (slow — only base 70% of weight)
    """
    if elapsed <= 0:
        return 1.0
    if elapsed < SPEED_THRESHOLDS[0]:
        return 1.0
    if elapsed < SPEED_THRESHOLDS[1]:
        return 0.67
    if elapsed < SPEED_THRESHOLDS[2]:
        return 0.33
    return 0.0


def _compute_additive_mastery(answers: list[list]) -> float:
    """Additive mastery: each level contributes its weight to the total score.

    Weights: L1=15%, L2=25%, L3=30%, L4=30%.
    Each correct answer: weight × (0.7 + 0.3 × speed_factor).
    Auto-credit: when a level is passed, all lower untested levels get 100% weight.
    L3 retry penalty: if L3 was failed first then retried, L3 weight × 0.8.
    L4 has no retry penalty.

    Returns p_mastery in range [0.0, 1.0].
    """
    if not answers:
        return 0.0

    levels = _reconstruct_levels(answers)
    if not levels:
        return 0.0

    # Detect retry: first L3 was wrong → recovery path
    had_retry = False
    l3_count = 0
    for lvl, a in zip(levels, answers):
        if lvl == 3:
            l3_count += 1
            if l3_count == 1 and not a[0]:
                had_retry = True

    # Collect first occurrence of each tested level
    tested_levels: dict[int, tuple[bool, float]] = {}
    for lvl, a in zip(levels, answers):
        if lvl not in tested_levels:
            tested_levels[lvl] = (a[0], a[1])
        elif lvl == 3 and l3_count > 1 and not tested_levels[3][0]:
            # L3 retry: overwrite the failed first attempt with the retry result
            tested_levels[3] = (a[0], a[1])

    score = 0.0
    credited: set[int] = set()

    for lvl in sorted(tested_levels.keys()):
        correct, elapsed = tested_levels[lvl]
        if not correct:
            continue

        weight = LEVEL_WEIGHTS[lvl]

        # Apply L3 retry penalty
        if lvl == 3 and had_retry:
            weight *= L3_RETRY_PENALTY

        score += weight * (0.7 + 0.3 * _speed_factor(elapsed))
        credited.add(lvl)

        # Auto-credit all lower levels that were NOT tested
        for lower in range(1, lvl):
            if lower not in tested_levels and lower not in credited:
                score += LEVEL_WEIGHTS[lower]  # full weight
                credited.add(lower)

    return round(min(score, 1.0), 3)


async def write_mastery_to_db(
    session: AsyncSession, state: DiagnosticState
) -> None:
    """Write diagnostic mastery to DB. Phase 2 averages with existing values."""
    for node_id, status in state.node_status.items():
        if status == "untested":
            continue

        answers = state.node_answers.get(node_id, [])

        if answers:
            p_mastery = _compute_additive_mastery(answers)
        else:
            # Transitive (not directly tested)
            if status == "mastered":
                p_mastery = 0.7
            elif status == "partial":
                p_mastery = 0.4
            else:
                p_mastery = 0.0

        was_tested = node_id in state.tested_nodes

        # Check existing mastery
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
                p_mastery=p_mastery,
                attempts_total=1 if was_tested else 0,
                attempts_correct=1 if (was_tested and status == "mastered") else 0,
            )
            session.add(mastery)
        else:
            if state.phase >= 2:
                # Phase 2/3: weighted average with existing (60% new, 40% old)
                mastery.p_mastery = round(p_mastery * 0.6 + mastery.p_mastery * 0.4, 3)
            else:
                mastery.p_mastery = p_mastery

            if was_tested:
                mastery.attempts_total += 1
                if status == "mastered":
                    mastery.attempts_correct += 1

    await session.flush()


# ── Compute outer fringe ─────────────────────────────────────


async def compute_outer_fringe(
    session: AsyncSession, student_id: int
) -> list[dict]:
    """Outer fringe: nodes with p_mastery < 0.5 where all prereqs >= 0.5.

    Returns list of dicts: {id, name_ru, tag, difficulty}.
    Sorted by difficulty ASC (easiest first).
    """
    result = await session.execute(
        text("""
            SELECT n.id, n.name_ru, n.tag, n.difficulty
            FROM nodes n
            WHERE
                COALESCE(
                    (SELECT m.p_mastery FROM mastery m
                     WHERE m.student_id = :sid AND m.node_id = n.id),
                    0
                ) < 0.5
                AND NOT EXISTS (
                    SELECT 1 FROM edges e
                    LEFT JOIN mastery m
                        ON m.node_id = e.from_node AND m.student_id = :sid
                    WHERE e.to_node = n.id
                      AND COALESCE(m.p_mastery, 0) < 0.5
                )
            ORDER BY n.difficulty ASC
        """),
        {"sid": student_id},
    )
    return [
        {"id": row[0], "name_ru": row[1], "tag": row[2], "difficulty": row[3]}
        for row in result.all()
    ]


# ── Finish diagnostic ────────────────────────────────────────


async def finish_phase1(
    session: AsyncSession, state: DiagnosticState
) -> dict:
    """Finish Phase 1, write to DB, return result summary.

    Note: does NOT set diagnostic_complete — that happens after Phase 2.
    """
    await write_mastery_to_db(session, state)
    await session.commit()

    mastered = [nid for nid, s in state.node_status.items() if s == "mastered"]
    failed = [nid for nid, s in state.node_status.items() if s == "failed"]
    partial = [nid for nid, s in state.node_status.items() if s == "partial"]
    untested = [nid for nid, s in state.node_status.items() if s == "untested"]

    outer_fringe = await compute_outer_fringe(session, state.student_id)

    # Category breakdown (same as Phase 2)
    category_stats = await _get_category_stats(session, state)

    # Only the directly failed topics (tested + transitive) for the "gaps" section
    failed_details = await _get_node_names(session, failed)
    partial_details = await _get_node_names(session, partial)

    # Build tested-node details for display
    tested_details = await _get_tested_details(session, state)

    total_nodes = len(state.node_status)

    # Test finished early if graph was fully mapped before hitting topic limit
    early_stop = state.topics_tested < state.max_topics

    return {
        "phase": 1,
        "score": f"{state.correct_count}/{state.questions_asked}",
        "topics_tested": state.topics_tested,
        "mastered_count": len(mastered),
        "failed_count": len(failed),
        "partial_count": len(partial),
        "untested_count": len(untested),
        "total_nodes": total_nodes,
        "tested_details": tested_details,
        "category_stats": category_stats,
        "failed_details": failed_details,
        "partial_details": partial_details,
        "outer_fringe": outer_fringe[:5],
        "show_phase2": len(untested) > 0,
        "early_stop": early_stop,
        "tested_nodes": state.tested_nodes,
    }


async def finish_phase2(
    session: AsyncSession, state: DiagnosticState
) -> dict:
    """Finish Phase 2, write to DB, return full result summary."""
    await write_mastery_to_db(session, state)

    # Mark diagnostic as complete after Phase 2
    from db.models import Student
    student = await session.get(Student, state.student_id)
    if student:
        student.diagnostic_complete = True

    await session.commit()

    mastered = [nid for nid, s in state.node_status.items() if s == "mastered"]
    failed = [nid for nid, s in state.node_status.items() if s == "failed"]
    partial = [nid for nid, s in state.node_status.items() if s == "partial"]
    untested = [nid for nid, s in state.node_status.items() if s == "untested"]

    outer_fringe = await compute_outer_fringe(session, state.student_id)

    # Category breakdown
    category_stats = await _get_category_stats(session, state)

    # Failed + partial node names
    failed_details = await _get_node_names(session, failed)
    partial_details = await _get_node_names(session, partial)

    tested_details = await _get_tested_details(session, state)

    total_nodes = len(state.node_status)

    early_stop = state.topics_tested < state.max_topics

    return {
        "phase": 2,
        "score": f"{state.correct_count}/{state.questions_asked}",
        "topics_tested": state.topics_tested,
        "mastered_count": len(mastered),
        "failed_count": len(failed),
        "partial_count": len(partial),
        "untested_count": len(untested),
        "total_nodes": total_nodes,
        "tested_details": tested_details,
        "category_stats": category_stats,
        "failed_details": failed_details,
        "partial_details": partial_details,
        "outer_fringe": outer_fringe[:5],
        "early_stop": early_stop,
    }


async def finish_phase3(
    session: AsyncSession, state: DiagnosticState
) -> dict:
    """Finish Phase 3 (repeat test), write to DB, return result summary."""
    await write_mastery_to_db(session, state)
    await session.commit()

    mastered = [nid for nid, s in state.node_status.items() if s == "mastered"]
    failed = [nid for nid, s in state.node_status.items() if s == "failed"]
    partial = [nid for nid, s in state.node_status.items() if s == "partial"]
    untested = [nid for nid, s in state.node_status.items() if s == "untested"]

    outer_fringe = await compute_outer_fringe(session, state.student_id)
    category_stats = await _get_category_stats(session, state)
    failed_details = await _get_node_names(session, failed)
    partial_details = await _get_node_names(session, partial)
    tested_details = await _get_tested_details(session, state)

    total_nodes = len(state.node_status)
    early_stop = state.topics_tested < state.max_topics

    return {
        "phase": 3,
        "score": f"{state.correct_count}/{state.questions_asked}",
        "topics_tested": state.topics_tested,
        "mastered_count": len(mastered),
        "failed_count": len(failed),
        "partial_count": len(partial),
        "untested_count": len(untested),
        "total_nodes": total_nodes,
        "tested_details": tested_details,
        "category_stats": category_stats,
        "failed_details": failed_details,
        "partial_details": partial_details,
        "outer_fringe": outer_fringe[:5],
        "early_stop": early_stop,
    }


# ── Helpers ──────────────────────────────────────────────────


async def _get_tested_details(
    session: AsyncSession, state: DiagnosticState
) -> list[dict]:
    """Get name + status for each directly tested node."""
    details: list[dict] = []
    for nid in state.tested_nodes:
        node = await session.get(Node, nid)
        if node:
            details.append({
                "id": nid,
                "name_ru": node.name_ru,
                "status": state.node_status.get(nid, "untested"),
            })
    return details


async def _get_node_names(
    session: AsyncSession, node_ids: list[str]
) -> list[dict]:
    """Get name for a list of node IDs."""
    result: list[dict] = []
    for nid in node_ids:
        node = await session.get(Node, nid)
        if node:
            result.append({"id": nid, "name_ru": node.name_ru})
    return result


async def _get_category_stats(
    session: AsyncSession, state: DiagnosticState
) -> list[dict]:
    """Per-category mastered/total counts."""
    # Fetch all nodes with tags
    nodes_result = await session.execute(select(Node.id, Node.tag))
    tag_map: dict[str, str] = {}
    for row in nodes_result.all():
        tag_map[row.id] = row.tag or "other"

    TAG_NAMES: dict[str, str] = {
        "arithmetic": "Арифметика",
        "numbers": "Числа",
        "fractions": "Дроби",
        "decimals": "Десятичные дроби",
        "percent": "Проценты",
        "proportion": "Пропорции",
        "equations": "Уравнения",
        "algebra": "Алгебра",
        "geometry": "Геометрия",
        "word_problems": "Текст. задачи",
        "divisibility": "Делимость",
        "conversion": "Ед. измерения",
        "sets": "Множества",
        "data": "Данные и графики",
        "logic": "Логика",
    }

    # Count per tag (partial counts as 0.5)
    stats: dict[str, dict] = {}
    for nid, status in state.node_status.items():
        tag = tag_map.get(nid, "other")
        if tag not in stats:
            stats[tag] = {"total": 0, "mastered": 0}
        stats[tag]["total"] += 1
        if status == "mastered":
            stats[tag]["mastered"] += 1
        elif status == "partial":
            stats[tag]["mastered"] += 0.5

    result: list[dict] = []
    for tag, s in sorted(stats.items(), key=lambda x: x[1]["mastered"] / max(x[1]["total"], 1), reverse=True):
        name = TAG_NAMES.get(tag, tag.capitalize())
        ratio = s["mastered"] / s["total"] if s["total"] else 0
        icon = "✅" if ratio >= 0.8 else "⚠️" if ratio >= 0.4 else "❌"
        result.append({
            "tag": tag,
            "name": name,
            "mastered": s["mastered"],
            "total": s["total"],
            "icon": icon,
        })

    return result
