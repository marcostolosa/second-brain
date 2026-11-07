<#
.SYNOPSIS
  Remove the SecondBrain scheduled tasks.
#>
$ErrorActionPreference = "Stop"
$TaskPath = "\SecondBrain\"
foreach ($name in @("SecondBrain Ingest", "SecondBrain Night")) {
  if (Get-ScheduledTask -TaskName $name -TaskPath $TaskPath -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $name -TaskPath $TaskPath -Confirm:$false
    Write-Host "removed: $TaskPath$name"
  } else {
    Write-Host "not present: $TaskPath$name"
  }
}
