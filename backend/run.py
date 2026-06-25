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
from db.seed import seed_graph, seed_problems, seed_topics

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
            # ── topics layer ──
            "ALTER TABLE nodes ADD COLUMN IF NOT EXISTS topic_id VARCHAR(20)",
            # ── fix NULLs in existing rows ──
            "UPDATE students SET practice_count = 0 WHERE practice_count IS NULL",
            "UPDATE students SET problems_on_current_node = 0 WHERE problems_on_current_node IS NULL",
            # ── тренажёр ошибок: банк декомпозиций ──
            # Каталог микро-умений (атомарные шаги решения)
            """
            CREATE TABLE IF NOT EXISTS micro_skills (
                code        VARCHAR(50) PRIMARY KEY,
                label_ru    TEXT        NOT NULL,
                domain      VARCHAR(50),
                freq        INTEGER
            )
            """,
            # Банк задач с декомпозицией (автономный, ключ = idx из JSON)
            """
            CREATE TABLE IF NOT EXISTS decomposition_problems (
                idx                 INTEGER     PRIMARY KEY,
                node_id             VARCHAR(10) NOT NULL REFERENCES nodes(id) ON DELETE RESTRICT,
                answer              TEXT        NOT NULL,
                primary_micro_skill VARCHAR(50),
                all_steps_verified  BOOLEAN     NOT NULL DEFAULT false,
                needs_review        BOOLEAN     NOT NULL DEFAULT false,
                problems_db_id      INTEGER     REFERENCES problems(id) ON DELETE SET NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_decomp_node ON decomposition_problems (node_id)",
            "CREATE INDEX IF NOT EXISTS idx_decomp_dbid  ON decomposition_problems (problems_db_id)",
            # Шаги решения задачи (FK → decomposition_problems.idx)
            """
            CREATE TABLE IF NOT EXISTS problem_steps (
                id              INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                decomp_idx      INTEGER     NOT NULL REFERENCES decomposition_problems(idx) ON DELETE CASCADE,
                n               INTEGER     NOT NULL,
                instruction_ru  TEXT        NOT NULL,
                micro_skill     VARCHAR(50) NOT NULL,
                expected_value  TEXT        NOT NULL,
                verified        VARCHAR(20)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_problem_steps_decomp ON problem_steps (decomp_idx)",
            # Отпечатки типичных ошибок (FK → decomposition_problems.idx)
            """
            CREATE TABLE IF NOT EXISTS problem_fingerprints (
                id          INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                decomp_idx  INTEGER     NOT NULL REFERENCES decomposition_problems(idx) ON DELETE CASCADE,
                micro_skill VARCHAR(50) NOT NULL,
                wrong_answer TEXT       NOT NULL,
                mistake_ru  TEXT        NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_problem_fingerprints_decomp ON problem_fingerprints (decomp_idx)",
            # ── тренажёр ошибок: захват и накопление ──
            # Один факт ошибки студента (из AI-анализа среза)
            """
            CREATE TABLE IF NOT EXISTS error_captures (
                id                  INTEGER         PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                student_id          BIGINT          NOT NULL REFERENCES students(id)  ON DELETE CASCADE,
                attempt_id          INTEGER         REFERENCES attempts(id)           ON DELETE SET NULL,
                problem_id          INTEGER         NOT NULL REFERENCES problems(id)  ON DELETE RESTRICT,
                node_id             VARCHAR(10)     NOT NULL,
                image_ref           TEXT            NOT NULL,
                transcription       TEXT,
                failed_step         INTEGER,
                failed_micro_skill  VARCHAR(50),
                cause_text          TEXT,
                level               SMALLINT,
                model               VARCHAR(50),
                confidence          FLOAT,
                created_at          TIMESTAMPTZ     NOT NULL DEFAULT now()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_error_captures_student_node ON error_captures (student_id, node_id)",
            "CREATE INDEX IF NOT EXISTS idx_error_captures_created_at   ON error_captures (created_at)",
            # Накопленная статистика повторяющихся ошибок (составной PK как у mastery)
            """
            CREATE TABLE IF NOT EXISTS recurring_errors (
                student_id      BIGINT      NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                micro_skill     VARCHAR(50) NOT NULL,
                node_id         VARCHAR(10),
                error_count     INTEGER     NOT NULL DEFAULT 0,
                last_seen_at    TIMESTAMPTZ,
                last_cause_text TEXT,
                resolved        BOOLEAN     NOT NULL DEFAULT false,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (student_id, micro_skill)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_recurring_errors_micro_skill ON recurring_errors (micro_skill)",
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

    # seed_topics вызывается всегда (и на свежей, и на уже засеянной БД) — идемпотентен
    async with async_session() as session:
        await seed_topics(session)


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
