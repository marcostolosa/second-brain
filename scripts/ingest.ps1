<#
.SYNOPSIS
  Import & process new inbox captures. Run by Task Scheduler every ~20 min.
.DESCRIPTION
  Mechanical by default (deterministic, offline-safe). Pass -Claude to enrich with
  the scout/librarian agents via claude -p (only if logged on and claude is auth'd).
  Processing is a no-op when the inbox has no new eligible items.
#>
[CmdletBinding()]
param([switch]$Claude)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$py  = Join-Path $Root ".venv\Scripts\python.exe"
$log = Join-Path $Root "logs\ingest.log"
New-Item -ItemType Directory -Force (Join-Path $Root "logs") | Out-Null

$ts = (Get-Date).ToString("s")
try {
  $args = @("-m","secondbrain.cli","process-inbox")
  if ($Claude) { $args += "--claude" }
  $out = & $py @args 2>&1
  Add-Content -Path $log -Value "[$ts] OK`n$out`n"
  Write-Output $out
  exit 0
} catch {
  Add-Content -Path $log -Value "[$ts] ERROR $($_.Exception.Message)`n"
  Write-Error $_
  exit 1
}
