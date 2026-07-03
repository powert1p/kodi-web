"""Миграция existing-БД на граф v02 (вердикт docs/specs/2026-07-03-graph-v02-verdict.md).

JSON-источники УЖЕ обновлены (коммиты b32c490, cd71acb): 114 узлов, 181 ребро,
36 тем, задачи и банк декомпозиций перепривязаны. Штатный `seed.py` это НЕ
подхватит на existing-БД: `seed_graph`/`seed_problems` — short-circuit по
row-count/версии, `_sync_problems` не трогает `node_id` (см. concern #3 в
`.superpowers/sdd/graph-v02-apply-report.md`). Этот скрипт — ручная
догоняющая миграция для уже засеянной (existing) БД.

ОДНА транзакция: любой упавший assert = полный rollback, в БД не остаётся
частичных изменений.

Запуск (dev):
    cd backend
    DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/nismathbot \
        ../.venv/bin/python scripts/migrate_graph_v02_db.py

Идемпотентность: guard в начале — если в nodes нет NM01, считаем что миграция
уже применена (DELETE_NODES удалены), выходим с кодом 0 без изменений.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import sys
from pathlib import Path

# Добавляем backend/ в sys.path — скрипт запускается из backend/ (как seed_demo.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from db.base import async_session

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_GRAPH_PATH = _DATA_DIR / "nis_knowledge_graph_v01.json"
_TOPICS_PATH = _DATA_DIR / "cc_topics_v01.json"
_PROBLEMS_PATH = _DATA_DIR / "problems_v10.json"
_DECOMP_PATH = _DATA_DIR / "full_decomposition_v1.json"

# Узлы, удалённые вердиктом v02 (изолированная дубль-ветка без exam_questions).
DELETE_NODES = ("NM01", "NM02", "NM03", "ALG01")
# Единственно допустимые цели перепривязки задач/декомпозиций с этих узлов.
REMAP_TARGETS = ("RN01", "MD01", "AL01")

EXPECTED_NODE_COUNT = 114
EXPECTED_EDGE_COUNT = 181
EXPECTED_PROBLEMS_TOTAL = 2525
EXPECTED_PROBLEMS_REMAP = 73
EXPECTED_DECOMP_REMAP = 73
SAMPLE_SIZE = 20


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── §1. Guard идемпотентности ────────────────────────────────────────────────


async def _already_migrated(session) -> bool:
    result = await session.execute(text("SELECT 1 FROM nodes WHERE id = 'NM01'"))
    return result.first() is None


# ── §2. problems.node_id — позиционное выравнивание ─────────────────────────


async def migrate_problems(session, problems_json: list[dict]) -> int:
    """Перепривязать problems.node_id по позиции ORDER BY id ↔ порядок в JSON.

    Паттерн — как _sync_problems в db/seed.py. Перед UPDATE — двойная проверка
    согласованности (count + сверка answer на случайных позициях), иначе abort
    (никаких UPDATE не применяем, транзакция целиком откатится).
    """
    db_count = (await session.execute(text("SELECT count(*) FROM problems"))).scalar() or 0
    json_count = len(problems_json)
    if db_count != json_count or json_count != EXPECTED_PROBLEMS_TOTAL:
        raise AssertionError(
            f"problems: несогласованность БД/JSON — в БД {db_count} строк, в JSON "
            f"{json_count}, ожидалось {EXPECTED_PROBLEMS_TOTAL} с обеих сторон. "
            "Позиционное выравнивание ORDER BY id ↔ JSON НЕБЕЗОПАСНО при "
            "расхождении количества — abort без изменений (см. SEED-1 в "
            "docs/data-state.md)."
        )

    rows = (
        await session.execute(text("SELECT id, node_id, answer FROM problems ORDER BY id"))
    ).fetchall()
    assert len(rows) == json_count, f"fetch дал {len(rows)} строк, ожидалось {json_count}"

    # Сверка на случайных позициях: answer в БД должен совпасть с answer в JSON
    # на той же позиции — иначе порядок разъехался (reorder в JSON, см. SEED-1).
    rng = random.Random(42)
    sample_positions = rng.sample(range(json_count), SAMPLE_SIZE)
    mismatches = []
    for pos in sample_positions:
        db_answer = str(rows[pos][2])
        json_answer = str(problems_json[pos].get("answer"))
        if db_answer != json_answer:
            mismatches.append((pos, db_answer, json_answer))
    if mismatches:
        raise AssertionError(
            f"problems: позиционное расхождение answer на {len(mismatches)}/"
            f"{SAMPLE_SIZE} случайных позициях — abort. Примеры: {mismatches[:5]}"
        )

    # Собираем диффы node_id по позиции.
    diffs: list[tuple[int, str, str]] = []  # (db_id, old_node_id, new_node_id)
    for pos, row in enumerate(rows):
        db_id, old_node_id, _answer = row
        new_node_id = problems_json[pos]["node_id"]
        if old_node_id != new_node_id:
            diffs.append((db_id, old_node_id, new_node_id))

    bad = [
        (old, new)
        for _db_id, old, new in diffs
        if old not in DELETE_NODES or new not in REMAP_TARGETS
    ]
    assert not bad, f"problems: неожиданные диффы node_id (не remap удалённых узлов): {bad[:10]}"
    assert len(diffs) == EXPECTED_PROBLEMS_REMAP, (
        f"problems: ожидалось {EXPECTED_PROBLEMS_REMAP} перепривязок, получено {len(diffs)}"
    )

    for db_id, _old, new in diffs:
        await session.execute(
            text("UPDATE problems SET node_id = :new WHERE id = :id"),
            {"new": new, "id": db_id},
        )

    return len(diffs)


# ── §3. decomposition_problems.node_id — прямой PK idx ──────────────────────


async def migrate_decomposition(session, decomp_json: list[dict]) -> int:
    rows = (
        await session.execute(text("SELECT idx, node_id FROM decomposition_problems"))
    ).fetchall()
    db_node_by_idx = {idx: node_id for idx, node_id in rows}

    diffs: list[tuple[int, str, str]] = []  # (idx, old_node_id, new_node_id)
    for rec in decomp_json:
        idx = rec["idx"]
        new_node_id = rec["node_id"]
        old_node_id = db_node_by_idx.get(idx)
        assert old_node_id is not None, f"decomposition_problems: idx={idx} отсутствует в БД"
        if old_node_id != new_node_id:
            diffs.append((idx, old_node_id, new_node_id))

    bad = [
        (old, new)
        for _idx, old, new in diffs
        if old not in DELETE_NODES or new not in REMAP_TARGETS
    ]
    assert not bad, f"decomposition: неожиданные диффы node_id: {bad[:10]}"
    assert len(diffs) == EXPECTED_DECOMP_REMAP, (
        f"decomposition: ожидалось {EXPECTED_DECOMP_REMAP} перепривязок, получено {len(diffs)}"
    )

    for idx, _old, new in diffs:
        await session.execute(
            text("UPDATE decomposition_problems SET node_id = :new WHERE idx = :idx"),
            {"new": new, "idx": idx},
        )

    return len(diffs)


# ── §4. attempts / error_captures / recurring_errors ─────────────────────────


async def migrate_dependent_tables(session) -> dict[str, int]:
    """Обновить хвостовые таблицы, ссылающиеся на удалённые узлы.

    attempts/error_captures — через JOIN на problems (problems.node_id уже
    новый на этот момент, т.к. вызывается ПОСЛЕ migrate_problems).
    recurring_errors — прямого problem_id нет, маппинг по правилу задачи:
    NM01/NM02/NM03 → RN01, ALG01 → AL01 (упрощённо, без текстового разбора —
    в этой таблице нет текста задачи для эвристики "есть модуль").
    """
    counters: dict[str, int] = {}

    result = await session.execute(
        text(
            """
            UPDATE attempts a
            SET node_id = p.node_id
            FROM problems p
            WHERE a.problem_id = p.id
              AND a.node_id IN ('NM01', 'NM02', 'NM03', 'ALG01')
            """
        )
    )
    counters["attempts"] = result.rowcount or 0

    result = await session.execute(
        text(
            """
            UPDATE error_captures e
            SET node_id = p.node_id
            FROM problems p
            WHERE e.problem_id = p.id
              AND e.node_id IN ('NM01', 'NM02', 'NM03', 'ALG01')
            """
        )
    )
    counters["error_captures"] = result.rowcount or 0

    result = await session.execute(
        text(
            "UPDATE recurring_errors SET node_id = 'RN01' "
            "WHERE node_id IN ('NM01', 'NM02', 'NM03')"
        )
    )
    counters["recurring_errors_nm"] = result.rowcount or 0

    result = await session.execute(
        text("UPDATE recurring_errors SET node_id = 'AL01' WHERE node_id = 'ALG01'")
    )
    counters["recurring_errors_alg01"] = result.rowcount or 0

    return counters


# ── §5+§6. nodes + edges ─────────────────────────────────────────────────────


async def migrate_nodes_and_edges(session, graph_json: dict) -> dict[str, int]:
    """Обновить поля 114 оставшихся узлов, заменить edges, удалить 4 старых узла.

    Порядок ВНУТРИ шага отличается от буквального порядка задания (5 затем 6)
    по FK-безопасности: edges.from_node/to_node → nodes.id БЕЗ ondelete
    (default NO ACTION) — удалить узлы NM*/ALG01 при живых edges на них
    невозможно. Поэтому: (1) UPDATE полей узлов, (2) DELETE FROM edges
    (полный wipe — старые рёбра всё равно заменяются), (3) DELETE mastery +
    DELETE nodes для 4 старых узлов, (4) INSERT 181 нового ребра. Конечное
    состояние идентично буквальному порядку задания, DELETE/DELETE не падает.
    """
    nodes_raw = graph_json["nodes"]
    assert len(nodes_raw) == EXPECTED_NODE_COUNT, (
        f"graph JSON: {len(nodes_raw)} узлов, ожидалось {EXPECTED_NODE_COUNT}"
    )

    # (1) UPDATE полей всех 114 узлов (name_ru/name_kz/difficulty/tag; FR13 difficulty=2 — уже в JSON).
    for n in nodes_raw:
        await session.execute(
            text(
                """
                UPDATE nodes SET
                    name_ru = :name_ru,
                    name_kz = :name_kz,
                    difficulty = :difficulty,
                    tag = :tag
                WHERE id = :id
                """
            ),
            {
                "id": n["id"],
                "name_ru": n["name_ru"],
                "name_kz": n["name_kz"],
                "difficulty": n.get("difficulty"),
                "tag": n.get("tag"),
            },
        )

    # (2) Полный wipe edges — снимает FK-блок на DELETE nodes ниже и готовит
    # таблицу под чистую вставку 181 нового ребра.
    result = await session.execute(text("DELETE FROM edges"))
    edges_deleted = result.rowcount or 0

    # (3) DELETE mastery + DELETE nodes для 4 удалённых узлов (одобрено владельцем).
    result = await session.execute(
        text("DELETE FROM mastery WHERE node_id IN ('NM01', 'NM02', 'NM03', 'ALG01')")
    )
    mastery_deleted = result.rowcount or 0

    result = await session.execute(
        text("DELETE FROM nodes WHERE id IN ('NM01', 'NM02', 'NM03', 'ALG01')")
    )
    nodes_deleted = result.rowcount or 0
    assert nodes_deleted == len(DELETE_NODES), (
        f"nodes: удалено {nodes_deleted}, ожидалось {len(DELETE_NODES)}"
    )

    # (4) INSERT 181 ребро из prerequisites графа.
    new_edges = [
        {"from_node": prereq, "to_node": n["id"]}
        for n in nodes_raw
        for prereq in n.get("prerequisites", [])
    ]
    assert len(new_edges) == EXPECTED_EDGE_COUNT, (
        f"graph JSON: {len(new_edges)} рёбер, ожидалось {EXPECTED_EDGE_COUNT}"
    )
    for e in new_edges:
        await session.execute(
            text(
                "INSERT INTO edges (from_node, to_node, encompassing_weight) "
                "VALUES (:from_node, :to_node, 0.5) ON CONFLICT DO NOTHING"
            ),
            e,
        )

    return {
        "edges_deleted_old": edges_deleted,
        "mastery_deleted": mastery_deleted,
        "nodes_deleted": nodes_deleted,
        "edges_inserted_new": len(new_edges),
    }


# ── §7. topics / topic_edges / nodes.topic_id ────────────────────────────────


async def migrate_topics(session, topics_json: dict) -> dict:
    """Upsert тем/рёбер-тем/привязки узел→тема (та же логика, что db/seed.py::seed_topics).

    Пустые/осиротевшие темы в БД (те, что убраны из нового JSON) НЕ удаляются —
    только докладываются (владелец решит cleanup отдельно, см. вердикт раздел 5).
    """
    for t in topics_json["topics"]:
        await session.execute(
            text(
                """
                INSERT INTO topics (id, strand, grade, order_idx, name_ru, name_kz)
                VALUES (:id, :strand, :grade, :order_idx, :name_ru, :name_kz)
                ON CONFLICT (id) DO UPDATE SET
                    strand = EXCLUDED.strand, grade = EXCLUDED.grade,
                    order_idx = EXCLUDED.order_idx,
                    name_ru = EXCLUDED.name_ru, name_kz = EXCLUDED.name_kz
                """
            ),
            {
                "id": t["id"],
                "strand": t["strand"],
                "grade": t.get("grade"),
                "order_idx": t.get("order", 0),
                "name_ru": t["name_ru"],
                "name_kz": t["name_kz"],
            },
        )

    for a, b in topics_json["topic_edges"]:
        await session.execute(
            text(
                "INSERT INTO topic_edges (from_topic, to_topic) VALUES (:a, :b) "
                "ON CONFLICT (from_topic, to_topic) DO NOTHING"
            ),
            {"a": a, "b": b},
        )

    for node_id, topic_id in topics_json["node_topic"].items():
        await session.execute(
            text("UPDATE nodes SET topic_id = :tid WHERE id = :nid"),
            {"tid": topic_id, "nid": node_id},
        )

    new_topic_ids = {t["id"] for t in topics_json["topics"]}
    db_topic_ids = {
        row[0] for row in (await session.execute(text("SELECT id FROM topics"))).fetchall()
    }
    orphan_topics = sorted(db_topic_ids - new_topic_ids)

    return {
        "topics_upserted": len(topics_json["topics"]),
        "topic_edges_upserted": len(topics_json["topic_edges"]),
        "nodes_mapped": len(topics_json["node_topic"]),
        "orphan_topics": orphan_topics,
    }


# ── §8. Пост-ассерты ──────────────────────────────────────────────────────────


async def post_assert(session, problems_json: list[dict]) -> None:
    node_count = (await session.execute(text("SELECT count(*) FROM nodes"))).scalar()
    assert node_count == EXPECTED_NODE_COUNT, f"пост-ассерт: nodes={node_count}, ожидалось {EXPECTED_NODE_COUNT}"

    edge_count = (await session.execute(text("SELECT count(*) FROM edges"))).scalar()
    assert edge_count == EXPECTED_EDGE_COUNT, f"пост-ассерт: edges={edge_count}, ожидалось {EXPECTED_EDGE_COUNT}"

    node_ids = {
        row[0] for row in (await session.execute(text("SELECT id FROM nodes"))).fetchall()
    }
    problem_node_ids = {
        row[0] for row in (await session.execute(text("SELECT DISTINCT node_id FROM problems"))).fetchall()
    }
    dangling_problems = problem_node_ids - node_ids
    assert not dangling_problems, f"пост-ассерт: problems ссылаются на несуществующие узлы {dangling_problems}"

    decomp_node_ids = {
        row[0]
        for row in (
            await session.execute(text("SELECT DISTINCT node_id FROM decomposition_problems"))
        ).fetchall()
    }
    dangling_decomp = decomp_node_ids - node_ids
    assert not dangling_decomp, f"пост-ассерт: decomposition ссылается на несуществующие узлы {dangling_decomp}"

    mastery_orphans = (
        await session.execute(
            text("SELECT count(*) FROM mastery WHERE node_id IN ('NM01', 'NM02', 'NM03', 'ALG01')")
        )
    ).scalar()
    assert mastery_orphans == 0, f"пост-ассерт: mastery по удалённым узлам = {mastery_orphans}, ожидалось 0"


async def run() -> int:
    async with async_session() as session:
        # ВАЖНО: guard-запрос и вся миграция — в ОДНОЙ транзакции. AsyncSession
        # автостартует implicit-транзакцию на первый execute(), поэтому
        # session.begin() открываем ДО guard-запроса — иначе "transaction
        # already begun".
        async with session.begin():
            if await _already_migrated(session):
                log.info("Узел NM01 отсутствует в nodes — граф уже мигрирован. Выход без изменений.")
                return 0

            graph_json = _load(_GRAPH_PATH)
            topics_json = _load(_TOPICS_PATH)
            problems_data = _load(_PROBLEMS_PATH)
            decomp_data = _load(_DECOMP_PATH)
            problems_json = problems_data["problems"]
            decomp_json = decomp_data["problems"]

            problems_remapped = await migrate_problems(session, problems_json)
            decomp_remapped = await migrate_decomposition(session, decomp_json)
            dependent_counters = await migrate_dependent_tables(session)
            node_edge_counters = await migrate_nodes_and_edges(session, graph_json)
            topics_counters = await migrate_topics(session, topics_json)
            await post_assert(session, problems_json)

        print("=== Миграция графа v02 на existing-БД: ПРИМЕНЕНО ===")
        print(f"problems.node_id перепривязано: {problems_remapped}")
        print(f"decomposition_problems.node_id перепривязано: {decomp_remapped}")
        print(f"attempts.node_id обновлено: {dependent_counters['attempts']}")
        print(f"error_captures.node_id обновлено: {dependent_counters['error_captures']}")
        print(
            "recurring_errors.node_id обновлено: "
            f"{dependent_counters['recurring_errors_nm']} (NM*→RN01) + "
            f"{dependent_counters['recurring_errors_alg01']} (ALG01→AL01)"
        )
        print(f"edges удалено (старых): {node_edge_counters['edges_deleted_old']}")
        print(f"mastery удалено (4 старых узла): {node_edge_counters['mastery_deleted']}")
        print(f"nodes удалено: {node_edge_counters['nodes_deleted']}")
        print(f"edges вставлено (новых): {node_edge_counters['edges_inserted_new']}")
        print(
            f"topics upsert: {topics_counters['topics_upserted']}, "
            f"topic_edges upsert: {topics_counters['topic_edges_upserted']}, "
            f"nodes_mapped: {topics_counters['nodes_mapped']}"
        )
        print(f"Темы-сироты в БД (НЕ удалены, только доклад): {topics_counters['orphan_topics']}")
        print()
        print("Пост-ассерты: OK (nodes=114, edges=181, no dangling problems/decomposition, mastery по удалённым=0)")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(run())
    sys.exit(exit_code)
