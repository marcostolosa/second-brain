#!/usr/bin/env python
"""Pure-Python vault lint (works without Obsidian running)."""

import _bootstrap_path  # noqa: F401
from secondbrain.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["lint"]))
