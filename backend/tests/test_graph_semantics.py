"""Семантический тест-гейт графа знаний v02+v03.

v02: docs/specs/2026-07-03-graph-v02-verdict.md.
v03: docs/specs/2026-07-06-graph-topic-audit-verdict.md (6 дропов + 3 добавления
рёбер, 3 переименования тем, 5 переносов задач).

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
    """metadata.total_nodes/total_edges графа == фактическим числам после v03 (178 = 181-6+3)."""
    g = _graph()
    assert g["metadata"]["total_nodes"] == len(g["nodes"]) == 114
    actual_edges = sum(len(n["prerequisites"]) for n in g["nodes"])
    assert g["metadata"]["total_edges"] == actual_edges == 178


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
    """Каждая тема имеет ≥1 узел (v02.1: 3.MD.B тоже удалена — пустых тем быть не должно)."""
    t = _topics()
    topic_ids = {x["id"] for x in t["topics"]}
    assert len(topic_ids) == 36

    node_count_by_topic: dict[str, int] = {}
    for tid in t["node_topic"].values():
        node_count_by_topic[tid] = node_count_by_topic.get(tid, 0) + 1

    empty_topics = {tid for tid in topic_ids if node_count_by_topic.get(tid, 0) == 0}
    assert not empty_topics, f"неожиданные пустые темы: {empty_topics}"


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


# ── v03: docs/specs/2026-07-06-graph-topic-audit-verdict.md ──────────────────

_V03_DROP_EDGES = [
    ("AR09", "CV04"), ("AR09", "CV05"), ("GE01", "GE12"),
    ("EQ02", "WP03"), ("DV02", "LG04"), ("AL01", "EQ02"),
]
_V03_ADD_EDGES = [
    ("AL02", "EQ02"), ("DC01", "AR07"), ("AR10", "LG04"),
]
_V03_EXPECTED_PREREQS = {
    "AR07": {"AR06", "DC01"},
    "LG04": {"AR06", "AR10"},
    "GE12": {"CB01"},
    "CV04": {"GE02"},
    "CV05": {"CV04"},
    "WP03": {"WP02"},
    "EQ02": {"EQ01", "AL02"},
}


def test_v03_edge_patch_applied():
    """6 дропнутых рёбер отсутствуют, 3 добавленных — присутствуют; входы
    7 затронутых узлов точно совпадают с ожиданием вердикта v03."""
    g = _graph()
    by_id = {n["id"]: n for n in g["nodes"]}

    for prereq, node in _V03_DROP_EDGES:
        assert prereq not in by_id[node]["prerequisites"], (
            f"дропнутое ребро {prereq}→{node} всё ещё в графе"
        )

    for prereq, node in _V03_ADD_EDGES:
        assert prereq in by_id[node]["prerequisites"], (
            f"добавленное ребро {prereq}→{node} отсутствует"
        )

    for node_id, expected in _V03_EXPECTED_PREREQS.items():
        actual = set(by_id[node_id]["prerequisites"])
        assert actual == expected, f"узел {node_id}: входы {actual}, ожидалось {expected}"


def test_v03_topic_renames_applied():
    """3 темы переименованы (name_ru) по вердикту v03."""
    t = _topics()
    by_id = {x["id"]: x for x in t["topics"]}
    expected_names = {
        "4.NF.B": "Смешанные числа и неправильные дроби",
        "NIS.ALG": "Продвинутая алгебра (системы, модуль, неравенства)",
        "4.MD.A": "Площадь прямоугольника и квадрата",
    }
    for topic_id, expected_name in expected_names.items():
        assert by_id[topic_id]["name_ru"] == expected_name, (
            f"тема {topic_id}: name_ru={by_id[topic_id]['name_ru']!r}, ожидалось {expected_name!r}"
        )


def test_v03_problem_transfers_applied():
    """5 задач перенесены на новые узлы (текст-гарды из вердикта v03)."""
    problems = _problems()
    expected = [
        ("У Пети и Васи вместе 14 яблок", "EQ07"),
        ("У Тани 3 яблока, у Саши на 2 больше", "AR01"),
        ("5 друзей пожали руки каждый с каждым", "CB01"),
        ("Айдар и Болат покрасили забор", "WP05"),
        ("Сколько мод есть в ряде чисел", "DA03"),
    ]
    for guard, expected_node in expected:
        matches = [p for p in problems if guard in p["text_ru"]]
        assert len(matches) == 1, f"гард {guard!r}: найдено {len(matches)}, ожидалась 1"
        assert matches[0]["node_id"] == expected_node, (
            f"гард {guard!r}: node_id={matches[0]['node_id']!r}, ожидался {expected_node!r}"
        )
