[CmdletBinding()]
param(
    [switch]$ImportOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$workspace = Split-Path -Parent $PSScriptRoot
Set-Location $workspace

function Get-OneTechTelegramWorkflowId {
    $lines = @(
        (& docker compose exec -T n8n n8n list:workflow --active=true 2>&1)
        (& docker compose exec -T n8n n8n list:workflow --active=false 2>&1)
    )
    $match = $lines |
        Where-Object { $_ -match "^([^|]+)\|OneTech AO - Telegram Mentions$" } |
        Select-Object -First 1
    if ($null -eq $match) {
        return $null
    }
    return ($match -split "\|", 2)[0].Trim()
}

Write-Host 'Starting the local Telegram automation services...'
& docker compose up -d postgres ao-worker n8n | Out-Host

$workflowId = Get-OneTechTelegramWorkflowId
if (-not $workflowId) {
    Write-Host 'Importing the OneTech Telegram workflow for the first time...'
    & docker compose exec -T n8n n8n import:workflow --input=/workflows/telegram-mentions.json | Out-Host
    $workflowId = Get-OneTechTelegramWorkflowId
}

if (-not $workflowId) {
    throw 'The OneTech Telegram workflow could not be found after import.'
}

if ($ImportOnly) {
    Write-Host "Workflow imported: $workflowId (left inactive by request)."
    exit 0
}

Write-Host "Activating workflow $workflowId..."
& docker compose exec -T n8n n8n update:workflow --id=$workflowId --active=true | Out-Host

# n8n loads schedule activation on restart.  Only n8n is recreated.
& docker compose up -d --force-recreate n8n | Out-Host

$activeLines = & docker compose exec -T n8n n8n list:workflow --active=true 2>&1
if (-not ($activeLines | Where-Object { $_ -eq "$workflowId|OneTech AO - Telegram Mentions" })) {
    throw 'The OneTech Telegram workflow is not active after the n8n restart.'
}

Write-Host 'Ready. Telegram group mentions/replies will be polled every minute.'
