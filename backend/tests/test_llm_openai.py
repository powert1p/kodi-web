"""Тесты для core/llm_openai.py — mocked, без реального API.

Все тесты работают без TEST_DATABASE_URL и без реального ключа OpenAI.
Паттерн: monkeypatch _get_openai_client → возвращает fake-клиент.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import types
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# env до импорта core.config (fail-fast guard)
os.environ.setdefault("JWT_SECRET", "test-secret")


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_fake_completion(payload: dict) -> MagicMock:
    """Создаёт фейковый объект ответа OpenAI (chat.completions.create)."""
    choice = MagicMock()
    choice.message.content = json.dumps(payload)
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def _make_fake_client(payload: dict) -> MagicMock:
    """Создаёт фейковый AsyncOpenAI-клиент."""
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=_make_fake_completion(payload))
    return client


# Минимальный PNG (1×1 прозрачный пиксель)
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Минимальный HEIC header (ftyp box с brand heic)
_FAKE_HEIC_BYTES = b"\x00\x00\x00\x18ftyp" + b"heic" + b"\x00\x00\x00\x00" + b"heicmif1"

_KNOWN_PAYLOAD = {
    "transcription": "x = 5",
    "failed_step": 2,
    "cause_text": "Ошибка при переносе слагаемого",
    "level": 2,
    "micro_skill": "eq_transpose",
    "confidence": 0.87,
}

_CANONICAL_STEPS = [
    {"n": 1, "instruction_ru": "Перенести слагаемое", "expected_value": "3"},
    {"n": 2, "instruction_ru": "Разделить обе части", "expected_value": "1"},
]


# ─── тест 1: happy path — parse DiagnosisResult ──────────────────────────────

@pytest.mark.asyncio
async def test_diagnose_photo_parses_result() -> None:
    """Фейковый клиент → diagnose_photo корректно парсит DiagnosisResult."""
    from core.llm_openai import DiagnosisResult, diagnose_photo

    fake_client = _make_fake_client(_KNOWN_PAYLOAD)

    with patch("core.llm_openai._get_openai_client", return_value=fake_client):
        result = await diagnose_photo(
            image_bytes=_TINY_PNG,
            content_type="image/png",
            statement="Реши уравнение: x + 2 = 3",
            canonical_steps=_CANONICAL_STEPS,
            correct_answer="1",
            wrong_answer="5",
            fingerprint_hint=None,
        )

    assert isinstance(result, DiagnosisResult)
    assert result.transcription == "x = 5"
    assert result.failed_step == 2
    assert result.cause_text == "Ошибка при переносе слагаемого"
    assert result.level == 2
    assert result.micro_skill == "eq_transpose"
    assert abs(result.confidence - 0.87) < 1e-9


# ─── тест 2: промпт содержит correct_answer и шаги ───────────────────────────

@pytest.mark.asyncio
async def test_diagnose_photo_prompt_contains_correct_answer_and_steps() -> None:
    """Промпт, отправляемый в OpenAI, содержит correct_answer и canonical_steps."""
    from core.llm_openai import diagnose_photo

    fake_client = _make_fake_client(_KNOWN_PAYLOAD)

    with patch("core.llm_openai._get_openai_client", return_value=fake_client):
        await diagnose_photo(
            image_bytes=_TINY_PNG,
            content_type="image/png",
            statement="Реши уравнение: x + 2 = 3",
            canonical_steps=_CANONICAL_STEPS,
            correct_answer="42",
            wrong_answer="5",
            fingerprint_hint="eq_transpose",
        )

    # Извлекаем аргументы вызова
    call_kwargs = fake_client.chat.completions.create.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0] if call_kwargs.args else None
    if messages is None:
        # positional-only — берём из kwargs
        messages = call_kwargs.kwargs["messages"]

    # Собираем весь текст из messages
    all_text = ""
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            all_text += content
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    all_text += part.get("text", "")

    assert "42" in all_text, "correct_answer должен присутствовать в промпте"
    assert "Перенести слагаемое" in all_text, "canonical_steps должны присутствовать в промпте"


# ─── тест 3: пустой ключ → LlmUnavailable ────────────────────────────────────

@pytest.mark.asyncio
async def test_diagnose_photo_no_key_raises_llm_unavailable() -> None:
    """Пустой openai_api_key → raises LlmUnavailable."""
    from core.llm_openai import LlmUnavailable, diagnose_photo

    with patch("core.llm_openai._get_openai_client", return_value=None):
        with pytest.raises(LlmUnavailable):
            await diagnose_photo(
                image_bytes=_TINY_PNG,
                content_type="image/png",
                statement="Задача",
                canonical_steps=[],
                correct_answer="1",
                wrong_answer=None,
                fingerprint_hint=None,
            )


# ─── тест 4: HEIC bytes → вызывается путь конвертации ────────────────────────

@pytest.mark.asyncio
async def test_diagnose_photo_heic_triggers_conversion() -> None:
    """HEIC-байты → pillow_heif регистрируется и Image.open вызывается."""
    from core.llm_openai import diagnose_photo

    fake_client = _make_fake_client(_KNOWN_PAYLOAD)

    # Фейковый Image из Pillow — возвращает PNG-байты при save
    fake_img = MagicMock()

    def fake_save(buf, format=None, **kw):  # noqa: A002
        buf.write(_TINY_PNG)

    fake_img.save = fake_save

    # Мок PIL.Image.open → возвращает fake_img
    fake_pil_open = MagicMock(return_value=fake_img)

    with (
        patch("core.llm_openai._get_openai_client", return_value=fake_client),
        patch("core.llm_openai._register_heif_opener") as mock_register,
        patch("PIL.Image.open", fake_pil_open),
    ):
        result = await diagnose_photo(
            image_bytes=_FAKE_HEIC_BYTES,
            content_type="image/heic",
            statement="Задача",
            canonical_steps=_CANONICAL_STEPS,
            correct_answer="1",
            wrong_answer=None,
            fingerprint_hint=None,
        )

    # Регистрация pillow_heif должна быть вызвана
    mock_register.assert_called_once()
    # PIL.Image.open должен быть вызван (конвертация)
    fake_pil_open.assert_called_once()
    # Результат всё равно парсится
    assert result.transcription == "x = 5"


# ─── тест 5: HEIC определяется по byte signature (content_type generic) ──────

@pytest.mark.asyncio
async def test_diagnose_photo_heic_detected_by_bytes() -> None:
    """Даже при content_type='image/jpeg' — HEIC по ftyp-сигнатуре → конвертация."""
    from core.llm_openai import diagnose_photo

    fake_client = _make_fake_client(_KNOWN_PAYLOAD)
    fake_img = MagicMock()

    def fake_save(buf, format=None, **kw):  # noqa: A002
        buf.write(_TINY_PNG)

    fake_img.save = fake_save
    fake_pil_open = MagicMock(return_value=fake_img)

    with (
        patch("core.llm_openai._get_openai_client", return_value=fake_client),
        patch("core.llm_openai._register_heif_opener"),
        patch("PIL.Image.open", fake_pil_open),
    ):
        await diagnose_photo(
            image_bytes=_FAKE_HEIC_BYTES,
            content_type="image/jpeg",  # неправильный content_type
            statement="Задача",
            canonical_steps=_CANONICAL_STEPS,
            correct_answer="1",
            wrong_answer=None,
            fingerprint_hint=None,
        )

    # Конвертация всё равно должна была произойти
    fake_pil_open.assert_called_once()


# ─── тест 6: все модели в chain падают → LlmUnavailable ─────────────────────

@pytest.mark.asyncio
async def test_diagnose_photo_all_models_fail_raises() -> None:
    """Если все модели из chain бросают исключение → LlmUnavailable."""
    from core.llm_openai import LlmUnavailable, diagnose_photo

    fake_client = MagicMock()
    fake_client.chat = MagicMock()
    fake_client.chat.completions = MagicMock()
    # Все вызовы бросают ошибку
    fake_client.chat.completions.create = AsyncMock(
        side_effect=Exception("API error")
    )

    with patch("core.llm_openai._get_openai_client", return_value=fake_client):
        with pytest.raises(LlmUnavailable):
            await diagnose_photo(
                image_bytes=_TINY_PNG,
                content_type="image/png",
                statement="Задача",
                canonical_steps=[],
                correct_answer="1",
                wrong_answer=None,
                fingerprint_hint=None,
            )
