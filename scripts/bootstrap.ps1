<#
.SYNOPSIS
  Idempotent local setup for SecondBrain (venv, deps, config, git).
.NOTES
  Does not touch anything outside C:\SecondBrain. Re-runnable.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== SecondBrain bootstrap ==" -ForegroundColor Cyan
Write-Host "root: $Root"

# 1. venv
$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Host "creating venv..."
  py -3 -m venv (Join-Path $Root ".venv")
}
& $py --version

# 2. deps (editable install + test extra)
Write-Host "installing dependencies..."
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -e ".[test,extract]" --quiet
Write-Host "deps installed."

# 3. config + env (copied from examples if missing; never overwrite)
$cfg = Join-Path $Root "config\config.yaml"
if (-not (Test-Path $cfg)) { Copy-Item (Join-Path $Root "config\config.example.yaml") $cfg; Write-Host "config.yaml created" }
$envf = Join-Path $Root ".env"
if (-not (Test-Path $envf)) { Copy-Item (Join-Path $Root ".env.example") $envf; Write-Host ".env created (JEV_MODE=mock)" }

# 4. git
if (-not (Test-Path (Join-Path $Root ".git"))) {
  git init -b main | Out-Null
  git config user.name  "Marcos Tolosa"
  git config user.email "marcos.tolosa@owasp.org"
}

# 5. sanity
& $py -m secondbrain.cli health

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  - Set the Jev token (optional, for live mode):"
Write-Host "      cmdkey /generic:SecondBrain/TypeSafe /user:token /pass:<YOUR_TOKEN>"
Write-Host "  - Register scheduled tasks: scripts\register-tasks.ps1"
Write-Host "  - Open C:\SecondBrain as an Obsidian vault and connect Obsidian Sync."
