# Register the watcher as a Windows Scheduled Task that runs at user logon.
# No admin elevation required — /RL LIMITED.
#
# Usage:
#   .\scripts\install_task.ps1

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$entry = Join-Path $repoRoot "scripts\run_watcher.pyw"

if (-not (Test-Path $entry)) {
    throw "Entry script not found: $entry"
}

$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    throw "pythonw.exe not found in PATH. Install Python 3.11+ and ensure 'Add to PATH' was checked."
}

$taskName = "PekinTV Foodphoto Bot"

schtasks /Delete /TN $taskName /F 2>$null | Out-Null

$tr = "`"$pythonw`" `"$entry`""
schtasks /Create /SC ONLOGON /TN $taskName /TR $tr /RL LIMITED /F

Write-Host "Registered scheduled task: $taskName"
Write-Host "Command: $tr"
Write-Host ""
Write-Host "Log off and log back in — the bot will start automatically."
Write-Host "Logs: `$env:LOG_DIR\bot.log (see .env)"
