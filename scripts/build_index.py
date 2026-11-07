#!/usr/bin/env python
"""Rebuild wiki/index.md from page frontmatter."""

import _bootstrap_path  # noqa: F401
from secondbrain.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["index"]))
