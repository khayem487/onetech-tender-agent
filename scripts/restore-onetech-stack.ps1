[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDirectory,

    [string]$TargetDatabase,
    [switch]$RestorePostgres,
    [switch]$ReplaceTargetDatabase,
    [switch]$AllowInPlaceDatabaseRestore,

    [switch]$RestoreN8nState,
    [switch]$RestoreN8nWorkflows,

    [switch]$RestoreProjectData,
    [string]$ProjectDataTargetRoot,

    [switch]$RestoreCompanyConfig,
    [string]$CompanyConfigTargetFile,

    [Parameter(Mandatory = $true)]
    [string]$ConfirmRestore
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$companyRoot = (Resolve-Path (Join-Path $projectRoot '..')).Path
$backup = (Resolve-Path -LiteralPath $BackupDirectory).Path

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & docker compose @Arguments
    if ($LASTEXITCODE -ne 0) { throw "docker compose $($Arguments -join ' ') a echoue." }
}

function Invoke-Docker {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "docker $($Arguments -join ' ') a echoue." }
}

function Get-ProjectEnvValue([string]$Name) {
    $match = Get-Content -LiteralPath (Join-Path $projectRoot '.env') |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=(.*)$" } |
        Select-Object -First 1
    if (-not $match) { throw "Variable .env manquante : $Name" }
    return (($match -split '=', 2)[1]).Trim().Trim('"').Trim("'")
}

function Get-RelativePathSafe {
    param([string]$Root, [string]$FullName)
    return $FullName.Substring($Root.Length).TrimStart('\', '/')
}

function Resolve-SafeTargetRoot([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    $driveRoot = [IO.Path]::GetPathRoot($full).TrimEnd('\')
    if ($full -eq $driveRoot) { throw "Une racine de disque ne peut pas etre une cible de restauration : $full" }
    $userHome = [Environment]::GetFolderPath('UserProfile').TrimEnd('\')
    if ($full -eq $userHome) { throw 'Le profil utilisateur entier ne peut pas etre une cible de restauration.' }
    return $full
}

function Test-BackupIntegrity {
    param([string]$BackupRoot)

    if (Test-Path -LiteralPath (Join-Path $BackupRoot 'INCOMPLETE')) {
        throw 'Cette sauvegarde est marquee INCOMPLETE.'
    }
    $manifestPath = Join-Path $BackupRoot 'manifest.json'
    $checksumsPath = Join-Path $BackupRoot 'checksums.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'manifest.json est absent.' }
    if (-not (Test-Path -LiteralPath $checksumsPath -PathType Leaf)) { throw 'checksums.json est absent.' }

    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    if ($manifest.schema -ne 'onetech-backup-v2') { throw "Schema non pris en charge : $($manifest.schema)" }
    $checksumDocument = Get-Content -Raw -LiteralPath $checksumsPath | ConvertFrom-Json
    if ($checksumDocument.schema -ne 'onetech-checksums-v1') { throw 'Schema de checksums invalide.' }

    $listed = @{}
    foreach ($entry in $checksumDocument.files) {
        $relative = ([string]$entry.path) -replace '\\', '/'
        if ([IO.Path]::IsPathRooted($relative) -or $relative -match '(^|/)\.\.(/|$)') {
            throw "Chemin non sur dans checksums.json : $relative"
        }
        $listed[$relative.ToLowerInvariant()] = $true
        $file = Join-Path $BackupRoot ($relative -replace '/', '\')
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Fichier manquant : $relative" }
        if ((Get-Item -LiteralPath $file).Length -ne [long]$entry.bytes) { throw "Taille invalide : $relative" }
        $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne ([string]$entry.sha256).ToLowerInvariant()) { throw "Checksum invalide : $relative" }
    }

    foreach ($file in (Get-ChildItem -LiteralPath $BackupRoot -Recurse -Force -File | Where-Object { $_.Name -ne 'checksums.json' })) {
        $relative = (Get-RelativePathSafe -Root $BackupRoot -FullName $file.FullName) -replace '\\', '/'
        if (-not $listed.ContainsKey($relative.ToLowerInvariant())) {
            throw "Fichier non reference par checksums.json : $relative"
        }
    }

    Get-Content -Raw -LiteralPath (Join-Path $BackupRoot 'n8n-workflows.json') | ConvertFrom-Json | Out-Null
    if (-not (Test-Path -LiteralPath (Join-Path $BackupRoot 'n8n-state\database.sqlite') -PathType Leaf)) {
        throw 'n8n-state/database.sqlite est absent.'
    }
    if (Test-Path -LiteralPath (Join-Path $BackupRoot 'n8n-state\config')) {
        throw 'Sauvegarde refusee : n8n-state/config contient normalement une cle secrete.'
    }
    return $manifest
}

function Wait-PostgresHealthy {
    param([int]$TimeoutSeconds = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $health = (& docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' onetech-postgres 2>$null).Trim()
        if ($LASTEXITCODE -eq 0 -and $health -eq 'healthy') { return }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw 'PostgreSQL n est pas devenu healthy dans le delai imparti.'
}

function Test-DatabaseName([string]$Name) {
    if (-not $Name -or $Name -notmatch '^[A-Za-z_][A-Za-z0-9_]{0,62}$') {
        throw "Nom de base invalide : '$Name'. Utilise uniquement lettres, chiffres et underscores."
    }
}

function Test-DatabaseExists {
    param([string]$User, [string]$Database)
    Test-DatabaseName $Database
    $value = "$(& docker compose exec -T postgres psql -U $User -d postgres -At -c "SELECT 1 FROM pg_database WHERE datname = '$Database';")"
    if ($LASTEXITCODE -ne 0) { throw 'Verification de la base cible echouee.' }
    return $value.Trim() -eq '1'
}

function Remove-ExactDatabase {
    param([string]$User, [string]$Database)
    Test-DatabaseName $Database
    & docker compose exec -T postgres psql -U $User -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$Database' AND pid <> pg_backend_pid();" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Arret des connexions a $Database echoue." }
    Invoke-Compose exec -T postgres dropdb --if-exists -U $User $Database
}

function New-ExactDatabase {
    param([string]$User, [string]$Database)
    Test-DatabaseName $Database
    Invoke-Compose exec -T postgres createdb -U $User $Database
}

function New-PreRestoreDatabaseDump {
    param([string]$Container, [string]$User, [string]$Database)
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $safetyRoot = Join-Path $projectRoot 'backups\pre-restore-safety'
    New-Item -ItemType Directory -Force -Path $safetyRoot | Out-Null
    $local = Join-Path $safetyRoot "pre-restore-$Database-$stamp.dump"
    $remote = "/tmp/pre-restore-$stamp.dump"
    try {
        Invoke-Compose exec -T postgres pg_dump -Fc -U $User "--dbname=$Database" -f $remote
        Invoke-Docker cp "${Container}:$remote" $local
    }
    finally {
        & docker compose exec -T postgres sh -lc "rm -f '$remote'" | Out-Null
    }
    Write-Host "Dump de securite cree : $local" -ForegroundColor Yellow
}

function Restore-FileTreeSafely {
    param(
        [string]$SourceRoot,
        [string]$TargetRoot,
        [string]$SafetyRoot
    )

    if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container)) { return }
    New-Item -ItemType Directory -Force -Path $TargetRoot | Out-Null
    foreach ($directory in (Get-ChildItem -LiteralPath $SourceRoot -Recurse -Force -Directory | Sort-Object FullName)) {
        $relative = Get-RelativePathSafe -Root $SourceRoot -FullName $directory.FullName
        $destination = Join-Path $TargetRoot $relative
        if (Test-Path -LiteralPath $destination -PathType Leaf) {
            throw "Conflit fichier/dossier pendant la restauration : $destination"
        }
        New-Item -ItemType Directory -Force -Path $destination | Out-Null
    }
    foreach ($file in (Get-ChildItem -LiteralPath $SourceRoot -Recurse -Force -File | Sort-Object FullName)) {
        $relative = Get-RelativePathSafe -Root $SourceRoot -FullName $file.FullName
        $destination = Join-Path $TargetRoot $relative
        if (Test-Path -LiteralPath $destination -PathType Container) {
            throw "Conflit dossier/fichier pendant la restauration : $destination"
        }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
        if (Test-Path -LiteralPath $destination -PathType Leaf) {
            $sourceHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
            $targetHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
            if ($sourceHash -eq $targetHash) { continue }
            $safetyFile = Join-Path $SafetyRoot $relative
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $safetyFile) | Out-Null
            Move-Item -LiteralPath $destination -Destination $safetyFile
        }
        Copy-Item -LiteralPath $file.FullName -Destination $destination
    }
}

$selected = @(@($RestorePostgres, $RestoreN8nState, $RestoreN8nWorkflows, $RestoreProjectData, $RestoreCompanyConfig) | Where-Object { $_ })
if ($selected.Count -eq 0) { throw 'Selectionne au moins un composant a restaurer.' }
if ($RestoreN8nState -and $RestoreN8nWorkflows) {
    throw 'Choisis RestoreN8nState (restauration exacte) ou RestoreN8nWorkflows (import seulement), pas les deux.'
}
if ($RestorePostgres) { Test-DatabaseName $TargetDatabase }
if ($RestoreProjectData -and -not $ProjectDataTargetRoot) { throw 'ProjectDataTargetRoot est obligatoire avec RestoreProjectData.' }
if ($RestoreCompanyConfig -and -not $CompanyConfigTargetFile) { throw 'CompanyConfigTargetFile est obligatoire avec RestoreCompanyConfig.' }

$activeDatabase = Get-ProjectEnvValue 'POSTGRES_DB'
$inPlace = $RestorePostgres -and ($TargetDatabase -eq $activeDatabase)
if ($inPlace -and -not $AllowInPlaceDatabaseRestore) {
    throw "La restauration vers la base active $activeDatabase est bloquee. Utilise AllowInPlaceDatabaseRestore explicitement."
}
if ($inPlace -and -not $ReplaceTargetDatabase) {
    throw 'ReplaceTargetDatabase est obligatoire pour une restauration en place.'
}
$confirmationLabel = if ($inPlace) { "RESTORE-IN-PLACE:$TargetDatabase" } elseif ($RestorePostgres) { "RESTORE:$TargetDatabase" } else { 'RESTORE:COMPONENTS' }
if ($ConfirmRestore -cne $confirmationLabel) {
    throw "Confirmation invalide. Valeur exacte requise : $confirmationLabel"
}

Push-Location $projectRoot
$stoppedServices = @()
$n8nStateRestored = $false
try {
    $manifest = Test-BackupIntegrity -BackupRoot $backup

    Invoke-Compose up --detach postgres
    Wait-PostgresHealthy
    $postgresContainer = (& docker compose ps -q postgres).Trim()
    $postgresUser = Get-ProjectEnvValue 'POSTGRES_USER'
    if (-not $postgresContainer) { throw 'Conteneur PostgreSQL introuvable.' }

    $dump = Join-Path $backup 'postgresql.dump'
    $remoteValidationDump = "/tmp/onetech-restore-validate-$([guid]::NewGuid().ToString('N')).dump"
    try {
        Invoke-Docker cp $dump "${postgresContainer}:$remoteValidationDump"
        & docker compose exec -T postgres pg_restore --list $remoteValidationDump | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Le dump PostgreSQL est invalide.' }
    }
    finally {
        & docker compose exec -T postgres sh -lc "rm -f '$remoteValidationDump'" | Out-Null
    }

    $runningBefore = @(& docker compose ps --services --status running)
    if ($inPlace) {
        New-PreRestoreDatabaseDump -Container $postgresContainer -User $postgresUser -Database $activeDatabase
        foreach ($service in @('ao-worker', 'n8n')) {
            if ($runningBefore -contains $service) {
                Invoke-Compose stop $service
                $stoppedServices += $service
            }
        }
    }

    if ($RestorePostgres) {
        $exists = Test-DatabaseExists -User $postgresUser -Database $TargetDatabase
        if ($exists -and -not $ReplaceTargetDatabase) {
            throw "La base cible $TargetDatabase existe deja. Ajoute ReplaceTargetDatabase pour la remplacer explicitement."
        }
        if ($exists) { Remove-ExactDatabase -User $postgresUser -Database $TargetDatabase }
        New-ExactDatabase -User $postgresUser -Database $TargetDatabase

        $remoteDump = "/tmp/onetech-restore-$([guid]::NewGuid().ToString('N')).dump"
        try {
            Invoke-Docker cp $dump "${postgresContainer}:$remoteDump"
            Invoke-Compose exec -T postgres pg_restore --no-owner --no-privileges --exit-on-error -U $postgresUser "--dbname=$TargetDatabase" $remoteDump
        }
        finally {
            & docker compose exec -T postgres sh -lc "rm -f '$remoteDump'" | Out-Null
        }

        foreach ($property in $manifest.postgres.table_counts.PSObject.Properties) {
            $table = $property.Name
            if ($table -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { throw "Table inattendue dans le manifeste : $table" }
            $actual = (& docker compose exec -T postgres psql -U $postgresUser -d $TargetDatabase -At -c "SELECT count(*) FROM public.`"$table`";").Trim()
            if ($LASTEXITCODE -ne 0 -or [long]$actual -ne [long]$property.Value) {
                throw "Comptage restaure invalide pour $table : attendu $($property.Value), obtenu $actual"
            }
        }
        Write-Host "PostgreSQL restaure et verifie dans la base cible : $TargetDatabase" -ForegroundColor Green
    }

    if ($RestoreN8nState) {
        Get-ProjectEnvValue 'N8N_ENCRYPTION_KEY' | Out-Null
        $n8nState = Join-Path $backup 'n8n-state'
        if (-not (Test-Path -LiteralPath (Join-Path $n8nState 'database.sqlite') -PathType Leaf)) {
            throw 'Etat n8n invalide : database.sqlite est absent.'
        }
        Invoke-Compose up --detach n8n
        $n8nContainer = (& docker compose ps -q n8n).Trim()
        if (-not $n8nContainer) { throw 'Conteneur n8n introuvable.' }
        $n8nWasRunning = @(& docker compose ps --services --status running) -contains 'n8n'
        if ($n8nWasRunning) { Invoke-Compose stop n8n }
        $image = (& docker inspect --format '{{.Config.Image}}' $n8nContainer).Trim()
        $helperName = "onetech-n8n-restore-$([guid]::NewGuid().ToString('N').Substring(0, 12))"
        try {
            Invoke-Docker create --name $helperName --volumes-from $n8nContainer --entrypoint sh $image -c 'sleep 600' | Out-Null
            Invoke-Docker start $helperName | Out-Null
            Invoke-Docker exec $helperName mkdir -p /tmp/n8n-state
            Invoke-Docker cp "$n8nState/." "${helperName}:/tmp/n8n-state"
            $safetyName = ".restore-safety-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            $script = @"
set -eu
safety=/home/node/.n8n/$safetyName
mkdir -p "`$safety"
for entry in /home/node/.n8n/* /home/node/.n8n/.[!.]* /home/node/.n8n/..?*; do
  [ -e "`$entry" ] || continue
  [ "`$entry" = "`$safety" ] && continue
  mv "`$entry" "`$safety/"
done
cp -a /tmp/n8n-state/. /home/node/.n8n/
rm -f /home/node/.n8n/config
chown -R node:node /home/node/.n8n
test -s /home/node/.n8n/database.sqlite
"@
            Invoke-Docker exec $helperName sh -c $script
            $n8nStateRestored = $true
            Write-Host "Etat n8n restaure; ancien etat conserve dans $safetyName." -ForegroundColor Green
        }
        finally {
            & docker rm -f $helperName | Out-Null
        }
        if ($n8nWasRunning -and $n8nStateRestored) { Invoke-Compose start n8n }
    }

    if ($RestoreN8nWorkflows) {
        $workflows = Join-Path $backup 'n8n-workflows.json'
        Invoke-Compose up --detach n8n
        $n8nContainer = (& docker compose ps -q n8n).Trim()
        $remoteWorkflows = "/tmp/onetech-restore-workflows-$([guid]::NewGuid().ToString('N')).json"
        try {
            Invoke-Docker cp $workflows "${n8nContainer}:$remoteWorkflows"
            Invoke-Compose exec -T n8n n8n import:workflow --input=$remoteWorkflows
        }
        finally {
            & docker compose exec -T n8n rm -f $remoteWorkflows | Out-Null
        }
    }

    if ($RestoreProjectData) {
        $targetRoot = Resolve-SafeTargetRoot $ProjectDataTargetRoot
        New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
        $safetyRoot = Join-Path $targetRoot ".onetech-restore-safety\$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Restore-FileTreeSafely -SourceRoot (Join-Path $backup 'project-data') -TargetRoot $targetRoot -SafetyRoot $safetyRoot
        Write-Host "Donnees projet restaurees vers : $targetRoot" -ForegroundColor Green
        if (Test-Path -LiteralPath $safetyRoot) { Write-Host "Fichiers remplaces conserves dans : $safetyRoot" -ForegroundColor Yellow }
    }

    if ($RestoreCompanyConfig) {
        $sourceConfig = Join-Path $backup 'company-openclaw\openclaw.sanitized.json'
        $activeConfig = (Join-Path $companyRoot 'openclaw.json')
        $targetConfig = [IO.Path]::GetFullPath($CompanyConfigTargetFile)
        if ($targetConfig -eq $activeConfig) {
            throw 'Le snapshot OpenClaw est sanitise et ne peut pas remplacer directement openclaw.json. Choisis un fichier de fusion distinct.'
        }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $targetConfig) | Out-Null
        if (Test-Path -LiteralPath $targetConfig -PathType Leaf) {
            $safetyFile = "$targetConfig.pre-restore-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            Move-Item -LiteralPath $targetConfig -Destination $safetyFile
            Write-Host "Ancienne cible conservee : $safetyFile" -ForegroundColor Yellow
        }
        Copy-Item -LiteralPath $sourceConfig -Destination $targetConfig
        Write-Host "Configuration OpenClaw sanitisee restauree vers : $targetConfig" -ForegroundColor Green
    }

    foreach ($service in $stoppedServices) {
        Invoke-Compose start $service
    }
    $stoppedServices = @()
    Write-Host 'Restauration terminee et controles de coherence reussis.' -ForegroundColor Green
}
finally {
    foreach ($service in $stoppedServices) {
        & docker compose start $service | Out-Null
    }
    Pop-Location
}
