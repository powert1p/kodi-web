"""Release-контракты: fail-closed auth, readiness и безопасный Docker ingress."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"


def test_config_rejects_bot_token_as_jwt_secret() -> None:
    """BOT_TOKEN не должен становиться ключом подписи пользовательских JWT."""
    env = os.environ.copy()
    env.pop("JWT_SECRET", None)
    env["BOT_TOKEN"] = "telegram-token-is-not-a-jwt-secret"
    code = (
        "import dotenv; "
        "dotenv.load_dotenv = lambda *args, **kwargs: False; "
        "import core.config"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "JWT_SECRET" in result.stderr


@pytest.mark.parametrize(
    ("jwt_secret", "bot_token"),
    [
        ("short", "telegram-token"),
        ("same-secret-with-at-least-32-characters", "same-secret-with-at-least-32-characters"),
    ],
)
def test_config_rejects_weak_or_reused_jwt_secret(jwt_secret, bot_token) -> None:
    env = os.environ.copy()
    env["JWT_SECRET"] = jwt_secret
    env["BOT_TOKEN"] = bot_token
    code = (
        "import dotenv; "
        "dotenv.load_dotenv = lambda *args, **kwargs: False; "
        "import core.config"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "JWT_SECRET" in result.stderr


def test_config_rejects_unknown_vision_provider() -> None:
    env = os.environ.copy()
    env["JWT_SECRET"] = "release-test-secret-with-at-least-32-chars"
    env["VISION_PROVIDER"] = "gemni"
    code = (
        "import dotenv; "
        "dotenv.load_dotenv = lambda *args, **kwargs: False; "
        "import core.config"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "VISION_PROVIDER" in result.stderr


def test_default_gemini_chain_contains_only_current_ga_models() -> None:
    """Release default не должен начинаться с исчерпанной или выключенной модели."""
    env = os.environ.copy()
    env["JWT_SECRET"] = "release-test-secret-with-at-least-32-chars"
    env.pop("GEMINI_MODEL_CHAIN", None)
    code = (
        "import dotenv; "
        "dotenv.load_dotenv = lambda *args, **kwargs: False; "
        "from core.config import settings; "
        "print(','.join(settings.gemini_model_chain))"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "gemini-3.1-flash-lite,gemini-3.5-flash"


def test_database_url_components_round_trip_reserved_chars_and_spaces(monkeypatch) -> None:
    from core.config import _database_url_from_env

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_HOST", "postgres")
    monkeypatch.setenv("DB_USER", "kodi user")
    monkeypatch.setenv("DB_PASSWORD", "p@ss word%:/?#")
    monkeypatch.setenv("DB_NAME", "kodi data")

    parsed = make_url(_database_url_from_env())

    assert parsed.username == "kodi user"
    assert parsed.password == "p@ss word%:/?#"
    assert parsed.host == "postgres"
    assert parsed.database == "kodi data"


@pytest.mark.parametrize("threshold", ["nan", "inf", "-0.1", "0", "1.1", "broken"])
def test_config_rejects_unsafe_step_confidence_threshold(threshold) -> None:
    env = os.environ.copy()
    env["JWT_SECRET"] = "release-test-secret-with-at-least-32-chars"
    env["STEP_CONFIDENCE_THRESHOLD"] = threshold
    code = (
        "import dotenv; "
        "dotenv.load_dotenv = lambda *args, **kwargs: False; "
        "import core.config"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "STEP_CONFIDENCE_THRESHOLD" in result.stderr


@pytest.mark.asyncio
async def test_ready_reports_all_release_dependencies(monkeypatch, tmp_path) -> None:
    """Readiness зелёный только при DB, собранном PWA и активном AI-provider."""
    import web

    (tmp_path / "index.html").write_text("ready", encoding="utf-8")

    async def database_ready() -> bool:
        return True

    monkeypatch.setattr(web, "_database_is_ready", database_ready, raising=False)
    monkeypatch.setattr(web, "WEBAPP_DIST_DIR", tmp_path)
    monkeypatch.setattr(
        web,
        "settings",
        SimpleNamespace(
            vision_provider="gemini",
            gemini_api_key="configured",
            openai_api_key="",
        ),
        raising=False,
    )

    async with AsyncClient(
        transport=ASGITransport(app=web.app), base_url="http://test"
    ) as client:
        response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": True, "pwa": True, "ai_provider": True},
    }


@pytest.mark.asyncio
async def test_ready_fails_closed_when_database_is_down(monkeypatch, tmp_path) -> None:
    """Оркестратор не оставляет контейнер healthy при недоступной БД."""
    import web

    (tmp_path / "index.html").write_text("ready", encoding="utf-8")

    async def database_not_ready() -> bool:
        return False

    monkeypatch.setattr(web, "_database_is_ready", database_not_ready, raising=False)
    monkeypatch.setattr(web, "WEBAPP_DIST_DIR", tmp_path)
    monkeypatch.setattr(
        web,
        "settings",
        SimpleNamespace(
            vision_provider="gemini",
            gemini_api_key="configured",
            openai_api_key="",
        ),
        raising=False,
    )

    async with AsyncClient(
        transport=ASGITransport(app=web.app), base_url="http://test"
    ) as client:
        response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["checks"]["database"] is False


@pytest.mark.asyncio
async def test_stale_railway_origin_is_not_allowed_by_default() -> None:
    """Пустой CORS_ORIGINS означает same-origin, а не скрытый старый allowlist."""
    import web

    async with AsyncClient(
        transport=ASGITransport(app=web.app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/health",
            headers={"Origin": "https://kodi-web-production.up.railway.app"},
        )

    assert "access-control-allow-origin" not in response.headers


def test_compose_is_fail_closed_and_loopback_only() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert '"127.0.0.1:8300:8000"' in compose
    assert "0.0.0.0:8300:8000" not in compose
    assert "DB_PASSWORD: ${POSTGRES_PASSWORD:?" in compose
    assert "DATABASE_URL: postgresql" not in compose
    assert "${JWT_SECRET:?" in compose
    assert "GEMINI_API_KEY: ${GEMINI_API_KEY:-}" in compose
    assert "OPENAI_API_KEY: ${OPENAI_API_KEY:-}" in compose
    assert "http://localhost:8000/ready" in compose
    assert "d.get('status')=='ready'" in compose
    assert 'FORWARDED_ALLOW_IPS: "172.30.57.1"' in compose
    assert "172.30.57.0/24" in compose
    assert "gateway: 172.30.57.1" in compose

    online = (REPO_ROOT / "docker-compose.online.yml").read_text(encoding="utf-8")
    assert "ipv4_address: 172.30.57.2" in compose
    assert "ipv4_address: 172.30.57.3" in compose
    assert 'FORWARDED_ALLOW_IPS: "172.30.57.1,172.30.57.4"' in online
    assert "ipv4_address: 172.30.57.4" in online
    assert 'FORWARDED_ALLOW_IPS: "*"' not in online

    nginx = (REPO_ROOT / "docker/nginx/kodi-web.conf").read_text(encoding="utf-8")
    assert "X-Forwarded-For   $remote_addr;" in nginx
    assert "$proxy_add_x_forwarded_for" not in nginx


def test_docker_context_excludes_private_and_runtime_data() -> None:
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "backend/data/error_photos/" in dockerignore
    assert "error_photos/" in dockerignore
    assert "backups/" in dockerignore
    assert "backend/webapp_dist/" in dockerignore

    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "rm -rf /app/webapp_dist /app/web_static" in dockerfile


def test_docker_entrypoint_repairs_photo_volume_then_drops_privileges() -> None:
    """Named volume может прийти root-owned, но само приложение не должно быть root."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = BACKEND_DIR / "scripts" / "docker-entrypoint.sh"
    script = entrypoint.read_text(encoding="utf-8")

    syntax = subprocess.run(
        ["sh", "-n", str(entrypoint)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert syntax.returncode == 0, syntax.stderr
    assert 'chown -R app:app "$photo_dir"' in script
    assert 'exec /usr/sbin/runuser -u app -- "$@"' in script
    assert 'ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]' in dockerfile
    assert "USER app" not in dockerfile
