[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$migrationDirectory = Join-Path $projectRoot 'database\init'

Push-Location $projectRoot
try {
    $runningServices = @(docker compose ps --services --status running)
    if ($LASTEXITCODE -ne 0 -or $runningServices -notcontains 'postgres') {
        throw 'Le service PostgreSQL doit etre demarre avec docker compose up -d.'
    }

    $migrations = @(Get-ChildItem -LiteralPath $migrationDirectory -Filter '*.sql' | Sort-Object Name)
    if ($migrations.Count -eq 0) {
        throw "Aucune migration SQL trouvee dans $migrationDirectory."
    }

    foreach ($migration in $migrations) {
        Write-Host "Application de $($migration.Name)..."
        Get-Content -LiteralPath $migration.FullName -Raw |
            docker compose exec -T postgres sh -lc 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

        if ($LASTEXITCODE -ne 0) {
            throw "La migration $($migration.Name) a echoue."
        }
    }

    Write-Host 'Schema PostgreSQL applique avec succes.' -ForegroundColor Green
}
finally {
    Pop-Location
}
