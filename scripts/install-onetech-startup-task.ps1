[CmdletBinding()]
param(
    [switch]$ConfirmInstall,
    [switch]$RunNow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $ConfirmInstall) {
    throw 'Installation bloquee. Relance avec -ConfirmInstall pour creer les taches Windows.'
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$startupScript = Join-Path $projectRoot 'scripts\start-onetech-stack.ps1'
$watchdogScript = Join-Path $projectRoot 'scripts\watchdog-onetech-stack.ps1'
$startupTaskName = 'OneTech Tender Agent Stack'
$watchdogTaskName = 'OneTech Tender Agent Watchdog'
$userId = "$env:USERDOMAIN\$env:USERNAME"

$startupArguments = "-NoProfile -ExecutionPolicy Bypass -File `"$startupScript`" -StartGateway -StartOllama"
$watchdogArguments = "-NoProfile -ExecutionPolicy Bypass -File `"$watchdogScript`""
$startupAction = New-ScheduledTaskAction -Execute 'PowerShell.exe' -Argument $startupArguments -WorkingDirectory $projectRoot
$watchdogAction = New-ScheduledTaskAction -Execute 'PowerShell.exe' -Argument $watchdogArguments -WorkingDirectory $projectRoot
$startupTrigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$watchdogTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited

$startupSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -MultipleInstances IgnoreNew
$watchdogSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $startupTaskName -Action $startupAction -Trigger $startupTrigger `
    -Settings $startupSettings -Principal $principal -Force | Out-Null
Register-ScheduledTask -TaskName $watchdogTaskName -Action $watchdogAction -Trigger $watchdogTrigger `
    -Settings $watchdogSettings -Principal $principal -Force | Out-Null

Write-Host "Tache Windows installee : $startupTaskName" -ForegroundColor Green
Write-Host "Tache Windows installee : $watchdogTaskName (toutes les 5 minutes)" -ForegroundColor Green
Write-Host 'Les deux taches sont autorisees sur batterie.' -ForegroundColor Green

if ($RunNow) {
    Start-ScheduledTask -TaskName $startupTaskName
    Write-Host 'La tache de demarrage a ete lancee pour validation.' -ForegroundColor Green
}
