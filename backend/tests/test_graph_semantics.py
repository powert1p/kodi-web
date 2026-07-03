"""Семантический тест-гейт графа знаний v02 (docs/specs/2026-07-03-graph-v02-verdict.md).

Чистые проверки JSON-источников, БЕЗ БД (не требует TEST_DATABASE_URL, не скипается).
Инварианты после чистки: ацикличность DAG, отсутствие dangling-ссылок, metadata
счётчики == фактическим данным, покрытие узлов темами, отсутствие "лишних" пустых
тем/узлов, консистентность problems ↔ граф.
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_GRAPH_PATH = _DATA_DIR / "nis_knowledge_graph_v01.json"
_TOPICS_PATH = _DATA_DIR / "cc_topics_v01.json"
_PROBLEMS_PATH = _DATA_DIR / "problems_v10.json"

# Известное расхождение с вердиктом v02 (зафиксировано осознанно, см.
# backend/scripts/apply_graph_v02.py и раздел 5 вердикта): RETAG DA01/DA02
# (3.MD.B → 6.SP.B, оба узла разом) осиротяет тему 3.MD.B — вердикт этого не
# учёл. Не чиним от себя — фиксируем как разрешённое исключение.
ALLOWED_EMPTY_TOPICS = {"3.MD.B"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _graph() -> dict:
    return _load(_GRAPH_PATH)


def _topics() -> dict:
    return _load(_TOPICS_PATH)


def _problems() -> list[dict]:
    return _load(_PROBLEMS_PATH)["problems"]


def test_graph_is_acyclic():
    """Kahn's algorithm: prereq→node не образует циклов."""
    g = _graph()
    node_ids = {n["id"] for n in g["nodes"]}
    indegree = {nid: 0 for nid in node_ids}
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for n in g["nodes"]:
        for prereq in n["prerequisites"]:
            adjacency[prereq].append(n["id"])
            indegree[n["id"]] += 1

    queue = [nid for nid, deg in indegree.items() if deg == 0]
    visited = 0
    while queue:
        nid = queue.pop()
        visited += 1
        for nxt in adjacency[nid]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    assert visited == len(node_ids), "граф содержит цикл(ы) — DAG нарушен"


def test_no_dangling_prereqs():
    """Каждая ссылка prerequisites указывает на существующий узел."""
    g = _graph()
    node_ids = {n["id"] for n in g["nodes"]}
    for n in g["nodes"]:
        for prereq in n["prerequisites"]:
            assert prereq in node_ids, f"узел {n['id']}: несуществующий prereq {prereq}"


def test_metadata_counts_match_actual():
    """metadata.total_nodes/total_edges графа == фактическим числам после v02."""
    g = _graph()
    assert g["metadata"]["total_nodes"] == len(g["nodes"]) == 114
    actual_edges = sum(len(n["prerequisites"]) for n in g["nodes"])
    assert g["metadata"]["total_edges"] == actual_edges


def test_every_node_has_topic():
    """Каждый узел графа привязан к существующей теме."""
    g = _graph()
    t = _topics()
    node_ids = {n["id"] for n in g["nodes"]}
    topic_ids = {x["id"] for x in t["topics"]}
    assert set(t["node_topic"].keys()) == node_ids, (
        "node_topic не покрывает ровно множество узлов графа"
    )
    for nid, tid in t["node_topic"].items():
        assert tid in topic_ids, f"узел {nid} → несуществующая тема {tid}"


def test_no_unexpected_empty_topics():
    """Каждая тема имеет ≥1 узел, кроме осознанно разрешённого списка (см. ALLOWED_EMPTY_TOPICS)."""
    t = _topics()
    topic_ids = {x["id"] for x in t["topics"]}
    assert len(topic_ids) == 37

    node_count_by_topic: dict[str, int] = {}
    for tid in t["node_topic"].values():
        node_count_by_topic[tid] = node_count_by_topic.get(tid, 0) + 1

    empty_topics = {tid for tid in topic_ids if node_count_by_topic.get(tid, 0) == 0}
    assert empty_topics == ALLOWED_EMPTY_TOPICS, (
        f"неожиданные пустые темы: {empty_topics - ALLOWED_EMPTY_TOPICS}"
    )


def test_all_problem_node_ids_exist_in_graph():
    """Каждая задача problems_v10.json ссылается на существующий узел графа."""
    g = _graph()
    node_ids = {n["id"] for n in g["nodes"]}
    problems = _problems()
    dangling = {p["node_id"] for p in problems} - node_ids
    assert not dangling, f"problems ссылаются на несуществующие узлы: {dangling}"


def test_no_nodes_with_empty_exam_questions():
    """После чистки (DELETE NM01/NM02/NM03/ALG01) узлов без exam_questions быть не должно."""
    g = _graph()
    empty = [n["id"] for n in g["nodes"] if not n["exam_questions"]]
    assert empty == [], f"узлы без exam_questions (не ожидались после v02): {empty}"


def test_no_duplicate_node_names():
    """Нет двух узлов с одинаковым name_ru (дубли-кандидаты на слияние — не задача этого гейта)."""
    g = _graph()
    names = [n["name_ru"] for n in g["nodes"]]
    dups = {name for name in names if names.count(name) > 1}
    assert not dups, f"дублирующиеся name_ru: {dups}"
