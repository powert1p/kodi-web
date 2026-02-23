"""Seed helpers — load knowledge graph and problems from JSON into the DB."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import text

from db.models import Edge, Node, Problem

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


async def seed_graph(session) -> int:
    """Load knowledge graph nodes + edges if the nodes table is empty."""
    result = await session.execute(text("SELECT count(*) FROM nodes"))
    count = result.scalar()
    if count and count > 0:
        return count

    graph_path = _DATA_DIR / "nis_knowledge_graph_v01.json"
    if not graph_path.exists():
        logger.warning("Knowledge graph file not found: %s", graph_path)
        return 0

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes_raw = data["nodes"]

    for n in nodes_raw:
        session.add(Node(
            id=n["id"],
            name_ru=n["name_ru"],
            name_kz=n["name_kz"],
            tag=n.get("tag"),
            difficulty=n.get("difficulty"),
            description=n.get("description"),
        ))
    await session.flush()

    for n in nodes_raw:
        for prereq_id in n.get("prerequisites", []):
            session.add(Edge(from_node=prereq_id, to_node=n["id"]))

    await session.commit()
    logger.info("Seeded %d knowledge graph nodes.", len(nodes_raw))
    return len(nodes_raw)


async def seed_problems(session) -> int:
    """Load problems if the problems table is empty."""
    result = await session.execute(text("SELECT count(*) FROM problems"))
    count = result.scalar()
    if count and count > 0:
        return count

    problems_path = None
    for vname in ("problems_v10.json", "problems_v9.json", "problems_v8.json",
                  "problems_v7.json", "problems_v6.json", "problems_v5.json",
                  "problems_v4.json", "problems_v3.json", "problems_v2.json",
                  "problems.json"):
        candidate = _DATA_DIR / vname
        if candidate.exists():
            problems_path = candidate
            break

    if not problems_path:
        logger.warning("No problems JSON found in %s", _DATA_DIR)
        return 0

    data = json.loads(problems_path.read_text(encoding="utf-8"))
    problems_raw = data["problems"]

    for p in problems_raw:
        session.add(Problem(
            node_id=p["node_id"],
            text_ru=p["text_ru"],
            text_kz=p.get("text_kz"),
            answer=p["answer"],
            answer_type=p.get("answer_type"),
            difficulty=p.get("difficulty"),
            sub_difficulty=p.get("sub_difficulty") or p.get("difficulty"),
            raw_score=p.get("raw_score"),
            image_path=p.get("image_file"),
            image_path_kz=p.get("image_file_kz"),
            source=p.get("source"),
            solution_ru=p.get("solution_ru"),
            solution_kz=p.get("solution_kz"),
        ))

    await session.commit()
    logger.info("Seeded %d problems from %s.", len(problems_raw), problems_path.name)
    return len(problems_raw)
