[CmdletBinding()]
param(
    [switch]$ImportOnly
)

$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
Set-Location $workspace

function Get-OneTechWorkflowId {
    $lines = @(
        (& docker compose exec -T n8n n8n list:workflow --active=true 2>&1)
        (& docker compose exec -T n8n n8n list:workflow --active=false 2>&1)
    )
    $match = $lines | Where-Object { $_ -match "^([^|]+)\|OneTech AO - Daily Digest$" } | Select-Object -First 1
    if ($null -eq $match) {
        return $null
    }
    return ($match -split "\|", 2)[0].Trim()
}

Write-Host "Starting the local automation services..."
& docker compose up -d postgres mailpit ao-worker n8n | Out-Host

$workflowId = Get-OneTechWorkflowId
if (-not $workflowId) {
    Write-Host "Importing the OneTech daily workflow for the first time..."
    & docker compose exec -T n8n n8n import:workflow --input=/workflows/daily-digest.json | Out-Host
    $workflowId = Get-OneTechWorkflowId
}

if (-not $workflowId) {
    throw "The OneTech n8n workflow could not be found after import."
}

if ($ImportOnly) {
    Write-Host "Workflow imported: $workflowId (left inactive by request)."
    exit 0
}

Write-Host "Activating workflow $workflowId..."
& docker compose exec -T n8n n8n update:workflow --id=$workflowId --active=true | Out-Host

# n8n applies CLI activation after a restart.  Only the n8n container is
# recreated; PostgreSQL, Mailpit, and the worker keep their state.
& docker compose up -d --force-recreate n8n | Out-Host

$activeLines = & docker compose exec -T n8n n8n list:workflow --active=true 2>&1
if (-not ($activeLines | Where-Object { $_ -eq "$workflowId|OneTech AO - Daily Digest" })) {
    throw "The OneTech workflow is not active after the n8n restart."
}

Write-Host "Ready. n8n will run weekdays at 08:00 Europe/Paris."
Write-Host "Safe delivery mode remains Mailpit; open http://localhost:8025 to inspect test emails."
