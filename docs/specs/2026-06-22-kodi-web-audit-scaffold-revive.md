# Spec: kodi-web — аудит → каркас → воскрешение

**Дата:** 2026-06-22 · **Тип:** L (3 фазы) · **Slug:** kodi-web-audit-scaffold-revive

## Цель
Старый проект kodi-web (адаптивная платформа по математике НИШ, делался на этапе обучения вайбкодингу,
последний коммит 2026-03-02) — провести архитектурный аудит, заложить каркас доков/правил по образцу CDP,
затем воскресить и задеплоить на свой VPS, чтобы он снова работал. Цель личная — поднять рабочим и развивать дальше.

## Scope
- **Фаза 1 — Аудит.** Исчерпывающий разбор: backend (core-алгоритмы BKT/grading/selector/diagnostic/exam, api/routes.py 1070 строк, db-слой), frontend (Flutter/BLoC), инфра/деплой, безопасность. Итог: `AUDIT-REPORT.md` с приоритизированным backlog и списком блокеров запуска.
- **Фаза 2 — Каркас.** Зеркалю структуру CDP: `PROJECT.md`, `.claude/rules/*.md`, `docs/{architecture,module-map,data-state}.md`, `docs/{decisions,plan,sessions,specs}`, `DESIGN_SYSTEM.md`. Root `CLAUDE.md` → указатель на доки.
- **Фаза 3 — Воскрешение + деплой.** Локальный запуск (backend+seed+Flutter build, smoke ядра), затем деплой на AiPlus VPS (свой compose-дир, отдельный Postgres, свежие порты, nginx vhost).

## Out-of-scope (якорь от расползания)
- Переписывание драйвера/стека (SQLAlchemy async+asyncpg, Flutter — оставляю как есть, работает).
- Новые продуктовые фичи, редизайн UI, изменение алгоритмов BKT/grading.
- Полный security-хардеринг и мониторинг продакшн-уровня (цель личная → только критичное; остальное в backlog).
- Чистка/удаление данных. Никаких DROP/DELETE/TRUNCATE.

## Продуктовые решения (от пользователя)
- Деплой — **на свой сервер/VPS** (не Railway), по образцу CDP-деплоя, инфру искать во «втором мозге» (vault).
- Цель — **личный проект, развивать дальше**: поднять рабочим, чинить только критичное, остальное в backlog.

## Технические решения (мои, обоснование в строку)
- Деплой на **тот же AiPlus VPS, что и CDP** (ssh `aiplus`, sudo НЕТ) — у пользователя один сервер, CDP — эталон; отдельный compose-дир `~/kodi-web`, свой Postgres-контейнер.
- Порты: api `127.0.0.1:8300`, postgres `127.0.0.1:5435` — заняты 8200/5432/5434 (CDP+системный PG); проверить свободность на хосте ПЕРЕД up (vault: compose-ports-check-host-before-up).
- Наружу — через **хостовый nginx vhost** (нужен root/Умид) ИЛИ временно SSH-туннель; vhost — последним, не блокирует (vault: cutover DNS-last).
- Каркас доков — **зеркало CDP** (минус data-engineering-специфика), адаптировать правила под SQLAlchemy/Flutter.
- Аудит — **Workflow с параллельными ридерами** по подсистемам + adversarial-верификация находок (ultracode).
- Локальный прогон — через **Docker** (паритет с прод Python 3.11), т.к. локально Python 3.14 может ломать зависимости.

## Критерии успеха (проверяемые)
- **Ф1:** `AUDIT-REPORT.md` покрывает backend core/api/db, frontend, инфра, security; каждая находка с `file:line`; есть раздел «блокеры запуска» и приоритизированный backlog (P0/P1/P2).
- **Ф2:** Существуют `PROJECT.md`, `.claude/rules/` (≥backend,frontend,deploy,sql,tests,decisions), `docs/{architecture,module-map,data-state}.md`, `DESIGN_SYSTEM.md`; `CLAUDE.md` ссылается на них; `git status` чистый после коммита доков.
- **Ф3:** Backend стартует в Docker против Postgres с засиженными данными (graph+problems), `GET /health` → 200; Flutter web билдится; задеплоен на VPS; live-проверка: `/health` → 200 и core-флоу (регистрация → задача → ответ → BKT update) проходит на проде.

## Риски
- Python 3.14 локально vs 3.11 прод → ломка зависимостей. Замечу: запускаю через Docker, не локальный python.
- Ноль тестов на 11k LOC backend → поведение не верифицируемо дёшево. Замечу/смягчу: добавлю smoke-тесты ядра при воскрешении.
- nginx vhost/SSL требует root (Умид) — внешняя зависимость фазы 3. Смягчу: сначала туннель, vhost асинхронно.
- Telegram-бот токен мог умереть → Telegram-вход сломан. Смягчу: проверю, фолбэк на phone-auth, отмечу в backlog.
