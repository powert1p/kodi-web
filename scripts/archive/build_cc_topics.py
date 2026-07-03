"""Собрать backend/data/cc_topics_v01.json — данные слоя тем графа.

Источники:
- docs/specs/cc_topic_skill_tree.json — 43 темы + 61 ребро (canonical CC backbone).
- scripts/topic_names.json — ru/kz названия 10 разделов и 43 тем.
- scripts/node_topic_map.json — карта узел→тема (118 узлов, результат семантического маппинга).
- backend/data/nis_knowledge_graph_v01.json — список 118 узлов (для валидации покрытия).

Запуск: python scripts/build_cc_topics.py
Падает (exit 1), если карта узлов неполна или ссылается на несуществующую тему.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "specs" / "cc_topic_skill_tree.json"
NAMES = ROOT / "scripts" / "topic_names.json"
NODE_MAP = ROOT / "scripts" / "node_topic_map.json"
GRAPH = ROOT / "backend" / "data" / "nis_knowledge_graph_v01.json"
OUT = ROOT / "backend" / "data" / "cc_topics_v01.json"

# Порядок разделов в UI: домены CC (по педагогической логике) + НИШ последним.
STRAND_ORDER = ["OA", "NBT", "NF", "MD", "G", "EE", "NS", "RP", "SP", "NIS"]


def main() -> None:
    cc = json.loads(SRC.read_text(encoding="utf-8"))
    names = json.loads(NAMES.read_text(encoding="utf-8"))
    node_topic = json.loads(NODE_MAP.read_text(encoding="utf-8"))
    graph_nodes = {n["id"] for n in json.loads(GRAPH.read_text(encoding="utf-8"))["nodes"]}

    ru_strand = {s["code"]: s["name_ru"] for s in names["strands"]}
    kz_strand = {s["code"]: s["name_kz"] for s in names["strands"]}
    ru_topic = {t["id"]: t["name_ru"] for t in names["topics"]}
    kz_topic = {t["id"]: t["name_kz"] for t in names["topics"]}

    # ── Разделы (10) ──
    strands = [
        {"code": code, "order": i + 1, "name_ru": ru_strand[code], "name_kz": kz_strand[code]}
        for i, code in enumerate(STRAND_ORDER)
    ]

    # ── Темы (43) — порядок по (класс, код) ──
    src_topics = cc["topics"]  # dict {topic_id: {...}}
    ordered = sorted(src_topics.values(), key=lambda t: (t.get("grade") or 99, t["topic_id"]))
    topics = [
        {
            "id": t["topic_id"],
            "strand": t["domain"],  # домен CC (OA/.../SP) или "NIS"
            "grade": t.get("grade"),
            "order": i + 1,
            "name_ru": ru_topic[t["topic_id"]],
            "name_kz": kz_topic[t["topic_id"]],
        }
        for i, t in enumerate(ordered)
    ]

    topic_edges = [list(e) for e in cc["topic_edges"]]

    # ── Валидация карты узел→тема ──
    topic_ids = {t["id"] for t in topics}
    missing = graph_nodes - set(node_topic)
    extra = set(node_topic) - graph_nodes
    bad = {n: tid for n, tid in node_topic.items() if tid not in topic_ids}
    if missing or extra or bad:
        print("FATAL: проблемы в node_topic", file=sys.stderr)
        print("не покрыты узлы:", sorted(missing), file=sys.stderr)
        print("лишние ключи:", sorted(extra), file=sys.stderr)
        print("несуществующая тема:", bad, file=sys.stderr)
        sys.exit(1)

    # Все strand тем должны существовать среди разделов
    strand_codes = {s["code"] for s in strands}
    bad_strand = {t["id"]: t["strand"] for t in topics if t["strand"] not in strand_codes}
    if bad_strand:
        print("FATAL: тема ссылается на несуществующий раздел:", bad_strand, file=sys.stderr)
        sys.exit(1)

    out = {
        "meta": {"topics": len(topics), "edges": len(topic_edges), "nodes_mapped": len(node_topic)},
        "strands": strands,
        "topics": topics,
        "topic_edges": topic_edges,
        "node_topic": node_topic,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"OK: {len(topics)} тем, {len(topic_edges)} рёбер, {len(node_topic)} узлов -> {OUT}")


if __name__ == "__main__":
    main()
