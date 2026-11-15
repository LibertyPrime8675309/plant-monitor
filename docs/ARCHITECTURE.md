# How Plant record is built

## Runtime
- **Docker:** `docker-compose.yml` has the services `plants` (container `plant-database`), `tailscale` and, from 1.18.0, `vision` (container `plant-vision`, see "Identify" below), and with the prototype proto/voice-search `speech` (container `plant-speech`, see "Search by voice" below). It is built from the `Dockerfile` on python:3.12-slim and runs gunicorn with 1 worker and 4 threads on port 8080. The image is tagged `plant-database:<version>` with label `plantdb.version`, and the build arg `PLANTDB_VERSION` writes `/app/VERSION`.
- **Volumes:** `./data:/data` holds the database and photos; `./backups:/backups` holds backups made by the app.
- **Environment:**

  | Variable | Purpose |
  |---|---|
  | `DATA_DIR` | data folder |
  | `PLANTDB_PASSWORD` | optional browser password (Basic auth, any user name) |
  | `PLANTDB_WEATHER=0` | stops the online weather jobs |
  | `PLANTDB_JOURNAL` | SQLite journal mode; default `DELETE`, because WAL misbehaves on Windows bind mounts |
  | `PLANTDB_BACKUP_DIR` | backup folder |
  | `PLANTDB_VERSION` | the version shown in the app |

- **Security:**
  - Every write request needs an `X-Editor` header (the name in "Editing as"), which also works as a CSRF guard. Cross-origin writes are refused.
  - `/api/readings` (sensor posts) is checked with an `X-Ingest-Token` instead.
  - The Content Security Policy forbids inline scripts.

## Back end: `app/server.py` and the `app/plantdb/` package (split in 1.32.0)
- `server.py` is the entry point gunicorn loads (`server:app`). It calls `plantdb.load()` (1.46.0: every `.py` in the package, `core` first, the rest by their `ORDER` constant, default 50, then by name; before that a hand-kept import line every prototype edited), links them, runs `init_db()` and starts the background threads. It re-exports every name, so `import server as S` in a test still gives `S.app`, `S.init_db`, `S.light_verdict` and the rest; `S.patch(name, value)` replaces a function in every module (the mock server does this for `http_json`).
- `plantdb/core.py`: the Flask app, DATA_DIR and the other paths, the schema and `init_db()`, batches, `norm()`, helpers (`now()`, `db()`, 1.57.0: `setting()` and `set_setting()`, `editor()`, `audit_only()`), people and security. `problem()` and `problem_exc()` are in `problems.py` (1.57.0; they were in weather.py). **Only the core's names may be used at import time** (module-level constants); everything else is linked.
- One module per feature: `where` (homes, places, areas and spots), `weather`, `plants` (the API, requests, photos, labels, `/api/meta`), `care`, `fert`, `groups`, `lights` (grow lights, pots and trays), `library` (the library, browse, offline photos by area, near home, care sheets), `identify` (1.57.0: pictures, the one identifier, examples, Pl@ntNet and Claude), `speciesfacts` (1.57.0: `species_facts`, `facts_keys()`), `places` (1.57.0: `loc_get()` and friends, `/api/places`), `pastdays` (1.57.0: a plant's past days), `problems` (1.57.0), `fungi`, `shopping`, `audit`, `offline`, `frost` (the frost alert and the calendar file), `backups`, `jobs`, `push` (1.33.0, Web Push; the crypto is in `app/webpush.py`), `search` (1.33.0, `/api/search`), `copies` (1.33.0, the second copy of backups), `heat` (1.34.0, the AHS heat zone from the weather history: `place_heat()`, `/api/heat`, `heat_brief()` in `/api/meta`). `sensors` (1.35.0): `sensor_devices` table (name, plant_id, spot_id, area_id, quiet_hours, auto_water), `sensor_card()` (newest values, 24-hour min/max, sparkline bins, verdicts via `sensor_judge()`), `/api/sensors`, `/api/sensors/summary` (Today), `PUT/DELETE /api/sensors/<device>` (DELETE owner-only), `sensor_after_readings()` called from `POST /api/readings` (a soil-moisture jump of 15 points within 3 hours logs a watering once a day), `push_sensors()` run by `push_loop` (kind `sensors`, `push_once` per sensor, kind and day). `readings` gained `weight_g` (1.35.0) and `soil_raw` (1.36.0, the probe's volts; `cal_dry`/`cal_wet` on `sensor_devices`, applied by `sensor_apply_cal()`; `/api/sensors/<device>/calibrate`; `/api/sensors/days` for the timeline and calendar). `heat` (1.36.0) also has `plants_heat()`, `/api/heat/plants`, `/api/heat?above=`; plants gained `heat_zone_high/low/source`. `jobs` has `/api/health` (1.36.0). `review` (1.37.0): `/api/review?year=` (one record per plant from audit_log, care_log, fertilizer_log, photos, requests and weather_daily) and the `/share` fallback. `mirror` (1.37.0): with `PLANTDB_MIRROR=1`, `mirror_loop` restores the newest backup from `PLANTDB_MIRROR_IN` (default `/mirror-in`) every `PLANTDB_MIRROR_MINUTES`, keeping only that zip; the guard in core makes everyone a viewer and refuses every change except `/api/me/prefs`; `mirror_info()` rides in `/api/meta` for the note on every page. `restore_backup(name, by, before=False)` skips the safety backup.
- Each feature module starts with `from .core import *`. Cross-module calls (the weather module calling a plant helper, say) work because `core.link()` fills every module's namespace with the names it does not define itself, after all are loaded: Python looks a name up when a function runs, so this behaves exactly like the one file did. A new module is one new file (1.46.0). 1.57.0: `dev/test/unit/test_lint.py` checks with pyflakes that every name used exists in some module, that nothing is imported or assigned and left unused (core's shared imports excepted), and that code run at import time uses only core's names and the module's own.
- `plantdb/jobs.py` (1.32.0): the one list of background jobs. A worker calls `job_start(kind, label, total)`, `job_progress(id, done, total, label)` and `job_end(id, ok, text)`; `job_run()` wraps a function in a thread with those. `/api/jobs` returns what is running, the last 30 finished, and `jobs_schedule()` (next weather update, store check and backup); `/api/jobs/run` (owner) starts one now. The Jobs window on Settings polls it every 3 s while open.
- The detail for each feature is in `docs/architecture/` (the list is at the end of this file); the file a feature's code lives in is the module of that name.
- **SQLite tables:**
  - `plants`: one row per plant. Columns come from the `FIELDS` list (name, kind, label); a new entry there adds the column on the next start.
  - `plant_versions`: a full snapshot per page version.
  - `audit_log`: the audit log (every change to every record). Written by `bump()`/`apply_changes()` for plant pages and by `audit_only()` for everything else.
  - `photos`
  - `requests`: things Claude needs from Ethan, shown as "Needed from you".
  - `to_photograph`
  - `fertilizer_log`
  - `care_log`: waterings, "still moist" checks and other care (1.8.0).
  - `readings`: hourly weather and sensor values, with JSON `extra`.
  - `weather_daily`
  - `weather_runs`
  - `locations`: weather places; one is "home".
  - `settings`: key/value. Includes `frost_done` (plants ticked off for a cold night) and `claude_copied_at` (when "Copy my answers for Claude" last ran).
- **Field kinds:** text, long, list (one item per line), int, num, enum and date (1.58.0: a day kept as `YYYY-MM-DD` or empty, never in the future; `acquired_on` is the first). Enums are winter plan, health and site (where the plant is: Outdoors, Covered porch, Indoors, Garage or shed). `norm()` validates, and `INT_RANGES` / `NUM_RANGES` bound the numbers.
- **Edits:**
  - `apply_changes()` writes only the changed fields, then `bump()` raises the page version and writes a snapshot plus audit rows.
  - `PUT /api/plants/<code>` needs `base_version` and refuses stale edits with a 409.
- **Starting up:** `init_db()` creates or upgrades the schema, seeds a fresh install from `seed/seed.json`, then runs `apply_batches()`.
- **API:** `/api/plants`, `/api/plants/<code>` and its sub-routes (`site`, `status`, `history`, `timeline`, `versions`, `restore`, `photos`, `qr.svg`, `daily`, `day`), plus `/api/requests`, `/api/photos`, `/api/to-photograph`, `/api/fertilizer`, `/api/water`, `/api/care`, `/api/frost`, `/api/for-claude`, `/api/weather*`, `/api/places*`, `/api/current`, `/api/backups*`, `/api/export.json|csv`, `/api/audit*`, `/api/meta`, `/api/version` and `/healthz`.

## Front end: `app/static/`
- `index.html`: the shell, with the top bar, `#app`, the section menu (`#sidenav`, titled Navigation from 1.42.0, with `#sn-foot` holding `#display-btn`), the audit log console (`#console`) and `#corner`, which holds the Debug button (and Display on a page with no sections: `pinLayout()` moves it there while `data-navempty="1"` on a wide screen).
- `prefs.js`: display preferences (size, spacing, contrast, theme, menu side, width, plant layout, read-aloud buttons, reading speed, voice, keyboard shortcuts), stored in localStorage `plantdb.display` and set as `data-*` attributes on `<html>`.
- `js/*.js`: classic scripts loaded in the order `js/manifest.json` gives, sharing one scope; `core.js` first (`html`, `raw`, `rend`, `api`, the router), `events.js` (every action, by delegation: `acts`, `changeActs`, `formActs`), `features.js` (the registry, below), then one file per feature and `main.js` last. Each is described in `docs/architecture/front-end.md`.
- `style.css` is one stylesheet in the browser and several files in git (1.46.0): the server's `GET /style.css` (`offline.py`) joins `static/css/00-core.css` (colour tokens on `:root`, overridden for dark mode and high contrast; everything up to 1.45.0 in its old order, additions in blocks headed with the version) and then every other file in `static/css/` in name order, one per feature (`checkup.css`, `frostdates.css`, `sensors.css`, `turning.css`, `voice.css`, ...). A feature's styles go in its own file; only rules shared by the whole app go in core. The result carries an ETag and `Cache-Control: no-cache`, and is rebuilt when a file changes.
- **The feature registry (1.46.0, PLAN.md step 2): `js/features.js`.** A feature module makes one `addFeature({ name, care, pages, today, adds })` call when it loads, and the rest of the app asks the registry instead of being wrapped or watched:
  - `pages`: `{ turning: { view, nav, section, label, href, after } }`. `route()` opens `view(parts, qs)` for the route; the page joins `SECTIONS` (the top bar) after the page named; `navMark()` marks `nav`.
  - `today`: blocks on the Today page, `{ id, order, load, html, jump }`. `viewToday()` (care.js) is a list of ordered blocks: 4 the spring note, 5 the frost-dates line, 6 the sitter link, 10 cold night, 20 sensors, 29 the health walk line, 30 water, 40 feed, 50 shopping, 60 coming inside, 65 turn the pots, 70 needed from you, 80 quiet today. `load()` runs alongside the page's own data; the jump row at the top is built from the blocks that give `jump`.
  - `adds`: something added to a page after it draws, `{ id, match(parts), anchor, where, load(parts, at), failed(e), html(d, parts, at), care, then(el, d) }`. `route()` calls `featAdds(parts)` once the page is on screen (and rebuilds Navigation when an add landed); `loadCarePlant()` calls `featAdds(parts, true)` for the adds marked `care` (Turned today beside Watered today). An add is replaced by id, never doubled; `where: 'inside'` fills a box the page left (`.fd-box`). Two run counters (`ADDS_RUN.page`, `.care`) let a newer run of the same kind cancel an older one still loading without the two kinds cancelling each other.
  - `care`: words for care-log kinds, merged into `CARE_WORD`.
  - On it: turning (page, Today block, plant-page button), repotting (1.50.0: page, Today block `today-repot` at order 68, plant-page line `rp-plant`), checkup (page, Today line, group section), frostdates (the three boxes, Today line), sensors (page, plant-page box), the card and sitter links (main.js) and the spring note (weather.js). The lazy fills that belong to the core pages (timeline, facts, prep box, Speak buttons, search-by-voice buttons, fitTables) still use their MutationObservers; they are not features.
- **Charts:** hand-drawn SVG using a palette checked for colour-blind readers (see the CHANGELOG for 1.5.0).

## Known constraints
- Files saved to Ethan's computer from a chat must be under 30 MB. From 1.8.0 the release zip carries no plant photos; they ship in photo packs (one per upgrade batch, split if over 28 MB), and only new packs are sent with a release. See `tools/make-release.py` and the updater.
- Claude's sandbox cannot reach Docker Hub, so it never builds an image. GitHub does (`.github/workflows/images.yml`, November 2026): every pull request builds the app, vision and speech images, and a push to main publishes them to `ghcr.io` under the repository, tagged with VERSION. Until the updater pulls them (PLAN.md step 3), Ethan's PC still builds its own. From 1.58.0 each image is also started before it counts as built or is pushed (`dev/test/image_check.sh`, see the end of this file); that script needs Docker, so its first run for any change is GitHub's.

## Where the detail is: `docs/architecture/`
Read the file for the part you are changing. Each holds the notes as they were written when the feature was built, newest facts included; when you change a feature, change its file. A new feature gets a section in the file it belongs to, or a file of its own, and a line here.

| File | What it covers |
|---|---|
| `data.md` | **Records, upgrade batches, weather, backups and update files.** Upgrade batches; Weather; Backups; Update files from Claude (1.58.0); Weather backup (1.58.0) |
| `care-and-today.md` | **Today, watering and care.** Watering by room and spot, and asking once (1.58.0); The first screen (1.58.0, `css/first-screen.css`); The November 11 review, second part (1.57.0); Bulk care at one home (1.58.0); Today tells the truth about tonight; small accessibility things (1.58.0; November 12 review, items 8 and 11) |
| `versions-1.8-to-1.14.md` | **What 1.8.0 to 1.14.0 added (inside, audit log, console, about this plant).** 1.8.0: frost, watering, the timeline, the photo check; 1.9.0: getting plants ready to come inside; 1.10.0: the audit log and console; 1.11.0: the place in use; 1.14.0: about this plant |
| `access-and-sites.md` | **Remote access, how the container starts, homes and sites.** 1.12.0 additions (remote access); 1.12.1 additions (starting the container); Sites (decided November 7, 2026; built in `PLAN.md` step 4) |
| `lights-pots-rooms.md` | **Grow lights, lights that fit the room, comparing lights, what is in each pot.** 1.13.0 additions (grow lights); Compare lights (1.56.0, PLAN.md step 10); What is in each pot (1.56.0, PLAN.md step 9); Lights that fit the room (1.56.0, PLAN.md step 8) |
| `front-end.md` | **The scripts one by one, units, the Plants page, layout.** Units (1.47.0, PLAN.md step 4a); each script in `js/`; Plants page cards (1.20.0); 1.21.0: watering and other changes; 1.26.0 layout; Plants page filters |
| `identify-library-knowledge.md` | **Identify, the Library, mushrooms, facts with their sources, the propagation guide.** 1.18.0 Identify and the plant library; 1.22.0: mushroom finds and fungi in the picture checker; 1.23.0: the Library, part 2; 1.27.0 uses, partners and propagation (species facts); 1.27.0: wishlist prices; Identify in two modes (1.51.0, PLAN.md step 5b); Knowledge with provenance (1.53.0, PLAN.md step 6a); The identification loop (1.52.0, PLAN.md step 5c); Mushroom find fields (1.51.1, PLAN.md step 5d); Propagation and breeding guide (1.57.0) |
| `offline.md` | **Offline use on phones and tablets.** 1.24.0 (offline use) |
| `own-pages.md` | **Features with files of their own: voice search, frost dates, repotting, the sitter sheet, care cards.** Search by voice (prototype proto/voice-search); Frost dates (1.45.0, prototype #65); Repotting (1.50.0, prototype #70 rebuilt on the registry); Plant-sitter sheet (1.43.0, prototype #41); Care cards (1.19.0, 1.20.0) |
| `releases-and-tests.md` | **Releases, and how old records and built images are tested.** The release rhythm (1.55.0, PLAN.md step 7); Old records and built images are tested (1.58.0; November 12 review, item 6) |
| `water-rhythm.md` | **How often you water (prototype).** How often you water (prototype proto/water-rhythm) |
