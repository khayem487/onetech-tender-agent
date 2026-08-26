[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$testDirectory = Join-Path $projectRoot 'database\tests'

Push-Location $projectRoot
try {
    $tests = @(Get-ChildItem -LiteralPath $testDirectory -Filter '*.sql' | Sort-Object Name)
    if ($tests.Count -eq 0) {
        throw "Aucun test SQL trouve dans $testDirectory."
    }

    foreach ($test in $tests) {
        Write-Host "Execution de $($test.Name)..."
        Get-Content -LiteralPath $test.FullName -Raw |
            docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U onetech -d onetech_ao

        if ($LASTEXITCODE -ne 0) {
            throw "Le test $($test.Name) a echoue."
        }
    }

    Write-Host 'Tous les tests PostgreSQL ont reussi.' -ForegroundColor Green
}
finally {
    Pop-Location
}
