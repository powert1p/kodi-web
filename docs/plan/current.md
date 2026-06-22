# Текущий план — kodi-web

**Обновлено:** 2026-06-22

Контекст: воскрешение проекта из learning-эпохи. Полный разбор — [AUDIT-REPORT.md](../../AUDIT-REPORT.md), спека — [docs/specs/2026-06-22-kodi-web-audit-scaffold-revive.md](../specs/2026-06-22-kodi-web-audit-scaffold-revive.md).

| # | Задача | Статус | Источник |
|---|--------|--------|----------|
| 1 | Архитектурный аудит → AUDIT-REPORT.md | **done** (2026-06-22) | Workflow: 5 ридеров + adversarial verify |
| 2 | Каркас доков/правил по образцу CDP (PROJECT, architecture, module-map, data-state, DESIGN_SYSTEM, .claude/rules) | **done** (2026-06-22) | этот файл и есть часть каркаса |
| 3 | Воскрешение локально (Docker): P0-фиксы + backend+seed+Flutter build + smoke ядра | in_progress | AUDIT revival checklist A+B |
| 4 | Деплой на свой VPS (compose, свой Postgres, свежие порты, nginx vhost) + live-проверка | pending | AUDIT revival checklist C; `.claude/rules/deploy.md` |

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
