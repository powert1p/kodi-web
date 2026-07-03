"""Схема Блока 1.2: таблица step_submissions создаётся метадатой (модель StepSubmission).

Плюс интеграционные тесты POST /api/trainer/step-submit (Task 3):
паттерн — httpx ASGITransport + реальная тест-БД (TEST_DATABASE_URL) + Bearer-токен,
мок classify_step_photo там, где его импортирует роутер (как diagnose_photo в test_trainer_api.py).
"""
from __future__ import annotations

import io
import os
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest.mark.asyncio
async def test_step_submissions_table_exists_with_expected_columns(db_session):
    cols = (await db_session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'step_submissions'"
    ))).scalars().all()
    expected = {
        "id",
        "student_id",
        "decomp_idx",
        "step_n",
        "problem_id",
        "verdict",
        "confidence",
        "matched_micro_skill",
        "photo_path",
        "created_at",
    }
    assert expected.issubset(set(cols))


@pytest.mark.asyncio
async def test_step_submissions_table_inserts(db_session, seeded_student):
    await db_session.execute(text(
        "INSERT INTO step_submissions (student_id, decomp_idx, step_n, verdict, photo_path) "
        "VALUES (:sid, 1, 1, 'match', 'foo.jpg')"
    ), {"sid": seeded_student})
    await db_session.commit()
    n = (await db_session.execute(text("SELECT count(*) FROM step_submissions"))).scalar()
    assert n == 1


# ── Task 3: POST /api/trainer/step-submit ────────────────────────────────────


def _make_tiny_jpeg() -> bytes:
    """Минимальный валидный JPEG-файл (1×1 px) для тестов (без Pillow)."""
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
async def client_for_step(db_session, tmp_path, monkeypatch):
    """Студент + узел + задача + decomposition_problems + problem_steps + problem_fingerprints.

    Возвращает (ac, student_id, token, decomp_idx, step_n, problem_id, tmp_path).
    """
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан — пропуск интеграционных тестов")

    STUDENT_ID = 7003
    NODE = "TR03"
    STEP_N = 1

    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete, photo_consent) "
        "VALUES (:sid, true, 'ru', NOW(), false, true) "
        "ON CONFLICT (id) DO NOTHING"
    ), {"sid": STUDENT_ID})

    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES (:nid, 'Деление-тест', 'Деление-тест', 0.3, 0.05, 0.1) "
        "ON CONFLICT (id) DO NOTHING"
    ), {"nid": NODE})

    prob_row = await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer) "
        "VALUES (:nid, 'Найди x: 2x = 8', '4') RETURNING id"
    ), {"nid": NODE})
    pid = prob_row.scalar_one()

    DECOMP_IDX = 90003  # idx — явный PK банка декомпозиций, не автоинкремент
    await db_session.execute(text(
        "INSERT INTO decomposition_problems (idx, node_id, answer, primary_micro_skill, problems_db_id) "
        "VALUES (:idx, :nid, '4', 'div_basic', :pid)"
    ), {"idx": DECOMP_IDX, "nid": NODE, "pid": pid})
    decomp_idx = DECOMP_IDX

    await db_session.execute(text(
        "INSERT INTO problem_steps (decomp_idx, n, instruction_ru, micro_skill, expected_value) "
        "VALUES (:d, :n, 'Раздели 8 на 2', 'div_basic', '4')"
    ), {"d": decomp_idx, "n": STEP_N})

    await db_session.execute(text(
        "INSERT INTO problem_fingerprints (decomp_idx, micro_skill, wrong_answer, mistake_ru) "
        "VALUES (:d, 'div_basic', '8', 'Забыл разделить на 2')"
    ), {"d": decomp_idx})

    await db_session.commit()

    from api.routes import _create_token
    token = _create_token(STUDENT_ID)

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
        yield ac, STUDENT_ID, token, decomp_idx, STEP_N, pid, tmp_path

    db_base.async_session = original_db
    routes_module.async_session = original_routes
    await test_engine.dispose()


def _mock_classify(verdict: str, confidence: float):
    """Фабрика monkeypatch-функции для classify_step_photo (verdict/confidence фиксированы)."""
    async def _inner(**kwargs):
        from core.llm_openai import StepClassification
        return StepClassification(verdict=verdict, seen_value=None, confidence=confidence)
    return _inner


@pytest.mark.asyncio
async def test_step_submit_match(client_for_step, monkeypatch):
    """match → 200, hint=None, строка в step_submissions, файл на диске."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step
    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _mock_classify("match", 0.9))

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 200, f"Ожидался 200, получен {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["verdict"] == "match"
    assert body["hint"] is None
    assert body["step_n"] == step_n

    from db.base import async_session
    async with async_session() as session:
        count = (await session.execute(text("SELECT count(*) FROM step_submissions"))).scalar()
        assert count == 1

    photo_files = list((tmp_path / "steps" / str(student_id)).glob("*.jpg"))
    assert len(photo_files) == 1


@pytest.mark.asyncio
async def test_step_submit_mismatch_hint(client_for_step, monkeypatch):
    """mismatch с высокой уверенностью → hint из fingerprint, matched_micro_skill в БД."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step
    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _mock_classify("mismatch", 0.9))

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "mismatch"
    assert body["hint"] == "Забыл разделить на 2"

    from db.base import async_session
    async with async_session() as session:
        row = (await session.execute(
            text("SELECT verdict, matched_micro_skill FROM step_submissions WHERE student_id = :sid"),
            {"sid": student_id},
        )).fetchone()
        assert row.verdict == "mismatch"
        assert row.matched_micro_skill == "div_basic"


@pytest.mark.asyncio
async def test_step_submit_low_conf_becomes_unsure(client_for_step, monkeypatch):
    """mismatch с confidence < порога (0.6) → мягко переквалифицируется в unsure."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step
    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _mock_classify("mismatch", 0.3))

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "unsure"
    assert body["hint"] is None

    from db.base import async_session
    async with async_session() as session:
        row = (await session.execute(
            text("SELECT verdict FROM step_submissions WHERE student_id = :sid"),
            {"sid": student_id},
        )).fetchone()
        assert row.verdict == "unsure"


@pytest.mark.asyncio
async def test_step_submit_unsure(client_for_step, monkeypatch):
    """unsure от классификатора → 200, hint=None, строка записана."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step
    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _mock_classify("unsure", 0.5))

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "unsure"
    assert body["hint"] is None

    from db.base import async_session
    async with async_session() as session:
        count = (await session.execute(text("SELECT count(*) FROM step_submissions"))).scalar()
        assert count == 1
        attempts_count = (await session.execute(text("SELECT count(*) FROM attempts"))).scalar()
        assert attempts_count == 0


@pytest.mark.asyncio
async def test_step_submit_consent_required(client_for_step, monkeypatch):
    """Студент без photo_consent → 403 consent_required."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step

    from db.base import async_session
    async with async_session() as session:
        await session.execute(
            text("UPDATE students SET photo_consent = NULL WHERE id = :sid"),
            {"sid": student_id},
        )
        await session.commit()

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "consent_required"


@pytest.mark.asyncio
async def test_step_submit_413(client_for_step, monkeypatch):
    """Фото больше лимита → 413."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step

    import api.routers.trainer as trainer_module
    monkeypatch.setattr(trainer_module, "_MAX_PHOTO_BYTES", 10)

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_step_submit_415(client_for_step, monkeypatch):
    """Недопустимый content_type → 415."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.txt", io.BytesIO(jpeg), "text/plain")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_step_submit_503(client_for_step, monkeypatch):
    """classify_step_photo бросает LlmUnavailable → 503."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step

    from core.llm_openai import LlmUnavailable

    async def _raise(**kwargs):
        raise LlmUnavailable("нет ключа")

    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _raise)

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_step_submit_step_not_found(client_for_step, monkeypatch):
    """Несуществующий step_n → 404."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step
    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _mock_classify("match", 0.9))

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": "999", "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 404
