"""Тесты для core/llm_openai.py — mocked, без реального API.

Все тесты работают без TEST_DATABASE_URL и без реального ключа OpenAI/Gemini.
Паттерн: monkeypatch _get_active_client → возвращает (fake_client, model_chain).
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import types
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

# env до импорта core.config (fail-fast guard)
os.environ.setdefault("JWT_SECRET", "test-secret")


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_fake_completion(payload: dict) -> MagicMock:
    """Создаёт фейковый объект ответа (chat.completions.create)."""
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

# Тестовая цепочка моделей
_TEST_MODEL_CHAIN = ["test-model-v1"]


# ─── тест 1: happy path — parse DiagnosisResult ──────────────────────────────

@pytest.mark.asyncio
async def test_diagnose_photo_parses_result() -> None:
    """Фейковый клиент → diagnose_photo корректно парсит DiagnosisResult."""
    from core.llm_openai import DiagnosisResult, diagnose_photo

    fake_client = _make_fake_client(_KNOWN_PAYLOAD)

    with patch("core.llm_openai._get_active_client", return_value=(fake_client, _TEST_MODEL_CHAIN)):
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
    """Промпт, отправляемый провайдеру, содержит correct_answer и canonical_steps."""
    from core.llm_openai import diagnose_photo

    fake_client = _make_fake_client(_KNOWN_PAYLOAD)

    with patch("core.llm_openai._get_active_client", return_value=(fake_client, _TEST_MODEL_CHAIN)):
        await diagnose_photo(
            image_bytes=_TINY_PNG,
            content_type="image/png",
            statement="Реши уравнение: x + 2 = 3",
            canonical_steps=_CANONICAL_STEPS,
            correct_answer="42",
            wrong_answer="5",
            fingerprint_hint="eq_transpose",
        )

    # messages всегда передаётся как kwargs
    create_mock = fake_client.chat.completions.create
    messages = create_mock.call_args.kwargs["messages"]

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
    # W2: проверяем что инструкция «не раскрывать ответ» включена в промпт
    assert "НИКОГДА не раскрывай" in all_text, "промпт должен содержать инструкцию не раскрывать ответ"


# ─── тест 3: клиент None → LlmUnavailable ────────────────────────────────────

@pytest.mark.asyncio
async def test_diagnose_photo_no_client_raises_llm_unavailable() -> None:
    """Клиент None (нет пакета openai) → raises LlmUnavailable."""
    from core.llm_openai import LlmUnavailable, diagnose_photo

    # _get_active_client возвращает (None, []) — пакет не установлен
    with patch("core.llm_openai._get_active_client", return_value=(None, [])):
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
        patch("core.llm_openai._get_active_client", return_value=(fake_client, _TEST_MODEL_CHAIN)),
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
        patch("core.llm_openai._get_active_client", return_value=(fake_client, _TEST_MODEL_CHAIN)),
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
    # Все вызовы бросают ошибку (не содержит "strict" → не триггерит fallback)
    fake_client.chat.completions.create = AsyncMock(
        side_effect=Exception("API error")
    )

    with patch("core.llm_openai._get_active_client", return_value=(fake_client, _TEST_MODEL_CHAIN)):
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


# ─── тест 7: Gemini provider — AsyncOpenAI вызывается с Gemini base_url ──────

def test_gemini_client_factory_uses_gemini_base_url() -> None:
    """При vision_provider=gemini AsyncOpenAI создаётся с Gemini endpoint и ключом."""
    import core.llm_openai as llm_mod
    from core.llm_openai import _GEMINI_BASE_URL

    captured_kwargs: dict = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    # Сбрасываем кэш lazy-клиента
    original = llm_mod._gemini_client
    llm_mod._gemini_client = None

    try:
        with (
            patch("core.llm_openai.openai", create=True) as mock_openai_mod,
            patch("core.config.settings") as mock_settings,
        ):
            mock_settings.gemini_api_key = "test-gemini-key-xyz"
            mock_settings.vision_provider = "gemini"
            mock_openai_mod.AsyncOpenAI = FakeAsyncOpenAI

            # Патчим импорт openai внутри _get_gemini_client
            import openai as real_openai
            with patch.object(real_openai, "AsyncOpenAI", FakeAsyncOpenAI):
                with patch("core.config.settings", mock_settings):
                    llm_mod._gemini_client = None  # сброс кэша перед вызовом
                    client = llm_mod._get_gemini_client()

        assert captured_kwargs.get("base_url") == _GEMINI_BASE_URL, (
            f"base_url должен быть {_GEMINI_BASE_URL}, получили: {captured_kwargs.get('base_url')}"
        )
        assert captured_kwargs.get("api_key") == "test-gemini-key-xyz", (
            "api_key должен быть передан gemini-ключ"
        )
    finally:
        llm_mod._gemini_client = original


# ─── тест 8: пустой GEMINI_API_KEY → LlmUnavailable ─────────────────────────

def test_gemini_empty_key_raises_llm_unavailable() -> None:
    """Пустой GEMINI_API_KEY при vision_provider=gemini → LlmUnavailable немедленно."""
    import core.llm_openai as llm_mod
    from core.llm_openai import LlmUnavailable

    original = llm_mod._gemini_client
    llm_mod._gemini_client = None

    try:
        with patch("core.config.settings") as mock_settings:
            mock_settings.gemini_api_key = ""  # пустой ключ
            mock_settings.vision_provider = "gemini"

            with pytest.raises(LlmUnavailable, match="GEMINI_API_KEY"):
                llm_mod._get_gemini_client()
    finally:
        llm_mod._gemini_client = original


# ─── тест 9: Gemini strict-rejected → fallback без strict ────────────────────

@pytest.mark.asyncio
async def test_gemini_strict_rejected_falls_back_to_no_strict() -> None:
    """Если Gemini бросает исключение с 'strict' в тексте — повтор без strict field."""
    from core.llm_openai import DiagnosisResult, diagnose_photo

    # Первый вызов (со strict) бросает — в тексте есть 'strict'
    # Второй вызов (без strict) успешен
    fake_client = MagicMock()
    fake_client.chat = MagicMock()
    fake_client.chat.completions = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        side_effect=[
            Exception("strict not supported by this model"),
            _make_fake_completion(_KNOWN_PAYLOAD),
        ]
    )

    with (
        patch("core.llm_openai._get_active_client", return_value=(fake_client, _TEST_MODEL_CHAIN)),
        patch("core.config.settings") as mock_settings,
    ):
        mock_settings.vision_provider = "gemini"
        result = await diagnose_photo(
            image_bytes=_TINY_PNG,
            content_type="image/png",
            statement="Задача",
            canonical_steps=_CANONICAL_STEPS,
            correct_answer="1",
            wrong_answer=None,
            fingerprint_hint=None,
        )

    # Метод вызван дважды (strict → no-strict)
    assert fake_client.chat.completions.create.call_count == 2
    # Результат корректно распарсен из второго вызова
    assert isinstance(result, DiagnosisResult)
    assert result.transcription == "x = 5"

    # Второй вызов НЕ должен содержать "strict" в json_schema
    second_call_kwargs = fake_client.chat.completions.create.call_args_list[1].kwargs
    rf = second_call_kwargs.get("response_format", {})
    schema_sent = rf.get("json_schema", {})
    assert "strict" not in schema_sent, "повторный запрос не должен содержать strict в json_schema"
