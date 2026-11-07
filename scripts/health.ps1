<#
.SYNOPSIS
  Print SecondBrain health (versions, queue, link integrity).
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $Root ".venv\Scripts\python.exe"
& $py -m secondbrain.cli health
