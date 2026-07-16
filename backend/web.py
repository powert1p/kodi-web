"""FastAPI app: REST API + SPA static serving for kodi-web."""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.routes import limiter, router as api_router
from api.routers.learning import router as learning_router
from api.routers.trainer import router as trainer_router
from core.config import settings
from db.base import engine

logger = logging.getLogger(__name__)

STATS_DIR = Path("/tmp/nis_stats")
STATS_DIR.mkdir(parents=True, exist_ok=True)

PROBLEM_IMAGES_DIR = Path(__file__).resolve().parent / "static"
# Директория скомпилированного PWA (webapp/dist → копируется в образе)
WEBAPP_DIST_DIR = Path(__file__).resolve().parent / "webapp_dist"
PWA_ENTRYPOINT = "/app/"

LEGACY_FLUTTER_SERVICE_WORKER = """\
const LEGACY_CACHE_NAMES = [
  'flutter-app-cache',
  'flutter-temp-cache',
  'flutter-app-manifest',
];

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    await Promise.all(LEGACY_CACHE_NAMES.map((name) => caches.delete(name)));
    await self.clients.claim();
    const windows = await self.clients.matchAll({ type: 'window' });
    await self.registration.unregister();
    await Promise.all(windows.map((client) => client.navigate(client.url)));
  })());
});

self.addEventListener('fetch', () => {});
"""

MAX_AGE_SECONDS = 3600


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers and disable CDN caching for API routes."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response


app = FastAPI(docs_url="/docs", redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)

_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router)
app.include_router(trainer_router)
app.include_router(learning_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


async def _database_is_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Readiness DB check failed: %s", exc)
        return False


@app.get("/ready")
async def readiness_check():
    provider_ready = (
        bool(settings.gemini_api_key.strip())
        if settings.vision_provider == "gemini"
        else bool(settings.openai_api_key.strip())
    )
    checks = {
        "database": await _database_is_ready(),
        "pwa": (WEBAPP_DIST_DIR / "index.html").is_file(),
        "ai_provider": provider_ready,
    }
    if not all(checks.values()):
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks": checks},
        )
    return {"status": "ready", "checks": checks}

if PROBLEM_IMAGES_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(PROBLEM_IMAGES_DIR)), name="problem_images")


class SPAStaticFiles(StaticFiles):
    """StaticFiles с SPA-фоллбэком для клиентских роутов React PWA.

    StaticFiles(html=True) сам по себе отдаёт index.html ТОЛЬКО для точных
    directory-путей (например, корня /app/) — для произвольных клиентских
    роутов вида /app/srez или /app/drill/5 Starlette не находит файла/каталога
    и кидает честный 404. Из-за этого прямой переход по ссылке или refresh
    (F5) внутри PWA ломался ({"detail":"Not Found"} вместо страницы).
    Здесь на 404 для путей БЕЗ расширения (значит — не запрос ассета, а
    клиентский роут) отдаём index.html, дальше маршрутизацией занимается
    React Router на клиенте. Запросы к реальным файлам с расширением
    (.js/.css/.png/...), которых нет на диске, остаются честным 404 — иначе
    отсутствующий ассет молча подменялся бы HTML-страницей.
    """

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not os.path.splitext(path)[1]:
                return await super().get_response("index.html", scope)
            raise


# ── Канонический production-entrypoint React PWA ────────────────────────────
@app.get("/", include_in_schema=False)
@app.get("/app", include_in_schema=False)
async def pwa_entrypoint():
    return RedirectResponse(PWA_ENTRYPOINT, status_code=308)


@app.get("/flutter_service_worker.js", include_in_schema=False)
async def retire_legacy_flutter_service_worker():
    """Обновляет и снимает уже установленные root-scope Flutter service workers."""
    return Response(
        content=LEGACY_FLUTTER_SERVICE_WORKER,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Service-Worker-Allowed": "/",
        },
    )


# ── React PWA смонтирована на /app/ ─────────────────────────────────────────
# Порядок важен: /api и /health уже зарегистрированы через include_router
# и @app.get ВЫШЕ — Starlette обходит смонтированное субприложение только
# если маршрут не совпал с зарегистрированными эндпоинтами.
if WEBAPP_DIST_DIR.exists():
    logger.info("Serving PWA from %s at /app", WEBAPP_DIST_DIR)
    app.mount("/app", SPAStaticFiles(directory=str(WEBAPP_DIST_DIR), html=True), name="pwa")
else:
    logger.info("No webapp_dist/ directory — /app not mounted")


def _cleanup_old_files() -> None:
    now = time.time()
    try:
        for f in STATS_DIR.iterdir():
            if f.suffix == ".html" and (now - f.stat().st_mtime) > MAX_AGE_SECONDS:
                f.unlink(missing_ok=True)
    except OSError:
        pass


def save_html(html_bytes: bytes) -> str:
    _cleanup_old_files()
    token = uuid.uuid4().hex[:16]
    path = STATS_DIR / f"{token}.html"
    path.write_bytes(html_bytes)
    return token


def _pwa_redirect_target(full_path: str) -> str | None:
    """Переносит старые extensionless Flutter deep links в единый React PWA."""
    normalized = full_path.strip("/")
    if normalized == "api" or normalized.startswith("api/"):
        return None
    if normalized and os.path.splitext(normalized)[1]:
        return None
    if not normalized or normalized == "app":
        return PWA_ENTRYPOINT
    return f"{PWA_ENTRYPOINT}{normalized}"


@app.get("/stats/{token}")
async def get_stats(token: str) -> HTMLResponse:
    if not token.isalnum() or len(token) > 32:
        raise HTTPException(status_code=400, detail="Invalid token")
    path = STATS_DIR / f"{token}.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return HTMLResponse(content=path.read_text(encoding="utf-8"))


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """Канонизирует UI deep links в React PWA, не маскируя missing assets."""
    redirect_target = _pwa_redirect_target(full_path)
    if redirect_target:
        return RedirectResponse(redirect_target, status_code=308)
    raise HTTPException(status_code=404, detail="Not Found")
