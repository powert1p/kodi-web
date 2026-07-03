"""Телеметрия: batch insert событий + owner-only CSV-экспорт."""
from __future__ import annotations

import os
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def eclient(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    SID = 9700
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.commit()
    from api.routes import _create_token
    token = _create_token(SID)
    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    eng = create_async_engine(_TEST_URL)
    fac = async_sessionmaker(eng, expire_on_commit=False)
    o1, o2 = db_base.async_session, routes_module.async_session
    db_base.async_session = fac
    routes_module.async_session = fac
    from web import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, token, SID
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_events_batch_insert(eclient, db_session):
    ac, token, sid = eclient
    h = {"Authorization": f"Bearer {token}"}
    r = await ac.post("/api/trainer/events", headers=h, json={"events": [
        {"event_type": "hub_opened"},
        {"event_type": "srez_answered", "payload": {"problem_id": 3, "is_correct": False}},
    ]})
    assert r.status_code == 200
    assert r.json()["inserted"] == 2
    n = (await db_session.execute(text(
        "SELECT count(*) FROM events WHERE student_id = :sid"), {"sid": sid})).scalar()
    assert n == 2


@pytest.mark.asyncio
async def test_events_export_owner_only(eclient):
    ac, token, sid = eclient
    from core.config import settings
    # Не владелец → 403
    old = settings.owner_student_id
    settings.owner_student_id = sid + 1
    r = await ac.get("/api/trainer/events/export?format=csv", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    # Владелец → 200 CSV
    settings.owner_student_id = sid
    r2 = await ac.get("/api/trainer/events/export?format=csv", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert "text/csv" in r2.headers["content-type"]
    assert "event_type" in r2.text
    settings.owner_student_id = old
