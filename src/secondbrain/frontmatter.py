"""YAML frontmatter parsing/emitting for wiki Markdown pages.

Canonical field order and schema per the spec. Unavailable fields are omitted or
left null — never invented.
"""

from __future__ import annotations

import io
from typing import Any

import yaml

__all__ = ["FIELD_ORDER", "parse", "dump", "make_frontmatter", "validate"]

FIELD_ORDER = [
    "id", "title", "type", "status", "lang",
    "created", "updated", "captured_at", "published_at",
    "source_url", "canonical_url", "provider", "author",
    "sha256", "tags", "aliases", "related", "confidence", "provenance",
]

# Minimum required (non-null) fields for a well-formed page.
REQUIRED = ["id", "title", "type", "status", "created"]

_DELIM = "---"


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body). Empty dict if no frontmatter block."""
    if not text.startswith(_DELIM):
        return {}, text
    lines = text.splitlines()
    # find closing delimiter
    for i in range(1, len(lines)):
        if lines[i].strip() == _DELIM:
            fm_text = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1:])
            meta = yaml.safe_load(fm_text) or {}
            if not isinstance(meta, dict):
                meta = {}
            return meta, body.lstrip("\n")
    return {}, text


def make_frontmatter(**fields: Any) -> dict[str, Any]:
    """Build an ordered frontmatter dict, dropping None values (never invent)."""
    out: dict[str, Any] = {}
    for key in FIELD_ORDER:
        if key in fields and fields[key] is not None:
            out[key] = fields[key]
    # allow extra keys not in the canonical order, appended at the end
    for key, val in fields.items():
        if key not in out and val is not None:
            out[key] = val
    return out


def dump(meta: dict[str, Any], body: str) -> str:
    """Serialize frontmatter + body back to a Markdown string."""
    ordered = {k: meta[k] for k in FIELD_ORDER if k in meta}
    for k in meta:
        if k not in ordered:
            ordered[k] = meta[k]
    buf = io.StringIO()
    buf.write(_DELIM + "\n")
    yaml.safe_dump(ordered, buf, sort_keys=False, allow_unicode=True, default_flow_style=False)
    buf.write(_DELIM + "\n\n")
    buf.write(body.rstrip() + "\n")
    return buf.getvalue()


def validate(meta: dict[str, Any], required: list[str] | None = None) -> list[str]:
    """Return a list of problems; empty means valid."""
    req = required or REQUIRED
    problems = []
    for key in req:
        if not meta.get(key):
            problems.append(f"missing required field: {key}")
    status = meta.get("status")
    allowed_status = {
        "new", "draft", "active", "retired", "superseded", "needs_review", "needs_extraction",
    }
    if status and status not in allowed_status:
        problems.append(f"unknown status: {status!r}")
    return problems
