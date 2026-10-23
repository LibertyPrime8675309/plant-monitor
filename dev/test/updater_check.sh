#!/bin/bash
# Tests the Windows updater (tools/update-plant-database.ps1) with PowerShell 7 on Linux, a fake "docker" and a fake app.
# Needs pwsh (set PWSH=/path/to/pwsh if it is not on the PATH). Builds a release from this repo into a temp folder, then runs:
#   A  an existing install that has every photo, only the new release zip present   -> updates, no packs needed
#   B  a folder without photos and no packs                                          -> stops before changing anything
#   C  the same with the packs present                                               -> adds every photo
#   D  -Force without packs, then one pack, then the rest                            -> adds photos as they arrive
#   E  nothing left to do                                                            -> "Already up to date"
set -u
PWSH=${PWSH:-pwsh}; REPO=$(cd "$(dirname "$0")/../.." && pwd); T=$(mktemp -d); FAILS=0; PORT=8097
cleanup() { kill $FAKE 2>/dev/null; rm -rf "$T"; }; trap cleanup EXIT
mkdir -p "$T/bin" "$T/repo" "$T/Plants"
(cd "$REPO" && git ls-files | grep -v '^dev/photos-raw' | tar -cf - -T -) | tar -xf - -C "$T/repo"
for f in tools/make-release.py tools/update-plant-database.ps1 app/server.py; do cp "$REPO/$f" "$T/repo/$f"; done   # include uncommitted work
cp -r "$REPO/app/seed" "$T/repo/app/"
(cd "$T/repo" && python3 tools/make-release.py --full >/dev/null && mv dist/plant-database-v*.zip "$T/full.zip" && python3 tools/make-release.py 99.0.0 >/dev/null) || exit 1
printf '#!/bin/sh\necho "docker $*" >> "%s/docker.txt"\nexit 0\n' "$T" > "$T/bin/docker"; chmod +x "$T/bin/docker"
cat > "$T/fake.py" <<PY
import http.server, json
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(s):
        try: v = open('$T/Plants/plant-database/VERSION').read().strip()
        except Exception: v = None
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
echo "$FAILS failed"; exit $FAILS
