"""
seed_decomposition.py — стратегия привязки full_decomposition_v1.json к таблице problems.

=== Контекст ===
Файл docs/specs/full_decomposition_v1.json содержит 2525 записей с полями:
    idx               : int   — порядковый номер (0..2524), НЕ соответствует problems.id
    node_id           : str   — идентификатор узла графа (напр. "AR01"), совпадает с DB
    answer            : str   — ответ задачи
    primary_micro_skill: str  — главный микро-навык
    steps             : list  — верифицированные шаги решения
    fingerprints      : list  — сигнатуры ошибок
    all_steps_verified: bool
    needs_review      : bool
    review_reason     : str

Полей text_ru / text_kz в декомпозиции НЕТ — они только в DB.

=== Результаты зондирования (2025-06-25, полный скан 2525 записей) ===

База данных: 1794 задачи (id 16675..18468), 118 узлов.
Декомпозиция: 2525 задач, 118 узлов (те же узлы, но другой банк задач).

Стратегия A: idx → problems.id (прямое или +1)
    → 0/2525 совпадений. idx ∈ [0..2524], DB id ∈ [16675..18468] — диапазоны не пересекаются.

Стратегия B: (node_id, answer) → уникальный problems.id
    → UNIQUE (ровно 1 совпадение): 1059/2525 = 41.9%
    → AMBIG  (>1 совпадений):      458/2525  = 18.1%
    → NONE   (0 совпадений):       1008/2525 = 39.9%

Стратегия C: (node_id, text_ru[:40]) — невозможна: text_ru в декомпозиции отсутствует.

=== Вывод ===
Полноценный JOIN декомпозиции с таблицей problems НЕВОЗМОЖЕН: датасеты генерировались
независимо. DB-задачи были сидированы из problems_v10.json (поле text_ru, своя нумерация).
Декомпозиция — отдельный банк с той же разбивкой по node_id, но разными условиями задач.

=== Выбранная стратегия для сидирования (Task 3) ===
Декомпозиция хранится в ОТДЕЛЬНОЙ таблице (decomposition_problems) с собственным PK = idx.
Привязка к DB: для 41.9% записей (unique_match) поле problems_db_id заполняется через
    (node_id, answer) lookup — ровно 1 совпадение; для остальных NULL.
Поле node_id является FK на nodes.id и служит «мягкой» связью для всех 100% записей.
Логика join при запросе к пользователю: сначала по problems_db_id (если не NULL),
    иначе по node_id (любая задача узла из DB).

JOIN-ключи в application-коде:
    SELECT p.id FROM problems p
    WHERE p.node_id = :node_id AND p.answer = :answer
    -- применять только если COUNT(*) = 1 для данного (node_id, answer)
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Путь к реальному JSON по умолчанию (относительно корня проекта)
_DEFAULT_JSON = (
    pathlib.Path(__file__).parent.parent.parent / "docs" / "specs" / "full_decomposition_v1.json"
)

# Размер batch при вставке строк
_BATCH_SIZE = 500


async def seed_decomposition(
    session: AsyncSession,
    *,
    json_path: pathlib.Path | str | None = None,
) -> dict[str, int]:
    """Сидирует банк декомпозиций из JSON в таблицы micro_skills / decomposition_problems /
    problem_steps / problem_fingerprints.

    Идемпотентность:
    - Пропускает полный сид если decomposition_problems уже не пуста,
      кроме случая когда задана переменная среды FORCE_RESEED=1.
    - micro_skills всегда обновляются через ON CONFLICT DO UPDATE.

    Возвращает словарь с количеством затронутых строк:
      {"micro_skills": int, "decomp_problems": int, "db_linked": int,
       "steps": int, "fingerprints": int}
    """
    path = pathlib.Path(json_path) if json_path else _DEFAULT_JSON

    # ── 1. Загрузка JSON ──────────────────────────────────────────────────────
    logger.info("Загрузка декомпозиций из %s …", path)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    catalog: dict[str, Any] = data["catalog"]
    micro_skills_list: list[dict] = catalog["micro_skills"]
    problems_list: list[dict] = data["problems"]

    # ── 2. Всегда upsert micro_skills ────────────────────────────────────────
    ms_count = 0
    for ms in micro_skills_list:
        await session.execute(
            text(
                """
                INSERT INTO micro_skills (code, label_ru, domain, freq)
                VALUES (:code, :label_ru, :domain, :freq)
                ON CONFLICT (code) DO UPDATE SET
                    label_ru = EXCLUDED.label_ru,
                    domain   = EXCLUDED.domain,
                    freq     = EXCLUDED.freq
                """
            ),
            {
                "code": ms["code"],
                "label_ru": ms["label_ru"],
                "domain": ms.get("domain"),
                "freq": ms.get("freq"),
            },
        )
        ms_count += 1
    await session.commit()
    logger.info("micro_skills upsert: %d записей.", ms_count)

    # ── 3. Гард идемпотентности: пропустить если таблица не пуста ────────────
    force = os.getenv("FORCE_RESEED", "0") == "1"
    existing = (
        await session.execute(text("SELECT count(*) FROM decomposition_problems"))
    ).scalar_one()

    if existing > 0 and not force:
        logger.info(
            "decomposition_problems уже содержит %d строк. Пропуск сида (FORCE_RESEED не задан).",
            existing,
        )
        return {
            "micro_skills": ms_count,
            "decomp_problems": 0,
            "db_linked": 0,
            "steps": 0,
            "fingerprints": 0,
        }

    if force and existing > 0:
        logger.warning("FORCE_RESEED=1: таблицы очищаются для повторного сида.")
        # Каскадное удаление: problem_steps / problem_fingerprints удалятся автоматически
        await session.execute(text("DELETE FROM decomposition_problems"))
        await session.commit()

    # ── 4. Построить lookup: (node_id, answer) → problems.id (только UNIQUE match) ──
    logger.info("Строю lookup (node_id, answer) → problems.id …")
    rows = (
        await session.execute(
            text(
                """
                SELECT node_id, answer, count(*) as cnt, min(id) as pid
                FROM problems
                GROUP BY node_id, answer
                HAVING count(*) = 1
                """
            )
        )
    ).fetchall()
    # Словарь: (node_id, answer) → problems.id
    unique_lookup: dict[tuple[str, str], int] = {
        (r.node_id, str(r.answer)): r.pid for r in rows
    }
    logger.info("Unique (node_id, answer) пар: %d", len(unique_lookup))

    # ── 5. Сид decomposition_problems / steps / fingerprints ─────────────────
    decomp_count = 0
    db_linked = 0
    steps_count = 0
    fp_count = 0

    # Буферы для batch-вставки шагов и fingerprints
    steps_buf: list[dict] = []
    fp_buf: list[dict] = []

    async def _flush_steps() -> None:
        nonlocal steps_count
        if not steps_buf:
            return
        await session.execute(
            text(
                """
                INSERT INTO problem_steps
                    (decomp_idx, n, instruction_ru, micro_skill, expected_value, verified)
                VALUES
                    (:decomp_idx, :n, :instruction_ru, :micro_skill, :expected_value, :verified)
                """
            ),
            steps_buf,
        )
        steps_count += len(steps_buf)
        steps_buf.clear()

    async def _flush_fp() -> None:
        nonlocal fp_count
        if not fp_buf:
            return
        await session.execute(
            text(
                """
                INSERT INTO problem_fingerprints
                    (decomp_idx, micro_skill, wrong_answer, mistake_ru)
                VALUES
                    (:decomp_idx, :micro_skill, :wrong_answer, :mistake_ru)
                """
            ),
            fp_buf,
        )
        fp_count += len(fp_buf)
        fp_buf.clear()

    for prob in problems_list:
        idx: int = prob["idx"]
        node_id: str = prob["node_id"]
        answer: str = str(prob["answer"])

        # Определяем problems_db_id по стратегии B
        problems_db_id: int | None = unique_lookup.get((node_id, answer))
        if problems_db_id is not None:
            db_linked += 1

        # Удаляем старые шаги/fingerprints (на случай FORCE_RESEED или повторного вызова)
        # decomposition_problems ON DELETE CASCADE → достаточно удалить родительскую строку
        # Но мы здесь делаем insert/replace: сначала удаляем если есть, потом вставляем
        await session.execute(
            text("DELETE FROM decomposition_problems WHERE idx = :idx"),
            {"idx": idx},
        )

        # Вставляем запись декомпозиции
        await session.execute(
            text(
                """
                INSERT INTO decomposition_problems
                    (idx, node_id, answer, primary_micro_skill,
                     all_steps_verified, needs_review, problems_db_id)
                VALUES
                    (:idx, :node_id, :answer, :primary_micro_skill,
                     :all_steps_verified, :needs_review, :problems_db_id)
                """
            ),
            {
                "idx": idx,
                "node_id": node_id,
                "answer": answer,
                "primary_micro_skill": prob.get("primary_micro_skill"),
                "all_steps_verified": bool(prob.get("all_steps_verified", False)),
                "needs_review": bool(prob.get("needs_review", False)),
                "problems_db_id": problems_db_id,
            },
        )
        decomp_count += 1

        # Шаги: буферизируем
        for step in prob.get("steps", []):
            steps_buf.append(
                {
                    "decomp_idx": idx,
                    "n": step["n"],
                    "instruction_ru": step["instruction_ru"],
                    "micro_skill": step["micro_skill"],
                    "expected_value": str(step["expected_value"]),
                    "verified": step.get("verified"),
                }
            )

        # Fingerprints: буферизируем
        for fp in prob.get("fingerprints", []):
            fp_buf.append(
                {
                    "decomp_idx": idx,
                    "micro_skill": fp["micro_skill"],
                    "wrong_answer": str(fp["wrong_answer"]),
                    "mistake_ru": fp["mistake_ru"],
                }
            )

        # Сбрасываем буфер при накоплении
        if len(steps_buf) >= _BATCH_SIZE:
            await _flush_steps()
        if len(fp_buf) >= _BATCH_SIZE:
            await _flush_fp()

        # Коммит батчами для снижения нагрузки на транзакцию
        if decomp_count % _BATCH_SIZE == 0:
            await _flush_steps()
            await _flush_fp()
            await session.commit()
            logger.info("Сидировано %d/%d задач декомпозиции…", decomp_count, len(problems_list))

    # Финальный сброс остатков
    await _flush_steps()
    await _flush_fp()
    await session.commit()

    logger.info(
        "Сид декомпозиций завершён: decomp_problems=%d, db_linked=%d (%.1f%%), "
        "steps=%d, fingerprints=%d",
        decomp_count,
        db_linked,
        db_linked / decomp_count * 100 if decomp_count else 0,
        steps_count,
        fp_count,
    )

    return {
        "micro_skills": ms_count,
        "decomp_problems": decomp_count,
        "db_linked": db_linked,
        "steps": steps_count,
        "fingerprints": fp_count,
    }
