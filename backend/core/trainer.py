"""Тренажёр ошибок: сопоставление ответа с банком отпечатков + список задач «срез».

Модуль предоставляет:
  - match_fingerprint          — поиск гипотезы об ошибке ученика по ответу.
  - resolve_decomp             — поиск подходящей декомпозиции для задачи.
  - build_wrong_tasks          — список задач из срезовых попыток с декомпозицией и маршрутом.
  - route_state                — маршрутный статус по порогу владения.
  - route_level                — числовой уровень 1/2/3 по порогу владения (Task 6).
  - pick_easier_decomp         — decomp-запись с наименьшим числом шагов для умения (Task 6).
  - pick_verification_problem  — проверочная задача того же узла, другая (Task 6).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Переиспользуем нормализацию из grading.py — не переизобретаем
from core.grading import _normalise, _try_as_number

logger = logging.getLogger(__name__)

# ── Пороги маршрута (Task 6 добавит route_level/pickers, не трогать) ─────────
LEVEL1_MAX: float = 0.40   # ниже — revisit
LEVEL2_MAX: float = 0.70   # ниже — almost, выше или равно — got


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


# ═══════════════════════════════════════════════════════════════════════════════
# Task 5: route_state / resolve_decomp / build_wrong_tasks
# ═══════════════════════════════════════════════════════════════════════════════


def route_state(mastery: float) -> str:
    """Маршрутный статус по владению узлом.

    revisit  — mastery < LEVEL1_MAX (0.40): повторить тему.
    almost   — LEVEL1_MAX <= mastery < LEVEL2_MAX (0.70): почти.
    got      — mastery >= LEVEL2_MAX: усвоено.
    """
    if mastery < LEVEL1_MAX:
        return "revisit"
    if mastery < LEVEL2_MAX:
        return "almost"
    return "got"


@dataclass
class StepDTO:
    """Один шаг декомпозиции задачи для тренажёра."""

    n: int
    instruction_ru: str
    micro_skill: str
    expected_value: str
    kind: str = "compute"
    reveal: None = None


@dataclass
class WrongTask:
    """Задача из неверных попыток ученика с декомпозицией и маршрутом."""

    id: str                          # UUID-строка для идентификации на клиенте
    problem_id: int
    node_id: str
    topic_label: str
    statement: str
    answer: str
    primary_micro_skill: str | None
    decomp_idx: int | None
    steps: list[StepDTO]
    state: str
    wrong_answer: str
    mastery: float


async def resolve_decomp(
    session: AsyncSession,
    *,
    problem_id: int,
    node_id: str,
    answer: str,
) -> object | None:
    """Ищет подходящую декомпозицию для задачи.

    Приоритет выбора:
      1. Linked: decomposition_problems.problems_db_id == problem_id.
      2. Same-node verified: all_steps_verified=true + node_id совпадает,
         предпочитая запись с answer = задачи (нормализованное сравнение).
      3. None — декомпозиция недоступна.

    Возвращает строку (Row) decomposition_problems или None.
    """
    # ── Шаг 1: linked decomp ─────────────────────────────────────────────────
    linked = await session.execute(
        text(
            "SELECT idx, node_id, answer, primary_micro_skill, all_steps_verified "
            "FROM decomposition_problems "
            "WHERE problems_db_id = :pid "
            "LIMIT 1"
        ),
        {"pid": problem_id},
    )
    row = linked.fetchone()
    if row is not None:
        return row

    # ── Шаг 2: same-node all_steps_verified decomp ────────────────────────────
    same_node = await session.execute(
        text(
            "SELECT idx, node_id, answer, primary_micro_skill, all_steps_verified "
            "FROM decomposition_problems "
            "WHERE node_id = :nid AND all_steps_verified = true "
            "ORDER BY idx"
        ),
        {"nid": node_id},
    )
    candidates = same_node.fetchall()
    if not candidates:
        return None

    # Предпочитаем запись с нормализованно совпадающим answer
    norm_answer = _normalise(answer)
    for c in candidates:
        if _normalise(c.answer) == norm_answer:
            return c

    # Любая verified-запись на том же узле
    return candidates[0]


async def build_wrong_tasks(
    session: AsyncSession,
    student_id: int,
    days: int = 14,
    limit: int = 30,
) -> list[WrongTask]:
    """Строит список задач для тренажёра ошибок на основе срезовых попыток.

    Алгоритм:
      1. Берём последние «days» дней: попытки источников diagnostic/exam/practice,
         где is_correct=false. Используем индекс ix_attempts_student_source.
      2. Джойним problems (statement, answer) и nodes (topic_label).
      3. Дедуплицируем в Python по problem_id — оставляем самую свежую попытку.
      4. Для каждой задачи вызываем resolve_decomp → mapим шаги в StepDTO.
      5. Mastery берём из таблицы mastery (default 0.0).
      6. state = route_state(mastery).
    """
    # ── Запрос неверных попыток за окно ──────────────────────────────────────
    # Интервал параметризован через make_interval(days => :days) — integer-friendly,
    # asyncpg не принимает int в ($N || ' days')::interval.
    # = ANY(:sources) — asyncpg-native синтаксис для text[] (нет f-строк).
    raw = await session.execute(
        text(
            "SELECT "
            "  a.problem_id, a.node_id, a.answer_given, a.created_at, "
            "  p.text_ru AS statement, p.answer, "
            "  n.name_ru AS topic_label "
            "FROM attempts a "
            "JOIN problems p ON p.id = a.problem_id "
            "JOIN nodes   n ON n.id = a.node_id "
            "WHERE a.student_id = :sid "
            "  AND a.is_correct = false "
            "  AND a.source = ANY(:sources) "
            "  AND a.created_at >= now() - make_interval(days => :days) "
            "ORDER BY a.created_at DESC "
            "LIMIT :lim"
        ),
        {
            "sid": student_id,
            "sources": ["diagnostic", "exam", "practice"],
            "days": days,
            "lim": limit * 10,  # берём с запасом — дедупликация в Python
        },
    )
    rows = raw.fetchall()

    # ── Дедупликация по problem_id (первая встреченная = самая свежая, DESC) ──
    seen: dict[int, object] = {}
    for row in rows:
        if row.problem_id not in seen:
            seen[row.problem_id] = row

    deduped = list(seen.values())[:limit]

    if not deduped:
        return []

    # ── Mastery: загружаем оптом для уникальных node_id ──────────────────────
    node_ids = list({r.node_id for r in deduped})
    mastery_rows = await session.execute(
        text(
            "SELECT node_id, p_mastery "
            "FROM mastery "
            "WHERE student_id = :sid AND node_id = ANY(:nids)"
        ),
        {"sid": student_id, "nids": node_ids},
    )
    mastery_map: dict[str, float] = {r.node_id: r.p_mastery for r in mastery_rows}

    # ── Строим WrongTask для каждой задачи ───────────────────────────────────
    result: list[WrongTask] = []
    for row in deduped:
        decomp = await resolve_decomp(
            session,
            problem_id=row.problem_id,
            node_id=row.node_id,
            answer=row.answer,
        )

        # Маппинг шагов из ProblemStep → StepDTO
        if decomp is not None:
            steps_raw = await session.execute(
                text(
                    "SELECT n, instruction_ru, micro_skill, expected_value "
                    "FROM problem_steps "
                    "WHERE decomp_idx = :didx "
                    "ORDER BY n"
                ),
                {"didx": decomp.idx},
            )
            steps = [
                StepDTO(
                    n=s.n,
                    instruction_ru=s.instruction_ru,
                    micro_skill=s.micro_skill,
                    expected_value=s.expected_value,
                )
                for s in steps_raw
            ]
            decomp_idx = decomp.idx
            primary_micro_skill = decomp.primary_micro_skill
        else:
            steps = []
            decomp_idx = None
            primary_micro_skill = None

        mastery_val = mastery_map.get(row.node_id, 0.0)

        result.append(
            WrongTask(
                id=str(uuid.uuid4()),
                problem_id=row.problem_id,
                node_id=row.node_id,
                topic_label=row.topic_label,
                statement=row.statement,
                answer=row.answer,
                primary_micro_skill=primary_micro_skill,
                decomp_idx=decomp_idx,
                steps=steps,
                state=route_state(mastery_val),
                wrong_answer=row.answer_given or "",
                mastery=mastery_val,
            )
        )

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Task 6: route_level / pick_easier_decomp / pick_verification_problem
#
# Пороги LEVEL1_MAX=0.40 и LEVEL2_MAX=0.70 специфичны для тренажёра ошибок.
# Они НЕ совпадают с BKT-порогом владения (0.85, core/bkt.py) и
# UX-порогом графа (0.7, web_graph.py) — разные алгоритмические контексты.
# ═══════════════════════════════════════════════════════════════════════════════


def route_level(mastery: float) -> int:
    """Числовой уровень задания по владению узлом.

    1 — mastery < LEVEL1_MAX (0.40): не знаю тему («revisit»).
    2 — LEVEL1_MAX <= mastery < LEVEL2_MAX (0.70): почти вспомнил («almost»).
    3 — mastery >= LEVEL2_MAX (0.70): усвоено («got»).

    Использует те же константы, что и route_state — не переопределять пороги.
    """
    if mastery < LEVEL1_MAX:
        return 1
    if mastery < LEVEL2_MAX:
        return 2
    return 3


async def pick_easier_decomp(
    session: AsyncSession,
    *,
    micro_skill: str,
    exclude_idx: int | None,
) -> object | None:
    """Ищет decomp-запись с наименьшим числом шагов для заданного micro_skill.

    Условия:
      - primary_micro_skill == micro_skill
      - all_steps_verified = true
      - exclude_idx исключается (поддержка climb-down: не возвращать текущий rung)

    Сортировка: число шагов по возрастанию (COUNT(ps.id)), тай-брейк по idx.
    Возвращает строку (Row) decomposition_problems или None если подходящих нет.

    Параметризованный SQL; f-строки и конкатенация не используются.
    """
    if exclude_idx is not None:
        rows = await session.execute(
            text(
                "SELECT dp.idx, dp.node_id, dp.answer, dp.primary_micro_skill, "
                "       dp.all_steps_verified, "
                "       COUNT(ps.id) AS step_count "
                "FROM decomposition_problems dp "
                "LEFT JOIN problem_steps ps ON ps.decomp_idx = dp.idx "
                "WHERE dp.primary_micro_skill = :ms "
                "  AND dp.all_steps_verified = true "
                "  AND dp.idx != :excl "
                "GROUP BY dp.idx "
                "ORDER BY step_count ASC, dp.idx ASC "
                "LIMIT 1"
            ),
            {"ms": micro_skill, "excl": exclude_idx},
        )
    else:
        rows = await session.execute(
            text(
                "SELECT dp.idx, dp.node_id, dp.answer, dp.primary_micro_skill, "
                "       dp.all_steps_verified, "
                "       COUNT(ps.id) AS step_count "
                "FROM decomposition_problems dp "
                "LEFT JOIN problem_steps ps ON ps.decomp_idx = dp.idx "
                "WHERE dp.primary_micro_skill = :ms "
                "  AND dp.all_steps_verified = true "
                "GROUP BY dp.idx "
                "ORDER BY step_count ASC, dp.idx ASC "
                "LIMIT 1"
            ),
            {"ms": micro_skill},
        )

    return rows.fetchone()


async def pick_verification_problem(
    session: AsyncSession,
    node_id: str,
    exclude_problem_id: int,
) -> object | None:
    """Ищет проверочную задачу того же узла, отличную от текущей.

    Алгоритм:
      - same node_id, id != exclude_problem_id
      - предпочитаем задачу с похожим sub_difficulty (ORDER BY ABS разница по sub_difficulty,
        затем по id для детерминированности)
      - если задач на узле нет кроме исключённой — None

    Параметризованный SQL; f-строки не используются.
    """
    # Сначала получаем sub_difficulty исключённой задачи для сортировки похожести
    excl_row = await session.execute(
        text("SELECT sub_difficulty FROM problems WHERE id = :pid"),
        {"pid": exclude_problem_id},
    )
    excl = excl_row.fetchone()
    ref_diff: int | None = excl.sub_difficulty if excl else None

    if ref_diff is not None:
        # Предпочитаем похожую сложность: ABS(sub_difficulty - ref) ASC, тай-брейк по id
        rows = await session.execute(
            text(
                "SELECT id, node_id, text_ru, answer, sub_difficulty "
                "FROM problems "
                "WHERE node_id = :nid AND id != :excl "
                "ORDER BY ABS(COALESCE(sub_difficulty, :ref) - :ref) ASC, id ASC "
                "LIMIT 1"
            ),
            {"nid": node_id, "excl": exclude_problem_id, "ref": ref_diff},
        )
    else:
        # sub_difficulty недоступен — просто берём следующую по id
        rows = await session.execute(
            text(
                "SELECT id, node_id, text_ru, answer, sub_difficulty "
                "FROM problems "
                "WHERE node_id = :nid AND id != :excl "
                "ORDER BY id ASC "
                "LIMIT 1"
            ),
            {"nid": node_id, "excl": exclude_problem_id},
        )

    return rows.fetchone()
