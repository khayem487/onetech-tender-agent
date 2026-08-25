[CmdletBinding()]
param(
    [switch]$NoRepair,
    [string]$LogPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$logRoot = Join-Path $projectRoot 'logs\operations'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
if (-not $LogPath) {
    $LogPath = Join-Path $logRoot ("watchdog-{0}.log" -f (Get-Date -Format 'yyyy-MM-dd'))
}

function Write-WatchdogLog([string]$Message, [string]$Level = 'INFO') {
    $line = "{0} [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    Write-Host $line
}

function Get-HealthResult {
    $json = & "$PSScriptRoot\healthcheck-onetech-stack.ps1" `
        -RequireGateway -RequireOllama -RequireWorkflows -RequireMcp -AsJson -NoExit
    return ($json | Out-String | ConvertFrom-Json)
}

$createdNew = $false
$mutex = [System.Threading.Mutex]::new($true, 'Local\OneTechTenderAgentWatchdog', [ref]$createdNew)
if (-not $createdNew) {
    Write-WatchdogLog 'Another watchdog instance is already running; this invocation exits.' 'WARN'
    $mutex.Dispose()
    exit 0
}

try {
    Write-WatchdogLog 'Watchdog check begins.'
    $health = Get-HealthResult
    if ($health.ok) {
        Write-WatchdogLog 'All required components are healthy.'
        exit 0
    }

    $failed = @($health.results | Where-Object { -not $_.ok } | ForEach-Object { $_.name })
    Write-WatchdogLog ("Unhealthy components: {0}" -f ($failed -join ', ')) 'WARN'
    if ($NoRepair) { exit 1 }

    Write-WatchdogLog 'Starting a bounded repair attempt.'
    & "$PSScriptRoot\start-onetech-stack.ps1" -StartGateway -StartOllama -LogPath $LogPath

    $afterRepair = Get-HealthResult
    if (-not $afterRepair.ok) {
        $stillFailed = @($afterRepair.results | Where-Object { -not $_.ok } | ForEach-Object { $_.name })
        Write-WatchdogLog ("Repair incomplete: {0}" -f ($stillFailed -join ', ')) 'ERROR'
        exit 1
    }
    Write-WatchdogLog 'Repair succeeded; all required components are healthy.'
}
catch {
    Write-WatchdogLog $_.Exception.Message 'ERROR'
    exit 1
}
finally {
    if ($createdNew) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
