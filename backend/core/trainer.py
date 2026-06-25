"""Тренажёр ошибок: сопоставление ответа с банком отпечатков ошибок.

Модуль предоставляет match_fingerprint — основную функцию для поиска
гипотезы о причине ошибки ученика по его ответу на задачу.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Переиспользуем нормализацию из grading.py — не переизобретаем
from core.grading import _normalise, _try_as_number

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Fingerprint:
    """Отпечаток типичной ошибки: умение + описание + неверный ответ + индекс декомпозиции."""

    micro_skill: str
    mistake_ru: str
    wrong_answer: str
    decomp_idx: int


def _answers_match(given: str, stored: str) -> bool:
    """Сравниваем нормализованные ответы с числовой толерантностью.

    Логика аналогична check_answer_rule_based: сначала точное строковое совпадение
    после нормализации, затем числовое сравнение с допуском 1e-6.
    """
    norm_given = _normalise(given)
    norm_stored = _normalise(stored)

    # Точное совпадение после нормализации
    if norm_given == norm_stored:
        return True

    # Числовое сравнение (ловит "80" == "80.0", "1/2" == "0.5" и т.п.)
    n_given = _try_as_number(norm_given)
    n_stored = _try_as_number(norm_stored)
    if n_given is not None and n_stored is not None:
        return abs(n_given - n_stored) < 1e-6

    return False


async def match_fingerprint(
    session: AsyncSession,
    *,
    problem_id: int,
    answer_given: str,
) -> Fingerprint | None:
    """Ищет отпечаток ошибки для заданного ответа ученика.

    Алгоритм в два шага:
      1. Linked-путь: ищем записи decomposition_problems с problems_db_id == problem_id.
         Это ~42% задач, где совпадение однозначно.
      2. Fallback по (node_id, answer): берём node_id и правильный answer из problems,
         ищем decomp-записи с теми же полями (в т.ч. problems_db_id IS NULL).

    Среди найденных decomp-записей запрашиваем их fingerprints и возвращаем тот,
    чей wrong_answer нормализованно совпадает с answer_given. Если совпадений нет — None.

    Args:
        session: Async SQLAlchemy-сессия.
        problem_id: ID задачи из таблицы problems.
        answer_given: Ответ ученика (до нормализации).

    Returns:
        Fingerprint с описанием ошибки, или None если отпечаток не найден.
    """
    # ── Шаг 1: ищем linked decomp-записи (problems_db_id == problem_id) ──────
    linked_rows = await session.execute(
        text(
            "SELECT idx FROM decomposition_problems "
            "WHERE problems_db_id = :pid"
        ),
        {"pid": problem_id},
    )
    decomp_idxs: list[int] = [row.idx for row in linked_rows]

    if not decomp_idxs:
        # ── Шаг 2: fallback — получаем node_id + answer из DB-задачи ──────────
        prob_row = await session.execute(
            text("SELECT node_id, answer FROM problems WHERE id = :pid"),
            {"pid": problem_id},
        )
        prob = prob_row.fetchone()
        if prob is None:
            # Задача не найдена в базе — fingerprint недоступен
            logger.warning("match_fingerprint: problem_id=%d не найден в problems", problem_id)
            return None

        node_id: str = prob.node_id
        correct_answer: str = prob.answer

        # Ищем все decomp-записи, разделяющие тот же (node_id, answer)
        fallback_rows = await session.execute(
            text(
                "SELECT idx FROM decomposition_problems "
                "WHERE node_id = :nid AND answer = :ans"
            ),
            {"nid": node_id, "ans": correct_answer},
        )
        decomp_idxs = [row.idx for row in fallback_rows]

    if not decomp_idxs:
        # Нет decomp-записей — fingerprint недоступен
        return None

    # ── Запрашиваем fingerprints для всех найденных decomp_idx ──────────────
    # Используем = ANY(:arr) — asyncpg-native синтаксис для массивов (безопасно, без f-string)
    fp_rows = await session.execute(
        text(
            "SELECT id, decomp_idx, micro_skill, wrong_answer, mistake_ru "
            "FROM problem_fingerprints "
            "WHERE decomp_idx = ANY(:arr)"
        ),
        {"arr": decomp_idxs},
    )
    fingerprints = fp_rows.fetchall()

    if not fingerprints:
        return None

    # ── Ищем fingerprint с нормализованно совпадающим wrong_answer ───────────
    for fp in fingerprints:
        if _answers_match(answer_given, fp.wrong_answer):
            return Fingerprint(
                micro_skill=fp.micro_skill,
                mistake_ru=fp.mistake_ru,
                wrong_answer=fp.wrong_answer,
                decomp_idx=fp.decomp_idx,
            )

    # Ни один wrong_answer не совпал — вероятно, правильный ответ или неизвестная ошибка
    return None
