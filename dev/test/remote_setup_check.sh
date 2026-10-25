#!/bin/bash
# Tests tools/setup-remote-access.ps1 with PowerShell 7 on Linux, a fake "docker" (Tailscale status replies are scripted) and the
# mock server on port 8080 (start it first: MOCK_TS=1 DATA_DIR=dev/tmp/data python3 dev/test/mock_server.py). Needs pwsh (set PWSH=...).
#   A  not signed in yet: opens the sign-in page, then makes the signed-in account the owner and reports the https address
#   B  signed in, but HTTPS certificates off: stops and says how to turn them on
#   C  everything already set up: changes nothing
set -u
PWSH=${PWSH:-pwsh}; REPO=$(cd "$(dirname "$0")/../.." && pwd); T=$(mktemp -d); FAILS=0
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/app/tools"
cp "$REPO/docker-compose.yml" "$T/app/"; cp "$REPO/tools/setup-remote-access.ps1" "$T/app/tools/"
cat > "$T/bin/docker" <<SH
#!/bin/bash
echo "docker \$*" >> "$T/docker.txt"
if [[ "\$*" == "exec plant-tailscale tailscale status --json" ]]; then
  n=\$(cat "$T/n" 2>/dev/null || echo 0); echo \$((n+1)) > "$T/n"
  scen=\$(cat "$T/scenario")
  user='"User":{"123":{"ID":123,"LoginName":"ethan@example.com","DisplayName":"Ethan Schmidtke"}}'
  self='"Self":{"DNSName":"plants.tail1234.ts.net.","UserID":123}'
  if [[ \$scen == A && \$n -lt 2 ]]; then echo '{"BackendState":"NeedsLogin","AuthURL":"https://login.tailscale.com/a/abc123","Self":{"DNSName":"","UserID":0},"User":{}}'
  elif [[ \$scen == B ]]; then echo "{\"BackendState\":\"Running\",\"AuthURL\":\"\",\"CertDomains\":null,\$self,\$user}"
  else echo "{\"BackendState\":\"Running\",\"AuthURL\":\"\",\"CertDomains\":[\"plants.tail1234.ts.net\"],\$self,\$user}"; fi
fi
exit 0
SH
chmod +x "$T/bin/docker"
run() { echo "$1" > "$T/scenario"; rm -f "$T/n"; PATH="$T/bin:$PATH" timeout 200 "$PWSH" -NoProfile -File "$T/app/tools/setup-remote-access.ps1" -Yes -NoBrowser -WaitSeconds 30 2>&1; }
want() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; FAILS=$((FAILS+1)); fi; }
owner() { python3 -c "import sqlite3; print(sqlite3.connect('$REPO/dev/tmp/data/plants.db').execute(\"SELECT role FROM people WHERE login='ethan@example.com'\").fetchone())"; }
out=$(run A)
want "A: opens Tailscale's sign-in page" '[[ "$out" == *"https://login.tailscale.com/a/abc123"* ]]'
want "A: signs in, finds the https address" '[[ "$out" == *"Signed in."* && "$out" == *"https://plants.tail1234.ts.net"* ]]'
want "A: the signed-in account becomes the owner" '[[ "$out" == *"ethan@example.com is the owner"* && "$(owner)" == "('"'"'owner'"'"',)" ]]'
want "A: says how to share it and turn off key expiry" '[[ "$out" == *"Disable key expiry"* && "$out" == *"Share"* ]]'
want "A: started the containers" 'grep -q "docker compose up -d" "$T/docker.txt"'
want "A: the tailscale state folder exists" '[[ -d "$T/app/tailscale/state" ]]'
out=$(run B)
want "B: HTTPS off: stops and points to the DNS page" '[[ "$out" == *"STOPPED: HTTPS is still off"* && "$out" == *"admin/dns"* ]]'
out=$(run C)
want "C: already set up: says so" '[[ "$out" == *"Already signed in."* && "$out" == *"HTTPS is on"* ]]'
cp "$REPO/docker-compose.yml" "$T/old.yml"; grep -v "plant-tailscale" "$T/old.yml" > "$T/app/docker-compose.yml"
out=$(run C)
want "D: an older plant-database folder: says to update first" '[[ "$out" == *"older than version 1.12.0"* ]]'
echo "$FAILS failed"; exit $FAILS
