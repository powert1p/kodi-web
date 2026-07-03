"""Одноразовый (но воспроизводимый) скрипт применения вердикта графа v02/v02.1.

Источник правды: docs/specs/2026-07-03-graph-v02-verdict.md — каждое
DROP/ADD/RETAG/DELETE взято дословно из таблиц вердикта, ничего "от себя".

Применяет IN-PLACE к четырём JSON-источникам:
  - backend/data/nis_knowledge_graph_v01.json (узлы, рёбра-prerequisites, metadata)
  - backend/data/cc_topics_v01.json (node_topic, topics, topic_edges, meta)
  - backend/data/problems_v10.json (перепривязка node_id удалённых узлов)
  - backend/data/full_decomposition_v1.json (v02.1: синхронная перепривязка
    банка декомпозиций — выравнивание idx↔позиция в problems_v10, сверка по answer)

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
_DECOMP_PATH = _DATA_DIR / "full_decomposition_v1.json"


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
# v02.1: 3.MD.B добавлена в список удаления — осиротела после RETAG DA01/DA02
# (правка вердикта задним числом, см. раздел 5 docs/specs/2026-07-03-graph-v02-verdict.md).
EMPTY_TOPICS_TO_DROP = [
    "3.MD.A", "3.OA.D", "4.MD.C", "4.NF.C", "4.OA.A", "5.MD.C", "3.MD.B",
]

EXPECTED_NODE_COUNT = 114
EXPECTED_TOPIC_COUNT = 36


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_graph_or_problems(path: Path, data: dict) -> None:
    """Формат nis_knowledge_graph/problems: indent=2, без trailing newline."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _dump_topics(path: Path, data: dict) -> None:
    """Формат cc_topics_v01.json: indent=1, с trailing newline."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _dump_decomp(path: Path, data: dict) -> None:
    """Формат full_decomposition_v1.json: компактный, без indent, без trailing newline."""
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


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


def sync_decomposition(problems: list[dict], decomp_problems: list[dict]) -> dict:
    """v02.1: перепривязать node_id банка декомпозиций синхронно с problems_v10.

    Выравнивание: idx декомпозиции == позиция задачи в списке problems (банк
    генерился из того же списка — проверено: idx всегда равен индексу).
    Сверка: answer декомпозиции должен совпасть с answer задачи на той же
    позиции ДО remap (answer не меняется при перепривязке node_id, поэтому
    сверка валидна и после remap_problems). При совпадении — копируется новый
    node_id этой позиции (уже проставлен remap_problems). При расхождении —
    fallback на текстовое правило самой decomp-записи (текст шагов).
    """
    targets = {"NM01", "NM02", "NM03", "ALG01"}
    total = 0
    aligned = 0
    mismatched = 0
    final_counts = {REMAP_TARGET_MODULUS: 0, REMAP_TARGET_PLAIN: 0, REMAP_TARGET_ALG01: 0}

    for rec in decomp_problems:
        old_node_id = rec["node_id"]
        if old_node_id not in targets:
            continue
        total += 1
        problem = problems[rec["idx"]]
        is_aligned = str(problem.get("answer")) == str(rec.get("answer"))

        if is_aligned:
            aligned += 1
            new_node_id = problem["node_id"]
        else:
            mismatched += 1
            if old_node_id == "ALG01":
                new_node_id = REMAP_TARGET_ALG01
            else:
                text = " ".join(s.get("instruction_ru", "") for s in rec.get("steps", []))
                new_node_id = (
                    REMAP_TARGET_MODULUS if ("|" in text or "модул" in text.lower())
                    else REMAP_TARGET_PLAIN
                )

        rec["node_id"] = new_node_id
        final_counts[new_node_id] = final_counts.get(new_node_id, 0) + 1

    return {
        "total": total,
        "aligned": aligned,
        "mismatched": mismatched,
        "alignment_pct": (aligned / total * 100) if total else 0.0,
        "final_counts": final_counts,
    }


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
    assert not empty_topics, f"пустые темы после применения: {empty_topics}"

    # Все node_id из problems существуют в графе.
    problem_node_ids = {p["node_id"] for p in problems}
    dangling = problem_node_ids - node_ids
    assert not dangling, f"problems ссылаются на несуществующие узлы: {dangling}"


def main() -> None:
    graph = _load(_GRAPH_PATH)
    topics_data = _load(_TOPICS_PATH)
    problems_data = _load(_PROBLEMS_PATH)
    decomp_data = _load(_DECOMP_PATH)

    nodes_by_id = {n["id"]: n for n in graph["nodes"]}

    apply_edges(nodes_by_id)
    apply_node_delete(graph, nodes_by_id)

    apply_retag(topics_data["node_topic"])
    for node_id in DELETE_NODES:
        topics_data["node_topic"].pop(node_id, None)
    drop_empty_topics(topics_data)

    remap_counters = remap_problems(problems_data["problems"])
    decomp_counters = sync_decomposition(problems_data["problems"], decomp_data["problems"])

    fr13 = nodes_by_id["FR13"]
    old_difficulty = fr13["difficulty"]
    fr13["difficulty"] = FR13_NEW_DIFFICULTY

    graph["metadata"]["total_nodes"] = len(graph["nodes"])
    graph["metadata"]["total_edges"] = sum(len(n["prerequisites"]) for n in graph["nodes"])

    topics_data["meta"]["topics"] = len(topics_data["topics"])
    topics_data["meta"]["edges"] = len(topics_data["topic_edges"])
    topics_data["meta"]["nodes_mapped"] = len(topics_data["node_topic"])

    validate(graph, topics_data, problems_data["problems"])

    # После sync_decomposition в банке декомпозиций не должно остаться ссылок
    # на удалённые узлы.
    remaining = {p["node_id"] for p in decomp_data["problems"]} & set(DELETE_NODES)
    assert not remaining, f"decomposition: остались ссылки на удалённые узлы {remaining}"

    _dump_graph_or_problems(_GRAPH_PATH, graph)
    _dump_topics(_TOPICS_PATH, topics_data)
    _dump_graph_or_problems(_PROBLEMS_PATH, problems_data)
    _dump_decomp(_DECOMP_PATH, decomp_data)

    print("=== Граф v02 применён ===")
    print(f"DROP рёбер: {len(DROP_EDGES)}")
    print(f"ADD рёбер: {len(ADD_EDGES)}")
    print(f"RETAG узлов: {len(RETAG_NODE_TOPIC)}")
    print(f"Удалено узлов: {len(DELETE_NODES)}")
    print(f"FR13 difficulty: {old_difficulty} → {FR13_NEW_DIFFICULTY}")
    print()
    print("Перепривязка задач удалённых узлов (problems_v10.json):")
    print(f"  NM01/NM02/NM03 → MD01 (есть модуль): {remap_counters['NM_modulus']}")
    print(f"  NM01/NM02/NM03 → RN01 (без модуля): {remap_counters['NM_plain']}")
    print(f"  ALG01 → AL01: {remap_counters['ALG01']}")
    print()
    print(f"metadata.total_nodes = {graph['metadata']['total_nodes']}")
    print(f"metadata.total_edges = {graph['metadata']['total_edges']}")
    print(f"cc_topics.meta = {topics_data['meta']}")
    print()
    print("Валидация: OK (ацикличность, prereq-ссылки, topic-покрытие [все темы непустые], problems-ссылки)")
    print()
    print("=== Синхронизация full_decomposition_v1.json (v02.1) ===")
    print(f"Записей затронуто: {decomp_counters['total']}")
    print(
        f"Выравнивание idx↔problems_v10 по answer: {decomp_counters['aligned']}/"
        f"{decomp_counters['total']} = {decomp_counters['alignment_pct']:.1f}%"
    )
    print(f"Расхождений (fallback на текстовое правило): {decomp_counters['mismatched']}")
    print("Итоговая перепривязка decomposition:")
    print(f"  → MD01: {decomp_counters['final_counts'][REMAP_TARGET_MODULUS]}")
    print(f"  → RN01: {decomp_counters['final_counts'][REMAP_TARGET_PLAIN]}")
    print(f"  → AL01: {decomp_counters['final_counts'][REMAP_TARGET_ALG01]}")


if __name__ == "__main__":
    main()
