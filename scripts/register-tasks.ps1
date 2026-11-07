<#
.SYNOPSIS
  Register two Windows Task Scheduler tasks under the current user:
    - "SecondBrain Ingest" — every 20 min while logged on
    - "SecondBrain Night"  — daily at 02:00
.NOTES
  Runs ONLY when the user is logged on (LogonType Interactive) so no password is
  stored and claude -p runs in the user's authenticated context. If you need it to
  run while logged off, that requires storing credentials (S4U) — a manual choice,
  documented in docs\OPERATIONS.md. Not elevated; no WAN exposure.
#>
[CmdletBinding()]
param([int]$IngestMinutes = 20, [string]$NightAt = "02:00")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$TaskPath = "\SecondBrain\"

# Prefer PowerShell 7 (pwsh) if present, else Windows PowerShell.
$shell = (Get-Command pwsh -ErrorAction SilentlyContinue)?.Source
if (-not $shell) { $shell = (Get-Command powershell).Source }

function Register-One($Name, $ScriptFile, $Trigger) {
  $action = New-ScheduledTaskAction -Execute $shell `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $Root "scripts\$ScriptFile")`"" `
    -WorkingDirectory $Root
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
  $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited
  if (Get-ScheduledTask -TaskName $Name -TaskPath $TaskPath -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $Name -TaskPath $TaskPath -Confirm:$false
  }
  Register-ScheduledTask -TaskName $Name -TaskPath $TaskPath -Action $action `
    -Trigger $Trigger -Settings $settings -Principal $principal | Out-Null
  Write-Host "registered: $TaskPath$Name" -ForegroundColor Green
}

# Ingest: repeat every N minutes, indefinitely, starting now.
$ingestTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
  -RepetitionInterval (New-TimeSpan -Minutes $IngestMinutes) `
  -RepetitionDuration (New-TimeSpan -Days 3650)
Register-One "SecondBrain Ingest" "ingest.ps1" $ingestTrigger

# Night: daily at 02:00
$nightTrigger = New-ScheduledTaskTrigger -Daily -At $NightAt
Register-One "SecondBrain Night" "night.ps1" $nightTrigger

Write-Host ""
Write-Host "Verify: Get-ScheduledTask -TaskPath '\SecondBrain\' | Format-Table TaskName,State"
Write-Host "Run now: Start-ScheduledTask -TaskPath '\SecondBrain\' -TaskName 'SecondBrain Ingest'"
