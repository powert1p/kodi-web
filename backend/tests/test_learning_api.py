"""Сквозной API-маршрут урока: один следующий шаг, resume и честное mastery."""

from __future__ import annotations

import json
import os

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-chars")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from core.learning import load_problem_bank


_TEST_URL = os.getenv("TEST_DATABASE_URL")
_CONTENT_INDICES = (1764, 1525, 1765, 331)


async def _seed_learning_content(db_session) -> int:
    problems = load_problem_bank()
    await db_session.execute(
        text(
            "INSERT INTO topics (id, strand, name_ru, name_kz, order_idx) "
            "VALUES ('PC', 'RP', 'Проценты', 'Пайыздар', 0) "
            "ON CONFLICT (id) DO NOTHING"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO nodes "
            "(id, name_ru, name_kz, difficulty, topic_id, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES ('PC06', 'Смеси и концентрации', 'Қоспалар', 3, 'PC', 0.3, 0.05, 0.1) "
            "ON CONFLICT (id) DO NOTHING"
        )
    )
    for content_idx in _CONTENT_INDICES:
        problem = problems[content_idx]
        await db_session.execute(
            text(
                "INSERT INTO problems "
                "(content_idx, node_id, text_ru, answer, answer_type, difficulty, raw_score) "
                "VALUES (:content_idx, :node_id, :text_ru, :answer, :answer_type, :difficulty, :raw_score)"
            ),
            {
                "content_idx": content_idx,
                "node_id": problem["node_id"],
                "text_ru": problem["text_ru"],
                "answer": str(problem["answer"]),
                "answer_type": problem.get("answer_type"),
                "difficulty": problem.get("difficulty"),
                "raw_score": problem.get("raw_score"),
            },
        )

    student_id = 9715
    await db_session.execute(
        text(
            "INSERT INTO students "
            "(id, first_name, registered, lang, grade, created_at, diagnostic_complete) "
            "VALUES (:student_id, 'Аян', true, 'ru', 7, NOW(), true)"
        ),
        {"student_id": student_id},
    )
    await db_session.commit()
    return student_id


@pytest_asyncio.fixture
async def learning_client(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")

    student_id = await _seed_learning_content(db_session)
    from api.routes import _create_token

    token = _create_token(student_id)
    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_TEST_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    original_db_session = db_base.async_session
    original_routes_session = routes_module.async_session
    db_base.async_session = factory
    routes_module.async_session = factory

    from web import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client, token, student_id

    db_base.async_session = original_db_session
    routes_module.async_session = original_routes_session
    await engine.dispose()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _assert_no_answers(payload: dict) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "expected_answer" not in serialized
    assert "correct_answer" not in serialized


@pytest.mark.asyncio
async def test_lesson_mutations_require_explicit_lesson_id(learning_client):
    client, token, _ = learning_client
    headers = _headers(token)

    start = await client.post("/api/learning/start", headers=headers, json={})
    advance = await client.post("/api/learning/advance", headers=headers, json={})

    assert start.status_code == 422
    assert advance.status_code == 422


@pytest.mark.asyncio
async def test_current_path_and_start_expose_one_safe_next_action(learning_client):
    client, token, _ = learning_client
    headers = _headers(token)

    path_response = await client.get("/api/learning/path/current", headers=headers)
    assert path_response.status_code == 200
    path_payload = path_response.json()
    assert path_payload["path"]["id"] == "nish-preparation"
    assert path_payload["path"]["title"] == "Подготовка к НИШ"
    assert path_payload["path"]["current_block"]["id"] == "PC06"
    assert path_payload["path"]["current_block"]["title"] == "Смеси и концентрации"
    assert path_payload["lesson"]["id"] == "mixtures-1"
    assert path_payload["lesson"]["status"] == "not_started"
    assert path_payload["lesson"]["primary_action"]["label"] == "Начать урок"
    _assert_no_answers(path_payload)

    started = await client.post(
        "/api/learning/start",
        headers=headers,
        json={"lesson_id": "mixtures-1"},
    )
    assert started.status_code == 200
    state = started.json()
    assert state["status"] == "active"
    assert state["activity"]["id"] == "worked-dilution"
    assert state["activity"]["role"] == "worked"
    assert state["progress"] == {"current": 1, "total": 6, "completed": 0}
    _assert_no_answers(state)


@pytest.mark.asyncio
async def test_wrong_answer_is_idempotent_and_restored_on_reload(
    learning_client,
    db_session,
):
    client, token, _ = learning_client
    headers = _headers(token)
    await client.post(
        "/api/learning/start",
        headers=headers,
        json={"lesson_id": "mixtures-1"},
    )
    advanced = await client.post(
        "/api/learning/advance",
        headers=headers,
        json={"lesson_id": "mixtures-1"},
    )
    assert advanced.status_code == 200
    assert advanced.json()["activity"]["id"] == "guided-substance"

    answer_body = {
        "lesson_id": "mixtures-1",
        "activity_id": "guided-substance",
        "activity_index": 1,
        "answer": "40",
        "client_attempt_id": "wrong-guided-1",
        "response_time_ms": 3100,
    }
    wrong = await client.post(
        "/api/learning/answer",
        headers=headers,
        json=answer_body,
    )
    assert wrong.status_code == 200
    wrong_state = wrong.json()
    assert wrong_state["feedback"]["is_correct"] is False
    assert wrong_state["activity"]["id"] == "guided-substance"
    assert wrong_state["activity"]["last_answer"] == "40"
    assert wrong_state["activity"]["support_level"] == 1
    assert "10%" in wrong_state["activity"]["support"]
    _assert_no_answers(wrong_state)

    duplicate = await client.post(
        "/api/learning/answer",
        headers=headers,
        json=answer_body,
    )
    assert duplicate.status_code == 200
    count = (
        await db_session.execute(
            text(
                "SELECT count(*) FROM learning_attempts "
                "WHERE client_attempt_id = 'wrong-guided-1'"
            )
        )
    ).scalar_one()
    assert count == 1

    resumed = await client.post(
        "/api/learning/start",
        headers=headers,
        json={"lesson_id": "mixtures-1"},
    )
    resume_state = resumed.json()
    assert resume_state["activity"]["id"] == "guided-substance"
    assert resume_state["activity"]["last_answer"] == "40"
    assert resume_state["activity"]["support_level"] == 1

    path_response = await client.get("/api/learning/path/current", headers=headers)
    assert path_response.json()["lesson"]["primary_action"]["label"] == "Продолжить"


@pytest.mark.asyncio
async def test_complete_route_records_only_independent_work_in_mastery(
    learning_client,
    db_session,
):
    client, token, student_id = learning_client
    headers = _headers(token)
    await client.post(
        "/api/learning/start",
        headers=headers,
        json={"lesson_id": "mixtures-1"},
    )
    advanced = await client.post(
        "/api/learning/advance",
        headers=headers,
        json={"lesson_id": "mixtures-1"},
    )
    state = advanced.json()

    route = [
        ("20", "guided-substance-correct"),
        ("250", "guided-total-correct"),
        ("8", "guided-concentration-correct"),
        ("15", "independent-correct"),
        ("12", "transfer-wrong"),
        ("30", "transfer-correct"),
    ]
    for answer, attempt_id in route:
        response = await client.post(
            "/api/learning/answer",
            headers=headers,
            json={
                "lesson_id": "mixtures-1",
                "activity_id": state["activity"]["id"],
                "activity_index": state["progress"]["completed"],
                "answer": answer,
                "client_attempt_id": attempt_id,
                "response_time_ms": 2400,
            },
        )
        assert response.status_code == 200
        state = response.json()

    assert state is not None
    assert state["status"] == "completed"
    assert state["activity"] is None
    assert state["result"]["independent_completed"] == 2
    assert state["result"]["transfer_completed"] == 1
    assert state["result"]["without_support"] == 1
    assert state["result"]["evidence_label"] == (
        "2 самостоятельных задания, одно — с переносом на новую ситуацию"
    )
    _assert_no_answers(state)

    learning_attempts = (
        await db_session.execute(
            text(
                "SELECT count(*) FROM learning_attempts la "
                "JOIN learning_sessions ls ON ls.id = la.session_id "
                "WHERE ls.student_id = :student_id"
            ),
            {"student_id": student_id},
        )
    ).scalar_one()
    assert learning_attempts == 6

    mastery_attempts = (
        await db_session.execute(
            text(
                "SELECT count(*) FROM attempts "
                "WHERE student_id = :student_id AND source = 'learning'"
            ),
            {"student_id": student_id},
        )
    ).scalar_one()
    assert mastery_attempts == 3

    path_response = await client.get("/api/learning/path/current", headers=headers)
    path_payload = path_response.json()
    assert path_payload["lesson"]["status"] == "completed"
    assert path_payload["path"]["current_block"]["completed_lessons"] == 1
    assert path_payload["lesson"]["primary_action"]["label"] == "Посмотреть результат"


@pytest.mark.asyncio
async def test_stale_tab_answer_cannot_advance_current_activity(
    learning_client,
    db_session,
):
    """Ответ из отставшей вкладки не оценивается как следующая activity."""
    client, token, _ = learning_client
    headers = _headers(token)
    await client.post(
        "/api/learning/start",
        headers=headers,
        json={"lesson_id": "mixtures-1"},
    )
    await client.post(
        "/api/learning/advance",
        headers=headers,
        json={"lesson_id": "mixtures-1"},
    )

    current = await client.post(
        "/api/learning/answer",
        headers=headers,
        json={
            "lesson_id": "mixtures-1",
            "activity_id": "guided-substance",
            "activity_index": 1,
            "answer": "20",
            "client_attempt_id": "tab-a-guided-correct",
        },
    )
    assert current.status_code == 200
    assert current.json()["activity"]["id"] == "guided-total"

    stale = await client.post(
        "/api/learning/answer",
        headers=headers,
        json={
            "lesson_id": "mixtures-1",
            "activity_id": "guided-substance",
            "activity_index": 1,
            # 250 было бы верным для уже текущей guided-total.
            "answer": "250",
            "client_attempt_id": "tab-b-stale-distinct-id",
        },
    )

    assert stale.status_code == 409
    detail = stale.json()["detail"]
    assert detail["code"] == "stale_activity"
    assert detail["state"]["activity"]["id"] == "guided-total"
    attempt_count = (
        await db_session.execute(
            text(
                "SELECT count(*) FROM learning_attempts "
                "WHERE client_attempt_id IN "
                "('tab-a-guided-correct', 'tab-b-stale-distinct-id')"
            )
        )
    ).scalar_one()
    assert attempt_count == 1
