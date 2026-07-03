"""Схема Блока 1.2: таблица step_submissions создаётся метадатой (модель StepSubmission)."""
from __future__ import annotations

import os
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_step_submissions_table_exists_with_expected_columns(db_session):
    cols = (await db_session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'step_submissions'"
    ))).scalars().all()
    expected = {
        "id",
        "student_id",
        "decomp_idx",
        "step_n",
        "problem_id",
        "verdict",
        "confidence",
        "matched_micro_skill",
        "photo_path",
        "created_at",
    }
    assert expected.issubset(set(cols))


@pytest.mark.asyncio
async def test_step_submissions_table_inserts(db_session, seeded_student):
    await db_session.execute(text(
        "INSERT INTO step_submissions (student_id, decomp_idx, step_n, verdict, photo_path) "
        "VALUES (:sid, 1, 1, 'match', 'foo.jpg')"
    ), {"sid": seeded_student})
    await db_session.commit()
    n = (await db_session.execute(text("SELECT count(*) FROM step_submissions"))).scalar()
    assert n == 1
