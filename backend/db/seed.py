"""Seed helpers — load knowledge graph and problems from JSON into the DB."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import text

from db.models import Edge, Node, Problem

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Версия данных задач — увеличить при каждом обновлении problems JSON
PROBLEMS_VERSION = "v10.1"  # v10.1: добавлены подсказки единиц, фикс ответа WP05


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


def _find_problems_path() -> Path | None:
    """Найти файл задач (от новой к старой версии)."""
    for vname in ("problems_v10.json", "problems_v9.json", "problems_v8.json",
                  "problems_v7.json", "problems_v6.json", "problems_v5.json",
                  "problems_v4.json", "problems_v3.json", "problems_v2.json",
                  "problems.json"):
        candidate = _DATA_DIR / vname
        if candidate.exists():
            return candidate
    return None


async def seed_problems(session) -> int:
    """Load problems if empty, or sync if version changed."""
    result = await session.execute(text("SELECT count(*) FROM problems"))
    count = result.scalar() or 0

    if count > 0:
        # Проверить версию — если совпадает, пропустить
        ver_result = await session.execute(
            text("SELECT value FROM settings WHERE key = 'problems_version'")
        )
        ver_row = ver_result.first()
        if ver_row and ver_row[0] == PROBLEMS_VERSION:
            return count

        # Версия устарела — обновить существующие записи
        return await _sync_problems(session)

    # Таблица пустая — вставить все
    return await _insert_all_problems(session)


async def _insert_all_problems(session) -> int:
    """Вставить все задачи из JSON (при пустой таблице)."""
    problems_path = _find_problems_path()
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

    # Сохранить версию
    await session.execute(
        text("INSERT INTO settings (key, value) VALUES ('problems_version', :v) "
             "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"),
        {"v": PROBLEMS_VERSION},
    )
    await session.commit()
    logger.info("Seeded %d problems from %s (version %s).",
                len(problems_raw), problems_path.name, PROBLEMS_VERSION)
    return len(problems_raw)


async def _sync_problems(session) -> int:
    """Обновить существующие задачи из JSON (по порядку id)."""
    problems_path = _find_problems_path()
    if not problems_path:
        logger.warning("No problems JSON found in %s", _DATA_DIR)
        return 0

    data = json.loads(problems_path.read_text(encoding="utf-8"))
    problems_raw = data["problems"]

    # Получить все id в порядке вставки
    result = await session.execute(text("SELECT id FROM problems ORDER BY id"))
    db_ids = [row[0] for row in result.fetchall()]

    updated = 0
    for i, p in enumerate(problems_raw):
        if i >= len(db_ids):
            # Новая задача — вставить
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
            updated += 1
            continue

        # Обновить существующую запись
        db_id = db_ids[i]
        await session.execute(
            text("""
                UPDATE problems SET
                    text_ru = :text_ru,
                    text_kz = :text_kz,
                    answer = :answer,
                    answer_type = :answer_type,
                    difficulty = :difficulty,
                    sub_difficulty = :sub_difficulty,
                    raw_score = :raw_score,
                    image_path = :image_path,
                    image_path_kz = :image_path_kz,
                    source = :source,
                    solution_ru = :solution_ru,
                    solution_kz = :solution_kz
                WHERE id = :id
            """),
            {
                "id": db_id,
                "text_ru": p["text_ru"],
                "text_kz": p.get("text_kz"),
                "answer": p["answer"],
                "answer_type": p.get("answer_type"),
                "difficulty": p.get("difficulty"),
                "sub_difficulty": p.get("sub_difficulty") or p.get("difficulty"),
                "raw_score": p.get("raw_score"),
                "image_path": p.get("image_file"),
                "image_path_kz": p.get("image_file_kz"),
                "source": p.get("source"),
                "solution_ru": p.get("solution_ru"),
                "solution_kz": p.get("solution_kz"),
            },
        )
        updated += 1

    # Сохранить версию
    await session.execute(
        text("INSERT INTO settings (key, value) VALUES ('problems_version', :v) "
             "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"),
        {"v": PROBLEMS_VERSION},
    )
    await session.commit()
    logger.info("Synced %d problems to version %s.", updated, PROBLEMS_VERSION)
    return updated
