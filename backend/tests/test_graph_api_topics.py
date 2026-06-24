"""Контракт API /graph/me: темы и разделы присутствуют, старые поля целы (integration)."""

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
