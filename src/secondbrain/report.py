"""Status reporting -> reports/latest.md (+ dated copy in reports/history)."""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .db import VaultDB
from .lint import lint_vault
from .models import now_iso
from .paths import assert_writable

__all__ = ["write_report"]


def write_report(cfg: Config, db: VaultDB, *, extra_notes: list[str] | None = None) -> Path:
    counts = db.counts()
    lint = lint_vault(cfg)
    day = now_iso()[:10]

    pending = sum(counts.get(s, 0) for s in ("new", "fetching", "extracted", "scouted",
                                             "deduped", "curated", "indexed", "retry",
                                             "needs_review", "needs_extraction"))
    done = counts.get("done", 0)
    failed = counts.get("failed", 0)
    dup = counts.get("duplicate", 0)
    jev_calls = db.usage_today("jev")

    lines = [
        f"# SecondBrain report — {now_iso()}", "",
        "## Queue", "",
        f"- done: **{done}**", f"- pending: **{pending}**", f"- duplicates: **{dup}**",
        f"- failed: **{failed}**", f"- needs_review: **{counts.get('needs_review', 0)}**",
        f"- needs_extraction: **{counts.get('needs_extraction', 0)}**", "",
        "### Full status breakdown", "",
        *[f"- `{k}`: {v}" for k, v in sorted(counts.items())], "",
        "## Jev / routing usage (today)", "",
        f"- Jev calls: {jev_calls}", "",
        "## Link integrity (mechanical lint)", "",
        lint.as_markdown(), "",
    ]
    if extra_notes:
        lines += ["## Notes", "", *[f"- {n}" for n in extra_notes], ""]
    lines += ["---", "_Fixes are proposed, not applied. Review and approve._", ""]

    reports = assert_writable("reports", cfg.root)
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "history").mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines)
    latest = reports / "latest.md"
    latest.write_text(content, encoding="utf-8")
    (reports / "history" / f"{day}.md").write_text(content, encoding="utf-8")
    return latest
