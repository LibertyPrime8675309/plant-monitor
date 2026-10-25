# Plant record (plant-monitor): rules for Claude and other agents

This is Ethan's home plant database: a Flask + SQLite web app ("Plant record") that runs in Docker Desktop on his Windows PC and tracks about 80 potted plants in Round Rock, Texas, along with the local weather. Read `docs/ARCHITECTURE.md` before changing code, and `docs/PROTOTYPING.md` before starting a prototype.

## Who it is for
- Ethan is visually impaired. Accessibility is a requirement:
  - Large, scalable text (everything scales with the Display setting).
  - High contrast and light/dark themes.
  - Full keyboard use with visible focus.
  - Real labels on every control.
  - No information carried by colour alone.
  - Nothing that only works on hover.
  - Pages must work at phone width with no sideways scrolling.
- Write labels, buttons and help text in plain words, sentence case, active voice. Say what a button does ("Save changes", "Moved indoors").

## How Ethan works
- **Commands:** whenever you give him a command, give it for **Windows cmd.exe, PowerShell and bash**, in that order. The same goes for the README.
- **Releases** ship as a zip named `plant-database-v<version>-YYYYMMDD-HHMM.zip` (UTC), with all files inside a `plant-database/` folder, VERSION and CHANGELOG included. Build it with `python3 tools/make-release.py [new-version]`.
  - From 1.8.0 the release zip has no plant photos. They go in **photo packs**, one per upgrade batch (`dist/plant-database-photos-<batch>.zip`).
  - Packs never change once made, so send Ethan only the packs for batches that are new in that release.
  - The updater adds any photos his folder is missing from packs saved next to the release zip.
  - `--full` builds the old single zip with everything.
  - He installs it with the updater: `tools/Update Plant Database.cmd` / `update-plant-database.ps1`. It unzips over his folder, keeps `data/` and `backups/`, makes a backup first and runs `docker compose up -d --build`.
  - Zips go in `C:\Users\Ethan\Documents\Claude\Plants\versions_plant-database` (from 1.12.2; the updater moves any zip saved in `Plants` there). Save releases and photo packs straight into that folder. Files saved to his computer from a chat must be under 30 MB.
- **Versions:** bump the patch number for fixes and small additions, the minor number for new features. Update all of these together:
  - `VERSION`
  - the three places in `docker-compose.yml` (build arg, image tag, label)
  - the top entry of `CHANGELOG.md` (written for Ethan, not for developers)
  - the README section for anything he uses
- **Requests to Ethan:** keep reminding him of what Claude is waiting on (open requests in the app and the "Still to photograph" list) at the end of replies, until he provides it.

## Rules for changes
- **Never touch his data.** `data/` (database and photos) and `backups/` never go into git or a release. A new version must upgrade an existing database in place, safely and idempotently (`init_db()` adds columns and tables; see ARCHITECTURE).
- **Plant facts go in upgrade batches** (`app/seed/batches/*.json`), never as hand edits to a database.
  - A field update states the value it expects to replace (`{field: [old, new]}`), so anything Ethan edited himself is left alone.
  - Batch files apply in **filename order**, once each. Name new ones so they sort last: `batch9d.json`, then `batchA1.json`. `batch10.json` would sort before `batch2.json`.
- **Access (from 1.12.0).** People reach the app through its own Tailscale container: port 8081, with identity headers, roles owner/editor/viewer. This computer uses port 8080 (localhost only), and sensors use 8082 (readings only).
  - Any new route that changes data is refused for viewers automatically.
  - Owner-only areas must be added to `OWNER_ONLY_PATHS` or `OWNER_ONLY_CHANGES` in `server.py`.
  - Buttons that make changes must also be added to the viewer CSS block in `style.css`.
  - Never publish 8081, and never trust `Tailscale-User-*` headers on any other port.
  - The container starts as root and `app/start.py` picks the user (10001 if it can write to the data folders, else root). Don't add `USER` to the Dockerfile, and keep gunicorn settings in `app/gunicorn.conf.py`.
- Keep the front end dependency-free (vanilla JS, one CSS file) and compatible with the strict Content Security Policy: **no inline scripts or inline event handlers**. Actions use `data-act` / `data-f` / `data-form` attributes, handled by delegation in `app.js`.
- **Test before shipping:**
  1. Run the app with `dev/test/mock_server.py` (fake weather, no internet).
  2. Run `dev/test/smoke.py`, and look at the screenshots it saves in `dev/tmp/shots/`.
  3. For upgrades, also test on a copy of a database that has the previous version's batches applied.
- Docker Hub is not reachable from Claude's sandbox. `docker compose config` works, a real image build does not, so say so when a change touches the Dockerfile.

## Where things are
- `app/`: the app (`server.py`, `static/app.js`, `static/style.css`, `static/index.html`, `static/prefs.js`, `seed/`)
- `tools/`: the updater and `make-release.py`
- `dev/seed_src/`: scripts that built each upgrade batch from Ethan's photos; `plants_*.py` and `envdata.py` hold the plant data and care profiles
- `dev/photos-raw/`: the photos those scripts read (already shrunk)
- `dev/test/`: mock server and browser smoke test
- `docs/`: architecture and the prototyping workflow
