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


@pytest.mark.asyncio
async def test_public_entrypoints_use_one_canonical_pwa_url(monkeypatch, tmp_path):
    """Root и /app больше не могут открыть legacy Flutter вместо учебного PWA."""
    import web as web_module

    # Маршрутная топология не должна зависеть от ignored локального build artifact.
    monkeypatch.setattr(web_module, "WEBAPP_DIST_DIR", tmp_path)
    real_app = web_module.app

    async with AsyncClient(
        transport=ASGITransport(app=real_app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        root_response = await ac.get("/")
        app_response = await ac.get("/app")

    assert root_response.status_code == 308
    assert root_response.headers["location"] == "/app/"
    assert app_response.status_code == 308
    assert app_response.headers["location"] == "/app/"


@pytest.mark.parametrize(
    ("legacy_path", "pwa_path"),
    [
        ("/login", "/app/login"),
        ("/lesson/mixtures-1", "/app/lesson/mixtures-1"),
    ],
)
@pytest.mark.asyncio
async def test_legacy_flutter_deep_links_redirect_to_react_pwa(
    legacy_path, pwa_path, monkeypatch, tmp_path
):
    """Сохранённые legacy-ссылки не возвращают ученика в старый интерфейс."""
    import web as web_module

    monkeypatch.setattr(web_module, "WEBAPP_DIST_DIR", tmp_path)
    real_app = web_module.app

    async with AsyncClient(
        transport=ASGITransport(app=real_app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        response = await ac.get(legacy_path)

    assert response.status_code == 308
    assert response.headers["location"] == pwa_path


@pytest.mark.asyncio
async def test_legacy_flutter_service_worker_retires_itself():
    """У уже установленных root-scope Flutter SW есть безопасный путь миграции."""
    from web import app as real_app

    async with AsyncClient(
        transport=ASGITransport(app=real_app),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/flutter_service_worker.js")

    assert response.status_code == 200
    assert "application/javascript" in response.headers["content-type"]
    assert response.headers["cache-control"] == "no-store, no-cache, must-revalidate"
    assert "flutter-app-cache" in response.text
    assert "registration.unregister" in response.text


@pytest.mark.parametrize(
    ("path", "redirect_target"),
    [
        ("", "/app/"),
        ("lesson/mixtures-1", "/app/lesson/mixtures-1"),
        ("api", None),
        ("api/nonexistent", None),
        ("api/v1/nonexistent", None),
        ("assets/nonexistent.js", None),
        ("favicon.ico", None),
    ],
)
def test_root_redirect_only_handles_client_routes(path, redirect_target):
    """PWA-redirect не должен маскировать API 404 и отсутствующие ассеты."""
    from web import _pwa_redirect_target

    assert _pwa_redirect_target(path) == redirect_target


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
