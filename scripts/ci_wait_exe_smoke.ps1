# Wait for windowed Jobhuntsaver onefile smoke to finish.
# PyInstaller console=False parents can return before the child writes SMOKE_TEST_OK;
# never treat process exit alone as success — poll marker + per-run token.
param(
    [Parameter(Mandatory = $true)][string]$ExePath,
    [Parameter(Mandatory = $true)][string]$LocalAppData,
    [string]$ExpectedDbSubstring = "",
    [int]$TimeoutSec = 180
)

$ErrorActionPreference = "Stop"

function Stop-JobhuntsaverProcesses {
    Get-Process -Name "Jobhuntsaver" -ErrorAction SilentlyContinue | ForEach-Object {
        try { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
    Start-Sleep -Milliseconds 400
}

$markerApp = Join-Path $LocalAppData "Jobhuntsaver\smoke_test_result.txt"
$markerDist = Join-Path (Split-Path -Parent $ExePath) "smoke_test_result.txt"
$token = [guid]::NewGuid().ToString("N")

Stop-JobhuntsaverProcesses
Remove-Item $markerApp, $markerDist -Force -ErrorAction SilentlyContinue

$env:LOCALAPPDATA = $LocalAppData
$env:JOBHUNTSAVER_SMOKE_TEST = "1"
$env:JOBHUNTSAVER_SMOKE_TOKEN = $token
if (-not $env:QT_QPA_PLATFORM) { $env:QT_QPA_PLATFORM = "offscreen" }

$proc = Start-Process -FilePath $ExePath -PassThru -WindowStyle Hidden
$deadline = (Get-Date).AddSeconds($TimeoutSec)
$finalText = $null

while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 400
    foreach ($marker in @($markerApp, $markerDist)) {
        if (-not (Test-Path $marker)) { continue }
        $text = Get-Content $marker -Raw -ErrorAction SilentlyContinue
        if (-not $text) { continue }
        if ($text -match ("token=" + [regex]::Escape($token)) -and $text -match "FAIL:") {
            Write-Host $text
            Stop-JobhuntsaverProcesses
            throw "EXE smoke reported FAIL (marker=$marker)"
        }
        if ($text -match ("token=" + [regex]::Escape($token)) -and $text -match "SMOKE_TEST_OK") {
            if ($ExpectedDbSubstring -and ($text -notmatch [regex]::Escape($ExpectedDbSubstring))) {
                Write-Host $text
                Stop-JobhuntsaverProcesses
                throw "EXE smoke OK but db path missing expected substring '$ExpectedDbSubstring'"
            }
            $finalText = $text
            break
        }
    }
    if ($null -ne $finalText) { break }
}

if ($null -eq $finalText) {
    Stop-JobhuntsaverProcesses
    $appTxt = if (Test-Path $markerApp) { Get-Content $markerApp -Raw } else { "<missing>" }
    $distTxt = if (Test-Path $markerDist) { Get-Content $markerDist -Raw } else { "<missing>" }
    throw "EXE smoke timeout after ${TimeoutSec}s. appdata=$appTxt dist=$distTxt"
}

# Allow child to exit; force-kill leftovers so the next smoke is isolated.
$exitDeadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $exitDeadline) {
    $alive = Get-Process -Name "Jobhuntsaver" -ErrorAction SilentlyContinue
    if (-not $alive) { break }
    Start-Sleep -Milliseconds 300
}
Stop-JobhuntsaverProcesses

Write-Host $finalText
Write-Output $finalText
