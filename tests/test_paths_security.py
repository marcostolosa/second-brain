"""Acceptance #5/#6: path allowlist, traversal, raw-write protection."""

import pytest

from secondbrain.paths import resolve_in_vault, assert_writable, PathSecurityError


def test_traversal_escape_blocked(vault):
    with pytest.raises(PathSecurityError):
        resolve_in_vault("../outside.md", vault.root)
    with pytest.raises(PathSecurityError):
        resolve_in_vault("wiki/../../etc/passwd", vault.root)


def test_write_to_raw_blocked_for_agents(vault):
    with pytest.raises(PathSecurityError):
        assert_writable("raw/inbox/x.md", vault.root)  # allow_raw defaults False


def test_write_to_raw_allowed_for_capture(vault):
    p = assert_writable("raw/inbox/x.md", vault.root, allow_raw=True)
    assert "raw" in str(p)


def test_write_outside_allowlist_blocked(vault):
    with pytest.raises(PathSecurityError):
        assert_writable(".env", vault.root)
    with pytest.raises(PathSecurityError):
        assert_writable("backups/x", vault.root)


def test_write_to_wiki_allowed(vault):
    assert assert_writable("wiki/entities/foo.md", vault.root)
    assert assert_writable("reports/latest.md", vault.root)


def test_scout_agent_tools_are_restricted():
    """Scout must not have Bash/Edit (cannot touch raw or run commands)."""
    import re
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / ".claude" / "agents" / "scout.md").read_text(encoding="utf-8")
    m = re.search(r"tools:\s*(.+)", text)
    tools = {t.strip() for t in m.group(1).split(",")}
    assert tools == {"Read", "Grep", "Glob", "Write"}
    assert "Bash" not in tools and "Edit" not in tools
