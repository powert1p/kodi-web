# kodi-web (NIS Math)

Адаптивная образовательная платформа по математике для учеников НИШ. Ученик проходит диагностику,
решает задачи в адаптивном цикле (BKT-mastery + spaced repetition), сдаёт экзамены и видит прогресс
по графу знаний. Монорепо: **Flutter Web** (frontend) + **FastAPI** (backend), один Docker-образ.

- **Стек:** Python 3.11 + FastAPI + SQLAlchemy 2.0 async + asyncpg + PostgreSQL; Flutter Web + BLoC + flutter_math_fork
- **Масштаб:** backend ~11.4k LOC, frontend ~8.6k LOC, 8 таблиц, 118 узлов графа, 2525 задач
- **Статус:** воскрешается из learning-эпохи (последний коммит 2026-03-02). Цель — личная, развивать дальше.
- **Деплой (план):** self-hosted на свой VPS (Docker Compose, host nginx vhost) по образцу sibling-проекта CDP. Раньше был на Railway.

## Где что лежит (живые доки)

| Вопрос | Док |
|---|---|
| Как устроена система (слои, потоки, auth, алгоритмы) | [docs/architecture.md](docs/architecture.md) |
| Какой файл за что отвечает | [docs/module-map.md](docs/module-map.md) |
| Что с данными/схемой сейчас (известные проблемы) | [docs/data-state.md](docs/data-state.md) |
| Результаты аудита + backlog (P0/P1/P2) | [AUDIT-REPORT.md](AUDIT-REPORT.md) |
| Текущий план и backlog | [docs/plan/current.md](docs/plan/current.md) |
| Дизайн-токены (читать перед UI-работой) | [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) |
| Почему так решили (ADR) | [docs/decisions/](docs/decisions/) |
| Спеки фич | [docs/specs/](docs/specs/) (шаблон: `_template.md`) |
| Журнал сессий | [docs/sessions/](docs/sessions/) (пишет /wrap) |
| Инструкции для агентов | [CLAUDE.md](CLAUDE.md) + [.claude/rules/](.claude/rules/) |

## Быстрый старт (локально)

```bash
# Backend (нужен локальный Postgres + env JWT_SECRET, DATABASE_URL)
cd backend && cp .env.example .env   # заполнить DATABASE_URL, JWT_SECRET (обязательно!)
pip install -r requirements.txt && python run.py        # бутает схему + сидит данные

# Frontend
cd frontend/apps/kodi_web
flutter pub get --directory ../../packages/kodi_core && flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

> ⚠️ Перед любым redeploy: `backend/fonts/DejaVuSerif.ttf` должен быть в git (иначе Docker build падает — см. AUDIT-REPORT P0 #1).
