<#
  Plant record: a test copy beside your real one (1.58.0).

  The test copy is a second Plant record in its own folder, plant-database-test, next to plant-database. It runs a newer
  version (the newest work on GitHub, a pull request, or a release) on a copy of your data, at http://localhost:8090.
  Nothing you do there reaches your real Plant record, and it sends no notifications, backups or shop checks.
  Every page in it says "Test copy", and its browser tabs start with "TEST COPY".

  Double-click one of these (they sit next to "Update Plant Database.cmd"):
    Start Test Copy.cmd     The first time: makes the test copy from the newest work on GitHub and copies your data into it.
                            After that: starts it again and opens it in the browser.
    Refresh Test Copy.cmd   Asks which version to try, then fetches it (your test data stays, unless you ask for a fresh copy).
    Stop Test Copy.cmd      Stops the test copy. Your real Plant record keeps running.

  Or from PowerShell:
      powershell -ExecutionPolicy Bypass -File .\test-copy.ps1 -Action Start
      powershell -ExecutionPolicy Bypass -File .\test-copy.ps1 -Action Refresh -Source 136 -NewData

  Options:
    -Action Start|Refresh|Stop   What to do (default Start).
    -Source <which>   main (the newest work, the default), a pull request number such as 136, or a release such as 1.57.0.
    -NewData          Copy your data again, replacing what is in the test copy.
    -Identify         Also copy the Identify model (about 5 GB) and turn Identify on in the test copy.
    -Yes              Do not ask questions; use the defaults.
    -Port <n>         Where the test copy answers on this computer (default 8090; sensors 8092 with -SensorPort).
    -PlantsFolder, -AppFolder, -TestFolder   Other locations (the folder holding plant-database, your real app folder,
                      the test copy's folder).
    -Repo <owner/name> The GitHub repository (default LibertyPrime8675309/plant-monitor).

  Copying your data stops your real Plant record for about a minute, so the copy is never taken halfway through a change.
  Works with Windows PowerShell 5.1 (built into Windows) and PowerShell 7.
#>
[CmdletBinding()]
param(
    [ValidateSet('Start', 'Refresh', 'Stop')]
    [string]$Action = 'Start',
    [string]$Source = '',
    [switch]$NewData,
    [switch]$Identify,
    [switch]$Yes,
    [int]$Port = 8090,
    [int]$SensorPort = 8092,
    [string]$PlantsFolder = '',
    [string]$AppFolder = '',
    [string]$TestFolder = '',
    [string]$Repo = 'LibertyPrime8675309/plant-monitor'
)

$ErrorActionPreference = 'Stop'
if (-not $PlantsFolder) {
    # next to the updater (the Plants folder), or inside plant-database\tools
    $PlantsFolder = $PSScriptRoot
    if ((Split-Path -Leaf $PSScriptRoot) -eq 'tools' -and (Test-Path (Join-Path (Split-Path $PSScriptRoot) 'docker-compose.yml'))) {
        $PlantsFolder = Split-Path (Split-Path $PSScriptRoot)
    }
}
if (-not $AppFolder) { $AppFolder = Join-Path $PlantsFolder 'plant-database' }
if (-not $TestFolder) { $TestFolder = Join-Path $PlantsFolder 'plant-database-test' }
$Marker = Join-Path $TestFolder 'TEST-COPY.txt'
$RealContainer = 'plant-database'
$Services = @('plants', 'vision', 'speech')

function Say([string]$msg, [string]$color = 'White') { Write-Host $msg -ForegroundColor $color }
function Fail([string]$msg) { Say $msg 'Red'; exit 1 }

# Docker and robocopy write progress to stderr; Windows PowerShell 5.1 would treat that as an error.
function Native([scriptblock]$sb) {
    $__eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { & $sb 2>&1 | ForEach-Object { "$_" } | Write-Host } finally { $ErrorActionPreference = $__eap }
    return $LASTEXITCODE
}
function Quiet([scriptblock]$sb) {
    $__eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { $t = (& $sb 2>&1 | Out-String) } finally { $ErrorActionPreference = $__eap }
    return "$t".Trim()
}
function Ask([string]$question, [bool]$default) {
    if ($Yes) { return $default }
    $hint = if ($default) { '[Y/n]' } else { '[y/N]' }
    $a = Read-Host "$question $hint"
    if (-not $a) { return $default }
    return ($a.Trim().ToLower().StartsWith('y'))
}

# ---- which version -----------------------------------------------------------------------------------------------
function Parse-Source([string]$s) {
    $s = "$s".Trim()
    if (-not $s -or $s -eq 'main') { return @{ kind = 'main'; ref = 'refs/heads/main'; label = 'main'; words = 'the newest work on GitHub (main)' } }
    if ($s -match '^(?:pr[:#\s]*|#)?(\d{1,6})$') { $n = $Matches[1]; return @{ kind = 'pr'; ref = "refs/pull/$n/head"; label = "pr:$n"; num = $n; words = "pull request #$n" } }
    if ($s -match '^v?(\d+\.\d+\.\d+)$') { $v = $Matches[1]; return @{ kind = 'release'; ref = "refs/tags/v$v"; label = "v$v"; ver = $v; words = "release $v" } }
    Fail "Not a version I know: '$s'. Use main, a pull request number such as 136, or a release such as 1.57.0."
}
function Current-Source {
    if (Test-Path $Marker) { foreach ($l in (Get-Content $Marker)) { if ($l -match '^Source:\s*(\S+)') { return $Matches[1] } } }
    return 'main'
}

# ---- .env and the override file -----------------------------------------------------------------------------------
function Set-EnvValue([string]$file, [string]$name, [string]$value) {
    $lines = @(); if (Test-Path $file) { $lines = @(Get-Content $file | Where-Object { $_ -notmatch ('^\s*' + [regex]::Escape($name) + '\s*=') }) }
    Set-Content -Path $file -Encoding ASCII -Value ($lines + "$name=$value")
}
function Write-Settings($src) {
    $envFile = Join-Path $TestFolder '.env'
    Set-EnvValue $envFile 'COMPOSE_PROJECT_NAME' 'plants-test'
    Set-EnvValue $envFile 'PLANTDB_PORT' "$Port"
    Set-EnvValue $envFile 'PLANTDB_SENSOR_PORT' "$SensorPort"
    if ($Identify) { Set-EnvValue $envFile 'PLANTDB_VISION' '1' }
    elseif (-not (Select-String -Path $envFile -Pattern '^\s*PLANTDB_VISION\s*=' -Quiet)) { Set-EnvValue $envFile 'PLANTDB_VISION' '0' }

    $g = 'ghcr.io/libertyprime8675309'
    $tag = if ($src.kind -eq 'release') { $src.ver } else { 'main' }
    $plantsImage = "$g/plant-database:$tag"; $policy = 'missing'
    if ($src.kind -eq 'pr') { $plantsImage = "plant-database-test:pr$($src.num)"; $policy = 'build' }   # GitHub publishes no images for pull requests
    $o = @"
# Made by tools/test-copy.ps1: this folder is the TEST COPY of Plant record. Changes here never reach the real one.
# Its own names, so it runs beside the real containers; no Tailscale; no notifications, backups, update checks or shop checks.
name: plants-test
services:
  plants:
    container_name: plant-database-test
    image: $plantsImage
    pull_policy: $policy
    labels:
      plantdb.test: "1"
    environment:
      PLANTDB_TEST: "1"
      PLANTDB_PUSH: "0"
      PLANTDB_BACKUPS: "0"
      PLANTDB_UPDATES: "0"
      PLANTDB_SHOPS: "0"
  vision:
    container_name: plant-vision-test
    image: $g/plant-database-vision:$tag
  speech:
    container_name: plant-speech-test
    image: $g/plant-database-speech:$tag
  tailscale:
    container_name: plant-tailscale-test
    profiles: ["never"]
"@
    Set-Content -Path (Join-Path $TestFolder 'docker-compose.override.yml') -Encoding ASCII -Value $o
}

function Write-Marker($src, [string]$dataAt) {
    if (-not $dataAt -and (Test-Path $Marker)) { foreach ($l in (Get-Content $Marker)) { if ($l -match '^Data copied:\s*(.+)$') { $dataAt = $Matches[1] } } }
    $now = (Get-Date).ToString('yyyy-MM-dd HH:mm')
    Set-Content -Path $Marker -Encoding ASCII -Value @(
        'This folder is the TEST COPY of Plant record, made by test-copy.ps1.',
        'Changes made here never reach your real Plant record (the plant-database folder).',
        'Start Test Copy.cmd, Refresh Test Copy.cmd and Stop Test Copy.cmd look after it; the updater leaves it alone.',
        'You can delete this whole folder when you are done (stop the test copy first).',
        '',
        "Source: $($src.label)",
        "Fetched: $now",
        "Data copied: $dataAt",
        "Address: http://localhost:$Port")
}

# ---- code from GitHub ---------------------------------------------------------------------------------------------
function Robo([string]$from, [string]$to, [string[]]$opts) {
    $code = Native { robocopy $from $to /NFL /NDL /NJH /NJS /NP @opts }
    if ($code -ge 8) { Fail "Copying $from to $to failed (robocopy code $code)." }
}
function Fetch-Code($src) {
    try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { }
    $tmp = Join-Path ([IO.Path]::GetTempPath()) ('plantdb-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    try {
        $zip = Join-Path $tmp 'code.zip'
        $url = "https://github.com/$Repo/archive/$($src.ref).zip"
        Say "Fetching $($src.words) from GitHub..." 'Cyan'
        $old = $ProgressPreference; $ProgressPreference = 'SilentlyContinue'
        try { Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing } catch { Fail "Could not fetch $url ($($_.Exception.Message)). Is that pull request or release there?" } finally { $ProgressPreference = $old }
        Expand-Archive -Path $zip -DestinationPath (Join-Path $tmp 'x') -Force
        $top = Get-ChildItem (Join-Path $tmp 'x') -Directory | Select-Object -First 1
        if (-not $top -or -not (Test-Path (Join-Path $top.FullName 'docker-compose.yml'))) { Fail 'What GitHub sent does not look like Plant record.' }
        New-Item -ItemType Directory -Force -Path $TestFolder | Out-Null
        foreach ($d in (Get-ChildItem $top.FullName -Directory)) {
            if (@('data', 'backups', 'dev', 'docs', '.github') -contains $d.Name) { continue }
            $dest = Join-Path $TestFolder $d.Name
            if (@('app', 'vision', 'speech', 'tools', 'manual') -contains $d.Name) { Robo $d.FullName $dest @('/MIR') }   # exactly as on GitHub
            else { Robo $d.FullName $dest @('/E') }                                                                     # adds to what is there (tailscale, plant-updates)
        }
        Get-ChildItem $top.FullName -File | ForEach-Object { Copy-Item $_.FullName (Join-Path $TestFolder $_.Name) -Force }
        foreach ($d in @('data', 'backups')) { New-Item -ItemType Directory -Force -Path (Join-Path $TestFolder $d) | Out-Null }
    } finally {
        Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    }
}

# ---- your data ----------------------------------------------------------------------------------------------------
function Copy-Data {
    $from = Join-Path $AppFolder 'data'
    if (-not (Test-Path (Join-Path $from 'plants.db'))) { Fail "No database at $from. Use -AppFolder to say where your real Plant record is." }
    $running = (Quiet { docker ps --filter "name=^/$RealContainer$" --format '{{.Names}}' }) -eq $RealContainer
    if ($running -and -not (Ask 'Your real Plant record stops for about a minute while its data is copied. Go ahead?' $true)) { Fail 'Stopped: nothing was copied.' }
    if (Test-Path (Join-Path $TestFolder 'docker-compose.yml')) { Push-Location $TestFolder; try { Native { docker compose stop } | Out-Null } finally { Pop-Location } }
    $opts = @('/MIR')
    if (-not $Identify) { $opts += @('/XD', (Join-Path $from 'vision')) }   # the Identify model (about 5 GB) stays out unless asked for
    try {
        if ($running) { Say 'Stopping your real Plant record for the copy...' 'Cyan'; Native { docker stop $RealContainer } | Out-Null }
        Say "Copying your data into the test copy..." 'Cyan'
        Robo $from (Join-Path $TestFolder 'data') $opts
    } finally {
        if ($running) { Say 'Starting your real Plant record again...' 'Cyan'; Native { docker start $RealContainer } | Out-Null }
    }
    return (Get-Date).ToString('yyyy-MM-dd HH:mm')
}

# ---- run it -------------------------------------------------------------------------------------------------------
function Up($src, [bool]$getImages) {
    Push-Location $TestFolder
    try {
        if ($getImages) {
            if ($src.kind -eq 'pr') {
                Say "Building pull request #$($src.num) on this computer (a few minutes)..." 'Cyan'
                if ((Native { docker compose build plants }) -ne 0) { Fail 'The build failed; the messages above say why.' }
                if ((Native { docker compose pull vision speech }) -ne 0) { Fail 'Could not fetch the containers from GitHub.' }
            } else {
                Say 'Fetching the containers from GitHub...' 'Cyan'
                if ((Native { docker compose pull plants vision speech }) -ne 0) { Fail 'Could not fetch the containers from GitHub. If the version is new, GitHub may still be building it: try again in a few minutes.' }
            }
        }
        if ((Native { docker compose up -d --remove-orphans plants vision speech }) -ne 0) { Fail 'The test copy did not start; the messages above say why.' }
    } finally { Pop-Location }
    $url = "http://localhost:$Port"
    Say "Waiting for the test copy to answer at $url ..." 'Cyan'
    $deadline = (Get-Date).AddSeconds(180)
    while ((Get-Date) -lt $deadline) {
        try { $r = Invoke-WebRequest -Uri "$url/healthz" -UseBasicParsing -TimeoutSec 5; if ($r.StatusCode -eq 200) { break } } catch { }
        Start-Sleep -Seconds 3
    }
    Say ''
    Say "The test copy is running at $url" 'Green'
    Say 'Every page there says "Test copy". Your real Plant record is still at its usual address.' 'Green'
    Start-Process $url
}

# ---- main ---------------------------------------------------------------------------------------------------------
if ((Quiet { docker info --format '{{.ServerVersion}}' }) -notmatch '^\d') { Fail 'Docker is not running. Start Docker Desktop, wait until it says it is running, and try again.' }
if ([IO.Path]::GetFullPath($AppFolder).TrimEnd('\') -eq [IO.Path]::GetFullPath($TestFolder).TrimEnd('\')) { Fail 'The test copy cannot be the real app folder.' }
if ((Test-Path $TestFolder) -and -not (Test-Path $Marker) -and (Get-ChildItem $TestFolder -Force | Select-Object -First 1)) { Fail "$TestFolder is not empty and is not a test copy, so it is left alone. Use -TestFolder to choose another folder." }

switch ($Action) {
    'Stop' {
        if (-not (Test-Path $Marker)) { Say 'There is no test copy yet.' 'Yellow'; exit 0 }
        Push-Location $TestFolder; try { Native { docker compose stop } | Out-Null } finally { Pop-Location }
        Say 'The test copy is stopped. Your real Plant record keeps running.' 'Green'
    }
    'Start' {
        if (Test-Path $Marker) {
            $src = Parse-Source (Current-Source)
            if ($NewData) { Write-Marker $src (Copy-Data) }
            Up $src $false
        } else {
            $src = Parse-Source $Source
            Say "Making the test copy in $TestFolder from $($src.words)." 'Cyan'
            Fetch-Code $src
            Write-Settings $src
            $at = Copy-Data
            Write-Marker $src $at
            Up $src $true
        }
    }
    'Refresh' {
        $was = Current-Source
        if (-not $Source -and -not $Yes) {
            Say "The test copy has: $((Parse-Source $was).words)." 'Cyan'
            $Source = Read-Host 'Which version now? Press Enter for the newest work on GitHub, or type a pull request number (such as 136) or a release (such as 1.57.0)'
        }
        $src = Parse-Source $Source
        if (-not (Test-Path $Marker)) { $NewData = $true }
        elseif (-not $NewData) { $NewData = Ask 'Copy your data again (replaces everything in the test copy)?' $false }
        Fetch-Code $src
        Write-Settings $src
        $at = ''
        if ($NewData) { $at = Copy-Data }
        Write-Marker $src $at
        Up $src $true
    }
}
