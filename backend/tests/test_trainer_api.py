"""Интеграционные тесты HTTP-роутов тренажёра ошибок (Task 9 + Task 10).

Паттерн: httpx ASGITransport + реальная тест-БД (TEST_DATABASE_URL) + Bearer-токен,
минтированный через _create_token из api/routes.py.

Сценарии Task 9:
  1. GET /api/trainer/wrong-tasks → 200 с tasks (seeded неверные попытки).
  2. GET /api/trainer/analytics   → 200 с my_top (seeded recurring_errors).
  3. Без токена → 401 на обоих эндпоинтах.
  4. При owner_student_id == student_id → global_top появляется в analytics.

Сценарии Task 10 (POST /api/trainer/diagnose):
  7. 200 + body shape + файл фото записан на диск.
  8. Ровно одна строка в error_captures после POST.
  9. Строка в recurring_errors; error_count = 2 после второго POST.
  10. 503 когда diagnose_photo бросает LlmUnavailable.
  11. 404 для несуществующего problem_id.
"""

from __future__ import annotations

import io
import os
import struct

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
    for field in ("id", "problem_id", "node_id", "topic_label", "statement", "answer", "state", "wrong_answer", "mastery", "steps", "primary_micro_skill_label"):
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

    # Проверяем структуру первой записи (label_ru — человеческая подпись, §2.2)
    item = body["my_top"][0]
    for field in ("micro_skill", "label_ru", "error_count", "node_id"):
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


# ── тест 6.1: has_activity разводит новичка и ветерана ───────────────────────


@pytest_asyncio.fixture
async def client_fresh_student(db_session):
    """ASGI-клиент + СВЕЖИЙ студент БЕЗ единой попытки (для has_activity).

    Отдельно от client_with_student (тот сеет попытки) — здесь нужен именно
    ученик с чистой историей, чтобы поймать has_activity=false.
    """
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан — пропуск интеграционных тестов")

    STUDENT_ID = 7010
    await _seed_student_api(db_session, STUDENT_ID)
    await db_session.commit()

    from api.routes import _create_token
    token = _create_token(STUDENT_ID)

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

    db_base.async_session = original_db_session
    routes_module.async_session = original_routes_session
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_wrong_tasks_has_activity_flag(client_fresh_student, db_session):
    """has_activity: свежий ученик → false; после первой попытки → true.

    Ветеранский случай: даже ВЕРНАЯ попытка (открытых ошибок нет, список пуст)
    даёт has_activity=true — это и есть «всё разобрано», а не новичок.
    """
    client, student_id, token = client_fresh_student
    headers = {"Authorization": f"Bearer {token}"}

    # Свежий ученик: ни одной попытки → has_activity=false, список пуст.
    resp1 = await client.get("/api/trainer/wrong-tasks", headers=headers)
    assert resp1.status_code == 200, resp1.text
    body1 = resp1.json()
    assert body1["has_activity"] is False
    assert body1["tasks"] == []

    # Появилась активность (верная попытка среза): ошибок нет, но has_activity=true.
    await _seed_node_api(db_session, "TR01", "Тренажёр-тест")
    pid = await _seed_problem_api(db_session, "TR01", "Задача для активности", "10")
    await db_session.execute(
        text(
            "INSERT INTO attempts "
            "(student_id, problem_id, node_id, answer_given, is_correct, source, created_at) "
            "VALUES (:sid, :pid, :nid, '10', true, 'diagnostic', NOW())"
        ),
        {"sid": student_id, "pid": pid, "nid": "TR01"},
    )
    await db_session.commit()

    resp2 = await client.get("/api/trainer/wrong-tasks", headers=headers)
    assert resp2.status_code == 200, resp2.text
    body2 = resp2.json()
    assert body2["has_activity"] is True
    # Ветеран: активность есть, но открытых ошибок нет (попытка была верной).
    assert body2["tasks"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# Task 10: POST /api/trainer/diagnose (фото → диагностика → память ошибок)
# ═══════════════════════════════════════════════════════════════════════════════


def _make_tiny_jpeg() -> bytes:
    """Минимальный валидный JPEG-файл (1×1 px, серый) для тестов.

    Используем минималистичный JFIF без импорта Pillow в тест-среде.
    Байты получены из стандартного минимального JFIF-SOI + APPo + SOF + SOS.
    """
    # Минимальный 1x1 JPEG: SOI + APP0 + SOF0 + DHT + SOS + EOI
    # (68 байт, проходит проверку content_type)
    return bytes([
        0xFF, 0xD8,                          # SOI
        0xFF, 0xE0, 0x00, 0x10,              # APP0 marker + length
        0x4A, 0x46, 0x49, 0x46, 0x00,        # "JFIF\0"
        0x01, 0x01,                          # version
        0x00,                                # aspect ratio unit
        0x00, 0x01, 0x00, 0x01,             # Xdensity, Ydensity
        0x00, 0x00,                          # thumbnail
        0xFF, 0xDB, 0x00, 0x43, 0x00,        # DQT
        *([0x08] * 64),                      # quant table (flat)
        0xFF, 0xC0, 0x00, 0x0B,              # SOF0 + length
        0x08,                                # precision
        0x00, 0x01, 0x00, 0x01,             # height=1, width=1
        0x01,                                # components
        0x01, 0x11, 0x00,                   # component spec
        0xFF, 0xC4, 0x00, 0x1F, 0x00,        # DHT
        0x00, 0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0A, 0x0B,
        0xFF, 0xDA, 0x00, 0x08,              # SOS
        0x01, 0x01, 0x00, 0x00, 0x3F, 0x00,
        0x7F,                               # scan data
        0xFF, 0xD9,                          # EOI
    ])


@pytest_asyncio.fixture
async def client_for_diagnose(db_session, tmp_path, monkeypatch):
    """Фикстура для тестов /diagnose: студент + задача + неверная попытка + monkeypatch фото_dir."""
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан — пропуск интеграционных тестов")

    STUDENT_ID = 7002
    NODE = "TR02"

    await _seed_student_api(db_session, STUDENT_ID)
    await _seed_node_api(db_session, NODE, "Диагностика-тест")

    # /diagnose гейтится согласием родителя (Блок 1.0) — для этих тестов согласие уже дано
    await db_session.execute(
        text("UPDATE students SET photo_consent = true WHERE id = :sid"),
        {"sid": STUDENT_ID},
    )

    pid = await _seed_problem_api(db_session, NODE, "Найди x: 2x = 8", "4")

    # Каталог micro_skills — нужен для label_ru в ответе /diagnose (DESIGN_SYSTEM §2.2)
    await db_session.execute(
        text(
            "INSERT INTO micro_skills (code, label_ru) VALUES ('div_basic', 'Базовое деление') "
            "ON CONFLICT (code) DO NOTHING"
        )
    )

    # Вставляем неверную попытку для resolve_wrong_answer
    row = await db_session.execute(
        text(
            "INSERT INTO attempts "
            "(student_id, problem_id, node_id, answer_given, is_correct, source, created_at) "
            "VALUES (:sid, :pid, :nid, :ans, false, 'diagnostic', NOW()) "
            "RETURNING id"
        ),
        {"sid": STUDENT_ID, "pid": pid, "nid": NODE, "ans": "8"},
    )
    attempt_id = row.scalar_one()
    await db_session.commit()

    from api.routes import _create_token
    token = _create_token(STUDENT_ID)

    # Переопределяем photo_dir на tmp_path (изоляция файловой системы)
    from core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "photo_dir", str(tmp_path))

    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    test_engine = create_async_engine(_TEST_URL)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    original_db = db_base.async_session
    original_routes = routes_module.async_session

    db_base.async_session = test_session_factory
    routes_module.async_session = test_session_factory

    from web import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac, STUDENT_ID, token, pid, attempt_id, tmp_path

    db_base.async_session = original_db
    routes_module.async_session = original_routes
    await test_engine.dispose()


def _fixed_diagnosis_result():
    """Возвращает фиксированный DiagnosisResult для monkeypatch."""
    from core.llm_openai import DiagnosisResult
    return DiagnosisResult(
        transcription="2x = 8, x = 8 (ошибка: делитель забыт)",
        failed_step=1,
        cause_text="Ученик забыл разделить на 2 в последнем шаге.",
        level=1,
        micro_skill="div_basic",
        confidence=0.92,
    )


# ── тест 7: 200 + body shape + файл записан ──────────────────────────────────


@pytest.mark.asyncio
async def test_diagnose_200_body_and_file(client_for_diagnose, monkeypatch):
    """POST /api/trainer/diagnose → 200, правильный body, файл фото существует."""
    client, student_id, token, pid, attempt_id, tmp_path = client_for_diagnose

    # Патчим diagnose_photo там, где его видит роутер
    async def _mock_diagnose(**kwargs):
        return _fixed_diagnosis_result()

    monkeypatch.setattr("api.routers.trainer.diagnose_photo", _mock_diagnose)

    jpeg = _make_tiny_jpeg()
    resp = await client.post(
        "/api/trainer/diagnose",
        headers={"Authorization": f"Bearer {token}"},
        data={"problem_id": str(pid), "attempt_id": str(attempt_id)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 200, f"Ожидался 200, получен {resp.status_code}: {resp.text}"

    body = resp.json()
    for field in ("transcription", "failed_step", "cause_text", "level", "micro_skill", "micro_skill_label", "confidence", "image_ref"):
        assert field in body, f"Отсутствует поле '{field}' в ответе"

    assert body["transcription"] == "2x = 8, x = 8 (ошибка: делитель забыт)"
    assert body["micro_skill"] == "div_basic"
    # label_ru из micro_skills вместо голого кода на UI (запрет §2.2 DESIGN_SYSTEM)
    assert body["micro_skill_label"] == "Базовое деление"
    assert body["confidence"] == pytest.approx(0.92)

    # Проверяем, что файл фото сохранён на диск
    image_ref: str = body["image_ref"]
    assert image_ref, "image_ref не должен быть пустым"
    saved_path = tmp_path / image_ref
    assert saved_path.exists(), f"Файл фото не найден: {saved_path}"
    assert saved_path.stat().st_size > 0, "Файл фото пустой"


# ── тест 8: ровно одна строка в error_captures ───────────────────────────────


@pytest.mark.asyncio
async def test_diagnose_inserts_error_capture(client_for_diagnose, monkeypatch):
    """После одного POST ровно одна строка в error_captures."""
    client, student_id, token, pid, attempt_id, tmp_path = client_for_diagnose

    async def _mock_diagnose(**kwargs):
        return _fixed_diagnosis_result()

    monkeypatch.setattr("api.routers.trainer.diagnose_photo", _mock_diagnose)

    jpeg = _make_tiny_jpeg()
    resp = await client.post(
        "/api/trainer/diagnose",
        headers={"Authorization": f"Bearer {token}"},
        data={"problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 200, resp.text

    # Проверяем в БД через прямой запрос
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    engine = create_async_engine(_TEST_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        row = await sess.execute(
            text("SELECT COUNT(*) FROM error_captures WHERE student_id = :sid AND problem_id = :pid"),
            {"sid": student_id, "pid": pid},
        )
        count = row.scalar_one()
    await engine.dispose()

    assert count == 1, f"Ожидалась 1 строка в error_captures, найдено {count}"


# ── тест 9: recurring_errors upsert + increment ──────────────────────────────


@pytest.mark.asyncio
async def test_diagnose_recurring_errors_upsert(client_for_diagnose, monkeypatch):
    """После двух POST error_count в recurring_errors = 2."""
    client, student_id, token, pid, attempt_id, tmp_path = client_for_diagnose

    async def _mock_diagnose(**kwargs):
        return _fixed_diagnosis_result()

    monkeypatch.setattr("api.routers.trainer.diagnose_photo", _mock_diagnose)

    jpeg = _make_tiny_jpeg()

    # Первый POST
    resp1 = await client.post(
        "/api/trainer/diagnose",
        headers={"Authorization": f"Bearer {token}"},
        data={"problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp1.status_code == 200, resp1.text

    # Второй POST — тот же студент + тот же micro_skill
    resp2 = await client.post(
        "/api/trainer/diagnose",
        headers={"Authorization": f"Bearer {token}"},
        data={"problem_id": str(pid)},
        files={"photo": ("test2.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp2.status_code == 200, resp2.text

    # Проверяем error_count в recurring_errors
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    engine = create_async_engine(_TEST_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        row = await sess.execute(
            text(
                "SELECT error_count FROM recurring_errors "
                "WHERE student_id = :sid AND micro_skill = 'div_basic'"
            ),
            {"sid": student_id},
        )
        rec = row.fetchone()
    await engine.dispose()

    assert rec is not None, "Запись в recurring_errors не найдена"
    assert rec.error_count == 2, f"Ожидался error_count=2, получен {rec.error_count}"


# ── тест 10: 503 когда diagnose_photo бросает LlmUnavailable ─────────────────


@pytest.mark.asyncio
async def test_diagnose_503_on_llm_unavailable(client_for_diagnose, monkeypatch):
    """POST /api/trainer/diagnose → 503 если diagnose_photo поднимает LlmUnavailable."""
    client, student_id, token, pid, attempt_id, tmp_path = client_for_diagnose

    from core.llm_openai import LlmUnavailable

    async def _mock_diagnose_fail(**kwargs):
        raise LlmUnavailable("OpenAI недоступен в тесте")

    monkeypatch.setattr("api.routers.trainer.diagnose_photo", _mock_diagnose_fail)

    jpeg = _make_tiny_jpeg()
    resp = await client.post(
        "/api/trainer/diagnose",
        headers={"Authorization": f"Bearer {token}"},
        data={"problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 503, f"Ожидался 503, получен {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "detail" in body, "503-ответ должен содержать 'detail'"


# ── тест 11: 404 для несуществующего problem_id ───────────────────────────────


@pytest.mark.asyncio
async def test_diagnose_404_unknown_problem(client_for_diagnose, monkeypatch):
    """POST /api/trainer/diagnose с несуществующим problem_id → 404."""
    client, student_id, token, pid, attempt_id, tmp_path = client_for_diagnose

    async def _mock_diagnose(**kwargs):
        return _fixed_diagnosis_result()

    monkeypatch.setattr("api.routers.trainer.diagnose_photo", _mock_diagnose)

    jpeg = _make_tiny_jpeg()
    resp = await client.post(
        "/api/trainer/diagnose",
        headers={"Authorization": f"Bearer {token}"},
        data={"problem_id": "999999"},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 404, f"Ожидался 404, получен {resp.status_code}: {resp.text}"


# ── тест 12: 413 при превышении лимита размера ───────────────────────────────


@pytest.mark.asyncio
async def test_diagnose_413_oversized_photo(client_for_diagnose, monkeypatch):
    """POST /api/trainer/diagnose с фото > _MAX_PHOTO_BYTES → 413.

    Устанавливаем минимальный лимит через monkeypatch, чтобы не гонять 8 МБ в тесте.
    """
    client, student_id, token, pid, attempt_id, tmp_path = client_for_diagnose

    import api.routers.trainer as trainer_module

    # Устанавливаем крохотный лимит — любой реальный файл превысит
    monkeypatch.setattr(trainer_module, "_MAX_PHOTO_BYTES", 10)

    jpeg = _make_tiny_jpeg()  # >10 байт → превысит лимит
    resp = await client.post(
        "/api/trainer/diagnose",
        headers={"Authorization": f"Bearer {token}"},
        data={"problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 413, f"Ожидался 413, получен {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "detail" in body, "413-ответ должен содержать 'detail'"


# ── тест 13: 415 при недопустимом content_type ───────────────────────────────


@pytest.mark.asyncio
async def test_diagnose_415_bad_content_type(client_for_diagnose, monkeypatch):
    """POST /api/trainer/diagnose с недопустимым content_type → 415."""
    client, student_id, token, pid, attempt_id, tmp_path = client_for_diagnose

    # diagnose_photo мокаем на случай, если проверка content_type пройдёт (не должна)
    async def _mock_diagnose(**kwargs):
        return _fixed_diagnosis_result()

    monkeypatch.setattr("api.routers.trainer.diagnose_photo", _mock_diagnose)

    jpeg = _make_tiny_jpeg()
    resp = await client.post(
        "/api/trainer/diagnose",
        headers={"Authorization": f"Bearer {token}"},
        data={"problem_id": str(pid)},
        files={"photo": ("test.gif", io.BytesIO(jpeg), "image/gif")},
    )
    assert resp.status_code == 415, f"Ожидался 415, получен {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "detail" in body, "415-ответ должен содержать 'detail'"
