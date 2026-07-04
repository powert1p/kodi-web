"""eval_stand.py — eval-стенд vision-пайплайна распознавания шагов лесенки.

Дев-инструмент владельца (НЕ прод-эндпоинт): прогоняет размеченный набор фото
«ступеней» решения через ``classify_step_photo`` и считает метрики качества.
Блок 1.1 мастер-плана, пункт 1.

Формат входа (``--dir``, default ``backend/data/eval``):
    photos/<photo_file>   — фото одного шага решения (JPEG/PNG/...)
    labels.csv            — разметка: photo_file,decomp_idx,step_n,expected_verdict
                            (expected_verdict: ``match`` | ``mismatch``)

Разрешение контекста по (decomp_idx, step_n) — ТОТ ЖЕ паттерн, что и прод
``api/routers/trainer.py`` (/step-submit):
  - instruction_ru / expected_value — из ``problem_steps``
    (``WHERE decomp_idx = ... AND n = ...``).
  - statement (условие задачи) — из ``problems.text_ru`` через
    ``decomposition_problems.problems_db_id`` (best-effort FK, линкуется ~42%
    банка, см. docs/data-state.md). Если decomp_idx не слинкован —
    statement = "" (штатный кейс, как и в проде: см. trainer.py:~672-680).
  ⚠️ Решение зафиксировано в коде: ни ``full_decomposition_v1.json``, ни
  ``decomposition_problems`` НЕ хранят текст задачи напрямую — только
  ``problems.text_ru`` через FK. Отсюда statement берём из БД (JOIN), а не
  из JSON-файла.

Метрики (принцип VISION.md: false-reject хуже пропуска — считаем отдельно):
  - accuracy           — среди предсказаний match/mismatch (unsure ИСКЛЮЧЁН
                          из знаменателя — это не про accuracy, это отдельный исход)
  - false_reject_rate  — P(pred=mismatch | expected=match). ГЛАВНОЕ число:
                          верный шаг ошибочно помечен неверным — это фрустрирует
                          ребёнка сильнее, чем пропущенная ошибка.
  - false_accept_rate  — P(pred=match | expected=mismatch)
  - unsure_rate        — доля unsure среди отсканированных (НЕ ошибка
                          классификатора — это «перефотай», UX-трение)
  - confusion 2×3 (expected × predicted) + средний confidence по ячейке

Ретраи: LlmUnavailable (в т.ч. 429 — free-tier Gemini rate-limit) → пауза
``--delay × 3`` секунд, 1 ретрай; если снова падает — skip с пометкой
(попадает в n_skipped, исключён из всех метрик). Любая ДРУГАЯ ошибка —
skip сразу, без ретрая.

Запуск:
    cd backend && ../.venv/bin/python scripts/eval_stand.py --delay 5
    cd backend && ../.venv/bin/python scripts/eval_stand.py --provider openai --limit 10
    cd backend && ../.venv/bin/python scripts/eval_stand.py --dir data/eval --out results.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import mimetypes
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Скрипт запускается из backend/ — добавляем backend/ в sys.path (паттерн seed_demo.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── DSN helper (тот же паттерн, что fix_step_answer_leaks.py) ──

def _fix_dsn(dsn: str) -> str:
    """Приводит DSN к драйверу asyncpg (SQLAlchemy 2.0 async)."""
    if dsn.startswith("postgres://"):
        return dsn.replace("postgres://", "postgresql+asyncpg://", 1)
    if dsn.startswith("postgresql://") and "+asyncpg" not in dsn:
        return dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return dsn


# ── чистая логика метрик (юнит-тестируется без БД/сети) ──

@dataclass
class EvalOutcome:
    """Один пример: ожидание vs предсказание модели.

    predicted=None — пример пропущен (skip: файл/шаг не найден или
    LlmUnavailable после ретрая); исключается из всех метрик.
    """

    expected: str                      # "match" | "mismatch"
    predicted: str | None = None       # "match" | "mismatch" | "unsure" | None
    confidence: float | None = None


@dataclass
class Metrics:
    n_total: int
    n_scored: int
    n_skipped: int
    accuracy: float | None
    false_reject_rate: float | None
    false_accept_rate: float | None
    unsure_rate: float | None
    confusion: dict = field(default_factory=dict)              # (expected, predicted) -> count
    confusion_confidence: dict = field(default_factory=dict)   # (expected, predicted) -> avg confidence | None


def compute_metrics(outcomes: list[EvalOutcome]) -> Metrics:
    """Считает метрики по списку исходов. Чистая функция — без БД/сети.

    unsure ИСКЛЮЧЁН из знаменателя accuracy (см. докстринг модуля), но ВХОДИТ
    в знаменатель false_reject/false_accept (это реальный исход для примера
    с данным expected — просто не являющийся "reject"/"accept").
    """
    n_total = len(outcomes)
    scored = [o for o in outcomes if o.predicted is not None]
    n_scored = len(scored)
    n_skipped = n_total - n_scored

    confusion: dict[tuple[str, str], int] = {}
    conf_sum: dict[tuple[str, str], float] = {}
    for o in scored:
        key = (o.expected, o.predicted)
        confusion[key] = confusion.get(key, 0) + 1
        if o.confidence is not None:
            conf_sum[key] = conf_sum.get(key, 0.0) + o.confidence

    confusion_confidence: dict[tuple[str, str], float | None] = {}
    for key, count in confusion.items():
        confusion_confidence[key] = (conf_sum[key] / count) if key in conf_sum else None

    # accuracy — только среди предсказаний match/mismatch, unsure исключён
    decided = [o for o in scored if o.predicted in ("match", "mismatch")]
    accuracy = (
        sum(1 for o in decided if o.predicted == o.expected) / len(decided)
        if decided else None
    )

    expected_match = [o for o in scored if o.expected == "match"]
    false_reject_rate = (
        sum(1 for o in expected_match if o.predicted == "mismatch") / len(expected_match)
        if expected_match else None
    )

    expected_mismatch = [o for o in scored if o.expected == "mismatch"]
    false_accept_rate = (
        sum(1 for o in expected_mismatch if o.predicted == "match") / len(expected_mismatch)
        if expected_mismatch else None
    )

    unsure_rate = (
        sum(1 for o in scored if o.predicted == "unsure") / n_scored
        if n_scored else None
    )

    return Metrics(
        n_total=n_total,
        n_scored=n_scored,
        n_skipped=n_skipped,
        accuracy=accuracy,
        false_reject_rate=false_reject_rate,
        false_accept_rate=false_accept_rate,
        unsure_rate=unsure_rate,
        confusion=confusion,
        confusion_confidence=confusion_confidence,
    )


def _fmt(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def format_report(m: Metrics) -> str:
    """Текстовый отчёт по метрикам (используется и в stdout, и в тестах)."""
    lines = [
        f"n_total={m.n_total}  n_scored={m.n_scored}  n_skipped={m.n_skipped}",
        f"accuracy            = {_fmt(m.accuracy)}   (среди match/mismatch-предсказаний, unsure исключён)",
        f"false_reject_rate   = {_fmt(m.false_reject_rate)}   <- ГЛАВНОЕ число: верный шаг помечен неверным",
        f"false_accept_rate   = {_fmt(m.false_accept_rate)}",
        f"unsure_rate         = {_fmt(m.unsure_rate)}   (не ошибка — 'перефотай')",
        "confusion (expected -> predicted): count  avg_confidence",
    ]
    for expected in ("match", "mismatch"):
        for predicted in ("match", "mismatch", "unsure"):
            key = (expected, predicted)
            count = m.confusion.get(key, 0)
            conf = m.confusion_confidence.get(key)
            lines.append(f"  {expected:>8} -> {predicted:<8}: {count:>3}   avg_conf={_fmt(conf)}")
    return "\n".join(lines)


# ── I/O: labels.csv, photos/, results CSV ──

def _load_labels(labels_path: Path) -> list[dict]:
    with open(labels_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["decomp_idx"] = int(row["decomp_idx"])
        row["step_n"] = int(row["step_n"])
        if row["expected_verdict"] not in ("match", "mismatch"):
            raise ValueError(
                f"labels.csv: expected_verdict должен быть match|mismatch, "
                f"получено {row['expected_verdict']!r} (photo_file={row['photo_file']})"
            )
    return rows


def _guess_content_type(photo_path: Path) -> str:
    ctype, _ = mimetypes.guess_type(str(photo_path))
    return ctype or "image/jpeg"


def _write_results_csv(out_path: Path, log_rows: list[dict]) -> None:
    fieldnames = [
        "photo_file", "decomp_idx", "step_n", "expected_verdict",
        "predicted_verdict", "confidence", "seen_value", "skipped", "error",
    ]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(log_rows)


# ── DB-контекст (instruction_ru/expected_value/statement) ──

async def _resolve_context(conn, decomp_idx: int, step_n: int) -> dict | None:
    """Возвращает {instruction_ru, expected_value, statement} или None если шаг не найден."""
    from sqlalchemy import text

    row = (await conn.execute(
        text(
            "SELECT ps.instruction_ru, ps.expected_value, p.text_ru AS statement "
            "FROM problem_steps ps "
            "JOIN decomposition_problems dp ON dp.idx = ps.decomp_idx "
            "LEFT JOIN problems p ON p.id = dp.problems_db_id "
            "WHERE ps.decomp_idx = :decomp_idx AND ps.n = :step_n"
        ),
        {"decomp_idx": decomp_idx, "step_n": step_n},
    )).mappings().fetchone()
    if row is None:
        return None
    return {
        "instruction_ru": row["instruction_ru"],
        "expected_value": row["expected_value"],
        "statement": row["statement"] or "",
    }


# ── vision-вызов с ретраем ──

async def _classify_step(*, delay: float, **kwargs) -> tuple["object | None", str | None]:
    """Вызывает classify_step_photo. Возвращает (result, error).

    result=None — skip: другая ошибка (без ретрая) либо LlmUnavailable после
    единственного ретрая (пауза delay*3с).
    """
    from core.llm_openai import LlmUnavailable, classify_step_photo

    try:
        result = await classify_step_photo(**kwargs)
        return result, None
    except LlmUnavailable as exc:
        wait = delay * 3
        print(f"    LlmUnavailable/429 — пауза {wait:.1f}с, 1 ретрай...")
        await asyncio.sleep(wait)
        try:
            result = await classify_step_photo(**kwargs)
            return result, None
        except LlmUnavailable as exc2:
            return None, f"LlmUnavailable после ретрая: {exc2}"
    except Exception as exc:  # noqa: BLE001 — неожиданная ошибка, skip без ретрая
        return None, f"{type(exc).__name__}: {exc}"


# ── основной прогон ──

async def run(args: argparse.Namespace) -> Metrics:
    from sqlalchemy.ext.asyncio import create_async_engine

    from core.config import settings

    if args.provider:
        settings.vision_provider = args.provider

    eval_dir = Path(args.dir)
    labels_path = eval_dir / "labels.csv"
    photos_dir = eval_dir / "photos"
    if not labels_path.exists():
        print(f"labels.csv не найден: {labels_path}", file=sys.stderr)
        sys.exit(1)

    labels = _load_labels(labels_path)
    if args.limit is not None:
        labels = labels[: args.limit]

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = eval_dir / out_path

    engine = create_async_engine(_fix_dsn(args.dsn))
    outcomes: list[EvalOutcome] = []
    log_rows: list[dict] = []

    try:
        async with engine.connect() as conn:
            for i, label in enumerate(labels):
                photo_file = label["photo_file"]
                decomp_idx = label["decomp_idx"]
                step_n = label["step_n"]
                expected = label["expected_verdict"]
                photo_path = photos_dir / photo_file
                prefix = f"[{i + 1}/{len(labels)}] {photo_file}"

                ctx = await _resolve_context(conn, decomp_idx, step_n)
                if ctx is None:
                    print(f"{prefix}: SKIP — decomp_idx={decomp_idx} n={step_n} не найден в problem_steps")
                    outcomes.append(EvalOutcome(expected=expected, predicted=None))
                    log_rows.append({
                        "photo_file": photo_file, "decomp_idx": decomp_idx, "step_n": step_n,
                        "expected_verdict": expected, "predicted_verdict": "", "confidence": "",
                        "seen_value": "", "skipped": True, "error": "шаг не найден в БД",
                    })
                    continue

                if not photo_path.exists():
                    print(f"{prefix}: SKIP — файл не найден ({photo_path})")
                    outcomes.append(EvalOutcome(expected=expected, predicted=None))
                    log_rows.append({
                        "photo_file": photo_file, "decomp_idx": decomp_idx, "step_n": step_n,
                        "expected_verdict": expected, "predicted_verdict": "", "confidence": "",
                        "seen_value": "", "skipped": True, "error": "файл не найден",
                    })
                    continue

                # Пауза между вызовами — от 429 free-tier Gemini (не перед первым).
                if i > 0:
                    await asyncio.sleep(args.delay)

                result, error = await _classify_step(
                    delay=args.delay,
                    image_bytes=photo_path.read_bytes(),
                    content_type=_guess_content_type(photo_path),
                    statement=ctx["statement"],
                    instruction_ru=ctx["instruction_ru"],
                    expected_value=ctx["expected_value"],
                )

                if result is None:
                    print(f"{prefix}: SKIP — {error}")
                    outcomes.append(EvalOutcome(expected=expected, predicted=None))
                    log_rows.append({
                        "photo_file": photo_file, "decomp_idx": decomp_idx, "step_n": step_n,
                        "expected_verdict": expected, "predicted_verdict": "", "confidence": "",
                        "seen_value": "", "skipped": True, "error": error,
                    })
                    continue

                print(
                    f"{prefix}: expected={expected} predicted={result.verdict} "
                    f"conf={result.confidence:.2f} seen={result.seen_value!r}"
                )
                outcomes.append(EvalOutcome(
                    expected=expected, predicted=result.verdict, confidence=result.confidence,
                ))
                log_rows.append({
                    "photo_file": photo_file, "decomp_idx": decomp_idx, "step_n": step_n,
                    "expected_verdict": expected, "predicted_verdict": result.verdict,
                    "confidence": result.confidence, "seen_value": result.seen_value or "",
                    "skipped": False, "error": "",
                })
    finally:
        await engine.dispose()

    _write_results_csv(out_path, log_rows)
    print(f"\nPer-example лог: {out_path}")

    metrics = compute_metrics(outcomes)
    print()
    print(format_report(metrics))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", type=str, default=str(Path(__file__).resolve().parent.parent / "data" / "eval"),
                         help="Папка с photos/ и labels.csv (default: backend/data/eval)")
    parser.add_argument("--dsn", type=str,
                         default="postgresql://postgres:postgres@127.0.0.1:5432/nismathbot",
                         help="Postgres DSN (default: dev nismathbot)")
    parser.add_argument("--provider", type=str, choices=["gemini", "openai"], default=None,
                         help="Переопределяет settings.vision_provider (default: из env)")
    parser.add_argument("--limit", type=int, default=None, help="Ограничить число примеров")
    parser.add_argument("--delay", type=float, default=4.0, help="Пауза между вызовами, секунды (default 4.0)")
    parser.add_argument("--out", type=str, default="results.csv",
                         help="Файл per-example лога (относительно --dir, если не абсолютный путь)")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
