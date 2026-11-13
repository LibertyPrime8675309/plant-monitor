#!/usr/bin/env bash
# 1.58.0 (November 12 review, item 6): the build alone is not the test.
#
# GitHub built the three images on every pull request and threw them away, and the browser checks run the code another way
# (Flask's own server, from the source). So nothing ever started the thing a PC runs. The failures that reached Ethan's PC
# were of exactly that kind: 1.12.0 could not write to its folders and restarted for ever.
#
#   bash dev/test/image_check.sh plant-database <version> [image]
#       Starts the app image with this repository's own docker-compose.yml (read-only, almost no privileges, data and
#       backups mapped in, as a new install has them), asks it a few questions, makes a backup the way the updater does,
#       then starts it again on the data it just made, as an update does.
#   bash dev/test/image_check.sh plant-database-speech <version> [image]
#       Decodes a second of sound with the real libraries (PyAV 19 broke this and nothing noticed: no model is needed).
#   bash dev/test/image_check.sh plant-database-vision <version> [image]
#       Loads the libraries the picture checker needs, and its own code, without downloading a model.
#
# Needs Docker. images.yml runs it for each image after building it; it also runs on any computer with Docker.
set -euo pipefail
NAME=${1:?which image: plant-database, plant-database-speech or plant-database-vision}
VER=${2:?the version, as in the VERSION file}
IMAGE=${3:-$NAME:ci}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
say() { printf '\n== %s\n' "$*"; }
fail() { printf '\nFAIL %s\n' "$*" >&2; exit 1; }

if [ "$NAME" = plant-database-speech ]; then
  say "The speech image decodes sound"
  docker run --rm --network none -e PLANTDB_SPEECH=0 --entrypoint python "$IMAGE" -c '
import io, struct, wave
b = io.BytesIO()
with wave.open(b, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
    w.writeframes(struct.pack("<16000h", *([0] * 16000)))
b.seek(0)
from faster_whisper import decode_audio
import ctranslate2, av, numpy, flask
a = decode_audio(b, sampling_rate=16000)
assert 15000 <= len(a) <= 17000, len(a)
print("ok   one second of sound decoded with faster-whisper, PyAV", av.__version__, "and CTranslate2", ctranslate2.__version__)
import service
print("ok   the service module loads (turned off, so it downloads nothing)")
' || fail "the speech image cannot decode sound or load its service"
  exit 0
fi

if [ "$NAME" = plant-database-vision ]; then
  say "The picture checker image loads its libraries"
  docker run --rm --network none -e PLANTDB_VISION=0 --entrypoint python "$IMAGE" -c '
import torch, torchvision, open_clip, timm, safetensors, huggingface_hub, numpy, PIL, flask
x = torch.nn.functional.normalize(torch.ones(2, 4), dim=-1) @ torch.ones(4)
assert abs(float(x[0]) - 2.0) < 1e-5
print("ok   torch", torch.__version__, "works on the processor; open_clip", getattr(open_clip, "__version__", "?"), "numpy", numpy.__version__)
import service
print("ok   the service module loads (turned off, so it downloads nothing)")
' || fail "the picture checker image cannot load its libraries or its service"
  exit 0
fi

[ "$NAME" = plant-database ] || fail "unknown image $NAME"
WORK=$(mktemp -d)
cp "$ROOT/docker-compose.yml" "$WORK/docker-compose.yml"          # a folder of its own, so ./data and ./backups start out as a new install's
cat > "$WORK/docker-compose.override.yml" <<YML
services:
  plants:
    image: $IMAGE
    pull_policy: never
    container_name: plant-database-check
    restart: "no"
    environment:
      PLANTDB_WEATHER: "0"
      PLANTDB_SHOPS: "0"
      PLANTDB_UPDATES: "0"
      PLANTDB_PUSH: "0"
      PLANTDB_OSM: "0"
YML
cd "$WORK"
URL=http://127.0.0.1:8080
logs() { printf '\n---- the container log ----\n'; docker compose logs --no-color plants 2>&1 | tail -80 || true; }
trap 'code=$?; [ $code -eq 0 ] || logs; docker compose down >/dev/null 2>&1 || true; exit $code' EXIT
up() {
  for i in $(seq 1 90); do
    if curl -fsS "$URL/healthz" >/dev/null 2>&1; then return 0; fi
    state=$(docker inspect -f '{{.State.Status}} {{.RestartCount}}' plant-database-check 2>/dev/null || echo 'missing 0')
    case "$state" in exited*|dead*|missing*) fail "the container stopped instead of starting ($state)";; esac
    sleep 2
  done
  fail "the app did not answer within three minutes"
}
json() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

say "Starting $IMAGE with docker-compose.yml, as a new install"
docker compose up -d --no-build plants
up
echo "ok   it answers on $URL"
docker compose logs --no-color plants 2>&1 | grep -m1 -i 'runs as\|running as\|as root\|own user' || true

say "A few questions"
meta=$(curl -fsS "$URL/api/meta")
v=$(printf '%s' "$meta" | json "d['version']"); n=$(printf '%s' "$meta" | json "d['counts']['plants']")
[ "$v" = "$VER" ] || fail "it says it is version $v, not $VER"
[ "$n" -gt 0 ] || fail "a new install has no plants: the seed did not load"
echo "ok   version $v, $n plants from the seed and its batches"
for path in / /app.js /style.css /sw.js /manifest.webmanifest /prefs.js /icon-192.png /sitter.html; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$URL$path")
  [ "$code" = 200 ] || fail "$path answers $code: a file the pages need is not in the image"
done
page=$(curl -fsS "$URL/")
case "$page" in *"app.js?v=$VER"*) ;; *) fail "the page does not load its script for version $VER";; esac
echo "ok   the page and its files are in the image"
h=$(curl -fsS "$URL/api/health")
printf '%s' "$h" | json "'ok   ' + str(d['runs_as'].get('text') if isinstance(d['runs_as'], dict) else d['runs_as']) + ' Saving mode: ' + str(d['journal']['mode']) + '.'"
[ "$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: evil.example:8080' "$URL/api/people")" = 403 ] || fail "it answers to a name that is not its own"
echo "ok   it does not answer to a stranger's name"

say "A backup, the way the updater asks for one"
b=$(curl -fsS -X POST -H 'X-Editor: Image check' -H 'Content-Type: application/json' -d '{"wait":true,"kind":"update","note":"Image check"}' "$URL/api/backups")
file=$(printf '%s' "$b" | json "d['file']")
[ -f "backups/$file" ] || fail "the backup $file is not in the backups folder on this computer"
echo "ok   $file is in the backups folder: the app can write where it must"
[ -f data/plants.db ] || fail "the database is not in the data folder on this computer"

say "Starting it again on the data it made, as an update does"
docker compose restart plants
sleep 3
up
n2=$(curl -fsS "$URL/api/meta" | json "d['counts']['plants']")
[ "$n2" = "$n" ] || fail "after a second start there are $n2 plants, not $n"
echo "ok   the same $n2 plants after a second start"
# what the app itself noticed. Something from the internet (a list it fetches) can fail on a given day, so this is shown, not failed on;
# a problem with the backup or the database is the app's own and does fail.
curl -fsS "$URL/api/problems" | python3 -c "
import json, sys
d = json.load(sys.stdin); own = [x for x in d['problems'] if not x.get('cleared_at') and x.get('area') in ('backup', 'database', 'batch', 'start')]
for x in d['problems'][:8]: print('note the Problems list has:', x.get('area'), '-', x.get('text'))
if not d['problems']: print('ok   nothing on the Problems list')
sys.exit(1 if own else 0)" || fail "the app put a problem of its own on the Problems list"
say "The app image passed"
