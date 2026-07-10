"""Заливка карточек теории «Как решать» (nodes.theory_ru) из .superpowers/theory/.

Читает все `cards-*.json` (list of {"id": "AL01", "theory_ru": "..."}), проверяет
инварианты (уникальность id между файлами; id существует в таблице nodes) и
идемпотентно проставляет метод узла: UPDATE nodes SET theory_ru.

Готово частично (57/114 на момент ввода) — скрипт спокойно работает с любым
подмножеством файлов: несуществующий id → warning + skip, дубль → warning + skip.

Запуск (dev-БД, DATABASE_URL из окружения как весь backend):
    cd backend && ../.venv/bin/python scripts/seed_theory.py
    cd backend && ../.venv/bin/python scripts/seed_theory.py --json   # + вписать в graph-JSON

Флаги:
    --dir PATH  — папка с cards-*.json (по умолчанию <repo>/.superpowers/theory)
    --json      — дополнительно вписать theory_ru в backend/data/nis_knowledge_graph_v01.json
                  (seed-источник свежих БД), in-place, indent=2.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

# backend/ в sys.path — скрипт запускается из backend/ (импорты db.base и т.п.)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Пути (repo root → backend/scripts/../..) ─────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DEFAULT_THEORY_DIR = _REPO_ROOT / ".superpowers" / "theory"
_GRAPH_JSON = _BACKEND_DIR / "data" / "nis_knowledge_graph_v01.json"


# ── Чистая валидация (без БД — тестируется отдельно) ─────────────────────────


@dataclass
class CardValidation:
    """Результат валидации набора карточек против существующих узлов."""

    card_map: dict[str, str]      # все id → theory_ru (первое вхождение)
    to_apply: dict[str, str]      # только id, существующие среди узлов
    duplicate_ids: list[str]      # id, встретившиеся в файлах более одного раза
    missing_ids: list[str]        # id карточек, которых нет среди узлов (skip)


def validate_cards(cards: list[dict], existing_node_ids: set[str]) -> CardValidation:
    """Сводит карточки в карту id→theory и разделяет на applicable/дубли/missing.

    Дубль id (нарушение «id уникальны между файлами») → первое вхождение
    побеждает, остальные попадают в duplicate_ids и не применяются.
    id, которого нет среди existing_node_ids → missing_ids (skip, НЕ падаем).
    """
    card_map: dict[str, str] = {}
    duplicates: list[str] = []
    for c in cards:
        cid = c["id"]
        if cid in card_map:
            duplicates.append(cid)
            continue
        card_map[cid] = c["theory_ru"]

    missing = [cid for cid in card_map if cid not in existing_node_ids]
    to_apply = {cid: t for cid, t in card_map.items() if cid in existing_node_ids}
    return CardValidation(
        card_map=card_map,
        to_apply=to_apply,
        duplicate_ids=sorted(set(duplicates)),
        missing_ids=sorted(missing),
    )


def load_cards(theory_dir: Path) -> list[dict]:
    """Читает и конкатенирует все cards-*.json из папки (порядок — по имени файла)."""
    cards: list[dict] = []
    files = sorted(theory_dir.glob("cards-*.json"))
    if not files:
        log.warning("В %s не найдено ни одного cards-*.json", theory_dir)
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        cards.extend(data)
        log.info("Прочитано %d карточек из %s", len(data), path.name)
    return cards


def update_graph_json(path: Path, card_map: dict[str, str]) -> int:
    """Вписывает theory_ru в узлы graph-JSON in-place. Возвращает число обновлённых.

    Порядок ключей узла сохраняется (theory_ru добавляется в конец), отступы —
    indent=2, ensure_ascii=False (как в исходном файле, без хвостового перевода строки).
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    updated = 0
    for node in data.get("nodes", []):
        theory = card_map.get(node["id"])
        if theory is not None:
            node["theory_ru"] = theory
            updated += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return updated


# ── Заливка в БД ─────────────────────────────────────────────────────────────


async def run(theory_dir: Path, write_json: bool) -> None:
    """Читает карточки, валидирует, заливает в nodes.theory_ru, печатает отчёт."""
    # Импорт БД внутри функции — чистая валидация тестируется без config/engine.
    from sqlalchemy import text

    from db.base import async_session

    cards = load_cards(theory_dir)

    async with async_session() as session:
        existing = {
            r[0] for r in (await session.execute(text("SELECT id FROM nodes"))).fetchall()
        }
        validation = validate_cards(cards, existing)

        for nid, theory in validation.to_apply.items():
            await session.execute(
                text("UPDATE nodes SET theory_ru = :t WHERE id = :id"),
                {"t": theory, "id": nid},
            )
        await session.commit()

        # Узлы, всё ещё без теории (полный список для отчёта)
        without = [
            r[0]
            for r in (
                await session.execute(
                    text("SELECT id FROM nodes WHERE theory_ru IS NULL ORDER BY id")
                )
            ).fetchall()
        ]

    # ── Отчёт ────────────────────────────────────────────────────────────────
    if validation.duplicate_ids:
        log.warning(
            "Дубли id между файлами (применено первое вхождение): %s",
            ", ".join(validation.duplicate_ids),
        )
    if validation.missing_ids:
        log.warning(
            "Карточки для несуществующих узлов (пропущены): %s",
            ", ".join(validation.missing_ids),
        )

    log.info("Залито карточек: %d", len(validation.to_apply))
    log.info(
        "Узлов без теории: %d%s",
        len(without),
        (" — " + ", ".join(without)) if without else "",
    )

    if write_json:
        n = update_graph_json(_GRAPH_JSON, validation.card_map)
        log.info("В graph-JSON вписано theory_ru в %d узлов: %s", n, _GRAPH_JSON.name)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Заливка карточек теории в nodes.theory_ru")
    parser.add_argument(
        "--dir",
        type=Path,
        default=_DEFAULT_THEORY_DIR,
        help="Папка с cards-*.json (по умолчанию <repo>/.superpowers/theory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Дополнительно вписать theory_ru в backend/data/nis_knowledge_graph_v01.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(run(args.dir, args.json))
