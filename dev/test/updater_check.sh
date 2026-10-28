#!/bin/bash
# Tests the Windows updater (tools/update-plant-database.ps1) with PowerShell 7 on Linux, a fake "docker" and a fake app.
# Needs pwsh (set PWSH=/path/to/pwsh if it is not on the PATH). Builds a release from this repo into a temp folder, then runs:
#   A  an existing install that has every photo, only the new release zip present   -> updates, no packs needed
#   B  a folder without photos and no packs                                          -> stops before changing anything
#   C  the same with the packs present                                               -> adds every photo
#   D  -Force without packs, then one pack, then the rest                            -> adds photos as they arrive
#   E  nothing left to do                                                            -> "Already up to date"
#   F  (1.12.1) the app cannot write to its data folder even as root                -> says so plainly; writes no override file
#   I  (1.12.1) the 1.12.0 fallback file is there                                    -> removed (the app now decides); a person's own override is kept
#   J  (1.12.2) zips in the Plants folder                                          -> moved into versions_plant-database; zips saved there are found
#   G  (1.12.1) port 8080 busy for a moment after the old container stops             -> waits, tries again, works
#   H  (1.12.1) port 8080 stays busy (another program)                               -> moves the app to a free port, saved in .env
set -u
PWSH=${PWSH:-pwsh}; REPO=$(cd "$(dirname "$0")/../.." && pwd); T=$(mktemp -d); FAILS=0; PORT=8097
cleanup() { kill $FAKE 2>/dev/null; rm -rf "$T"; }; trap cleanup EXIT
mkdir -p "$T/bin" "$T/repo" "$T/Plants"
(cd "$REPO" && git ls-files | grep -v '^dev/photos-raw' | tar -cf - -T -) | tar -xf - -C "$T/repo"
for f in tools/make-release.py tools/update-plant-database.ps1 tools/setup-remote-access.ps1 app/server.py docker-compose.yml Dockerfile; do cp "$REPO/$f" "$T/repo/$f"; done   # include uncommitted work
mkdir -p "$T/repo/tailscale/config"; cp -r "$REPO/tailscale/config/." "$T/repo/tailscale/config/"; cp "$REPO/tailscale/README.txt" "$T/repo/tailscale/" 2>/dev/null
cp -r "$REPO/app/seed" "$T/repo/app/"
(cd "$T/repo" && python3 tools/make-release.py --full >/dev/null && mv dist/plant-database-v*.zip "$T/full.zip" && python3 tools/make-release.py 99.0.0 >/dev/null) || exit 1
cat > "$T/bin/docker" <<SH
#!/bin/bash
echo "docker \$*" >> "$T/docker.txt"
case "\$*" in
  "compose build --pull"|"compose build") [ -f "$T/vision-fails" ] && { echo 'failed to solve: process "pip install torch" did not complete successfully' >&2; exit 1; };;
  *"compose logs"*) [ -f "$T/logs" ] && cat "$T/logs";;
  "compose up -d")
    busy() { echo 'Error response from daemon: ports are not available: exposing port TCP 127.0.0.1:8080 -> 127.0.0.1:0: listen tcp4 127.0.0.1:8080: bind: Only one usage of each socket address (protocol/network address/port) is normally permitted.' >&2; exit 1; }
    if [ -f "$T/busy-once" ]; then rm -f "$T/busy-once"; busy; fi
    if [ -f "$T/busy-always" ] && ! grep -q PLANTDB_PORT "$T/Plants/plant-database/.env" 2>/dev/null; then busy; fi;;
esac
exit 0
SH
chmod +x "$T/bin/docker"
cat > "$T/fake.py" <<PY
import http.server, json
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(s):
        try: v = open('$T/Plants/plant-database/VERSION').read().strip()
        except Exception: v = None
        import os
        if os.path.exists('$T/stuck') and not os.path.exists('$T/Plants/plant-database/docker-compose.override.yml'): v = 'starting'
        s.send_response(200); s.send_header('Content-Type', 'application/json'); s.end_headers(); s.wfile.write(json.dumps({'version': v}).encode())
    def do_POST(s):
        s.rfile.read(int(s.headers.get('Content-Length') or 0)); s.send_response(201); s.end_headers(); s.wfile.write(b'{"file":"test.zip"}')
    def log_message(s, *a): pass
http.server.HTTPServer(('127.0.0.1', $PORT), H).serve_forever()
PY
python3 "$T/fake.py" & FAKE=$!; sleep 1
run() { PATH="$T/bin:$PATH" timeout 120 "$PWSH" -NoProfile -File "$T/Plants/update-plant-database.ps1" -Yes -Url "http://127.0.0.1:$PORT" "$@" 2>&1; }
photos() { ls "$T/Plants/plant-database/app/seed/photos" 2>/dev/null | wc -l; }
want() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; FAILS=$((FAILS+1)); fi; }
fresh() { rm -rf "$T/Plants"/*; mkdir -p "$T/Plants/plant-database"; cp "$T/repo/docker-compose.yml" "$T/Plants/plant-database/"; echo 1.7.0 > "$T/Plants/plant-database/VERSION"
          cp "$T/repo/dist"/plant-database-v*.zip "$T/repo/tools/update-plant-database.ps1" "$T/Plants/"; }
ALL=$(ls "$T/repo/app/seed/photos" | wc -l)
rm -rf "$T/Plants"/*; (cd "$T/Plants" && unzip -q "$T/full.zip"); cp "$T/repo/dist"/plant-database-v*.zip "$T/repo/tools/update-plant-database.ps1" "$T/Plants/"
out=$(run); want "A: existing install updates without packs" '[[ "$out" == *"Done. Plant record version 99.0.0"* && $(photos) -eq $ALL ]]'
fresh; out=$(run); want "B: missing packs stop the update before any change" '[[ "$out" == *"STOPPED"* && $(cat "$T/Plants/plant-database/VERSION") == 1.7.0 ]]'
cp "$T/repo/dist"/plant-database-photos-*.zip "$T/Plants/"; out=$(run); want "C: packs present: all $ALL photos added" '[[ "$out" == *"Done."* && $(photos) -eq $ALL ]]'
fresh; out=$(run -Force); want "D1: -Force updates without the packs" '[[ "$out" == *"Done."* && $(photos) -eq 0 ]]'
one=$(ls "$T/repo/dist"/plant-database-photos-*.zip | tail -1); cp "$one" "$T/Plants/"; out=$(run)
want "D2: one pack arrives later and its photos are added" '[[ "$out" == *"photo packs for it have arrived"* && $(photos) -gt 0 && $(photos) -lt $ALL ]]'
cp "$T/repo/dist"/plant-database-photos-*.zip "$T/Plants/"; out=$(run); want "D3: the rest arrive: all photos present" '[[ $(photos) -eq $ALL ]]'
out=$(run); want "E: nothing left to do" '[[ "$out" == *"Already up to date"* ]]'
want "1.12.0: builds on a fresh base image and fetches the Tailscale container" 'grep -q "docker compose build --pull" "$T/docker.txt" && grep -q "docker compose pull --ignore-buildable" "$T/docker.txt"'
touch "$T/vision-fails"; : > "$T/docker.txt"; fresh; cp "$T/repo/dist"/plant-database-photos-*.zip "$T/Plants/"; out=$(run)
want "1.18.0: if the picture checker cannot be built, the rest of the app still updates and starts" '[[ "$out" == *"Starting the rest of Plant record without it"* && "$out" == *"Done. Plant record version 99.0.0"* ]] && grep -q "docker compose build plants" "$T/docker.txt" && grep -q "docker compose up -d plants tailscale" "$T/docker.txt"'
rm -f "$T/vision-fails"; : > "$T/docker.txt"; fresh; cp "$T/repo/dist"/plant-database-photos-*.zip "$T/Plants/"; out=$(run)
want "1.18.0: normally everything starts, the picture checker too" '[[ "$out" == *"Done."* && "$out" != *"without it"* ]] && grep -qx "docker compose up -d" "$T/docker.txt"'
rm -rf "$T/Plants"/*; (cd "$T/Plants" && unzip -q "$T/full.zip"); cp "$T/repo/dist"/plant-database-v*.zip "$T/repo/tools/update-plant-database.ps1" "$T/Plants/"
touch "$T/stuck"; echo "PLANTDB_NOT_WRITABLE: the app cannot write to /data" > "$T/logs"
out=$(run -WaitSeconds 6); rm -f "$T/stuck" "$T/logs"
want "F: cannot write even as root: says so plainly, no override file" '[[ "$out" == *"even running as root"* && "$out" == *"the app cannot write to /data"* && ! -f "$T/Plants/plant-database/docker-compose.override.yml" ]]'
rm -rf "$T/Plants"/*; (cd "$T/Plants" && unzip -q "$T/full.zip"); cp "$T/repo/dist"/plant-database-v*.zip "$T/repo/tools/update-plant-database.ps1" "$T/Plants/"
printf '%s\r\n' '# Written by Claude (same as the updater writes): Docker would not let the app write to its data folder as an unprivileged user,' 'services:' '  plants:' '    user: "0:0"' > "$T/Plants/plant-database/docker-compose.override.yml"
out=$(run -Force)
want "I1: the 1.12.0 fallback file is removed" '[[ "$out" == *"Removed docker-compose.override.yml"* && ! -f "$T/Plants/plant-database/docker-compose.override.yml" && "$out" == *"Done. Plant record version 99.0.0"* ]]'
printf '%s\n' '# my own settings' 'services:' '  plants:' '    environment:' '      PLANTDB_WEATHER: "0"' > "$T/Plants/plant-database/docker-compose.override.yml"
out=$(run -Force)
want "I2: a person's own override file is kept" '[[ "$out" != *"Removed docker-compose.override.yml"* && -f "$T/Plants/plant-database/docker-compose.override.yml" ]]'
rm -f "$T/Plants/plant-database/docker-compose.override.yml"
rm -rf "$T/Plants"/*; (cd "$T/Plants" && unzip -q "$T/full.zip"); cp "$T/repo/dist"/plant-database-v*.zip "$T/repo/tools/update-plant-database.ps1" "$T/Plants/"
touch "$T/busy-once"; out=$(run)
want "G: port busy for a moment: waits, tries again, works" '[[ "$out" == *"still in use. Waiting 5 seconds"* && "$out" == *"close those tabs now"* && "$out" == *"Done. Plant record version 99.0.0"* && ! -f "$T/Plants/plant-database/.env" ]]'
rm -rf "$T/Plants"/*; (cd "$T/Plants" && unzip -q "$T/full.zip"); cp "$T/repo/dist"/plant-database-v*.zip "$T/repo/tools/update-plant-database.ps1" "$T/Plants/"
touch "$T/busy-always"; out=$(run -WaitSeconds 6); rm -f "$T/busy-always"
want "H: port stays busy: moves to a free port, saved in .env, and says the new address" '[[ "$out" == *"stays busy"* && "$out" == *"now answers at http://127.0.0.1:809"* ]] && grep -q "^PLANTDB_PORT=809[0-9]$" "$T/Plants/plant-database/.env"'
rm -rf "$T/Plants"/*; (cd "$T/Plants" && unzip -q "$T/full.zip"); cp "$T/repo/tools/update-plant-database.ps1" "$T/Plants/"
echo old > "$T/Plants/plant-database-1.zip"; mkdir -p "$T/Plants/versions_plant-database"; cp "$T/repo/dist"/plant-database-v*.zip "$T/Plants/versions_plant-database/"
cp "$T/repo/dist"/plant-database-photos-*.zip "$T/Plants/"; z=$(basename "$T"/repo/dist/plant-database-v*.zip); echo different > "$T/Plants/$z"
out=$(run)
want "J1: zips saved in versions_plant-database are found and installed" '[[ "$out" == *"Done. Plant record version 99.0.0"* ]]'
want "J2: other zips in Plants move into versions_plant-database" '[[ -f "$T/Plants/versions_plant-database/plant-database-1.zip" && ! -f "$T/Plants/plant-database-1.zip" && -z "$(ls "$T/Plants"/plant-database-photos-*.zip 2>/dev/null)" && -n "$(ls "$T/Plants/versions_plant-database"/plant-database-photos-*.zip)" ]]'
want "J3: a different file with the same name is left in place, not overwritten" '[[ "$out" == *"Left $z in place"* && $(cat "$T/Plants/$z") == different && $(stat -c %s "$T/Plants/versions_plant-database/$z") -gt 1000 ]]'
cp "$T/Plants/versions_plant-database/$z" "$T/Plants/$z"; out=$(run)
want "J4: an identical copy in Plants is removed" '[[ ! -f "$T/Plants/$z" && "$out" == *"removed 1 copies"* ]]'
want "F: the release carries the Tailscale setup but no sign-in state" 'unzip -l "$T/repo/dist"/plant-database-v99.0.0-*.zip | grep -q "tailscale/config/serve.json" && unzip -l "$T/repo/dist"/plant-database-v99.0.0-*.zip | grep -q "tools/setup-remote-access.ps1" && ! unzip -l "$T/repo/dist"/plant-database-v99.0.0-*.zip | grep -q "tailscale/state"'
echo "$FAILS failed"; exit $FAILS
