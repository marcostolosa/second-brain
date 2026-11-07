"""URL handling: normalization, tracking-param removal, X/Twitter helpers, and
an SSRF guard that blocks private/loopback/link-local destinations.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

__all__ = [
    "normalize_url",
    "strip_tracking",
    "tweet_id",
    "is_twitter_host",
    "SsrfError",
    "assert_public_http_url",
]

# Query keys stripped as tracking noise (exact or prefix match).
_TRACKING_EXACT = {
    "ref", "ref_src", "ref_url", "s", "t", "cxt", "si", "spm", "scwx",
    "fbclid", "gclid", "dclid", "yclid", "igshid", "igsh", "mc_cid", "mc_eid",
    "vero_id", "_hsenc", "_hsmi", "mkt_tok", "twclid",
}
_TRACKING_PREFIX = ("utm_",)

_TWEET_RE = re.compile(r"/status(?:es)?/(\d{5,25})")
_TWITTER_HOSTS = {
    "x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com",
    "fxtwitter.com", "www.fxtwitter.com", "fixupx.com", "www.fixupx.com",
    "vxtwitter.com", "nitter.net",
}


class SsrfError(Exception):
    """Raised when a URL resolves to a non-public or disallowed target."""


def is_twitter_host(host: str) -> bool:
    return host.lower() in _TWITTER_HOSTS


def strip_tracking(url: str) -> str:
    p = urlparse(url)
    kept = [
        (k, v)
        for (k, v) in parse_qsl(p.query, keep_blank_values=False)
        if k not in _TRACKING_EXACT and not k.lower().startswith(_TRACKING_PREFIX)
    ]
    return urlunparse(p._replace(query=urlencode(kept)))


def normalize_url(url: str) -> str:
    """Canonicalize: lowercase scheme/host, drop default port and fragment, strip
    tracking params, remove a trailing slash on non-root paths."""
    url = url.strip()
    p = urlparse(url)
    scheme = (p.scheme or "https").lower()
    host = (p.hostname or "").lower()
    netloc = host
    if p.port and not ((scheme == "http" and p.port == 80) or (scheme == "https" and p.port == 443)):
        netloc = f"{host}:{p.port}"
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    cleaned = urlunparse((scheme, netloc, path, "", p.query, ""))
    return strip_tracking(cleaned)


def tweet_id(url: str) -> str | None:
    m = _TWEET_RE.search(urlparse(url).path)
    return m.group(1) if m else None


def _is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def assert_public_http_url(url: str, *, allowed_schemes=("http", "https")) -> str:
    """Validate a URL for outbound fetching; raise SsrfError on any risk.

    Blocks non-http(s) schemes, hostless URLs, obvious internal names, and any
    host whose DNS resolution includes a private/loopback/link-local address
    (defends against DNS-rebinding to internal services).
    """
    p = urlparse(url)
    if p.scheme.lower() not in allowed_schemes:
        raise SsrfError(f"scheme not allowed: {p.scheme!r}")
    host = (p.hostname or "").lower()
    if not host:
        raise SsrfError("URL has no host")

    bad_names = {"localhost", "localhost.localdomain", "ip6-localhost"}
    if host in bad_names or host.endswith(".local") or host.endswith(".internal"):
        raise SsrfError(f"internal hostname blocked: {host!r}")

    # If host is a literal IP, check it directly.
    try:
        ipaddress.ip_address(host)
        if not _is_public_ip(host):
            raise SsrfError(f"non-public IP blocked: {host}")
        return url
    except ValueError:
        pass

    # Resolve and verify every A/AAAA record is public.
    try:
        infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80))
    except socket.gaierror as e:
        raise SsrfError(f"DNS resolution failed for {host!r}: {e}") from e

    ips = {sockaddr[0] for (*_, sockaddr) in infos}
    if not ips:
        raise SsrfError(f"no addresses for {host!r}")
    for ip in ips:
        if not _is_public_ip(ip):
            raise SsrfError(f"{host!r} resolves to non-public address {ip}")
    return url
