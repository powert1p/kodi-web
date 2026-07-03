"""Инварианты данных слоя тем (cc_topics_v01.json). Чистые проверки JSON, без БД."""

import json
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data" / "cc_topics_v01.json"
_GRAPH = Path(__file__).resolve().parent.parent / "data" / "nis_knowledge_graph_v01.json"


def _load() -> dict:
    return json.loads(_DATA.read_text(encoding="utf-8"))


def test_counts():
    d = _load()
    # 43/61 → 36/38 после чистки графа v02/v02.1 (docs/specs/2026-07-03-graph-v02-verdict.md):
    # удалены 7 пустых тем (6 изначально + осиротевшая 3.MD.B после RETAG DA01/DA02)
    # + их topic_edges, узлы NM01/NM02/NM03/ALG01 удалены из графа.
    assert len(d["topics"]) == 36
    assert len(d["topic_edges"]) == 38
    assert len(d["strands"]) == 10


def test_every_node_mapped_to_existing_topic():
    d = _load()
    topic_ids = {t["id"] for t in d["topics"]}
    graph_nodes = {n["id"] for n in json.loads(_GRAPH.read_text(encoding="utf-8"))["nodes"]}
    # ровно 114 узлов покрыты (после v02), ни одного лишнего/сироты
    assert set(d["node_topic"].keys()) == graph_nodes
    for nid, tid in d["node_topic"].items():
        assert tid in topic_ids, f"{nid} → несуществующая тема {tid}"


def test_topics_have_strand_and_labels():
    d = _load()
    strand_codes = {s["code"] for s in d["strands"]}
    for t in d["topics"]:
        assert t["strand"] in strand_codes, f"{t['id']} → раздел {t['strand']} не найден"
        assert t["name_ru"] and t["name_kz"], f"{t['id']} без названия"


def test_strands_have_labels():
    d = _load()
    for s in d["strands"]:
        assert s["name_ru"] and s["name_kz"], f"раздел {s['code']} без названия"


def test_edges_reference_existing_topics():
    d = _load()
    topic_ids = {t["id"] for t in d["topics"]}
    for a, b in d["topic_edges"]:
        assert a in topic_ids and b in topic_ids, f"ребро {a}->{b} ссылается на несуществующую тему"
