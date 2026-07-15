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
PROBLEMS_VERSION = "v10.2"  # v10.2: исправлены 5 ошибочных ответов/решений


async def seed_graph(session) -> int:
    """Недеструктивно долить отсутствующие узлы и рёбра knowledge graph.

    Existing-узлы не обновляются: в рабочей БД их метаданные могли быть
    отредактированы вручную. Это делает startup безопасным и для пустой, и для
    частично засеянной БД.
    """
    graph_path = _DATA_DIR / "nis_knowledge_graph_v01.json"
    if not graph_path.exists():
        logger.warning("Knowledge graph file not found: %s", graph_path)
        return 0

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes_raw = data["nodes"]
    existing_node_ids = set(
        (await session.execute(text("SELECT id FROM nodes"))).scalars().all()
    )

    for n in nodes_raw:
        if n["id"] in existing_node_ids:
            continue
        session.add(Node(
            id=n["id"],
            name_ru=n["name_ru"],
            name_kz=n["name_kz"],
            tag=n.get("tag"),
            difficulty=n.get("difficulty"),
            description=n.get("description"),
            theory_ru=n.get("theory_ru"),  # может отсутствовать в graph-JSON → NULL
        ))
    await session.flush()

    existing_edges = set(
        (await session.execute(text("SELECT from_node, to_node FROM edges"))).all()
    )
    added_edges = 0
    for n in nodes_raw:
        for prereq_id in n.get("prerequisites", []):
            if (prereq_id, n["id"]) in existing_edges:
                continue
            session.add(Edge(from_node=prereq_id, to_node=n["id"]))
            added_edges += 1

    await session.commit()
    count = (await session.execute(text("SELECT count(*) FROM nodes"))).scalar() or 0
    added_nodes = len({n["id"] for n in nodes_raw} - existing_node_ids)
    if added_nodes or added_edges:
        logger.info(
            "Knowledge graph repaired: added %d nodes and %d edges (%d nodes total).",
            added_nodes,
            added_edges,
            count,
        )
    return count


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

        # Версия устарела — обновить только по stable content_idx.
        return await sync_canonical_problems(session)

    # Таблица пустая — вставить все
    return await _insert_all_problems(session)


async def backfill_problem_content_idx(session) -> int:
    """Недеструктивно привязать existing-БД к canonical problem index.

    Autoincrement ``problems.id`` нестабилен между базами, поэтому backfill идёт
    по уникальному natural key ``(node_id, text_ru)``. Уже заполненные значения
    не перезаписываются; ручные задачи, которых нет в canonical JSON, остаются NULL.
    """
    problems_path = _find_problems_path()
    if not problems_path:
        logger.warning("No problems JSON found in %s", _DATA_DIR)
        return 0

    problems_raw = json.loads(problems_path.read_text(encoding="utf-8"))["problems"]
    identities = [
        {
            "content_idx": content_idx,
            "node_id": problem["node_id"],
            "text_ru": problem["text_ru"],
        }
        for content_idx, problem in enumerate(problems_raw)
    ]
    result = await session.execute(
        text(
            "UPDATE problems SET content_idx = :content_idx "
            "WHERE content_idx IS NULL "
            "  AND node_id = :node_id "
            "  AND text_ru = :text_ru"
        ),
        identities,
    )
    await session.commit()
    # asyncpg executemany может вернуть -1 («неизвестно»), это не число строк.
    updated = max(result.rowcount or 0, 0)
    if updated:
        logger.info("Problem identity: backfilled content_idx for %d rows.", updated)
    return updated


async def sync_canonical_problems(session) -> int:
    """Идемпотентно синхронизировать canonical-банк по ``content_idx``.

    Порядок ``problems.id`` между базами нестабилен. Поэтому existing-строки
    перед этим проходят ``backfill_problem_content_idx``, а upsert никогда
    не сопоставляет задачи по autoincrement id и не трогает ручные NULL-строки.
    """
    problems_path = _find_problems_path()
    if not problems_path:
        logger.warning("No problems JSON found in %s", _DATA_DIR)
        return 0

    problems_raw = json.loads(problems_path.read_text(encoding="utf-8"))["problems"]
    rows = [
        {
            "content_idx": content_idx,
            "node_id": problem["node_id"],
            "text_ru": problem["text_ru"],
            "text_kz": problem.get("text_kz"),
            "answer": problem["answer"],
            "answer_type": problem.get("answer_type"),
            "difficulty": problem.get("difficulty"),
            "sub_difficulty": problem.get("sub_difficulty") or problem.get("difficulty"),
            "raw_score": problem.get("raw_score"),
            "image_path": problem.get("image_file"),
            "image_path_kz": problem.get("image_file_kz"),
            "source": problem.get("source"),
            "solution_ru": problem.get("solution_ru"),
            "solution_kz": problem.get("solution_kz"),
        }
        for content_idx, problem in enumerate(problems_raw)
    ]
    await session.execute(
        text(
            """
            INSERT INTO problems (
                content_idx, node_id, text_ru, text_kz, answer, answer_type,
                difficulty, sub_difficulty, raw_score, image_path, image_path_kz,
                source, solution_ru, solution_kz
            ) VALUES (
                :content_idx, :node_id, :text_ru, :text_kz, :answer, :answer_type,
                :difficulty, :sub_difficulty, :raw_score, :image_path, :image_path_kz,
                :source, :solution_ru, :solution_kz
            )
            ON CONFLICT (content_idx) DO UPDATE SET
                node_id = EXCLUDED.node_id,
                text_ru = EXCLUDED.text_ru,
                text_kz = EXCLUDED.text_kz,
                answer = EXCLUDED.answer,
                answer_type = EXCLUDED.answer_type,
                difficulty = EXCLUDED.difficulty,
                sub_difficulty = EXCLUDED.sub_difficulty,
                raw_score = EXCLUDED.raw_score,
                image_path = EXCLUDED.image_path,
                image_path_kz = EXCLUDED.image_path_kz,
                source = EXCLUDED.source,
                solution_ru = EXCLUDED.solution_ru,
                solution_kz = EXCLUDED.solution_kz
            """
        ),
        rows,
    )
    await session.execute(
        text(
            "INSERT INTO settings (key, value) VALUES ('problems_version', :v) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"v": PROBLEMS_VERSION},
    )
    await session.commit()
    logger.info(
        "Synced %d canonical problems by content_idx to version %s.",
        len(rows),
        PROBLEMS_VERSION,
    )
    return len(rows)


async def _insert_all_problems(session) -> int:
    """Вставить все задачи из JSON (при пустой таблице)."""
    problems_path = _find_problems_path()
    if not problems_path:
        logger.warning("No problems JSON found in %s", _DATA_DIR)
        return 0

    data = json.loads(problems_path.read_text(encoding="utf-8"))
    problems_raw = data["problems"]

    for content_idx, p in enumerate(problems_raw):
        session.add(Problem(
            content_idx=content_idx,
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


async def seed_topics(session) -> int:
    """Идемпотентно загрузить темы/рёбра и привязать узлы к темам.

    Безопасно на уже засеянной БД: upsert тем, рёбра ON CONFLICT DO NOTHING,
    node.topic_id через UPDATE. Деструктива нет. Возвращает число тем.
    """
    topics_path = _DATA_DIR / "cc_topics_v01.json"
    if not topics_path.exists():
        logger.warning("cc_topics file not found: %s", topics_path)
        return 0

    d = json.loads(topics_path.read_text(encoding="utf-8"))

    for t in d["topics"]:
        await session.execute(
            text("""
                INSERT INTO topics (id, strand, grade, order_idx, name_ru, name_kz)
                VALUES (:id, :strand, :grade, :order_idx, :name_ru, :name_kz)
                ON CONFLICT (id) DO UPDATE SET
                    strand = EXCLUDED.strand, grade = EXCLUDED.grade,
                    order_idx = EXCLUDED.order_idx,
                    name_ru = EXCLUDED.name_ru, name_kz = EXCLUDED.name_kz
            """),
            {"id": t["id"], "strand": t["strand"], "grade": t.get("grade"),
             "order_idx": t.get("order", 0), "name_ru": t["name_ru"], "name_kz": t["name_kz"]},
        )

    for a, b in d["topic_edges"]:
        await session.execute(
            text("INSERT INTO topic_edges (from_topic, to_topic) VALUES (:a, :b) "
                 "ON CONFLICT (from_topic, to_topic) DO NOTHING"),
            {"a": a, "b": b},
        )

    for node_id, topic_id in d["node_topic"].items():
        await session.execute(
            text("UPDATE nodes SET topic_id = :tid WHERE id = :nid"),
            {"tid": topic_id, "nid": node_id},
        )

    await session.commit()
    logger.info("Seeded %d topics, %d topic edges.", len(d["topics"]), len(d["topic_edges"]))
    return len(d["topics"])


async def backfill_theory(session) -> int:
    """Идемпотентно долить карточки теории (nodes.theory_ru) из graph-JSON.

    Прод-путь: existing-БД не проходит seed_graph, а карточки нужны — берём
    theory_ru из запечённого в образ nis_knowledge_graph_v01.json и заполняем
    ТОЛЬКО пустые (IS NULL): значения, залитые scripts/seed_theory.py поверх,
    не перетираются. Возвращает число долитых узлов.
    """
    graph_path = _DATA_DIR / "nis_knowledge_graph_v01.json"
    if not graph_path.exists():
        logger.warning("graph JSON not found: %s", graph_path)
        return 0

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    filled = 0
    for n in data["nodes"]:
        theory = n.get("theory_ru")
        if not theory:
            continue
        res = await session.execute(
            text("UPDATE nodes SET theory_ru = :t WHERE id = :nid AND theory_ru IS NULL"),
            {"t": theory, "nid": n["id"]},
        )
        filled += res.rowcount or 0
    await session.commit()
    if filled:
        logger.info("Теория узлов: долито %d карточек (theory_ru IS NULL).", filled)
    return filled
