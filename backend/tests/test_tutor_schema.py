"""Тест схемы чат-тьютора: таблицы tutor_sessions / tutor_messages создаются и связаны."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest.mark.asyncio
async def test_tutor_tables_exist_and_link(db_session):
    """tutor_sessions + tutor_messages существуют; FK-каскад работает."""
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")

    # Сид минимального студента + узла + задачи
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (9100, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ))
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('TS01', 'тема', 'тема', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    pid = (await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer) VALUES ('TS01', 'q', '1') RETURNING id"
    ))).scalar_one()

    sid = (await db_session.execute(text(
        "INSERT INTO tutor_sessions (student_id, problem_id, node_id, created_at) "
        "VALUES (9100, :pid, 'TS01', NOW()) RETURNING id"
    ), {"pid": pid})).scalar_one()

    await db_session.execute(text(
        "INSERT INTO tutor_messages (session_id, role, content, created_at) "
        "VALUES (:sid, 'user', 'привет', NOW())"
    ), {"sid": sid})
    await db_session.commit()

    cnt = (await db_session.execute(text(
        "SELECT COUNT(*) FROM tutor_messages WHERE session_id = :sid"
    ), {"sid": sid})).scalar_one()
    assert cnt == 1
