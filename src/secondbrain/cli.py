"""SecondBrain command-line interface.

Mutating commands take the single-writer vault lock. Read-only commands do not.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .answer import answer_question
from .capture import (capture_link, capture_note, import_file, import_folder,
                      capture_links_file)
from .claude_runner import claude_available
from .config import load_config
from .db import VaultDB, single_writer_lock
from .index_build import build_index
from .jev_client import JevClient
from .lint import lint_vault
from .obsidian import cli_available
from .pipeline import run_inbox
from .report import write_report
from .secrets import get_typesafe_token
from .utils import read_text


def _p(msg: str) -> None:
    print(msg, flush=True)


def cmd_health(args, cfg) -> int:
    _p(f"SecondBrain {__version__}")
    _p(f"root: {cfg.root}")
    _p(f"jev mode: {cfg.jev_mode}  (token configured: {bool(get_typesafe_token())})")
    _p(f"claude CLI: {'yes' if claude_available() else 'no'}")
    _p(f"obsidian CLI: {'yes' if cli_available(cfg) else 'no'}")
    with VaultDB(cfg) as db:
        _p(f"queue counts: {db.counts()}")
    lint = lint_vault(cfg)
    _p(f"wiki pages: {lint.pages} | unresolved: {len(lint.unresolved)} | "
       f"orphans: {len(lint.orphans)} | deadends: {len(lint.deadends)}")
    return 0


def cmd_capture_url(args, cfg) -> int:
    with single_writer_lock(cfg):
        res = capture_link(cfg, args.url, title=args.title, comment=args.comment,
                           tags=(args.tags.split(",") if args.tags else None))
    _p(f"captured -> {res.path}")
    _p(f"canonical: {res.canonical_url}")
    return 0


def cmd_capture_note(args, cfg) -> int:
    with single_writer_lock(cfg):
        res = capture_note(cfg, args.title, args.body or "",
                           tags=(args.tags.split(",") if args.tags else None))
    _p(f"note -> {res.path}")
    return 0


def cmd_import_file(args, cfg) -> int:
    with single_writer_lock(cfg):
        res = import_file(cfg, args.path)
    _p(f"imported -> {res.path}")
    return 0


def cmd_import_folder(args, cfg) -> int:
    with single_writer_lock(cfg):
        results = import_folder(cfg, args.path, pattern=args.glob, recursive=not args.flat)
    for r in results:
        _p(f"imported -> {r.path}")
    _p(f"{len(results)} file(s) imported into raw/inbox")
    return 0


def cmd_capture_links(args, cfg) -> int:
    with single_writer_lock(cfg):
        results = capture_links_file(cfg, args.path)
    for r in results:
        _p(f"captured -> {r.canonical_url}")
    _p(f"{len(results)} link(s) captured")
    return 0


def cmd_process_inbox(args, cfg) -> int:
    use_claude = args.claude and claude_available()
    if args.claude and not use_claude:
        _p("WARNING: --claude requested but claude CLI not found; running mechanical mode.")
    with single_writer_lock(cfg):
        with VaultDB(cfg) as db:
            summary = run_inbox(cfg, db, use_claude=use_claude, limit=args.limit)
            write_report(cfg, db, extra_notes=[f"ingest run: {summary.__dict__}"])
    _p(f"discovered: {summary.discovered}  processed: {summary.processed}  "
       f"done: {summary.done}  duplicates: {summary.duplicates}  "
       f"needs_review: {summary.needs_review}  failed: {summary.failed}")
    for pg in summary.pages_created:
        _p(f"  page: {pg}")
    return 0


def cmd_ask(args, cfg) -> int:
    with VaultDB(cfg) as db:
        ans = answer_question(cfg, args.question, db=db)
    _p(ans.as_markdown())
    return 0


def cmd_lint(args, cfg) -> int:
    _p(lint_vault(cfg).as_markdown())
    return 0


def cmd_index(args, cfg) -> int:
    with single_writer_lock(cfg):
        out = build_index(cfg)
    _p(f"index rebuilt -> {out}")
    return 0


def cmd_report(args, cfg) -> int:
    with VaultDB(cfg) as db:
        out = write_report(cfg, db)
    _p(f"report -> {out}")
    return 0


def cmd_route(args, cfg) -> int:
    with VaultDB(cfg) as db:
        jev = JevClient(cfg, db=db)
        if args.dedupe:
            summary_text = read_text(args.dedupe)
            index_text = read_text(cfg.path("vault.wiki_dir", "wiki") / "index.md")
            v = jev.dedupe(summary_text, index_text)
            _p(v.verdict)
        else:
            index_text = read_text(cfg.path("vault.wiki_dir", "wiki") / "index.md")
            v = jev.route_question(args.question or "", index_text)
            _p(v.model)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="secondbrain", description="Personal LLM Wiki / Second Brain")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health").set_defaults(func=cmd_health)

    c = sub.add_parser("capture-url"); c.add_argument("url")
    c.add_argument("--title"); c.add_argument("--comment"); c.add_argument("--tags")
    c.set_defaults(func=cmd_capture_url)

    c = sub.add_parser("capture-note"); c.add_argument("title")
    c.add_argument("--body"); c.add_argument("--tags")
    c.set_defaults(func=cmd_capture_note)

    c = sub.add_parser("import-file"); c.add_argument("path")
    c.set_defaults(func=cmd_import_file)

    c = sub.add_parser("import-folder"); c.add_argument("path")
    c.add_argument("--glob", default="*"); c.add_argument("--flat", action="store_true")
    c.set_defaults(func=cmd_import_folder)

    c = sub.add_parser("capture-links"); c.add_argument("path")
    c.set_defaults(func=cmd_capture_links)

    c = sub.add_parser("process-inbox")
    c.add_argument("--claude", action="store_true")
    c.add_argument("--limit", type=int, default=None)
    c.set_defaults(func=cmd_process_inbox)

    c = sub.add_parser("ask"); c.add_argument("question"); c.set_defaults(func=cmd_ask)
    sub.add_parser("lint").set_defaults(func=cmd_lint)
    sub.add_parser("index").set_defaults(func=cmd_index)
    sub.add_parser("report").set_defaults(func=cmd_report)

    c = sub.add_parser("route")
    c.add_argument("question", nargs="?")
    c.add_argument("--dedupe", help="path to a summary file to check for duplication")
    c.set_defaults(func=cmd_route)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    cfg = load_config()
    return args.func(args, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
