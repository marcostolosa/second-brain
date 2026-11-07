"""SQLite queue/state store — reconstructible from the Markdown files.

Durability: WAL journal + synchronous=NORMAL survive interruption/power loss.
Concurrency: a single-writer OS lock (one worker per vault) plus an append-only
events table for the audit log. The DB holds state only; the wiki is the truth.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .config import Config
from .models import Item, Status, now_iso
from .paths import assert_writable

__all__ = ["VaultDB", "single_writer_lock", "LockError"]


class LockError(Exception):
    pass


@contextmanager
def single_writer_lock(cfg: Config, timeout: float = 30.0) -> Iterator[None]:
    """Exclusive cross-process lock so only one writer touches the vault at a time.

    Uses msvcrt on Windows and fcntl elsewhere, over a lock file in state/.
    """
    state_dir = assert_writable("state", cfg.root)
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / "writer.lock"
    fh = open(lock_path, "a+b")
    deadline = time.monotonic() + timeout
    try:
        if os.name == "nt":
            import msvcrt

            while True:
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise LockError("another writer holds the vault lock") from None
                    time.sleep(0.25)
        else:  # pragma: no cover - POSIX path, Windows is the target
            import fcntl

            while True:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise LockError("another writer holds the vault lock") from None
                    time.sleep(0.25)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                try:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:  # pragma: no cover
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id            TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,
    status        TEXT NOT NULL,
    risk          TEXT NOT NULL DEFAULT 'low',
    source_url    TEXT,
    canonical_url TEXT,
    sha256        TEXT,
    title         TEXT,
    inbox_path    TEXT,
    summary_path  TEXT,
    provider      TEXT,
    author        TEXT,
    published_at  TEXT,
    attempts      INTEGER NOT NULL DEFAULT 0,
    error         TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    meta          TEXT NOT NULL DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_items_sha ON items(sha256) WHERE sha256 IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_items_canon ON items(canonical_url);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);

CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id   TEXT NOT NULL,
    ts        TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    note      TEXT
);

CREATE TABLE IF NOT EXISTS usage (
    day       TEXT NOT NULL,
    component TEXT NOT NULL,
    calls     INTEGER NOT NULL DEFAULT 0,
    tokens    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, component)
);
"""


class VaultDB:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        db_dir = assert_writable("state", cfg.root)
        db_dir.mkdir(parents=True, exist_ok=True)
        self.path = db_dir / "secondbrain.sqlite3"
        self.conn = sqlite3.connect(str(self.path), isolation_level=None, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.conn.executescript(_SCHEMA)

    # --- lifecycle --------------------------------------------------------
    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "VaultDB":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- queries ----------------------------------------------------------
    def get(self, item_id: str) -> Item | None:
        row = self.conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        return self._row_to_item(row) if row else None

    def by_sha(self, sha: str) -> Item | None:
        row = self.conn.execute("SELECT * FROM items WHERE sha256=?", (sha,)).fetchone()
        return self._row_to_item(row) if row else None

    def by_canonical(self, url: str) -> Item | None:
        row = self.conn.execute(
            "SELECT * FROM items WHERE canonical_url=?", (url,)
        ).fetchone()
        return self._row_to_item(row) if row else None

    def find_committed_duplicate(self, item: Item) -> Item | None:
        """A DIFFERENT, already-ingested item with the same sha or canonical URL.

        Only committed statuses count, so two not-yet-processed siblings do not
        mark each other as duplicates.
        """
        row = self.conn.execute(
            "SELECT * FROM items WHERE id != ? "
            "AND status IN ('deduped','curated','indexed','done','duplicate') "
            "AND (sha256 = ? OR (canonical_url IS NOT NULL AND canonical_url = ?)) "
            "ORDER BY created_at LIMIT 1",
            (item.id, item.sha256 or "", item.canonical_url or ""),
        ).fetchone()
        return self._row_to_item(row) if row else None

    def list_by_status(self, status: str) -> list[Item]:
        rows = self.conn.execute(
            "SELECT * FROM items WHERE status=? ORDER BY created_at", (status,)
        ).fetchall()
        return [self._row_to_item(r) for r in rows]

    def counts(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT status, COUNT(*) c FROM items GROUP BY status"
        ).fetchall()
        return {r["status"]: r["c"] for r in rows}

    # --- mutations (idempotent upsert) ------------------------------------
    def upsert(self, item: Item) -> Item:
        existing = self.get(item.id)
        item.updated_at = now_iso()
        row = item.to_row()
        row["meta"] = json.dumps(row.get("meta") or {}, ensure_ascii=False)
        cols = ",".join(row.keys())
        ph = ",".join(["?"] * len(row))
        updates = ",".join(f"{k}=excluded.{k}" for k in row if k not in ("id", "created_at"))
        self.conn.execute(
            f"INSERT INTO items ({cols}) VALUES ({ph}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}",
            list(row.values()),
        )
        if existing is None:
            self._event(item.id, None, item.status, "created")
        return item

    def set_status(self, item: Item, to: str, note: str | None = None) -> Item:
        if not item.can_transition(to):
            raise ValueError(f"illegal transition {item.status} -> {to} for {item.id}")
        frm = item.status
        item.status = to
        item.updated_at = now_iso()
        self.conn.execute(
            "UPDATE items SET status=?, updated_at=? WHERE id=?",
            (to, item.updated_at, item.id),
        )
        self._event(item.id, frm, to, note)
        return item

    def bump_attempt(self, item: Item, error: str | None = None) -> None:
        item.attempts += 1
        item.error = error
        self.conn.execute(
            "UPDATE items SET attempts=?, error=?, updated_at=? WHERE id=?",
            (item.attempts, error, now_iso(), item.id),
        )

    def record_usage(self, component: str, calls: int = 1, tokens: int = 0) -> None:
        day = now_iso()[:10]
        self.conn.execute(
            "INSERT INTO usage(day, component, calls, tokens) VALUES(?,?,?,?) "
            "ON CONFLICT(day, component) DO UPDATE SET calls=calls+?, tokens=tokens+?",
            (day, component, calls, tokens, calls, tokens),
        )

    def usage_today(self, component: str) -> int:
        day = now_iso()[:10]
        row = self.conn.execute(
            "SELECT calls FROM usage WHERE day=? AND component=?", (day, component)
        ).fetchone()
        return int(row["calls"]) if row else 0

    def events_since(self, iso_ts: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM events WHERE ts >= ? ORDER BY id", (iso_ts,)
        ).fetchall()

    # --- internals --------------------------------------------------------
    def _event(self, item_id: str, frm: str | None, to: str | None, note: str | None) -> None:
        self.conn.execute(
            "INSERT INTO events(item_id, ts, from_status, to_status, note) VALUES(?,?,?,?,?)",
            (item_id, now_iso(), frm, to, note),
        )

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> Item:
        d = dict(row)
        d["meta"] = json.loads(d.get("meta") or "{}")
        return Item(**d)
