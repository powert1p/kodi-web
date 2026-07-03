from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

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


def _parse_id_list(raw: str) -> list[int]:
    """Parse comma-separated list of Telegram user IDs."""
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


@dataclass
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    database_url: str = field(default_factory=lambda: _fix_database_url(
        os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/nismathbot",
        )
    ))
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
    jwt_secret: str = os.getenv("JWT_SECRET") or os.getenv("BOT_TOKEN", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    # Vision-провайдер: "gemini" (default) или "openai"
    vision_provider: str = os.getenv("VISION_PROVIDER", "gemini")
    # Gemini Vision — диагностика фото-решений через OpenAI-совместимый endpoint
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model_chain: list[str] = field(
        default_factory=lambda: (
            [m.strip() for m in os.getenv("GEMINI_MODEL_CHAIN", "").split(",") if m.strip()]
            or ["gemini-2.5-flash", "gemini-2.0-flash"]
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
    step_confidence_threshold: float = float(os.getenv("STEP_CONFIDENCE_THRESHOLD", "0.6"))
    # Telegram user_id владельца (для owner-only функций)
    owner_student_id: int = int(os.getenv("OWNER_STUDENT_ID", "0") or 0)
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    def is_privileged(self, user_id: int) -> bool:
        """True for admin and testers — they see correct answers in questions."""
        return user_id in self.admin_ids or user_id in self.tester_ids


settings = Settings()

if not os.getenv("JWT_SECRET"):
    import logging as _log
    _log.getLogger(__name__).warning(
        "JWT_SECRET not set — falling back to BOT_TOKEN. "
        "Set JWT_SECRET in .env for production security."
    )

# Fail-fast: пустой ключ подписи = forgery токенов / полная подмена пользователя.
# Не стартуем без секрета — лучше явный отказ, чем тихая дыра в auth.
if not settings.jwt_secret.strip():
    raise RuntimeError(
        "JWT_SECRET не задан (и BOT_TOKEN тоже пуст). "
        "Установите JWT_SECRET в окружении — приложение не запускается "
        "с пустым ключом подписи JWT."
    )
