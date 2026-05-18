"""LAN-allowlist middleware for the mobile profile.

Rejects requests whose source IP is not RFC1918 private, loopback, or
link-local. Only active when ``settings.kos_profile == "mobile"``; install
explicitly from ``app.main``.

``X-Forwarded-For`` is trusted only when ``settings.trusted_proxy_count > 0``;
otherwise the source IP comes from ``request.client.host`` (the actual TCP peer).
"""

from __future__ import annotations

import ipaddress
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)


def _is_private_or_loopback(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local


def _effective_client_host(request: Request, trusted_proxy_count: int) -> str | None:
    if trusted_proxy_count > 0:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            chain = [h.strip() for h in xff.split(",") if h.strip()]
            if len(chain) >= trusted_proxy_count:
                return chain[-trusted_proxy_count]
    if request.client:
        return request.client.host
    return None


def install_lan_guard(app: FastAPI, trusted_proxy_count: int = 0) -> None:
    """Attach an HTTP middleware that 403s requests from non-private source IPs."""

    @app.middleware("http")
    async def lan_guard(request: Request, call_next):
        host = _effective_client_host(request, trusted_proxy_count)
        if host is None or not _is_private_or_loopback(host):
            log.info("lan_guard: rejecting request from %s", host)
            return JSONResponse(
                status_code=403,
                content={"detail": "Source IP not allowed", "code": "lan_guard"},
            )
        return await call_next(request)
