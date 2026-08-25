[CmdletBinding()]
param(
    [string]$BackupRoot,
    [switch]$IncludeMailpit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$companyRoot = (Resolve-Path (Join-Path $projectRoot '..')).Path
if (-not $BackupRoot) {
    $BackupRoot = Join-Path $projectRoot 'backups'
}

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & docker compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($Arguments -join ' ') a echoue."
    }
}

function Invoke-Docker {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($Arguments -join ' ') a echoue."
    }
}

function Get-ProjectEnvValue([string]$Name) {
    $envFile = Join-Path $projectRoot '.env'
    $match = Get-Content -LiteralPath $envFile |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=(.*)$" } |
        Select-Object -First 1
    if (-not $match) { throw "Variable .env manquante : $Name" }
    return (($match -split '=', 2)[1]).Trim().Trim('"').Trim("'")
}

function Copy-DirectorySnapshot {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        return $false
    }
    $parent = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
    return $true
}

function Test-SecretPropertyName([string]$Name) {
    $normalized = ($Name -replace '[-_.]', '').ToLowerInvariant()
    return $normalized -in @(
        'token', 'apikey', 'password', 'secret', 'clientsecret',
        'accesstoken', 'refreshtoken', 'encryptionkey', 'credential', 'credentials'
    )
}

function ConvertTo-SanitizedValue($Value) {
    if ($null -eq $Value) { return $null }

    if ($Value -is [System.Collections.IDictionary]) {
        $copy = [ordered]@{}
        foreach ($key in $Value.Keys) {
            if (Test-SecretPropertyName ([string]$key)) {
                $copy[[string]$key] = '<redacted>'
            }
            else {
                $copy[[string]$key] = ConvertTo-SanitizedValue $Value[$key]
            }
        }
        return $copy
    }

    if ($Value -is [pscustomobject]) {
        $copy = [ordered]@{}
        foreach ($property in $Value.PSObject.Properties) {
            if (Test-SecretPropertyName $property.Name) {
                $copy[$property.Name] = '<redacted>'
            }
            else {
                $copy[$property.Name] = ConvertTo-SanitizedValue $property.Value
            }
        }
        return $copy
    }

    if (($Value -is [System.Collections.IEnumerable]) -and -not ($Value -is [string])) {
        return @($Value | ForEach-Object { ConvertTo-SanitizedValue $_ })
    }

    return $Value
}

function Get-RelativeBackupPath {
    param([string]$Root, [string]$FullName)
    return $FullName.Substring($Root.Length).TrimStart('\', '/') -replace '\\', '/'
}

function Get-PublicTableCounts {
    param([string]$User, [string]$Database)

    $tables = @(& docker compose exec -T postgres psql -U $User -d $Database -At -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")
    if ($LASTEXITCODE -ne 0) { throw 'Lecture des tables PostgreSQL echouee.' }

    $counts = [ordered]@{}
    foreach ($table in ($tables | Where-Object { $_ })) {
        if ($table -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
            throw "Nom de table inattendu : $table"
        }
        $count = (& docker compose exec -T postgres psql -U $User -d $Database -At -c "SELECT count(*) FROM public.`"$table`";").Trim()
        if ($LASTEXITCODE -ne 0) { throw "Comptage de la table $table echoue." }
        $counts[$table] = [long]$count
    }
    return $counts
}

function Test-BackupPayload {
    param(
        [string]$BackupDirectory,
        [string]$PostgresContainer
    )

    $manifestPath = Join-Path $BackupDirectory 'manifest.json'
    $checksumsPath = Join-Path $BackupDirectory 'checksums.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'manifest.json est absent.' }
    if (-not (Test-Path -LiteralPath $checksumsPath -PathType Leaf)) { throw 'checksums.json est absent.' }

    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    if ($manifest.schema -ne 'onetech-backup-v2') { throw "Schema de sauvegarde non pris en charge : $($manifest.schema)" }

    $checksumDocument = Get-Content -Raw -LiteralPath $checksumsPath | ConvertFrom-Json
    if ($checksumDocument.schema -ne 'onetech-checksums-v1') { throw 'Schema de checksums invalide.' }
    foreach ($entry in $checksumDocument.files) {
        $relative = [string]$entry.path
        if ([IO.Path]::IsPathRooted($relative) -or $relative -match '(^|/)\.\.(/|$)') {
            throw "Chemin de checksum non sur : $relative"
        }
        $file = Join-Path $BackupDirectory ($relative -replace '/', '\')
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Fichier sauvegarde manquant : $relative" }
        $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne ([string]$entry.sha256).ToLowerInvariant()) { throw "Checksum invalide : $relative" }
        if ((Get-Item -LiteralPath $file).Length -ne [long]$entry.bytes) { throw "Taille invalide : $relative" }
    }

    $workflows = Join-Path $BackupDirectory 'n8n-workflows.json'
    Get-Content -Raw -LiteralPath $workflows | ConvertFrom-Json | Out-Null
    $n8nDatabase = Join-Path $BackupDirectory 'n8n-state\database.sqlite'
    if (-not (Test-Path -LiteralPath $n8nDatabase -PathType Leaf) -or (Get-Item $n8nDatabase).Length -le 0) {
        throw 'La base n8n sauvegardee est absente ou vide.'
    }
    if (Test-Path -LiteralPath (Join-Path $BackupDirectory 'n8n-state\config')) {
        throw 'Le fichier secret n8n-state/config ne doit jamais etre inclus.'
    }

    $dump = Join-Path $BackupDirectory 'postgresql.dump'
    $remoteDump = "/tmp/onetech-backup-validate-$([guid]::NewGuid().ToString('N')).dump"
    try {
        Invoke-Docker cp $dump "${PostgresContainer}:$remoteDump"
        & docker compose exec -T postgres pg_restore --list $remoteDump | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Le dump PostgreSQL est illisible par pg_restore.' }
    }
    finally {
        & docker compose exec -T postgres sh -lc "rm -f '$remoteDump'" | Out-Null
    }
}

Push-Location $projectRoot
$target = $null
$n8nWasStopped = $false
$mailpitWasStopped = $false
try {
    $requiredServices = @('postgres', 'n8n')
    $running = @(& docker compose ps --services --status running)
    foreach ($service in $requiredServices) {
        if ($running -notcontains $service) {
            throw "Le service $service doit etre demarre avant une sauvegarde."
        }
    }

    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
    $backupRootResolved = (Resolve-Path -LiteralPath $BackupRoot).Path
    $target = Join-Path $backupRootResolved "onetech-$stamp"
    New-Item -ItemType Directory -Path $target | Out-Null
    Set-Content -LiteralPath (Join-Path $target 'INCOMPLETE') -Value 'Backup creation is still in progress.' -Encoding ascii

    $postgresContainer = (& docker compose ps -q postgres).Trim()
    $n8nContainer = (& docker compose ps -q n8n).Trim()
    $postgresUser = Get-ProjectEnvValue 'POSTGRES_USER'
    $postgresDatabase = Get-ProjectEnvValue 'POSTGRES_DB'
    if (-not $postgresContainer -or -not $n8nContainer) {
        throw 'Impossible de trouver les conteneurs PostgreSQL ou n8n.'
    }

    $remoteDump = "/tmp/onetech-postgres-$stamp.dump"
    $localDump = Join-Path $target 'postgresql.dump'
    try {
        Invoke-Compose exec -T postgres pg_dump -Fc -U $postgresUser "--dbname=$postgresDatabase" -f $remoteDump
        Invoke-Docker cp "${postgresContainer}:$remoteDump" $localDump
    }
    finally {
        & docker compose exec -T postgres sh -lc "rm -f '$remoteDump'" | Out-Null
    }
    $tableCounts = Get-PublicTableCounts -User $postgresUser -Database $postgresDatabase

    $remoteWorkflows = "/tmp/onetech-n8n-workflows-$stamp.json"
    $localWorkflows = Join-Path $target 'n8n-workflows.json'
    try {
        Invoke-Compose exec -T n8n n8n export:workflow --all --output=$remoteWorkflows
        Invoke-Docker cp "${n8nContainer}:$remoteWorkflows" $localWorkflows
    }
    finally {
        & docker compose exec -T n8n rm -f $remoteWorkflows | Out-Null
    }

    # Stop n8n briefly so database.sqlite cannot change while it is copied.
    Invoke-Compose stop n8n
    $n8nWasStopped = $true
    $n8nState = Join-Path $target 'n8n-state'
    New-Item -ItemType Directory -Path $n8nState | Out-Null
    Invoke-Docker cp "${n8nContainer}:/home/node/.n8n/." $n8nState
    $n8nConfig = Join-Path $n8nState 'config'
    if (Test-Path -LiteralPath $n8nConfig) {
        # n8n writes its encryption key here. The key must be recovered from .env,
        # never from a portable backup.
        Remove-Item -LiteralPath $n8nConfig -Force
    }
    Invoke-Compose start n8n
    $n8nWasStopped = $false

    $projectDataRoot = Join-Path $target 'project-data'
    $components = [ordered]@{}
    $components['data/documents'] = Copy-DirectorySnapshot (Join-Path $projectRoot 'data\documents') (Join-Path $projectDataRoot 'data\documents')
    $components['data/analysis_context'] = Copy-DirectorySnapshot (Join-Path $projectRoot 'data\analysis_context') (Join-Path $projectDataRoot 'data\analysis_context')
    $components['data/digests'] = Copy-DirectorySnapshot (Join-Path $projectRoot 'data\digests') (Join-Path $projectDataRoot 'data\digests')
    $components['fiches'] = Copy-DirectorySnapshot (Join-Path $projectRoot 'fiches') (Join-Path $projectDataRoot 'fiches')
    $components['config'] = Copy-DirectorySnapshot (Join-Path $projectRoot 'config') (Join-Path $projectDataRoot 'config')
    $components['automation/prompts'] = Copy-DirectorySnapshot (Join-Path $projectRoot 'automation\prompts') (Join-Path $projectDataRoot 'automation\prompts')
    $components['automation/n8n/workflows'] = Copy-DirectorySnapshot (Join-Path $projectRoot 'automation\n8n\workflows') (Join-Path $projectDataRoot 'automation\n8n\workflows')

    $companyConfigRoot = Join-Path $target 'company-openclaw'
    New-Item -ItemType Directory -Path $companyConfigRoot | Out-Null
    $openclawConfigPath = Join-Path $companyRoot 'openclaw.json'
    $openclawConfig = Get-Content -Raw -LiteralPath $openclawConfigPath | ConvertFrom-Json
    $sanitized = ConvertTo-SanitizedValue $openclawConfig
    $sanitized | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $companyConfigRoot 'openclaw.sanitized.json') -Encoding utf8
    foreach ($helperName in @('start-company-gateway.cmd', 'company-tui.cmd', 'openclaw.cmd')) {
        $helper = Join-Path $companyRoot $helperName
        if (Test-Path -LiteralPath $helper -PathType Leaf) {
            Copy-Item -LiteralPath $helper -Destination (Join-Path $companyConfigRoot $helperName)
        }
    }

    if ($IncludeMailpit) {
        $mailpitContainer = (& docker compose ps -q mailpit).Trim()
        if ($mailpitContainer) {
            Invoke-Compose stop mailpit
            $mailpitWasStopped = $true
            Invoke-Docker cp "${mailpitContainer}:/data/mailpit.db" (Join-Path $target 'mailpit.db')
            Invoke-Compose start mailpit
            $mailpitWasStopped = $false
        }
    }

    @(
        'This backup intentionally contains no .env file or plaintext service secret.',
        'Provide these values separately before a restore:',
        '- POSTGRES_PASSWORD',
        '- PGADMIN_DEFAULT_PASSWORD',
        '- N8N_ENCRYPTION_KEY (must match the source instance to decrypt n8n credentials)',
        '- AUTOMATION_API_TOKEN',
        '- TELEGRAM_BOT_TOKEN, when Telegram is enabled',
        '- the company OpenClaw gateway token or a newly generated replacement'
    ) | Set-Content -LiteralPath (Join-Path $target 'SECRETS_REQUIRED.txt') -Encoding utf8

    $gitCommit = $null
    & git rev-parse --verify HEAD *> $null
    if ($LASTEXITCODE -eq 0) { $gitCommit = (& git rev-parse HEAD).Trim() }
    $manifest = [ordered]@{
        schema = 'onetech-backup-v2'
        created_at = (Get-Date).ToUniversalTime().ToString('o')
        source = [ordered]@{
            project_root = $projectRoot
            git_commit = $gitCommit
        }
        postgres = [ordered]@{
            dump = 'postgresql.dump'
            source_database = $postgresDatabase
            format = 'custom'
            table_counts = $tableCounts
        }
        n8n = [ordered]@{
            workflows = 'n8n-workflows.json'
            state = 'n8n-state'
            state_captured_while_stopped = $true
            encryption_key_included = $false
        }
        project_data = [ordered]@{
            root = 'project-data'
            components = $components
        }
        company_openclaw = [ordered]@{
            config = 'company-openclaw/openclaw.sanitized.json'
            secrets_redacted = $true
        }
        includes_mailpit = [bool]$IncludeMailpit
        required_secrets = @(
            'POSTGRES_PASSWORD', 'PGADMIN_DEFAULT_PASSWORD', 'N8N_ENCRYPTION_KEY',
            'AUTOMATION_API_TOKEN', 'TELEGRAM_BOT_TOKEN', 'OPENCLAW_GATEWAY_TOKEN'
        )
    }
    $manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $target 'manifest.json') -Encoding utf8

    $checksumEntries = @()
    foreach ($file in (Get-ChildItem -LiteralPath $target -Recurse -Force -File | Where-Object { $_.Name -notin @('INCOMPLETE', 'checksums.json') } | Sort-Object FullName)) {
        $checksumEntries += [ordered]@{
            path = Get-RelativeBackupPath -Root $target -FullName $file.FullName
            bytes = [long]$file.Length
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    [ordered]@{
        schema = 'onetech-checksums-v1'
        algorithm = 'SHA256'
        files = $checksumEntries
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $target 'checksums.json') -Encoding utf8

    Test-BackupPayload -BackupDirectory $target -PostgresContainer $postgresContainer
    Remove-Item -LiteralPath (Join-Path $target 'INCOMPLETE') -Force

    Write-Host "Sauvegarde creee et validee : $target" -ForegroundColor Green
    Write-Host "Fichiers controles par SHA-256 : $($checksumEntries.Count)"
    Write-Host 'Aucun .env, token OpenClaw ou fichier config n8n contenant la cle de chiffrement n a ete copie.'
}
catch {
    if ($target -and (Test-Path -LiteralPath $target)) {
        Write-Warning "Sauvegarde incomplete conservee pour diagnostic : $target"
    }
    throw
}
finally {
    if ($n8nWasStopped) { & docker compose start n8n | Out-Null }
    if ($mailpitWasStopped) { & docker compose start mailpit | Out-Null }
    Pop-Location
}
