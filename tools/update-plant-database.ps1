<#
  Plant database updater.

  Put this script (and "Update Plant Database.cmd") next to the plant-database folder,
  for example in C:\Users\Ethan\Documents\Claude\Plants. Since 1.12.2 the release zips and photo packs live in the
  versions_plant-database folder beside it. Zips saved straight into the Plants folder are moved there each time this runs.
  Double-click "Update Plant Database.cmd", or run it from PowerShell:

      powershell -ExecutionPolicy Bypass -File .\update-plant-database.ps1

  What it does:
    1. Moves any plant-database-*.zip in this folder into versions_plant-database, then finds the newest
       plant-database-vX.Y.Z-*.zip there.
    2. Compares it with the version installed and the version running.
    3. Asks the running app for a backup (Backups page), or copies the database itself if the app is too old to do that.
    4. Unzips the release and copies it over the plant-database folder. Your data and backups folders are never touched.
    5. Adds plant photos from any photo pack (plant-database-photos-*.zip) in versions_plant-database that the release needs
       and the plant-database folder does not have yet. From 1.8.0 photos travel in these packs, so release zips stay small.
    6. Builds the new version on a freshly downloaded base image (so security fixes arrive), fetches the newest Tailscale
       container, starts everything ("docker compose up -d") and waits until the new version answers.
       Since 1.12.1 the app itself picks which user it runs as each time it starts (README: "Which user the app runs as"),
       so the updater removes the docker-compose.override.yml that 1.12.0 wrote for that.
       If the app's port on this computer (8080) is busy, often because Plant record is still open in a browser, it says so,
       waits and tries again. If the port stays busy it says which program holds it and moves the app to a free port
       (saved as PLANTDB_PORT in plant-database\.env).

  Options:
    -Yes              Do not ask before updating.
    -Force            Re-apply the newest zip even if it is already installed.
    -SkipBackup       Do not make a backup first (not recommended).
    -RemoveOldImage   Delete the previous version's Docker image afterwards to save disk space.
    -Password <text>  Only if you set PLANTDB_PASSWORD in docker-compose.yml.
    -Url <address>    Where the app answers (default http://localhost:8080, or the port saved as PLANTDB_PORT in plant-database\.env).
    -WaitSeconds <n>  How long to wait for the new version to answer (default 180).
    -ZipFolder, -AppFolder, -VersionsFolder   Other locations, if you moved things (the folder holding plant-database,
                      the plant-database folder, and the folder for release zips and photo packs).

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
    [switch]$RemoveOldImage,
    [int]$WaitSeconds = 180,
    [string]$VersionsFolder = ''
)

$ErrorActionPreference = 'Stop'
if (-not $AppFolder) { $AppFolder = Join-Path $ZipFolder 'plant-database' }
if (-not $VersionsFolder) { $VersionsFolder = Join-Path $ZipFolder 'versions_plant-database' }   # 1.12.2: release zips and photo packs
$LogFile = Join-Path $ZipFolder 'update-log.txt'
# 1.12.1: settings kept in plant-database\.env (PLANTDB_PORT, PLANTDB_BIND and others), one NAME=value per line
$EnvFile = Join-Path $AppFolder '.env'
function Get-EnvValue([string]$name) {
    if (-not (Test-Path $EnvFile)) { return $null }
    foreach ($l in (Get-Content $EnvFile)) { if ($l -match ('^\s*' + [regex]::Escape($name) + '\s*=\s*(.*?)\s*$')) { return $Matches[1] } }
    return $null
}
function Set-EnvValue([string]$name, [string]$value) {
    $lines = @(); if (Test-Path $EnvFile) { $lines = @(Get-Content $EnvFile | Where-Object { $_ -notmatch ('^\s*' + [regex]::Escape($name) + '\s*=') }) }
    Set-Content -Path $EnvFile -Encoding ASCII -Value ($lines + "$name=$value")
}
$savedPort = Get-EnvValue 'PLANTDB_PORT'
if (-not $PSBoundParameters.ContainsKey('Url') -and $savedPort -match '^\d+$') { $Url = "http://localhost:$savedPort" }

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
    $__eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { & $sb 2>&1 | ForEach-Object { $l = "$_".Trim(); if ($l) { Say ("  " + $l) } } } finally { $ErrorActionPreference = $__eap }
    return $LASTEXITCODE
}
function JoinAll([string]$base, [string[]]$parts) { $p = $base; foreach ($x in $parts) { $p = Join-Path $p $x }; return $p }
# Photo packs the release in $root needs: packs with photos missing from both $root and the installed folder.
function Pending-Packs([string]$root) {
    $mf = JoinAll $root @('app', 'seed', 'photo-packs.json')
    if (-not (Test-Path $mf)) { return @() }
    $m = Get-Content $mf -Raw | ConvertFrom-Json
    $mine = JoinAll $AppFolder @('app', 'seed', 'photos'); $theirs = JoinAll $root @('app', 'seed', 'photos')
    $out = @()
    foreach ($pp in $m.packs.PSObject.Properties) {
        $miss = @($pp.Value.files | Where-Object { -not (Test-Path (Join-Path $mine $_)) -and -not (Test-Path (Join-Path $theirs $_)) })
        if ($miss.Count -eq 0) { continue }
        $pz = Join-Path $VersionsFolder $pp.Value.zip
        $out += [pscustomobject]@{ Name = $pp.Name; Zip = $pp.Value.zip; Path = $pz; Missing = $miss.Count; Present = (Test-Path $pz) }
    }
    return $out
}
function Docker-Ready {
    $__eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { docker info --format '{{.ServerVersion}}' 2>&1 | Out-Null; return ($LASTEXITCODE -eq 0) } catch { return $false } finally { $ErrorActionPreference = $__eap }
}

Say ''
Say ('Plant database updater, ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')) 'Green'

# ---- 1. newest zip -------------------------------------------------------------------------------
Step 'Looking for the newest release zip'
# 1.12.2: keep the Plants folder tidy. Release zips and photo packs (and the very first plant-database-1.zip style zips)
# go into versions_plant-database. A zip that is already there with the same size and contents is just removed here.
if (-not (Test-Path $VersionsFolder)) { New-Item -ItemType Directory -Path $VersionsFolder -Force | Out-Null; Say ("Made the folder " + $VersionsFolder) }
$moved = 0; $dupes = 0
foreach ($f in @(Get-ChildItem -Path $ZipFolder -Filter 'plant-database-*.zip' -File)) {
    $dest = Join-Path $VersionsFolder $f.Name
    if (Test-Path $dest) {
        $same = ((Get-Item $dest).Length -eq $f.Length) -and ((Get-FileHash $dest).Hash -eq (Get-FileHash $f.FullName).Hash)
        if ($same) { Remove-Item $f.FullName -Force; $dupes++ }
        else { Say ("Left {0} in place: a different file with that name is already in versions_plant-database." -f $f.Name) 'Yellow' }
        continue
    }
    Move-Item $f.FullName $dest; $moved++
}
if ($moved -or $dupes) { Say ("Moved {0} zip file(s) into versions_plant-database{1}." -f $moved, $(if ($dupes) { " (and removed $dupes copies that were already there)" } else { '' })) 'Green' }
$zips = @()
foreach ($f in Get-ChildItem -Path $VersionsFolder -Filter 'plant-database-v*.zip' -File) {
    if ($f.Name -match '^plant-database-v(\d+)\.(\d+)\.(\d+)-(\d{8})-(\d{4})\.zip$') {
        $zips += [pscustomobject]@{ File = $f; Version = [version]("{0}.{1}.{2}" -f $Matches[1], $Matches[2], $Matches[3]); Stamp = $Matches[4] + $Matches[5] }
    }
}
if ($zips.Count -eq 0) { Fail "No plant-database-vX.Y.Z-YYYYMMDD-HHMM.zip found in $VersionsFolder (or in $ZipFolder)" }
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
$photosOnly = $false
if ($upToDate -and -not $Force -and @(Pending-Packs $AppFolder | Where-Object { $_.Present }).Count) {
    Say 'Version is up to date, but photo packs for it have arrived in versions_plant-database: adding their photos.' 'Yellow'
    $upToDate = $false; $photosOnly = $true
}
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

    # photo packs this release needs (checked before anything is copied, so a missing pack changes nothing)
    $packs = @(Pending-Packs $src)
    $absent = @($packs | Where-Object { -not $_.Present })
    if ($absent.Count) {
        Say 'This release needs plant photos that are not in the plant-database folder yet, and these photo packs are not in versions_plant-database:' 'Yellow'
        foreach ($a in $absent) { Say ("  {0}  ({1} photos)" -f $a.Zip, $a.Missing) 'Yellow' }
        if (-not $Force -and -not $photosOnly) { Fail 'Save those photo packs in versions_plant-database (or the Plants folder) and run the updater again. Nothing has been changed. (To update without them, run it with -Force; the photos appear after you add the packs and run the updater again.)' }
        Say $(if ($photosOnly) { 'Adding the packs that are here now. Save the others next to the release zip and run the updater again.' } else { 'Carrying on without them (-Force).' }) 'Yellow'
    }

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

    foreach ($np in @($packs | Where-Object { $_.Present })) {
        Step ('Adding plant photos from ' + $np.Zip)
        $pt = Join-Path $tmp ('pack-' + $np.Name)
        Expand-Archive -Path $np.Path -DestinationPath $pt -Force
        $from = JoinAll $pt @('plant-database', 'app', 'seed', 'photos'); $to = JoinAll $AppFolder @('app', 'seed', 'photos')
        New-Item -ItemType Directory -Force -Path $to | Out-Null
        $n = 0
        Get-ChildItem -Path $from -File | ForEach-Object { $d = Join-Path $to $_.Name; if (-not (Test-Path $d)) { Copy-Item $_.FullName $d; $n++ } }
        Say ("{0} photos added." -f $n) 'Green'
    }

    # keep this updater current: copy the newest copy of itself next to the zips
    foreach ($n in @('update-plant-database.ps1', 'Update Plant Database.cmd')) {
        $newer = Join-Path (Join-Path $src 'tools') $n
        if (Test-Path $newer) { Copy-Item $newer (Join-Path $ZipFolder $n) -Force }
    }
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}

# ---- 6. rebuild and restart ------------------------------------------------------------------------
# Docker output as text (for reading the app's own log), with Windows PowerShell 5.1's error handling relaxed as in Native.
function Native-Text([scriptblock]$sb) {
    $__eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { $t = (& $sb 2>&1 | Out-String) } finally { $ErrorActionPreference = $__eap }
    return "$t"
}
function Wait-Version {
    $t0 = Get-Date
    do {
        Start-Sleep -Seconds 3
        $v = Running-Version
    } while ($v -ne $newVersion -and ((Get-Date) - $t0).TotalSeconds -lt $WaitSeconds)
    return $v
}
# docker output, logged line by line as in Native, and also kept as text
function Native-Capture([scriptblock]$sb) {
    $__eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $lines = New-Object System.Collections.Generic.List[string]
    try { & $sb 2>&1 | ForEach-Object { $l = "$_".Trim(); if ($l) { Say ("  " + $l); $lines.Add($l) } } } finally { $ErrorActionPreference = $__eap }
    return @{ code = $LASTEXITCODE; text = ($lines -join "`n") }
}
function Port-Free([int]$p) {
    try { $l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $p); $l.Start(); $l.Stop(); return $true } catch { return $false }
}
function Port-Owner([int]$p) {     # which program listens on this port (Windows only; empty elsewhere)
    try {
        $c = @(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction Stop)
        return (($c | ForEach-Object { try { (Get-Process -Id $_.OwningProcess -ErrorAction Stop).ProcessName } catch { "process $($_.OwningProcess)" } }) | Select-Object -Unique) -join ', '
    } catch { return '' }
}
# 1.12.1: start everything. If a port on this computer is busy, wait and try again (the old container can take a few seconds to
# let go of it); if it stays busy, move that port to a free one and save it in .env.
function Start-App {
    $svc = $script:Services                     # 1.18.0: empty means all of them
    $r = Native-Capture { docker compose up -d @svc }
    $waits = @(5, 10, 15, 30)
    for ($i = 0; $r.code -ne 0 -and $i -le $waits.Count; $i++) {
        if ($r.text -notmatch 'ports are not available|port is already allocated|address already in use|Only one usage of each socket address') { break }
        $busy = $null
        if ($r.text -match 'listen tcp\d?\s+[^\s]*?:(\d+):') { $busy = [int]$Matches[1] } elseif ($r.text -match 'Bind for [^\s]*?:(\d+) failed') { $busy = [int]$Matches[1] }
        if ($i -lt $waits.Count) {
            if ($i -eq 0) { Say ("Port {0} on this computer is still in use. If Plant record is open in a browser, close those tabs now." -f $busy) 'Yellow' }
            Say ("Port {0} on this computer is still in use. Waiting {1} seconds and trying again." -f $busy, $waits[$i]) 'Yellow'
            Start-Sleep -Seconds $waits[$i]
        } else {
            $owner = Port-Owner $busy
            $appPort = $(if ($savedPort -match '^\d+$') { [int]$savedPort } else { 8080 })
            $sensorPort = $(if ((Get-EnvValue 'PLANTDB_SENSOR_PORT') -match '^\d+$') { [int](Get-EnvValue 'PLANTDB_SENSOR_PORT') } else { 8082 })
            if ($busy -eq $appPort) { $var = 'PLANTDB_PORT'; $range = 8090..8099 } elseif ($busy -eq $sensorPort) { $var = 'PLANTDB_SENSOR_PORT'; $range = 8180..8189 } else { break }
            $free = $range | Where-Object { Port-Free $_ } | Select-Object -First 1
            if (-not $free) { Say ("Port {0} stays busy{1}, and no free port was found to move to." -f $busy, $(if ($owner) { " (used by $owner)" } else { '' })) 'Red'; break }
            Say ("Port {0} on this computer stays busy{1}. Moving the app's port {0} to {2} (saved as {3}={2} in plant-database\.env)." -f $busy, $(if ($owner) { ", used by $owner" } else { '' }), $free, $var) 'Yellow'
            Set-EnvValue $var $free
            if ($var -eq 'PLANTDB_PORT') {
                $script:savedPort = "$free"
                $script:Url = $(if ($Url -match ':\d+(/.*)?$') { $Url -replace ':\d+(/.*)?$', ":$free" } else { "http://localhost:$free" })
                Say ("On this computer the app now answers at {0}. The Tailscale address does not change." -f $Url) 'Cyan'
            }
        }
        $r = Native-Capture { docker compose up -d @svc }
    }
    return $r.code
}
Step 'Building the new version with the newest security fixes'
# 1.12.0 (or Claude) wrote docker-compose.override.yml to run the app as root when its own user could not write to the data folder.
# Since 1.12.1 the app decides that by itself each time it starts, so that file is no longer needed. Only our own file is removed.
$override = Join-Path $AppFolder 'docker-compose.override.yml'
if (Test-Path $override) {
    $first = (Get-Content $override -TotalCount 1)
    if ("$first" -match '^# Written by (the updater|Claude \(same as the updater writes\)): Docker would not let the app write') {
        Remove-Item $override -Force
        Say 'Removed docker-compose.override.yml: since 1.12.1 the app picks the right way to run by itself.'
    }
}
$tsState = JoinAll $AppFolder @('tailscale', 'state')
if (-not (Test-Path $tsState)) { New-Item -ItemType Directory -Path $tsState -Force | Out-Null }      # 1.12.0: the Tailscale sign-in lives here
Push-Location $AppFolder
$code = Native { docker compose build --pull }
if ($code -ne 0) { Say 'Could not download the newest base image (is the internet down?). Building with the one already on this computer.' 'Yellow'; $code = Native { docker compose build } }
# 1.18.0: the picture checker (container plant-vision, for Identify and Library) downloads about 1 GB of packages when it is built.
# If only that fails, start the rest of the app without it, so an internet hiccup never keeps the app itself from updating.
$script:Services = @()
# Search by voice (container plant-speech) is the same: if only it fails, the app and the picture checker start without it.
if ($code -ne 0) {
    $c3 = Native { docker compose build plants vision }
    if ($c3 -eq 0) {
        $script:Services = @('plants', 'vision', 'tailscale'); $code = 0
        Say 'Could not build the speech service for Search by voice (see the messages above). Starting the rest of Plant record without it. Run the updater again later to try again.' 'Yellow'
    } else {
        $c2 = Native { docker compose build plants }
        if ($c2 -eq 0) {
            $script:Services = @('plants', 'tailscale'); $code = 0
            Say 'Could not build the picture checker for Identify and Library, or the speech service for Search by voice (see the messages above). Starting the rest of Plant record without them. Run the updater again later to try again.' 'Yellow'
        }
    }
}
if ($code -eq 0) {
    $pc = Native { docker compose pull --ignore-buildable }      # the Tailscale container's image; the app itself is built above
    if ($pc -ne 0) { Say 'Could not download the newest Tailscale container. The one already on this computer is used.' 'Yellow' }
    $code = Start-App
}
Pop-Location
if ($code -ne 0) { Say ("docker compose failed (code {0}). The new files are in place; fix the error above and run 'docker compose up -d --build' in the plant-database folder." -f $code) 'Red'; exit 1 }

Step 'Waiting for the app to answer'
$now = Wait-Version
if ($now -ne $newVersion) {
    Push-Location $AppFolder
    $applog = Native-Text { docker compose logs --tail 80 plants }
    Pop-Location
    $bad = @($applog -split "`n" | Where-Object { $_ -match 'PLANTDB_NOT_WRITABLE' }) | Select-Object -Last 1
    if ($bad) {      # since 1.12.1 the app already falls back to root by itself, so this means even root cannot write there
        Say 'The app cannot write to its data folder, even running as root inside its container. Docker said:' 'Red'
        Say ('  ' + ($bad -replace '^.*PLANTDB_NOT_WRITABLE:\s*', '').Trim()) 'Red'
        Say 'Check that the plant-database folder and its data and backups folders are not read-only, then run this again. Your plants and photos are not changed.' 'Yellow'
    }
}
if ($now -eq $newVersion) { Say ("Done. Plant record version {0} is running at {1}" -f $now, $Url) 'Green' }
else { Say ("The app has not answered with version {0} yet (it says: {1}). Give it a minute, then check {2}. In Docker Desktop, Containers > plant-database > Logs shows why." -f $newVersion, $(if ($now) { $now } else { 'nothing' }), $Url) 'Yellow' }
if ((Get-EnvValue 'PLANTDB_BIND') -eq '0.0.0.0') {
    Say 'Note: the app is open to your home network (PLANTDB_BIND=0.0.0.0 in plant-database\.env). Remove that line and run "docker compose up -d" there when you no longer need it.' 'Yellow'
}
if ($now -eq $newVersion -and -not (Test-Path (JoinAll $AppFolder @('tailscale', 'state', 'tailscaled.state')))) {
    Say 'To use the app away from home, run "Set Up Remote Access.cmd" in the plant-database\tools folder once (README: "Using the app away from home").' 'Cyan'
}

# ---- 7. tidy up old images -----------------------------------------------------------------------
# 1.19.1: every older plant-database, plant-database-vision (and plant-database-speech) image, not only the last version's app image. (Until 1.19.1 the
# image name was kept in $old, the same name the Native helper used inside, so Docker was asked to delete an image called "Stop".)
if ($installed -and $installed -ne $newVersion -and $now -eq $newVersion) {
    $oldImages = @((Native-Text { docker image ls --format '{{.Repository}}:{{.Tag}}' }) -split "`r?`n" | ForEach-Object { $_.Trim() } |
        Where-Object { $_ -match '^plant-database(-vision|-speech)?:\d+\.\d+\.\d+$' -and $_ -notmatch (':' + [regex]::Escape($newVersion) + '$') } | Sort-Object -Unique)
    if ($oldImages.Count) {
        $doRemove = $RemoveOldImage
        if (-not $doRemove -and -not $Yes) {
            Say ("Older versions' Docker images still take up disk space: " + ($oldImages -join ', '))
            $doRemove = (Read-Host 'Delete them? Type Y and press Enter, or just Enter to keep them') -match '^(y|yes)$'
        }
        if ($doRemove) {
            $gone = @()
            foreach ($img in $oldImages) { if ((Native { docker image rm $img }) -eq 0) { $gone += $img } }
            if ($gone.Count) { Say ("Removed {0} old image(s): {1}" -f $gone.Count, ($gone -join ', ')) 'Green' }
            if ($gone.Count -lt $oldImages.Count) { Say 'Some old images could not be removed (see above). They do no harm; the updater offers again next time.' 'Yellow' }
        }
    }
}
Say ("Log saved to " + $LogFile)
exit 0
