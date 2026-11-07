"""Path security: vault-root resolution and a hard directory allowlist.

Security-critical. Every file access in SecondBrain goes through here so that:
  * no agent/script can read or write outside C:\\SecondBrain (allowlist),
  * directory traversal ("..", absolute escapes) is rejected,
  * symlinks/junctions (NTFS reparse points) that escape the vault are rejected,
  * ``raw/`` is writable ONLY by the controlled capture path, never by agents.

Natural-language rules in CLAUDE.md are not trusted on their own; this module is
the mechanical enforcement the spec requires.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "PathSecurityError",
    "find_vault_root",
    "resolve_in_vault",
    "is_within",
    "assert_writable",
    "assert_readable",
    "RAW_PREFIXES",
]

# Paths (relative to root) that agents must never write to.
RAW_PREFIXES = ("raw",)

# Directories under the vault that are legitimately writable by the pipeline.
# ``raw`` is intentionally absent: only capture.py writes there, via write_raw().
_WRITABLE_SUBDIRS = ("wiki", "reports", "state", "logs", "templates")


class PathSecurityError(Exception):
    """Raised when a path escapes the vault or violates the allowlist."""


def find_vault_root(start: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the vault root.

    Order: ``SECONDBRAIN_ROOT`` env var, then walk up from *start* looking for a
    directory that contains both ``pyproject.toml`` and a ``wiki`` folder, then
    fall back to ``C:\\SecondBrain``.
    """
    env = os.environ.get("SECONDBRAIN_ROOT")
    if env:
        return Path(env).resolve()

    here = Path(start) if start is not None else Path(__file__).resolve()
    if here.is_file():
        here = here.parent
    for cand in [here, *here.parents]:
        if (cand / "pyproject.toml").exists() and (cand / "wiki").is_dir():
            return cand.resolve()

    return Path(r"C:\SecondBrain").resolve()


def _real(p: Path) -> Path:
    """Fully resolve a path, following reparse points, without requiring existence."""
    # os.path.realpath resolves symlinks/junctions on Windows and POSIX and does
    # not require the leaf to exist, so it is safe for not-yet-created targets.
    return Path(os.path.realpath(str(p)))


def is_within(child: Path, parent: Path) -> bool:
    """True iff *child* (after full real-path resolution) is inside *parent*."""
    rp = _real(parent)
    rc = _real(child)
    try:
        rc.relative_to(rp)
        return True
    except ValueError:
        return False


def resolve_in_vault(relpath: str | os.PathLike[str], root: Path | None = None) -> Path:
    """Resolve *relpath* against the vault root and verify it stays inside.

    Rejects absolute paths that escape, ``..`` traversal, and reparse points that
    point outside the vault. Returns the resolved absolute path.
    """
    root = (root or find_vault_root()).resolve()
    raw = Path(relpath)

    candidate = raw if raw.is_absolute() else (root / raw)
    resolved = _real(candidate)

    if not is_within(resolved, root):
        raise PathSecurityError(
            f"Path escapes vault: {relpath!r} -> {resolved} (root={root})"
        )

    # Defence in depth: reject any existing component that is a reparse point
    # whose real target leaves the vault.
    probe = resolved
    while probe != root and probe.parent != probe:
        if probe.exists() and not is_within(probe, root):
            raise PathSecurityError(f"Reparse point escapes vault: {probe}")
        probe = probe.parent

    return resolved


def assert_readable(relpath: str | os.PathLike[str], root: Path | None = None) -> Path:
    """Resolve and confirm the path is inside the vault (anything in-vault is readable)."""
    return resolve_in_vault(relpath, root)


def assert_writable(
    relpath: str | os.PathLike[str],
    root: Path | None = None,
    *,
    allow_raw: bool = False,
) -> Path:
    """Resolve and confirm the path is writable under the allowlist.

    ``raw/`` is refused unless *allow_raw* is True (used only by the controlled
    capture writer). All other writes must fall under a known writable subdir.
    """
    root = (root or find_vault_root()).resolve()
    resolved = resolve_in_vault(relpath, root)
    rel = resolved.relative_to(root.resolve())
    top = rel.parts[0] if rel.parts else ""

    if top in RAW_PREFIXES:
        if not allow_raw:
            raise PathSecurityError(
                f"Refusing to write under raw/ (immutable to agents): {rel}"
            )
        return resolved

    if top not in _WRITABLE_SUBDIRS:
        raise PathSecurityError(
            f"Write target not in allowlist {_WRITABLE_SUBDIRS}: {rel}"
        )
    return resolved
