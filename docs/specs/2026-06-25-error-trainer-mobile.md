# 2026-06-25 — Тренажёр «Работа над ошибками» (mobile PWA, срез-driven)

**Цель.** Ребёнок ошибается в ежедневном срезе → мы тренажёр: показываем ГДЕ именно он ошибся (по фото рукописного решения), помогаем подсказками **не выдавая ответ**, закрепляем 2-3 похожими задачами, запоминаем тип ошибки для таргетинга следующих задач и аналитики владельцу. Это зерно нового mobile-first фронта продукта.

## Scope (v1 — вертикальный срез, доказывает петлю end-to-end)
- Новый mobile-first **PWA-фронт** (растёт из `cabinet/`: React19 + Vite + Tailwind v4 + React Router 7 + TanStack Query), свежий **«смелый энергичный»** дизайн, минимальный логин (backend JWT).
- **Hub:** список ошибок ученика из среза (diagnostic wrong-attempts), traffic-light state.
- **Drill ошибки:** авто-уровень по mastery (1 «не знаю тему» / 2 «забыл» / 3 «описка»); лесенка шагов (порт `useLadder`: hint→ступень-полегче→reveal); на уровне 3 / «проверь моё решение» — **ФОТО → grounded-диагноз gpt-5.4-mini** → найденный сбойный шаг + сократический хинт (не ответ) + транскрипция (receipts).
- **Closure:** 1-2 свежие проверочные задачи того же узла (другие числа) без подсказок → ошибка «закрыта».
- **Память:** `error_captures` (фото+диагноз) + `recurring_errors` (счётчик по микро-навыку) → таргетинг closure-задач + экран аналитики владельцу.
- **Backend:** сид `full_decomposition_v1.json` в БД (`micro_skills`/`problem_steps`/`problem_fingerprints`); эндпоинты `GET /trainer/wrong-tasks`, `POST /trainer/diagnose` (multipart), `GET /trainer/analytics`. Идемпотентные CREATE/ALTER в `run.py`.

## Out-of-scope (следующие волны)
Миграция остальных экранов (дашборд/практика/экзамен/граф) на новый фронт; свободное фото произвольной задачи; полноценный **чат-репетитор** (v1 = staged hints, не диалог); генерация теории-контента (v1 = краткий explainer из `solution_ru` + worked example); `getUserMedia` live-камера; родительский экран; удаление старого Flutter-фронта (заморозить, не трогать).

## Продуктовые решения (из ответов)
Только наши задачи (срез-anchored, новые — потом); vision = дешёвый OpenAI; уровень — авто по mastery+срезу; память → таргетинг + аналитика владельцу; дизайн — смелый энергичный, mobile-first.

## Технические решения (мои; обоснование 1 строкой)
- **Модель:** `gpt-5.4-mini`, `detail:high`, strict `json_schema`, «диагноз с транскрипцией» — handwriting OCR врёт 12-24%, receipts ловят misread. (`gpt-4o-mini` ретайрится; точный id сверю при интеграции, фолбэк-цепочка если 5.4 нет на аккаунте.)
- **Grounded-диагноз:** в промпт кладём канонические `steps[]` + правильный ответ + `wrong_answer` ученика → модель локализует расхождение, не решает с нуля → надёжнее free-form.
- **Fingerprint-first:** матч `answer_given` к `fingerprints[].wrong_answer` → бесплатная гипотеза причины без фото; фото уточняет шаг.
- **Фото:** `<input type=file accept=image/* capture=environment>` + клиент-сжатие (`createImageBitmap`→`OffscreenCanvas`→JPEG q0.8, ≤1568px, нормализует EXIF/HEIC); сервер-фолбэк `pillow-heif` (OpenAI HEIC не ест).
- **Лесенка/матчинг/хинты** — порт логики `cabinet` (`useLadder`, `lib/math.ts`, hints-контракт); визуал заново. Easier-rung = задача того же узла с меньшим `sub_difficulty` (данные, не генерация).
- **БД:** новые таблицы идемпотентным CREATE/ALTER в `run.py` (нет Alembic); сид `full_decomposition` одноразово.
- **PWA:** `vite-plugin-pwa` autoUpdate shell-only; `viewport-fit=cover`; 16px inputs; safe-area insets; manifest+maskable icon; KaTeX `overflow-x` на wrapper, `throwOnError:false`.
- **Privacy:** фото минора → OpenAI **платным API (НЕ data-sharing free-tier)**; в БД храним ключ файла, не блоб; retention/удаление — отметить в data-state.

## Критерии успеха (проверяемые)
- `pytest` зелёный: wrong-task builder, fingerprint-match, diagnose-response-parse, авто-уровень-роутер; `ruff` чисто.
- Frontend: `tsc` чисто, `vite build` проходит; Playwright (390px): логин→hub→drill→фото(мок)→диагноз→closure без ошибок консоли.
- `POST /trainer/diagnose` на тестовом фото → валидный `{transcription, failed_step, cause_text, level, micro_skill}`; `error_capture` + `recurring_errors` записались (SQL-инвариант).
- Авто-уровень: low/mid/high mastery → 1/2/3 (unit-тест).
- Деплой на `aiplus`, `/health` 200, live: пройти drill на проде.

## Риски
- **OCR врёт (12-24%)** → receipts + grounded-диагноз + «поправь, если не так»; валидировать на реальных НИШ-фото до доверия `failed_step`.
- **gpt-5.4 id** может отличаться на аккаунте → фолбэк-цепочка моделей + явная ошибка если ключа нет.
- **Сид 2.7MB** (2525×steps/fingerprints) → идемпотентно, один раз, не на каждый старт.
- **Scope велик** → строго v1-вертикаль, остальное волнами; не раздувать.
