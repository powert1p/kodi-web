"""Rate-limit контракты для класса за общим NAT и защиты PIN."""

from __future__ import annotations

import hashlib
import os
import time

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-chars")

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from starlette.requests import Request


_TEST_URL = os.getenv("TEST_DATABASE_URL")
_PIN = "7319"
_PIN_HASH = hashlib.sha256(_PIN.encode()).hexdigest()


@pytest_asyncio.fixture
async def auth_client(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")

    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_TEST_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    original_db_session = db_base.async_session
    original_routes_session = routes_module.async_session
    db_base.async_session = factory
    routes_module.async_session = factory
    routes_module.limiter.reset()
    routes_module._reset_login_failure_limiter()

    from web import app

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client
    finally:
        routes_module.limiter.reset()
        routes_module._reset_login_failure_limiter()
        db_base.async_session = original_db_session
        routes_module.async_session = original_routes_session
        await engine.dispose()


async def _insert_students(db_session, phones: list[str]) -> None:
    for offset, phone in enumerate(phones, start=1):
        await db_session.execute(
            text(
                "INSERT INTO students "
                "(id, first_name, phone, pin_hash, registered, lang, created_at, diagnostic_complete) "
                "VALUES (:id, :name, :phone, :pin_hash, true, 'ru', NOW(), false)"
            ),
            {
                "id": 880_000 + offset,
                "name": f"Ученик {offset}",
                "phone": phone,
                "pin_hash": _PIN_HASH,
            },
        )
    await db_session.commit()


@pytest.mark.asyncio
async def test_ten_students_can_login_from_one_classroom_ip(auth_client, db_session):
    """Успешные входы разных детей не делят старый лимит 5/minute."""
    phones = [f"+77010000{index:03d}" for index in range(10)]
    await _insert_students(db_session, phones)

    responses = [
        await auth_client.post(
            "/api/auth/phone/login",
            json={"phone": phone, "pin": _PIN},
        )
        for phone in phones
    ]

    assert [response.status_code for response in responses] == [200] * len(phones)


@pytest.mark.asyncio
async def test_success_clears_phone_failure_window(auth_client, db_session):
    """Корректный PIN после нескольких ошибок сбрасывает узкий fail-only bucket."""
    phone = "+77019990001"
    await _insert_students(db_session, [phone])

    for _ in range(4):
        response = await auth_client.post(
            "/api/auth/phone/login",
            json={"phone": phone, "pin": "0000"},
        )
        assert response.status_code == 401

    success = await auth_client.post(
        "/api/auth/phone/login",
        json={"phone": phone, "pin": _PIN},
    )
    assert success.status_code == 200

    for _ in range(5):
        response = await auth_client.post(
            "/api/auth/phone/login",
            json={"phone": phone, "pin": "0000"},
        )
        assert response.status_code == 401

    blocked = await auth_client.post(
        "/api/auth/phone/login",
        json={"phone": phone, "pin": "0000"},
    )
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"]


@pytest.mark.asyncio
async def test_pin_failure_windows_are_isolated_by_phone(auth_client, db_session):
    """Ошибки одного ребёнка не блокируют другого за тем же NAT."""
    phones = ["+77019990002", "+77019990003"]
    await _insert_students(db_session, phones)

    for phone in phones:
        for _ in range(5):
            response = await auth_client.post(
                "/api/auth/phone/login",
                json={"phone": phone, "pin": "0000"},
            )
            assert response.status_code == 401


@pytest.mark.asyncio
async def test_telegram_auth_does_not_block_eleventh_classmate(auth_client):
    """Telegram secondary login тоже выдерживает classroom NAT burst."""
    responses = [
        await auth_client.post(
            "/api/auth/telegram",
            json={
                "id": 990_000 + index,
                "first_name": "Ученик",
                "auth_date": int(time.time()),
                "hash": "invalid-synthetic-hash",
            },
        )
        for index in range(11)
    ]

    assert [response.status_code for response in responses] == [401] * len(responses)


def test_registration_uses_hourly_account_creation_ceiling() -> None:
    """Саморегистрацию нельзя превратить в быстрый генератор AI-аккаунтов."""
    from api.routes import limiter

    limits = limiter._route_limits["api.routes.auth_phone_register"]
    assert [str(item.limit) for item in limits] == ["30 per 1 hour"]


@pytest.mark.asyncio
async def test_pin_bcrypt_work_is_offloaded_from_event_loop(
    auth_client,
    monkeypatch,
) -> None:
    """bcrypt hash/check не блокируют single-worker event loop."""
    import api.routes as routes_module

    original_to_thread = routes_module.asyncio.to_thread
    offloaded: list[str] = []

    async def _observed_to_thread(function, /, *args, **kwargs):
        offloaded.append(function.__name__)
        return await original_to_thread(function, *args, **kwargs)

    monkeypatch.setattr(routes_module.asyncio, "to_thread", _observed_to_thread)

    register = await auth_client.post(
        "/api/auth/phone/register",
        json={
            "phone": "+77018880001",
            "name": "Тест",
            "pin": _PIN,
            "grade": 6,
        },
    )
    assert register.status_code == 200, register.text

    login = await auth_client.post(
        "/api/auth/phone/login",
        json={"phone": "+77018880001", "pin": _PIN},
    )
    assert login.status_code == 200, login.text
    assert "_hash_pin" in offloaded
    assert "_verify_pin" in offloaded


@pytest.mark.asyncio
async def test_ai_ip_ceiling_survives_rotating_student_tokens(auth_client) -> None:
    """Новые аккаунты не умножают общий classroom IP budget для LLM."""
    from api.routes import _create_token

    responses = []
    for student_id in range(910_000, 910_061):
        responses.append(
            await auth_client.post(
                "/api/trainer/tutor/chat",
                headers={"Authorization": f"Bearer {_create_token(student_id)}"},
                json={"problem_id": 1, "message": "Помоги"},
            )
        )

    assert [response.status_code for response in responses[:60]] == [401] * 60
    assert responses[60].status_code == 429


async def _insert_report_problem(db_session) -> tuple[int, int]:
    student_id = 920_001
    await db_session.execute(
        text(
            "INSERT INTO students "
            "(id, first_name, registered, lang, created_at, diagnostic_complete) "
            "VALUES (:sid, 'Ученик', true, 'ru', NOW(), false)"
        ),
        {"sid": student_id},
    )
    await db_session.execute(
        text(
            "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES ('SAFE01', 'Тест', 'Тест', 0.3, 0.05, 0.1)"
        )
    )
    problem_id = (
        await db_session.execute(
            text(
                "INSERT INTO problems (node_id, text_ru, answer) "
                "VALUES ('SAFE01', 'Сколько будет 2 + 2?', '4') RETURNING id"
            )
        )
    ).scalar_one()
    await db_session.commit()
    return student_id, problem_id


@pytest.mark.asyncio
async def test_problem_report_never_mutates_canonical_answer(
    auth_client,
    db_session,
    monkeypatch,
) -> None:
    """Жалоба ребёнка только ставит задачу на review, даже если AI сказал YES."""
    import api.routes as routes_module

    student_id, problem_id = await _insert_report_problem(db_session)
    ai_called = False

    async def _unsafe_ai_yes(*args, **kwargs):
        nonlocal ai_called
        ai_called = True
        return True, "ответ ребёнка якобы верный"

    async def _skip_notification(*args, **kwargs):
        return None

    monkeypatch.setattr(routes_module, "check_with_claude", _unsafe_ai_yes, raising=False)
    monkeypatch.setattr(routes_module, "_notify_report", _skip_notification)

    response = await auth_client.post(
        "/api/practice/report",
        headers={"Authorization": f"Bearer {routes_module._create_token(student_id)}"},
        json={
            "problem_id": problem_id,
            "reason": "wrong_answer",
            "student_answer": "999",
        },
    )
    assert response.status_code == 200, response.text
    await routes_module.asyncio.sleep(0)

    problem_answer = (
        await db_session.execute(
            text("SELECT answer FROM problems WHERE id = :pid"),
            {"pid": problem_id},
        )
    ).scalar_one()
    report = (
        await db_session.execute(
            text(
                "SELECT status, correct_answer FROM problem_reports "
                "WHERE problem_id = :pid"
            ),
            {"pid": problem_id},
        )
    ).one()

    assert ai_called is False
    assert problem_answer == "4"
    assert report.status == "open"
    assert report.correct_answer == "4"


@pytest.mark.asyncio
async def test_problem_report_has_student_and_shared_ip_ceilings(
    auth_client,
    db_session,
    monkeypatch,
) -> None:
    """Один ребёнок ограничен 5/min, а ротация JWT — общими 30/min на IP."""
    import api.routes as routes_module

    async def _skip_notification(*args, **kwargs):
        return None

    monkeypatch.setattr(routes_module, "_notify_report", _skip_notification)
    student_id, problem_id = await _insert_report_problem(db_session)
    token = routes_module._create_token(student_id)

    own_responses = [
        await auth_client.post(
            "/api/practice/report",
            headers={"Authorization": f"Bearer {token}"},
            json={"problem_id": problem_id, "reason": "error"},
        )
        for _ in range(6)
    ]
    assert [response.status_code for response in own_responses[:5]] == [200] * 5
    assert own_responses[5].status_code == 429

    routes_module.limiter.reset()
    rotated = []
    for rotated_id in range(930_000, 930_031):
        rotated.append(
            await auth_client.post(
                "/api/practice/report",
                headers={
                    "Authorization": f"Bearer {routes_module._create_token(rotated_id)}"
                },
                json={"problem_id": problem_id, "reason": "error"},
            )
        )
    assert [response.status_code for response in rotated[:30]] == [401] * 30
    assert rotated[30].status_code == 429


@pytest.mark.asyncio
async def test_problem_report_rejects_oversized_text(auth_client) -> None:
    """Текст жалобы ограничен до любых DB/Telegram операций."""
    from api.routes import _create_token

    response = await auth_client.post(
        "/api/practice/report",
        headers={"Authorization": f"Bearer {_create_token(940_001)}"},
        json={
            "problem_id": 1,
            "reason": "x" * 31,
            "student_answer": "y" * 501,
        },
    )
    assert response.status_code == 422


def _request(path: str, *, authorization: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": headers,
            "client": ("203.0.113.10", 41234),
            "scheme": "https",
            "server": ("testserver", 443),
            "query_string": b"",
        }
    )


def test_authenticated_rate_limit_key_is_per_student() -> None:
    """AI и learning buckets разделяются по student, а не по school IP."""
    from api.routes import _create_token, _rate_limit_key

    token_one = _create_token(101)
    token_two = _create_token(202)

    first = _rate_limit_key(
        _request(
            "/api/trainer/tutor/chat",
            authorization=f"Bearer {token_one}",
        )
    )
    second = _rate_limit_key(
        _request(
            "/api/trainer/tutor/chat",
            authorization=f"Bearer {token_two}",
        )
    )

    assert first != second
    assert first.startswith("student:")
    assert second.startswith("student:")


def test_auth_and_malformed_tokens_keep_ip_bucket() -> None:
    """Auth routes и мусорный JWT нельзя вывести из IP ceiling поддельным sub."""
    from api.routes import JWT_ALGORITHM, _rate_limit_key

    forged = jwt.encode(
        {"sub": "101", "exp": 4_102_444_800},
        "attacker-secret-that-is-at-least-32-characters",
        algorithm=JWT_ALGORITHM,
    )

    auth_key = _rate_limit_key(
        _request(
            "/api/auth/phone/login",
            authorization=f"Bearer {forged}",
        )
    )
    malformed_key = _rate_limit_key(
        _request(
            "/api/trainer/tutor/chat",
            authorization=f"Bearer {forged}",
        )
    )

    assert auth_key == "ip:203.0.113.10"
    assert malformed_key == "ip:203.0.113.10"
