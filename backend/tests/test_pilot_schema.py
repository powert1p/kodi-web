"""Схема Блока 1.0: колонки consent + таблица events создаются метадатой."""
from __future__ import annotations

import os
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-chars")

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_students_have_consent_columns(db_session):
    cols = (await db_session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'students'"
    ))).scalars().all()
    assert "photo_consent" in cols
    assert "photo_consent_at" in cols


@pytest.mark.asyncio
async def test_student_phone_has_named_unique_index(db_session):
    row = (await db_session.execute(text(
        "SELECT indexdef FROM pg_indexes "
        "WHERE schemaname = 'public' AND tablename = 'students' "
        "AND indexname = 'uq_students_phone_not_null'"
    ))).fetchone()
    assert row is not None
    assert "UNIQUE INDEX" in row.indexdef
    assert "(phone)" in row.indexdef


@pytest.mark.asyncio
async def test_events_table_exists_and_inserts(db_session):
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (1, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ))
    await db_session.execute(text(
        "INSERT INTO events (student_id, event_type, payload) "
        "VALUES (1, 'hub_opened', '{\"k\": 1}'::jsonb)"
    ))
    await db_session.commit()
    n = (await db_session.execute(text("SELECT count(*) FROM events"))).scalar()
    assert n == 1
