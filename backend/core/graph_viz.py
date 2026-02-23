"""Knowledge graph visualization — generates PNG of the student's mastery map.

Uses graphviz to render nodes colored by mastery status, grouped by category.
Supports two modes:
  1. Diagnostic graph (after Phase 1): 3-zone "fog of war" with tested nodes highlighted
  2. Full/focused graph (practice mode): all nodes colored by mastery
"""

from __future__ import annotations

import logging
from typing import Sequence

import graphviz
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.diagnostic import DIAG_MASTERY_THRESHOLD, compute_outer_fringe
from db.models import Edge, Mastery, Node

logger = logging.getLogger(__name__)

# ── Color scheme ─────────────────────────────────────────────

COLORS = {
    "mastered": {"fill": "#4CAF50", "font": "white", "border": "#388E3C"},
    "in_progress": {"fill": "#FFC107", "font": "black", "border": "#FFA000"},
    "failed": {"fill": "#F44336", "font": "white", "border": "#D32F2F"},
    "untested": {"fill": "#E0E0E0", "font": "#666666", "border": "#BDBDBD"},
    "fog": {"fill": "#F5F5F5", "font": "#CCCCCC", "border": "#E0E0E0"},
    "fringe": {"border": "#2196F3", "width": "3"},
}

CLUSTER_LABELS: dict[str, str] = {
    "arithmetic": "Арифметика",
    "fractions": "Дроби",
    "decimals": "Десятичные",
    "divisibility": "Делимость",
    "percent": "Проценты",
    "proportion": "Пропорции",
    "equations": "Уравнения",
    "algebra": "Алгебра",
    "numbers": "Числа",
    "geometry": "Геометрия",
    "conversion": "Ед. измерения",
    "word_problems": "Текст. задачи",
    "logic": "Логика",
    "sets": "Множества",
    "data": "Данные",
}

CLUSTER_COLORS: dict[str, str] = {
    "arithmetic": "#FFF3E0",
    "fractions": "#E3F2FD",
    "decimals": "#E8F5E9",
    "divisibility": "#F3E5F5",
    "percent": "#FFF8E1",
    "proportion": "#E0F2F1",
    "equations": "#FCE4EC",
    "algebra": "#F1F8E9",
    "numbers": "#E8EAF6",
    "geometry": "#FBE9E7",
    "conversion": "#EFEBE9",
    "word_problems": "#E0F7FA",
    "logic": "#F9FBE7",
    "sets": "#EDE7F6",
    "data": "#E1F5FE",
}


# ── Helpers ──────────────────────────────────────────────────


def _get_node_status(
    node_id: str,
    mastery_map: dict[str, float],
    fringe_ids: set[str],
) -> tuple[str, bool]:
    """Determine visual status and fringe membership for a node."""
    p = mastery_map.get(node_id)
    if p is None:
        status = "untested"
    elif p >= 0.7:
        status = "mastered"
    elif p >= 0.2:
        status = "in_progress"
    else:
        status = "failed"
    return status, node_id in fringe_ids


def _truncate(text: str, max_len: int = 22) -> str:
    if len(text) > max_len:
        return text[: max_len - 1] + "\u2026"
    return text


def _compute_zones(
    all_node_ids: set[str],
    tested_nodes: set[str],
    edges: Sequence[tuple[str, str]],
    fringe_ids: set[str],
) -> dict[str, int]:
    """Assign each node to a visibility zone (1, 2, or 3).

    Zone 1: directly tested nodes
    Zone 2: direct prereqs/dependents of tested + fringe nodes
    Zone 3: everything else (fog)
    """
    zone: dict[str, int] = {}

    # Zone 1: tested
    for nid in tested_nodes:
        zone[nid] = 1

    # Zone 2: direct neighbors of tested + fringe
    neighbors: set[str] = set()
    for from_n, to_n in edges:
        if from_n in tested_nodes or to_n in tested_nodes:
            neighbors.add(from_n)
            neighbors.add(to_n)

    # Fringe nodes are always zone 2 (or 1 if tested)
    neighbors |= fringe_ids

    for nid in neighbors:
        if nid not in zone:
            zone[nid] = 2

    # Zone 3: everything else
    for nid in all_node_ids:
        if nid not in zone:
            zone[nid] = 3

    return zone


def _get_diag_node_status(
    node_id: str,
    tested_nodes: set[str],
    mastery_map: dict[str, float],
) -> str:
    """Determine status for diagnostic graph — only tested nodes get colored."""
    if node_id not in tested_nodes:
        return "untested"
    p = mastery_map.get(node_id)
    if p is None:
        return "untested"
    if p >= 0.7:
        return "mastered"
    if p >= 0.2:
        return "in_progress"
    return "failed"


def _category_stats(
    nodes: list,
    tested_nodes: set[str],
    mastery_map: dict[str, float],
) -> dict[str, dict]:
    """Compute per-category stats: tested count, total count, avg mastery %."""
    stats: dict[str, dict] = {}
    for node in nodes:
        tag = node.tag or "other"
        if tag not in stats:
            stats[tag] = {"total": 0, "tested": 0, "mastery_sum": 0.0}
        stats[tag]["total"] += 1
        if node.id in tested_nodes:
            stats[tag]["tested"] += 1
            pm = mastery_map.get(node.id, 0.0)
            stats[tag]["mastery_sum"] += pm
    return stats


# ── Diagnostic graph (Phase 1 — "fog of war") ────────────────


async def generate_diagnostic_graph(
    session: AsyncSession,
    student_id: int,
    tested_nodes: set[str],
) -> bytes:
    """Generate a 3-zone diagnostic PNG: tested nodes bright, neighbors gray, rest fog."""
    # Load all data
    nodes_result = await session.execute(select(Node))
    all_nodes = list(nodes_result.scalars().all())
    all_node_ids = {n.id for n in all_nodes}

    edges_result = await session.execute(select(Edge.from_node, Edge.to_node))
    edges = edges_result.all()
    edge_tuples = [(e[0], e[1]) for e in edges]

    mastery_result = await session.execute(
        select(Mastery.node_id, Mastery.p_mastery).where(
            Mastery.student_id == student_id
        )
    )
    mastery_map = {row.node_id: row.p_mastery for row in mastery_result.all()}

    outer_fringe = await compute_outer_fringe(session, student_id)
    fringe_ids = {f["id"] for f in outer_fringe}

    # Compute zones
    zones = _compute_zones(all_node_ids, tested_nodes, edge_tuples, fringe_ids)

    # Compute category stats
    cat_stats = _category_stats(all_nodes, tested_nodes, mastery_map)

    # Count tested / total for title
    tested_count = len(tested_nodes)
    total_count = len(all_nodes)
    correct = sum(
        1 for nid in tested_nodes
        if mastery_map.get(nid, 0) >= 0.6
    )

    png_bytes = _render_diagnostic_graph(
        all_nodes, edge_tuples, mastery_map, tested_nodes,
        fringe_ids, zones, cat_stats, tested_count, total_count, correct,
    )
    return png_bytes


def _render_diagnostic_graph(
    nodes: list,
    edges: list[tuple[str, str]],
    mastery_map: dict[str, float],
    tested_nodes: set[str],
    fringe_ids: set[str],
    zones: dict[str, int],
    cat_stats: dict[str, dict],
    tested_count: int,
    total_count: int,
    correct_count: int,
) -> bytes:
    """Render the 3-zone diagnostic graph to PNG."""
    dot = graphviz.Digraph(
        format="png",
        engine="dot",
        graph_attr={
            "rankdir": "TB",
            "bgcolor": "white",
            "fontname": "Helvetica",
            "dpi": "96",
            "ranksep": "0.6",
            "nodesep": "0.25",
            "margin": "0.4",
            "size": "40,50!",
            "label": (
                f"Диагностика: {tested_count}/{total_count} тем проверено  "
                f"| Результат: {correct_count}/{tested_count}"
            ),
            "labelloc": "t",
            "labeljust": "c",
            "fontsize": "16",
            "fontcolor": "#333333",
        },
        node_attr={
            "fontname": "Helvetica",
        },
        edge_attr={
            "color": "#CCCCCC",
            "arrowsize": "0.4",
        },
    )

    # ── Legend subgraph ──
    with dot.subgraph(name="cluster_legend") as leg:
        leg.attr(
            label="Обозначения",
            style="rounded",
            color="#CCCCCC",
            fillcolor="white",
            fontname="Helvetica",
            fontsize="10",
            labeljust="l",
            rank="min",
        )
        leg.node(
            "leg_mastered", "✅ Освоено",
            shape="box", style="filled,rounded",
            fillcolor=COLORS["mastered"]["fill"],
            fontcolor="white", fontsize="9", width="0", height="0",
            margin="0.08,0.04",
        )
        leg.node(
            "leg_partial", "⚠️ Частично",
            shape="box", style="filled,rounded",
            fillcolor=COLORS["in_progress"]["fill"],
            fontcolor="black", fontsize="9", width="0", height="0",
            margin="0.08,0.04",
        )
        leg.node(
            "leg_failed", "❌ Не освоено",
            shape="box", style="filled,rounded",
            fillcolor=COLORS["failed"]["fill"],
            fontcolor="white", fontsize="9", width="0", height="0",
            margin="0.08,0.04",
        )
        leg.node(
            "leg_untested", "Не проверено",
            shape="box", style="filled,rounded",
            fillcolor=COLORS["untested"]["fill"],
            fontcolor=COLORS["untested"]["font"], fontsize="9",
            width="0", height="0", margin="0.08,0.04",
        )
        leg.node(
            "leg_fringe", "🔵 Учи дальше",
            shape="box", style="filled,rounded",
            fillcolor="white",
            color=COLORS["fringe"]["border"],
            penwidth=COLORS["fringe"]["width"],
            fontcolor="#2196F3", fontsize="9",
            width="0", height="0", margin="0.08,0.04",
        )
        leg.edge("leg_mastered", "leg_partial", style="invis")
        leg.edge("leg_partial", "leg_failed", style="invis")
        leg.edge("leg_failed", "leg_untested", style="invis")
        leg.edge("leg_untested", "leg_fringe", style="invis")

    # ── Group nodes by tag ──
    nodes_by_tag: dict[str, list] = {}
    for node in nodes:
        tag = node.tag or "other"
        nodes_by_tag.setdefault(tag, []).append(node)

    # ── Create category clusters ──
    for tag, tag_nodes in nodes_by_tag.items():
        cluster_name = f"cluster_{tag}"
        base_label = CLUSTER_LABELS.get(tag, tag.capitalize())
        bg_color = CLUSTER_COLORS.get(tag, "#F5F5F5")

        cs = cat_stats.get(tag, {"total": 0, "tested": 0, "mastery_sum": 0.0})
        if cs["tested"] > 0:
            avg_pct = int(cs["mastery_sum"] / cs["tested"] * 100)
            cluster_label = f"{base_label} ({avg_pct}%) — {cs['tested']}/{cs['total']}"
        else:
            cluster_label = f"{base_label} — не проверено"

        with dot.subgraph(name=cluster_name) as sub:
            sub.attr(
                label=cluster_label,
                style="filled,rounded",
                color="#CCCCCC",
                fillcolor=bg_color,
                fontname="Helvetica",
                fontsize="10",
                labeljust="l",
            )

            for node in tag_nodes:
                z = zones.get(node.id, 3)

                if z == 1:
                    # Zone 1: directly tested — bright, large
                    status = _get_diag_node_status(
                        node.id, tested_nodes, mastery_map
                    )
                    colors = COLORS[status]
                    pm = mastery_map.get(node.id, 0.0)
                    pct = int(pm * 100)
                    label_text = f"{_truncate(node.name_ru, 20)}\n{pct}%"

                    node_attrs: dict[str, str] = {
                        "shape": "box",
                        "style": "filled,rounded,bold",
                        "fillcolor": colors["fill"],
                        "fontcolor": colors["font"],
                        "color": colors["border"],
                        "fontsize": "11",
                        "width": "0",
                        "height": "0",
                        "margin": "0.14,0.08",
                        "penwidth": "2",
                    }
                    sub.node(node.id, label=label_text, **node_attrs)

                elif z == 2:
                    # Zone 2: connected neighbor — medium, gray, visible
                    is_fringe = node.id in fringe_ids
                    label_text = _truncate(node.name_ru, 18)

                    node_attrs = {
                        "shape": "box",
                        "style": "filled,rounded",
                        "fillcolor": COLORS["untested"]["fill"],
                        "fontcolor": COLORS["untested"]["font"],
                        "color": COLORS["untested"]["border"],
                        "fontsize": "9",
                        "width": "0",
                        "height": "0",
                        "margin": "0.10,0.05",
                    }

                    if is_fringe:
                        node_attrs["color"] = COLORS["fringe"]["border"]
                        node_attrs["penwidth"] = COLORS["fringe"]["width"]
                        label_text = f"→ {label_text}"

                    sub.node(node.id, label=label_text, **node_attrs)

                else:
                    # Zone 3: fog — tiny dot
                    sub.node(
                        node.id,
                        label="",
                        shape="circle",
                        style="filled",
                        fillcolor=COLORS["fog"]["fill"],
                        color=COLORS["fog"]["border"],
                        width="0.15",
                        height="0.15",
                        fixedsize="true",
                    )

    # ── Add edges (skip zone3→zone3) ──
    for from_n, to_n in edges:
        z_from = zones.get(from_n, 3)
        z_to = zones.get(to_n, 3)

        if z_from == 3 and z_to == 3:
            continue

        edge_attrs: dict[str, str] = {}
        if z_from <= 1 and z_to <= 1:
            edge_attrs["color"] = "#888888"
            edge_attrs["penwidth"] = "1.5"
        elif z_from <= 2 and z_to <= 2:
            edge_attrs["color"] = "#AAAAAA"
        else:
            edge_attrs["color"] = "#DDDDDD"
            edge_attrs["style"] = "dashed"

        dot.edge(from_n, to_n, **edge_attrs)

    return dot.pipe()


# ── Full graph (practice mode) ───────────────────────────────


async def generate_graph_image(
    session: AsyncSession, student_id: int
) -> bytes:
    """Generate full knowledge graph PNG colored by mastery."""
    nodes_result = await session.execute(select(Node))
    all_nodes = list(nodes_result.scalars().all())

    edges_result = await session.execute(select(Edge.from_node, Edge.to_node))
    edges = edges_result.all()

    mastery_result = await session.execute(
        select(Mastery.node_id, Mastery.p_mastery).where(
            Mastery.student_id == student_id
        )
    )
    mastery_map = {row.node_id: row.p_mastery for row in mastery_result.all()}

    outer_fringe = await compute_outer_fringe(session, student_id)
    fringe_ids = {f["id"] for f in outer_fringe}

    png_bytes = _render_full_graph(all_nodes, edges, mastery_map, fringe_ids)
    return png_bytes


async def generate_focused_graph(
    session: AsyncSession, student_id: int
) -> bytes:
    """Generate focused graph: only mastered + failed + fringe + neighbors."""
    mastery_result = await session.execute(
        select(Mastery.node_id, Mastery.p_mastery).where(
            Mastery.student_id == student_id
        )
    )
    mastery_map = {row.node_id: row.p_mastery for row in mastery_result.all()}

    outer_fringe = await compute_outer_fringe(session, student_id)
    fringe_ids = {f["id"] for f in outer_fringe}

    visible = set(mastery_map.keys()) | fringe_ids

    for fid in fringe_ids:
        prereqs = await session.execute(
            select(Edge.from_node).where(Edge.to_node == fid)
        )
        for (p,) in prereqs.all():
            visible.add(p)

    for nid, pm in mastery_map.items():
        if pm >= 0.8:
            deps = await session.execute(
                select(Edge.to_node).where(Edge.from_node == nid)
            )
            for (d,) in deps.all():
                visible.add(d)

    nodes_result = await session.execute(
        select(Node).where(Node.id.in_(visible))
    )
    visible_nodes = list(nodes_result.scalars().all())

    edges_result = await session.execute(
        select(Edge.from_node, Edge.to_node).where(
            Edge.from_node.in_(visible),
            Edge.to_node.in_(visible),
        )
    )
    visible_edges = edges_result.all()

    png_bytes = _render_full_graph(
        visible_nodes, visible_edges, mastery_map, fringe_ids
    )
    return png_bytes


async def get_graph_image(
    session: AsyncSession, student_id: int
) -> bytes:
    """Choose full or focused graph based on mastery data."""
    result = await session.execute(
        text("SELECT COUNT(*) FROM mastery WHERE student_id = :sid"),
        {"sid": student_id},
    )
    total_mastery = result.scalar_one()

    if total_mastery == 0:
        return await generate_graph_image(session, student_id)

    mastered_result = await session.execute(
        text(
            "SELECT COUNT(*) FROM mastery "
            "WHERE student_id = :sid AND p_mastery >= 0.7"
        ),
        {"sid": student_id},
    )
    mastered_count = mastered_result.scalar_one()

    if mastered_count >= 25:
        return await generate_graph_image(session, student_id)
    else:
        return await generate_focused_graph(session, student_id)


async def get_graph_stats(
    session: AsyncSession, student_id: int
) -> dict:
    """Get mastery stats for graph caption."""
    result = await session.execute(
        text("""
            SELECT
                COUNT(*) FILTER (WHERE p_mastery >= 0.7) AS mastered,
                COUNT(*) FILTER (WHERE p_mastery < 0.7 AND p_mastery >= 0.2) AS in_progress,
                COUNT(*) FILTER (WHERE p_mastery < 0.2) AS failed
            FROM mastery WHERE student_id = :sid
        """),
        {"sid": student_id},
    )
    row = result.one()
    total_nodes = (await session.execute(
        text("SELECT COUNT(*) FROM nodes")
    )).scalar_one()

    return {
        "mastered": row[0],
        "in_progress": row[1],
        "failed": row[2],
        "untested": total_nodes - row[0] - row[1] - row[2],
        "total": total_nodes,
    }


# ── Full-graph rendering (practice mode) ─────────────────────


def _render_full_graph(
    nodes: list,
    edges: list,
    mastery_map: dict[str, float],
    fringe_ids: set[str],
) -> bytes:
    """Render a full graphviz graph to PNG bytes."""
    node_count = len(nodes)
    if node_count > 80:
        dpi, fontsize, ranksep, nodesep = "72", "8", "0.5", "0.2"
    elif node_count > 40:
        dpi, fontsize, ranksep, nodesep = "96", "9", "0.6", "0.25"
    else:
        dpi, fontsize, ranksep, nodesep = "120", "10", "0.7", "0.3"

    dot = graphviz.Digraph(
        format="png",
        engine="dot",
        graph_attr={
            "rankdir": "TB",
            "bgcolor": "white",
            "fontname": "Helvetica",
            "dpi": dpi,
            "ranksep": ranksep,
            "nodesep": nodesep,
            "margin": "0.3",
            "size": "40,50!",
        },
        node_attr={
            "shape": "box",
            "style": "filled,rounded",
            "fontname": "Helvetica",
            "fontsize": fontsize,
            "width": "0",
            "height": "0",
            "margin": "0.12,0.06",
        },
        edge_attr={
            "color": "#999999",
            "arrowsize": "0.5",
        },
    )

    nodes_by_tag: dict[str, list] = {}
    for node in nodes:
        tag = node.tag or "other"
        nodes_by_tag.setdefault(tag, []).append(node)

    for tag, tag_nodes in nodes_by_tag.items():
        cluster_name = f"cluster_{tag}"
        label = CLUSTER_LABELS.get(tag, tag.capitalize())
        bg_color = CLUSTER_COLORS.get(tag, "#F5F5F5")

        with dot.subgraph(name=cluster_name) as sub:
            sub.attr(
                label=label,
                style="filled,rounded",
                color="#CCCCCC",
                fillcolor=bg_color,
                fontname="Helvetica",
                fontsize="11",
                labeljust="l",
            )

            for node in tag_nodes:
                status, is_fringe = _get_node_status(
                    node.id, mastery_map, fringe_ids
                )
                colors = COLORS[status]
                label_text = _truncate(node.name_ru)

                node_attrs = {
                    "fillcolor": colors["fill"],
                    "fontcolor": colors["font"],
                    "color": colors["border"],
                }

                if is_fringe:
                    node_attrs["color"] = COLORS["fringe"]["border"]
                    node_attrs["penwidth"] = COLORS["fringe"]["width"]

                sub.node(node.id, label=label_text, **node_attrs)

    for edge in edges:
        from_n = edge[0] if isinstance(edge, tuple) else edge.from_node
        to_n = edge[1] if isinstance(edge, tuple) else edge.to_node
        dot.edge(from_n, to_n)

    return dot.pipe()
