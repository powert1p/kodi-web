# Текущий план — kodi-web

**Обновлено:** 2026-07-16 · **Стратегия:** [docs/VISION.md](../VISION.md) · **Текущий production flow:** регистрация → адаптация → diagnostic → персональный NIS-route → photo-first lesson → при явном запросе guided → independent transfer. Дизайн-канон: [webapp/DESIGN_SYSTEM.md](../../webapp/DESIGN_SYSTEM.md) (v12 «Фокус-станция»).

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
- [x] ~~DESIGN заменить Roboto на выразительную систему~~ — закрыто v12: Alumni Sans для stage headings + Onest для чтения, verified production matrix.
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

### 2026-07-10 MVP Заход 1 «поэтапная подготовка НИШ» — DONE (ТЗ `docs/specs/2026-07-10-mvp-nish-path.md`)
- [x] Онбординг: has_activity в /wrong-tasks разводит новичка («Привет! Я Кёди» + CTA срез) и ветерана («Всё разобрано»).
- [x] Класс при регистрации (grade 4-7, обязательный шаг UI) + срез v2: окно difficulty по классу (7→[3,5]) + 2 стретча; live «иду в 7» = 12/12 задач ≥3, 0 примитива.
- [x] Теория «Как решать»: 114/114 карточек (Метод/Пример/Ловушка, 10 приняты владельцем контента) → nodes.theory_ru → в wrong-tasks payload → раскрывашка в drill. Доставка: seed_graph (свежая БД) + backfill_theory на старте (existing/прод) + scripts/seed_theory.py (перезаливка из cards-JSON).
- [x] Тьютор-grounding: theory узла + step_n застревания в промпт, 6 жёстких правил; чат возвращён в drill («Спросить Кёди», step_n прокинут). Live e2e: метод+встречный вопрос, ответ под выпрашиванием не выдал.
- [x] Один вход сдачи (нижний PhotoCapture удалён), фейковые стрик/очки удалены, фолбэк-ступень для задач без декомпозиции.
- [x] Ревью-волна opus: READY_WITH_MINOR (step_n ge=1 починен). Деплой aiplus + live-протык. Merge ff → main (c9bdc6c).
- Минорки из ревью в бэклог: мёртвый diagnose-путь (postDiagnose/useDiagnose + /trainer/diagnose без UI-консьюмера — возможно нужен для report-fix); срез 4 класса может дать <12 задач (by design); design-baseline drill.png устарел (нет харнесса регенерации).

### 2026-07-14 webapp v10 «Живое равенство» — DONE, исторический run
- [x] AI-native flow: frozen brief/rubric → 3 структурных концепта → production render → 3 независимых judges → consensus deltas → fix/review loop.
- [x] Полный mobile-first redesign Hub / Drill / Closure / Mini-srez / Analytics / Auth и всех loading/error/empty/wrong/success состояний; реальный AiPlus lockup и новый редкий mascot.
- [x] Финальный panel единогласно READY (8.71–8.88/10, `wow=true`); Round 11 production gate 43/43 на 320/375/1280, 71 tests, code review CLEAN. Evidence: [`docs/loops/runs/2026-07-14-webapp-v10-premium-mobile/round-11/RESULT.md`](../loops/runs/2026-07-14-webapp-v10-premium-mobile/round-11/RESULT.md).

### 2026-07-15 webapp v11 «Лента решения» — DONE локально

- [x] Clean-slate generator flow: frozen brief/rubric → 3 spatial directions → independent concept panel → production redesign.
- [x] Новый code-native seed mark вместо exact lockup; реальные белки из Drive вместо costume mascot; старый v10 — anti-reference.
- [x] Math-first Hub, компактный context Drill, functional solution rail, переработанные Srez/Closure/Analytics/Auth и route-specific states.
- [x] Strict production matrix: 44 состояний, 375×844 + 1280×900, keyboard/touch/network/input-preserve/normal+reduced motion, checksums 46/46.
- [x] Финальный blind production panel READY 3/3, score 8.75–8.91, panel avg 8.85, `wow=true` 3/3; evidence: `docs/loops/runs/2026-07-15-webapp-v11-squirrel-clean-slate/round-production-5/`.

### 2026-07-15 learning path v1 «Мой путь» — READY локально

- [x] После owner correction удалена дневная модель «Сегодня/закрыть ошибки»: главный вход `/app/` теперь показывает накопительный путь `курс → текущий блок → следующий урок`; старый hub сохранён в `/app/review`.
- [x] На первом экране остаётся один содержательный следующий шаг, а сам урок ведёт через `Пример → Вместе → Сам → Перенос → доказанный результат`.
- [x] Первый вертикальный урок по смесям работает end-to-end на серверных сессиях и попытках: fading support, transfer, resume, idempotency, stale-state `409` и BKT evidence.
- [x] Stable `content_idx`, curriculum manifest и safe startup sync поддерживают свежую и существующую БД; неоднозначный decomposition fallback теперь fail-closed.
- [x] Production gate: backend `176 passed`, frontend `89 passed`, production browser E2E 18 кадров без console/page/request/API ошибок, включая возврат в накопительный путь `0/1 → 1/1`; frozen path evidence 19/19, independent code re-review `CLEAN/READY`, blind panel `READY` 3/3 (avg `9.45`).
- [ ] Следующий продуктовый блок: уроки 2+ по тому же learning-path contract и выбор следующего named skill по mastery, без возврата к случайным одношаговым задачам.

### 2026-07-16 adaptive photo-first NIS — READY, ONLINE

- [x] Новый ученик проходит durable adaptation, честную карту математической подготовки NIS,
  адаптивную diagnostic, объяснимый персональный route и только затем явно начинает тему.
- [x] Default урок — одно содержательное решение на бумаге и одно фото. Guided включается только
  по явному «Не знаю, как решать», использует typed/options, не растит mastery и завершается новой
  independent transfer-задачей по фото.
- [x] Server-authoritative resume и identity binding закрывают refresh/relogin, stale revision,
  idempotent retry, cross-account pending photo и provider ABA. Unreadable/uncertain/provider
  error не записываются как математическая ошибка; retry использует сохранённое фото.
- [x] Итог полного решения определяет vision AI: ему передаются условие, все canonical stages,
  ожидаемые значения и правильный ответ. Backend проверяет только строгий JSON-контракт и при
  неоднозначном/повреждённом ответе возвращает `unsure`, не дублируя математическую проверку.
- [x] Mastery truth: probability ≥0.85 + минимум 3 самостоятельных correct + accuracy ≥0.5;
  guided evidence исключён, diagnostic 0.7 остаётся отдельным порогом.
- [x] Production evidence: backend `633 passed`, React `111 passed`, state matrix 40 состояний ×
  2 viewport, exact `linux/amd64` image, full real-Gemini CJM и outage→saved-photo recovery.
- [x] Blind design panel: READY 3/3, averages 8.69–9.06, `wow=true` 3/3; канон v12
  «Фокус-станция» без mascot в primary journey.
- [x] Online rollout: image-only r16 развёрнут без замены production DB и `error_photos`;
  `/ready` подтверждает database/PWA/AI provider, а реальный `IMG_4979.heic` прошёл 3/3 на
  исходной задаче и был отклонён 4/4 на контрольной задаче с обратным вопросом.
- [x] Online rollout r17: versioned `workspace_version=1` envelope развёрнут image-only;
  production CJM подтвердил контракт во всех активных состояниях, 5 реальных Gemini-вызовов,
  exact resume, mastery `3/4`, чистые browser/runtime errors и нулевые DB-инварианты.
- [x] ~~Один стабильный учебный экран без переходов~~ — закрыто run'ом
  `docs/loops/runs/2026-07-20-mobile-learning-workspace-v2/` (кандидат r4, blind-панель 3×READY
  8.63/8.69/8.56, задеплоен 2026-07-21): единый workbook 375/390/844×375/932×430/1280, AI-вердикты
  guided-шагов, контекстный tutor c Escape/focus-restore, публичный real-AI smoke. Остаточные P2 —
  в `RELEASE-VERIFICATION.md` рана (пилюля шапки/выход, галочка «ответ проверен» у неверного,
  гонка restore-фокуса при Escape впритык к ответу, «Например» дублируется в guided-подсказке).

### Бэклог тренажёра (после 2026-07-02)
- [x] ~~Онбординг нового ученика~~ — закрыто Заходом 1 (has_activity + HubOnboarding).
- [ ] Продуктовое решение: скрывать ли закрытые ошибки из wrong-tasks (сейчас «Закрыто 0 из 2» при закрытой теме — счётчик от recurring_errors, список от attempts).
- [ ] Подключить climb-down UI (GET /easier есть, фронт-консьюмера нет — fetchEasier без хука).
- [ ] Мелочи: FinishedCard «46 ₽» (валютный формат на арифметике); seed_demo.py `.scalar()` дважды; dead code (resolve_decomp import F401 в роутере, analytics/mock.ts, stale docstring).
- [ ] Обогатить diagnose-промпт полями context-pack (recurring_errors/past_diagnoses сейчас отбрасываются проекцией — структурно готово).
- [ ] ru+kz parity фронта; валидация vision на реальных рукописных фото НИШ; публичный vhost (root/Умид).
