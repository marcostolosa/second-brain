# Windows 11 setup

Local-native. No WSL runtime. PowerShell 7 (`pwsh`) preferred; Windows PowerShell
5.1 works for the scripts too.

## Prerequisites (verified on this machine)
- Windows 11 Pro (build 26300) · PowerShell 7.6.9
- Python 3.14 (`py -3`) · Git 2.56 · Node/npm (for Claude Code)
- Claude Code CLI 2.1.319 (`claude`) - authenticated with an eligible claude.ai account
- Obsidian Desktop (installed) - enable the CLI at **Settings → General → Command
  line interface** (Obsidian ≥ 1.12.7). The CLI needs Obsidian running; when it is
  not, SecondBrain uses its Python lint fallback automatically.

## One-time bootstrap
```powershell
cd C:\SecondBrain
.\scripts\bootstrap.ps1
```
This creates `.venv`, installs pinned dependencies (`-e .[test,extract]`), copies
`config/config.example.yaml → config/config.yaml` and `.env.example → .env`
(both git-ignored), initializes the local Git repo, and prints health.

## Everyday commands
```powershell
# health (versions, queue, link integrity)
.\scripts\health.ps1

# capture a link into the inbox
.\.venv\Scripts\secondbrain capture-url "https://x.com/user/status/123" --title "a note"

# process the inbox (fetch, extract, dedupe, index) - mechanical, offline-safe
.\.venv\Scripts\secondbrain process-inbox

# process with Scout/Librarian agents (needs claude logged in)
.\.venv\Scripts\secondbrain process-inbox --claude

# ask the vault (routes simple→Sonnet, complex→Opus via Jev)
.\.venv\Scripts\secondbrain ask "what did I save about X?"

# nightly maintenance by hand
.\scripts\night.ps1

# scheduled tasks
.\scripts\register-tasks.ps1      # every 20 min + daily 02:00
.\scripts\unregister-tasks.ps1

# backup (destination OUTSIDE the vault)
.\scripts\backup.ps1 -Destination D:\Backups\SecondBrain -Password <pass>
```

## Jev / TypeSafe token (optional - enables `live` routing)
Stays `mock` (deterministic, offline) until you set a token:
```powershell
cmdkey /generic:SecondBrain/TypeSafe /user:token /pass:<YOUR_TOKEN>
# then set JEV_MODE=live in .env  (the REST endpoint is treated as UNVALIDATED
# until a real call succeeds; mock remains the safe fallback)
```

## Notes
- Python 3.14 is recent; all dependencies (incl. trafilatura/lxml) installed with
  wheels. If a future dependency lacks a 3.14 wheel, pin an older minor in
  `pyproject.toml`.
- Nothing is read or written outside `C:\SecondBrain` except the venv, the Jev
  credential (Credential Manager), and the backup destination you choose.
