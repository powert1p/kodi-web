"""Идемпотентность и инварианты сида слоя тем (integration, реальный Postgres)."""

import pytest
from sqlalchemy import text

from db.seed import seed_graph, seed_topics
from db.models import Node


async def test_seed_graph_repairs_partial_database_without_overwriting_existing_nodes(
    db_session,
):
    db_session.add(
        Node(
            id="AR01",
            name_ru="Сохранённое название",
            name_kz="Сақталған атау",
            difficulty=1,
        )
    )
    await db_session.commit()

    n1 = await seed_graph(db_session)
    n2 = await seed_graph(db_session)

    nodes = (await db_session.execute(text("SELECT count(*) FROM nodes"))).scalar()
    edges = (await db_session.execute(text("SELECT count(*) FROM edges"))).scalar()
    preserved_name = (
        await db_session.execute(text("SELECT name_ru FROM nodes WHERE id = 'AR01'"))
    ).scalar_one()

    assert n1 == n2 == nodes == 114
    assert edges == 178
    assert preserved_name == "Сохранённое название"


async def test_seed_topics_idempotent(db_session):
    await seed_graph(db_session)
    n1 = await seed_topics(db_session)
    n2 = await seed_topics(db_session)  # повторный прогон не падает и не плодит дублей
    # 43/61/118 → 36/38/114 после чистки графа v02/v02.1 (docs/specs/2026-07-03-graph-v02-verdict.md):
    # удалены 7 пустых тем (6 изначально + осиротевшая 3.MD.B после RETAG DA01/DA02)
    # + их topic_edges, узлы NM01/NM02/NM03/ALG01 удалены из графа.
    assert n1 == n2 == 36

    topics = (await db_session.execute(text("SELECT count(*) FROM topics"))).scalar()
    edges = (await db_session.execute(text("SELECT count(*) FROM topic_edges"))).scalar()
    orphans = (await db_session.execute(
        text("SELECT count(*) FROM nodes WHERE topic_id IS NULL"))).scalar()
    nodes = (await db_session.execute(text("SELECT count(*) FROM nodes"))).scalar()
    assert topics == 36
    assert edges == 38
    assert nodes == 114
    assert orphans == 0  # все 114 узлов привязаны к теме
