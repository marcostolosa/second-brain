"""Source sensitivity policy + redaction (config/source-policy.yaml).

HIGH-risk material never auto-ingests, never auto-syncs, and is redacted before
any external call (Jev/Claude). Enforced here, not merely described in prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .models import Risk

__all__ = ["Policy", "load_policy", "Decision"]


@dataclass
class Decision:
    risk: str
    reasons: list[str]
    auto_ingest: bool
    allow_sync: bool
    allow_jev: bool


class Policy:
    def __init__(self, data: dict):
        self._d = data or {}
        self._compiled = {
            level: [re.compile(p) for p in (self._d.get("sensitive_signals", {}) or {}).get(level, [])]
            for level in ("high", "medium")
        }
        self._redact = [re.compile(p) for p in self._d.get("redact_before_external", [])]
        self._allow = set(self._d.get("public_allow_domains", []) or [])

    def classify(self, *, url: str | None, text: str | None) -> Decision:
        reasons: list[str] = []
        risk = self._d.get("default_risk", "low")

        blob = text or ""
        for level in ("high", "medium"):
            for rx in self._compiled[level]:
                if rx.search(blob):
                    reasons.append(f"signal:{level}:{rx.pattern[:40]}")
                    risk = self._raise(risk, level)

        handling = (self._d.get("handling", {}) or {}).get(risk, {})
        return Decision(
            risk=risk,
            reasons=reasons,
            auto_ingest=bool(handling.get("auto_ingest", True)),
            allow_sync=bool(handling.get("allow_sync", True)),
            allow_jev=bool(handling.get("allow_jev", True)),
        )

    def is_public_allowed(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return any(host == d or host.endswith("." + d) for d in self._allow)

    def redact(self, text: str) -> str:
        out = text
        for rx in self._redact:
            out = rx.sub(lambda m: (m.group(1) if m.lastindex else "") + "[REDACTED]", out)
        return out

    @staticmethod
    def _raise(current: str, level: str) -> str:
        order = {Risk.LOW.value: 0, Risk.MEDIUM.value: 1, Risk.HIGH.value: 2}
        return level if order.get(level, 0) > order.get(current, 0) else current


@lru_cache(maxsize=4)
def _load_cached(path_str: str, mtime: float) -> Policy:
    data = yaml.safe_load(Path(path_str).read_text(encoding="utf-8")) or {}
    return Policy(data)


def load_policy(root: Path) -> Policy:
    path = root / "config" / "source-policy.yaml"
    if not path.exists():
        return Policy({})
    return _load_cached(str(path), path.stat().st_mtime)
