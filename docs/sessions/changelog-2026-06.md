# Сессии — 2026-06

## 2026-06-22 15:47
**Тип:** plan (revival, 3 фазы)
**Зачем:** воскресить старый learning-эпохи проект kodi-web (адаптивная платформа по математике НИШ, последний коммит 2026-03-02): аудит → каркас доков → деплой на свой сервер, чтобы снова работал и можно было развивать.
**Что сделано:**
- Ф1 аудит (Workflow 5 ридеров + adversarial): AUDIT-REPORT.md. Вердикт — жив/воскрешаем; 1 P0 (untracked шрифт ломал build), 4 P1, долг ≈0 тестов.
- Ф2 каркас по образцу CDP: PROJECT.md, slim CLAUDE.md, DESIGN_SYSTEM.md, docs/{architecture,module-map,data-state}.md, .claude/rules/*, ADR-001. Исправлены неточности старого CLAUDE.md (2525 задач/118 нод/8 таблиц).
- Ф3 фиксы P0/P1 + docker-compose (свой Postgres) → локальный Docker → smoke ядра → деплой на VPS.
**Решение:** деплой self-hosted на тот же VPS, что CDP (aiplus), отдельный compose-дир ~/kodi-web, свежая БД, порты 8300/5435 (не Railway — выбор владельца; ADR-001). Стек kodi-web (SQLAlchemy async/asyncpg, Flutter) сохранён, не переписан под CDP.
**Итог:** ✅ задеплоено и живо на проде — kodi-app/kodi-postgres healthy, /health 200, core-флоу (register→задача→ответ→BKT p_mastery 0.305) зелёный, seed 118/2525, 0 ошибок. Авто-ревью (reviewer) APPROVE. Доступ с мака — SSH-туннель (ssh -L 8300:127.0.0.1:8300 aiplus). 5 коммитов в origin/main.
**Ключевая находка:** smoke-тест поймал P0, которого статический аудит не видел — timestamp-колонки naive vs datetime.now(timezone.utc) aware → asyncpg DataError на /practice/next (весь цикл практики падал). Фикс timezone=True заодно починил 2 латентных краша в spaced-repetition (selector.py:149,380).
**Открытые вопросы:** nginx vhost + SSL = root/Умид (домен подтвердить) — пока туннель; backlog аудита (тесты, Alembic-миграции, разбить routes.py 1070 строк, заменить Roboto-шрифт, dead code scorers/classifiers).
**Файлы:** AUDIT-REPORT.md, docker-compose.yml, backend/db/models.py, backend/{run,api/routes,core/config,core/grading}.py, .claude/rules/deploy.md
**Issue:** —
