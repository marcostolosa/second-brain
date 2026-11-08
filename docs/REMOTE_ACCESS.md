# Remote access & multi-device sync

## Obsidian Sync - the ONE sync channel
Use Obsidian Sync as the single sync mechanism. Do **not** also sync the same
vault with iCloud, OneDrive, Syncthing, or Git - Git here is local versioning only.

### What to sync (Obsidian → Settings → Sync)
- **Sync:** `wiki/`, `raw/inbox/`, `raw/archive/`, `templates/`, `CLAUDE.md`,
  `README.md`, and (optionally) a de-identified `reports/` summary.
- **Do NOT sync:** `state/`, `logs/`, `backups/`, `.venv/`, `.git/`, `.env`,
  `config/config.yaml`, and `.claude/` (operational/agent config). Turn off
  "Sync all other file types" and exclude these folders explicitly.
- Keep large binaries in `raw/assets/` local to the PC unless you are on a Sync
  plan with a big per-file limit; link to them instead of syncing.

### Plans
- **Standard**: 1 GB, ≤ 5 MB/file. **Plus**: 10 GB, ≤ 200 MB/file. For large PDFs
  choose Plus, or keep heavy attachments on the PC with explanatory links (mobile
  will not have files that are not synced - do not promise otherwise).

### Write discipline
`wiki/` is owned by the librarian (one writer). On mobile, create NEW notes in
`raw/inbox/` and edit personal notes; avoid editing `wiki/` while the night job
runs. Resolve any `*.sync-conflict` per `docs/RECOVERY.md`.

## Talk to Claude from your phone - Claude Code Remote Control (preferred)
```powershell
cd C:\SecondBrain
claude remote-control --name "Second Brain"
```
Then open the Claude app (iOS/Android) or claude.ai/code and connect to this
session. Requirements: Claude Code authenticated with an eligible claude.ai
account (NOT API-key auth), the PC awake and the process running, internet.
Use restricted permissions and one writer at a time when editing `wiki/`.
Docs: https://code.claude.com/docs/en/remote-control · https://code.claude.com/docs/en/mobile

When the PC is **off**: Obsidian Sync still lets you read/edit synced notes on the
phone, but no local agents run until the PC is back.

## Tailscale (optional, private admin only)
Tailscale is already installed on this machine. Use it only for private
maintenance (RDP/SSH over the tailnet) with strong auth, approved devices, and
restrictive ACLs. **Never** expose RDP/SSH to the WAN and **never** use Tailscale
Funnel. Prefer Remote Control for talking to Claude; use Tailscale for OS-level
admin only.

Status: **MANUAL_PENDING** - enabling Remote Control and connecting phones require
your account/login and are done interactively.
