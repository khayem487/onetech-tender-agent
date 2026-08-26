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
$startupTaskName = 'OneTech Tender Agent Stack'
$userId = "$env:USERDOMAIN\$env:USERNAME"

$startupArguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$startupScript`" -StartGateway -StartOllama"
$startupAction = New-ScheduledTaskAction -Execute 'PowerShell.exe' -Argument $startupArguments -WorkingDirectory $projectRoot
$startupTrigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited

$startupSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $startupTaskName -Action $startupAction -Trigger $startupTrigger `
    -Settings $startupSettings -Principal $principal -Force | Out-Null

Write-Host "Tache Windows installee : $startupTaskName" -ForegroundColor Green
Write-Host 'La tache est autorisee sur batterie.' -ForegroundColor Green

if ($RunNow) {
    Start-ScheduledTask -TaskName $startupTaskName
    Write-Host 'La tache de demarrage a ete lancee pour validation.' -ForegroundColor Green
}
