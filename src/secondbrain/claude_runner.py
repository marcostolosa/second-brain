"""Invoke Claude Code headlessly (claude -p) for the Scout/Librarian/Answerer.

Never uses --dangerously-skip-permissions. Tools and permission mode are passed
explicitly and scoped per agent. Availability is detected; when claude is absent
the pipeline stays in mechanical mode.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from .config import Config

__all__ = ["claude_available", "ClaudeResult", "run_claude", "scout_cmd", "librarian_cmd"]


def claude_available() -> bool:
    return shutil.which("claude") is not None


@dataclass
class ClaudeResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


def run_claude(
    prompt: str,
    cfg: Config,
    *,
    model: str,
    allowed_tools: list[str],
    permission_mode: str = "acceptEdits",
    timeout: int = 600,
) -> ClaudeResult:
    if not claude_available():
        return ClaudeResult(False, "", "claude CLI not found on PATH", 127)
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--permission-mode", permission_mode,
        "--allowedTools", ",".join(allowed_tools),
    ]
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=str(cfg.root),
        )
        return ClaudeResult(res.returncode == 0, res.stdout, res.stderr, res.returncode)
    except subprocess.TimeoutExpired as e:
        return ClaudeResult(False, "", f"timeout after {timeout}s: {e}", 124)
    except OSError as e:
        return ClaudeResult(False, "", str(e), 1)


def scout_cmd(cfg: Config) -> list[str]:
    return ["Read", "Grep", "Glob", "Write"]


def librarian_cmd(cfg: Config) -> list[str]:
    return ["Read", "Grep", "Glob", "Edit", "Write", "Bash"]
