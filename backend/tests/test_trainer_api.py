"""Интеграционные тесты HTTP-роутов тренажёра ошибок (Task 9).

Паттерн: httpx ASGITransport + реальная тест-БД (TEST_DATABASE_URL) + Bearer-токен,
минтированный через _create_token из api/routes.py.

Сценарии:
  1. GET /api/trainer/wrong-tasks → 200 с tasks (seeded неверные попытки).
  2. GET /api/trainer/analytics   → 200 с my_top (seeded recurring_errors).
  3. Без токена → 401 на обоих эндпоинтах.
  4. При owner_student_id == student_id → global_top появляется в analytics.
"""

from __future__ import annotations

import os

# JWT_SECRET задаётся в conftest.py ДО импорта core.config
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")

# ── вспомогательные seed-функции ─────────────────────────────────────────────


async def _seed_student_api(session, student_id: int) -> None:
    """Вставляет студента."""
    await session.execute(
        text(
            "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
            "VALUES (:sid, true, 'ru', NOW(), false) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"sid": student_id},
    )


async def _seed_node_api(session, node_id: str, name_ru: str) -> None:
    """Вставляет узел графа."""
    await session.execute(
        text(
            "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES (:nid, :name, :name, 0.3, 0.05, 0.1) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"nid": node_id, "name": name_ru},
    )


async def _seed_problem_api(session, node_id: str, text_ru: str, answer: str) -> int:
    """Вставляет задачу, возвращает её id."""
    row = await session.execute(
        text(
            "INSERT INTO problems (node_id, text_ru, answer) "
            "VALUES (:nid, :txt, :ans) RETURNING id"
        ),
        {"nid": node_id, "txt": text_ru, "ans": answer},
    )
    return row.scalar_one()


async def _seed_attempt_api(
    session,
    student_id: int,
    problem_id: int,
    node_id: str,
    answer_given: str,
    source: str = "diagnostic",
) -> None:
    """Вставляет неверную попытку."""
    await session.execute(
        text(
            "INSERT INTO attempts "
            "(student_id, problem_id, node_id, answer_given, is_correct, source, created_at) "
            "VALUES (:sid, :pid, :nid, :ans, false, :src, NOW())"
        ),
        {
            "sid": student_id,
            "pid": problem_id,
            "nid": node_id,
            "ans": answer_given,
            "src": source,
        },
    )


async def _seed_recurring_error(
    session,
    student_id: int,
    micro_skill: str,
    error_count: int,
    node_id: str = "TR01",
    last_cause_text: str | None = None,
) -> None:
    """Вставляет запись recurring_errors."""
    await session.execute(
        text(
            "INSERT INTO recurring_errors "
            "(student_id, micro_skill, node_id, error_count, last_cause_text, resolved, created_at) "
            "VALUES (:sid, :ms, :nid, :cnt, :cause, false, NOW()) "
            "ON CONFLICT (student_id, micro_skill) DO UPDATE "
            "SET error_count = :cnt"
        ),
        {
            "sid": student_id,
            "ms": micro_skill,
            "nid": node_id,
            "cnt": error_count,
            "cause": last_cause_text,
        },
    )


# ── фикстура: seeded тест-сессия + ASGI-клиент ───────────────────────────────


@pytest_asyncio.fixture
async def client_with_student(db_session):
    """
    Минтирует студента + 2 неверные попытки + 2 recurring_errors.
    Возвращает (AsyncClient, student_id, token) с поднятым ASGI-транспортом.
    Использует web.app (тот же, что в prod) с переопределённой БД через monkeypatch
    на async_session в db.base — app читает сессию из модуля, не из engine напрямую.
    """
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан — пропуск интеграционных тестов")

    STUDENT_ID = 7001
    NODE = "TR01"

    # Сид данных
    await _seed_student_api(db_session, STUDENT_ID)
    await _seed_node_api(db_session, NODE, "Тренажёр-тест")

    pid1 = await _seed_problem_api(db_session, NODE, "Задача API-1", "10")
    pid2 = await _seed_problem_api(db_session, NODE, "Задача API-2", "20")

    await _seed_attempt_api(db_session, STUDENT_ID, pid1, NODE, "9", source="diagnostic")
    await _seed_attempt_api(db_session, STUDENT_ID, pid2, NODE, "19", source="exam")

    await _seed_recurring_error(db_session, STUDENT_ID, "int_add", 5, NODE, "Перепутал знак")
    await _seed_recurring_error(db_session, STUDENT_ID, "frac_div", 3, NODE, "Перевернул дробь")

    await db_session.commit()

    # Минтируем токен через хелпер из routes.py (не дублируем JWT-логику)
    from api.routes import _create_token
    token = _create_token(STUDENT_ID)

    # Переопределяем async_session в обоих модулях — db.base и api.routes —
    # потому что routes.py импортирует async_session напрямую (bound name),
    # поэтому патч только db_base недостаточен.
    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    test_engine = create_async_engine(_TEST_URL)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    original_db_session = db_base.async_session
    original_routes_session = routes_module.async_session

    db_base.async_session = test_session_factory
    routes_module.async_session = test_session_factory

    from web import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac, STUDENT_ID, token

    # Восстанавливаем оригинальные async_session
    db_base.async_session = original_db_session
    routes_module.async_session = original_routes_session
    await test_engine.dispose()


# ── тест 1: wrong-tasks → 200 с задачами ─────────────────────────────────────


@pytest.mark.asyncio
async def test_wrong_tasks_returns_200(client_with_student):
    """GET /api/trainer/wrong-tasks → 200, tasks не пустые."""
    client, student_id, token = client_with_student

    resp = await client.get(
        "/api/trainer/wrong-tasks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Ожидался 200, получен {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "tasks" in body, "Ответ должен содержать ключ 'tasks'"
    assert isinstance(body["tasks"], list)
    assert len(body["tasks"]) >= 2, f"Ожидалось >=2 задач, получено {len(body['tasks'])}"

    # Проверяем структуру первой задачи
    task = body["tasks"][0]
    for field in ("id", "problem_id", "node_id", "topic_label", "statement", "answer", "state", "wrong_answer", "mastery", "steps"):
        assert field in task, f"В задаче отсутствует поле '{field}'"


# ── тест 2: wrong-tasks без токена → 401 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_wrong_tasks_no_token_401(client_with_student):
    """GET /api/trainer/wrong-tasks без Authorization → 401."""
    client, _, _ = client_with_student

    resp = await client.get("/api/trainer/wrong-tasks")
    assert resp.status_code == 401, f"Ожидался 401, получен {resp.status_code}"


# ── тест 3: analytics → 200 с my_top ────────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_returns_my_top(client_with_student):
    """GET /api/trainer/analytics → 200, my_top содержит seeded ошибки."""
    client, student_id, token = client_with_student

    resp = await client.get(
        "/api/trainer/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Ожидался 200, получен {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "my_top" in body, "Ответ должен содержать ключ 'my_top'"
    assert isinstance(body["my_top"], list)
    assert len(body["my_top"]) >= 2, f"Ожидалось >=2 записей my_top, получено {len(body['my_top'])}"

    # Проверяем структуру первой записи
    item = body["my_top"][0]
    for field in ("micro_skill", "error_count", "node_id"):
        assert field in item, f"В my_top-записи отсутствует поле '{field}'"

    # Первая запись — int_add (error_count=5 > frac_div error_count=3)
    assert body["my_top"][0]["micro_skill"] == "int_add"
    assert body["my_top"][0]["error_count"] == 5

    # global_top НЕ должен присутствовать для обычного студента
    assert "global_top" not in body or body.get("global_top") is None


# ── тест 4: analytics без токена → 401 ───────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_no_token_401(client_with_student):
    """GET /api/trainer/analytics без Authorization → 401."""
    client, _, _ = client_with_student

    resp = await client.get("/api/trainer/analytics")
    assert resp.status_code == 401, f"Ожидался 401, получен {resp.status_code}"


# ── тест 5: owner → global_top появляется ────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_owner_sees_global_top(client_with_student, monkeypatch):
    """Если student_id == settings.owner_student_id → global_top включён в ответ."""
    client, student_id, token = client_with_student

    from core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "owner_student_id", student_id)

    resp = await client.get(
        "/api/trainer/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Ожидался 200, получен {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "global_top" in body, "owner должен видеть global_top"
    assert isinstance(body["global_top"], list)
    assert len(body["global_top"]) >= 1

    # Проверяем структуру global_top-записи
    g_item = body["global_top"][0]
    for field in ("micro_skill", "total_errors", "students_affected"):
        assert field in g_item, f"В global_top-записи отсутствует поле '{field}'"


# ── тест 6: валидация параметров wrong-tasks ─────────────────────────────────


@pytest.mark.asyncio
async def test_wrong_tasks_invalid_params(client_with_student):
    """days=0 и limit=100 → 422 (Pydantic-валидация)."""
    client, _, token = client_with_student
    headers = {"Authorization": f"Bearer {token}"}

    resp_days = await client.get("/api/trainer/wrong-tasks?days=0", headers=headers)
    assert resp_days.status_code == 422, f"days=0 должен вернуть 422, получен {resp_days.status_code}"

    resp_limit = await client.get("/api/trainer/wrong-tasks?limit=100", headers=headers)
    assert resp_limit.status_code == 422, f"limit=100 должен вернуть 422, получен {resp_limit.status_code}"
