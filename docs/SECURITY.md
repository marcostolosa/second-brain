# Security model

Defense is mechanical, not just prose in CLAUDE.md.

## Path confinement
`src/secondbrain/paths.py` resolves every path and refuses anything that escapes
`C:\SecondBrain` (traversal, absolute escapes, NTFS junction/symlink targets that
leave the vault). `raw/` is write-blocked except through the controlled capture
path (`allow_raw=True`). Writable areas are allowlisted (`wiki/`, `reports/`,
`state/`, `logs/`, `templates/`). Tested in `tests/test_paths_security.py`.

## Claude Code permissions (`.claude/settings.json`)
- **deny**: read of `.env`, `state/`, `backups/`, `*.key`/`*.pem`; edit/write of
  `raw/`, `.env`, `state/`; `WebFetch`; destructive Bash (`rm`, `del`,
  `Remove-Item`, `format`), `curl`/`Invoke-WebRequest`, `reg`, `schtasks`.
- **allow**: read in-vault, edit/write `wiki/` + `reports/`, `obsidian`, the
  project scripts, read-only git.
- **ask**: writes to `.claude/`, edits to `CLAUDE.md`, `git push`.
Verify after install with `/status` inside `claude`. Never accept a broad
"always allow" rule mid-run.

## Prompt injection & exfiltration
All source content is untrusted DATA (CLAUDE.md §2). The scout/librarian are told
never to execute embedded instructions, read secrets, or fetch URLs. Mechanically,
`WebFetch` is denied and the Python fetcher has an SSRF guard. Tested in
`tests/test_injection.py`.

## SSRF / URL safety
`src/secondbrain/urls.py` blocks non-http(s) schemes, hostless URLs, internal
names (`localhost`, `*.local`, `*.internal`), literal private/loopback/link-local
IPs, and any hostname that *resolves* to a non-public address (DNS-rebinding
defense). `fetch.py` re-checks every redirect hop, caps bytes, limits redirects,
and never executes downloads. Tested in `tests/test_urls.py`.

## Secrets
The Jev token lives in Windows Credential Manager (`SecondBrain/TypeSafe`) or a
git-ignored `.env` - never in Markdown, Git, logs, or prompts. Text is redacted
(`policy.redact`) before any external call. Tested in `tests/test_policy.py`.

## Sensitive data
`config/source-policy.yaml` classifies risk. HIGH-risk content (client/engagement,
credentials, identity/health) becomes `needs_review`: not auto-ingested, not
synced, not sent to Jev/Claude. A separate sensitive vault is recommended for such
material (not created here).

## Network exposure
None. No public HTTP API, no tunnel, no `0.0.0.0` listener, no WAN port. Tailscale
(if used) is private admin only - strong auth, approved devices, restrictive ACLs,
never Funnel. Remote Control is the preferred way to talk to Claude from mobile.
