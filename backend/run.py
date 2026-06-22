"""Standalone web server entry point.

Usage: python run.py
"""

import asyncio
import logging
import os

import uvicorn
from sqlalchemy import text

from web import app
from core.config import settings
from db.base import Base, async_session, engine
from db.seed import seed_graph, seed_problems

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add columns that may be missing in existing DB
        for stmt in [
            # ── students table ──
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS practice_count INTEGER DEFAULT 0",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS current_practice_node VARCHAR(10)",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS problems_on_current_node INTEGER DEFAULT 0",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS pin_hash VARCHAR(128)",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS paused_diagnostic JSONB",
            # ── problem_reports table ──
            "ALTER TABLE problem_reports ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'open'",
            # TIMESTAMPTZ (не TIMESTAMP): колонка tz-aware в модели; иначе naive-vs-aware DataError
            # на resolved_at write (AI report-fix). На свежей БД no-op (create_all уже сделал tz-aware).
            "ALTER TABLE problem_reports ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ",
            "ALTER TABLE problem_reports ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(100)",
            "ALTER TABLE problem_reports ADD COLUMN IF NOT EXISTS comment TEXT DEFAULT ''",
            # ── fix NULLs in existing rows ──
            "UPDATE students SET practice_count = 0 WHERE practice_count IS NULL",
            "UPDATE students SET problems_on_current_node = 0 WHERE problems_on_current_node IS NULL",
        ]:
            await conn.execute(text(stmt))
    logger.info("DB tables ensured.")

    async with async_session() as session:
        count = (await session.execute(text("SELECT count(*) FROM nodes"))).scalar()
        if count == 0:
            logger.info("Seeding graph + problems...")
            await seed_graph(session)
            await seed_problems(session)
            await session.commit()
            logger.info("Seed complete.")
        else:
            logger.info("DB already seeded (%d nodes).", count)


async def main():
    await on_startup()
    # За host-nginx доверяем X-Forwarded-* → реальный IP клиента (иначе slowapi
    # лочит всех в один bucket как 127.0.0.1). Single-worker не трогаем —
    # _diagnostic_states process-local.
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.port,
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips=os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"),
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
