"""Grounded photo diagnosis via OpenAI Vision API.

Принимает фото рукописного решения ученика, список канонических шагов,
правильный и неправильный ответы — и просит модель локализовать ошибку,
сформулировать сократический комментарий, вернуть структурированный JSON.

Архитектура:
  - Lazy-init AsyncOpenAI (как _get_anthropic_client в grading.py).
  - HEIC → JPEG через pillow-heif (lazy import) если нужно.
  - Fallback по openai_model_chain; LlmUnavailable при полной недоступности.
  - asyncio.wait_for с таймаутом (vision медленнее текста).
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Таймаут одного запроса vision (секунды)
_OPENAI_TIMEOUT = 30.0

# Глобальный lazy-клиент (None пока не инициализирован)
_openai_client = None


# ─── публичные типы ────────────────────────────────────────────────────────────

@dataclass
class DiagnosisResult:
    """Результат диагностики фото-решения.

    Attributes:
        transcription:  Дословное распознавание рукописного текста.
        failed_step:    Номер шага (1-based), где ученик ошибся; None если шаг неясен.
        cause_text:     Сократический комментарий — что пошло не так (без финального ответа).
        level:          Сложность ошибки 1–3.
        micro_skill:    Идентификатор навыка если определён, иначе None.
        confidence:     Уверенность модели 0.0–1.0.
    """
    transcription: str
    failed_step: int | None
    cause_text: str
    level: int
    micro_skill: str | None
    confidence: float


class LlmUnavailable(Exception):
    """Ключ API не задан или все модели из chain вернули ошибку."""


# ─── JSON Schema для structured output ────────────────────────────────────────

# OpenAI требует strict=True + additionalProperties=false + все поля в required.
# Nullable поля через anyOf: [{type:...}, {type:"null"}] (JSON Schema draft-07).
_DIAGNOSIS_JSON_SCHEMA = {
    "name": "diagnosis",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "transcription",
            "failed_step",
            "cause_text",
            "level",
            "micro_skill",
            "confidence",
        ],
        "properties": {
            "transcription": {"type": "string"},
            "failed_step": {
                "anyOf": [{"type": "integer"}, {"type": "null"}]
            },
            "cause_text": {"type": "string"},
            "level": {"type": "integer"},
            "micro_skill": {
                "anyOf": [{"type": "string"}, {"type": "null"}]
            },
            "confidence": {"type": "number"},
        },
    },
}


# ─── HEIC detection & conversion ──────────────────────────────────────────────

def _is_heic(image_bytes: bytes, content_type: str) -> bool:
    """Определяет HEIC по content_type или по ftyp-сигнатуре в байтах.

    HEIC/HEIF файлы начинаются с ISO Base Media File Format box:
      bytes 4–7: 'ftyp'
      bytes 8–11: brand ('heic', 'heif', 'mif1' и подобные)
    """
    ct = content_type.lower()
    if ct in ("image/heic", "image/heif"):
        return True
    # Проверка ftyp box (минимум 12 байт)
    if len(image_bytes) >= 12:
        box_type = image_bytes[4:8]
        brand = image_bytes[8:12]
        if box_type == b"ftyp" and brand[:3] in (b"hei", b"mif"):
            return True
    return False


def _register_heif_opener() -> None:
    """Регистрирует pillow_heif в Pillow (lazy import)."""
    import pillow_heif  # noqa: PLC0415
    pillow_heif.register_heif_opener()


def _convert_heic_to_jpeg(image_bytes: bytes) -> bytes:
    """Конвертирует HEIC-байты в JPEG через pillow_heif + Pillow."""
    _register_heif_opener()
    from PIL import Image  # noqa: PLC0415
    img = Image.open(io.BytesIO(image_bytes))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ─── lazy OpenAI client ───────────────────────────────────────────────────────

def _get_openai_client():
    """Lazy-init AsyncOpenAI клиент.

    Возвращает None если пакет не установлен или ключ пуст.
    Зеркалит паттерн _get_anthropic_client из grading.py.
    """
    global _openai_client
    if _openai_client is None:
        try:
            import openai  # noqa: PLC0415
            from core.config import settings  # noqa: PLC0415
            if settings.openai_api_key:
                _openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        except ImportError:
            logger.warning("openai package не установлен, vision diagnosis недоступен")
    return _openai_client


# ─── grounded prompt ──────────────────────────────────────────────────────────

def _build_prompt(
    *,
    statement: str,
    canonical_steps: list[dict],
    correct_answer: str,
    wrong_answer: str | None,
    fingerprint_hint: str | None,
) -> str:
    """Формирует grounded промпт на русском для диагностики ошибки."""
    steps_text = "\n".join(
        f"  Шаг {s.get('n', i + 1)}: {s.get('instruction_ru', '')} → {s.get('expected_value', '')}"
        for i, s in enumerate(canonical_steps)
    )

    wrong_part = f"Неправильный ответ ученика: {wrong_answer}" if wrong_answer else "Ответ не указан."
    hint_part = f"\nПодсказка о типе ошибки (fingerprint): {fingerprint_hint}" if fingerprint_hint else ""

    return (
        "Ты — математический тьютор. Проанализируй рукописное решение ученика на фото.\n\n"
        f"ЗАДАЧА:\n{statement}\n\n"
        f"КАНОНИЧЕСКОЕ РЕШЕНИЕ (эталонные шаги):\n{steps_text}\n\n"
        f"ПРАВИЛЬНЫЙ ОТВЕТ: {correct_answer}\n"
        f"{wrong_part}{hint_part}\n\n"
        "ИНСТРУКЦИЯ:\n"
        "1. Прочитай рукопись дословно (поле transcription).\n"
        "2. Найди шаг (failed_step), где решение ученика расходится с эталоном "
        "   (номер шага из канонического списка, или null если неясно).\n"
        "3. Напиши краткий сократический комментарий (cause_text): ЧТО именно пошло не так. "
        "   НИКОГДА не раскрывай финальный ответ напрямую.\n"
        "4. Укажи сложность ошибки level (1=вычислительная, 2=концептуальная, 3=системная).\n"
        "5. Если определяешь конкретный micro-навык (micro_skill) — укажи snake_case идентификатор, иначе null.\n"
        "6. Укажи свою уверенность confidence от 0.0 до 1.0.\n\n"
        "Отвечай строго в указанной JSON-схеме."
    )


# ─── основная функция ─────────────────────────────────────────────────────────

async def diagnose_photo(
    *,
    image_bytes: bytes,
    content_type: str,
    statement: str,
    canonical_steps: list[dict],
    correct_answer: str,
    wrong_answer: str | None,
    fingerprint_hint: str | None,
) -> DiagnosisResult:
    """Диагностирует ошибку в рукописном решении по фото.

    Args:
        image_bytes:      Сырые байты изображения (PNG/JPEG/HEIC).
        content_type:     MIME-тип ('image/png', 'image/jpeg', 'image/heic', ...).
        statement:        Условие задачи (текст).
        canonical_steps:  Список шагов решения [{'n':1, 'instruction_ru':..., 'expected_value':...}].
        correct_answer:   Правильный ответ на задачу.
        wrong_answer:     Ответ ученика (может быть None).
        fingerprint_hint: Подсказка о типе ошибки из fingerprint-таблицы (может быть None).

    Returns:
        DiagnosisResult с расшифровкой рукописи и локализованной ошибкой.

    Raises:
        LlmUnavailable: Если ключ не задан или все модели в chain недоступны.
    """
    client = _get_openai_client()
    if client is None:
        raise LlmUnavailable(
            "OpenAI клиент недоступен: пустой OPENAI_API_KEY или пакет openai не установлен."
        )

    # HEIC → JPEG если нужно (OpenAI не принимает HEIC)
    actual_bytes = image_bytes
    actual_mime = content_type
    if _is_heic(image_bytes, content_type):
        logger.info("Detected HEIC image, converting to JPEG")
        actual_bytes = _convert_heic_to_jpeg(image_bytes)
        actual_mime = "image/jpeg"

    # Формируем base64 data URL
    b64 = base64.b64encode(actual_bytes).decode("ascii")
    data_url = f"data:{actual_mime};base64,{b64}"

    prompt_text = _build_prompt(
        statement=statement,
        canonical_steps=canonical_steps,
        correct_answer=correct_answer,
        wrong_answer=wrong_answer,
        fingerprint_hint=fingerprint_hint,
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {"url": data_url, "detail": "high"},
                },
            ],
        }
    ]

    from core.config import settings  # noqa: PLC0415

    last_exc: Exception | None = None
    for model in settings.openai_model_chain:
        try:
            logger.debug("Attempting OpenAI model: %s", model)
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_schema", "json_schema": _DIAGNOSIS_JSON_SCHEMA},
                    max_tokens=1024,
                ),
                timeout=_OPENAI_TIMEOUT,
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            return DiagnosisResult(
                transcription=data["transcription"],
                failed_step=data.get("failed_step"),
                cause_text=data["cause_text"],
                level=int(data["level"]),
                micro_skill=data.get("micro_skill"),
                confidence=float(data["confidence"]),
            )
        except asyncio.TimeoutError as exc:
            logger.warning("OpenAI timeout (model=%s, %.1fs)", model, _OPENAI_TIMEOUT)
            last_exc = exc
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI error (model=%s): %s", model, exc)
            last_exc = exc

    raise LlmUnavailable(
        f"Все модели в openai_model_chain недоступны. Последняя ошибка: {last_exc}"
    )
