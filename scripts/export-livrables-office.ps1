[CmdletBinding()]
param(
    [string]$Workspace
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($Workspace)) {
    $Workspace = Split-Path -Parent $PSScriptRoot
}
$livrables = Join-Path $Workspace 'livrables'
$reportDocx = Join-Path $livrables 'RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.docx'
$reportHtml = Join-Path $livrables 'RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.html'
$reportPdf = Join-Path $livrables 'RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.pdf'
$reportPdfTmp = Join-Path $livrables 'RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.exporting.pdf'
$deckPptx = Join-Path $livrables 'PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pptx'
$deckPdf = Join-Path $livrables 'PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pdf'
$deckPdfTmp = Join-Path $livrables 'PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.exporting.pdf'

foreach ($temporaryPdf in @($reportPdfTmp, $deckPdfTmp)) {
    if (Test-Path -LiteralPath $temporaryPdf) {
        Remove-Item -LiteralPath $temporaryPdf -Force
    }
}

foreach ($path in @($reportDocx, $reportHtml, $deckPptx)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Livrable source introuvable : $path"
    }
}

$chromeCandidates = @(
    'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
)
$chrome = $chromeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $chrome) {
    throw 'Google Chrome est requis pour exporter le rapport PDF.'
}
$chromeProfile = Join-Path $Workspace '.tmp\chrome-report-export'
[void](New-Item -ItemType Directory -Force -Path $chromeProfile)
$reportUri = [System.Uri]::new($reportHtml).AbsoluteUri
$chromeArguments = @(
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-pdf-header-footer',
    "--user-data-dir=$chromeProfile",
    "--print-to-pdf=$reportPdfTmp",
    $reportUri
)
Write-Host 'Export du rapport HTML imprime en PDF...'
$chromeProcess = Start-Process -FilePath $chrome -ArgumentList $chromeArguments -Wait -PassThru -WindowStyle Hidden
if ($chromeProcess.ExitCode -ne 0) {
    throw "Chrome a retourne le code $($chromeProcess.ExitCode)."
}

if (-not (Test-Path -LiteralPath $reportPdfTmp)) {
    throw "Export PDF du rapport depuis Chrome échoué : $reportPdfTmp"
}
Move-Item -LiteralPath $reportPdfTmp -Destination $reportPdf -Force

$powerPoint = $null
$presentation = $null
try {
    Write-Host 'Ouverture de PowerPoint...'
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $presentation = $powerPoint.Presentations.Open($deckPptx, $true, $false, $false)
    # 32 = ppSaveAsPDF
    Write-Host 'Export de la presentation en PDF...'
    $presentation.SaveAs($deckPdfTmp, 32)
}
finally {
    if ($presentation) { $presentation.Close() }
    if ($powerPoint) { $powerPoint.Quit() }
    if ($presentation) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) }
    if ($powerPoint) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

if (-not (Test-Path -LiteralPath $deckPdfTmp)) {
    throw "Export PDF de la présentation depuis PowerPoint échoué : $deckPdfTmp"
}
Move-Item -LiteralPath $deckPdfTmp -Destination $deckPdf -Force

Get-Item -LiteralPath $reportPdf, $deckPdf |
    Select-Object FullName, Length, LastWriteTime
