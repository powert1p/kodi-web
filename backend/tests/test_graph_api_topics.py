"""Контракт слоя тем (integration).

Тестирует generate_graph_data (HTML-экспорт) и общий хелпер build_topics_payload,
который питает и REST-роут /graph/me. Сам HTTP-роут /graph/me проверен live
(curl + Playwright против реального сервера) — здесь покрыта общая логика сборки.
"""

from sqlalchemy import select as _select

from db.seed import seed_graph, seed_topics
from core.web_graph import generate_graph_data


async def test_graph_data_has_topics_and_strands(db_session, seeded_student):
    await seed_graph(db_session)
    await seed_topics(db_session)
    data = await generate_graph_data(db_session, seeded_student, lang="ru")

    # старые поля целы
    for key in ("nodes", "edges", "stats", "personal_stats", "leaderboard"):
        assert key in data
    # новые поля
    assert "topics" in data and "strands" in data
    assert all("topic_id" in n for n in data["nodes"])
    assert len(data["topics"]) >= 1
    assert all(t["node_ids"] for t in data["topics"])  # только непустые темы
    # связность раздел↔тема
    strand_codes = {s["code"] for s in data["strands"]}
    assert all(t["strand"] in strand_codes for t in data["topics"])
    # имена разделов есть
    assert all(s["name_ru"] and s["name_kz"] for s in data["strands"])
    # сортировка по order
    assert [t["order"] for t in data["topics"]] == sorted(t["order"] for t in data["topics"])
    assert [s["order"] for s in data["strands"]] == sorted(s["order"] for s in data["strands"])
    # prereq — список строк
    for t in data["topics"]:
        assert isinstance(t["prereq"], list)


async def test_build_topics_payload_helper(db_session):
    """Детерминированная проверка хелпера build_topics_payload через seed-данные."""
    from db.models import Node, Topic, TopicEdge
    from core.web_graph import build_topics_payload

    await seed_graph(db_session)
    await seed_topics(db_session)

    topic_rows = list((await db_session.execute(_select(Topic))).scalars().all())
    edge_rows = (await db_session.execute(_select(TopicEdge.from_topic, TopicEdge.to_topic))).all()
    all_nodes = list((await db_session.execute(_select(Node))).scalars().all())

    topics_json, strands_json = build_topics_payload(topic_rows, edge_rows, all_nodes)

    # только непустые темы (у каждой есть хотя бы один узел)
    assert all(t["node_ids"] for t in topics_json)
    # темы отсортированы по order
    assert [t["order"] for t in topics_json] == sorted(t["order"] for t in topics_json)
    # все разделы тем присутствуют в strands
    assert {t["strand"] for t in topics_json} <= {s["code"] for s in strands_json}
    # сумма узлов по темам == число узлов с topic_id
    assert sum(len(t["node_ids"]) for t in topics_json) == sum(1 for n in all_nodes if n.topic_id)
