"""Core data types and the item state machine."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any

__all__ = ["Status", "Kind", "Risk", "Item", "now_iso", "VALID_TRANSITIONS"]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Status(str, Enum):
    NEW = "new"
    FETCHING = "fetching"
    EXTRACTED = "extracted"
    SCOUTED = "scouted"
    DEDUPED = "deduped"
    CURATED = "curated"
    INDEXED = "indexed"
    DONE = "done"
    # off-path
    RETRY = "retry"
    NEEDS_REVIEW = "needs_review"
    NEEDS_EXTRACTION = "needs_extraction"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class Kind(str, Enum):
    TWEET = "tweet"
    ARTICLE = "article"
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"
    GITHUB = "github"
    NOTE = "note"
    IMAGE = "image"
    MEDIA = "media"
    UNKNOWN = "unknown"


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Allowed forward transitions (plus universal escapes to retry/failed/needs_*).
VALID_TRANSITIONS: dict[str, set[str]] = {
    Status.NEW: {Status.FETCHING, Status.EXTRACTED, Status.NEEDS_EXTRACTION},
    Status.FETCHING: {Status.EXTRACTED, Status.NEEDS_EXTRACTION},
    Status.EXTRACTED: {Status.SCOUTED},
    Status.SCOUTED: {Status.DEDUPED, Status.DUPLICATE},
    Status.DEDUPED: {Status.CURATED},
    Status.CURATED: {Status.INDEXED},
    Status.INDEXED: {Status.DONE},
}

_UNIVERSAL = {Status.RETRY, Status.FAILED, Status.NEEDS_REVIEW, Status.NEEDS_EXTRACTION,
              Status.DUPLICATE}


@dataclass
class Item:
    id: str
    kind: str = Kind.UNKNOWN.value
    status: str = Status.NEW.value
    risk: str = Risk.LOW.value
    source_url: str | None = None
    canonical_url: str | None = None
    sha256: str | None = None
    title: str | None = None
    inbox_path: str | None = None
    summary_path: str | None = None
    provider: str | None = None
    author: str | None = None
    published_at: str | None = None
    attempts: int = 0
    error: str | None = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def can_transition(self, to: str) -> bool:
        if to in _UNIVERSAL or to == self.status:
            return True
        return to in VALID_TRANSITIONS.get(self.status, set())  # type: ignore[arg-type]
