"""FastAPI app: REST API + SPA static serving for kodi-web."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from api.routes import router as api_router

logger = logging.getLogger(__name__)

STATS_DIR = Path("/tmp/nis_stats")
STATS_DIR.mkdir(parents=True, exist_ok=True)

WEB_STATIC_DIR = Path(__file__).resolve().parent / "web_static"
PROBLEM_IMAGES_DIR = Path(__file__).resolve().parent / "static"

MAX_AGE_SECONDS = 3600


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Disable CDN caching for API routes."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response


app = FastAPI(docs_url="/docs", redoc_url=None)

app.add_middleware(NoCacheMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if PROBLEM_IMAGES_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(PROBLEM_IMAGES_DIR)), name="problem_images")


def _cleanup_old_files() -> None:
    now = time.time()
    try:
        for f in STATS_DIR.iterdir():
            if f.suffix == ".html" and (now - f.stat().st_mtime) > MAX_AGE_SECONDS:
                f.unlink(missing_ok=True)
    except Exception:
        pass


def save_html(html_bytes: bytes) -> str:
    _cleanup_old_files()
    token = uuid.uuid4().hex[:16]
    path = STATS_DIR / f"{token}.html"
    path.write_bytes(html_bytes)
    return token


@app.get("/stats/{token}")
async def get_stats(token: str) -> HTMLResponse:
    if not token.isalnum() or len(token) > 32:
        raise HTTPException(status_code=400, detail="Invalid token")
    path = STATS_DIR / f"{token}.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return HTMLResponse(content=path.read_text(encoding="utf-8"))


if WEB_STATIC_DIR.exists():
    logger.info("Serving Flutter web from %s", WEB_STATIC_DIR)

    @app.get("/{full_path:path}")
    async def spa_fallback(request: Request, full_path: str):
        file_path = WEB_STATIC_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(WEB_STATIC_DIR / "index.html")
else:
    logger.info("No web_static/ directory — API-only mode")

    @app.get("/")
    async def health() -> dict:
        return {"status": "ok"}
