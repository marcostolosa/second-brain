# Recovery runbook

Three independent layers: **Git** (local history), **Obsidian Sync** (device
replication - NOT a backup), **backups** (off-vault archives). Sync is not backup;
Git is not a backup for large assets.

## Rebuild state from the Markdown
The SQLite queue is reconstructible - the Markdown files are the source of truth.
If `state/` is lost or corrupt:
```powershell
Remove-Item C:\SecondBrain\state\secondbrain.sqlite3* -Force
.\.venv\Scripts\secondbrain process-inbox   # re-registers from raw/inbox + archive
.\.venv\Scripts\secondbrain index            # rebuild index.md from frontmatter
```

## Git vs your data
Git versions the **project/framework** only - your captures and generated wiki
pages are git-ignored and never committed (this repo is public). So Git restores
code/config, **not** your knowledge. Recover personal content from **Obsidian Sync**
(other devices) or **backups** (below).
```powershell
cd C:\SecondBrain
git log --oneline
git restore --source <commit> -- src scripts docs   # recover framework files
```

## Restore from backup
```powershell
# zip
Expand-Archive D:\Backups\SecondBrain\secondbrain-<stamp>.zip C:\Temp\sb-restore
# 7z (encrypted)
& "$env:ProgramFiles\7-Zip\7z.exe" x D:\Backups\SecondBrain\secondbrain-<stamp>.7z -oC:\Temp\sb-restore
cd C:\Temp\sb-restore
# validate before trusting it:
C:\SecondBrain\.venv\Scripts\python.exe -m secondbrain.cli lint
```
Test a restore periodically (quarterly). A backup you have never restored is a
hypothesis, not a backup.

## Crash / power loss mid-ingest
SQLite runs in WAL mode; interrupted runs leave items in an intermediate status
(`fetching`, `extracted`, …). The next `process-inbox` resumes them idempotently -
no duplicate pages, no corruption (`tests/test_pipeline_e2e.py::test_resume_after_interruption`).

## Obsidian Sync conflicts
If a page was edited on two devices, Obsidian keeps a `*.sync-conflict` copy. Treat
`wiki/` as librarian-owned: resolve by keeping the librarian's version and folding
mobile edits into a `raw/inbox/` note to be re-ingested.
