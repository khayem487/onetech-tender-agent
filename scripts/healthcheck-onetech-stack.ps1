[CmdletBinding()]
param(
    [switch]$RequireGateway,
    [switch]$RequireOllama,
    [switch]$RequireWorkflows,
    [switch]$RequireMcp,
    [switch]$AsJson,
    [switch]$NoExit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$companyRoot = Split-Path -Parent $projectRoot
$results = [System.Collections.Generic.List[object]]::new()

function Add-Result([string]$Name, [bool]$Ok, [string]$Detail) {
    $results.Add([pscustomobject]@{ name = $Name; ok = $Ok; detail = $Detail })
}

function Test-TcpPort([string]$HostName, [int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        if (-not $task.Wait(3000)) { return $false }
        return $client.Connected
    }
    catch { return $false }
    finally { $client.Dispose() }
}

function Get-ProjectEnvValue([string]$Name) {
    $envPath = Join-Path $projectRoot '.env'
    if (-not (Test-Path -LiteralPath $envPath)) {
        throw '.env introuvable.'
    }
    $match = Get-Content -LiteralPath $envPath |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=(.*)$" } |
        Select-Object -First 1
    if (-not $match) { throw "Variable .env manquante : $Name" }
    return (($match -split '=', 2)[1]).Trim().Trim('"').Trim("'")
}

function Get-OptionalProjectEnvValue([string]$Name) {
    $envPath = Join-Path $projectRoot '.env'
    if (-not (Test-Path -LiteralPath $envPath)) { return $null }
    $match = Get-Content -LiteralPath $envPath |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=(.*)$" } |
        Select-Object -First 1
    if (-not $match) { return $null }
    return (($match -split '=', 2)[1]).Trim().Trim('"').Trim("'")
}

function Get-TelegramConfiguration {
    $enabledValue = Get-OptionalProjectEnvValue 'TELEGRAM_ENABLED'
    $enabled = $enabledValue -match '^(?i:true|1|yes)$'
    if (-not $enabled) {
        return [pscustomobject]@{ Enabled = $false; Valid = $true; Detail = 'disabled by configuration' }
    }

    $token = Get-OptionalProjectEnvValue 'TELEGRAM_BOT_TOKEN'
    $chatId = Get-OptionalProjectEnvValue 'TELEGRAM_CHAT_ID'
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

function Get-ActiveN8nWorkflows {
    try {
        return @(& docker compose exec -T n8n n8n list:workflow --active=true 2>$null)
    }
    catch {
        return @()
    }
}

Push-Location $projectRoot
try {
    $dockerReachable = $false
    try {
        & docker info *> $null
        $dockerReachable = $LASTEXITCODE -eq 0
    }
    catch { $dockerReachable = $false }
    Add-Result 'docker:engine' $dockerReachable $(if ($dockerReachable) { 'reachable' } else { 'unreachable' })

    $expected = @('postgres', 'pgadmin', 'mailpit', 'ao-worker', 'n8n')
    $running = if ($dockerReachable) { @(& docker compose ps --services --status running 2>$null) } else { @() }
    foreach ($service in $expected) {
        $isRunning = $running -contains $service
        Add-Result "docker:$service" $isRunning $(if ($isRunning) { 'running' } else { 'not running' })
    }

    $postgresOk = $false
    try {
        $postgresUser = Get-ProjectEnvValue 'POSTGRES_USER'
        $postgresDatabase = Get-ProjectEnvValue 'POSTGRES_DB'
        $answer = (& docker compose exec -T postgres psql -X -U $postgresUser -d $postgresDatabase -tAc 'SELECT 1;' 2>$null).Trim()
        $postgresOk = $answer -eq '1'
    }
    catch { $postgresOk = $false }
    Add-Result 'postgres:query' $postgresOk $(if ($postgresOk) { 'SELECT 1' } else { 'query failed' })

    foreach ($check in @(
        @{ name = 'n8n:http'; url = 'http://127.0.0.1:5678/healthz' },
        @{ name = 'mailpit:http'; url = 'http://127.0.0.1:8025/api/v1/info' },
        @{ name = 'pgadmin:http'; url = 'http://127.0.0.1:5050/misc/ping' }
    )) {
        $ok = $false
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $check.url -TimeoutSec 5
            $ok = $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
        }
        catch { $ok = $false }
        Add-Result $check.name $ok $(if ($ok) { $check.url } else { 'unreachable' })
    }

    $workerOk = $false
    try {
        $workerStatus = (& docker compose exec -T ao-worker python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=5).status)" 2>$null).Trim()
        $workerOk = $workerStatus -eq '200'
    }
    catch { $workerOk = $false }
    Add-Result 'ao-worker:http' $workerOk $(if ($workerOk) { 'health 200' } else { 'health failed' })

    $activeWorkflows = if ($dockerReachable) { @(Get-ActiveN8nWorkflows) } else { @() }
    $dailyName = 'OneTech AO - Daily Digest'
    $dailyActive = @($activeWorkflows | Where-Object { $_ -match "^[^|]+\|$([regex]::Escape($dailyName))$" }).Count -gt 0
    Add-Result 'n8n:workflow:daily' $dailyActive $(if ($dailyActive) { 'active' } else { 'inactive or missing' })

    $telegramConfiguration = Get-TelegramConfiguration
    Add-Result 'telegram:configuration' $telegramConfiguration.Valid $telegramConfiguration.Detail
    $telegramName = 'OneTech AO - Telegram Mentions'
    $telegramActive = @($activeWorkflows | Where-Object { $_ -match "^[^|]+\|$([regex]::Escape($telegramName))$" }).Count -gt 0
    $telegramWorkflowOk = if ($telegramConfiguration.Enabled -and $telegramConfiguration.Valid) { $telegramActive } else { -not $telegramActive }
    $telegramWorkflowDetail = if ($telegramConfiguration.Enabled -and $telegramConfiguration.Valid) {
        if ($telegramActive) { 'active with dedicated configuration' } else { 'enabled but inactive or missing' }
    }
    else {
        if ($telegramActive) { 'must remain inactive without dedicated configuration' } else { 'inactive by design' }
    }
    Add-Result 'n8n:workflow:telegram' $telegramWorkflowOk $telegramWorkflowDetail

    $gatewayOk = Test-TcpPort '127.0.0.1' 18790
    Add-Result 'openclaw-company:gateway' $gatewayOk $(if ($gatewayOk) { '127.0.0.1:18790' } else { 'not listening' })

    $ollamaOk = $false
    $ollamaDetail = 'not listening'
    try {
        $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5
        $names = @($tags.models | ForEach-Object { $_.name })
        $ollamaOk = @($names | Where-Object { $_ -match '^phi4-mini(?::|$)' }).Count -gt 0
        $ollamaDetail = if ($ollamaOk) { 'phi4-mini available' } else { 'Ollama reachable but phi4-mini missing' }
    }
    catch { }
    Add-Result 'ollama:phi4-mini' $ollamaOk $ollamaDetail

    $mcpOk = $false
    $mcpDetail = 'unavailable'
    try {
        $companyConfig = Get-Content -LiteralPath (Join-Path $companyRoot 'openclaw.json') -Raw | ConvertFrom-Json
        $registered = $null -ne $companyConfig.mcp.servers.'onetech-tender'
        $python = Join-Path $projectRoot '.venv\Scripts\python.exe'
        if ($registered -and (Test-Path -LiteralPath $python)) {
            $probe = & $python -c "import asyncio; from onetech_ao.mcp_server import create_server; s=create_server(); names=set(t.name for t in asyncio.run(s.list_tools())); expected={'analyze_tender','collect_tenders','generate_digest','get_tender','list_open_tenders'}; assert expected.issubset(names); print(len(names))" 2>$null
            $probeCount = ($probe | Select-Object -Last 1).ToString().Trim()
            $mcpOk = $LASTEXITCODE -eq 0 -and $probeCount -match '^\d+$' -and [int]$probeCount -ge 5
            if ($mcpOk) { $mcpDetail = "registered; $probeCount tools advertised" }
        }
    }
    catch { $mcpOk = $false }
    Add-Result 'mcp:onetech-tender' $mcpOk $mcpDetail

    $requiredChecks = @(
        'docker:engine', 'docker:postgres', 'docker:pgadmin', 'docker:mailpit',
        'docker:ao-worker', 'docker:n8n', 'postgres:query',
        'n8n:http', 'mailpit:http', 'pgadmin:http', 'ao-worker:http'
    )
    if ($RequireGateway) { $requiredChecks += 'openclaw-company:gateway' }
    if ($RequireOllama) { $requiredChecks += 'ollama:phi4-mini' }
    if ($RequireWorkflows) { $requiredChecks += @('n8n:workflow:daily', 'telegram:configuration', 'n8n:workflow:telegram') }
    if ($RequireMcp) { $requiredChecks += 'mcp:onetech-tender' }

    $failed = @($results | Where-Object { -not $_.ok })
    $failedRequired = @($results | Where-Object { -not $_.ok -and $_.name -in $requiredChecks })
    if ($AsJson) {
        [pscustomobject]@{
            ok = $failedRequired.Count -eq 0
            checked_at = (Get-Date).ToString('o')
            warnings = @($failed | Where-Object { $_.name -notin $requiredChecks })
            results = $results
        } | ConvertTo-Json -Depth 5
    }
    else {
        $results | Format-Table -AutoSize
    }
    if ($failedRequired.Count -gt 0 -and -not $NoExit) { exit 1 }
}
finally {
    Pop-Location
}
