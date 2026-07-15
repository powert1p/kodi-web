"""Persistence schema server-owned learning sessions."""

from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_learning_tables_exist(db_session):
    rows = await db_session.execute(
        text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' "
            "  AND tablename = ANY(:names)"
        ),
        {"names": ["learning_sessions", "learning_attempts"]},
    )

    assert {row.tablename for row in rows} == {
        "learning_sessions",
        "learning_attempts",
    }


@pytest.mark.asyncio
async def test_learning_schema_has_resume_and_idempotency_constraints(db_session):
    constraints = await db_session.execute(
        text(
            "SELECT conname FROM pg_constraint "
            "WHERE conname = ANY(:names)"
        ),
        {
            "names": [
                "uq_learning_session_student_lesson_version",
                "uq_learning_attempt_session_client",
            ]
        },
    )

    assert {row.conname for row in constraints} == {
        "uq_learning_session_student_lesson_version",
        "uq_learning_attempt_session_client",
    }
