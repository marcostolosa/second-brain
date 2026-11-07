<div align="center">

<img src="assets/logo.svg" alt="SecondBrain" width="640">

# SecondBrain

**A local-first personal LLM Wiki for Windows 11 — Claude Code + Obsidian + Jev.**

[![CI](https://github.com/marcostolosa/second-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/marcostolosa/second-brain/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-36f9c7.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3aa0ff.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%2011-0a0e14.svg)](docs/WINDOWS_SETUP.md)
[![Tests](https://img.shields.io/badge/tests-44%20passing-36f9c7.svg)](tests/)
[![Built with Claude Code](https://img.shields.io/badge/built%20with-Claude%20Code-3aa0ff.svg)](https://claude.com/claude-code)

</div>

---

Turn a stream of links, PDFs and notes into a linked, cited knowledge base you
actually trust. Markdown files are the source of truth; a small SQLite queue holds
only reconstructible state. No vector DB, no cloud, no public endpoint — it runs on
your machine and syncs to your devices through Obsidian Sync.

> It reproduces the architecture of Mr. Buzzoni's first LLM-Wiki article
> (scout / librarian / answerer, Jev routing, ingest·curate·ask skills, a nightly
> maintenance shift) and adapts it to Windows with multi-device capture.

## Why
- **Local-first & private** — your knowledge never leaves your machine by default.
- **Cited, not hallucinated** — every claim links to a source page or primary URL.
- **Safe with hostile input** — sources are treated as inert data; a dedicated
  layer strips invisible characters, detects prompt injection, and fences content.
- **Cheap routing** — Jev (a tiny yes/no model) picks Sonnet for lookups and Opus
  for synthesis; a deterministic mock keeps it working offline.

## Architecture
```
capture ──▶ raw/inbox ──▶ fetch ─▶ extract ─▶ policy ─▶ dedupe(Jev) ─▶ scout ─▶ curate(librarian) ─▶ index ──▶ wiki/ ──▶ Obsidian Sync ──▶ phones
```
| Agent | Model | Role |
|-------|-------|------|
| **scout** | Haiku | neutral summaries into `wiki/sources/`, proposes links · no Bash/Edit, cannot touch `raw/` |
| **librarian** | Opus | writes `entities/`·`concepts/`·`questions/`·`index.md`, resolves conflicts · ≤15 edits/source |
| **answerer** | Sonnet / Opus | answers; the model is chosen by **Jev** |
| **Jev** | TypeSafe REST | dedupe (Noul) + routing (Choice); deterministic **mock** by default |

## Quickstart (Windows 11, PowerShell 7)
```powershell
git clone https://github.com/marcostolosa/second-brain.git C:\SecondBrain
cd C:\SecondBrain
.\scripts\bootstrap.ps1
.\.venv\Scripts\secondbrain capture-url "https://x.com/user/status/123"
.\.venv\Scripts\secondbrain process-inbox
.\.venv\Scripts\secondbrain ask "what did I save about X?"
```
Bulk add: `secondbrain import-folder <dir>` · `secondbrain capture-links links.txt`.

## Features
- Ingest **X/Twitter** (FxTwitter API, X Articles flagged as partial), **articles**
  (trafilatura + fallback), **PDFs** (text layer; OCR flagged), **Markdown/TXT**,
  **GitHub**, and quick notes. Images/audio/video enter as `needs_extraction`.
- Durable pipeline: SQLite WAL, single-writer lock, idempotent, crash-safe resume.
- **Security**: path confinement, SSRF guard, scoped Claude permissions, a
  sensitive-data policy (financials/credentials never auto-sync or leave the box).
- **Nightly**: mechanical lint (Obsidian CLI or pure-Python fallback), scout lint,
  librarian curate, report, Git checkpoint, backup.
- **All generated content in pt-BR** by default (configurable).

## Docs
[Windows setup](docs/WINDOWS_SETUP.md) ·
[Daily use & best practices](docs/DIA_A_DIA.md) ·
[Security](docs/SECURITY.md) · [Operations](docs/OPERATIONS.md) ·
[Recovery](docs/RECOVERY.md) · [iOS](docs/IOS_CAPTURE.md) ·
[Android](docs/ANDROID_CAPTURE.md) · [Remote access](docs/REMOTE_ACCESS.md)

## Tests
```powershell
.\.venv\Scripts\python -m pytest -q   # 44 passing
```

## License
MIT © 2026 Marcos Tolosa — see [LICENSE](LICENSE).
