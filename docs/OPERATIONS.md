# Operations

## Scheduled tasks (Windows Task Scheduler)
`scripts\register-tasks.ps1` registers two tasks under `\SecondBrain\`:
- **SecondBrain Ingest** — repeats every 20 min, runs `ingest.ps1`.
- **SecondBrain Night** — daily 02:00, runs `night.ps1`.

Both run with **LogonType Interactive** (only while you are logged on), so no
password is stored and `claude -p` runs in your authenticated context. Settings:
`MultipleInstances=IgnoreNew`, `StartWhenAvailable` (catches up a missed run),
2-hour limit, battery-friendly.

```powershell
.\scripts\register-tasks.ps1
Get-ScheduledTask -TaskPath '\SecondBrain\' | Format-Table TaskName,State
Start-ScheduledTask -TaskPath '\SecondBrain\' -TaskName 'SecondBrain Ingest'
Get-ScheduledTaskInfo -TaskPath '\SecondBrain\' -TaskName 'SecondBrain Ingest' |
  Select LastRunTime,LastTaskResult   # LastTaskResult 0 = success
```

### Run while logged off (optional, manual)
Requires storing credentials (S4U) — a deliberate choice:
```powershell
# re-register the principal with -LogonType S4U (will prompt for the password)
```
Headless `claude -p` may not have an interactive auth context when logged off;
prefer interactive logon, or rely on mechanical mode (no Claude) for logged-off runs.

## `claude -p` headless
`night.ps1` invokes the scout lint (haiku) and librarian curate (opus) with
`--permission-mode acceptEdits` and scoped `--allowedTools`. It never uses
`--dangerously-skip-permissions`. If `claude` is absent or not authenticated, the
night still produces the mechanical report. Verify headless works:
```powershell
claude -p "say ok" --model haiku --permission-mode acceptEdits --allowedTools "Read"
```

## Logs & reports
- `logs\ingest.log`, `logs\night.log` — operational (not synced, not committed).
- `reports\latest.md` + `reports\history\<date>.md` — queue counts, Jev usage,
  link integrity, notes. A de-identified summary may be synced; raw logs stay local.

## Single writer
One writer per vault (`state\writer.lock`). Mobile must create NEW notes in
`raw/inbox/` and edit personal notes only — never edit `wiki/` while the librarian
runs. CLI mutations take the lock; concurrent runs get `IgnoreNew`.

## Jev usage & budget
`config.yaml → jev.daily_call_budget` caps live calls/day; exceeding it forces the
deterministic fallback. `secondbrain report` shows today's Jev call count.
