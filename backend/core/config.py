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
    admin_id: int = int(os.getenv("ADMIN_ID", "0"))
    tester_ids: list[int] = field(
        default_factory=lambda: _parse_id_list(os.getenv("TESTER_IDS", "745533750"))
    )
    public_url: str = os.getenv("PUBLIC_URL", "") or (
        f"https://{d}" if (d := os.getenv("RAILWAY_PUBLIC_DOMAIN")) else "http://localhost:8000"
    )
    port: int = int(os.getenv("PORT", "8000"))
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    def is_privileged(self, user_id: int) -> bool:
        """True for admin and testers — they see correct answers in questions."""
        return user_id == self.admin_id or user_id in self.tester_ids


settings = Settings()
