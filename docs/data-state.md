# Data State

> Обновлено: 2026-06-22 (по результатам аудита). Качественный снимок схемы/контента. Точные счётчики — live-аудит из БД, не из этого файла.

## Контент (сидится из `backend/data/*.json`)

| Что | Состояние |
|---|---|
| Граф знаний (`nis_knowledge_graph_v01.json`) | ✅ 118 узлов (тем). Все node_id из задач существуют в графе (0 FK-нарушений) |
| Банк задач (`problems_v10.json`) | ✅ 2525 задач. 0 NULL в required-полях, image-пути в лимите |
| Картинки задач RU (`static/questions/`) | ✅ 2525 (генерятся `generate_images.py --lang ru` на build-time) |
| Картинки задач KZ (`static/questions_kz/`) | ⚠️ 2522 против 2525 RU — **3 KZ-карточки сломаны** (AUDIT DATA-2). Self-heal на чистом build |
| Локализация UI (ru/kz `.arb`) | ✅ 200/200 ключей, 0 пустых |

⚠️ **CLAUDE.md исторически врал:** заявлял «10000+ задач» и «29/80+ узлов». Реально — **2525 задач, 118 узлов** (AUDIT DATA-1, исправлено).

## Схема и миграции

- 8 таблиц, SQLAlchemy 2.0 async (`Mapped[...]`), asyncpg. Индексы под query-паттерны selector/stats (`ix_problems_node_id`, `ix_problems_raw_score`, `ix_attempts_student_node`).
- **Нет migration-фреймворка** (нет Alembic). Схема: `create_all` (НЕ альтерит existing-таблицы) + hand-list `ALTER` в `run.py:24-45`, покрывающий только `students`/`problem_reports`.
- ⚠️ **Migration-gap (AUDIT MIG-1):** FSRS-колонки `mastery` (`fsrs_stability`, `fsrs_difficulty`, `next_review_at`) НЕ в ALTER-листе. На **свежей БД** `create_all` строит полную схему — безопасно. При миграции **старой Railway-БД** без этих колонок → `UndefinedColumn` на practice-цикле.
- **Решение для revival:** стартовать со свежей БД (см. `docs/decisions/001-*`). Старые student-данные Railway НЕ переносим (личный проект, данные тестовые).

## Идемпотентность сидинга

- `seed.py` short-circuit'ит по row-count + gate по `problems_version`. Сид зовётся только при пустой `nodes` (`run.py:47`).
- ⚠️ **SEED-1 (дормантный):** `_sync_problems` матчит DB↔JSON **позиционно** (`ORDER BY id` + zip). Insert/delete в середине `problems_v10.json` → хвост перезаписывается на чужие строки. Путь за guard'ом (не на обычном деплое), но **правило: `problems_v10.json` только APPEND, никогда reorder/delete** до фикса на natural key.

## Инварианты (DoD при работе с данными)

- Каждый `node_id` из `problems_*.json` существует в графе (`nodes`).
- 0 NULL в required-полях задач; image-пути влезают в колонку.
- KZ-картинки = RU-картинки по количеству (после `generate_images.py --lang kz`).
- Деструктив данных (DROP/DELETE/TRUNCATE) — только с явного согласия владельца.
