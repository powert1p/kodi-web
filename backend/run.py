"""Standalone web server entry point.

Usage: python run.py
"""

import asyncio
import logging

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
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS practice_count INTEGER DEFAULT 0",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS current_practice_node VARCHAR(10)",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS problems_on_current_node INTEGER DEFAULT 0",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS pin_hash VARCHAR(128)",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS paused_diagnostic JSONB",
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
    config = uvicorn.Config(app, host="0.0.0.0", port=settings.port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
