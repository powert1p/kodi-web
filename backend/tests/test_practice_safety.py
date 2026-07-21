"""Регрессии production-grade practice/BKT: mastery, retry и конкуренция."""

from __future__ import annotations

import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.bkt import record_attempt
from db.models import Attempt, Mastery, Problem


_TEST_URL = os.getenv("TEST_DATABASE_URL")
_STUDENT_ID = 74001
_NODE_ID = "PS01"


async def _seed_practice(db_session) -> int:
    await db_session.execute(
        text(
            "INSERT INTO students "
            "(id, registered, lang, created_at, diagnostic_complete, current_streak, longest_streak) "
            "VALUES (:sid, true, 'ru', NOW(), false, 0, 0)"
        ),
        {"sid": _STUDENT_ID},
    )
    await db_session.execute(
        text(
            "INSERT INTO nodes "
            "(id, name_ru, name_kz, difficulty, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES (:nid, 'Безопасная практика', 'Безопасная практика', 2, 0.3, 0.05, 0.1)"
        ),
        {"nid": _NODE_ID},
    )
    problem_id = (
        await db_session.execute(
            text(
                "INSERT INTO problems "
                "(node_id, text_ru, solution_ru, answer, answer_type, difficulty) "
                "VALUES (:nid, 'Сколько будет 6 × 7?', '6 × 7 = 42', '42', 'number', 2) "
                "RETURNING id"
            ),
            {"nid": _NODE_ID},
        )
    ).scalar_one()
    await db_session.commit()
    return int(problem_id)


@pytest_asyncio.fixture
async def practice_client(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    problem_id = await _seed_practice(db_session)

    import api.routes as routes_module
    import db.base as db_base
    from api.routes import _create_token, limiter as api_limiter
    from web import app

    engine = create_async_engine(_TEST_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    original_db_session = db_base.async_session
    original_routes_session = routes_module.async_session
    db_base.async_session = factory
    routes_module.async_session = factory
    api_limiter.reset()
    app.state.limiter.reset()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client, _create_token(_STUDENT_ID), problem_id, db_session
    finally:
        db_base.async_session = original_db_session
        routes_module.async_session = original_routes_session
        await engine.dispose()


@pytest.mark.asyncio
async def test_probability_alone_does_not_mark_topic_mastered(practice_client) -> None:
    client, token, _problem_id, db_session = practice_client
    await db_session.execute(
        text(
            "INSERT INTO mastery "
            "(student_id, node_id, p_mastery, attempts_total, attempts_correct) "
            "VALUES (:sid, :nid, 0.99, 1, 1)"
        ),
        {"sid": _STUDENT_ID, "nid": _NODE_ID},
    )
    await db_session.commit()

    response = await client.get(
        "/api/stats/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["mastered_count"] == 0

    from core.selector import _get_review_topics

    assert await _get_review_topics(db_session, _STUDENT_ID) == []

    await db_session.execute(
        text(
            "UPDATE mastery SET attempts_total = 4, attempts_correct = 3 "
            "WHERE student_id = :sid AND node_id = :nid"
        ),
        {"sid": _STUDENT_ID, "nid": _NODE_ID},
    )
    await db_session.commit()
    response = await client.get(
        "/api/stats/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.json()["mastered_count"] == 1
    assert await _get_review_topics(db_session, _STUDENT_ID) == [_NODE_ID]


@pytest.mark.asyncio
async def test_exam_head_stays_in_route_until_full_mastery(db_session) -> None:
    from core.exam import EXAM_HEADS
    from core.selector import _get_weak_exam_heads

    head = EXAM_HEADS[0]
    await db_session.execute(
        text(
            "INSERT INTO students "
            "(id, registered, lang, created_at, diagnostic_complete) "
            "VALUES (:sid, true, 'ru', NOW(), false)"
        ),
        {"sid": _STUDENT_ID},
    )
    await db_session.execute(
        text(
            "INSERT INTO nodes "
            "(id, name_ru, name_kz, difficulty, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES (:nid, 'Экзаменационная тема', 'Экзаменационная тема', 3, 0.3, 0.05, 0.1)"
        ),
        {"nid": head},
    )
    await db_session.execute(
        text(
            "INSERT INTO mastery "
            "(student_id, node_id, p_mastery, attempts_total, attempts_correct) "
            "VALUES (:sid, :nid, 0.99, 1, 1)"
        ),
        {"sid": _STUDENT_ID, "nid": head},
    )
    await db_session.commit()

    assert head in await _get_weak_exam_heads(db_session, _STUDENT_ID)

    await db_session.execute(
        text(
            "UPDATE mastery SET attempts_total = 3, attempts_correct = 3 "
            "WHERE student_id = :sid AND node_id = :nid"
        ),
        {"sid": _STUDENT_ID, "nid": head},
    )
    await db_session.commit()

    assert head not in await _get_weak_exam_heads(db_session, _STUDENT_ID)


@pytest.mark.asyncio
async def test_practice_answer_retry_is_exactly_once(practice_client) -> None:
    client, token, problem_id, db_session = practice_client
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "problem_id": problem_id,
        "answer": "42",
        "client_attempt_id": "practice-network-retry-1",
    }

    first = await client.post("/api/practice/answer", headers=headers, json=payload)
    second = await client.post("/api/practice/answer", headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    attempts = await db_session.scalar(
        select(func.count(Attempt.id)).where(Attempt.student_id == _STUDENT_ID)
    )
    mastery = await db_session.get(Mastery, (_STUDENT_ID, _NODE_ID))
    assert attempts == 1
    assert mastery is not None and mastery.attempts_total == 1

    conflict = await client.post(
        "/api/practice/answer",
        headers=headers,
        json={**payload, "answer": "41"},
    )
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_practice_answer_requires_client_attempt_id(practice_client) -> None:
    client, token, problem_id, _db_session = practice_client
    response = await client.post(
        "/api/practice/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"problem_id": problem_id, "answer": "42"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_practice_answer_rejects_unsupported_language(practice_client) -> None:
    client, token, problem_id, _db_session = practice_client
    response = await client.post(
        "/api/practice/answer?lang=en",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "problem_id": problem_id,
            "answer": "42",
            "client_attempt_id": "practice-invalid-lang-1",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_parallel_attempts_do_not_lose_mastery_updates(db_session) -> None:
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    problem_id = await _seed_practice(db_session)
    engine = create_async_engine(_TEST_URL, pool_size=10, max_overflow=0)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def submit(index: int) -> None:
        async with factory() as session:
            problem = await session.get(Problem, problem_id)
            assert problem is not None
            await record_attempt(
                session,
                _STUDENT_ID,
                problem,
                str(42 + index * 0),
                True,
                source="practice",
            )
            await session.commit()

    try:
        await asyncio.gather(*(submit(index) for index in range(8)))
    finally:
        await engine.dispose()

    db_session.expire_all()
    mastery = await db_session.get(Mastery, (_STUDENT_ID, _NODE_ID))
    attempt_count = await db_session.scalar(
        select(func.count(Attempt.id)).where(Attempt.student_id == _STUDENT_ID)
    )
    assert attempt_count == 8
    assert mastery is not None
    assert mastery.attempts_total == 8
    assert mastery.attempts_correct == 8
