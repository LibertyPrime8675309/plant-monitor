<#
  Plant record: set up (or check) using the app away from home, through Tailscale. From version 1.12.0.

  Double-click "Set Up Remote Access.cmd" in the plant-database\tools folder, or run it from PowerShell:

      powershell -ExecutionPolicy Bypass -File .\setup-remote-access.ps1

  What it does:
    1. Starts the app and its own Tailscale device ("plants"), if they are not running.
    2. If that device is not signed in yet, opens Tailscale's sign-in page in your browser. Sign in with your
       usual Tailscale account and approve it.
    3. Checks that HTTPS certificates are on for your tailnet, and opens the page to turn them on if not.
    4. Makes you the owner of the app (everything, including backups and who can use it).
    5. Opens https://plants.<your-tailnet>.ts.net once so Tailscale fetches its certificate.
    6. Offers to point the QR codes on plant labels at that address.
    7. Says what to do next: your phone, sharing with someone, and turning off key expiry.
  Run it again any time to check that everything is still working. It changes nothing that is already right.

  Options:
    -Yes          Do not ask questions (keeps the label address as it is).
    -NoBrowser    Print addresses instead of opening them.
    -AppFolder    The plant-database folder, if this script is somewhere else.
    -Url          Where the app answers on this computer (default http://localhost:8080, or the port saved as PLANTDB_PORT in .env).

  Works with Windows PowerShell 5.1 (built into Windows) and PowerShell 7.
#>
[CmdletBinding()]
param(
    [string]$AppFolder = '',
    [string]$Url = 'http://localhost:8080',
    [switch]$Yes,
    [switch]$NoBrowser,
    [int]$WaitSeconds = 300
)

$ErrorActionPreference = 'Stop'
if (-not $AppFolder) { $AppFolder = Split-Path -Parent $PSScriptRoot }
$LogFile = Join-Path $AppFolder 'remote-access-log.txt'
$EnvFile = Join-Path $AppFolder '.env'          # the updater saves PLANTDB_PORT here if port 8080 was busy
if (-not $PSBoundParameters.ContainsKey('Url') -and (Test-Path $EnvFile)) {
    foreach ($l in (Get-Content $EnvFile)) { if ($l -match '^\s*PLANTDB_PORT\s*=\s*(\d+)\s*$') { $Url = "http://localhost:" + $Matches[1] } }
}

function Say([string]$text, [string]$color = 'Gray') { Write-Host $text -ForegroundColor $color; Add-Content -Path $LogFile -Value ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $text) }
function Step([string]$text) { Say ''; Say ("== " + $text) 'Cyan' }
function Fail([string]$text) { Say ("STOPPED: " + $text) 'Red'; Say ("Details are in " + $LogFile) 'Yellow'; exit 1 }
function Open-Page([string]$u) {
    if ($NoBrowser) { Say ("  Open this in your browser: " + $u) 'Cyan'; return }
    try { Start-Process $u } catch { Say ("  Open this in your browser: " + $u) 'Cyan' }
}
# Run docker and keep its output as text. Windows PowerShell 5.1 treats a program's error output as errors, so relax that here.
function Docker-Run([string[]]$a) {
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { $out = (& docker @a 2>&1 | Out-String) } finally { $ErrorActionPreference = $old }
    return @{ code = $LASTEXITCODE; text = "$out" }
}
function TS-Status {
    $r = Docker-Run @('exec', 'plant-tailscale', 'tailscale', 'status', '--json')
    $t = $r.text.Trim()
    if (-not $t.StartsWith('{')) { return $null }
    try { return ($t | ConvertFrom-Json) } catch { return $null }
}
function Headers { return @{ 'X-Editor' = 'Remote access setup' } }

Say ''
Say 'Plant record: using the app away from home (Tailscale)' 'Green'
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail 'Docker is not installed or not on the PATH. Start Docker Desktop and try again.' }
if (-not (Test-Path (Join-Path $AppFolder 'docker-compose.yml'))) { Fail ("No docker-compose.yml in " + $AppFolder + ". Run this from the plant-database\tools folder.") }
if (-not (Select-String -Path (Join-Path $AppFolder 'docker-compose.yml') -Pattern 'plant-tailscale' -Quiet)) { Fail 'This plant-database folder is older than version 1.12.0. Run the updater first.' }

# ---- 1. start ---------------------------------------------------------------------------------------
Step 'Starting the app and its Tailscale device'
$state = Join-Path (Join-Path $AppFolder 'tailscale') 'state'
if (-not (Test-Path $state)) { New-Item -ItemType Directory -Path $state -Force | Out-Null }
Push-Location $AppFolder
$r = Docker-Run @('compose', 'up', '-d')
Pop-Location
if ($r.code -ne 0) { Say $r.text; Fail 'docker compose could not start the containers. Is Docker Desktop running?' }
$st = $null; $t0 = Get-Date
do { Start-Sleep -Seconds 2; $st = TS-Status } while (-not $st -and ((Get-Date) - $t0).TotalSeconds -lt 90)
if (-not $st) { Fail 'The Tailscale container (plant-tailscale) did not start. In Docker Desktop, open Containers > plant-tailscale > Logs to see why.' }

# ---- 2. sign in -------------------------------------------------------------------------------------
Step 'Signing the plants device in to your Tailscale account'
if ($st.BackendState -eq 'Running') { Say '  Already signed in.' 'Green' }
else {
    $opened = $false; $t0 = Get-Date
    while ($st.BackendState -ne 'Running' -and ((Get-Date) - $t0).TotalSeconds -lt $WaitSeconds) {
        if ($st.AuthURL -and -not $opened) {
            Say '  Opening the Tailscale sign-in page. Sign in with your usual Tailscale account, then come back here.' 'Yellow'
            Open-Page $st.AuthURL; $opened = $true
        }
        if ($st.BackendState -eq 'NeedsMachineAuth' -and $opened) { Say '  Waiting for the device to be approved in the Tailscale admin console (Machines page).' 'Yellow'; $opened = 'approve' }
        Start-Sleep -Seconds 3
        $n = TS-Status; if ($n) { $st = $n }
    }
    if ($st.BackendState -ne 'Running') { Fail ("The plants device is not signed in yet (Tailscale says: " + $st.BackendState + "). Run this again to get a fresh sign-in page.") }
    Say '  Signed in.' 'Green'
}

# ---- 3. HTTPS ---------------------------------------------------------------------------------------
Step 'Checking HTTPS for your tailnet'
$tries = 0
while ((-not $st.CertDomains -or @($st.CertDomains).Count -eq 0) -and $tries -lt 3) {
    $tries++
    Say '  HTTPS certificates are off for your tailnet. Opening the DNS page of the Tailscale admin console:' 'Yellow'
    Say '  turn on MagicDNS if it is off, then press "Enable HTTPS" under HTTPS Certificates.' 'Yellow'
    Open-Page 'https://login.tailscale.com/admin/dns'
    if ($Yes) { break }
    $null = Read-Host '  When that is done, press Enter here'
    Start-Sleep -Seconds 3
    $n = TS-Status; if ($n) { $st = $n }
}
if (-not $st.CertDomains -or @($st.CertDomains).Count -eq 0) { Fail 'HTTPS is still off for your tailnet. Turn it on (admin console, DNS page), then run this again.' }
$dns = "$($st.Self.DNSName)".TrimEnd('.')
if (-not $dns) { Fail 'The plants device has no MagicDNS name yet. Turn on MagicDNS (admin console, DNS page), then run this again.' }
$addr = "https://$dns"
Say ("  HTTPS is on. The app's address is " + $addr) 'Green'

# ---- 4. owner ---------------------------------------------------------------------------------------
Step 'Making you the owner of the app'
$me = $null
try { $me = $st.User."$($st.Self.UserID)" } catch { }
if ($me -and $me.LoginName) {
    $body = @{ login = $me.LoginName; name = $(if ($me.DisplayName) { $me.DisplayName } else { $me.LoginName }); role = 'owner' } | ConvertTo-Json
    try {
        $null = Invoke-RestMethod -Method Put -Uri "$Url/api/people" -Headers (Headers) -ContentType 'application/json' -Body $body -TimeoutSec 20
        Say ("  " + $me.LoginName + " is the owner. Everyone else starts as 'Can view only'.") 'Green'
    } catch { Say ("  Could not reach the app at " + $Url + " to set the owner (" + $_.Exception.Message + "). The first person to open the app through Tailscale becomes the owner, so open it yourself first.") 'Yellow' }
} else { Say '  Could not tell which account signed in. The first person to open the app through Tailscale becomes the owner, so open it yourself first.' 'Yellow' }

# ---- 5. first visit ---------------------------------------------------------------------------------
Step ("Opening " + $addr + " once, so Tailscale fetches its certificate (this can take a minute the first time)")
$ok = $false
for ($i = 0; $i -lt 3 -and -not $ok; $i++) {
    try { $v = Invoke-RestMethod -Uri "$addr/api/version" -TimeoutSec 60; $ok = $true; Say ("  It answers: Plant record " + $v.version) 'Green' }
    catch { Start-Sleep -Seconds 5 }
}
if (-not $ok) { Say ("  No answer yet. Make sure Tailscale is on for this computer, wait a minute, then open " + $addr) 'Yellow' }

# ---- 6. label codes ---------------------------------------------------------------------------------
Step 'QR codes on plant labels'
try {
    $s = Invoke-RestMethod -Uri "$Url/api/settings" -TimeoutSec 20
    if ($s.base_url -eq $addr) { Say ("  Labels already open " + $addr) 'Green' }
    else {
        $now = $(if ($s.base_url) { $s.base_url } else { 'the address the Labels page is opened at' })
        Say ("  The codes now open " + $now + ". With " + $addr + " they work anywhere Tailscale is on, for you and anyone you share with.")
        $answer = $(if ($Yes) { 'n' } else { Read-Host '  Use the Tailscale address for the codes? Type Y and press Enter, or just Enter to leave it' })
        if ($answer -match '^(y|yes)$') {
            $null = Invoke-RestMethod -Method Put -Uri "$Url/api/settings" -Headers (Headers) -ContentType 'application/json' -Body (@{ base_url = $addr } | ConvertTo-Json) -TimeoutSec 20
            Say '  Done. Print new labels from the Labels page when you like; old labels keep their old address.' 'Green'
        }
    }
} catch { Say ("  Could not check the label address (" + $_.Exception.Message + ")") 'Yellow' }

# ---- 7. what next -----------------------------------------------------------------------------------
Step 'Done. What to do next'
Say ("  1. On this computer and your phone: with Tailscale on, open " + $addr + "  (bookmark it, or add it to your home screen).") 'Green'
Say ("     " + $Url + " still works on this computer. The old address on your home network no longer does (README explains why).")
Say  '  2. Turn off key expiry for the plants device, so it never needs signing in again:'
Say  '     Tailscale admin console > Machines > plants > the ... menu > Disable key expiry.'
Say  '  3. To share it with someone (for example your girlfriend): Machines > plants > the ... menu > Share. Send them the invite link.'
Say  '     They install Tailscale, sign in with their own account, accept, and open the same address. They can reach the plant app'
Say  '     and nothing else of yours. They start as "Can view only"; change that in the app: press your name at the top right.'
Open-Page 'https://login.tailscale.com/admin/machines'
Open-Page $addr
Say ("Log saved to " + $LogFile)
exit 0
