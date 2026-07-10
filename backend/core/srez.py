"""Мини-срез (Блок 1.0): stateless-выбор задач для быстрого онбординга.

НЕ переиспользует diagnostic/exam FSM. Задачи выбираются один раз на /srez/start,
стейт держит клиент; ответы пишутся как attempts(source="diagnostic").
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# answer_type, набираемые с клавиатуры (choice/text исключены — их не ввести полем).
_TYPEABLE = ("number", "integer", "fraction", "decimal", "float")

# Сколько задач-стретчей (сложнее окна класса) добавляем сверх основного набора.
_STRETCH_COUNT = 2

# Окно node.difficulty по классу, в который ИДЁТ ученик.
# Шкала difficulty УЗЛА (1..5): 1≈3кл, 2≈4кл, 3≈5кл, 4≈6кл, 5=олимпиада/НИШ.
# grade 7 тянем до самого верха (подготовка к экзамену), grade 4 — низ шкалы.
_GRADE_WINDOW: dict[int, tuple[int, int]] = {
    4: (1, 2),
    5: (2, 3),
    6: (3, 4),
    7: (3, 5),
}
# Класс неизвестен (NULL / вне 4–7) — берём середину шкалы.
_DEFAULT_WINDOW: tuple[int, int] = (2, 4)


def _window_for_grade(grade: int | None) -> tuple[int, int]:
    """Окно [lo, hi] целевой difficulty по классу (или дефолт, если класс неизвестен)."""
    if grade is None:
        return _DEFAULT_WINDOW
    return _GRADE_WINDOW.get(grade, _DEFAULT_WINDOW)


def _diff_key(row) -> int:
    """Ключ сортировки по уровню задачи: node.difficulty (None → -1, «ниже всех»)."""
    return row.node_difficulty if row.node_difficulty is not None else -1


def _spread_by_difficulty(rows: list, budget: int) -> list:
    """Отбирает `budget` задач из `rows`, равномерно распределяя по уровням difficulty
    (round-robin по уровням) — чтобы срез не съезжал в низ окна. Внутри уровня — по id."""
    if budget <= 0 or not rows:
        return []
    buckets: dict[int, list] = {}
    for r in rows:
        buckets.setdefault(_diff_key(r), []).append(r)
    for lvl in buckets:
        buckets[lvl].sort(key=lambda r: r.id)
    levels = sorted(buckets)
    picked: list = []
    while len(picked) < budget and any(buckets[lvl] for lvl in levels):
        for lvl in levels:
            if buckets[lvl]:
                picked.append(buckets[lvl].pop(0))
                if len(picked) >= budget:
                    break
    return picked


async def pick_srez_problems(
    session: AsyncSession, student_id: int, count: int = 12, grade: int | None = None
):
    """Возвращает до `count` задач онбординг-среза ПО УРОВНЮ КЛАССА.

    Уровень ЗАДАЧИ = node.difficulty (1..5). ⚠️ problems.difficulty / sub_difficulty —
    это относительный ранг ВНУТРИ узла (1=easy..4=advanced, на всём банке идентичны
    друг другу), НЕ абсолютный класс — поэтому окно строим по difficulty узла.

    Логика (grade → окно, см. `_GRADE_WINDOW`):
      • ~`count - стретч` задач В ОКНЕ [lo, hi]: разброс по темам (DISTINCT ON topic),
        decomp-задачи мягко предпочтены, разброс по уровням внутри окна (round-robin);
      • + до `_STRETCH_COUNT` «стретч»-задач difficulty ВЫШЕ окна (если такие есть) —
        ближайшие к окну, как посильный вызов;
      • задачи с уже решёнными attempts исключаются.

    Добор задачами НИЖЕ окна — ТОЛЬКО при нехватке кандидатов в окне (узкий банк или
    почти всё решено). Пока в окне есть кандидаты, «лёгкое» (23+45) не показываем.

    Каждая строка: .id .statement .answer_type .node_id .node_title .node_difficulty .topic_key
    """
    lo, hi = _window_for_grade(grade)
    # По одной лучшей задаче на тему; представитель темы выбирается band-aware:
    # сначала «в окне» (band 0), затем «выше окна» (1), затем «ниже/неизвестно» (2).
    # Внутри band — difficulty DESC: тема отдаёт свой САМЫЙ сложный в окне узел (потолок,
    # посильный классу), иначе почти все темы схлопнулись бы в d3 (модальный уровень) и
    # срез для 6–7 класса вышел бы слишком лёгким. Разброс по уровням даёт round-robin ниже.
    result = await session.execute(
        text(
            "SELECT DISTINCT ON (COALESCE(n.topic_id, n.id)) "
            "  p.id, p.text_ru AS statement, p.answer_type, p.node_id, "
            "  n.name_ru AS node_title, n.difficulty AS node_difficulty, "
            "  COALESCE(n.topic_id, n.id) AS topic_key, "
            "  CASE "
            "    WHEN n.difficulty IS NULL THEN 2 "
            "    WHEN n.difficulty < :lo THEN 2 "
            "    WHEN n.difficulty > :hi THEN 1 "
            "    ELSE 0 "
            "  END AS band "
            "FROM problems p "
            "JOIN nodes n ON n.id = p.node_id "
            "LEFT JOIN decomposition_problems dp ON dp.problems_db_id = p.id "
            "WHERE (p.answer_type IS NULL OR p.answer_type = ANY(:types)) "
            "  AND NOT EXISTS ( "
            "    SELECT 1 FROM attempts a "
            "    WHERE a.student_id = :sid AND a.problem_id = p.id "
            "  ) "
            "ORDER BY COALESCE(n.topic_id, n.id), band, "
            "         (dp.problems_db_id IS NOT NULL) DESC, "
            "         n.difficulty DESC NULLS LAST, p.id"
        ),
        {"types": list(_TYPEABLE), "sid": student_id, "lo": lo, "hi": hi},
    )
    rows = result.fetchall()

    in_window = [r for r in rows if r.band == 0]
    above = [r for r in rows if r.band == 1]
    below = [r for r in rows if r.band == 2]

    # Стретч: ближайшие к окну сверху, не больше _STRETCH_COUNT (и не больше count).
    stretch = sorted(above, key=_diff_key)[: min(_STRETCH_COUNT, count)]
    main_budget = max(0, count - len(stretch))

    # Основной набор — из окна, с разбросом по уровням.
    main = _spread_by_difficulty(in_window, main_budget)
    if len(main) < main_budget:
        # Нехватка в окне → добор снизу: ближайшие к окну (наибольший difficulty) первыми.
        deficit = main_budget - len(main)
        main += sorted(below, key=_diff_key, reverse=True)[:deficit]

    # Показ: монотонный рост сложности, стретч — в конце как финальный вызов.
    main.sort(key=_diff_key)
    return (main + stretch)[:count]
