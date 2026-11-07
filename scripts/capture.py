#!/usr/bin/env python
"""Capture helper.

    python scripts/capture.py url <url> [--title T] [--comment C] [--tags a,b]
    python scripts/capture.py note <title> [--body B] [--tags a,b]
    python scripts/capture.py file <path>
"""

import sys

import _bootstrap_path  # noqa: F401
from secondbrain.cli import main

_MAP = {"url": "capture-url", "note": "capture-note", "file": "import-file",
        "folder": "import-folder", "links": "capture-links"}

if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] not in _MAP:
        print("usage: capture.py {url|note|file} ...", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main([_MAP[argv[0]], *argv[1:]]))
