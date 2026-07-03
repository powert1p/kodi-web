"""Мини-срез (Блок 1.0): stateless-выбор задач для быстрого онбординга.

НЕ переиспользует diagnostic/exam FSM. Задачи выбираются один раз на /srez/start,
стейт держит клиент; ответы пишутся как attempts(source="diagnostic").
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# answer_type, набираемые с клавиатуры (choice/text исключены — их не ввести полем).
_TYPEABLE = ("number", "integer", "fraction", "decimal", "float")


async def pick_srez_problems(session: AsyncSession, student_id: int, count: int = 12):
    """Возвращает до `count` задач: разброс по темам, difficulty ASC, decomp мягко предпочтён,
    исключая задачи, по которым у ученика уже есть attempts.

    Каждая строка: .id .statement .answer_type .node_id .node_title .node_difficulty .topic_key
    """
    result = await session.execute(
        text(
            "SELECT id, statement, answer_type, node_id, node_title, node_difficulty, topic_key "
            "FROM ( "
            "  SELECT DISTINCT ON (COALESCE(n.topic_id, n.id)) "
            "    p.id, p.text_ru AS statement, p.answer_type, p.node_id, "
            "    n.name_ru AS node_title, n.difficulty AS node_difficulty, "
            "    COALESCE(n.topic_id, n.id) AS topic_key, "
            "    (dp.problems_db_id IS NOT NULL) AS has_decomp "
            "  FROM problems p "
            "  JOIN nodes n ON n.id = p.node_id "
            "  LEFT JOIN decomposition_problems dp ON dp.problems_db_id = p.id "
            "  WHERE (p.answer_type IS NULL OR p.answer_type = ANY(:types)) "
            "    AND NOT EXISTS ( "
            "      SELECT 1 FROM attempts a "
            "      WHERE a.student_id = :sid AND a.problem_id = p.id "
            "    ) "
            "  ORDER BY COALESCE(n.topic_id, n.id), has_decomp DESC, "
            "           n.difficulty ASC NULLS LAST, p.id "
            ") per_topic "
            "ORDER BY node_difficulty ASC NULLS LAST, id "
            "LIMIT :lim"
        ),
        {"types": list(_TYPEABLE), "sid": student_id, "lim": count},
    )
    return result.fetchall()
