<div align="center">

<img src="assets/logo.svg" alt="SecondBrain" width="640">

# SecondBrain

**A local-first personal LLM Wiki for Windows 11: Claude Code + Obsidian + Jev.**

[![CI](https://github.com/marcostolosa/second-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/marcostolosa/second-brain/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-36f9c7.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3aa0ff.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%2011-0a0e14.svg)](docs/WINDOWS_SETUP.md)
[![Tests](https://img.shields.io/badge/tests-44%20passing-36f9c7.svg)](tests/)
[![Built with Claude Code](https://img.shields.io/badge/built%20with-Claude%20Code-3aa0ff.svg)](https://claude.com/claude-code)

</div>

Turn a stream of links, PDFs and notes into a linked, cited knowledge base you
actually trust. Markdown files are the source of truth; a small SQLite queue holds
only reconstructible state. No vector DB, no cloud, no public endpoint: it runs on
your machine and syncs to your devices through Obsidian Sync.

> Reproduces the architecture of Mr. Buzzoni's first LLM-Wiki article (scout,
> librarian, answerer; Jev routing; ingest/curate/ask skills; a nightly
> maintenance shift) adapted to Windows with multi-device capture.

## Why
- **Local-first & private**: your knowledge never leaves your machine by default.
- **Cited, not hallucinated**: every claim links to a source page or primary URL.
- **Safe with hostile input**: sources are treated as inert data; a dedicated layer
  strips invisible characters, detects prompt injection, and fences the content.
- **Cheap routing**: Jev (a tiny yes/no model) picks Sonnet for lookups and Opus for
  synthesis; a deterministic mock keeps it working offline.

## Architecture
```
capture -> raw/inbox -> fetch -> extract -> policy -> dedupe(Jev) -> scout -> curate(librarian) -> index -> wiki/ -> Obsidian Sync -> phones
```
| Agent | Model | Role |
|-------|-------|------|
| **scout** | Haiku | neutral summaries into `wiki/sources/`; proposes links; no Bash/Edit; cannot touch `raw/` |
| **librarian** | Opus | writes `entities/`, `concepts/`, `questions/`, `index.md`; resolves conflicts; max 15 edits/source |
| **answerer** | Sonnet / Opus | answers; the model is chosen by **Jev** |
| **Jev** | TypeSafe REST | dedupe (Noul) + routing (Choice); deterministic **mock** by default |

## Prerequisites
- Windows 11 (Pro recommended), PowerShell 7 (`pwsh`); Windows PowerShell 5.1 also runs the scripts
- Python 3.11+ (`py -3`), Git
- Node.js + npm (for Claude Code), and the Claude Code CLI: `npm i -g @anthropic-ai/claude-code`
- Obsidian Desktop (to read/navigate the vault and sync to phones)

## Install & run
```powershell
git clone https://github.com/marcostolosa/second-brain.git C:\SecondBrain
cd C:\SecondBrain
.\scripts\bootstrap.ps1          # creates .venv, installs deps, config.yaml, .env, health check
```
Everyday use:
```powershell
.\.venv\Scripts\secondbrain capture-url "https://x.com/user/status/123" --tags web
.\.venv\Scripts\secondbrain process-inbox          # fetch, extract, dedupe, index
.\.venv\Scripts\secondbrain ask "what did I save about X?"
.\.venv\Scripts\secondbrain report                 # writes reports/latest.md
```
Bulk add:
```powershell
.\.venv\Scripts\secondbrain import-folder "C:\docs" --glob *.pdf
.\.venv\Scripts\secondbrain capture-links links.txt   # one URL per line: url | title | tags
```

### Open it in Obsidian
Open `C:\SecondBrain` as a vault, then open `home.md` (the cockpit) and the Graph
view. See [docs/REMOTE_ACCESS.md](docs/REMOTE_ACCESS.md) to sync to iPhone/Android.

### Optional: real LLM agents (`--claude`)
The mechanical pipeline works with no login. To let the scout/librarian write the
summaries, authenticate Claude Code (`claude auth login`), trust the folder once,
then run `secondbrain process-inbox --claude` or the nightly `scripts\night.ps1`.

### Optional: Jev live routing
Jev runs in a deterministic **mock** by default. For the real router, store a
TypeSafe token and switch mode (otherwise it stays on the safe mock):
```powershell
cmdkey /generic:SecondBrain/TypeSafe /user:token /pass:YOUR_TOKEN
# then set JEV_MODE=live in .env
```

### Optional: automation & backup
```powershell
.\scripts\register-tasks.ps1     # ingest every ~20 min + nightly maintenance at 02:00
.\scripts\backup.ps1 -Destination D:\Backups\SecondBrain -Password YOUR_PASS
```

## Features
- Ingests **X/Twitter** (FxTwitter API; X Articles flagged partial), **articles**
  (trafilatura with a built-in fallback), **PDFs** (text layer; OCR flagged),
  **Markdown/TXT**, **GitHub**, and quick notes. Images/audio/video enter as
  `needs_extraction`.
- Durable pipeline: SQLite WAL, single-writer lock, idempotent, crash-safe resume.
- **Security**: path confinement, SSRF guard, scoped Claude permissions, and a
  sensitive-data policy (financials/credentials never auto-sync or leave the box).
- **Nightly**: mechanical lint (Obsidian CLI, or pure-Python fallback), scout lint,
  librarian curate, report, Git checkpoint, backup.
- **All generated content in pt-BR** by default (configurable).

## Docs
- [Windows setup](docs/WINDOWS_SETUP.md)
- [Daily use & best practices](docs/DIA_A_DIA.md)
- [Security](docs/SECURITY.md)
- [Operations](docs/OPERATIONS.md)
- [Recovery](docs/RECOVERY.md)
- [iOS capture](docs/IOS_CAPTURE.md) · [Android capture](docs/ANDROID_CAPTURE.md) · [Remote access](docs/REMOTE_ACCESS.md)

## Privacy
This repo is the **project** only. Your captures and generated knowledge (`raw/`,
`wiki/sources`, `entities`, `concepts`, `index.md`, `log.md`, `overview.md`) are
git-ignored and never published. Recover your data from Obsidian Sync or backups;
Git versions the framework only.

## Tests
```powershell
.\.venv\Scripts\python -m pytest -q   # 44 passing
```

## License
MIT, (c) 2026 Marcos Tolosa. See [LICENSE](LICENSE).
