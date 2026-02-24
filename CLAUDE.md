# NIS Math (kodi-web)

Адаптивная образовательная платформа по математике для учеников НИШ.
Монорепо: Flutter Web (frontend) + FastAPI (backend), деплой на Railway одним Docker-образом.

## Структура проекта

```
kodi-web/
├── backend/
│   ├── run.py                  # Точка входа, запуск uvicorn + сидинг БД
│   ├── web.py                  # FastAPI app, middleware, CORS, SPA-фолбэк
│   ├── api/routes.py           # ВСЕ REST эндпоинты (~930 строк)
│   ├── core/
│   │   ├── bkt.py              # Bayesian Knowledge Tracing (обновление mastery)
│   │   ├── selector.py         # Выбор следующей задачи (блочное чередование)
│   │   ├── diagnostic.py       # Диагностика: 3 фазы адаптивного тестирования
│   │   ├── exam.py             # Экзамен: Phase A (15 голов) + Phase B (5 подтем)
│   │   ├── grading.py          # Проверка ответов (8 правил + Claude LLM фолбэк)
│   │   ├── graph.py            # Операции с графом знаний (fringe, prerequisites)
│   │   ├── web_graph.py        # JSON граф для фронтенда
│   │   ├── config.py           # Настройки из .env
│   │   ├── classifiers/        # Автоклассификация задач по темам (20+ модулей)
│   │   └── scorers/            # Оценка сложности задач (20+ модулей)
│   ├── db/
│   │   ├── models.py           # SQLAlchemy модели (9 таблиц)
│   │   ├── base.py             # Подключение к БД, session factory
│   │   └── seed.py             # Загрузка графа + задач из JSON
│   └── data/
│       ├── nis_knowledge_graph_v01.json  # 80+ нод (темы)
│       └── problems_v10.json             # 10,000+ задач
├── frontend/
│   ├── apps/kodi_web/          # Flutter Web приложение
│   │   ├── lib/
│   │   │   ├── main.dart
│   │   │   ├── app/            # router.dart, config.dart, theme.dart
│   │   │   ├── features/       # auth, dashboard, practice, diagnostic, exam
│   │   │   └── shared/         # widgets (problem_card, answer_input, result_card, math_text)
│   │   └── web/                # index.html, telegram_login.html
│   └── packages/kodi_core/     # Общая библиотека (модели + API клиент)
│       └── lib/
│           ├── api/nis_api.dart    # HTTP клиент ко всем эндпоинтам
│           └── models/             # Student, Stats, GraphNode, Problem
├── Dockerfile                  # Multi-stage: Flutter build → Python serve
├── railway.toml                # Railway деплой конфиг
└── CLAUDE.md                   # ← этот файл
```

## CJM (Customer Journey Map)

```
1. РЕГИСТРАЦИЯ
   Телефон+PIN или Telegram OAuth → JWT токен → Student создан
   ↓
2. ДИАГНОСТИКА (опционально)
   Адаптивный тест: Phase 1 (5 якорных тем) → Phase 2 (глубокое сканирование) → Phase 3 (полное)
   Результат: Mastery записи для каждой протестированной темы
   ↓
3. ПРАКТИКА (основной цикл)
   Блочное чередование: 5 задач по одной теме → переключение на самую слабую
   Каждый ответ: BKT обновляет p_mastery → is_mastered проверяет порог 0.85
   Если тема mastered раньше 5 задач → переключение сразу
   Spaced repetition: mastered темы возвращаются на повторение по расписанию [1,3,7,21,60 дней]
   ↓
4. ЭКЗАМЕН (оценка прогресса)
   Phase A: тест 15 EXAM_HEADS (ключевые темы)
   Phase B: 5 самых неопределённых подтем
   Результат: обновлённые Mastery по всем затронутым темам
   ↓
5. ПРОСМОТР ПРОГРЕССА
   Граф знаний: ноды по статусу (mastered/partial/failed/untested)
   Статистика: решено, точность, стрик, освоенные темы
   Лидерборд: сравнение с другими
```

## Модели БД

| Таблица | Назначение | PK |
|---------|-----------|-----|
| `nodes` | Темы графа знаний (AR01, FR06, GE07...) | id (String) |
| `edges` | Пререквизитные связи между темами | from_node + to_node |
| `problems` | Банк задач (10k+), привязаны к нодам | id (auto) |
| `students` | Профили учеников (Telegram/телефон) | id (BigInt) |
| `mastery` | BKT mastery per student x node | student_id + node_id |
| `attempts` | Каждый ответ ученика | id (auto) |
| `problem_reports` | Жалобы на задачи | id (auto) |
| `settings` | Key-value конфигурация | key (String) |

### Ключевые поля Student
- `practice_count` — счётчик задач в практике (в БД, не в памяти)
- `current_practice_node` — текущая тема в блоке (для блочного чередования)
- `problems_on_current_node` — сколько задач решено в текущем блоке (из 5)
- `paused_diagnostic` (JSONB) — сохранённое состояние диагностики
- `diagnostic_complete` — прошёл ли диагностику
- `current_streak` / `longest_streak` — стрики активности

### Ключевые поля Mastery
- `p_mastery` — вероятность освоения (0.0–1.0), порог mastery = 0.85
- `attempts_total` / `attempts_correct` — статистика
- `next_review_at` — когда повторить (spaced repetition)

## Алгоритмы

### BKT (Bayesian Knowledge Tracing) — `core/bkt.py`
- Формула: P(L_{n+1}) = P(L_n|obs) + (1 - P(L_n|obs)) * P(T)
- Параметры per node: P(T)=0.3, P(G)=0.05, P(S)=0.1
- P(L0) = 0.1 (начальная вероятность)
- **MASTERY_THRESHOLD = 0.85**
- `is_mastered()`: p_mastery >= 0.85 AND attempts_correct >= 3 AND accuracy >= 50%
- `difficulty_adjusted_params()`: масштабирует P(G)/P(S) по raw_score задачи

### Селектор задач — `core/selector.py`
- **Блочное чередование**: 5 задач по теме → переключение
- При переключении выбирает самую слабую тему из heads + fringe
- Приоритет: spaced rep reviews → weakest unmastered → review stale → challenge
- Внутри темы: raw_score cascade (Tier 1-4) или sub_difficulty фолбэк

### Диагностика — `core/diagnostic.py`
- 3 фазы: якорные темы → глубокое сканирование → полное
- Адаптивно: если ответил правильно → сложнее, если неправильно → пререквизиты
- Пороги в диагностике — **НЕ** Bayesian, отдельная логика (0.7)
- `write_mastery_to_db()`: аддитивный скоринг L1=15%, L2=25%, L3=30%, L4=30%

### Экзамен — `core/exam.py`
- 15 EXAM_HEADS → 5 неопределённых подтем
- Пороги в экзамене — **НЕ** Bayesian, отдельная логика (0.7)
- BKT параметры для экзамена: SLIP/GUESS зависят от sub_difficulty

### Грейдинг — `core/grading.py`
- 8 правил: нормализация → exact → numeric → fraction → compact → multi-value → text-number → symbols
- Claude LLM фолбэк: если правила сказали "неверно", Claude Haiku перепроверяет

## API эндпоинты

### Auth
- `POST /api/auth/telegram` — вход через Telegram
- `POST /api/auth/phone/check` — проверка номера
- `POST /api/auth/phone/register` — регистрация
- `POST /api/auth/phone/login` — вход по PIN
- `GET /api/auth/me` — текущий профиль

### Практика
- `GET /api/practice/next` — следующая задача (блочное чередование)
- `POST /api/practice/answer` — отправить ответ → BKT update
- `POST /api/practice/skip` — пропустить задачу
- `POST /api/practice/exam/start` — начать тайм-экзамен

### Диагностика/Экзамен
- `POST /api/diagnostic/start` — начать (mode: exam/gaps/phase1/2/3)
- `GET /api/diagnostic/question` — следующий вопрос
- `POST /api/diagnostic/answer` — ответить
- `POST /api/diagnostic/finish` — завершить → write mastery
- `GET /api/diagnostic/status` — статус сессии

### Статистика
- `GET /api/stats/me` — персональная статистика
- `GET /api/graph/me` — граф знаний (JSON)

## Правила работы

### Пороги — НЕ ПУТАТЬ
- **BKT mastery (практика)**: `MASTERY_THRESHOLD = 0.85` в `bkt.py` — алгоритмический порог
- **Диагностика/экзамен**: 0.7 в `diagnostic.py` и `exam.py` — отдельная логика, НЕ трогать
- **Граф визуализация**: 0.7 в `web_graph.py` — UX порог для отображения, НЕ трогать

### SQL миграции
- `Base.metadata.create_all()` НЕ добавляет колонки в существующие таблицы
- Новые колонки нужно добавлять через `ALTER TABLE` на Railway вручную
- При добавлении полей с `server_default` — указывать для PostgreSQL совместимости

### In-memory состояние
- `_diagnostic_states` в routes.py — in-memory dict для диагностики/экзамена
- Бэкапится в `student.paused_diagnostic` (JSONB) для восстановления после рестарта
- Практика НЕ хранит состояние в памяти — всё в БД (current_practice_node, practice_count)

### Фронтенд
- State management: BLoC (AuthBloc, DashboardBloc) + StatefulWidget для страниц
- API клиент: `packages/kodi_core/lib/api/nis_api.dart`
- Конфиг: `apps/kodi_web/lib/app/config.dart` (API_BASE_URL через --dart-define)
- UI: Material 3, русский язык, LaTeX рендеринг через flutter_math_fork

## Деплой

- **Хостинг**: Railway (один сервис)
- **Docker**: multi-stage (Flutter build → Python serve)
- **БД**: PostgreSQL на Railway
- **Env**: BOT_TOKEN, DATABASE_URL, JWT_SECRET, ANTHROPIC_API_KEY (опционально)
- **Порт**: 8000
- **SPA**: FastAPI отдаёт Flutter static + фолбэк на index.html
