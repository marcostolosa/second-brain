#!/usr/bin/env python
"""Direct access to the full SecondBrain CLI."""

import sys

import _bootstrap_path  # noqa: F401
from secondbrain.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
