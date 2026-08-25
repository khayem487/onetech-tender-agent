[CmdletBinding()]
param(
    [string]$BackupDirectory,
    [string]$ReportDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $ReportDirectory) {
    $ReportDirectory = Join-Path $projectRoot 'backups\restore-drill-reports'
}

function Get-ProjectEnvValue([string]$Name) {
    $match = Get-Content -LiteralPath (Join-Path $projectRoot '.env') |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=(.*)$" } |
        Select-Object -First 1
    if (-not $match) { throw "Variable .env manquante : $Name" }
    return (($match -split '=', 2)[1]).Trim().Trim('"').Trim("'")
}

function Test-DatabaseExists {
    param([string]$User, [string]$Database)
    if ($Database -notmatch '^onetech_restore_drill_[0-9]{14}_[a-f0-9]{6}$') {
        throw "Nom de base de drill non sur : $Database"
    }
    $value = "$(& docker compose exec -T postgres psql -U $User -d postgres -At -c "SELECT 1 FROM pg_database WHERE datname = '$Database';")"
    if ($LASTEXITCODE -ne 0) { throw 'Verification de la base temporaire echouee.' }
    return $value.Trim() -eq '1'
}

Push-Location $projectRoot
$startedAt = (Get-Date).ToUniversalTime()
$targetDatabase = "onetech_restore_drill_$((Get-Date).ToString('yyyyMMddHHmmss'))_$([guid]::NewGuid().ToString('N').Substring(0, 6))"
if ($targetDatabase -notmatch '^onetech_restore_drill_[0-9]{14}_[a-f0-9]{6}$') {
    throw 'Le nom de base temporaire genere ne respecte pas la garde de securite.'
}
$status = 'failed'
$errorMessage = $null
$restoredTableCounts = [ordered]@{}
$reportPath = $null
try {
    if (-not $BackupDirectory) {
        $latest = Get-ChildItem -LiteralPath (Join-Path $projectRoot 'backups') -Directory -Filter 'onetech-*' |
            Where-Object {
                (Test-Path -LiteralPath (Join-Path $_.FullName 'manifest.json')) -and
                -not (Test-Path -LiteralPath (Join-Path $_.FullName 'INCOMPLETE'))
            } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if (-not $latest) { throw 'Aucune sauvegarde complete trouvee.' }
        $BackupDirectory = $latest.FullName
    }
    $backup = (Resolve-Path -LiteralPath $BackupDirectory).Path
    $manifest = Get-Content -Raw -LiteralPath (Join-Path $backup 'manifest.json') | ConvertFrom-Json

    & (Join-Path $PSScriptRoot 'restore-onetech-stack.ps1') `
        -BackupDirectory $backup `
        -RestorePostgres `
        -TargetDatabase $targetDatabase `
        -ConfirmRestore "RESTORE:$targetDatabase"
    if ($LASTEXITCODE -ne 0) { throw 'Le script de restauration a retourne une erreur.' }

    $postgresUser = Get-ProjectEnvValue 'POSTGRES_USER'
    foreach ($property in $manifest.postgres.table_counts.PSObject.Properties) {
        $table = $property.Name
        if ($table -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { throw "Nom de table non sur : $table" }
        $count = (& docker compose exec -T postgres psql -U $postgresUser -d $targetDatabase -At -c "SELECT count(*) FROM public.`"$table`";").Trim()
        if ($LASTEXITCODE -ne 0) { throw "Lecture de $table dans la base restauree echouee." }
        $restoredTableCounts[$table] = [long]$count
    }
    $integrity = (& docker compose exec -T postgres psql -U $postgresUser -d $targetDatabase -At -c "SELECT count(*) FROM pg_catalog.pg_class WHERE relnamespace = 'public'::regnamespace AND relkind IN ('r','p');").Trim()
    if ($LASTEXITCODE -ne 0 -or [int]$integrity -le 0) { throw 'La base restauree ne contient aucune table publique.' }

    $status = 'passed'
}
catch {
    $errorMessage = $_.Exception.Message
    throw
}
finally {
    try {
        $postgresUser = Get-ProjectEnvValue 'POSTGRES_USER'
        if (Test-DatabaseExists -User $postgresUser -Database $targetDatabase) {
            & docker compose exec -T postgres psql -U $postgresUser -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$targetDatabase' AND pid <> pg_backend_pid();" | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Arret des connexions de drill echoue.' }
            & docker compose exec -T postgres dropdb --if-exists -U $postgresUser $targetDatabase
            if ($LASTEXITCODE -ne 0) { throw 'Suppression de la base temporaire de drill echouee.' }
        }
    }
    catch {
        if (-not $errorMessage) { $errorMessage = $_.Exception.Message }
        $status = 'failed_cleanup'
    }

    New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null
    $reportDirectoryResolved = (Resolve-Path -LiteralPath $ReportDirectory).Path
    $reportPath = Join-Path $reportDirectoryResolved "restore-drill-$((Get-Date).ToString('yyyyMMdd-HHmmss')).json"
    [ordered]@{
        schema = 'onetech-restore-drill-v1'
        started_at = $startedAt.ToString('o')
        finished_at = (Get-Date).ToUniversalTime().ToString('o')
        backup_directory = if ($BackupDirectory) { [IO.Path]::GetFullPath($BackupDirectory) } else { $null }
        temporary_database = $targetDatabase
        temporary_database_removed = -not (Test-DatabaseExists -User (Get-ProjectEnvValue 'POSTGRES_USER') -Database $targetDatabase)
        status = $status
        restored_table_counts = $restoredTableCounts
        error = $errorMessage
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding utf8
    Pop-Location
    Write-Host "Rapport du drill : $reportPath"
}

if ($status -ne 'passed') { throw "Restore drill non valide : $status" }
Write-Host 'Restore drill PostgreSQL reussi; la base temporaire a ete supprimee.' -ForegroundColor Green
