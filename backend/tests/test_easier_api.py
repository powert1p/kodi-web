"""Тест climb-down endpoint /easier."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-chars")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def eclient(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    SID = 9500
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('EZ01', 'Легче', 'Легче', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    # два decomp: idx=98001 (2 шага, текущий), idx=98002 (1 шаг, полегче)
    await db_session.execute(text(
        "INSERT INTO decomposition_problems (idx, node_id, answer, primary_micro_skill, all_steps_verified) "
        "VALUES (98001, 'EZ01', '5', 'ez_skill', true), (98002, 'EZ01', '3', 'ez_skill', true)"
    ))
    await db_session.execute(text(
        "INSERT INTO problem_steps (decomp_idx, n, instruction_ru, micro_skill, expected_value) VALUES "
        "(98001, 1, 'шаг1', 'ez_skill', '2'), (98001, 2, 'шаг2', 'ez_skill', '5'), "
        "(98002, 1, 'один шаг', 'ez_skill', '3')"
    ))
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
        yield ac, token
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_easier_returns_fewest_steps(eclient):
    ac, token = eclient
    resp = await ac.get("/api/trainer/easier?micro_skill=ez_skill&exclude_idx=98001",
                        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["decomp_idx"] == 98002
    assert body["step_count"] == 1
    assert len(body["steps"]) == 1
    assert "answer" not in body
    assert "expected_value" not in body["steps"][0]


@pytest.mark.asyncio
async def test_easier_404_unknown_skill(eclient):
    ac, token = eclient
    resp = await ac.get("/api/trainer/easier?micro_skill=nonexistent",
                        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_easier_never_publishes_needs_review_decomposition(eclient):
    ac, token = eclient
    from db.base import async_session

    async with async_session() as session:
        await session.execute(text(
            "INSERT INTO decomposition_problems "
            "(idx, node_id, answer, primary_micro_skill, all_steps_verified, needs_review) "
            "VALUES (97999, 'EZ01', '999', 'review_only_skill', true, true)"
        ))
        await session.execute(text(
            "INSERT INTO problem_steps "
            "(decomp_idx, n, instruction_ru, micro_skill, expected_value) "
            "VALUES (97999, 1, 'Ошибочный шаг = 999', 'review_only_skill', '999')"
        ))
        await session.commit()

    response = await ac.get(
        "/api/trainer/easier?micro_skill=review_only_skill",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
