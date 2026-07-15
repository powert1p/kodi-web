"""SPA-фоллбэк для /app/* (React PWA «Работа над ошибками»).

Прямой заход/refresh на клиентский роут (без расширения в пути) должен
отдавать index.html, а не 404 — иначе /app/srez или /app/drill/5 по прямой
ссылке ломались. Ассеты с расширением и /api/* фоллбэк не затрагивает.

Компонент (SPAStaticFiles) тестируется на изолированном мини-приложении с
tmp_path — не зависит от того, собран ли реальный backend/webapp_dist в
текущем окружении. Отдельно — smoke против настоящего web.py:app, если
webapp_dist в этом окружении реально собран (пропускается, если нет).
"""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-chars")

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from web import SPAStaticFiles, WEBAPP_DIST_DIR


@pytest.fixture
def pwa_dir(tmp_path):
    """Мини-копия структуры webapp_dist: index.html + assets/app.js."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(
        "<!doctype html><title>kodi PWA</title>", encoding="utf-8"
    )
    (tmp_path / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    return tmp_path


@pytest.fixture
def spa_app(pwa_dir):
    """Изолированное ASGI-приложение с тем же монтированием, что в web.py."""
    app = FastAPI()
    app.mount("/app", SPAStaticFiles(directory=str(pwa_dir), html=True), name="pwa")
    return app


@pytest.mark.asyncio
async def test_spa_route_falls_back_to_index(spa_app):
    """Прямой заход на клиентский роут (/app/srez) → index.html, 200."""
    async with AsyncClient(transport=ASGITransport(app=spa_app), base_url="http://test") as ac:
        r = await ac.get("/app/srez")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "kodi PWA" in r.text


@pytest.mark.asyncio
async def test_spa_nested_route_falls_back_to_index(spa_app):
    """Вложенный клиентский роут (/app/drill/5) — тоже index.html."""
    async with AsyncClient(transport=ASGITransport(app=spa_app), base_url="http://test") as ac:
        r = await ac.get("/app/drill/5")
    assert r.status_code == 200
    assert "kodi PWA" in r.text


@pytest.mark.asyncio
async def test_missing_asset_stays_404(spa_app):
    """Несуществующий ассет с расширением (/app/assets/nonexistent.js) — честный 404."""
    async with AsyncClient(transport=ASGITransport(app=spa_app), base_url="http://test") as ac:
        r = await ac.get("/app/assets/nonexistent.js")
    assert r.status_code == 404
    assert "kodi PWA" not in r.text


@pytest.mark.asyncio
async def test_existing_asset_served_as_is(spa_app):
    """Существующий ассет отдаётся как обычный файл, а не подменяется index.html."""
    async with AsyncClient(transport=ASGITransport(app=spa_app), base_url="http://test") as ac:
        r = await ac.get("/app/assets/app.js")
    assert r.status_code == 200
    assert "console.log" in r.text


@pytest.mark.asyncio
async def test_api_404_stays_json():
    """/api/* не затронут SPA-фоллбэком — обычный JSON 404 от FastAPI."""
    from web import app as real_app

    async with AsyncClient(transport=ASGITransport(app=real_app), base_url="http://test") as ac:
        r = await ac.get("/api/nonexistent")
    assert r.status_code == 404
    assert r.json() == {"detail": "Not Found"}


@pytest.mark.skipif(not WEBAPP_DIST_DIR.exists(), reason="webapp_dist не собран в этом окружении")
@pytest.mark.asyncio
async def test_real_app_spa_route_smoke():
    """Smoke против реально смонтированного /app в web.py — та же логика, что в spa_app."""
    from web import app as real_app

    async with AsyncClient(transport=ASGITransport(app=real_app), base_url="http://test") as ac:
        route_resp = await ac.get("/app/srez")
        asset_resp = await ac.get("/app/assets/nonexistent.js")
    assert route_resp.status_code == 200
    assert "text/html" in route_resp.headers["content-type"]
    assert asset_resp.status_code == 404
