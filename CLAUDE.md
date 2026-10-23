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
  - He installs it with the updater: `tools/Update Plant Database.cmd` / `update-plant-database.ps1`. It unzips over his folder, keeps `data/` and `backups/`, makes a backup first and runs `docker compose up -d --build`.
  - He saves zips in `C:\Users\Ethan\Documents\Claude\Plants`. Files saved to his computer from a chat must be under 30 MB.
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
