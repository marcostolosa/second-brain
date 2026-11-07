"""Small shared helpers: slugify, timestamps, safe index read."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

__all__ = ["slugify", "stamp", "read_text", "token_set"]

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
_WORD = re.compile(r"[a-z0-9]{3,}")


def slugify(text: str, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = _SLUG_STRIP.sub("-", text.lower()).strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "untitled"


def stamp() -> str:
    """Compact local timestamp for filenames: YYYYMMDD-HHMMSS."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def read_text(path: str | Path) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def token_set(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))
