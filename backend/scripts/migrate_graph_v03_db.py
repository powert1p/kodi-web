"""Миграция existing-БД на граф v03 (вердикт docs/specs/2026-07-06-graph-topic-audit-verdict.md).

В отличие от v02 (полный wipe+reinsert edges, т.к. МЕНЯЛИСЬ сами узлы и их
поля) — v03 не удаляет/добавляет узлы, только точечная правка: 6 DROP + 3 ADD
рёбер, 3 переименования тем (name_ru), 5 точечных переносов node_id у
конкретных задач. Поэтому подход — ТОЧЕЧНЫЙ DELETE/INSERT/UPDATE по явным
литералам из вердикта (self-contained: скрипт не зависит от того, что JSON-
файлы уже применены apply_graph_v03.py — он сам содержит те же литералы,
"дословно из вердикта").

ОДНА транзакция: любой упавший assert = полный rollback, в БД не остаётся
частичных изменений.

Идемпотентность: КАЖДАЯ правка проверяет текущее состояние перед изменением
(DELETE/INSERT ON CONFLICT естественно дают rowcount=0 на повторном прогоне;
UPDATE — через явный pre-check "текущее значение = старое ИЛИ новое, иначе
abort"). Второй прогон скрипта = 0 изменений по всем счётчикам, без ошибок.

Синхронизация node_id 5 перенесённых задач — БЕЗ позиционного выравнивания
(ORDER BY id + zip), а ПО ТЕКСТУ (text_ru LIKE) — это НЕ подвержено SEED-1
(дормантный баг позиционного рассинхрона problems_v10.json↔БД, см.
docs/data-state.md): здесь каждая из 5 задач ищется по уникальной текстовой
подстроке, а не по позиции.

Денорм node_id — обновляется в problems + связанных таблицах, где есть точный
problem_id (attempts/error_captures/problem_reports/tutor_sessions — точное
попадание WHERE problem_id=<найденный id>) и decomposition_problems (точное
попадание WHERE idx=<известный idx>). recurring_errors ЦЕЛЕНАПРАВЛЕННО НЕ
трогается: там нет problem_id (PK student_id+micro_skill, node_id — "последний
узел ошибки"), а узлы LG06/WP08/DA01 НЕ удаляются (в отличие от v02, где
NM01-3/ALG01 удалялись целиком и blanket-UPDATE recurring_errors был
безопасен). Blanket UPDATE recurring_errors SET node_id=... WHERE node_id IN
(LG06,WP08,DA01) в v03 задел бы ошибки ПО ДРУГИМ задачам этих узлов — узлы
остаются, у них полно других задач. Нет надёжного ключа — не трогаем.

Запуск (dev):
    cd backend
    ../.venv/bin/python scripts/migrate_graph_v03_db.py \\
        --dsn postgresql://postgres:postgres@127.0.0.1:5432/nismathbot
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем backend/ в sys.path — скрипт запускается из backend/ (как seed_demo.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── §1. Литералы вердикта (дословно те же, что в apply_graph_v03.py) ────────

DROP_EDGES: list[tuple[str, str]] = [
    ("AR09", "CV04"), ("AR09", "CV05"), ("GE01", "GE12"),
    ("EQ02", "WP03"), ("DV02", "LG04"), ("AL01", "EQ02"),
]

ADD_EDGES: list[tuple[str, str]] = [
    ("AL02", "EQ02"), ("DC01", "AR07"), ("AR10", "LG04"),
]

# {topic_id: (старое name_ru, новое name_ru)}
TOPIC_RENAMES: dict[str, tuple[str, str]] = {
    "4.NF.B": (
        "Дроби на числовой прямой и смешанные числа",
        "Смешанные числа и неправильные дроби",
    ),
    "NIS.ALG": (
        "Продвинутая алгебра (системы, модуль, квадратные)",
        "Продвинутая алгебра (системы, модуль, неравенства)",
    ),
    "4.MD.A": (
        "Измерения и перевод единиц",
        "Площадь прямоугольника и квадрата",
    ),
}

# (текст-гард — уникальная подстрока text_ru, старый node_id, новый node_id,
# idx в decomposition_problems/problems_v10.json — позиция, ПОДТВЕРЖДЕНА
# сверкой с problems_v10.json на этапе apply_graph_v03.py, метка из вердикта).
PROBLEM_TRANSFERS: list[dict] = [
    {"guard": "У Пети и Васи вместе 14 яблок", "old": "LG06", "new": "EQ07",
     "idx": 774, "label": "id 775 — сумма-разность"},
    {"guard": "У Тани 3 яблока, у Саши на 2 больше", "old": "LG06", "new": "AR01",
     "idx": 771, "label": "id 772 — простое сложение"},
    {"guard": "5 друзей пожали руки каждый с каждым", "old": "LG06", "new": "CB01",
     "idx": 776, "label": "id 777 — рукопожатия C(5,2)"},
    {"guard": "Айдар и Болат покрасили забор", "old": "WP08", "new": "WP05",
     "idx": 1195, "label": "совместная работа"},
    {"guard": "Сколько мод есть в ряде чисел", "old": "DA01", "new": "DA03",
     "idx": 2323, "label": "мода без диаграммы"},
]

EXPECTED_EDGE_COUNT = 178
EXPECTED_NODE_COUNT = 114
EXPECTED_PREREQS_AFTER: dict[str, set[str]] = {
    "AR07": {"AR06", "DC01"},
    "LG04": {"AR06", "AR10"},
    "GE12": {"CB01"},
    "CV04": {"GE02"},
    "CV05": {"CV04"},
    "WP03": {"WP02"},
    "EQ02": {"EQ01", "AL02"},
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Миграция графа v03 на existing-БД")
    parser.add_argument("--dsn", required=True, help="postgresql://... DSN целевой БД")
    return parser.parse_args()


# ── §2. Рёбра ─────────────────────────────────────────────────────────────


async def migrate_edges(session) -> dict[str, int]:
    from sqlalchemy import text

    dropped = 0
    for prereq, node in DROP_EDGES:
        result = await session.execute(
            text("DELETE FROM edges WHERE from_node = :p AND to_node = :n"),
            {"p": prereq, "n": node},
        )
        dropped += result.rowcount or 0

    added = 0
    for prereq, node in ADD_EDGES:
        result = await session.execute(
            text(
                "INSERT INTO edges (from_node, to_node, encompassing_weight) "
                "VALUES (:p, :n, 0.5) ON CONFLICT DO NOTHING"
            ),
            {"p": prereq, "n": node},
        )
        added += result.rowcount or 0

    edge_count = (await session.execute(text("SELECT count(*) FROM edges"))).scalar()
    assert edge_count == EXPECTED_EDGE_COUNT, (
        f"edges: после правки {edge_count}, ожидалось {EXPECTED_EDGE_COUNT}"
    )

    return {"dropped": dropped, "added": added}


# ── §3. Темы (name_ru) ────────────────────────────────────────────────────


async def migrate_topics(session) -> dict[str, int]:
    from sqlalchemy import text

    renamed = already_new = 0
    for topic_id, (old_name, new_name) in TOPIC_RENAMES.items():
        row = (
            await session.execute(text("SELECT name_ru FROM topics WHERE id = :id"), {"id": topic_id})
        ).first()
        assert row is not None, f"тема {topic_id} отсутствует в БД"
        current = row[0]
        assert current in (old_name, new_name), (
            f"тема {topic_id}: name_ru={current!r}, ожидалось {old_name!r} или {new_name!r}"
        )
        if current == old_name:
            result = await session.execute(
                text("UPDATE topics SET name_ru = :new WHERE id = :id AND name_ru = :old"),
                {"new": new_name, "id": topic_id, "old": old_name},
            )
            renamed += result.rowcount or 0
        else:
            already_new += 1

    return {"renamed": renamed, "already_new": already_new}


# ── §4. Переносы задач (текст-гард, БЕЗ позиционного выравнивания) ─────────


async def migrate_problems(session) -> list[dict]:
    """Найти каждую из 5 задач по text_ru (LIKE %guard%), проверить node_id,
    обновить точечно. Возвращает список результатов с реальным problems.id —
    нужен для денорм-каскада в §5."""
    from sqlalchemy import text

    results: list[dict] = []
    for tr in PROBLEM_TRANSFERS:
        rows = (
            await session.execute(
                text("SELECT id, node_id FROM problems WHERE text_ru LIKE :pattern"),
                {"pattern": f"%{tr['guard']}%"},
            )
        ).fetchall()
        assert len(rows) == 1, (
            f"гард {tr['guard']!r} ({tr['label']}): найдено {len(rows)} строк в problems, ожидалась 1"
        )
        problem_id, current_node = rows[0]
        assert current_node in (tr["old"], tr["new"]), (
            f"problems.id={problem_id} ({tr['label']}): node_id={current_node!r}, "
            f"ожидался {tr['old']!r} или {tr['new']!r}"
        )
        if current_node == tr["old"]:
            result = await session.execute(
                text("UPDATE problems SET node_id = :new WHERE id = :id AND node_id = :old"),
                {"new": tr["new"], "id": problem_id, "old": tr["old"]},
            )
            status = "moved" if (result.rowcount or 0) else "noop"
        else:
            status = "already_moved"
        results.append({**tr, "problem_id": problem_id, "status": status})

    return results


# ── §5. Денорм node_id в связанных таблицах ─────────────────────────────────


async def migrate_dependent_tables(session, problem_transfers: list[dict]) -> dict[str, int]:
    """Обновить node_id в таблицах, денормализующих его через ТОЧНЫЙ problem_id
    (attempts/error_captures/problem_reports/tutor_sessions), и отдельно
    decomposition_problems (через idx — там нет problem_id-связи, только
    best-effort problems_db_id у ~42% строк).

    recurring_errors ИСКЛЮЧЕНА из этого списка — см. docstring модуля.
    """
    from sqlalchemy import text

    counters: dict[str, int] = {
        "attempts": 0, "error_captures": 0, "problem_reports": 0,
        "tutor_sessions": 0, "decomposition_problems": 0,
    }

    for tr in problem_transfers:
        pid, new_node, old_node = tr["problem_id"], tr["new"], tr["old"]

        for table in ("attempts", "error_captures", "problem_reports", "tutor_sessions"):
            result = await session.execute(
                text(
                    f"UPDATE {table} SET node_id = :new "
                    f"WHERE problem_id = :pid AND node_id = :old"
                ),
                {"new": new_node, "pid": pid, "old": old_node},
            )
            counters[table] += result.rowcount or 0

        result = await session.execute(
            text(
                "UPDATE decomposition_problems SET node_id = :new "
                "WHERE idx = :idx AND node_id = :old"
            ),
            {"new": new_node, "idx": tr["idx"], "old": old_node},
        )
        counters["decomposition_problems"] += result.rowcount or 0

    return counters


# ── §6. Пост-ассерты ──────────────────────────────────────────────────────


async def post_assert(session) -> None:
    from sqlalchemy import text

    node_count = (await session.execute(text("SELECT count(*) FROM nodes"))).scalar()
    assert node_count == EXPECTED_NODE_COUNT, f"пост-ассерт: nodes={node_count}, ожидалось {EXPECTED_NODE_COUNT}"

    edge_count = (await session.execute(text("SELECT count(*) FROM edges"))).scalar()
    assert edge_count == EXPECTED_EDGE_COUNT, f"пост-ассерт: edges={edge_count}, ожидалось {EXPECTED_EDGE_COUNT}"

    # Ацикличность — Kahn's algorithm поверх реальных рёбер БД.
    rows = (await session.execute(text("SELECT from_node, to_node FROM edges"))).fetchall()
    node_ids = {
        row[0] for row in (await session.execute(text("SELECT id FROM nodes"))).fetchall()
    }
    indegree = {nid: 0 for nid in node_ids}
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for from_node, to_node in rows:
        adjacency[from_node].append(to_node)
        indegree[to_node] += 1
    queue = [nid for nid, deg in indegree.items() if deg == 0]
    visited = 0
    while queue:
        nid = queue.pop()
        visited += 1
        for nxt in adjacency[nid]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    assert visited == len(node_ids), f"пост-ассерт: граф содержит цикл(ы) — Kahn посетил {visited}/{len(node_ids)}"

    # Ожидаемые входы затронутых узлов.
    for nid, expected in EXPECTED_PREREQS_AFTER.items():
        actual = {
            row[0] for row in
            (await session.execute(text("SELECT from_node FROM edges WHERE to_node = :n"), {"n": nid})).fetchall()
        }
        assert actual == expected, f"пост-ассерт: узел {nid} входы={actual}, ожидалось {expected}"

    # 0 задач-сирот (problems.node_id ссылается на существующий узел).
    orphans = (
        await session.execute(
            text(
                "SELECT count(*) FROM problems p "
                "LEFT JOIN nodes n ON p.node_id = n.id WHERE n.id IS NULL"
            )
        )
    ).scalar()
    assert orphans == 0, f"пост-ассерт: задач-сирот (node_id не в nodes) = {orphans}, ожидалось 0"

    # Темы переименованы.
    for topic_id, (_old, new_name) in TOPIC_RENAMES.items():
        current = (
            await session.execute(text("SELECT name_ru FROM topics WHERE id = :id"), {"id": topic_id})
        ).scalar()
        assert current == new_name, f"пост-ассерт: тема {topic_id} name_ru={current!r}, ожидалось {new_name!r}"

    # 5 задач на новых узлах.
    for tr in PROBLEM_TRANSFERS:
        current = (
            await session.execute(
                text("SELECT node_id FROM problems WHERE text_ru LIKE :pattern"),
                {"pattern": f"%{tr['guard']}%"},
            )
        ).scalar()
        assert current == tr["new"], (
            f"пост-ассерт: задача {tr['label']} node_id={current!r}, ожидалось {tr['new']!r}"
        )


async def run(dsn: str) -> int:
    # env ДО любого импорта core.config — иначе fail-fast по пустому JWT_SECRET
    # (тот же паттерн, что backend/tests/conftest.py).
    os.environ.setdefault("JWT_SECRET", "migration-script")
    os.environ["DATABASE_URL"] = dsn

    from db.base import async_session  # локальный импорт — подхватывает --dsn как DATABASE_URL

    async with async_session() as session:
        async with session.begin():
            edge_counters = await migrate_edges(session)
            topic_counters = await migrate_topics(session)
            problem_results = await migrate_problems(session)
            dependent_counters = await migrate_dependent_tables(session, problem_results)
            await post_assert(session)

        print("=== Миграция графа v03 на existing-БД: ПРИМЕНЕНО ===")
        print(f"Рёбра: {edge_counters['dropped']} дропнуто, {edge_counters['added']} добавлено")
        print(f"Темы: {topic_counters['renamed']} переименовано, {topic_counters['already_new']} уже новые")
        print("Перенос задач:")
        for r in problem_results:
            print(f"  [{r['status']}] problems.id={r['problem_id']} ({r['label']}): {r['old']}→{r['new']}")
        print(
            "Денорм-каскад (обновлено строк): "
            f"attempts={dependent_counters['attempts']}, "
            f"error_captures={dependent_counters['error_captures']}, "
            f"problem_reports={dependent_counters['problem_reports']}, "
            f"tutor_sessions={dependent_counters['tutor_sessions']}, "
            f"decomposition_problems={dependent_counters['decomposition_problems']}"
        )
        print("recurring_errors: НЕ тронуто (нет надёжного problem_id-ключа, см. docstring)")
        print()
        print(
            "Пост-ассерты: OK (nodes=114, edges=178, ацикличность Kahn, "
            "ожидаемые входы AR07/LG04/GE12/CV04/CV05/WP03/EQ02, 0 задач-сирот, "
            "темы переименованы, 5 задач на новых узлах)"
        )
        return 0


if __name__ == "__main__":
    args = _parse_args()
    exit_code = asyncio.run(run(args.dsn))
    sys.exit(exit_code)
