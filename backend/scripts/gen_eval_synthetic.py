"""gen_eval_synthetic.py — синтетический smoke-набор для eval_stand.py.

Генерит 8 «фото» ступеней лесенки PIL-ом по РЕАЛЬНЫМ ступеням из dev-БД
(nismathbot) — 4 с верным значением ступени (expected match), 4 с неверным
(expected mismatch). 2 из 8 — «грязные» (поворот 3-5°, серый фон, шум) —
PIL only, БЕЗ новых зависимостей (используем ``Image.effect_noise``, встроен
в Pillow — не требует numpy).

Не претендует на фотореализм рукописи — это smoke-тест пайплайна (доезжает
ли фото до vision-модели и получается ли разумный вердикт), НЕ полноценный
датасет для замера точности на реальном почерке (для этого — README.md,
30-50 реальных фото от владельца).

Источник ступеней — 8 фиксированных (decomp_idx, n=1) пар, отобранных вручную
(численный expected_value, слинкован с problems.text_ru): idx 0/1/8/10 → match,
idx 2/9/16/20 → mismatch (перепутанное значение).

Запуск:
    cd backend && ../.venv/bin/python scripts/gen_eval_synthetic.py
"""

from __future__ import annotations

import asyncio
import csv
import random
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

_DSN = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/nismathbot"
_FONT_PATH = str(Path(__file__).resolve().parent.parent / "fonts" / "DejaVuSerif.ttf")

_EVAL_DIR = Path(__file__).resolve().parent.parent / "data" / "eval"
_PHOTOS_DIR = _EVAL_DIR / "photos"

# (decomp_idx, expected_verdict) — n всегда 1 (см. докстринг модуля)
_CANDIDATES = [
    (0, "match"),
    (1, "match"),
    (8, "match"),
    (10, "match"),
    (2, "mismatch"),
    (9, "mismatch"),
    (16, "mismatch"),
    (20, "mismatch"),
]
_STEP_N = 1

# Индексы (0-based, по порядку _CANDIDATES) — «грязные» варианты (одна match, одна mismatch).
_DIRTY_POSITIONS = {1, 5}

# ── Рендер ──

_CANVAS_W = 800
_CANVAS_H = 420
_BG = (247, 246, 240)          # бумага
_GRID = (196, 214, 235)        # клетка (светло-голубая)
_INK = (30, 40, 130)           # синяя ручка
_MUTED_INK = (70, 70, 70)


def _wrong_value(expected_value: str) -> str:
    """Правдоподобно неверное числовое значение (перепутанный шаг)."""
    if "." in expected_value or "," in expected_value:
        v = float(expected_value.replace(",", "."))
        return f"{v + 1:.1f}"
    v = int(expected_value)
    return str(v + 7)


def _wrap(text_: str, width_chars: int) -> list[str]:
    return textwrap.wrap(text_, width=width_chars) or [""]


def _draw_grid(draw: ImageDraw.ImageDraw) -> None:
    """Клетчатый фон тетради — тонкие линии каждые 28px."""
    step = 28
    for x in range(0, _CANVAS_W, step):
        draw.line([(x, 0), (x, _CANVAS_H)], fill=_GRID, width=1)
    for y in range(0, _CANVAS_H, step):
        draw.line([(0, y), (_CANVAS_W, y)], fill=_GRID, width=1)


def render_step_photo(*, statement: str, instruction_ru: str, shown_value: str) -> Image.Image:
    """Рисует «фото» тетрадного листа с условием, инструкцией и (не)верным ответом."""
    img = Image.new("RGB", (_CANVAS_W, _CANVAS_H), _BG)
    draw = ImageDraw.Draw(img)
    _draw_grid(draw)

    font_small = ImageFont.truetype(_FONT_PATH, 22)
    font_medium = ImageFont.truetype(_FONT_PATH, 26)
    font_big = ImageFont.truetype(_FONT_PATH, 40)

    y = 32
    if statement:
        for line in _wrap(f"Задача: {statement}", 46):
            draw.text((36, y), line, font=font_small, fill=_MUTED_INK)
            y += 30
        y += 12

    for line in _wrap(instruction_ru, 42):
        draw.text((36, y), line, font=font_medium, fill=_INK)
        y += 36

    y += 24
    draw.text((36, y), f"= {shown_value}", font=font_big, fill=_INK)

    return img


def _make_dirty(img: Image.Image) -> Image.Image:
    """Лёгкий поворот 3-5°, серый фон (fillcolor), шум — имитация плохого фото."""
    angle = random.choice([-1, 1]) * random.uniform(3, 5)
    rotated = img.rotate(angle, expand=True, fillcolor=(160, 160, 160))

    noise = Image.effect_noise(rotated.size, 22).convert("RGB")
    dirty = Image.blend(rotated, noise, alpha=0.10)
    return dirty


# ── Основной сценарий ──

async def _fetch_steps() -> dict[int, dict]:
    idxs = [idx for idx, _ in _CANDIDATES]
    engine = create_async_engine(_DSN)
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(
                text(
                    "SELECT dp.idx, ps.instruction_ru, ps.expected_value, p.text_ru AS statement "
                    "FROM decomposition_problems dp "
                    "JOIN problem_steps ps ON ps.decomp_idx = dp.idx "
                    "LEFT JOIN problems p ON p.id = dp.problems_db_id "
                    "WHERE dp.idx = ANY(:idxs) AND ps.n = :n"
                ),
                {"idxs": idxs, "n": _STEP_N},
            )).mappings().fetchall()
    finally:
        await engine.dispose()
    by_idx = {row["idx"]: dict(row) for row in rows}
    missing = [idx for idx in idxs if idx not in by_idx]
    if missing:
        raise RuntimeError(f"Не найдены шаги в dev-БД для decomp_idx={missing} (n={_STEP_N})")
    return by_idx


async def main() -> None:
    random.seed(42)  # воспроизводимость «грязных» вариантов между прогонами

    steps = await _fetch_steps()

    _PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    labels_rows: list[dict] = []

    for i, (decomp_idx, expected_verdict) in enumerate(_CANDIDATES):
        step = steps[decomp_idx]
        shown_value = step["expected_value"] if expected_verdict == "match" else _wrong_value(step["expected_value"])

        img = render_step_photo(
            statement=step["statement"] or "",
            instruction_ru=step["instruction_ru"],
            shown_value=shown_value,
        )

        dirty = i in _DIRTY_POSITIONS
        if dirty:
            img = _make_dirty(img)

        suffix = "_dirty" if dirty else ""
        photo_file = f"synthetic_{i:02d}_{expected_verdict}{suffix}.jpg"
        img.convert("RGB").save(_PHOTOS_DIR / photo_file, format="JPEG", quality=88)

        labels_rows.append({
            "photo_file": photo_file,
            "decomp_idx": decomp_idx,
            "step_n": _STEP_N,
            "expected_verdict": expected_verdict,
        })
        print(f"  {photo_file}: decomp_idx={decomp_idx} expected={expected_verdict} shown={shown_value!r} dirty={dirty}")

    labels_path = _EVAL_DIR / "labels.csv"
    with open(labels_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["photo_file", "decomp_idx", "step_n", "expected_verdict"])
        writer.writeheader()
        writer.writerows(labels_rows)

    print(f"\nСгенерировано {len(labels_rows)} фото в {_PHOTOS_DIR}")
    print(f"labels.csv: {labels_path}")


if __name__ == "__main__":
    asyncio.run(main())
