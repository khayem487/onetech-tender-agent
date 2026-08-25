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

function Get-OptionalEnvValue([string]$Name) {
    $envPath = Join-Path $workspace '.env'
    if (-not (Test-Path -LiteralPath $envPath)) { return $null }
    $match = Get-Content -LiteralPath $envPath |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=(.*)$" } |
        Select-Object -First 1
    if (-not $match) { return $null }
    return (($match -split '=', 2)[1]).Trim().Trim('"').Trim("'")
}

function Get-TelegramConfiguration {
    $enabledValue = Get-OptionalEnvValue 'TELEGRAM_ENABLED'
    $enabled = $enabledValue -match '^(?i:true|1|yes)$'
    if (-not $enabled) {
        return [pscustomobject]@{
            Enabled = $false
            Valid = $true
            Detail = 'disabled by configuration'
        }
    }

    $token = Get-OptionalEnvValue 'TELEGRAM_BOT_TOKEN'
    $chatId = Get-OptionalEnvValue 'TELEGRAM_CHAT_ID'
    $tokenShapeValid = $token -match '^\d+:[A-Za-z0-9_-]{20,}$'
    $negativeGroupId = $chatId -match '^-[1-9]\d+$'
    $dedicatedToken = $tokenShapeValid

    try {
        $personalConfigPath = Join-Path $env:USERPROFILE '.openclaw\openclaw.json'
        $personalConfig = Get-Content -LiteralPath $personalConfigPath -Raw | ConvertFrom-Json
        $personalToken = $personalConfig.channels.telegram.botToken
        if ($personalToken -and $token -eq $personalToken) {
            $dedicatedToken = $false
        }
    }
    catch { }

    $valid = $tokenShapeValid -and $negativeGroupId -and $dedicatedToken
    return [pscustomobject]@{
        Enabled = $true
        Valid = $valid
        Detail = if ($valid) {
            'dedicated bot and group configured'
        }
        else {
            'invalid or non-dedicated Telegram configuration'
        }
    }
}

function Disable-OneTechTelegramWorkflow([string]$WorkflowId) {
    & docker compose exec -T n8n n8n update:workflow --id=$WorkflowId --active=false | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw 'The OneTech Telegram workflow could not be deactivated safely.'
    }
    & docker compose up -d --force-recreate n8n | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw 'n8n could not be restarted after Telegram workflow deactivation.'
    }
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
    Disable-OneTechTelegramWorkflow $workflowId
    Write-Host "Workflow imported: $workflowId (left inactive by request)."
    exit 0
}

$telegramConfiguration = Get-TelegramConfiguration
if (-not $telegramConfiguration.Enabled -or -not $telegramConfiguration.Valid) {
    Disable-OneTechTelegramWorkflow $workflowId
    throw "Telegram activation refused: $($telegramConfiguration.Detail). Configure TELEGRAM_ENABLED=true with a dedicated OneTech bot token and a negative group chat ID."
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
