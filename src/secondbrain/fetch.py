"""Safe HTTP fetching with SSRF defense, size caps, timeouts, and redirect limits.

Every hop (initial + each redirect) is re-validated as a public http(s) target, so
a redirect cannot bounce us into an internal service. Executables are never fetched
for execution; callers get raw bytes + the real content-type and preserve them.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

from .config import Config
from .urls import assert_public_http_url, SsrfError

__all__ = ["FetchResult", "FetchError", "fetch_url"]


class FetchError(Exception):
    pass


@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    status: int
    content_type: str
    content: bytes


def fetch_url(url: str, cfg: Config) -> FetchResult:
    f = cfg.get("fetch", {}) or {}
    schemes = tuple(f.get("allowed_schemes", ["http", "https"]))
    timeout = float(f.get("timeout_seconds", 30))
    max_redirects = int(f.get("max_redirects", 5))
    max_bytes = int(f.get("max_bytes", 25 * 1024 * 1024))
    ua = f.get("user_agent", "SecondBrain/0.1")

    session = requests.Session()
    session.headers.update({"User-Agent": ua, "Accept": "*/*"})

    current = url
    for _hop in range(max_redirects + 1):
        try:
            assert_public_http_url(current, allowed_schemes=schemes)
        except SsrfError as e:
            raise FetchError(f"blocked by SSRF guard: {e}") from e

        resp = session.get(current, timeout=timeout, allow_redirects=False, stream=True)
        if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get("Location")
            resp.close()
            if not loc:
                raise FetchError(f"redirect without Location at {current}")
            current = requests.compat.urljoin(current, loc)
            continue

        # terminal response — stream with a hard byte cap
        chunks = bytearray()
        for chunk in resp.iter_content(chunk_size=65536):
            chunks.extend(chunk)
            if len(chunks) > max_bytes:
                resp.close()
                raise FetchError(f"response exceeds max_bytes ({max_bytes})")
        ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        status = resp.status_code
        final = resp.url
        resp.close()
        return FetchResult(url, final, status, ct, bytes(chunks))

    raise FetchError(f"too many redirects (> {max_redirects})")
