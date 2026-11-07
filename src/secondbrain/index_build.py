"""Rebuild wiki/index.md from page frontmatter — every page with a one-line summary.

The index is derived from the Markdown files (the source of truth), so it is
always reconstructible. Retired/superseded pages are listed but marked.
"""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .frontmatter import parse
from .models import now_iso

__all__ = ["build_index", "one_line_summary"]

_SECTIONS = [
    ("sources", "Sources"),
    ("entities", "Entities"),
    ("concepts", "Concepts"),
    ("questions", "Questions"),
]


def one_line_summary(body: str, limit: int = 140) -> str:
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        # skip headings, frontmatter rules, html, fences, italic meta, callouts/quotes
        if s.startswith(("#", "---", "<", "```", "_", ">")):
            continue
        if s.startswith(("- ", "* ")):
            s = s.lstrip("-* ").strip()
        if s.startswith("[!") or not s:
            continue
        return (s[:limit] + "…") if len(s) > limit else s
    return ""


def build_index(cfg: Config) -> Path:
    wiki = cfg.path("vault.wiki_dir", "wiki")
    lines = ["---", "id: index", "title: Index", "type: index", "status: active",
             f"created: {now_iso()}", f"updated: {now_iso()}", "---", "", "# Index", "",
             "Every page with a one-line summary. Rebuilt from page frontmatter.", ""]

    total = 0
    for sub, heading in _SECTIONS:
        d = wiki / sub
        if not d.exists():
            continue
        pages = sorted(d.glob("*.md"))
        if not pages:
            continue
        lines.append(f"## {heading}")
        lines.append("")
        for p in pages:
            meta, body = parse(p.read_text(encoding="utf-8", errors="replace"))
            title = meta.get("title") or p.stem
            status = meta.get("status", "")
            summary = one_line_summary(body)
            tag = f" `({status})`" if status in ("retired", "superseded", "needs_review") else ""
            link = f"[[{sub}/{p.stem}|{title}]]"
            lines.append(f"- {link}{tag} — {summary}" if summary else f"- {link}{tag}")
            total += 1
        lines.append("")

    lines.append(f"\n_{total} pages indexed._\n")
    out = wiki / "index.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
