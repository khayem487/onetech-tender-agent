[CmdletBinding()]
param()

Set-StrictMode -Version Latest
foreach ($taskName in @('OneTech Tender Agent Stack', 'OneTech Tender Agent Watchdog')) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Tache Windows supprimee : $taskName"
}
