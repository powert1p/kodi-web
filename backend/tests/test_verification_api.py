"""Интеграционные тесты verification-эндпоинтов closure."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-chars")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def vclient(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    SID = 9400
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('VF01', 'Проверка', 'Проверка', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    p1 = (await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer, sub_difficulty) "
        "VALUES ('VF01', 'drill-задача', '10', 2) RETURNING id"
    ))).scalar_one()
    p2 = (await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer, sub_difficulty) "
        "VALUES ('VF01', 'контрольная', '20', 2) RETURNING id"
    ))).scalar_one()
    # Каталог micro_skills — нужен для label_ru в ответе verification/start (§2.2)
    await db_session.execute(text(
        "INSERT INTO micro_skills (code, label_ru) VALUES ('vf_skill', 'Навык проверки') "
        "ON CONFLICT (code) DO NOTHING"
    ))
    # recurring_errors ключуется ДИАГНОСТИРОВАННЫМ failed_micro_skill ('vf_failed_ms'),
    # который отличается от primary_micro_skill decomp'а, приходящего с FE ('vf_skill') —
    # резолв должен идти по node_id, а не по совпадению micro_skill.
    await db_session.execute(text(
        "INSERT INTO recurring_errors (student_id, micro_skill, node_id, error_count, resolved, created_at) "
        "VALUES (:sid, 'vf_failed_ms', 'VF01', 2, false, NOW()) ON CONFLICT DO NOTHING"
    ), {"sid": SID})
    await db_session.execute(text(
        "INSERT INTO attempts "
        "(student_id, problem_id, node_id, answer_given, is_correct, source, created_at) "
        "VALUES (:sid, :pid, 'VF01', '11', false, 'diagnostic', NOW())"
    ), {"sid": SID, "pid": p1})
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
        yield ac, token, p1, p2, SID
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_verification_start_returns_other_problem(vclient):
    ac, token, p1, p2, sid = vclient
    resp = await ac.post("/api/trainer/verification/start",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"problem_id": p1, "micro_skill": "vf_skill"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["problem_id"] == p2
    assert body["statement"] == "контрольная"
    assert body["node_id"] == "VF01"
    # label_ru из micro_skills вместо голого кода на UI (запрет §2.2 DESIGN_SYSTEM)
    assert body["micro_skill_label"] == "Навык проверки"


@pytest.mark.asyncio
async def test_verification_start_micro_skill_label_none_for_unknown_code(vclient):
    """Неизвестный micro_skill (нет в каталоге) → micro_skill_label=None, без 500."""
    ac, token, p1, p2, sid = vclient
    resp = await ac.post("/api/trainer/verification/start",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"problem_id": p1, "micro_skill": "unknown_skill_code"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["micro_skill"] == "unknown_skill_code"
    assert body["micro_skill_label"] is None


@pytest.mark.asyncio
async def test_verification_answer_correct_resolves(vclient):
    ac, token, p1, p2, sid = vclient
    headers = {"Authorization": f"Bearer {token}"}
    before = await ac.get("/api/trainer/wrong-tasks", headers=headers)
    assert before.status_code == 200, before.text
    assert any(task["problem_id"] == p1 for task in before.json()["tasks"])

    resp = await ac.post("/api/trainer/verification/answer",
                         headers=headers,
                         json={"problem_id": p2, "answer": "20", "micro_skill": "vf_skill"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["correct"] is True

    after = await ac.get("/api/trainer/wrong-tasks", headers=headers)
    assert after.status_code == 200, after.text
    assert all(task["problem_id"] != p1 for task in after.json()["tasks"])

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    eng = create_async_engine(_TEST_URL)
    fac = async_sessionmaker(eng, expire_on_commit=False)
    async with fac() as s:
        res = (await s.execute(text(
            "SELECT resolved FROM recurring_errors WHERE student_id = :sid AND micro_skill = 'vf_failed_ms'"
        ), {"sid": sid})).scalar_one()
        closure_attempt = (await s.execute(text(
            "SELECT problem_id, answer_given, is_correct, source "
            "FROM attempts WHERE student_id = :sid AND source = 'closure'"
        ), {"sid": sid})).one()
    await eng.dispose()
    assert res is True
    assert tuple(closure_attempt) == (p2, "20", True, "closure")


@pytest.mark.asyncio
async def test_verification_answer_wrong_not_resolved(vclient):
    ac, token, p1, p2, sid = vclient
    headers = {"Authorization": f"Bearer {token}"}
    resp = await ac.post("/api/trainer/verification/answer",
                         headers=headers,
                         json={"problem_id": p2, "answer": "99", "micro_skill": "vf_skill"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["correct"] is False

    wrong_tasks = await ac.get("/api/trainer/wrong-tasks", headers=headers)
    assert wrong_tasks.status_code == 200, wrong_tasks.text
    assert any(task["problem_id"] == p1 for task in wrong_tasks.json()["tasks"])


@pytest.mark.asyncio
async def test_new_wrong_attempt_after_closure_reopens_task(vclient):
    ac, token, p1, p2, sid = vclient
    headers = {"Authorization": f"Bearer {token}"}
    closed = await ac.post(
        "/api/trainer/verification/answer",
        headers=headers,
        json={"problem_id": p2, "answer": "20", "micro_skill": "vf_skill"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["correct"] is True

    reopened = await ac.post(
        "/api/trainer/srez/answer",
        headers=headers,
        json={"problem_id": p1, "answer": "11", "elapsed_ms": 500},
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["is_correct"] is False

    wrong_tasks = await ac.get("/api/trainer/wrong-tasks", headers=headers)
    assert wrong_tasks.status_code == 200, wrong_tasks.text
    assert any(task["problem_id"] == p1 for task in wrong_tasks.json()["tasks"])

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    eng = create_async_engine(_TEST_URL)
    fac = async_sessionmaker(eng, expire_on_commit=False)
    async with fac() as s:
        resolved = (await s.execute(text(
            "SELECT resolved FROM recurring_errors "
            "WHERE student_id = :sid AND micro_skill = 'vf_failed_ms'"
        ), {"sid": sid})).scalar_one()
    await eng.dispose()
    assert resolved is False


@pytest.mark.asyncio
async def test_wrong_recorded_attempt_reopens_recurring_progress(vclient):
    """Любая новая неверная попытка через record_attempt снова открывает узел."""
    ac, token, _p1, p2, sid = vclient
    headers = {"Authorization": f"Bearer {token}"}

    closed = await ac.post(
        "/api/trainer/verification/answer",
        headers=headers,
        json={"problem_id": p2, "answer": "20", "micro_skill": "vf_skill"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["correct"] is True

    wrong = await ac.post(
        "/api/trainer/verification/answer",
        headers=headers,
        json={"problem_id": p2, "answer": "99", "micro_skill": "vf_skill"},
    )
    assert wrong.status_code == 200, wrong.text
    assert wrong.json()["correct"] is False

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    eng = create_async_engine(_TEST_URL)
    fac = async_sessionmaker(eng, expire_on_commit=False)
    async with fac() as s:
        resolved = (await s.execute(text(
            "SELECT resolved FROM recurring_errors "
            "WHERE student_id = :sid AND micro_skill = 'vf_failed_ms'"
        ), {"sid": sid})).scalar_one()
    await eng.dispose()
    assert resolved is False


@pytest.mark.asyncio
async def test_verification_start_no_token_401(vclient):
    ac, token, p1, p2, sid = vclient
    resp = await ac.post("/api/trainer/verification/start", json={"problem_id": p1})
    assert resp.status_code == 401
