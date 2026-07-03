"""Consent API: 403 на diagnose без согласия, проставление через /consent."""
from __future__ import annotations

import os
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def cclient(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    SID = 9500
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('CN01', 'Узел', 'Узел', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    pid = (await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer, answer_type) "
        "VALUES ('CN01', 'задача', '5', 'number') RETURNING id"
    ))).scalar_one()
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
        yield ac, token, pid, SID
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_diagnose_requires_consent(cclient):
    ac, token, pid, _sid = cclient
    files = {"photo": ("x.jpg", b"\xff\xd8\xff", "image/jpeg")}
    data = {"problem_id": str(pid)}
    r = await ac.post("/api/trainer/diagnose", headers={"Authorization": f"Bearer {token}"},
                      data=data, files=files)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "consent_required"


@pytest.mark.asyncio
async def test_consent_endpoint_sets_flag(cclient, db_session):
    ac, token, _pid, sid = cclient
    r = await ac.post("/api/trainer/consent", headers={"Authorization": f"Bearer {token}"},
                      json={"photo_consent": True})
    assert r.status_code == 200
    row = (await db_session.execute(text(
        "SELECT photo_consent, photo_consent_at FROM students WHERE id = :sid"
    ), {"sid": sid})).fetchone()
    assert row.photo_consent is True
    assert row.photo_consent_at is not None


@pytest_asyncio.fixture
async def rclient(db_session):
    """Клиент против свежей *_test БД без предзаполненного студента — для тестов регистрации."""
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")

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
        yield ac
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_register_without_checkbox_leaves_consent_null(rclient, db_session):
    """Снятый чекбокс при регистрации = «не ответил» (NULL), НЕ отказ (False)."""
    r = await rclient.post("/api/auth/phone/register", json={
        "name": "Тест Студент",
        "phone": "+77011234567",
        "pin": "1234",
    })
    assert r.status_code == 200
    token = r.json()["access_token"]

    row = (await db_session.execute(text(
        "SELECT photo_consent, photo_consent_at FROM students WHERE phone = :phone"
    ), {"phone": "+77011234567"})).fetchone()
    assert row.photo_consent is None
    assert row.photo_consent_at is None

    me = await rclient.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["photo_consent"] is None
