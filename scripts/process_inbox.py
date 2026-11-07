#!/usr/bin/env python
"""Process raw/inbox end to end. Passes through --claude and --limit."""

import sys

import _bootstrap_path  # noqa: F401
from secondbrain.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["process-inbox", *sys.argv[1:]]))
