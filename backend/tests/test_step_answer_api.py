"""Серверная проверка typed-answer для лесенки без утечки эталона."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-chars")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def step_answer_client(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")

    student_id = 9701
    decomp_idx = 99701
    step_n = 1

    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false)"
    ), {"sid": student_id})
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('SA01', 'Дроби', 'Дроби', 0.3, 0.05, 0.1)"
    ))
    problem_id = (await db_session.execute(text(
        "INSERT INTO problems (content_idx, node_id, text_ru, answer, answer_type) "
        "VALUES (:idx, 'SA01', 'Сократи дробь 2/4', '1/2', 'fraction') RETURNING id"
    ), {"idx": decomp_idx})).scalar_one()
    await db_session.execute(text(
        "INSERT INTO decomposition_problems "
        "(idx, node_id, answer, primary_micro_skill, all_steps_verified, needs_review, problems_db_id) "
        "VALUES (:idx, 'SA01', '1/2', 'fraction_reduce', true, false, :pid)"
    ), {"idx": decomp_idx, "pid": problem_id})
    await db_session.execute(text(
        "INSERT INTO problem_steps (decomp_idx, n, instruction_ru, micro_skill, expected_value) "
        "VALUES (:idx, :n, 'Сократи 2/4', 'fraction_reduce', '1/2'), "
        "       (:idx, 2, 'Запиши результат десятичной дробью', 'fraction_reduce', '0.5')"
    ), {"idx": decomp_idx, "n": step_n})
    await db_session.execute(text(
        "INSERT INTO problem_fingerprints (decomp_idx, micro_skill, wrong_answer, mistake_ru) "
        "VALUES (:idx, 'fraction_reduce', '2/4', 'Раздели числитель и знаменатель на общий делитель')"
    ), {"idx": decomp_idx})
    await db_session.commit()

    from api.routes import _create_token
    token = _create_token(student_id)

    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_TEST_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    original_db = db_base.async_session
    original_routes = routes_module.async_session
    db_base.async_session = factory
    routes_module.async_session = factory

    from web import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client, token, student_id, problem_id, decomp_idx, step_n

    db_base.async_session = original_db
    routes_module.async_session = original_routes
    await engine.dispose()


@pytest.mark.asyncio
async def test_step_answer_grades_on_server_and_records_attempt(step_answer_client):
    client, token, student_id, problem_id, decomp_idx, step_n = step_answer_client
    response = await client.post(
        "/api/trainer/step-answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id,
            "decomp_idx": decomp_idx,
            "step_n": step_n,
            "answer": "0,5",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"correct": True, "hint": None, "step_n": step_n}
    assert "expected" not in response.text

    from db.base import async_session
    async with async_session() as session:
        row = (await session.execute(text(
            "SELECT problem_id, decomp_idx, step_n, is_correct, source "
            "FROM drill_step_attempts WHERE student_id = :sid"
        ), {"sid": student_id})).one()
    assert tuple(row) == (problem_id, decomp_idx, step_n, True, "input")

    state = await client.get(
        f"/api/trainer/drill-state?problem_id={problem_id}&decomp_idx={decomp_idx}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert state.status_code == 200, state.text
    assert state.json() == {"solved_step_ns": [step_n]}


@pytest.mark.asyncio
async def test_step_answer_wrong_returns_step_grounded_hint_without_fingerprint_leak(
    step_answer_client,
):
    client, token, _student_id, problem_id, decomp_idx, step_n = step_answer_client
    response = await client.post(
        "/api/trainer/step-answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id,
            "decomp_idx": decomp_idx,
            "step_n": step_n,
            "answer": "2/4/2",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["correct"] is False
    assert body["hint"] == "Проверь этот шаг ещё раз: Сократи 2/4"
    assert "1/2" not in response.text


@pytest.mark.asyncio
async def test_step_answer_does_not_accept_final_equation_for_an_earlier_stage(
    step_answer_client,
):
    client, token, _student_id, problem_id, decomp_idx, step_n = step_answer_client
    from db.base import async_session

    async with async_session() as session:
        await session.execute(
            text(
                "UPDATE problem_steps "
                "SET expected_value = '0.05x+(500-x)*0.15=40' "
                "WHERE decomp_idx = :didx AND n = :step_n"
            ),
            {"didx": decomp_idx, "step_n": step_n},
        )
        await session.commit()

    response = await client.post(
        "/api/trainer/step-answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id,
            "decomp_idx": decomp_idx,
            "step_n": step_n,
            "answer": "x=350",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "correct": False,
        "hint": "Проверь этот шаг ещё раз: Сократи 2/4",
        "step_n": step_n,
    }
    state = await client.get(
        f"/api/trainer/drill-state?problem_id={problem_id}&decomp_idx={decomp_idx}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert state.status_code == 200, state.text
    assert state.json() == {"solved_step_ns": []}


@pytest.mark.asyncio
async def test_step_answer_wrong_sanitizes_answer_leaking_instruction(step_answer_client):
    client, token, _student_id, problem_id, decomp_idx, step_n = step_answer_client
    from db.base import async_session

    async with async_session() as session:
        await session.execute(text(
            "UPDATE problem_steps SET instruction_ru = 'Сократи 2/4 = 1/2' "
            "WHERE decomp_idx = :didx AND n = :step_n"
        ), {"didx": decomp_idx, "step_n": step_n})
        await session.commit()

    response = await client.post(
        "/api/trainer/step-answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id,
            "decomp_idx": decomp_idx,
            "step_n": step_n,
            "answer": "2/4/2",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["hint"] == "Проверь этот шаг ещё раз: Сократи 2/4."
    assert "1/2" not in response.text


@pytest.mark.asyncio
async def test_step_answer_rejects_decomp_from_another_problem(step_answer_client):
    client, token, _student_id, problem_id, decomp_idx, step_n = step_answer_client
    response = await client.post(
        "/api/trainer/step-answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id + 999,
            "decomp_idx": decomp_idx,
            "step_n": step_n,
            "answer": "1/2",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_step_answer_fallback_grades_problem_when_decomp_is_missing(step_answer_client):
    client, token, _student_id, _problem_id, _decomp_idx, step_n = step_answer_client
    from db.base import async_session

    async with async_session() as session:
        problem_id = (await session.execute(text(
            "INSERT INTO problems (node_id, text_ru, answer, answer_type) "
            "VALUES ('SA01', 'Сократи дробь 4/8', '1/2', 'fraction') RETURNING id"
        ))).scalar_one()
        await session.commit()

    response = await client.post(
        "/api/trainer/step-answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id,
            "decomp_idx": None,
            "step_n": step_n,
            "answer": "2/4",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["correct"] is True


@pytest.mark.asyncio
async def test_step_answer_fallback_cannot_bypass_published_steps(step_answer_client):
    client, token, _student_id, problem_id, _decomp_idx, step_n = step_answer_client
    response = await client.post(
        "/api/trainer/step-answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id,
            "decomp_idx": None,
            "step_n": step_n,
            "answer": "1/2",
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Для задачи доступно пошаговое решение"


@pytest.mark.asyncio
async def test_step_answer_validates_payload(step_answer_client):
    client, token, _student_id, problem_id, decomp_idx, step_n = step_answer_client
    response = await client.post(
        "/api/trainer/step-answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id,
            "decomp_idx": decomp_idx,
            "step_n": step_n,
            "answer": " " * 4,
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_step_answer_rejects_skipping_previous_step(step_answer_client):
    client, token, _student_id, problem_id, decomp_idx, _step_n = step_answer_client
    response = await client.post(
        "/api/trainer/step-answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id,
            "decomp_idx": decomp_idx,
            "step_n": 2,
            "answer": "0.5",
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_step_answer_allows_next_step_after_previous_is_solved(step_answer_client):
    client, token, _student_id, problem_id, decomp_idx, step_n = step_answer_client
    first = await client.post(
        "/api/trainer/step-answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id,
            "decomp_idx": decomp_idx,
            "step_n": step_n,
            "answer": "1/2",
        },
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        "/api/trainer/step-answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id,
            "decomp_idx": decomp_idx,
            "step_n": 2,
            "answer": "0,5",
        },
    )
    assert second.status_code == 200, second.text
    assert second.json() == {"correct": True, "hint": None, "step_n": 2}

    state = await client.get(
        f"/api/trainer/drill-state?problem_id={problem_id}&decomp_idx={decomp_idx}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert state.json() == {"solved_step_ns": [1, 2]}
