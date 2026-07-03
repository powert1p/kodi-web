# Текущий план — kodi-web

**Обновлено:** 2026-07-03 · **Стратегия:** [docs/VISION.md](../VISION.md) — этап 0 (ядро тренажёра) закрыт, следующий = Этап 1 «Поэтапная сдача» (MVP стартапа: eval-набор кириллица+клетка → consent-флоу → поэтапный флоу)

Контекст: воскрешение проекта из learning-эпохи. Полный разбор — [AUDIT-REPORT.md](../../AUDIT-REPORT.md), спека — [docs/specs/2026-06-22-kodi-web-audit-scaffold-revive.md](../specs/2026-06-22-kodi-web-audit-scaffold-revive.md).

| # | Задача | Статус | Источник |
|---|--------|--------|----------|
| 1 | Архитектурный аудит → AUDIT-REPORT.md | **done** (2026-06-22) | Workflow: 5 ридеров + adversarial verify |
| 2 | Каркас доков/правил по образцу CDP (PROJECT, architecture, module-map, data-state, DESIGN_SYSTEM, .claude/rules) | **done** (2026-06-22) | этот файл и есть часть каркаса |
| 3 | Воскрешение локально (Docker): P0-фиксы + backend+seed+Flutter build + smoke ядра | **done** (2026-06-22) | + найден/пофикшен tz-баг практики (timezone=True) |
| 4 | Деплой на свой VPS (compose, свой Postgres, порты 8300/5435) + live-проверка | **done, на проде** (2026-06-22) | `~/kodi-web` на `aiplus`, health 200, core-флоу зелёный. Осталось: nginx vhost от root/Умида (пока туннель) |

## P0 — блокеры запуска/деплоя (чинить в фазе 3)
- **BUILD-1** `git add backend/fonts/DejaVuSerif.ttf` (Docker build падает на свежем clone).
- **SEC-1** выделенный `JWT_SECRET` + fail-fast при пустом.
- **API-1** exam/start `IN :seen` → `expanding=True` / `= ANY()`.
- **ARCH-1** uvicorn single-worker (зафиксировать).
- **OPS-1** за nginx — `proxy_headers` + `forwarded_allow_ips`.
- **SEC-2** `CORS_ORIGINS` = домен VPS.
- **MIG-1** старт со свежей БД (полная схема через `create_all`).

## P1 — безопасность/корректность (по ходу)
- CORE-1 валидный Claude model id (`claude-haiku-4-5`) + проверить `ANTHROPIC_API_KEY`.
- AUTH-2 upgrade-on-login legacy SHA-256 PIN → bcrypt.
- SEC-3 `/docs` за `settings.debug`.
- OPS-1(db) bootstrap в FastAPI lifespan (чтобы `uvicorn web:app` тоже сидил схему).

## P2 — долг для дальнейшей разработки (backlog)
- TEST-0 добавить pytest + bloc_test (начать с pure-функций BKT/grading/diagnostic).
- ARCH-2 нумерованные миграции (Alembic-style) как в CDP.
- API-3 разбить монолит `routes.py` на `routers/` + `security.py` (Depends).
- FE-1/FE-2 убрать `dart:html` → `package:web`+`js_interop`.
- CORE-2 вынести/удалить dead `scorers/`+`classifiers/` (~40 модулей).
- CORE-3 выровнять/задокументировать порог 0.7 vs 0.85.
- DESIGN заменить Roboto на выразительный шрифт (DESIGN_SYSTEM рекомендации).
- Мелочи: см. AUDIT backlog P2.

## Тренажёр ошибок (2026-06-26) — статус
- [x] Backend: схема+сид декомпозиции, trainer-core, vision (Gemini), API (/wrong-tasks /diagnose /analytics) — 59 тестов.
- [x] Frontend: новый mobile-PWA `webapp/` (Duolingo-style), все экраны + phone+PIN auth.
- [x] E2E live (локально): login→hub→drill→фото→РЕАЛЬНЫЙ Gemini-диагноз. Спека `docs/specs/2026-06-25-error-trainer-mobile.md`, план `docs/superpowers/plans/2026-06-25-error-trainer-mobile.md`.
- [ ] ДЕПЛОЙ на aiplus: rsync → `docker compose up -d --build`; **GEMINI_API_KEY в ~/kodi-web/.env на сервере**; live-проверка /app/ + /health + drill.
- [ ] Closure/Analytics на живые данные (нет verification-эндпоинта; сейчас мок-fallback).
- [ ] Финальное whole-branch ревью; ru+kz parity фронта; валидация vision на реальных рукописных фото НИШ.

### 2026-06-26 деплой — DONE (кроме server-key)
- [x] Фронт под AiPlus design system (v4). rsync+docker build на aiplus, прод поднят: /health 200, /app/ PWA, 6 таблиц+сид (db_linked 61.8%), login→wrong-tasks live.
- [x] GEMINI_API_KEY на сервере, /diagnose live (2026-06-26).
- [x] Closure/Analytics live + финальное ревью — закрыто волной 2026-07-02 (ниже).

### 2026-07-02 бэк-ядро + ИИ-тьютор — DONE (спека `docs/specs/2026-07-02-error-trainer-backend-core.md`)
- [x] Каноническая таксономия = CC-слой; `node.tag`/`micro_skills.domain` deprecated; remap 372→337 отклонён (архив).
- [x] Context-pack (`core/agent_context.py`) — единый grounding для diagnose и чата.
- [x] Чат-тьютор: tutor_sessions/tutor_messages + POST /tutor/chat + TutorPanel в drill. Прод live: сократика, session reuse, history растёт.
- [x] Verification API (closure с мока → сервер, resolved по node_id), GET /problem-topics (+hub-блок), GET /easier.
- [x] Analytics контракт my_top BE↔FE. 77 pytest (реальный PG) + 43 vitest. E2E ALL PASS. Деплой aiplus + live-чат. Merge ff → main (15dea9f), push origin.

### 2026-07-03 граф v02 — DONE (вердикт `docs/specs/2026-07-03-graph-v02-verdict.md`)
- [x] Ручной проход Fable: 28 drop + 15 add рёбер, 7 retag тем, снос NM01-03/ALG01 (73 задачи → RN01/MD01/AL01, decomp-банк синхронно). 114 узлов/181 ребро/36 непустых тем.
- [x] Семантический тест-гейт (test_graph_semantics.py), пересборка дев-БД, миграция прода (пост-ассерты OK), live-проверка, merge → main.
- [ ] Бэклог графа: слить CB02≈CB04 (дубль «размещения без повторений»); cleanup 7 тем-сирот в прод-БД (нужно одобрение DELETE); косяки задач: FR05 (сравнение дробей требует десятичных), DA02 (пример с ускорением — физика), EQ06-пример дублирует EQ07.

### Бэклог тренажёра (после 2026-07-02)
- [ ] Онбординг нового ученика: у свежего аккаунта тренажёр пуст («Всё разобрано») — нет источника ошибок внутри PWA. Нужен мини-срез в PWA или мост к диагностике Flutter (замечено владельцем 2026-07-02).
- [ ] Продуктовое решение: скрывать ли закрытые ошибки из wrong-tasks (сейчас «Закрыто 0 из 2» при закрытой теме — счётчик от recurring_errors, список от attempts).
- [ ] Подключить climb-down UI (GET /easier есть, фронт-консьюмера нет — fetchEasier без хука).
- [ ] Мелочи: FinishedCard «46 ₽» (валютный формат на арифметике); seed_demo.py `.scalar()` дважды; dead code (resolve_decomp import F401 в роутере, analytics/mock.ts, stale docstring); in-flight guard useClosure.check.
- [ ] Обогатить diagnose-промпт полями context-pack (recurring_errors/past_diagnoses сейчас отбрасываются проекцией — структурно готово).
- [ ] ru+kz parity фронта; валидация vision на реальных рукописных фото НИШ; публичный vhost (root/Умид).
