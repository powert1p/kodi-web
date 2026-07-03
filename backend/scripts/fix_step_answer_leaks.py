"""fix_step_answer_leaks.py — срезает хвост «= <ответ>» из instruction_ru шагов декомпозиции.

Проблема (P1, контент-баг): ~49% текстов ступеней палят ответ хвостом вида
«Сначала сложи: 63 + 28 = 91.» — ученик видит готовый результат вычисления
до того, как должен его посчитать сам.

Правило правки (безопасная категория, утверждено контент-директором) — режем
хвост `= <expected_value>` из instruction_ru ТОЛЬКО если ВСЕ условия:
  1. expected_value — числовой: ``^-?[\\d\\s.,]+%?$``;
  2. `= <ev>` стоит в АБСОЛЮТНОМ конце строки (допустимы пробелы и финальная
     `.`/`!` после);
  3. сегмент непосредственно перед этим `=` (текст между последним из
     [`:`, `=`, началом строки] и найденным `=`) содержит хотя бы один
     оператор из `+ − - – × ÷ · / *` — т.е. режем только «<выражение> = <ответ>»,
     НЕ «x = 1» (одиночная переменная без оператора — пропускаем).

Всё, что не подходит (mid-sentence «= 36 яблок», «частное равно 338»,
ev-выражения со скобками) — НЕ трогаем.

Источники данных (два независимых, каждый правится своим режимом):
  - DB-таблица problem_steps (id, decomp_idx, n, instruction_ru, expected_value);
  - backend/data/full_decomposition_v1.json (problems[].steps[]).

Запуск:
  python fix_step_answer_leaks.py --audit                      # только отчёт, ничего не меняет (default)
  python fix_step_answer_leaks.py --apply --dsn <postgres-dsn> # правит БД (с бэкапом CSV)
  python fix_step_answer_leaks.py --apply-json                 # правит JSON (с бэкапом .bak-<date>)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

# ── Regex-константы правила ──

# expected_value должен быть чисто числовым (допустимы пробелы-разделители разрядов,
# точка/запятая как десятичный разделитель, ведущий минус, финальный %).
_NUMERIC_EV_RE = re.compile(r"^-?[\d\s.,]+%?$")

# Операторы, наличие которых перед "=" делает срез безопасным
# (иначе это одиночная переменная типа "x = 1", а не выражение).
_OPERATOR_RE = re.compile(r"[+−–×÷·/*-]")

_JSON_PATH = Path(__file__).parent.parent / "data" / "full_decomposition_v1.json"


def clean_instruction(instr: str, ev: str) -> str | None:
    """Срезать хвост «= <ev>» из instr, если это безопасно (см. правило в docstring модуля).

    Возвращает новый instruction_ru, либо None — если правка не применяется
    (ни одно условие не подходит, менять нечего).
    """
    ev = str(ev)

    # Условие 1: expected_value чисто числовой
    if not _NUMERIC_EV_RE.match(ev):
        return None

    # Условие 2: "= <ev>" в абсолютном конце строки (с опциональным пробелом/пунктуацией после)
    pattern = r"\s*=\s*" + re.escape(ev) + r"\s*([.!]?)$"
    m = re.search(pattern, instr)
    if m is None:
        return None

    # Находим позицию символа "=" внутри найденного совпадения
    # (m.start() указывает на начало \s* перед "=", а не на сам символ).
    lead = instr[m.start():]
    eq_offset = len(lead) - len(lead.lstrip())
    eq_pos = m.start() + eq_offset

    # Условие 3: сегмент между последним из [':', '='] (или началом строки) и этим "="
    # должен содержать хотя бы один оператор.
    segment_before = instr[:eq_pos]
    last_delim = max(segment_before.rfind(":"), segment_before.rfind("="))
    check_segment = segment_before[last_delim + 1:]
    if _OPERATOR_RE.search(check_segment) is None:
        return None

    return instr[:m.start()] + m.group(1)


# ── DB-режим (--audit / --apply --dsn) ──

async def _fetch_steps(dsn: str) -> list[dict]:
    """Читает id/decomp_idx/n/instruction_ru/expected_value из problem_steps."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql+asyncpg://", 1)
    elif dsn.startswith("postgresql://") and "+asyncpg" not in dsn:
        dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(dsn)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT id, decomp_idx, n, instruction_ru, expected_value "
                    "FROM problem_steps ORDER BY id"
                )
            )
            rows = [dict(r._mapping) for r in result]
    finally:
        await engine.dispose()
    return rows


async def _apply_db(dsn: str) -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    rows = await _fetch_steps(dsn)
    changes: list[dict] = []
    for row in rows:
        new_instr = clean_instruction(row["instruction_ru"], row["expected_value"])
        if new_instr is not None:
            changes.append({**row, "new_instruction_ru": new_instr})

    print(f"Найдено к правке: {len(changes)}/{len(rows)} шагов.")

    if not changes:
        print("Правок нет — идемпотентность подтверждена (или уже применено ранее).")
        return

    # (а) Бэкап ПЕРЕД правкой — только правящиеся строки
    date_str = dt.date.today().isoformat()
    backup_dir = Path(__file__).parent.parent / "data"
    backup_path = backup_dir / f"backup_step_instructions_{date_str}.csv"
    with open(backup_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["decomp_idx", "n", "old_instruction_ru"])
        for c in changes:
            writer.writerow([c["decomp_idx"], c["n"], c["instruction_ru"]])
    print(f"Бэкап сохранён: {backup_path} ({len(changes)} строк)")

    # (б) UPDATE батчем, параметризованный SQL
    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql+asyncpg://", 1)
    elif dsn.startswith("postgresql://") and "+asyncpg" not in dsn:
        dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(dsn)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "UPDATE problem_steps SET instruction_ru = :new_instruction_ru "
                    "WHERE id = :id"
                ),
                [{"id": c["id"], "new_instruction_ru": c["new_instruction_ru"]} for c in changes],
            )
    finally:
        await engine.dispose()

    print(f"Применено: {len(changes)} UPDATE.")


def _audit_db(dsn: str) -> None:
    import asyncio

    rows = asyncio.run(_fetch_steps(dsn))
    changes = []
    for row in rows:
        new_instr = clean_instruction(row["instruction_ru"], row["expected_value"])
        if new_instr is not None:
            changes.append((row, new_instr))

    print(f"Всего шагов: {len(rows)}")
    print(f"Подпадает под правку: {len(changes)} ({len(changes) / len(rows) * 100:.1f}%)")
    print("\nПримеры (before → after):")
    for row, new_instr in changes[:5]:
        print(f"  [decomp_idx={row['decomp_idx']} n={row['n']}]")
        print(f"    before: {row['instruction_ru']!r}")
        print(f"    after:  {new_instr!r}")


# ── JSON-режим (--apply-json) ──

def _apply_json(json_path: Path) -> None:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    changed = 0
    total = 0
    examples: list[tuple[str, str]] = []
    for prob in data["problems"]:
        for step in prob.get("steps", []):
            total += 1
            new_instr = clean_instruction(step["instruction_ru"], step["expected_value"])
            if new_instr is not None:
                if len(examples) < 5:
                    examples.append((step["instruction_ru"], new_instr))
                step["instruction_ru"] = new_instr
                changed += 1

    print(f"Всего шагов в JSON: {total}")
    print(f"Изменено: {changed}")
    for before, after in examples:
        print(f"  before: {before!r}")
        print(f"  after:  {after!r}")

    if changed == 0:
        print("Правок нет — идемпотентность подтверждена (или уже применено ранее).")
        return

    # Бэкап — точная копия исходного файла на диске (ещё не тронутого), делаем ДО записи.
    date_str = dt.date.today().isoformat()
    backup_path = json_path.with_suffix(json_path.suffix + f".bak-{date_str}")
    shutil.copy2(json_path, backup_path)

    # Исходный файл — компактный однострочный JSON (json.dumps без indent, дефолтные
    # разделители). Сохраняем ТОТ ЖЕ формат, чтобы diff показывал только реальные правки.
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False))
    print(f"Бэкап: {backup_path}")
    print(f"Сохранено: {json_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true", help="только отчёт по БД, ничего не меняет (default)")
    parser.add_argument("--apply", action="store_true", help="применить правку к БД")
    parser.add_argument("--apply-json", action="store_true", help="применить правку к full_decomposition_v1.json")
    parser.add_argument("--dsn", type=str, default=None, help="postgres DSN для --audit/--apply")
    args = parser.parse_args()

    if args.apply_json:
        _apply_json(_JSON_PATH)
        return

    if args.apply:
        if not args.dsn:
            print("--apply требует --dsn <postgres-dsn>", file=sys.stderr)
            sys.exit(1)
        import asyncio

        asyncio.run(_apply_db(args.dsn))
        return

    # --audit (default)
    if not args.dsn:
        print("--audit требует --dsn <postgres-dsn>", file=sys.stderr)
        sys.exit(1)
    _audit_db(args.dsn)


if __name__ == "__main__":
    main()
