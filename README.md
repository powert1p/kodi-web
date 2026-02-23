# kodi-web

NIS Math web application — Flutter frontend + FastAPI backend.

## Structure

```
kodi-web/
  backend/          # FastAPI REST API + core math logic
    api/routes.py   # REST endpoints
    core/           # diagnostic, exam, BKT, grading, graph
    db/             # SQLAlchemy models + seeding
    web.py          # FastAPI app
    run.py          # entry point
  frontend/
    apps/kodi_web/  # Flutter web application
    packages/kodi_core/  # shared Dart models & API client
  Dockerfile        # multi-stage: Flutter build + Python
```

## Local development

### Backend

```bash
cd backend
cp .env.example .env  # fill in DATABASE_URL, BOT_TOKEN
pip install -r requirements.txt
python run.py
```

### Frontend

```bash
cd frontend/apps/kodi_web
flutter pub get --directory ../../packages/kodi_core
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

## Deploy (Railway)

Single service — Dockerfile builds both frontend and backend.

```bash
railway up
```

Environment variables needed:
- `DATABASE_URL` (auto-set by Railway Postgres plugin)
- `BOT_TOKEN`
- `ADMIN_ID`
- `PORT` (auto-set by Railway)
