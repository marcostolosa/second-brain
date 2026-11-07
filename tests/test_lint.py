"""Acceptance #9 (lint without Obsidian) and #7 (conflict mechanism)."""

from secondbrain.lint import lint_vault


def _w(vault, rel, text):
    p = vault.root / "wiki" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_lint_detects_unresolved_orphans_deadends(vault):
    _w(vault, "concepts/alpha.md", "# Alpha\nsee [[beta]] and [[ghost]]\n")
    _w(vault, "concepts/beta.md", "# Beta\nstandalone, links to nothing\n")
    _w(vault, "concepts/gamma.md", "# Gamma\npoints to [[alpha]]\n")

    rep = lint_vault(vault)
    assert ("alpha", "ghost") in rep.unresolved
    assert "beta" in rep.deadends      # no outbound links
    assert "gamma" in rep.orphans      # no inbound links
    assert "beta" not in rep.orphans   # alpha links to beta
    assert "alpha" not in rep.deadends # alpha has outbound links


def test_conflict_callout_is_reported(vault):
    _w(vault, "concepts/x.md", "# X\n> [!conflict] sources disagree\nsee [[y]]\n")
    _w(vault, "concepts/y.md", "# Y\n> [!conflict] sources disagree\nsee [[x]]\n")
    rep = lint_vault(vault)
    assert "x" in rep.conflicts and "y" in rep.conflicts
