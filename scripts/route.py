#!/usr/bin/env python
"""Jev router — reproduces the original interface.

    python scripts/route.py "<question>"          -> prints "sonnet" or "opus"
    python scripts/route.py --dedupe <summary>    -> prints "duplicate" or "new"
"""

import sys

import _bootstrap_path  # noqa: F401
from secondbrain.cli import main


def entry() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--dedupe":
        if len(args) < 2:
            print("usage: route.py --dedupe <summary-path>", file=sys.stderr)
            return 2
        return main(["route", "--dedupe", args[1]])
    return main(["route", args[0] if args else ""])


if __name__ == "__main__":
    raise SystemExit(entry())
