"""Идемпотентность и инварианты сида слоя тем (integration, реальный Postgres)."""

import pytest
from sqlalchemy import text

from db.seed import seed_graph, seed_topics


async def test_seed_topics_idempotent(db_session):
    await seed_graph(db_session)
    n1 = await seed_topics(db_session)
    n2 = await seed_topics(db_session)  # повторный прогон не падает и не плодит дублей
    assert n1 == n2 == 43

    topics = (await db_session.execute(text("SELECT count(*) FROM topics"))).scalar()
    edges = (await db_session.execute(text("SELECT count(*) FROM topic_edges"))).scalar()
    orphans = (await db_session.execute(
        text("SELECT count(*) FROM nodes WHERE topic_id IS NULL"))).scalar()
    nodes = (await db_session.execute(text("SELECT count(*) FROM nodes"))).scalar()
    assert topics == 43
    assert edges == 61
    assert nodes == 118
    assert orphans == 0  # все 118 узлов привязаны к теме
