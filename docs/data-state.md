# Data State

> Обновлено: 2026-07-03 (граф v02). Качественный снимок схемы/контента. Точные счётчики — live-аудит из БД, не из этого файла.

## Контент (сидится из `backend/data/*.json`)

| Что | Состояние |
|---|---|
| Граф знаний (`nis_knowledge_graph_v01.json`) | ✅ **v02 (2026-07-03): 114 узлов, 181 ребро** — ручная чистка логики рёбер (вердикт `docs/specs/2026-07-03-graph-v02-verdict.md`), снесена дубль-ветка NM01-03/ALG01 (73 задачи перепривязаны). Гейт: `tests/test_graph_semantics.py` |
| Слой тем CC (`cc_topics_v01.json`) | ✅ **v02: 36 тем + 38 рёбер, ВСЕ непустые**, мост 114 узлов→тема. 7 перепривязок исправили ложные темы. В прод-БД остались 7 тем-сирот (скрыты фильтром, cleanup при следующем одобрении) |
| Банк задач (`problems_v10.json`) | ✅ 2525 задач. 0 NULL в required-полях, image-пути в лимите |
| Картинки задач RU (`static/questions/`) | ✅ 2525 (генерятся `generate_images.py --lang ru` на build-time) |
| Картинки задач KZ (`static/questions_kz/`) | ⚠️ 2522 против 2525 RU — **3 KZ-карточки сломаны** (AUDIT DATA-2). Self-heal на чистом build |
| Локализация UI (ru/kz `.arb`) | ✅ 200/200 ключей, 0 пустых |

⚠️ **CLAUDE.md исторически врал:** заявлял «10000+ задач» и «29/80+ узлов». Реально — **2525 задач, 118 узлов** (AUDIT DATA-1, исправлено).

## Схема и миграции

- 10 таблиц, SQLAlchemy 2.0 async (`Mapped[...]`), asyncpg. Индексы под query-паттерны selector/stats (`ix_problems_node_id`, `ix_problems_raw_score`, `ix_attempts_student_node`).
- **Слой тем (2026-06-24):** `topics`(id CC/НИШ, strand, grade, order_idx, name_ru/kz), `topic_edges`(from→to, 61), колонка `nodes.topic_id` (FK логический, без констрейнта на existing-БД через `ALTER ... ADD COLUMN IF NOT EXISTS`). View-only — движок (BKT/diagnostic/practice/exam) их не читает.
- **Нет migration-фреймворка** (нет Alembic). Схема: `create_all` (НЕ альтерит existing-таблицы) + hand-list `ALTER` в `run.py:24-45`, покрывающий только `students`/`problem_reports`.
- ⚠️ **Migration-gap (AUDIT MIG-1):** FSRS-колонки `mastery` (`fsrs_stability`, `fsrs_difficulty`, `next_review_at`) НЕ в ALTER-листе. На **свежей БД** `create_all` строит полную схему — безопасно. При миграции **старой Railway-БД** без этих колонок → `UndefinedColumn` на practice-цикле.
- **Решение для revival:** стартовать со свежей БД (см. `docs/decisions/001-*`). Старые student-данные Railway НЕ переносим (личный проект, данные тестовые).

## Идемпотентность сидинга

- `seed.py` short-circuit'ит по row-count + gate по `problems_version`. Граф/задачи сидятся только при пустой `nodes`.
- ⚠️ **`seed_topics` — ИНАЧЕ:** зовётся ВСЕГДА (вне `if nodes==0`), идемпотентно (upsert тем `ON CONFLICT DO UPDATE`, рёбра `DO NOTHING`, `UPDATE nodes.topic_id`). Так темы доезжают и на уже засеянную прод-БД при каждом деплое (проверено: лог `Seeded 43 topics, 61 topic edges` на existing-БД).
- ⚠️ **SEED-1 (дормантный):** `_sync_problems` матчит DB↔JSON **позиционно** (`ORDER BY id` + zip). Insert/delete в середине `problems_v10.json` → хвост перезаписывается на чужие строки. Путь за guard'ом (не на обычном деплое), но **правило: `problems_v10.json` только APPEND, никогда reorder/delete** до фикса на natural key.

## Инварианты (DoD при работе с данными)

- Каждый `node_id` из `problems_*.json` существует в графе (`nodes`).
- 0 NULL в required-полях задач; image-пути влезают в колонку.
- KZ-картинки = RU-картинки по количеству (после `generate_images.py --lang kz`).
- Деструктив данных (DROP/DELETE/TRUNCATE) — только с явного согласия владельца.

## Тренажёр ошибок — новые таблицы (Обновлено: 2026-06-26)
6 новых таблиц (DDL: `backend/db/models.py` + идемпотентный `CREATE TABLE IF NOT EXISTS` в `run.py:on_startup`):
- **micro_skills** (code PK) — каталог 372 микро-умений.
- **decomposition_problems** (idx PK) — автономный банк декомпозиций из `docs/specs/full_decomposition_v1.json` (2525 задач). `problems_db_id` — best-effort FK к боевым problems по уникальному (node_id, answer); линкуется только **~42%** (idx ≠ боевой id, в декомпозиции нет текста). Педагогику берём по node+micro_skill из банка, не из exact-задачи.
- **problem_steps** (FK decomp_idx) — 7036 шагов (99% sympy-verified).
- **problem_fingerprints** (FK decomp_idx) — 3684 отпечатка типичных ошибок {wrong_answer, mistake_ru, micro_skill} (93% задач). Матч answer_given→mistake_ru = бесплатная гипотеза причины без фото.
- **error_captures** — факт ошибки по фото + диагноз (transcription/failed_step/cause_text/level/model/confidence/image_ref).
- **recurring_errors** (PK student_id+micro_skill) — накопление повторов для таргетинга + аналитики владельцу.
⚠️ Сид: `seed_decomposition()` в одной транзакции, guarded (только если пусто или FORCE_RESEED=1). ⚠️ Старая dev-БД `nismathbot` могла недосоздать error_captures/recurring_errors (ancient state) — лечится `Base.metadata.create_all`. На свежей серверной БД `run.py` создаёт все 6.

## Чат-тьютор + каноническая таксономия (Обновлено: 2026-07-02)
- **tutor_sessions** (id PK, UNIQUE(student_id, problem_id) — против гонки auto-create) и **tutor_messages** (FK session CASCADE, role/content) — история диалога с ИИ-тьютором. DDL идемпотентно в `run.py`. Итого таблиц: **18**.
- `recurring_errors.resolved` выставляется closure-флоу **по node_id** верификационной задачи (не по micro_skill — ключи диагноза и декомпозиции расходятся, см. commit 89ba073).
- **Каноническая таксономия = CC-слой** (strand→topic→node→micro_skill). Агрегат «проблемных тем» (`build_problem_topics`): error_captures→problems.node_id→nodes.topic_id→topics. **Deprecated (legacy, не удалять молча):** `node.tag` (15 плоских доменов) и `micro_skills.domain` — рантайм на них больше не группирует. `docs/specs/cc_topic_skill_tree.json` (remap 372→337) — архив, кодом не читается, remap решено НЕ делать.
