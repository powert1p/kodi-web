"""Generate self-contained HTML file with interactive knowledge graph.

The HTML template lives in static/graph.html (accordion layout by category);
this module reads it, embeds student-specific JSON data, and returns the
complete HTML as bytes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.diagnostic import compute_outer_fringe
from db.models import Edge, Mastery, Node

from sqlalchemy import select

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "static" / "graph.html"


async def generate_graph_data(
    session: AsyncSession,
    student_id: int,
    student_name: str = "",
    lang: str = "ru",
) -> dict:
    """Build graph + stats data dict for a student.

    Used by both the HTML stats page and the REST API.
    """
    # ── Load graph structure ──
    nodes_result = await session.execute(select(Node))
    all_nodes = list(nodes_result.scalars().all())

    edges_result = await session.execute(select(Edge.from_node, Edge.to_node))
    all_edges = edges_result.all()

    # ── Load mastery data ──
    mastery_result = await session.execute(
        select(Mastery.node_id, Mastery.p_mastery, Mastery.attempts_correct,
               Mastery.attempts_total).where(
            Mastery.student_id == student_id
        )
    )
    mastery_rows = mastery_result.all()
    mastery_map: dict[str, dict] = {}
    for row in mastery_rows:
        mastery_map[row.node_id] = {
            "p_mastery": row.p_mastery,
            "correct": row.attempts_correct,
            "total": row.attempts_total,
        }

    # ── Load tested nodes (directly attempted) ──
    tested_result = await session.execute(
        text("""
            SELECT DISTINCT node_id FROM attempts
            WHERE student_id = :sid AND source IN ('diagnostic', 'exam')
        """),
        {"sid": student_id},
    )
    tested_nodes = {row[0] for row in tested_result.all()}

    # ── Load per-node answer details ──
    answer_details = await _load_answer_details(session, student_id)

    # ── Compute outer fringe ──
    outer_fringe = await compute_outer_fringe(session, student_id)
    fringe_ids = {f["id"] for f in outer_fringe}

    # ── Compute zones ──
    all_node_ids = {n.id for n in all_nodes}
    edge_tuples = [(e[0], e[1]) for e in all_edges]
    zones = _compute_zones(all_node_ids, tested_nodes, edge_tuples, fringe_ids)

    # ── Compute blocked nodes (prereq directly tested & failed) ──
    prereq_map: dict[str, list[str]] = {}
    for from_n, to_n in edge_tuples:
        prereq_map.setdefault(to_n, []).append(from_n)

    failed_tested = set()
    for nid in tested_nodes:
        m = mastery_map.get(nid)
        if m and m["p_mastery"] < 0.2:
            failed_tested.add(nid)

    blocked_ids = set()
    for nid in all_node_ids:
        if nid in tested_nodes:
            continue
        prereqs = prereq_map.get(nid, [])
        if any(p in failed_tested for p in prereqs):
            blocked_ids.add(nid)

    # ── Compute downstream counts (how many nodes depend on each node) ──
    dependents_map: dict[str, set[str]] = {}
    for from_n, to_n in edge_tuples:
        dependents_map.setdefault(from_n, set()).add(to_n)

    def _count_downstream(nid: str, cache: dict[str, int]) -> int:
        if nid in cache:
            return cache[nid]
        direct = dependents_map.get(nid, set())
        total = len(direct)
        for dep in direct:
            total += _count_downstream(dep, cache)
        cache[nid] = total
        return total

    ds_cache: dict[str, int] = {}
    downstream_counts = {nid: _count_downstream(nid, ds_cache) for nid in all_node_ids}

    # ── Build JSON data ──
    nodes_json = []
    for node in all_nodes:
        z = zones.get(node.id, 3)
        m = mastery_map.get(node.id)
        p_mastery = m["p_mastery"] if m else 0.0
        details = answer_details.get(node.id)

        status = _determine_status(node.id, tested_nodes, p_mastery, m is not None)

        node_data: dict = {
            "id": node.id,
            "name_ru": node.name_ru,
            "name_kz": node.name_kz or node.name_ru,
            "tag": node.tag or "other",
            "zone": z,
            "status": status,
            "p_mastery": round(p_mastery, 3) if m else None,
            "is_fringe": node.id in fringe_ids,
            "is_blocked": node.id in blocked_ids,
            "difficulty": node.difficulty or 1,
            "downstream": downstream_counts.get(node.id, 0),
        }

        if details:
            node_data["levels_detail"] = details.get("levels_detail", "")
            node_data["avg_time"] = details.get("avg_time")
            node_data["q_total"] = details.get("q_total", 0)
            node_data["q_correct"] = details.get("q_correct", 0)

        nodes_json.append(node_data)

    edges_json = [
        {"source": e[0], "target": e[1]}
        for e in edge_tuples
    ]

    # ── Stats ──
    mastered = sum(1 for m in mastery_map.values() if m["p_mastery"] >= 0.7)
    in_progress = sum(
        1 for m in mastery_map.values()
        if 0.2 <= m["p_mastery"] < 0.7
    )
    failed = sum(1 for m in mastery_map.values() if m["p_mastery"] < 0.2)
    untested = len(all_nodes) - len(mastery_map)

    # ── Personal stats (problems solved, accuracy, avg time) ──
    personal_result = await session.execute(
        text("""
            SELECT COUNT(DISTINCT problem_id) AS total,
                   COUNT(DISTINCT CASE WHEN is_correct THEN problem_id END) AS correct,
                   AVG(response_time_ms) AS avg_time
            FROM attempts WHERE student_id = :sid AND (source IS NULL OR source NOT IN ('skip', 'report'))
        """),
        {"sid": student_id},
    )
    p_row = personal_result.one()
    personal_solved = int(p_row[0] or 0)
    personal_correct = int(p_row[1] or 0)
    personal_accuracy = round(personal_correct / personal_solved * 100) if personal_solved > 0 else 0
    personal_avg_time = round(float(p_row[2]) / 1000.0, 1) if p_row[2] else 0

    # ── Leaderboard (all registered students) ──
    leaderboard = await _build_leaderboard(session, student_id)

    data = {
        "lang": lang,
        "student_name": student_name,
        "nodes": nodes_json,
        "edges": edges_json,
        "stats": {
            "mastered": mastered,
            "in_progress": in_progress,
            "failed": failed,
            "untested": untested,
            "total": len(all_nodes),
            "tested_directly": len(tested_nodes),
        },
        "personal_stats": {
            "solved": personal_solved,
            "correct": personal_correct,
            "accuracy": personal_accuracy,
            "avg_time_s": personal_avg_time,
            "mastered_count": mastered,
            "total_nodes": len(all_nodes),
        },
        "leaderboard": leaderboard,
    }

    return data


async def generate_graph_html(
    session: AsyncSession,
    student_id: int,
    student_name: str = "",
    lang: str = "ru",
) -> bytes:
    """Generate a self-contained HTML file with embedded graph data.

    Returns UTF-8 encoded HTML bytes ready to send as a Telegram document.
    """
    data = await generate_graph_data(session, student_id, student_name, lang)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    data_script = f"<script>const DATA = {json.dumps(data, ensure_ascii=False)};</script>"
    html = template.replace("<!-- DATA_PLACEHOLDER -->", data_script)
    return html.encode("utf-8")


def _determine_status(
    node_id: str,
    tested_nodes: set[str],
    p_mastery: float,
    has_mastery: bool,
) -> str:
    """Determine display status."""
    if node_id in tested_nodes:
        if not has_mastery:
            return "untested"
        if p_mastery >= 0.7:
            return "mastered"
        if p_mastery >= 0.2:
            return "partial"
        return "failed"
    # Not directly tested but has mastery from propagation
    if has_mastery and p_mastery >= 0.7:
        return "auto_mastered"
    if has_mastery and p_mastery >= 0.2:
        return "auto_partial"
    return "untested"


def _compute_zones(
    all_node_ids: set[str],
    tested_nodes: set[str],
    edges: list[tuple[str, str]],
    fringe_ids: set[str],
) -> dict[str, int]:
    """Assign visibility zones (same logic as graph_viz.py)."""
    zone: dict[str, int] = {}

    for nid in tested_nodes:
        zone[nid] = 1

    neighbors: set[str] = set()
    for from_n, to_n in edges:
        if from_n in tested_nodes or to_n in tested_nodes:
            neighbors.add(from_n)
            neighbors.add(to_n)
    neighbors |= fringe_ids

    for nid in neighbors:
        if nid not in zone:
            zone[nid] = 2

    for nid in all_node_ids:
        if nid not in zone:
            zone[nid] = 3

    return zone


async def _load_answer_details(
    session: AsyncSession, student_id: int,
) -> dict[str, dict]:
    """Load per-node answer details for tooltip display.

    Returns {node_id: {levels_detail, avg_time, q_total, q_correct}}
    """
    # Per-node: unique problems solved + correct
    result = await session.execute(
        text("""
            SELECT
                a.node_id,
                COUNT(DISTINCT a.problem_id) AS q_total,
                COUNT(DISTINCT CASE WHEN a.is_correct THEN a.problem_id END) AS q_correct,
                AVG(a.response_time_ms) AS avg_time
            FROM attempts a
            WHERE a.student_id = :sid
              AND (a.source IS NULL OR a.source NOT IN ('skip', 'report'))
            GROUP BY a.node_id
        """),
        {"sid": student_id},
    )

    details: dict[str, dict] = {}
    for row in result.all():
        details[row[0]] = {
            "levels_detail": "",
            "avg_time": round(float(row[3]) / 1000.0, 1) if row[3] else None,
            "q_total": int(row[1]),
            "q_correct": int(row[2]),
        }

    return details


async def _build_leaderboard(
    session: AsyncSession, current_student_id: int,
) -> list[dict]:
    """Build leaderboard with solved/correct/mastered counts for all students."""
    result = await session.execute(
        text("""
            SELECT
                s.id,
                COALESCE(s.full_name, CONCAT(s.first_name, ' ', s.last_name)) AS name,
                COALESCE(att.solved, 0) AS solved,
                COALESCE(att.correct, 0) AS correct,
                COALESCE(mst.mastered, 0) AS mastered
            FROM students s
            LEFT JOIN (
                SELECT student_id,
                       COUNT(*) AS solved,
                       SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS correct
                FROM attempts
                WHERE (source IS NULL OR source NOT IN ('skip', 'report'))
                GROUP BY student_id
            ) att ON att.student_id = s.id
            LEFT JOIN (
                SELECT student_id,
                       COUNT(*) AS mastered
                FROM mastery
                WHERE p_mastery >= 0.7
                GROUP BY student_id
            ) mst ON mst.student_id = s.id
            WHERE s.registered = true
              AND (COALESCE(att.correct, 0) > 0 OR s.id = :sid)
            ORDER BY att.correct DESC NULLS LAST
        """),
        {"sid": current_student_id},
    )

    leaderboard = []
    for row in result.all():
        sid = row[0]
        name = (row[1] or "").strip() or "Ученик"
        total = int(row[2])
        correct = int(row[3])
        mastered_count = int(row[4])
        accuracy = round(correct / total * 100) if total > 0 else 0

        leaderboard.append({
            "name": name,
            "solved": correct,
            "correct": correct,
            "accuracy": accuracy,
            "mastered": mastered_count,
            "is_current": sid == current_student_id,
        })

    return leaderboard
