"""Thin wrapper around the Obsidian CLI (orphans / unresolved / deadends).

The CLI requires Obsidian to be running with the CLI enabled (Settings > General,
Obsidian >= 1.12.7). When unavailable, callers fall back to lint.py (pure Python).
"""

from __future__ import annotations

import shutil
import subprocess

from .config import Config

__all__ = ["cli_available", "run_checks"]


def cli_available(cfg: Config) -> bool:
    cmd = cfg.get("obsidian.cli_command", "obsidian")
    return shutil.which(cmd) is not None


def run_checks(cfg: Config, timeout: int = 60) -> dict[str, str | None]:
    """Run the three mechanical Obsidian checks. Values are stdout or None."""
    cmd = cfg.get("obsidian.cli_command", "obsidian")
    out: dict[str, str | None] = {"orphans": None, "unresolved": None, "deadends": None}
    if not cli_available(cfg):
        return out
    for check in list(out.keys()):
        try:
            res = subprocess.run(
                [cmd, check], capture_output=True, text=True, timeout=timeout,
                cwd=str(cfg.root),
            )
            out[check] = res.stdout if res.returncode == 0 else None
        except (subprocess.SubprocessError, OSError):
            out[check] = None
    return out
