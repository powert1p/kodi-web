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

# ── Stage 2: Build PWA (webapp) ──────────────────────────────
# node:20-slim — минимальный образ с npm; base=/app/ задаётся в vite.config.ts
FROM node:20-slim AS pwa-build

WORKDIR /webapp
COPY webapp/package.json webapp/package-lock.json ./
RUN npm ci

COPY webapp/ ./
# Базовый URL задан в vite.config.ts (base: '/app/') — same-origin, no overrides needed
RUN npm run build

# ── Stage 3: Python backend ──────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev graphviz && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
RUN rm -rf /app/webapp_dist /app/web_static
# Банк декомпозиций для сид-движка лежит в backend/data/ (в build-контексте; docs/ исключён .dockerignore)
# и уже попадает в образ через `COPY backend/ .` → /app/data/full_decomposition_v1.json.

# Flutter SPA — корень /
COPY --from=flutter-build /frontend/apps/kodi_web/build/web /app/web_static

# PWA «Работа над ошибками» — монтируется на /app/ в web.py
COPY --from=pwa-build /webapp/dist /app/webapp_dist

RUN python scripts/generate_images.py --lang ru && \
    python scripts/generate_images.py --lang kz

RUN useradd -m -s /bin/bash app && \
    chown -R app:app /app && \
    chmod 0755 /app/scripts/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["python", "run.py"]
