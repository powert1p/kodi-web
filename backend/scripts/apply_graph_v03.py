"""Скрипт применения вердикта графа v03 (правки JSON-источников, БЕЗ БД).

Источник правды: docs/specs/2026-07-06-graph-topic-audit-verdict.md — каждое
DROP/ADD ребро, переименование темы и перенос задачи взято дословно из
вердикта, ничего "от себя" (кроме синхронизации банка декомпозиций — см. §4).

Применяет IN-PLACE к JSON-источникам:
  - backend/data/nis_knowledge_graph_v01.json (рёбра: −6 +3, metadata.total_edges)
  - backend/data/cc_topics_v01.json (3 name_ru тем)
  - backend/data/problems_v10.json (node_id 5 задач, по текст-гардам)
  - backend/data/full_decomposition_v1.json (синхронный перенос ТЕХ ЖЕ 5 задач
    в банке декомпозиций — не входило в буквальный список файлов задания, но
    без этого на следующем FORCE_RESEED=1 банк тихо откатит node_id обратно
    на старый узел; тот же паттерн, что v02.1 применял для NM01-3/ALG01)

В отличие от v02 (одноразовый скрипт с hard-assert, падал при повторном
запуске) — этот скрипт ИДЕМПОТЕНТЕН: каждая правка проверяет текущее
состояние (уже применено? ещё нет? что-то неожиданное?) вместо жёсткого
assert "ребро точно есть/точно нет".

Запуск:
  python backend/scripts/apply_graph_v03.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_GRAPH_PATH = _DATA_DIR / "nis_knowledge_graph_v01.json"
_TOPICS_PATH = _DATA_DIR / "cc_topics_v01.json"
_PROBLEMS_PATH = _DATA_DIR / "problems_v10.json"
_DECOMP_PATH = _DATA_DIR / "full_decomposition_v1.json"

_BACKUP_SUFFIX = ".bak-v03"

# ── §1. DROP/ADD рёбер (дословно из вердикта, раздел "Дроп рёбер"/"Добавление") ─
# Формат: (prereq, node) — ребро "A→B" живёт в prerequisites узла B.
DROP_EDGES: list[tuple[str, str]] = [
    ("AR09", "CV04"),  # конвертация км²/м³ не требует "Степени"; вход остаётся GE02→CV04→CV05
    ("AR09", "CV05"),
    ("GE01", "GE12"),  # "периметр" не нужен для подсчёта фигур на чертеже; GE12 сохраняет CB01
    ("EQ02", "WP03"),  # движение по воде — арифметика (v±течение); WP03 сохраняет WP02
    ("DV02", "LG04"),  # ребусы AB+BA=99 не требуют делителей
    ("AL01", "EQ02"),  # транзитивная редукция после AL02→EQ02 (AL01→AL02→EQ02)
]

ADD_EDGES: list[tuple[str, str]] = [
    ("AL02", "EQ02"),  # 65%+ задач "Линейные уравнения" требуют раскрытия скобок
    ("DC01", "AR07"),  # AR07 содержит "округлите 6.478 до десятых" — нужно понятие десятичной дроби
    ("AR10", "LG04"),  # ребусы требуют разрядной записи (AB = 10A+B) — это AR10
]

# ── §2. Переименования тем (view-слой, только name_ru) ───────────────────────
# {topic_id: (старое name_ru, новое name_ru)} — старое значение проверяется
# перед записью (защита от переименования "не той" темы при дрейфе данных).
TOPIC_RENAMES: dict[str, tuple[str, str]] = {
    "4.NF.B": (
        "Дроби на числовой прямой и смешанные числа",
        "Смешанные числа и неправильные дроби",
    ),
    "NIS.ALG": (
        "Продвинутая алгебра (системы, модуль, квадратные)",
        "Продвинутая алгебра (системы, модуль, неравенства)",
    ),
    "4.MD.A": (
        "Измерения и перевод единиц",
        "Площадь прямоугольника и квадрата",
    ),
}

# ── §3. Переносы задач (текст-гарды перед UPDATE) ────────────────────────────
# CB01 vs CB05 (узел "сочетаний" для рукопожатий): в графе НЕТ узла, буквально
# названного "сочетания" — выбор между CB01 "Комбинаторика: правило суммы и
# произведения" (базовый, prereq=AR02) и CB05 "Перестановки (формула P)"
# (prereq=CB04+CB06, формула перестановок — ПОРЯДОК важен). Рукопожатия —
# классическая задача на НЕУПОРЯДОЧЕННые пары (C(5,2)=10, не P(5,2)=20) →
# педагогически это CB01 (базовый принцип подсчёта), НЕ CB05 (там была бы
# неверная формула). Проверено: name_ru всех CB01..CB07 не содержит "сочетан".
#
# Формат: (текст-гард — уникальная подстрока text_ru, старый node_id, новый
# node_id, метка из вердикта для отчёта).
PROBLEM_TRANSFERS: list[tuple[str, str, str, str]] = [
    ("У Пети и Васи вместе 14 яблок", "LG06", "EQ07", "id 775 — сумма-разность"),
    ("У Тани 3 яблока, у Саши на 2 больше", "LG06", "AR01", "id 772 — простое сложение"),
    ("5 друзей пожали руки каждый с каждым", "LG06", "CB01", "id 777 — рукопожатия C(5,2)"),
    ("Айдар и Болат покрасили забор", "WP08", "WP05", "совместная работа"),
    ("Сколько мод есть в ряде чисел", "DA01", "DA03", "мода без диаграммы"),
]

EXPECTED_NODE_COUNT = 114
EXPECTED_EDGE_COUNT = 178
EXPECTED_TOPIC_COUNT = 36

# Ожидаемые входы затронутых узлов ПОСЛЕ применения (пост-ассерт из задания).
EXPECTED_PREREQS_AFTER: dict[str, set[str]] = {
    "AR07": {"AR06", "DC01"},
    "LG04": {"AR06", "AR10"},
    "GE12": {"CB01"},
    "CV04": {"GE02"},
    "CV05": {"CV04"},
    "WP03": {"WP02"},
    "EQ02": {"EQ01", "AL02"},
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _backup_once(path: Path) -> bool:
    """Создать <file>.bak-v03, только если его ещё нет (сохраняет ИСХОДНОЕ
    состояние до v03 даже при повторных запусках скрипта)."""
    backup_path = path.with_name(path.name + _BACKUP_SUFFIX)
    if backup_path.exists():
        return False
    shutil.copy2(path, backup_path)
    return True


def _dump_graph_or_problems(path: Path, data: dict) -> None:
    """Формат nis_knowledge_graph/problems: indent=2, без trailing newline."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _dump_topics(path: Path, data: dict) -> None:
    """Формат cc_topics_v01.json: indent=1, с trailing newline."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _dump_decomp(path: Path, data: dict) -> None:
    """Формат full_decomposition_v1.json: компактный, без indent, без trailing newline."""
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def apply_edges(nodes_by_id: dict[str, dict]) -> dict[str, int]:
    """DROP/ADD рёбер — идемпотентно (проверка текущего состояния, не hard-assert)."""
    dropped = already_absent = 0
    for prereq, node_id in DROP_EDGES:
        prereqs = nodes_by_id[node_id]["prerequisites"]
        if prereq in prereqs:
            prereqs.remove(prereq)
            dropped += 1
        else:
            already_absent += 1

    added = already_present = 0
    for prereq, node_id in ADD_EDGES:
        prereqs = nodes_by_id[node_id]["prerequisites"]
        if prereq not in prereqs:
            prereqs.append(prereq)
            added += 1
        else:
            already_present += 1

    return {
        "dropped": dropped,
        "already_absent": already_absent,
        "added": added,
        "already_present": already_present,
    }


def apply_topic_renames(topics_data: dict) -> dict[str, int]:
    renamed = already_new = 0
    by_id = {t["id"]: t for t in topics_data["topics"]}
    for topic_id, (old_name, new_name) in TOPIC_RENAMES.items():
        topic = by_id.get(topic_id)
        assert topic is not None, f"RENAME: тема {topic_id} не найдена"
        if topic["name_ru"] == old_name:
            topic["name_ru"] = new_name
            renamed += 1
        elif topic["name_ru"] == new_name:
            already_new += 1
        else:
            raise AssertionError(
                f"тема {topic_id}: текущее name_ru={topic['name_ru']!r}, "
                f"ожидалось {old_name!r} (старое) или {new_name!r} (новое)"
            )
    return {"renamed": renamed, "already_new": already_new}


def transfer_problems(problems: list[dict]) -> list[dict]:
    """Перенести 5 задач по текст-гардам. Возвращает список результатов с
    позицией (idx = позиция в списке problems) — нужно для sync_decomposition."""
    results: list[dict] = []
    for guard, old_node, new_node, label in PROBLEM_TRANSFERS:
        matches = [(i, p) for i, p in enumerate(problems) if guard in p["text_ru"]]
        assert len(matches) == 1, (
            f"гард {guard!r} ({label}): найдено {len(matches)} совпадений в "
            f"problems_v10.json, ожидалось ровно 1"
        )
        idx, p = matches[0]
        if p["node_id"] == old_node:
            p["node_id"] = new_node
            status = "moved"
        elif p["node_id"] == new_node:
            status = "already_moved"
        else:
            raise AssertionError(
                f"гард {guard!r} ({label}) на позиции {idx}: node_id={p['node_id']!r}, "
                f"ожидался {old_node!r} (до переноса) или {new_node!r} (после)"
            )
        results.append({
            "idx": idx, "guard": guard, "label": label,
            "from": old_node, "to": new_node, "status": status,
        })
    return results


def sync_decomposition(transfer_results: list[dict], decomp_problems: list[dict]) -> dict:
    """Синхронизировать node_id тех же 5 задач в банке декомпозиций (по idx —
    позиция в JSON = idx, подтверждено 1:1 совпадением node_id/answer).

    Не входит в буквальный список файлов задания — добавлено, чтобы
    full_decomposition_v1.json не разошёлся с problems_v10.json (иначе
    следующий FORCE_RESEED=1 тихо откатит decomposition_problems.node_id
    обратно на старый узел). См. docstring модуля.
    """
    by_idx = {rec["idx"]: rec for rec in decomp_problems}
    synced = already_synced = missing = 0
    for tr in transfer_results:
        rec = by_idx.get(tr["idx"])
        if rec is None:
            missing += 1
            continue
        if rec["node_id"] == tr["from"]:
            rec["node_id"] = tr["to"]
            synced += 1
        elif rec["node_id"] == tr["to"]:
            already_synced += 1
        else:
            raise AssertionError(
                f"decomposition idx={tr['idx']} ({tr['label']}): node_id={rec['node_id']!r}, "
                f"ожидался {tr['from']!r} или {tr['to']!r}"
            )
    return {"synced": synced, "already_synced": already_synced, "missing": missing}


def validate(graph: dict, topics_data: dict, problems: list[dict]) -> None:
    """Ассерты целостности после всех правок."""
    nodes = graph["nodes"]
    node_ids = {n["id"] for n in nodes}
    by_id = {n["id"]: n for n in nodes}

    assert len(nodes) == EXPECTED_NODE_COUNT, f"узлов {len(nodes)}, ожидалось {EXPECTED_NODE_COUNT}"
    assert len(topics_data["topics"]) == EXPECTED_TOPIC_COUNT, (
        f"тем {len(topics_data['topics'])}, ожидалось {EXPECTED_TOPIC_COUNT}"
    )

    total_edges = sum(len(n["prerequisites"]) for n in nodes)
    assert total_edges == EXPECTED_EDGE_COUNT, f"рёбер {total_edges}, ожидалось {EXPECTED_EDGE_COUNT}"

    # Все prereq-ссылки существуют.
    for n in nodes:
        for prereq in n["prerequisites"]:
            assert prereq in node_ids, f"узел {n['id']}: несуществующий prereq {prereq}"

    # Ожидаемые входы затронутых узлов.
    for node_id, expected in EXPECTED_PREREQS_AFTER.items():
        actual = set(by_id[node_id]["prerequisites"])
        assert actual == expected, f"узел {node_id}: входы {actual}, ожидалось {expected}"

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
    assert visited == len(node_ids), f"граф содержит цикл(ы) — Kahn посетил {visited}/{len(node_ids)}"

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

    # Все node_id из problems существуют в графе (0 задач-сирот).
    problem_node_ids = {p["node_id"] for p in problems}
    dangling = problem_node_ids - node_ids
    assert not dangling, f"problems ссылаются на несуществующие узлы: {dangling}"


def main() -> None:
    for path in (_GRAPH_PATH, _TOPICS_PATH, _PROBLEMS_PATH, _DECOMP_PATH):
        _backup_once(path)

    graph = _load(_GRAPH_PATH)
    topics_data = _load(_TOPICS_PATH)
    problems_data = _load(_PROBLEMS_PATH)
    decomp_data = _load(_DECOMP_PATH)

    nodes_by_id = {n["id"]: n for n in graph["nodes"]}

    edge_counters = apply_edges(nodes_by_id)
    topic_counters = apply_topic_renames(topics_data)
    transfer_results = transfer_problems(problems_data["problems"])
    decomp_counters = sync_decomposition(transfer_results, decomp_data["problems"])

    graph["metadata"]["total_nodes"] = len(graph["nodes"])
    graph["metadata"]["total_edges"] = sum(len(n["prerequisites"]) for n in graph["nodes"])
    topics_data["meta"]["topics"] = len(topics_data["topics"])
    topics_data["meta"]["edges"] = len(topics_data["topic_edges"])
    topics_data["meta"]["nodes_mapped"] = len(topics_data["node_topic"])

    validate(graph, topics_data, problems_data["problems"])

    _dump_graph_or_problems(_GRAPH_PATH, graph)
    _dump_topics(_TOPICS_PATH, topics_data)
    _dump_graph_or_problems(_PROBLEMS_PATH, problems_data)
    _dump_decomp(_DECOMP_PATH, decomp_data)

    print("=== Граф v03 применён ===")
    print(
        f"DROP рёбер: {edge_counters['dropped']} применено, "
        f"{edge_counters['already_absent']} уже отсутствовали (идемпотентно)"
    )
    print(
        f"ADD рёбер: {edge_counters['added']} применено, "
        f"{edge_counters['already_present']} уже были (идемпотентно)"
    )
    print(
        f"Темы переименованы: {topic_counters['renamed']} применено, "
        f"{topic_counters['already_new']} уже переименованы"
    )
    print("Перенос задач:")
    for tr in transfer_results:
        print(f"  [{tr['status']}] {tr['label']}: позиция {tr['idx']} {tr['from']}→{tr['to']}")
    print(
        f"Синхронизация decomposition-банка: {decomp_counters['synced']} применено, "
        f"{decomp_counters['already_synced']} уже синхронны, {decomp_counters['missing']} без записи"
    )
    print()
    print(f"metadata.total_nodes = {graph['metadata']['total_nodes']}")
    print(f"metadata.total_edges = {graph['metadata']['total_edges']}")
    print(f"cc_topics.meta = {topics_data['meta']}")
    print()
    print(
        "Валидация: OK (114 узлов, 178 рёбер, ацикличность Kahn 114/114, "
        "ожидаемые входы AR07/LG04/GE12/CV04/CV05/WP03/EQ02, topic-покрытие, "
        "0 задач-сирот)"
    )


if __name__ == "__main__":
    main()
