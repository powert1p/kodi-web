"""Мини-срез: выбор задач (разброс тем, difficulty ASC, исключение решённых) + API."""
from __future__ import annotations

import os
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-chars")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TEST_URL = os.getenv("TEST_DATABASE_URL")


async def _seed_graph(db_session):
    # 3 темы, по 2 узла, по 2 задачи — хватит проверить разброс и исключение решённых.
    # ⚠️ asyncpg требует уникальный $N на каждое употребление bind-параметра, даже
    # если значение совпадает: одинаковый :t на VARCHAR(id) и TEXT(name_ru/name_kz)
    # даёт AmbiguousParameterError (типы деduced по-разному) — используем разные ключи.
    for tid in ("T1", "T2", "T3"):
        await db_session.execute(text(
            "INSERT INTO topics (id, strand, name_ru, name_kz, order_idx) "
            "VALUES (:t, 'RP', :t_name, :t_name, 0) ON CONFLICT (id) DO NOTHING"
        ), {"t": tid, "t_name": tid})
    diff = {"N1": 1, "N2": 2, "N3": 3}
    topic = {"N1": "T1", "N2": "T2", "N3": "T3"}
    for nid in ("N1", "N2", "N3"):
        await db_session.execute(text(
            "INSERT INTO nodes (id, name_ru, name_kz, difficulty, topic_id, bkt_p_t, bkt_p_g, bkt_p_s) "
            "VALUES (:n, :n_name, :n_name, :d, :t, 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
        ), {"n": nid, "n_name": nid, "d": diff[nid], "t": topic[nid]})
    ids = {}
    for nid in ("N1", "N2", "N3"):
        pid = (await db_session.execute(text(
            "INSERT INTO problems (node_id, text_ru, answer, answer_type) "
            "VALUES (:n, 'задача '||:n_text, '5', 'number') RETURNING id"
        ), {"n": nid, "n_text": nid})).scalar_one()
        ids[nid] = pid
    await db_session.commit()
    return ids


async def _seed_graph_spread(db_session):
    """Сид с РАЗБРОСОМ node.difficulty 1..5 (у каждого узла — своя тема, 1 задача).
    Нужен, чтобы проверить окно среза по классу. Возвращает {node_id: (difficulty, problem_id)}.

    Раскладка задумана так, чтобы окна классов имели ≥ бюджета кандидатов И не пустой
    добор снизу/стретч сверху:
      grade 7 [3,5] → в окне 15, ниже 8, стретча нет (верх шкалы);
      grade 5 [2,3] → в окне 12, стретч (d4/d5) есть, ниже (d1) не добираем.
    """
    spread = {1: 2, 2: 6, 3: 6, 4: 6, 5: 3}
    out: dict[str, tuple[int, int]] = {}
    for diff, cnt in spread.items():
        for i in range(cnt):
            nid = f"S{diff}{i}"
            tid = f"TS{diff}{i}"
            await db_session.execute(text(
                "INSERT INTO topics (id, strand, name_ru, name_kz, order_idx) "
                "VALUES (:t, 'RP', :t_name, :t_name, 0) ON CONFLICT (id) DO NOTHING"
            ), {"t": tid, "t_name": tid})
            await db_session.execute(text(
                "INSERT INTO nodes (id, name_ru, name_kz, difficulty, topic_id, bkt_p_t, bkt_p_g, bkt_p_s) "
                "VALUES (:n, :n_name, :n_name, :d, :t, 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
            ), {"n": nid, "n_name": nid, "d": diff, "t": tid})
            pid = (await db_session.execute(text(
                "INSERT INTO problems (node_id, text_ru, answer, answer_type) "
                "VALUES (:n, 'задача '||:n_text, '5', 'number') RETURNING id"
            ), {"n": nid, "n_text": nid})).scalar_one()
            out[nid] = (diff, pid)
    await db_session.commit()
    return out


@pytest.mark.asyncio
async def test_pick_srez_grade7_no_easy(db_session):
    """grade=7 → окно [3,5]: 0 задач difficulty 1 и ≥80% difficulty ≥3 (критерий приёмки 1b)."""
    from core.srez import pick_srez_problems
    await _seed_graph_spread(db_session)
    rows = await pick_srez_problems(db_session, student_id=101, count=12, grade=7)
    diffs = [r.node_difficulty for r in rows]
    assert diffs, "срез не должен быть пустым"
    assert 1 not in diffs                      # «23+45» новичку-семикласснику не показываем
    assert 2 not in diffs                      # difficulty 2 тоже ниже окна [3,5]
    share_hard = sum(1 for d in diffs if d >= 3) / len(diffs)
    assert share_hard >= 0.8                   # ≥80% задач difficulty ≥3


@pytest.mark.asyncio
async def test_pick_srez_grade5_stretch(db_session):
    """grade=5 → окно [2,3] + ровно 2 стретча (>3). Ниже окна не добираем, пока в окне есть кандидаты."""
    from core.srez import pick_srez_problems
    await _seed_graph_spread(db_session)
    rows = await pick_srez_problems(db_session, student_id=102, count=12, grade=5)
    diffs = [r.node_difficulty for r in rows]
    assert 1 not in diffs                      # в окне достаточно кандидатов → лёгкое не добираем
    stretch = [d for d in diffs if d > 3]
    assert len(stretch) == 2                   # 2 стретч-задачи выше окна
    assert all(d >= 4 for d in stretch)


@pytest.mark.asyncio
async def test_pick_srez_grade_null_ok(db_session):
    """grade=None → окно по умолчанию [2,4]: старый вызов (без grade) не падает и даёт задачи."""
    from core.srez import pick_srez_problems
    await _seed_graph_spread(db_session)
    rows = await pick_srez_problems(db_session, student_id=103, count=12)  # без grade
    assert len(rows) > 0
    diffs = [r.node_difficulty for r in rows]
    assert 1 not in diffs                      # дефолт [2,4] — крайний низ не берём (в окне есть кандидаты)


@pytest.mark.asyncio
async def test_pick_srez_distinct_topics_and_difficulty(db_session):
    from core.srez import pick_srez_problems
    await _seed_graph(db_session)
    rows = await pick_srez_problems(db_session, student_id=1, count=12)
    # Разброс: не более одной задачи на topic
    topics = [r.topic_key for r in rows]
    assert len(topics) == len(set(topics))
    # difficulty ASC
    diffs = [r.node_difficulty for r in rows]
    assert diffs == sorted(diffs)


@pytest.mark.asyncio
async def test_pick_srez_excludes_attempted(db_session):
    from core.srez import pick_srez_problems
    ids = await _seed_graph(db_session)
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (7, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ))
    await db_session.execute(text(
        "INSERT INTO attempts (student_id, problem_id, node_id, answer_given, is_correct, source, created_at) "
        "VALUES (7, :pid, 'N1', '5', true, 'diagnostic', NOW())"
    ), {"pid": ids["N1"]})
    await db_session.commit()
    rows = await pick_srez_problems(db_session, student_id=7, count=12)
    assert ids["N1"] not in [r.id for r in rows]


@pytest_asyncio.fixture
async def sclient(db_session):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    ids = await _seed_graph(db_session)
    SID = 9600
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.commit()
    from api.routes import _create_token
    token = _create_token(SID)
    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    eng = create_async_engine(_TEST_URL)
    fac = async_sessionmaker(eng, expire_on_commit=False)
    o1, o2 = db_base.async_session, routes_module.async_session
    db_base.async_session = fac
    routes_module.async_session = fac
    from web import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, token, ids, SID
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_srez_start_and_answer_flow(sclient, db_session):
    ac, token, ids, sid = sclient
    h = {"Authorization": f"Bearer {token}"}
    r = await ac.post("/api/trainer/srez/start", headers=h, json={})
    assert r.status_code == 200
    tasks = r.json()["tasks"]
    assert len(tasks) >= 1
    assert "answer" not in tasks[0]        # НЕ палим правильный ответ
    assert "solution" not in tasks[0]
    first = tasks[0]
    # Отвечаем неверно
    a = await ac.post("/api/trainer/srez/answer", headers=h,
                      json={"problem_id": first["problem_id"], "answer": "-999", "elapsed_ms": 1000})
    assert a.status_code == 200
    assert a.json()["is_correct"] is False
    # attempt записан как diagnostic → build_wrong_tasks его увидит
    n = (await db_session.execute(text(
        "SELECT count(*) FROM attempts WHERE student_id = :sid AND source = 'diagnostic' AND is_correct = false"
    ), {"sid": sid})).scalar()
    assert n == 1
