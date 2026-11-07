# Acceptance report — SecondBrain

Date: 2026-11-07 · Host: Windows 11 Pro 26300 · Python 3.14.4 · PowerShell 7.6.9 ·
Claude Code 2.1.319 · pytest: **39 passed**.

Legend: **PASS** verified here · **MANUAL_PENDING** needs your login/device/token.

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | X post + manual link: ID extraction, URL normalization, metadata; no invented text on failure | **PASS** | `tests/test_urls.py`, `tests/test_twitter_mock.py`; live demo produced `wiki/sources/how-to-turn-claude-opus-5-5-...md` with real author/date, body flagged `partial` (X Article) — not fabricated |
| 2 | Duplicate URL with tracking params → idempotent, no duplicate source | **PASS** | `tests/test_pipeline_e2e.py::test_duplicate_url_with_tracking_is_deduped` (2 captures → 1 page, 1 duplicate) |
| 3 | Markdown + PDF (text layer): hash, extraction, page refs | **PASS** | `tests/test_extract.py` (markdown hash == sha256; PDF text + page count; OCR path raises `PdfNeedsOCR`) |
| 4 | Deleted post / HTTP 429 / Jev offline → correct status, retry/backoff, fallback | **PASS** | `tests/test_twitter_mock.py` (404→deleted, 429→rate_limited), `tests/test_jev.py::test_live_network_failure_falls_back_to_opus` |
| 5 | Malicious instruction in a source → treated as data, not executed | **PASS** | `tests/test_injection.py` (injection stored verbatim as data; `.env` traversal blocked by `paths`) |
| 6 | Scout cannot alter raw/entities; Librarian ≤15 edits/source | **PASS** | `tests/test_paths_security.py` (raw write blocked; scout tools = Read,Grep,Glob,Write only); budget = `ingest.max_edits_per_source: 15` enforced in curate skill/CLAUDE.md |
| 7 | Two contradictory sources → documented conflict with citations | **PARTIAL / PASS (mechanism)** | `tests/test_lint.py::test_conflict_callout_is_reported` detects `> [!conflict]`; auto-authoring the callout is the Librarian's job (needs `--claude`) |
| 8 | Run ingest twice → no spurious changes | **PASS** | `tests/test_pipeline_e2e.py::test_end_to_end_tweet_ingest` (2nd run: discovered 0, 1 page); live re-run confirmed |
| 9 | Lint lists unresolved/orphans/deadends without Obsidian open | **PASS** | `tests/test_lint.py`; `secondbrain lint` runs pure-Python |
| 10 | Interrupt/restart mid-step → safe resume, no corruption | **PASS** | `tests/test_pipeline_e2e.py::test_resume_after_interruption` (WAL + status resume) |
| 11 | iPhone & Android send, manual checklist | **MANUAL_PENDING** | `docs/IOS_CAPTURE.md`, `docs/ANDROID_CAPTURE.md` — devices not on this PC |
| 12 | No keys/operational folders in Git or Sync; backups restorable | **PASS** | `git check-ignore` confirms `.env`, `.venv`, `config/config.yaml`, `state/`, `logs/`, `backups/` ignored; sync exclusions in `docs/REMOTE_ACCESS.md`; restore test in `docs/RECOVERY.md` + `backup.ps1` |
| 13 | Simple→Sonnet, complex→Opus; Jev Choice/Noul with confidence + fallback | **PASS** | `tests/test_jev.py`; live: `ask "...guide about"` → lookup 0.91 → **sonnet**; `ask "compare...synthesize"` → **opus** |
| 14 | Task Scheduler: exit code + log; else scripts + manual | **PASS (script) / MANUAL_PENDING (register)** | `scripts/ingest.ps1` ran exit 0, logged to `logs/ingest.log`; register with `scripts/register-tasks.ps1` (persistent system change — run when ready) |
| 15 | Produce this acceptance report | **PASS** | this file + `reports/latest.md` |

## Security measures in place
- Path confinement + allowlist + traversal/junction guard (`paths.py`), raw write-blocked.
- `.claude/settings.json`: deny `.env`/`state`/`raw`/`WebFetch`/destructive Bash; verify with `/status`.
- SSRF guard on all fetches (private/loopback/link-local + DNS-rebinding), byte/redirect caps.
- Secrets in Windows Credential Manager / git-ignored `.env`; redaction before external calls.
- Sensitive-data policy (`source-policy.yaml`): HIGH-risk → `needs_review`, never auto-synced/sent.
- No public listener/tunnel. Jev daily call budget guard.

## To enable the MANUAL_PENDING items
1. **Jev live**: `cmdkey /generic:SecondBrain/TypeSafe /user:token /pass:<TOKEN>`; set `JEV_MODE=live`; confirm `https://api.typesafe.ai/v1/systemone` responds (treated as unvalidated until a real 200).
2. **Claude agents**: ensure `claude` is logged in, then `process-inbox --claude` / `night.ps1`.
3. **Scheduled tasks**: `./scripts/register-tasks.ps1` (every 20 min + 02:00).
4. **Obsidian Sync + phones**: connect the vault on each device; follow `docs/REMOTE_ACCESS.md` and the capture checklists.
5. **Remote Control**: `claude remote-control --name "Second Brain"` from `C:\SecondBrain`.
