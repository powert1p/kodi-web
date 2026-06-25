"""Тест: все шесть таблиц тренажёра ошибок существуют в схеме БД.

TDD-RED: упадёт до добавления моделей в db/models.py.
TDD-GREEN: пройдёт после добавления ORM-моделей и CREATE TABLE IF NOT EXISTS в run.py.
"""

import pytest
from sqlalchemy import inspect


@pytest.mark.asyncio
async def test_new_tables_exist(db_session):
    """Шесть новых таблиц тренажёра должны присутствовать в схеме."""
    async with db_session.bind.connect() as conn:
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())

    expected = (
        "micro_skills",
        "decomposition_problems",
        "problem_steps",
        "problem_fingerprints",
        "error_captures",
        "recurring_errors",
    )
    for table in expected:
        assert table in names, f"отсутствует таблица: {table}"
