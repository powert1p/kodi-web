from __future__ import annotations

import os
import secrets
import math
from dataclasses import dataclass, field

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()


def _fix_database_url(url: str) -> str:
    """Ensure the URL uses the asyncpg driver.

    Railway and other PaaS providers give a plain ``postgresql://`` URL.
    SQLAlchemy async requires ``postgresql+asyncpg://``.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _database_url_from_env() -> str | URL:
    """Строит async URL без небезопасной подстановки пароля в compose-строку."""
    explicit = os.getenv("DATABASE_URL", "").strip()
    if explicit:
        return _fix_database_url(explicit)

    host = os.getenv("DB_HOST", "").strip()
    if host:
        return URL.create(
            "postgresql+asyncpg",
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            host=host,
            port=int(os.getenv("DB_PORT", "5432").strip()),
            database=os.getenv("DB_NAME", "postgres"),
        )

    return "postgresql+asyncpg://postgres:postgres@localhost:5432/nismathbot"


def _parse_id_list(raw: str) -> list[int]:
    """Parse comma-separated list of Telegram user IDs."""
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


def _parse_probability_env(name: str, default: str) -> float:
    raw = os.getenv(name, default)
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} должен быть числом от 0 (не включая) до 1.") from exc
    if not math.isfinite(value) or not 0.0 < value <= 1.0:
        raise RuntimeError(f"{name} должен быть числом от 0 (не включая) до 1.")
    return value


@dataclass
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    database_url: str | URL = field(default_factory=_database_url_from_env)
    admin_ids: list[int] = field(
        default_factory=lambda: _parse_id_list(os.getenv("ADMIN_ID", "0"))
    )
    tester_ids: list[int] = field(
        default_factory=lambda: _parse_id_list(os.getenv("TESTER_IDS", "745533750"))
    )
    public_url: str = os.getenv("PUBLIC_URL", "") or (
        f"https://{d}" if (d := os.getenv("RAILWAY_PUBLIC_DOMAIN")) else "http://localhost:8000"
    )
    port: int = int(os.getenv("PORT", "8000"))
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    # Vision-провайдер: "gemini" (default) или "openai"
    vision_provider: str = os.getenv("VISION_PROVIDER", "gemini")
    # Gemini Vision — диагностика фото-решений через OpenAI-совместимый endpoint
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model_chain: list[str] = field(
        default_factory=lambda: (
            [m.strip() for m in os.getenv("GEMINI_MODEL_CHAIN", "").split(",") if m.strip()]
            or ["gemini-3.5-flash", "gemini-3.1-flash-lite"]
        )
    )
    # OpenAI Vision — запасной провайдер (VISION_PROVIDER=openai)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model_chain: list[str] = field(
        default_factory=lambda: (
            [m.strip() for m in os.getenv("OPENAI_MODEL_CHAIN", "").split(",") if m.strip()]
            or ["gpt-5.4-mini", "gpt-5.4-nano", "gpt-4o-mini"]
        )
    )
    # Папка для хранения загруженных фото ошибок
    photo_dir: str = os.getenv(
        "PHOTO_DIR",
        os.path.join(os.path.dirname(__file__), "..", "data", "error_photos"),
    )
    # Порог уверенности для step-submit: mismatch с confidence ниже → трактуем как unsure
    step_confidence_threshold: float = field(
        default_factory=lambda: _parse_probability_env(
            "STEP_CONFIDENCE_THRESHOLD",
            "0.6",
        )
    )
    # Telegram user_id владельца (для owner-only функций)
    owner_student_id: int = int(os.getenv("OWNER_STUDENT_ID", "0") or 0)
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    def is_privileged(self, user_id: int) -> bool:
        """True for admin and testers — they see correct answers in questions."""
        return user_id in self.admin_ids or user_id in self.tester_ids


settings = Settings()

# Fail-fast: слабый/переиспользованный ключ подписи = подмена пользователя.
jwt_secret = settings.jwt_secret.strip()
if len(jwt_secret.encode("utf-8")) < 32:
    raise RuntimeError(
        "JWT_SECRET должен быть задан и содержать не менее 32 байт."
    )
if settings.bot_token.strip() and secrets.compare_digest(
    jwt_secret,
    settings.bot_token.strip(),
):
    raise RuntimeError("JWT_SECRET не должен совпадать с BOT_TOKEN.")

if settings.vision_provider not in {"gemini", "openai"}:
    raise RuntimeError(
        "VISION_PROVIDER должен быть одним из значений: gemini, openai."
    )
