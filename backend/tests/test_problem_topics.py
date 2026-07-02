"""Тесты агрегата проблемных тем + SQL-инвариант error_count."""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from sqlalchemy import text


async def _seed(session, sid=9300):
    await session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": sid})
    await session.execute(text(
        "INSERT INTO topics (id, strand, grade, order_idx, name_ru, name_kz) "
        "VALUES ('6.PC', 'PC', 6, 1, 'Проценты', 'Пайыздар') ON CONFLICT (id) DO NOTHING"
    ))
    await session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, topic_id, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('PC02', 'Проценты', 'Пайыздар', '6.PC', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    pid = (await session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer) VALUES ('PC02', 'q', '1') RETURNING id"
    ))).scalar_one()
    # 3 error_captures на PC02
    for i in range(3):
        await session.execute(text(
            "INSERT INTO error_captures (student_id, problem_id, node_id, image_ref, created_at) "
            "VALUES (:sid, :pid, 'PC02', :img, NOW())"
        ), {"sid": sid, "pid": pid, "img": f"x/{i}.jpg"})
    await session.execute(text(
        "INSERT INTO recurring_errors (student_id, micro_skill, node_id, error_count, resolved, created_at) "
        "VALUES (:sid, 'percent_base', 'PC02', 3, false, NOW()) ON CONFLICT DO NOTHING"
    ), {"sid": sid})
    await session.execute(text(
        "INSERT INTO recurring_errors (student_id, micro_skill, node_id, error_count, resolved, created_at) "
        "VALUES (:sid, 'percent_change', 'PC02', 1, true, NOW()) ON CONFLICT DO NOTHING"
    ), {"sid": sid})
    await session.commit()
    return pid


@pytest.mark.asyncio
async def test_problem_topics_invariant(db_session):
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL не задан")
    from core.trainer import build_problem_topics

    await _seed(db_session)
    rows = await build_problem_topics(db_session, 9300)
    pc = next(r for r in rows if r.topic_id == "6.PC")

    # SQL-инвариант: error_count == raw count error_captures по topic
    raw = (await db_session.execute(text(
        "SELECT COUNT(*) FROM error_captures ec "
        "JOIN problems p ON p.id = ec.problem_id "
        "JOIN nodes n ON n.id = p.node_id "
        "WHERE n.topic_id = '6.PC' AND ec.student_id = 9300"
    ))).scalar_one()
    assert pc.error_count == raw == 3
    assert "percent_base" in pc.top_micro_skills
    # closure_progress = 1 resolved из 2 = 0.5
    assert abs(pc.closure_progress - 0.5) < 1e-9


@pytest.mark.asyncio
async def test_problem_topics_empty_student(db_session):
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL не задан")
    from core.trainer import build_problem_topics

    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (9399, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ))
    await db_session.commit()
    rows = await build_problem_topics(db_session, 9399)
    assert rows == []
