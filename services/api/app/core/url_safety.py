"""SSRF mitigation for user-controlled HTTP(S) URLs (ingestion, thumbnails).

Validates scheme and host, rejects credentials in URLs, resolves DNS and requires
globally routable addresses. Does not fully mitigate DNS rebinding (see comments).
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx

MAX_URL_LENGTH = 2048
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_MAX_BODY_BYTES = 6 * 1024 * 1024

_REDIRECT_STATUS = frozenset({301, 302, 303, 307, 308})

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "metadata.google.internal",
        "metadata.google.internal.",
        "kubernetes.default",
        "kubernetes.default.svc",
        "kubernetes.default.svc.cluster.local",
    }
)


class UnsafeUrlError(ValueError):
    """Raised when a URL must not be fetched (SSRF policy)."""


def _normalized_hostname(host: str) -> str:
    return host.lower().rstrip(".")


def _literal_ip_if_any(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    candidate = host.strip()
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1]
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        return None


def _ensure_global_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if not addr.is_global:
        raise UnsafeUrlError("URL target is not a globally routable address")


def _blocked_hostname(host: str) -> bool:
    norm = _normalized_hostname(host)
    if norm in _BLOCKED_HOSTNAMES:
        return True
    if norm == "169.254.169.254":
        return True
    if norm.endswith(".localhost"):
        return True
    return False


def _resolve_host_must_be_global(hostname: str, port: int) -> None:
    if _blocked_hostname(hostname):
        raise UnsafeUrlError("Host is not allowed for fetching")

    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise UnsafeUrlError(f"Cannot resolve host: {hostname}") from e

    if not infos:
        raise UnsafeUrlError(f"No addresses for host: {hostname}")

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            parsed_ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        _ensure_global_ip(parsed_ip)


def validate_safe_http_url(url: str) -> None:
    """Raise UnsafeUrlError if *url* must not be fetched."""
    if not url or not isinstance(url, str):
        raise UnsafeUrlError("URL is empty")

    cleaned = url.strip()
    if len(cleaned) > MAX_URL_LENGTH:
        raise UnsafeUrlError("URL is too long")

    parsed = urlparse(cleaned)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise UnsafeUrlError("Only http and https URLs are allowed")

    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrlError("URLs with embedded credentials are not allowed")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeUrlError("URL has no host")

    if _blocked_hostname(hostname):
        raise UnsafeUrlError("Host is not allowed for fetching")

    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80

    literal = _literal_ip_if_any(hostname)
    if literal is not None:
        _ensure_global_ip(literal)
        return

    _resolve_host_must_be_global(hostname, port)


@dataclass(frozen=True)
class SafeHttpResult:
    status_code: int
    content: bytes
    final_url: str


def _drain_response_body(response: httpx.Response, limit: int = 65536) -> None:
    n = 0
    for chunk in response.iter_bytes():
        n += len(chunk)
        if n >= limit:
            break


def _read_body_limited(response: httpx.Response, max_body_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > max_body_bytes:
            raise UnsafeUrlError("Response body is too large")
        chunks.append(chunk)
    return b"".join(chunks)


def safe_http_get(
    url: str,
    *,
    headers: dict[str, str],
    timeout: float,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
) -> SafeHttpResult:
    """GET *url* with manual redirects; each hop is validated."""
    current = url.strip()
    validate_safe_http_url(current)

    with httpx.Client(timeout=timeout, follow_redirects=False, verify=True) as client:
        for _ in range(max_redirects + 1):
            validate_safe_http_url(current)
            with client.stream("GET", current, headers=headers) as response:
                status = response.status_code
                if status in _REDIRECT_STATUS:
                    loc = response.headers.get("location")
                    if not loc:
                        raise UnsafeUrlError("Redirect response missing Location header")
                    _drain_response_body(response)
                    current = urljoin(current, loc.strip())
                    continue

                body = _read_body_limited(response, max_body_bytes)
                return SafeHttpResult(status_code=status, content=body, final_url=current)

    raise UnsafeUrlError("Too many redirects")
