#!/usr/bin/env python
"""Dedupe check for a summary file: prints 'duplicate' or 'new'.

    python scripts/dedupe.py wiki/sources/<slug>.md
"""

import sys

import _bootstrap_path  # noqa: F401
from secondbrain.cli import main

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: dedupe.py <summary-path>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(["route", "--dedupe", sys.argv[1]]))
