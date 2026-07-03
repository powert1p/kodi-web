"""Схема Блока 1.0: колонки consent + таблица events создаются метадатой."""
from __future__ import annotations

import os
os.environ.setdefault("JWT_SECRET", "test-secret")

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
