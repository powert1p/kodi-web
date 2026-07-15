"""Схема Блока 1.2: таблица step_submissions создаётся метадатой (модель StepSubmission).

Плюс интеграционные тесты POST /api/trainer/step-submit (Task 3):
паттерн — httpx ASGITransport + реальная тест-БД (TEST_DATABASE_URL) + Bearer-токен,
мок classify_step_photo там, где его импортирует роутер (как diagnose_photo в test_trainer_api.py).
"""
from __future__ import annotations

import io
import os
from pathlib import Path
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-chars")

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


def _make_tiny_png() -> bytes:
    """Валидный PNG 1×1 для round-trip проверки."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), (255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


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
        "INSERT INTO decomposition_problems "
        "(idx, node_id, answer, primary_micro_skill, problems_db_id, all_steps_verified, needs_review) "
        "VALUES (:idx, :nid, '4', 'div_basic', :pid, true, false)"
    ), {"idx": DECOMP_IDX, "nid": NODE, "pid": pid})
    decomp_idx = DECOMP_IDX

    await db_session.execute(text(
        "INSERT INTO problem_steps (decomp_idx, n, instruction_ru, micro_skill, expected_value) "
        "VALUES (:d, :n, 'Раздели 8 на 2', 'div_basic', '4'), "
        "       (:d, 2, 'Проверь результат умножением', 'div_basic', '8')"
    ), {"d": decomp_idx, "n": STEP_N})

    await db_session.execute(text(
        "INSERT INTO problem_fingerprints (decomp_idx, micro_skill, wrong_answer, mistake_ru) "
        "VALUES (:d, 'div_basic', '8', 'Забыл разделить на 2: правильный шаг даёт 4')"
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
    from api.routes import limiter

    # SlowAPI хранит счётчик между function-scoped ASGI-клиентами. Сбрасываем
    # только in-memory test storage, чтобы кейсы не влияли друг на друга.
    limiter._storage.reset()

    async with AsyncClient(
        transport=ASGITransport(
            app=app,
            client=(f"step-{tmp_path.name}", 123),
        ),
        base_url="http://testserver",
    ) as ac:
        yield ac, STUDENT_ID, token, decomp_idx, STEP_N, pid, tmp_path

    db_base.async_session = original_db
    routes_module.async_session = original_routes
    await test_engine.dispose()


def _mock_classify(verdict: str, confidence: float, seen_value: str | None = None):
    """Фабрика monkeypatch-функции для classify_step_photo (verdict/confidence фиксированы)."""
    async def _inner(**kwargs):
        from core.llm_openai import StepClassification
        return StepClassification(verdict=verdict, seen_value=seen_value, confidence=confidence)
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
async def test_step_submit_does_not_commit_when_photo_storage_fails(client_for_step, monkeypatch):
    """Ошибка диска → 503 и ни ложного submission, ни успешного ответа."""
    ac, student_id, token, decomp_idx, step_n, pid, _tmp_path = client_for_step
    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _mock_classify("match", 0.9))

    def _fail_write(_self: Path, _data: bytes) -> int:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_bytes", _fail_write)
    response = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(_make_tiny_jpeg()), "image/jpeg")},
    )

    assert response.status_code == 503
    from db.base import async_session
    async with async_session() as session:
        count = (await session.execute(text(
            "SELECT count(*) FROM step_submissions WHERE student_id = :sid"
        ), {"sid": student_id})).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_step_submit_rejects_decomp_from_another_problem(client_for_step, monkeypatch):
    """Фото нельзя проверить против декомпозиции другой задачи."""
    ac, _student_id, token, decomp_idx, step_n, pid, _tmp_path = client_for_step

    async def _must_not_call_provider(**_kwargs):
        raise AssertionError("vision provider не должен вызываться для чужой задачи")

    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _must_not_call_provider)
    response = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid + 999)},
        files={"photo": ("test.jpg", io.BytesIO(_make_tiny_jpeg()), "image/jpeg")},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_step_submit_rejects_skipping_previous_step(client_for_step, monkeypatch):
    """Нельзя отметить второй шаг решённым, не подтвердив первый."""
    ac, _student_id, token, decomp_idx, _step_n, pid, _tmp_path = client_for_step

    async def _must_not_call_provider(**_kwargs):
        raise AssertionError("vision provider не должен вызываться при пропуске шага")

    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _must_not_call_provider)
    response = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": "2", "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(_make_tiny_jpeg()), "image/jpeg")},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_step_submit_mismatch_hint(client_for_step, monkeypatch):
    """Даже точный fingerprint не раскрывает expected_value из сырого mistake_ru."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step
    monkeypatch.setattr(
        "api.routers.trainer.classify_step_photo",
        _mock_classify("mismatch", 0.9, seen_value="8"),
    )

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
    assert body["hint"] == "Проверь этот шаг ещё раз: Раздели 8 на 2"
    assert "4" not in body["hint"]

    from db.base import async_session
    async with async_session() as session:
        row = (await session.execute(
            text("SELECT verdict, matched_micro_skill FROM step_submissions WHERE student_id = :sid"),
            {"sid": student_id},
        )).fetchone()
        assert row.verdict == "mismatch"
        assert row.matched_micro_skill == "div_basic"


@pytest.mark.asyncio
async def test_step_submit_unknown_mismatch_uses_step_grounded_hint(client_for_step, monkeypatch):
    """Неизвестная ошибка не должна получать объяснение от чужого fingerprint."""
    ac, student_id, token, decomp_idx, step_n, pid, _tmp_path = client_for_step
    monkeypatch.setattr(
        "api.routers.trainer.classify_step_photo",
        _mock_classify("mismatch", 0.9, seen_value="7"),
    )

    response = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(_make_tiny_jpeg()), "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "mismatch"
    assert body["hint"] == "Проверь этот шаг ещё раз: Раздели 8 на 2"

    from db.base import async_session
    async with async_session() as session:
        matched_micro_skill = (await session.execute(
            text(
                "SELECT matched_micro_skill FROM step_submissions "
                "WHERE student_id = :sid"
            ),
            {"sid": student_id},
        )).scalar_one()
    assert matched_micro_skill is None


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
async def test_step_submit_low_conf_match_becomes_unsure_and_does_not_solve(
    client_for_step,
    monkeypatch,
):
    """Неуверенный match не должен подтверждать шаг и открывать следующий."""
    ac, student_id, token, decomp_idx, step_n, pid, _tmp_path = client_for_step
    monkeypatch.setattr(
        "api.routers.trainer.classify_step_photo",
        _mock_classify("match", 0.3),
    )

    response = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(_make_tiny_jpeg()), "image/jpeg")},
    )

    assert response.status_code == 200, response.text
    assert response.json()["verdict"] == "unsure"
    state = await ac.get(
        f"/api/trainer/drill-state?problem_id={pid}&decomp_idx={decomp_idx}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert state.status_code == 200, state.text
    assert state.json() == {"solved_step_ns": []}


@pytest.mark.asyncio
@pytest.mark.parametrize("unsafe_confidence", [float("nan"), -0.1, 1.1])
async def test_step_submit_invalid_confidence_is_safe_unsure(
    client_for_step,
    monkeypatch,
    unsafe_confidence,
):
    """Невалидная confidence не подтверждает шаг и не попадает как NaN в JSON/БД."""
    ac, _student_id, token, decomp_idx, step_n, pid, _tmp_path = client_for_step
    monkeypatch.setattr(
        "api.routers.trainer.classify_step_photo",
        _mock_classify("match", unsafe_confidence),
    )

    response = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(_make_tiny_jpeg()), "image/jpeg")},
    )

    assert response.status_code == 200, response.text
    assert response.json()["verdict"] == "unsure"
    assert response.json()["confidence"] == 0.0
    state = await ac.get(
        f"/api/trainer/drill-state?problem_id={pid}&decomp_idx={decomp_idx}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert state.json() == {"solved_step_ns": []}


@pytest.mark.asyncio
async def test_step_submit_malformed_provider_types_fail_soft_to_unsure(
    client_for_step,
    monkeypatch,
):
    """no-strict Gemini JSON не роняет route и не отправляет dict в SQL."""
    ac, _student_id, token, decomp_idx, step_n, pid, _tmp_path = client_for_step

    async def _malformed_classification(**kwargs):
        from core.llm_openai import StepClassification

        return StepClassification(
            verdict=["mismatch"],  # type: ignore[arg-type]
            seen_value={"value": "8"},  # type: ignore[arg-type]
            confidence={"confidence": 1},  # type: ignore[arg-type]
        )

    monkeypatch.setattr(
        "api.routers.trainer.classify_step_photo",
        _malformed_classification,
    )
    response = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "decomp_idx": str(decomp_idx),
            "step_n": str(step_n),
            "problem_id": str(pid),
        },
        files={"photo": ("test.jpg", io.BytesIO(_make_tiny_jpeg()), "image/jpeg")},
    )

    assert response.status_code == 200, response.text
    assert response.json()["verdict"] == "unsure"
    assert response.json()["confidence"] == 0.0
    assert response.json()["hint"] is None


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
async def test_step_submit_rejects_corrupt_image_before_provider(client_for_step, monkeypatch):
    """Заявленный JPEG с произвольными байтами не уходит во внешний provider."""
    ac, _student_id, token, decomp_idx, step_n, pid, _tmp_path = client_for_step
    provider_called = False

    async def _classify(**kwargs):
        nonlocal provider_called
        provider_called = True
        return _mock_classify("match", 0.9)(**kwargs)

    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _classify)
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("fake.jpg", io.BytesIO(b"not-an-image"), "image/jpeg")},
    )

    assert resp.status_code == 422, resp.text
    assert provider_called is False


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


# ── Task 4: owner-эндпоинты — export CSV + step-photo ────────────────────────


@pytest.mark.asyncio
async def test_step_export_owner_ok(client_for_step, monkeypatch):
    """Владелец после ≥1 сдачи → 200, text/csv, тело содержит заголовок + строку."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step
    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _mock_classify("match", 0.9))

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 200

    from core.config import settings as app_settings
    old = app_settings.owner_student_id
    app_settings.owner_student_id = student_id
    try:
        r = await ac.get(
            "/api/trainer/step-submissions/export?format=csv",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        lines = r.text.strip().splitlines()
        assert lines[0].split(",")[0] == "id"
        assert len(lines) >= 2
    finally:
        app_settings.owner_student_id = old


@pytest.mark.asyncio
async def test_step_export_forbidden(client_for_step):
    """owner_student_id=0 (никому) → 403."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step

    from core.config import settings as app_settings
    old = app_settings.owner_student_id
    app_settings.owner_student_id = 0
    try:
        r = await ac.get(
            "/api/trainer/step-submissions/export?format=csv",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403
    finally:
        app_settings.owner_student_id = old


@pytest.mark.asyncio
async def test_step_photo_owner_ok(client_for_step, monkeypatch):
    """Владелец → GET step-photo по id из БД → 200, image/jpeg."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step
    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _mock_classify("match", 0.9))

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 200

    from db.base import async_session
    async with async_session() as session:
        submission_id = (await session.execute(
            text("SELECT id FROM step_submissions WHERE student_id = :sid"),
            {"sid": student_id},
        )).scalar_one()

    from core.config import settings as app_settings
    old = app_settings.owner_student_id
    app_settings.owner_student_id = student_id
    try:
        r = await ac.get(
            f"/api/trainer/step-photo/{submission_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/jpeg"
        assert r.content == jpeg
    finally:
        app_settings.owner_student_id = old


@pytest.mark.asyncio
async def test_step_photo_owner_png_round_trip(client_for_step, monkeypatch):
    """PNG сохраняет расширение, байты и Content-Type при GET."""
    ac, student_id, token, decomp_idx, step_n, pid, _tmp_path = client_for_step
    monkeypatch.setattr(
        "api.routers.trainer.classify_step_photo",
        _mock_classify("match", 0.9),
    )

    png = _make_tiny_png()
    response = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "decomp_idx": str(decomp_idx),
            "step_n": str(step_n),
            "problem_id": str(pid),
        },
        files={"photo": ("step.png", io.BytesIO(png), "image/png")},
    )
    assert response.status_code == 200, response.text

    from db.base import async_session

    async with async_session() as session:
        submission = (
            await session.execute(
                text(
                    "SELECT id, photo_path FROM step_submissions "
                    "WHERE student_id = :sid"
                ),
                {"sid": student_id},
            )
        ).one()
    assert submission.photo_path.endswith(".png")

    from core.config import settings as app_settings

    old = app_settings.owner_student_id
    app_settings.owner_student_id = student_id
    try:
        loaded = await ac.get(
            f"/api/trainer/step-photo/{submission.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert loaded.status_code == 200
        assert loaded.headers["content-type"] == "image/png"
        assert loaded.content == png
    finally:
        app_settings.owner_student_id = old


@pytest.mark.asyncio
async def test_step_photo_forbidden(client_for_step, monkeypatch):
    """Не-владелец → 403."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step
    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _mock_classify("match", 0.9))

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 200

    from db.base import async_session
    async with async_session() as session:
        submission_id = (await session.execute(
            text("SELECT id FROM step_submissions WHERE student_id = :sid"),
            {"sid": student_id},
        )).scalar_one()

    from core.config import settings as app_settings
    old = app_settings.owner_student_id
    app_settings.owner_student_id = student_id + 1  # чужой владелец
    try:
        r = await ac.get(
            f"/api/trainer/step-photo/{submission_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403
    finally:
        app_settings.owner_student_id = old


@pytest.mark.asyncio
async def test_step_photo_404(client_for_step):
    """Владелец, несуществующий id → 404."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step

    from core.config import settings as app_settings
    old = app_settings.owner_student_id
    app_settings.owner_student_id = student_id
    try:
        r = await ac.get(
            "/api/trainer/step-photo/999999999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404
    finally:
        app_settings.owner_student_id = old


@pytest.mark.asyncio
async def test_step_photo_row_exists_file_missing_404(client_for_step, monkeypatch):
    """Владелец, строка в БД есть, но файл на диске удалён → 404 (не 500)."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step
    monkeypatch.setattr("api.routers.trainer.classify_step_photo", _mock_classify("match", 0.9))

    jpeg = _make_tiny_jpeg()
    resp = await ac.post(
        "/api/trainer/step-submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"decomp_idx": str(decomp_idx), "step_n": str(step_n), "problem_id": str(pid)},
        files={"photo": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 200

    from db.base import async_session
    async with async_session() as session:
        submission_id = (await session.execute(
            text("SELECT id FROM step_submissions WHERE student_id = :sid"),
            {"sid": student_id},
        )).scalar_one()

    photo_files = list((tmp_path / "steps" / str(student_id)).glob("*.jpg"))
    assert len(photo_files) == 1
    photo_files[0].unlink()  # строка в БД остаётся, файл исчезает

    from core.config import settings as app_settings
    old = app_settings.owner_student_id
    app_settings.owner_student_id = student_id
    try:
        r = await ac.get(
            f"/api/trainer/step-photo/{submission_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404
    finally:
        app_settings.owner_student_id = old


@pytest.mark.asyncio
async def test_step_photo_forbidden_nonexistent_id_gate_before_select(client_for_step):
    """Не-владелец + несуществующий id → 403 (owner-гейт срабатывает раньше SELECT)."""
    ac, student_id, token, decomp_idx, step_n, pid, tmp_path = client_for_step

    from core.config import settings as app_settings
    old = app_settings.owner_student_id
    app_settings.owner_student_id = student_id + 1  # чужой владелец
    try:
        r = await ac.get(
            "/api/trainer/step-photo/999999999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403
    finally:
        app_settings.owner_student_id = old
