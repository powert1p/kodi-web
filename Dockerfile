# ── Stage 1: Build Flutter web frontend ──────────────────────
FROM ghcr.io/cirruslabs/flutter:stable AS flutter-build

COPY frontend/ /frontend/

WORKDIR /frontend/apps/kodi_web

RUN flutter pub get --directory /frontend/packages/kodi_core && \
    flutter pub get

RUN mkdir -p assets/images && \
    flutter build web --release --no-tree-shake-icons \
      --dart-define=API_BASE_URL= \
      --dart-define=TG_BOT_NAME=nis_math_test_bot

# ── Stage 2: Python backend ─────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev graphviz && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

COPY --from=flutter-build /frontend/apps/kodi_web/build/web /app/web_static

RUN python scripts/generate_images.py --lang ru && \
    python scripts/generate_images.py --lang kz

EXPOSE 8000

CMD ["python", "run.py"]
