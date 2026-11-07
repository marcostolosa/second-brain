<#
.SYNOPSIS
  Nightly maintenance: mechanical checks, incremental scout/librarian passes (if
  claude is available & logged on), report, Git snapshot, optional backup.
.DESCRIPTION
  Proposes fixes; never applies destructive corrections or permission changes.
  Never uses --dangerously-skip-permissions. Each stage is isolated so one failure
  does not abort the rest.
#>
[CmdletBinding()]
param([string]$BackupDestination)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$py   = Join-Path $Root ".venv\Scripts\python.exe"
$day  = (Get-Date).ToString("yyyy-MM-dd")
$log  = Join-Path $Root "logs\night.log"
New-Item -ItemType Directory -Force (Join-Path $Root "logs") | Out-Null
function Log($m) { Add-Content -Path $log -Value "[$((Get-Date).ToString('s'))] $m" }

Log "=== night start $day ==="

# 0. Git checkpoint BEFORE changes (local recovery point)
try { git add -A 2>$null; git commit -m "night: checkpoint before $day" --quiet 2>$null; Log "git pre-checkpoint ok" }
catch { Log "git pre-checkpoint skipped: $($_.Exception.Message)" }

# 1. Mechanical checks (Obsidian CLI if available, else Python lint)
$mech = Join-Path $Root "reports\$day-mechanical.txt"
$obsidian = Get-Command obsidian -ErrorAction SilentlyContinue
if ($obsidian) {
  try {
    & obsidian orphans    > $mech 2>&1
    & obsidian unresolved >> $mech 2>&1
    & obsidian deadends   >> $mech 2>&1
    Log "obsidian mechanical checks ok"
  } catch { Log "obsidian checks failed: $($_.Exception.Message)" }
} else {
  & $py -m secondbrain.cli lint > $mech 2>&1
  Log "python lint fallback ok (obsidian CLI not on PATH)"
}

# 2. Advance any pending inbox items mechanically (always safe)
& $py -m secondbrain.cli process-inbox 2>&1 | Tee-Object -Variable ingestOut | Out-Null
Log "process-inbox: $ingestOut"

# 3. Scout lint + Librarian curate via claude -p (only if claude present)
$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($claude) {
  try {
    & claude -p "Run the LINT rules in CLAUDE.md on pages changed since the last lint in wiki/log.md. Write reports/$day-lint.md and propose fixes. Apply nothing." `
      --model haiku --permission-mode acceptEdits --allowedTools "Read,Grep,Glob,Write" 2>&1 | Out-Null
    Log "scout lint (claude) ok"
    & claude -p "Use the curate skill on everything logged today. Max 15 page edits per source. Apply nothing destructive." `
      --model opus --permission-mode acceptEdits 2>&1 | Out-Null
    Log "librarian curate (claude) ok"
  } catch { Log "claude passes failed: $($_.Exception.Message)" }
} else {
  Log "claude CLI not found; skipped LLM passes (mechanical report still produced)"
}

# 4. Report (always)
& $py -m secondbrain.cli report 2>&1 | Out-Null
Log "report written -> reports/latest.md"

# 5. Git snapshot AFTER
try { git add -A 2>$null; git commit -m "night: $day snapshot" --quiet 2>$null; Log "git post-snapshot ok" }
catch { Log "git post-snapshot skipped: $($_.Exception.Message)" }

# 6. Optional backup
if ($BackupDestination) {
  try { & (Join-Path $PSScriptRoot "backup.ps1") -Destination $BackupDestination; Log "backup ok -> $BackupDestination" }
  catch { Log "backup failed: $($_.Exception.Message)" }
}

Log "=== night end $day ==="
