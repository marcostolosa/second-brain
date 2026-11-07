"""Content hashing. SHA-256 over the raw bytes of originals, for identity & dedupe."""

from __future__ import annotations

import hashlib
from pathlib import Path

__all__ = ["sha256_bytes", "sha256_file", "short"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def short(digest: str, n: int = 12) -> str:
    return digest[:n]
