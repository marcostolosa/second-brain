"""Deduplication: local-first (canonical id, sha256, text similarity), then Jev.

A duplicate *post* is not an *updated* post: exact byte/id matches dedupe, but
semantic near-matches only raise a flag and defer to Jev's Noul with a high
threshold. Conservative by design — never silently drop distinct material.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .db import VaultDB
from .jev_client import JevClient
from .models import Item
from .utils import token_set, read_text

__all__ = ["DedupeOutcome", "local_duplicate", "text_similarity", "semantic_dedupe"]


@dataclass
class DedupeOutcome:
    is_duplicate: bool
    reason: str
    existing_id: str | None = None
    score: float | None = None
    source: str = "local"


def text_similarity(a: str, b: str) -> float:
    """Jaccard similarity over 3+ char tokens (cheap, order-independent)."""
    ta, tb = token_set(a), token_set(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb) or 1
    return inter / union


def local_duplicate(db: VaultDB, item: Item) -> DedupeOutcome:
    """Exact-match dedupe by sha256 or canonical URL against already-ingested items."""
    prior = db.find_committed_duplicate(item)
    if prior:
        reason = "sha256 match" if prior.sha256 == item.sha256 else "canonical_url match"
        return DedupeOutcome(True, reason, prior.id, 1.0, "local")
    return DedupeOutcome(False, "no local match")


def semantic_dedupe(cfg: Config, db: VaultDB, summary_text: str) -> DedupeOutcome:
    """Ask Jev (or its deterministic mock) whether the index already covers this."""
    index_path = cfg.path("vault.wiki_dir", "wiki") / "index.md"
    index_text = read_text(index_path)
    jev = JevClient(cfg, db=db)
    verdict = jev.dedupe(summary_text, index_text)
    return DedupeOutcome(
        is_duplicate=(verdict.verdict == "duplicate"),
        reason=f"jev noul={verdict.score}",
        score=verdict.score,
        source=verdict.source,
    )
