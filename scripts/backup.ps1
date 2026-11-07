<#
.SYNOPSIS
  Full compressed backup of the vault to a destination OUTSIDE the vault & sync.
.DESCRIPTION
  Sync is not backup and Git is not backup for large assets — this is. Excludes
  secrets (.env, *.key), the venv, logs, prior backups, and .git. Includes wiki,
  raw, state (for recovery), config, templates, .claude, scripts, src, docs.
  Encryption: pass -Password AND have 7-Zip installed; otherwise the script
  refuses to pretend and creates an UNENCRYPTED zip with a clear warning.
.PARAMETER Destination
  Folder to write the archive into. Must be outside C:\SecondBrain.
.PARAMETER Password
  Optional. Enables AES-256 encryption (requires 7-Zip on PATH / default install).
.PARAMETER Keep
  Retention: keep this many newest archives (default 14).
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)] [string]$Destination,
  [string]$Password,
  [int]$Keep = 14
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

# Refuse to back up into the vault itself (sync/backup separation).
$destFull = [System.IO.Path]::GetFullPath($Destination)
if ($destFull.StartsWith([System.IO.Path]::GetFullPath($Root), [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Destination must be OUTSIDE the vault ($Root). Sync is not backup."
}
New-Item -ItemType Directory -Force $destFull | Out-Null

$stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
$include = @("wiki","raw","state","config","templates",".claude","scripts","src","docs",
             "CLAUDE.md","README.md","pyproject.toml")
$exclude = @(".env","*.key","*.pem")

# Stage a clean copy (excluding secrets) via robocopy mirror into a temp dir.
$stage = Join-Path $env:TEMP "sb-backup-$stamp"
New-Item -ItemType Directory -Force $stage | Out-Null
foreach ($item in $include) {
  $src = Join-Path $Root $item
  if (-not (Test-Path $src)) { continue }
  if ((Get-Item $src).PSIsContainer) {
    robocopy $src (Join-Path $stage $item) /E /XF $exclude /NFL /NDL /NJH /NJS /NP | Out-Null
  } else {
    Copy-Item $src (Join-Path $stage $item)
  }
}
# Hard guarantee: no secrets slipped in.
Get-ChildItem $stage -Recurse -Force -Include ".env","*.key","*.pem" -ErrorAction SilentlyContinue |
  Remove-Item -Force -ErrorAction SilentlyContinue

$sevenZip = (Get-Command 7z -ErrorAction SilentlyContinue)?.Source
if (-not $sevenZip -and (Test-Path "$env:ProgramFiles\7-Zip\7z.exe")) { $sevenZip = "$env:ProgramFiles\7-Zip\7z.exe" }

if ($Password) {
  if (-not $sevenZip) {
    throw "Encryption requested but 7-Zip not found. Install 7-Zip, or re-run without -Password for an UNENCRYPTED zip."
  }
  $archive = Join-Path $destFull "secondbrain-$stamp.7z"
  & $sevenZip a -t7z "-p$Password" -mhe=on $archive (Join-Path $stage "*") | Out-Null
  Write-Host "encrypted backup -> $archive" -ForegroundColor Green
} else {
  $archive = Join-Path $destFull "secondbrain-$stamp.zip"
  Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $archive -Force
  Write-Warning "UNENCRYPTED backup -> $archive  (pass -Password with 7-Zip installed to encrypt)"
}

Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue

# Retention: keep newest $Keep archives.
Get-ChildItem $destFull -File -Include "secondbrain-*.zip","secondbrain-*.7z" |
  Sort-Object LastWriteTime -Descending | Select-Object -Skip $Keep |
  ForEach-Object { Remove-Item $_.FullName -Force; Write-Host "pruned old backup: $($_.Name)" }

Write-Host ""
Write-Host "Restore test (do this periodically):" -ForegroundColor Cyan
Write-Host "  Expand-Archive <archive>.zip -DestinationPath C:\Temp\sb-restore   # or 7z x for .7z"
Write-Host "  then run:  .\.venv\Scripts\python.exe -m secondbrain.cli health   # from the restore"
