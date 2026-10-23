<#
  Plant database updater.

  Put this script (and "Update Plant Database.cmd") in the folder that holds the release zips,
  for example C:\Users\Ethan\Documents\Claude\Plants, next to the plant-database folder.
  Double-click "Update Plant Database.cmd", or run it from PowerShell:

      powershell -ExecutionPolicy Bypass -File .\update-plant-database.ps1

  What it does:
    1. Finds the newest plant-database-vX.Y.Z-*.zip in this folder.
    2. Compares it with the version installed and the version running.
    3. Asks the running app for a backup (Backups page), or copies the database itself if the app is too old to do that.
    4. Unzips the release and copies it over the plant-database folder. Your data and backups folders are never touched.
    5. Runs "docker compose up -d --build" and waits until the new version answers.

  Options:
    -Yes              Do not ask before updating.
    -Force            Re-apply the newest zip even if it is already installed.
    -SkipBackup       Do not make a backup first (not recommended).
    -RemoveOldImage   Delete the previous version's Docker image afterwards to save disk space.
    -Password <text>  Only if you set PLANTDB_PASSWORD in docker-compose.yml.
    -Url <address>    Where the app answers (default http://localhost:8080).
    -ZipFolder, -AppFolder   Other locations, if you moved things.

  Works with Windows PowerShell 5.1 (built into Windows) and PowerShell 7.
#>
[CmdletBinding()]
param(
    [string]$ZipFolder = $PSScriptRoot,
    [string]$AppFolder = '',
    [string]$Url = 'http://localhost:8080',
    [string]$Password = '',
    [switch]$Yes,
    [switch]$Force,
    [switch]$SkipBackup,
    [switch]$RemoveOldImage
)

$ErrorActionPreference = 'Stop'
if (-not $AppFolder) { $AppFolder = Join-Path $ZipFolder 'plant-database' }
$LogFile = Join-Path $ZipFolder 'update-log.txt'

function Say([string]$text, [string]$color = 'Gray') { Write-Host $text -ForegroundColor $color; Add-Content -Path $LogFile -Value ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $text) }
function Step([string]$text) { Say ''; Say ("== " + $text) 'Cyan' }
function Fail([string]$text) { Say ("STOPPED: " + $text) 'Red'; Say 'Your data folder was not touched. See update-log.txt for details.' 'Yellow'; exit 1 }

function Headers {
    $h = @{ 'X-Editor' = 'Updater' }
    if ($Password) { $h['Authorization'] = 'Basic ' + [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("updater:$Password")) }
    return $h
}
function Running-Version {
    try { return (Invoke-RestMethod -Uri "$Url/api/version" -Headers (Headers) -TimeoutSec 5).version } catch { return $null }
}
# Run docker/robocopy with their messages logged. Windows PowerShell 5.1 treats any text a program
# writes to stderr as an error, and docker writes its normal progress there, so relax that here.
function Native([scriptblock]$sb) {
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { & $sb 2>&1 | ForEach-Object { $l = "$_".Trim(); if ($l) { Say ("  " + $l) } } } finally { $ErrorActionPreference = $old }
    return $LASTEXITCODE
}
function Docker-Ready {
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { docker info --format '{{.ServerVersion}}' 2>&1 | Out-Null; return ($LASTEXITCODE -eq 0) } catch { return $false } finally { $ErrorActionPreference = $old }
}

Say ''
Say ('Plant database updater, ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')) 'Green'

# ---- 1. newest zip -------------------------------------------------------------------------------
Step 'Looking for the newest release zip'
$zips = @()
foreach ($f in Get-ChildItem -Path $ZipFolder -Filter 'plant-database-v*.zip' -File) {
    if ($f.Name -match '^plant-database-v(\d+)\.(\d+)\.(\d+)-(\d{8})-(\d{4})\.zip$') {
        $zips += [pscustomobject]@{ File = $f; Version = [version]("{0}.{1}.{2}" -f $Matches[1], $Matches[2], $Matches[3]); Stamp = $Matches[4] + $Matches[5] }
    }
}
if ($zips.Count -eq 0) { Fail "No plant-database-vX.Y.Z-YYYYMMDD-HHMM.zip found in $ZipFolder" }
$latest = $zips | Sort-Object Version, Stamp | Select-Object -Last 1
Say ("Newest zip: {0} (version {1})" -f $latest.File.Name, $latest.Version)

# ---- 2. what is installed and running -------------------------------------------------------------
if (-not (Test-Path (Join-Path $AppFolder 'docker-compose.yml'))) { Fail "The app folder was not found: $AppFolder" }
$installed = $null
$vf = Join-Path $AppFolder 'VERSION'
if (Test-Path $vf) { $installed = (Get-Content $vf -Raw).Trim() }
$running = Running-Version
Say ("Installed files: {0}" -f $(if ($installed) { $installed } else { 'unknown' }))
Say ("Running app:     {0}" -f $(if ($running) { $running } else { 'not answering at ' + $Url }))

$upToDate = $installed -and ([version]$installed -ge $latest.Version) -and ($running -eq $installed)
if ($upToDate -and -not $Force) {
    Say ("Already up to date (version {0}). Nothing to do. Use -Force to re-apply it anyway." -f $installed) 'Green'
    exit 0
}
if ($installed -and ([version]$installed -gt $latest.Version) -and -not $Force) {
    Fail ("The installed version ({0}) is newer than the newest zip ({1}). Use -Force if you really want to go back." -f $installed, $latest.Version)
}
if (-not $Yes) {
    $answer = Read-Host ("Update to {0}? Type Y and press Enter" -f $latest.Version)
    if ($answer -notmatch '^(y|yes)$') { Say 'Cancelled. Nothing was changed.' 'Yellow'; exit 0 }
}

# ---- 3. Docker ---------------------------------------------------------------------------------
Step 'Checking Docker'
if (-not (Docker-Ready)) {
    $dd = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if ($env:ProgramFiles -and (Test-Path $dd)) {
        Say 'Docker is not running. Starting Docker Desktop and waiting up to 3 minutes...' 'Yellow'
        Start-Process $dd | Out-Null
        $t0 = Get-Date
        while (-not (Docker-Ready)) {
            if (((Get-Date) - $t0).TotalSeconds -gt 180) { Fail 'Docker Desktop did not start within 3 minutes. Start it yourself and run the updater again.' }
            Start-Sleep -Seconds 5
        }
    } else { Fail 'Docker is not running. Start Docker Desktop and run the updater again.' }
}
Say 'Docker is running.' 'Green'

# ---- 4. backup ---------------------------------------------------------------------------------
if ($SkipBackup) { Say 'Skipping the backup (-SkipBackup).' 'Yellow' }
else {
    Step 'Making a backup first'
    $made = $false
    if ($running) {
        try {
            $body = @{ wait = $true; kind = 'update'; note = ("Before update to {0}" -f $latest.Version) } | ConvertTo-Json
            $r = Invoke-RestMethod -Method Post -Uri "$Url/api/backups" -Headers (Headers) -ContentType 'application/json' -Body $body -TimeoutSec 600
            Say ("Backup made by the app: backups\{0}" -f $r.file) 'Green'
            $made = $true
        } catch { Say ('The app could not make the backup (' + $_.Exception.Message + '). Copying the database instead.') 'Yellow' }
    }
    if (-not $made) {
        # the app is too old for the Backups page, or not running: stop it so the database file is complete, then copy it
        Push-Location $AppFolder
        Native { docker compose stop } | Out-Null
        Pop-Location
        $db = Join-Path $AppFolder 'data\plants.db'
        if (-not (Test-Path $db)) { $db = Join-Path (Join-Path $AppFolder 'data') 'plants.db' }
        if (Test-Path $db) {
            $bdir = Join-Path $AppFolder 'backups'
            New-Item -ItemType Directory -Force -Path $bdir | Out-Null
            $dest = Join-Path $bdir ("plants-before-{0}-{1}.db" -f $latest.Version, (Get-Date -Format 'yyyyMMdd-HHmmss'))
            Copy-Item $db $dest
            Say ("Database copied to backups\{0}" -f (Split-Path $dest -Leaf)) 'Green'
        } else { Say 'No database file found yet (new install?), so there is nothing to back up.' 'Yellow' }
    }
}

# ---- 5. unzip and copy over --------------------------------------------------------------------
Step ('Unpacking ' + $latest.File.Name)
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('plantdb-update-' + (Get-Date -Format 'yyyyMMddHHmmss'))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
try {
    Expand-Archive -Path $latest.File.FullName -DestinationPath $tmp -Force
    $src = Join-Path $tmp 'plant-database'
    $newVersion = (Get-Content (Join-Path $src 'VERSION') -Raw).Trim()
    if ($newVersion -ne $latest.Version.ToString()) { Fail ("The zip says version {0} inside but {1} in its name." -f $newVersion, $latest.Version) }

    Step 'Copying the new files over the old ones (data and backups are left alone)'
    if (Get-Command robocopy -ErrorAction SilentlyContinue) {
        $rc = Native { robocopy $src $AppFolder /E /XD (Join-Path $src 'data') (Join-Path $src 'backups') /R:2 /W:2 /NFL /NDL /NJH /NP }
        if ($rc -ge 8) { Fail ("Copying failed (robocopy code {0}). Close any program that has files in the plant-database folder open and try again." -f $rc) }
    } else {
        Get-ChildItem -Path $src -Force | Where-Object { $_.Name -notin @('data', 'backups') } | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $AppFolder -Recurse -Force
        }
    }
    Say ("Files updated to version {0}." -f $newVersion) 'Green'

    # keep this updater current: copy the newest copy of itself next to the zips
    foreach ($n in @('update-plant-database.ps1', 'Update Plant Database.cmd')) {
        $newer = Join-Path (Join-Path $src 'tools') $n
        if (Test-Path $newer) { Copy-Item $newer (Join-Path $ZipFolder $n) -Force }
    }
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}

# ---- 6. rebuild and restart ------------------------------------------------------------------------
Step 'Building and starting the new version (docker compose up -d --build)'
Push-Location $AppFolder
$code = Native { docker compose up -d --build }
Pop-Location
if ($code -ne 0) { Say ("docker compose failed (code {0}). The new files are in place; fix the error above and run 'docker compose up -d --build' in the plant-database folder." -f $code) 'Red'; exit 1 }

Step 'Waiting for the app to answer'
$t0 = Get-Date
do {
    Start-Sleep -Seconds 3
    $now = Running-Version
} while ($now -ne $newVersion -and ((Get-Date) - $t0).TotalSeconds -lt 180)
if ($now -eq $newVersion) { Say ("Done. Plant record version {0} is running at {1}" -f $now, $Url) 'Green' }
else { Say ("The app has not answered with version {0} yet (it says: {1}). Give it a minute, then check {2}" -f $newVersion, $(if ($now) { $now } else { 'nothing' }), $Url) 'Yellow' }

# ---- 7. tidy up old image ------------------------------------------------------------------------
if ($installed -and $installed -ne $newVersion) {
    $old = "plant-database:$installed"
    $doRemove = $RemoveOldImage
    if (-not $doRemove -and -not $Yes) { $doRemove = (Read-Host ("Delete the old Docker image {0} to free disk space? Type Y and press Enter, or just Enter to keep it" -f $old)) -match '^(y|yes)$' }
    if ($doRemove) {
        if ((Native { docker image rm $old }) -eq 0) { Say ("Removed the old image {0}." -f $old) 'Green' }
    }
}
Say ("Log saved to " + $LogFile)
exit 0
