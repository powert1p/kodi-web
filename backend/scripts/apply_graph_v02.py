"""Одноразовый (но воспроизводимый) скрипт применения вердикта графа v02.

Источник правды: docs/specs/2026-07-03-graph-v02-verdict.md — каждое
DROP/ADD/RETAG/DELETE взято дословно из таблиц вердикта, ничего "от себя".

Применяет IN-PLACE к трём JSON-источникам:
  - backend/data/nis_knowledge_graph_v01.json (узлы, рёбра-prerequisites, metadata)
  - backend/data/cc_topics_v01.json (node_topic, topics, topic_edges, meta)
  - backend/data/problems_v10.json (перепривязка node_id удалённых узлов)

Запуск:
  python backend/scripts/apply_graph_v02.py
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_GRAPH_PATH = _DATA_DIR / "nis_knowledge_graph_v01.json"
_TOPICS_PATH = _DATA_DIR / "cc_topics_v01.json"
_PROBLEMS_PATH = _DATA_DIR / "problems_v10.json"


# ── §1. DROP рёбер (дословно из таблицы вердикта, раздел 1) ──────────────────
# Формат: (prereq, node) — ребро "A→B" живёт в prerequisites узла B.
DROP_EDGES: list[tuple[str, str]] = [
    ("AR05", "AR06"), ("GE02", "FR13"), ("FR01", "DC04"), ("EQ02", "PC06"),
    ("FR09", "EQ04"), ("AR06", "EQ07"), ("EQ01", "EQ08"), ("FR01", "RN01"),
    ("FR01", "RN04"), ("DC01", "RN04"), ("FR09", "GE03"), ("RN03", "GE09"),
    ("DC03", "GE08"), ("EQ01", "WP02"), ("FR06", "WP03"), ("FR08", "WP04"),
    ("EQ02", "WP05"), ("PR02", "WP06"), ("EQ01", "WP08"), ("AR06", "WP09"),
    ("AR05", "LG01"), ("EQ01", "LG02"), ("AR05", "LG05"), ("AR05", "LG06"),
    ("AR05", "LG07"), ("FR07", "PR02"), ("FR01", "DA01"), ("AR06", "DA03"),
    ("GE05", "GE07"),
]

# ── §2. ADD рёбер (раздел 2) ─────────────────────────────────────────────────
ADD_EDGES: list[tuple[str, str]] = [
    ("AR01", "AR06"), ("AR02", "AR06"), ("AR03", "AR06"),
    ("AR04", "FR02"),
    ("DV02", "DV04"),
    ("AL03", "MD03"),
    ("RN01", "AL02"),
    ("FR07", "GE05"),
    ("CV02", "GE08"),
    ("GE01", "GE09"),
    ("AR02", "LG01"),
    ("AL01", "LG05"),
    ("AR01", "LG06"), ("AR01", "LG07"),
    ("AR02", "WP04"),
    ("FR03", "PR02"),
]

# ── §3. RETAG узел→тема (раздел 3) ───────────────────────────────────────────
RETAG_NODE_TOPIC: dict[str, str] = {
    "AR03": "3.OA.A",
    "DC03": "5.NBT.A",
    "AL04": "NIS.ALG",
    "RN04": "7.NS.A",
    "EQ08": "5.OA.A",
    "DA01": "6.SP.B",
    "DA02": "6.SP.B",
}

# ── §4. DELETE узлов (раздел 4) ──────────────────────────────────────────────
DELETE_NODES: list[str] = ["NM01", "NM02", "NM03", "ALG01"]

# Перепривязка задач удалённых узлов: NM01/NM02/NM03 → MD01 (если есть модуль
# в тексте) иначе RN01; ALG01 → AL01.
REMAP_TARGET_MODULUS = "MD01"
REMAP_TARGET_PLAIN = "RN01"
REMAP_TARGET_ALG01 = "AL01"

# ── §5. Прочее ────────────────────────────────────────────────────────────────
FR13_NEW_DIFFICULTY = 2
EMPTY_TOPICS_TO_DROP = ["3.MD.A", "3.OA.D", "4.MD.C", "4.NF.C", "4.OA.A", "5.MD.C"]

EXPECTED_NODE_COUNT = 114
EXPECTED_TOPIC_COUNT = 37

# ИЗВЕСТНОЕ РАСХОЖДЕНИЕ с вердиктом (найдено при применении, не чинится здесь):
# RETAG DA01/DA02 (3.MD.B → 6.SP.B, оба узла разом) осиротяет тему 3.MD.B —
# в вердикте это не учтено, её нет в списке EMPTY_TOPICS_TO_DROP, а итоговая
# строка вердикта заявляет "37 тем (все непустые)". Дословное применение
# 6-пунктного списка удаления даёт ровно 37 тем (совпадает с ожидаемым
# счётчиком), но 3.MD.B остаётся с 0 узлами — противоречие внутри самого
# документа-вердикта. Решение: не изобретать замену DA01/DA02 от себя,
# сохранить 37 тем как явно ожидаемое число, зафиксировать исключение здесь
# и в тесте-гейте осознанно (см. docs/specs/2026-07-03-graph-v02-verdict.md).
KNOWN_EMPTY_TOPICS_AFTER_APPLY = {"3.MD.B"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_graph_or_problems(path: Path, data: dict) -> None:
    """Формат nis_knowledge_graph/problems: indent=2, без trailing newline."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _dump_topics(path: Path, data: dict) -> None:
    """Формат cc_topics_v01.json: indent=1, с trailing newline."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def apply_edges(nodes_by_id: dict[str, dict]) -> None:
    """Применить DROP и ADD рёбер к prerequisites узлов."""
    for prereq, node_id in DROP_EDGES:
        node = nodes_by_id[node_id]
        assert prereq in node["prerequisites"], (
            f"DROP {prereq}→{node_id}: ребро отсутствует в prerequisites"
        )
        node["prerequisites"].remove(prereq)

    for prereq, node_id in ADD_EDGES:
        node = nodes_by_id[node_id]
        assert prereq not in node["prerequisites"], (
            f"ADD {prereq}→{node_id}: ребро уже существует"
        )
        node["prerequisites"].append(prereq)


def apply_node_delete(graph: dict, nodes_by_id: dict[str, dict]) -> None:
    """Удалить узлы DELETE_NODES вместе с их рёбрами (внешних ссылок нет — проверено)."""
    for node_id in DELETE_NODES:
        for other in graph["nodes"]:
            if node_id in other["prerequisites"]:
                assert other["id"] in DELETE_NODES, (
                    f"внешняя ссылка на удаляемый узел {node_id} из {other['id']}"
                )
    graph["nodes"] = [n for n in graph["nodes"] if n["id"] not in DELETE_NODES]
    for node_id in DELETE_NODES:
        nodes_by_id.pop(node_id, None)


def remap_problems(problems: list[dict]) -> dict[str, int]:
    """Перепривязать node_id удалённых узлов согласно правилу вердикта (раздел 4)."""
    counters = {"NM_modulus": 0, "NM_plain": 0, "ALG01": 0}
    for p in problems:
        node_id = p["node_id"]
        if node_id in ("NM01", "NM02", "NM03"):
            text = p.get("text_ru", "")
            if "|" in text or "модул" in text.lower():
                p["node_id"] = REMAP_TARGET_MODULUS
                counters["NM_modulus"] += 1
            else:
                p["node_id"] = REMAP_TARGET_PLAIN
                counters["NM_plain"] += 1
        elif node_id == "ALG01":
            p["node_id"] = REMAP_TARGET_ALG01
            counters["ALG01"] += 1
    return counters


def apply_retag(node_topic: dict[str, str]) -> None:
    for node_id, topic_id in RETAG_NODE_TOPIC.items():
        assert node_id in node_topic, f"RETAG: узел {node_id} не найден в node_topic"
        node_topic[node_id] = topic_id


def drop_empty_topics(topics_data: dict) -> None:
    to_drop = set(EMPTY_TOPICS_TO_DROP)
    topics_data["topics"] = [t for t in topics_data["topics"] if t["id"] not in to_drop]
    topics_data["topic_edges"] = [
        e for e in topics_data["topic_edges"] if e[0] not in to_drop and e[1] not in to_drop
    ]


def validate(graph: dict, topics_data: dict, problems: list[dict]) -> None:
    """Ассерты целостности после всех правок."""
    nodes = graph["nodes"]
    node_ids = {n["id"] for n in nodes}

    assert len(nodes) == EXPECTED_NODE_COUNT, f"узлов {len(nodes)}, ожидалось {EXPECTED_NODE_COUNT}"
    assert len(topics_data["topics"]) == EXPECTED_TOPIC_COUNT, (
        f"тем {len(topics_data['topics'])}, ожидалось {EXPECTED_TOPIC_COUNT}"
    )

    # Все prereq-ссылки существуют.
    for n in nodes:
        for prereq in n["prerequisites"]:
            assert prereq in node_ids, f"узел {n['id']}: несуществующий prereq {prereq}"

    # Ацикличность — Kahn's algorithm (edge prereq→node = зависимость).
    indegree = {nid: 0 for nid in node_ids}
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for n in nodes:
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
    assert visited == len(node_ids), "граф содержит цикл(ы)"

    # Каждый узел графа имеет тему; каждая тема имеет ≥1 узел.
    topic_ids = {t["id"] for t in topics_data["topics"]}
    assert set(topics_data["node_topic"].keys()) == node_ids, (
        "node_topic не совпадает с множеством узлов графа"
    )
    node_count_by_topic: dict[str, int] = {}
    for nid, tid in topics_data["node_topic"].items():
        assert tid in topic_ids, f"узел {nid} → несуществующая тема {tid}"
        node_count_by_topic[tid] = node_count_by_topic.get(tid, 0) + 1
    empty_topics = {tid for tid in topic_ids if node_count_by_topic.get(tid, 0) == 0}
    assert empty_topics == KNOWN_EMPTY_TOPICS_AFTER_APPLY, (
        f"пустые темы после применения {empty_topics}, ожидалось ровно "
        f"{KNOWN_EMPTY_TOPICS_AFTER_APPLY} (см. комментарий выше)"
    )

    # Все node_id из problems существуют в графе.
    problem_node_ids = {p["node_id"] for p in problems}
    dangling = problem_node_ids - node_ids
    assert not dangling, f"problems ссылаются на несуществующие узлы: {dangling}"


def main() -> None:
    graph = _load(_GRAPH_PATH)
    topics_data = _load(_TOPICS_PATH)
    problems_data = _load(_PROBLEMS_PATH)

    nodes_by_id = {n["id"]: n for n in graph["nodes"]}

    apply_edges(nodes_by_id)
    apply_node_delete(graph, nodes_by_id)

    apply_retag(topics_data["node_topic"])
    for node_id in DELETE_NODES:
        topics_data["node_topic"].pop(node_id, None)
    drop_empty_topics(topics_data)

    remap_counters = remap_problems(problems_data["problems"])

    fr13 = nodes_by_id["FR13"]
    old_difficulty = fr13["difficulty"]
    fr13["difficulty"] = FR13_NEW_DIFFICULTY

    graph["metadata"]["total_nodes"] = len(graph["nodes"])
    graph["metadata"]["total_edges"] = sum(len(n["prerequisites"]) for n in graph["nodes"])

    topics_data["meta"]["topics"] = len(topics_data["topics"])
    topics_data["meta"]["edges"] = len(topics_data["topic_edges"])
    topics_data["meta"]["nodes_mapped"] = len(topics_data["node_topic"])

    validate(graph, topics_data, problems_data["problems"])

    _dump_graph_or_problems(_GRAPH_PATH, graph)
    _dump_topics(_TOPICS_PATH, topics_data)
    _dump_graph_or_problems(_PROBLEMS_PATH, problems_data)

    print("=== Граф v02 применён ===")
    print(f"DROP рёбер: {len(DROP_EDGES)}")
    print(f"ADD рёбер: {len(ADD_EDGES)}")
    print(f"RETAG узлов: {len(RETAG_NODE_TOPIC)}")
    print(f"Удалено узлов: {len(DELETE_NODES)}")
    print(f"FR13 difficulty: {old_difficulty} → {FR13_NEW_DIFFICULTY}")
    print()
    print("Перепривязка задач удалённых узлов:")
    print(f"  NM01/NM02/NM03 → MD01 (есть модуль): {remap_counters['NM_modulus']}")
    print(f"  NM01/NM02/NM03 → RN01 (без модуля): {remap_counters['NM_plain']}")
    print(f"  ALG01 → AL01: {remap_counters['ALG01']}")
    print()
    print(f"metadata.total_nodes = {graph['metadata']['total_nodes']}")
    print(f"metadata.total_edges = {graph['metadata']['total_edges']}")
    print(f"cc_topics.meta = {topics_data['meta']}")
    print()
    print("Валидация: OK (ацикличность, prereq-ссылки, topic-покрытие, problems-ссылки)")
    print(
        f"ВНИМАНИЕ: известное расхождение с вердиктом — тема(ы) {sorted(KNOWN_EMPTY_TOPICS_AFTER_APPLY)} "
        "остаются без узлов (побочный эффект RETAG DA01/DA02, вердикт это не учёл — см. комментарий в скрипте)."
    )


if __name__ == "__main__":
    main()
