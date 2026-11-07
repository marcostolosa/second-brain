"""Vault lint — mechanical checks that work WITHOUT Obsidian running.

Mirrors the Obsidian CLI checks (orphans / unresolved / deadends) in pure Python
so the nightly job never blocks on the GUI/CLI being available. When the Obsidian
CLI *is* available, obsidian.py can supplement these.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .frontmatter import parse, validate

__all__ = ["LintReport", "lint_vault"]

_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
# Pages that are hubs by nature and should not be flagged as orphans.
_HUB_PAGES = {"index", "overview", "log"}


@dataclass
class LintReport:
    pages: int = 0
    unresolved: list[tuple[str, str]] = field(default_factory=list)  # (page, missing_target)
    orphans: list[str] = field(default_factory=list)                 # no inbound links
    deadends: list[str] = field(default_factory=list)                # no outbound links
    schema_problems: list[tuple[str, str]] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)               # pages with [!conflict]

    def as_markdown(self) -> str:
        def sect(title, rows):
            if not rows:
                return f"### {title}\n\n_none_\n"
            body = "\n".join(f"- {r}" for r in rows)
            return f"### {title} ({len(rows)})\n\n{body}\n"

        return "\n".join([
            f"**Pages scanned:** {self.pages}\n",
            sect("Unresolved links", [f"`{p}` -> `[[{t}]]`" for p, t in self.unresolved]),
            sect("Orphans (no inbound links)", self.orphans),
            sect("Dead ends (no outbound links)", self.deadends),
            sect("Schema problems", [f"`{p}`: {m}" for p, m in self.schema_problems]),
            sect("Conflict callouts", self.conflicts),
        ])


def _page_stem(path: Path) -> str:
    return path.stem.lower()


def lint_vault(cfg: Config) -> LintReport:
    wiki = cfg.path("vault.wiki_dir", "wiki")
    rep = LintReport()
    if not wiki.exists():
        return rep

    md_files = sorted(wiki.rglob("*.md"))
    stems = {_page_stem(p) for p in md_files}
    inbound: dict[str, int] = {s: 0 for s in stems}

    for path in md_files:
        rep.pages += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        meta, body = parse(text)
        stem = _page_stem(path)

        if meta:
            for prob in validate(meta):
                rep.schema_problems.append((stem, prob))
        if "[!conflict]" in text.lower():
            rep.conflicts.append(stem)

        targets = [m.group(1).strip().lower() for m in _WIKILINK.finditer(body)]
        targets = [t for t in targets if t]
        if not targets and stem not in _HUB_PAGES:
            rep.deadends.append(stem)
        for t in targets:
            tstem = Path(t).stem.lower()
            if tstem in inbound:
                inbound[tstem] += 1
            else:
                rep.unresolved.append((stem, t))

    for stem, count in inbound.items():
        if count == 0 and stem not in _HUB_PAGES:
            rep.orphans.append(stem)

    rep.unresolved.sort()
    rep.orphans.sort()
    rep.deadends.sort()
    return rep
