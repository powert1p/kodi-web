"""Регрессии доверия к reverse proxy и защиты IP rate-limit buckets."""

from __future__ import annotations

import pytest
from starlette.requests import Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from api.routes import _rate_limit_key


TRUSTED_PROXY_IPS = "172.30.57.1,172.30.57.4"


async def _rate_key_after_proxy(*, peer: str, x_forwarded_for: str) -> str:
    captured: list[str] = []

    async def app(scope, receive, send) -> None:
        captured.append(_rate_limit_key(Request(scope)))
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = ProxyHeadersMiddleware(app, trusted_hosts=TRUSTED_PROXY_IPS)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/auth/phone/login",
        "raw_path": b"/api/auth/phone/login",
        "query_string": b"",
        "headers": [(b"x-forwarded-for", x_forwarded_for.encode("ascii"))],
        "client": (peer, 45123),
        "server": ("testserver", 80),
    }

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        return None

    await middleware(scope, receive, send)
    return captured[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("proxy_ip", ["172.30.57.1", "172.30.57.4"])
async def test_trusted_proxy_ignores_spoofed_left_xff_prefix(proxy_ip: str) -> None:
    """Host nginx и cloudflared берут правый реальный IP, а не подделку слева."""
    first = await _rate_key_after_proxy(
        peer=proxy_ip,
        x_forwarded_for="198.51.100.66, 203.0.113.9",
    )
    second = await _rate_key_after_proxy(
        peer=proxy_ip,
        x_forwarded_for="192.0.2.123, 203.0.113.9",
    )

    assert first == "ip:203.0.113.9"
    assert second == first


@pytest.mark.asyncio
async def test_untrusted_peer_cannot_override_client_ip() -> None:
    """Прямой peer вне allowlist не может подменить bucket через XFF."""
    key = await _rate_key_after_proxy(
        peer="172.30.57.99",
        x_forwarded_for="198.51.100.66, 203.0.113.9",
    )

    assert key == "ip:172.30.57.99"
