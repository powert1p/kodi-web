"""Тесты build_agent_context — сборка grounding-пакета из БД."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from sqlalchemy import text


async def _seed(session):
    await session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (9200, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ))
    await session.execute(text(
        "INSERT INTO topics (id, strand, grade, order_idx, name_ru, name_kz) "
        "VALUES ('6.PC', 'PC', 6, 1, 'Проценты', 'Пайыздар') ON CONFLICT (id) DO NOTHING"
    ))
    await session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, topic_id, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('PC02', 'Проценты', 'Пайыздар', '6.PC', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    pid = (await session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer) VALUES ('PC02', 'Найди 20% от 800', '160') RETURNING id"
    ))).scalar_one()
    await session.execute(text(
        "INSERT INTO decomposition_problems (idx, node_id, answer, primary_micro_skill, all_steps_verified, problems_db_id) "
        "VALUES (99001, 'PC02', '160', 'percent_base', true, :pid)"
    ), {"pid": pid})
    await session.execute(text(
        "INSERT INTO problem_steps (decomp_idx, n, instruction_ru, micro_skill, expected_value) "
        "VALUES (99001, 1, 'Перевести процент в дробь', 'percent_to_frac', '0.2')"
    ))
    await session.execute(text(
        "INSERT INTO problem_fingerprints (decomp_idx, micro_skill, wrong_answer, mistake_ru) "
        "VALUES (99001, 'percent_base', '20', 'Взял процент как число')"
    ))
    await session.execute(text(
        "INSERT INTO mastery (student_id, node_id, p_mastery, attempts_total, attempts_correct) "
        "VALUES (9200, 'PC02', 0.42, 0, 0) "
        "ON CONFLICT (student_id, node_id) DO UPDATE SET p_mastery = 0.42"
    ))
    await session.execute(text(
        "INSERT INTO recurring_errors (student_id, micro_skill, node_id, error_count, last_cause_text, resolved, created_at) "
        "VALUES (9200, 'percent_base', 'PC02', 4, 'Путает базу', false, NOW()) "
        "ON CONFLICT (student_id, micro_skill) DO NOTHING"
    ))
    await session.commit()
    return pid


@pytest.mark.asyncio
async def test_build_agent_context_full(db_session):
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL не задан")
    from core.agent_context import build_agent_context

    pid = await _seed(db_session)
    ctx = await build_agent_context(db_session, student_id=9200, problem_id=pid)

    assert ctx.node_id == "PC02"
    assert ctx.correct_answer == "160"
    assert ctx.canonical_steps and ctx.canonical_steps[0]["instruction_ru"] == "Перевести процент в дробь"
    assert any(f["mistake_ru"] == "Взял процент как число" for f in ctx.fingerprints)
    assert abs(ctx.node_mastery - 0.42) < 1e-9
    assert any(r["micro_skill"] == "percent_base" for r in ctx.recurring_errors)
    assert ctx.topic and ctx.topic["name_ru"] == "Проценты"


@pytest.mark.asyncio
async def test_build_agent_context_unknown_problem(db_session):
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL не задан")
    from core.agent_context import build_agent_context

    with pytest.raises(ValueError):
        await build_agent_context(db_session, student_id=9200, problem_id=987654)
