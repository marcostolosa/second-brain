"""Controlled capture — the ONLY component that writes into raw/.

Contract: raw/ is immutable to agents. Captures always create a NEW file (never
overwrite), record a SHA-256 of the bytes, and keep originals intact. Imports of
user-chosen files copy the bytes into raw/inbox/ without touching the source.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .frontmatter import dump, make_frontmatter
from .hashing import sha256_bytes, sha256_file
from .models import now_iso
from .paths import assert_writable, PathSecurityError
from .urls import normalize_url
from .utils import slugify, stamp

__all__ = ["CaptureResult", "write_raw", "capture_link", "capture_note", "import_file",
           "import_folder", "capture_links_file"]


@dataclass
class CaptureResult:
    path: Path
    sha256: str
    canonical_url: str | None = None


def write_raw(relpath: str, data: bytes, cfg: Config) -> Path:
    """Write bytes to a NEW file under raw/ (refuses to overwrite). Atomic."""
    target = assert_writable(relpath, cfg.root, allow_raw=True)
    if target.exists():
        raise PathSecurityError(f"refusing to overwrite existing raw file: {relpath}")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, target)
    return target


def _unique_inbox_name(cfg: Config, slug: str, ext: str) -> str:
    base = f"{stamp()}-{slug}"
    inbox = cfg.get("vault.raw_inbox", "raw/inbox")
    rel = f"{inbox}/{base}{ext}"
    n = 1
    while (cfg.root / rel).exists():
        rel = f"{inbox}/{base}-{n}{ext}"
        n += 1
    return rel


def capture_link(
    cfg: Config,
    url: str,
    *,
    title: str | None = None,
    comment: str | None = None,
    tags: list[str] | None = None,
    source: str = "manual",
) -> CaptureResult:
    """Write a captured-link Markdown stub into raw/inbox for later enrichment."""
    canonical = normalize_url(url)
    slug = slugify(title or canonical.split("//", 1)[-1])
    meta = make_frontmatter(
        type="captured-link",
        status="new",
        title=title or canonical,
        source_url=url,
        canonical_url=canonical,
        captured_at=now_iso(),
        tags=tags or None,
        provenance=f"captured via {source}",
    )
    body_lines = [f"# {title or canonical}", "", f"<{canonical}>", ""]
    if comment:
        body_lines += ["## Note", comment, ""]
    content = dump(meta, "\n".join(body_lines)).encode("utf-8")
    rel = _unique_inbox_name(cfg, slug, ".md")
    path = write_raw(rel, content, cfg)
    return CaptureResult(path=path, sha256=sha256_bytes(content), canonical_url=canonical)


def capture_note(
    cfg: Config, title: str, body: str, tags: list[str] | None = None
) -> CaptureResult:
    """Write a quick personal note into raw/inbox."""
    meta = make_frontmatter(
        type="note", status="new", title=title, captured_at=now_iso(),
        tags=tags or None, provenance="quick note",
    )
    content = dump(meta, f"# {title}\n\n{body}\n").encode("utf-8")
    rel = _unique_inbox_name(cfg, slugify(title), ".md")
    path = write_raw(rel, content, cfg)
    return CaptureResult(path=path, sha256=sha256_bytes(content))


def import_file(cfg: Config, src: str | Path) -> CaptureResult:
    """Copy a user-chosen file into raw/inbox without modifying the original."""
    src = Path(src).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"not a file: {src}")
    rel = _unique_inbox_name(cfg, slugify(src.stem), src.suffix.lower() or ".bin")
    target = assert_writable(rel, cfg.root, allow_raw=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise PathSecurityError(f"refusing to overwrite: {rel}")
    shutil.copy2(src, target)
    return CaptureResult(path=target, sha256=sha256_file(target))


def import_folder(cfg: Config, folder: str | Path, pattern: str = "*",
                  recursive: bool = True) -> list[CaptureResult]:
    """Bulk-import every matching file from a folder into raw/inbox.

    Works with a UNC/WSL path too (e.g. \\\\wsl$\\kali-linux\\home\\user\\lifeos),
    so it doubles as the bridge for pulling LifeOS sources into the vault. Reads
    the source files only; never modifies them.
    """
    folder = Path(folder).resolve()
    if not folder.is_dir():
        raise NotADirectoryError(f"not a folder: {folder}")
    globber = folder.rglob if recursive else folder.glob
    results: list[CaptureResult] = []
    for p in sorted(globber(pattern)):
        if p.is_file() and not p.name.startswith("."):
            results.append(import_file(cfg, p))
    return results


def capture_links_file(cfg: Config, path: str | Path) -> list[CaptureResult]:
    """Capture many links from a text file. One per line; '#' comments ignored.

    Optional pipe syntax per line: ``url | title | tag1,tag2``.
    """
    results: list[CaptureResult] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [x.strip() for x in line.split("|")]
        url = parts[0]
        title = parts[1] if len(parts) > 1 and parts[1] else None
        tags = [t.strip() for t in parts[2].split(",")] if len(parts) > 2 and parts[2] else None
        results.append(capture_link(cfg, url, title=title, tags=tags))
    return results
