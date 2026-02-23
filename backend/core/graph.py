"""Knowledge-graph operations.

Key concepts (from Knowledge Space Theory):
    outer fringe  — skills the student is READY to learn (all prereqs mastered).
    inner fringe  — recently mastered skills, vulnerable to forgetting.
    backward walk — when a student fails a node, trace prereqs to find the root gap.
"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.bkt import MASTERY_THRESHOLD, get_or_create_mastery
from db.models import Edge, Mastery, Node


async def get_prerequisites(session: AsyncSession, node_id: str) -> list[str]:
    """Return IDs of direct prerequisite nodes."""
    result = await session.execute(
        select(Edge.from_node).where(Edge.to_node == node_id)
    )
    return list(result.scalars().all())


async def get_dependents(session: AsyncSession, node_id: str) -> list[str]:
    """Return IDs of nodes that depend on *node_id* (node_id is their prereq)."""
    result = await session.execute(
        select(Edge.to_node).where(Edge.from_node == node_id)
    )
    return list(result.scalars().all())


async def get_mastery_map(
    session: AsyncSession, student_id: int
) -> dict[str, float]:
    """Return {node_id: p_mastery} for all nodes the student has touched."""
    result = await session.execute(
        select(Mastery.node_id, Mastery.p_mastery).where(
            Mastery.student_id == student_id
        )
    )
    return {row.node_id: row.p_mastery for row in result.all()}


async def get_outer_fringe(
    session: AsyncSession,
    student_id: int,
    threshold: float | None = None,
) -> list[str]:
    """Nodes where ALL prerequisites are mastered but the node itself is NOT.

    *threshold* controls what counts as "mastered":
        - Default (None) uses MASTERY_THRESHOLD (0.95) — for practice mode.
        - Pass 0.5 after diagnostic (mastered=0.8, failed=0.2).

    For nodes with NO prerequisites and p_mastery < threshold — they are also
    in the outer fringe (entry points like AR01).
    """
    if threshold is None:
        threshold = MASTERY_THRESHOLD

    mastery_map = await get_mastery_map(session, student_id)

    # Fetch all nodes
    all_nodes = (await session.execute(select(Node.id))).scalars().all()

    # Fetch all edges
    edges_result = await session.execute(select(Edge.from_node, Edge.to_node))
    edges = edges_result.all()

    # Build prereq map: node_id -> list of prerequisite node_ids
    prereqs: dict[str, list[str]] = {nid: [] for nid in all_nodes}
    for from_n, to_n in edges:
        prereqs[to_n].append(from_n)

    fringe: list[str] = []
    for node_id in all_nodes:
        own_mastery = mastery_map.get(node_id, 0.0)
        if own_mastery >= threshold:
            continue  # already mastered

        prs = prereqs[node_id]
        if not prs:
            # Root node (no prereqs) — always in fringe if not mastered
            fringe.append(node_id)
            continue

        # All prereqs must be mastered
        all_prereqs_ok = all(
            mastery_map.get(p, 0.0) >= threshold for p in prs
        )
        if all_prereqs_ok:
            fringe.append(node_id)

    return fringe


async def count_downstream(session: AsyncSession, node_id: str) -> int:
    """Count how many nodes are reachable downstream from *node_id*.

    Used to prioritise 'unblocking' nodes that open the most new skills.
    """
    result = await session.execute(
        text("""
            WITH RECURSIVE downstream AS (
                SELECT e.to_node AS nid
                FROM edges e
                WHERE e.from_node = :node_id
                UNION
                SELECT e.to_node
                FROM edges e
                JOIN downstream d ON e.from_node = d.nid
            )
            SELECT COUNT(DISTINCT nid) FROM downstream
        """),
        {"node_id": node_id},
    )
    return result.scalar_one()


async def backward_diagnose(
    session: AsyncSession,
    student_id: int,
    failed_node_id: str,
    max_depth: int = 5,
) -> list[str]:
    """Trace prerequisites of a failed node to find the root skill gap.

    Returns a list of unmastered prerequisite node IDs, ordered by depth
    (deepest = most fundamental gap first).
    """
    mastery_map = await get_mastery_map(session, student_id)
    visited: set[str] = set()
    gaps: list[tuple[int, str]] = []  # (depth, node_id)

    async def _walk(node_id: str, depth: int) -> None:
        if depth > max_depth or node_id in visited:
            return
        visited.add(node_id)
        prereqs = await get_prerequisites(session, node_id)
        for p in prereqs:
            p_m = mastery_map.get(p, 0.0)
            if p_m < MASTERY_THRESHOLD:
                gaps.append((depth, p))
                await _walk(p, depth + 1)

    await _walk(failed_node_id, 1)

    # Sort: deepest first (most fundamental gap), deduplicate
    seen: set[str] = set()
    ordered: list[str] = []
    for _, nid in sorted(gaps, key=lambda x: -x[0]):
        if nid not in seen:
            seen.add(nid)
            ordered.append(nid)
    return ordered
