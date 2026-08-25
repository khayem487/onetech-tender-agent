[CmdletBinding()]
param(
    [switch]$StartGateway,
    [switch]$StartOllama,
    [switch]$SkipWorkflowActivation,
    [switch]$SkipDatabaseMigration,
    [string]$LogPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$companyRoot = Split-Path -Parent $projectRoot
$operationsLogRoot = Join-Path $projectRoot 'logs\operations'
New-Item -ItemType Directory -Path $operationsLogRoot -Force | Out-Null
if (-not $LogPath) {
    $LogPath = Join-Path $operationsLogRoot ("startup-{0}.log" -f (Get-Date -Format 'yyyy-MM-dd'))
}

function Write-OperationLog([string]$Message, [string]$Level = 'INFO') {
    $line = "{0} [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    Write-Host $line
}

function Test-TcpPort([string]$HostName, [int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        if (-not $task.Wait(2000)) { return $false }
        return $client.Connected
    }
    catch { return $false }
    finally { $client.Dispose() }
}

function Test-DockerEngine {
    try {
        & docker info *> $null
        return $LASTEXITCODE -eq 0
    }
    catch { return $false }
}

function Wait-TcpPort([string]$HostName, [int]$Port, [int]$TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (Test-TcpPort $HostName $Port) { return $true }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Test-N8nWorkflowActive([string]$WorkflowName) {
    try {
        $active = @(& docker compose exec -T n8n n8n list:workflow --active=true 2>$null)
        return @($active | Where-Object { $_ -match "^[^|]+\|$([regex]::Escape($WorkflowName))$" }).Count -gt 0
    }
    catch { return $false }
}

function Get-N8nWorkflowId([string]$WorkflowName) {
    try {
        $lines = @(
            (& docker compose exec -T n8n n8n list:workflow --active=true 2>$null)
            (& docker compose exec -T n8n n8n list:workflow --active=false 2>$null)
        )
        $match = $lines | Where-Object { $_ -match "^([^|]+)\|$([regex]::Escape($WorkflowName))$" } | Select-Object -First 1
        if ($match) { return ($match -split '\|', 2)[0].Trim() }
    }
    catch { }
    return $null
}

function Get-OptionalEnvValue([string]$Name) {
    $envPath = Join-Path $projectRoot '.env'
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
        return [pscustomobject]@{ Enabled = $false; Valid = $true; Detail = 'disabled by configuration' }
    }

    $token = Get-OptionalEnvValue 'TELEGRAM_BOT_TOKEN'
    $chatId = Get-OptionalEnvValue 'TELEGRAM_CHAT_ID'
    $tokenShapeValid = $token -match '^\d+:[A-Za-z0-9_-]{20,}$'
    $negativeGroupId = $chatId -match '^-[1-9]\d+$'
    $dedicatedToken = $tokenShapeValid
    try {
        $personalConfig = Get-Content -LiteralPath (Join-Path $env:USERPROFILE '.openclaw\openclaw.json') -Raw | ConvertFrom-Json
        $personalToken = $personalConfig.channels.telegram.botToken
        if ($personalToken -and $token -eq $personalToken) { $dedicatedToken = $false }
    }
    catch { }

    $valid = $tokenShapeValid -and $negativeGroupId -and $dedicatedToken
    return [pscustomobject]@{
        Enabled = $true
        Valid = $valid
        Detail = if ($valid) { 'dedicated bot and group configured' } else { 'invalid or non-dedicated Telegram configuration' }
    }
}

function Disable-N8nWorkflow([string]$WorkflowName) {
    if (-not (Test-N8nWorkflowActive $WorkflowName)) { return }
    $workflowId = Get-N8nWorkflowId $WorkflowName
    if (-not $workflowId) { throw "Cannot find active n8n workflow: $WorkflowName" }
    Write-OperationLog "Deactivating n8n workflow: $WorkflowName"
    & docker compose exec -T n8n n8n update:workflow --id=$workflowId --active=false | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Failed to deactivate n8n workflow: $WorkflowName" }
    & docker compose up -d --force-recreate n8n | Out-Host
}

function Start-CompanyGateway {
    if (Test-TcpPort '127.0.0.1' 18790) {
        Write-OperationLog 'Company gateway already listens on 127.0.0.1:18790.'
        return
    }

    $launcher = Join-Path $companyRoot 'start-company-gateway.cmd'
    if (-not (Test-Path -LiteralPath $launcher)) {
        throw "Company gateway launcher not found: $launcher"
    }
    $launchStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $stdout = Join-Path $operationsLogRoot "company-gateway-$launchStamp.stdout.log"
    $stderr = Join-Path $operationsLogRoot "company-gateway-$launchStamp.stderr.log"
    Write-OperationLog 'Starting company OpenClaw gateway on port 18790.'
    Start-Process -FilePath 'cmd.exe' `
        -ArgumentList @('/d', '/c', "`"$launcher`"") `
        -WorkingDirectory $companyRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr | Out-Null

    if (-not (Wait-TcpPort '127.0.0.1' 18790 120)) {
        throw "Company gateway did not bind port 18790. Inspect $stderr"
    }
    Write-OperationLog 'Company gateway is ready.'
}

function Start-LocalOllama {
    if (Test-TcpPort '127.0.0.1' 11434) {
        Write-OperationLog 'Ollama already listens on 127.0.0.1:11434.'
        return
    }

    $ollamaCommand = Get-Command ollama.exe -ErrorAction SilentlyContinue
    $ollamaPath = if ($ollamaCommand) { $ollamaCommand.Source } else { Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe' }
    if (-not (Test-Path -LiteralPath $ollamaPath)) {
        throw 'Ollama is installed neither in PATH nor in the standard local application directory.'
    }
    $launchStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $stdout = Join-Path $operationsLogRoot "ollama-$launchStamp.stdout.log"
    $stderr = Join-Path $operationsLogRoot "ollama-$launchStamp.stderr.log"
    Write-OperationLog 'Starting the local Ollama service.'
    Start-Process -FilePath $ollamaPath `
        -ArgumentList @('serve') `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr | Out-Null
    if (-not (Wait-TcpPort '127.0.0.1' 11434 45)) {
        throw "Ollama did not bind port 11434. Inspect $stderr"
    }
    Write-OperationLog 'Ollama is ready.'
}

Write-OperationLog 'OneTech stack startup begins.'
try {
    if (-not (Test-DockerEngine)) {
        $dockerDesktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
        if (-not (Test-Path -LiteralPath $dockerDesktop)) {
            throw 'Docker Desktop is unavailable.'
        }
        Write-OperationLog 'Starting Docker Desktop.'
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden | Out-Null
        $deadline = (Get-Date).AddMinutes(4)
        do {
            Start-Sleep -Seconds 5
            if (Test-DockerEngine) { break }
        } while ((Get-Date) -lt $deadline)
        if (-not (Test-DockerEngine)) { throw 'Docker Desktop did not become ready within four minutes.' }
    }

    Push-Location $projectRoot
    try {
        Write-OperationLog 'Starting Docker Compose services.'
        # Docker Compose writes normal progress messages to stderr.  Under
        # Windows PowerShell, ErrorActionPreference=Stop would incorrectly
        # turn those messages into terminating NativeCommandError records.
        $savedErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $composeOutput = @(& docker compose up -d 2>&1)
            $composeExitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $savedErrorActionPreference
        }
        foreach ($composeLine in $composeOutput) {
            $composeText = $composeLine.ToString()
            Add-Content -LiteralPath $LogPath -Value $composeText -Encoding UTF8
            Write-Host $composeText
        }
        if ($composeExitCode -ne 0) { throw "docker compose up failed with exit code $composeExitCode" }

        if (-not $SkipDatabaseMigration) {
            Write-OperationLog 'Applying idempotent database migrations.'
            & "$PSScriptRoot\apply-database.ps1"
        }

        if (-not $SkipWorkflowActivation) {
            if (-not (Test-N8nWorkflowActive 'OneTech AO - Daily Digest')) {
                Write-OperationLog 'Activating the daily n8n workflow.'
                & "$PSScriptRoot\activate-daily-automation.ps1"
            }
            else { Write-OperationLog 'Daily n8n workflow is already active.' }

            $telegramConfiguration = Get-TelegramConfiguration
            $telegramWorkflowName = 'OneTech AO - Telegram Mentions'
            $telegramWorkflow = Join-Path $projectRoot 'automation\n8n\workflows\telegram-mentions.json'
            if ($telegramConfiguration.Enabled -and $telegramConfiguration.Valid) {
                if (-not (Test-Path -LiteralPath $telegramWorkflow)) {
                    throw 'Telegram is enabled but its n8n workflow file is missing.'
                }
                if (-not (Test-N8nWorkflowActive $telegramWorkflowName)) {
                    Write-OperationLog 'Activating the dedicated OneTech Telegram workflow.'
                    & "$PSScriptRoot\activate-telegram-automation.ps1"
                }
                else { Write-OperationLog 'Dedicated OneTech Telegram workflow is already active.' }
            }
            else {
                Disable-N8nWorkflow $telegramWorkflowName
                Write-OperationLog "Telegram remains inactive: $($telegramConfiguration.Detail)."
            }
        }
    }
    finally { Pop-Location }

    if ($StartOllama) { Start-LocalOllama }
    if ($StartGateway) { Start-CompanyGateway }

    $healthParameters = @{
        RequireWorkflows = $true
        RequireMcp = $true
    }
    if ($StartGateway) { $healthParameters.RequireGateway = $true }
    if ($StartOllama) { $healthParameters.RequireOllama = $true }
    Write-OperationLog 'Running final health checks.'
    & "$PSScriptRoot\healthcheck-onetech-stack.ps1" @healthParameters
    Write-OperationLog 'OneTech stack startup completed successfully.'
}
catch {
    Write-OperationLog $_.Exception.Message 'ERROR'
    throw
}
