"""Интеграционный тест чата тьютора (LLM замокан)."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def tclient(db_session, monkeypatch):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    SID = 9600
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('TU01', 'Тема', 'Тема', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    pid = (await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer) VALUES ('TU01', 'q', '1') RETURNING id"
    ))).scalar_one()
    await db_session.commit()

    from api.routes import _create_token
    token = _create_token(SID)

    # Мокаем LLM на уровне endpoint-импорта
    async def _fake_reply(*args, **kwargs):
        return "Подумай, что меняется на втором шаге?"
    monkeypatch.setattr("api.routers.trainer.generate_tutor_reply", _fake_reply)

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
async def test_tutor_chat_creates_session_and_persists(tclient):
    ac, token, pid, sid = tclient
    resp = await ac.post("/api/trainer/tutor/chat",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"problem_id": pid, "message": "не понял этот шаг"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reply"].startswith("Подумай")
    # history: user + assistant
    assert len(body["history"]) == 2
    assert body["history"][0]["role"] == "user"
    assert body["history"][1]["role"] == "assistant"

    # второй ход — та же сессия, history растёт
    resp2 = await ac.post("/api/trainer/tutor/chat",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"problem_id": pid, "message": "а дальше?"})
    body2 = resp2.json()
    assert body2["session_id"] == body["session_id"]
    assert len(body2["history"]) == 4


@pytest.mark.asyncio
async def test_tutor_chat_no_token_401(tclient):
    ac, token, pid, sid = tclient
    resp = await ac.post("/api/trainer/tutor/chat", json={"problem_id": pid, "message": "hi"})
    assert resp.status_code == 401
