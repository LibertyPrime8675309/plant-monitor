# Plant record (plant-monitor): rules for Claude and other agents

This is Ethan's plant database: a Flask + SQLite web app ("Plant record") that runs in Docker Desktop on his Windows PC. It is being built to manage large plant collections at several sites around the world, to hold the knowledge about them, and to identify and log plants and mushrooms better over time. Today it has one site, Ethan's house in Round Rock, Texas, with about 80 potted plants and the local weather. `docs/PLAN.md` is the agreed order of work (November 2026): its first three steps come before any new feature. Read `docs/ARCHITECTURE.md` before changing code, and `docs/PROTOTYPING.md` before starting a prototype.

## Who it is for
- Accessibility is a requirement, to the standard a person with low vision needs:
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
  - He installs it with the updater: `tools/Update Plant Database.cmd` / `update-plant-database.ps1`. It unzips over his folder, keeps `data/` and `backups/`, makes a backup first, pulls the release's images from ghcr.io (from 1.46.0; `images.yml` publishes them on every push to main, so **a release's version must be on main before he installs it**) and runs `docker compose up -d`. Building on his PC is only the fallback.
  - Zips go in `C:\Users\Ethan\Documents\Claude\Plants\versions_plant-database` (from 1.12.2; the updater moves any zip saved in `Plants` there). Save releases and photo packs straight into that folder. Files saved to his computer from a chat must be under 30 MB.
- **Monthly releases (from December 2026, PLAN.md step 7):** a pull request for a feature merges when green **without** changing VERSION; its CHANGELOG lines go under the next version's heading, written `## 1.58.0 (coming December 1, 2026)`. Pushes between releases publish images tagged `main` only. On the first of the month a release pull request bumps the version (below) and dates the heading; merging it makes GitHub build the images and the release (`release.yml`), and the updater on Ethan's PC fetches it. Patches for something broken can go out between, the same way. Saving a zip into his folder is the fallback.
- **Versions:** bump the patch number for fixes and small additions, the minor number for new features. Update all of these together:
  - `VERSION`
  - the five version strings in `docker-compose.yml` (build arg, label, and the three ghcr.io image tags)
  - the top entry of `CHANGELOG.md` (written for Ethan, not for developers)
  - the README section for anything he uses
- **Requests to Ethan:** keep reminding him of what Claude is waiting on at the end of replies, until he provides it. Open requests in the app and the "Still to photograph" list are not in these reminders: he handles those in the app himself (November 10, 2026).

## Rules for changes
- **Never touch his data.** `data/` (database and photos) and `backups/` never go into git or a release. A new version must upgrade an existing database in place, safely and idempotently (`init_db()` adds columns and tables; see ARCHITECTURE).
- **Plant facts go in upgrade batches** (`app/seed/batches/*.json`), never as hand edits to a database.
  - A field update states the value it expects to replace (`{field: [old, new]}`), so anything Ethan edited himself is left alone.
  - Batch files apply in **filename order**, once each. Name new ones so they sort last: `batch9d.json`, then `batchA1.json`. `batch10.json` would sort before `batch2.json`.
- **Access (from 1.12.0).** People reach the app through its own Tailscale container: port 8081, with identity headers, roles owner/editor/viewer. This computer uses port 8080 (localhost only), and sensors use 8082 (readings only).
  - Any new route that changes data is refused for viewers automatically.
  - The exceptions are `VIEWER_POSTS` (`/api/identify`, `/api/me/prefs`) and `VIEWER_PREFIXES` (`/api/push/`): requests that change nothing of the plants, or only the person's own settings and devices.
  - Owner-only areas must be added to `OWNER_ONLY_PATHS` or `OWNER_ONLY_CHANGES` in `app/plantdb/core.py`.
  - Buttons that make changes must also be added to the viewer CSS block in `style.css`.
  - Never publish 8081, and never trust `Tailscale-User-*` headers on any other port.
  - On 8080 everyone is the owner, so it answers only to names `host_known()` in `core.py` allows (1.58.0: `localhost`, number addresses, single-word and `.local` names, `PLANTDB_HOSTS`, the saved addresses). Tests and tools use `127.0.0.1` or `localhost`.
  - **From the internet (1.58.0):** Funnel publishes `/cal` and `/share` of port 8080, where every other request is the owner's. A request marked `Tailscale-Funnel-Request` reaches only what `public_link()` in `core.py` allows (the calendar link and `/share/<token>`); a new public route must be added there, must check its own token, and must not live beside anything that changes data without one.
  - The container starts as root and `app/start.py` picks the user (10001 if it can write to the data folders, else root). Don't add `USER` to the Dockerfile, and keep gunicorn settings in `app/gunicorn.conf.py`.
- **Mushrooms (from 1.22.0):** nothing in the app may say or suggest that a wild mushroom is edible or safe; IDs are always "leads, not proof". Front-end names for finds use the `mu` prefix (`fz` belongs to the frost checklist).
- Keep the front end dependency-free (vanilla JS in `app/static/js/*.js`, loaded in the order `js/manifest.json` gives; one stylesheet in the browser, built by the server from `static/css/00-core.css` plus one file per feature) and compatible with the strict Content Security Policy: **no inline scripts or inline event handlers**. Actions use `data-act` / `data-f` / `data-form` attributes, handled by delegation in `static/js/events.js`. A feature module says what it adds with one `addFeature()` call (`static/js/features.js`: pages, Today blocks, additions to pages, care kinds); never wrap `viewToday` or `loadCarePlant`, and never watch the page with a MutationObserver to insert something.
- **Test before shipping:**
  1. `python3 -m pytest dev/test/unit -q` (seconds).
  2. `python3 dev/test/run_checks.py` runs every browser check and the smoke test on a fresh mock server each (fake weather, no internet; about 90 minutes), or `run_checks.py lights shops` for a few. Look at the screenshots in `dev/tmp/shots/`. GitHub runs the same on every pull request (`.github/workflows/checks.yml`), and builds the three container images (`images.yml`). **Merge a pull request only when both are green.** The repository is public (November 7, 2026) and a branch rule on main requires the `unit`, `browser (n/4)` and `build (...)` checks, so a merge with a red check is refused.
  3. For upgrades, also test on a copy of a database that has the previous version's batches applied.
- Docker Hub is not reachable from Claude's sandbox. `docker compose config` works, a real image build does not, so say so when a change touches the Dockerfile.

## Where things are
- `app/`: the app (`server.py` is the entry point; the code is in `plantdb/`, one module per feature, `core.py` first; `static/js/*.js`, `static/style.css`, `static/index.html`, `static/prefs.js`, `seed/`)
- `vision/`: the picture checker container for Identify and Library (BioCLIP on the processor; 1.18.0). Its model and lists download into `data/vision` on first start. `dev/vision/` holds the tests that chose the model.
- `tools/`: the updater and `make-release.py`
- `dev/seed_src/`: scripts that built each upgrade batch from Ethan's photos; `plants_*.py` and `envdata.py` hold the plant data and care profiles
- `dev/photos-raw/`: the photos those scripts read (already shrunk)
- `dev/test/`: mock server and browser smoke test
- `docs/`: architecture and the prototyping workflow
