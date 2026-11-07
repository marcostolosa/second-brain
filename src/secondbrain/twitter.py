"""X/Twitter capture via the FxTwitter API v2 (no HTML scraping).

Docs: https://docs.fxembed.com/api/twitter/
  GET https://api.fxtwitter.com/2/status/{id}
  GET https://api.fxtwitter.com/2/thread/{id}

Returns the raw JSON (kept immutable alongside the capture) plus a normalized
dict. Deleted tweets (404), rate limits (429), and 5xx are reported as status,
never fabricated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import requests

from .config import Config

__all__ = ["TweetResult", "TwitterError", "fetch_tweet", "fetch_thread"]

_API = "https://api.fxtwitter.com"


class TwitterError(Exception):
    def __init__(self, message: str, *, http_status: int | None = None, kind: str = "error"):
        super().__init__(message)
        self.http_status = http_status
        self.kind = kind  # deleted | rate_limited | server | network | error


@dataclass
class TweetResult:
    id: str
    url: str
    author_name: str | None
    author_screen_name: str | None
    text: str
    created_at: str | None
    media: list[dict[str, Any]] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    thread: list[dict[str, Any]] = field(default_factory=list)
    incomplete: bool = False          # long article/attachment/media not fully captured
    article_url: str | None = None
    article_title: str | None = None
    raw_json: bytes = b"{}"


def _request(path: str, cfg: Config) -> dict[str, Any]:
    f = cfg.get("fetch", {}) or {}
    ua = f.get("user_agent", "SecondBrain/0.1")
    timeout = float(f.get("timeout_seconds", 30))
    url = f"{_API}{path}"
    try:
        r = requests.get(url, headers={"User-Agent": ua, "Accept": "application/json"},
                         timeout=timeout)
    except requests.RequestException as e:
        raise TwitterError(f"network error: {e}", kind="network") from e

    if r.status_code == 404:
        raise TwitterError("tweet not found / deleted", http_status=404, kind="deleted")
    if r.status_code == 429:
        raise TwitterError("rate limited by FxTwitter", http_status=429, kind="rate_limited")
    if r.status_code >= 500:
        raise TwitterError(f"FxTwitter server error {r.status_code}",
                           http_status=r.status_code, kind="server")
    if r.status_code != 200:
        raise TwitterError(f"unexpected status {r.status_code}", http_status=r.status_code)
    try:
        data = r.json()
    except json.JSONDecodeError as e:
        raise TwitterError(f"invalid JSON from FxTwitter: {e}") from e
    data["_raw_bytes"] = r.content
    return data


def _tweet_from_obj(obj: dict[str, Any], author_top: dict[str, Any] | None,
                    raw: bytes) -> TweetResult:
    author = obj.get("author") or author_top or {}
    media_obj = obj.get("media") or {}
    media = []
    for m in (media_obj.get("all") or []):
        media.append({"type": m.get("type"), "url": m.get("url"), "width": m.get("width"),
                      "height": m.get("height")})

    text = obj.get("text") or obj.get("raw_text") or ""
    urls = [u.get("expanded_url") for u in ((obj.get("entities") or {}).get("urls") or [])
            if u.get("expanded_url")]

    # X Articles and note tweets keep their body outside the tweet payload.
    article = obj.get("article") or None
    article_url = None
    article_title = None
    incomplete = False
    if article:
        incomplete = True
        if isinstance(article, dict):
            article_title = article.get("title") or (article.get("article") or {}).get("title")
        article_url = text if text.startswith("http") else obj.get("url")
        if article_url and article_url not in urls:
            urls.append(article_url)
    if obj.get("is_note_tweet") and not text:
        incomplete = True

    return TweetResult(
        id=str(obj.get("id") or ""),
        url=obj.get("url") or "",
        author_name=author.get("name"),
        author_screen_name=author.get("screen_name"),
        text=text,
        created_at=obj.get("created_at"),
        media=media,
        urls=urls,
        incomplete=incomplete,
        article_url=article_url,
        article_title=article_title,
        raw_json=raw,
    )


def _extract_tweet_obj(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """FxTwitter v2 returns the tweet under 'status' (or 'tweet'); author at top."""
    obj = data.get("status") or data.get("tweet") or {}
    if not obj and "text" in data:
        obj = data
    return obj, data.get("author")


def fetch_tweet(tweet_id: str, cfg: Config) -> TweetResult:
    data = _request(f"/2/status/{tweet_id}", cfg)
    raw = data.pop("_raw_bytes", b"{}")
    code = data.get("code")
    if code and code != 200:
        kind = "deleted" if code == 404 else ("rate_limited" if code == 429 else "error")
        raise TwitterError(data.get("message", f"code {code}"), http_status=code, kind=kind)
    obj, author_top = _extract_tweet_obj(data)
    return _tweet_from_obj(obj, author_top, raw)


def fetch_thread(tweet_id: str, cfg: Config) -> TweetResult:
    data = _request(f"/2/thread/{tweet_id}", cfg)
    raw = data.pop("_raw_bytes", b"{}")
    code = data.get("code")
    if code and code != 200:
        kind = "deleted" if code == 404 else ("rate_limited" if code == 429 else "error")
        raise TwitterError(data.get("message", f"code {code}"), http_status=code, kind=kind)
    head, author_top = _extract_tweet_obj(data)
    container = data.get("thread") or {}
    posts = (container.get("thread") if isinstance(container, dict) else None) \
        or data.get("replies") or []
    if not head and posts:
        head = posts[0]
    result = _tweet_from_obj(head, author_top, raw)
    result.thread = [
        {"id": str(p.get("id") or ""), "text": p.get("text") or "",
         "created_at": p.get("created_at")}
        for p in posts if isinstance(p, dict)
    ]
    return result
