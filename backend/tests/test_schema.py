"""Тест: все шесть таблиц тренажёра ошибок существуют в схеме БД.

TDD-RED: упадёт до добавления моделей в db/models.py.
TDD-GREEN: пройдёт после добавления ORM-моделей и CREATE TABLE IF NOT EXISTS в run.py.
"""

import pytest
from sqlalchemy import text

# Ожидаемые таблицы тренажёра ошибок
_EXPECTED_TABLES = {
    "micro_skills",
    "decomposition_problems",
    "problem_steps",
    "problem_fingerprints",
    "error_captures",
    "recurring_errors",
}


@pytest.mark.asyncio
async def test_new_tables_exist(db_session):
    """Шесть новых таблиц тренажёра должны присутствовать в схеме.

    Проверяем через pg_tables напрямую через сессию — надёжнее, чем
    AsyncSession.bind.connect() + inspect (зависит от версии SQLAlchemy).
    asyncpg-native массив: = ANY(:names) вместо IN-tuple.
    """
    result = await db_session.execute(
        text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = ANY(:names)"
        ).bindparams(names=list(_EXPECTED_TABLES))
    )
    found = {row[0] for row in result}
    missing = _EXPECTED_TABLES - found
    assert not missing, f"отсутствуют таблицы: {missing}"
