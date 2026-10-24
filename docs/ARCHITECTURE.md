# How Plant record is built

## Runtime
- **Docker:** `docker-compose.yml` has one service, `plants`, with container `plant-database`. It is built from the `Dockerfile` on python:3.12-slim and runs gunicorn with 1 worker and 4 threads on port 8080. The image is tagged `plant-database:<version>` with label `plantdb.version`, and the build arg `PLANTDB_VERSION` writes `/app/VERSION`.
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

## Back end: `app/server.py` (one file, about 2,300 lines)
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
- **Field kinds:** text, long, list (one item per line), int, num and enum. Enums are winter plan, health and site (where the plant is: Outdoors, Covered porch, Indoors, Garage or shed). `norm()` validates, and `INT_RANGES` / `NUM_RANGES` bound the numbers.
- **Edits:**
  - `apply_changes()` writes only the changed fields, then `bump()` raises the page version and writes a snapshot plus audit rows.
  - `PUT /api/plants/<code>` needs `base_version` and refuses stale edits with a 409.
- **Starting up:** `init_db()` creates or upgrades the schema, seeds a fresh install from `seed/seed.json`, then runs `apply_batches()`.
- **Upgrade batches** (`seed/batches/*.json`) are applied once each, in filename order, and recorded as `settings` key `batch_applied:<id>`. Keys:
  - `plants`: new pages, numbered next free `P-###`. Each can carry `photos` and `take_photos` (`[{file, from}]`, which moves an existing photo onto the new page).
  - `existing_photos`: `[{code, file, caption, primary}]`
  - `updates`: `[{code, name, photos, note, set: {field: [old, new]}}]`. A field is only changed if it still holds `old`; otherwise a note is logged. `find_plant()` matches by photo file first, then by code plus name.
  - `archive`: `[{code, name, photos, note}]`
  - `requests_add`: `[{key, code, kind, text}]`
  - `requests_done`: `[key or {key, answer}]`
  - `to_photograph_add` / `to_photograph_done`
- **Weather:**
  - Data comes from Open-Meteo: forecast, archive and geocoding, with no account needed.
  - A background loop updates every enabled place hourly. "Load history" backfills years of readings in chunks, with retries and progress shown in `/api/weather/job`.
  - Recent years keep full hourly detail; older years keep core hourly values plus daily summaries.
  - `/api/readings/series` aggregates readings for the charts.
- **Backups:** `make_backup()` uses SQLite's backup API to write a zip containing `plants.db`, `backup.json` and optionally the photos. `backup_loop` handles automatic backups. `POST /api/backups {wait:true, kind:'update'}` is what the updater calls.
- **1.8.0 additions:**
  - **Frost:** `frost_report()` turns the home forecast into cold nights and the outdoor plants at risk (`FROST_MARGIN` = close calls). `GET /api/frost`, `POST /api/frost/done`.
  - **Watering:** `water_report()` works out each plant's next check from its soil moisture range (or the `water_every_days` field), the last three days' highs and rain (0.25 in or more counts for Outdoors plants), and `care_log`. `GET /api/water`, `GET/POST /api/care`, `DELETE /api/care/<id>`.
  - **Timeline:** `GET /api/plants/<code>/timeline` groups the plant's `audit_log` rows into events and adds its finished requests.
  - **Copy for Claude:** `GET /api/for-claude`, `GET /api/for-claude.txt`, `POST /api/for-claude/copied`. Rows signed "Claude (...)" (upgrade batches) are left out.
  - **Photos:** `repair_seed_photos()` copies seed photos that are missing from the data folder, for installs whose photos arrived in packs.
- **1.9.0 additions:** getting plants ready to come inside. Plant fields `leaf_type` and `pot_size` (optional enums: `ENUMS`, `OPTIONAL_ENUMS`) and `pests_found` (list). `PREP_METHODS` holds the ten methods and their steps; `prep_rate()` rates each for a plant, `prep_plan()` adds progress, status and the keep-apart date. Steps are logged to `care_log` as `prep_*` kinds (a soak or repot counts as watering). `GET /api/prep`, `GET /api/plants/<code>/prep`, `POST /api/plants/<code>/prep-traits`.
- **1.10.0 additions:** the Audit log page and console. `audit_query(c, args)` builds the filtered query (`q` searches notes, values, names, codes and field labels with `LIKE … ESCAPE`; `plant` (`-` = no plant), `who` (`~claude`, `~people` or a name), `kind` (a key of `AUDIT_KINDS`), `field`, `from`/`to` (local dates, turned into UTC with the home time zone), `after` (ids above N, oldest first), `order`). `audit_rows()` adds `label` (`audit_label()`) and `action_word` (`ACTION_WORD`). Routes: `GET /api/audit` (newest first; `?after=ID` for the live console), `GET /api/audit/search` (`{entries, total, offset, limit, max_id}`, up to 500 a page), `GET /api/audit/facets` (what the filters can choose from), and `GET /api/audit.csv`, which takes the same filters.
- **API:** `/api/plants`, `/api/plants/<code>` and its sub-routes (`site`, `status`, `history`, `timeline`, `versions`, `restore`, `photos`, `qr.svg`, `daily`, `day`), plus `/api/requests`, `/api/photos`, `/api/to-photograph`, `/api/fertilizer`, `/api/water`, `/api/care`, `/api/frost`, `/api/for-claude`, `/api/weather*`, `/api/places*`, `/api/current`, `/api/backups*`, `/api/export.json|csv`, `/api/audit*`, `/api/meta`, `/api/version` and `/healthz`.

## Front end: `app/static/`
- `index.html`: the shell, with the top bar, `#app`, the section menu (`#sidenav`), the audit log console (`#console`) and `#corner`, which holds the Debug and Display buttons.
- `prefs.js`: display preferences (size, spacing, contrast, theme, menu side, width, plant layout, read-aloud buttons, reading speed, voice, keyboard shortcuts), stored in localStorage `plantdb.display` and set as `data-*` attributes on `<html>`.
- `app.js`:
  - A hash router (`route()`) and one `view*()` function per page: gallery, plant, edit, today, winter, frost, inside, weather, fertilizer, photos, labels, history and backups. Each returns `{title, html, after}`.
  - 1.8.0 modules, each in its own block: frost banner and checklist, watering and Today, read aloud and shortcuts (`addReadButtons()`, Web Speech API), timeline (filled by a `MutationObserver` on `#app`), copy for Claude (`forClaudeDialog()`), and the photo check (`photoCheck()`, which runs before every upload).
  - 1.10.0: the Audit log page (`viewHistory()`, state in `AUD`, filters remembered in localStorage `plantdb.auditf`), the Debug window (`debugDialog()`, settings in `DBG`, localStorage `plantdb.debug`, change events with `data-dbg`) and the console (`conPoll()` every 3 s via `/api/audit?after=`, `conAdd()`, `conLayout()`). `conLayout()` sizes the console to the newest 3, 4 or 5 rows, places it clear of the side menu and of every button pinned to the bottom, and sets `--console-space`, which `fitPanes()` and `main` use to leave room. `pinLayout()` stacks the Sections button and the job note above Debug and Display on phones when they would otherwise overlap.
  - Templates use the `html` tagged template, which escapes values (`raw()` opts out, `rend()` renders).
  - Click, change and submit events are delegated to `acts`, `changeActs` and `formActs`.
  - `buildSideNav()` builds the "On this page" menu from the `section.blk > h2` headings.
  - `linkify()` turns plant codes into links with photo previews.
- **Plants page filters:** the state lives in `G` and is remembered in localStorage `plantdb.filters`. It also drives Previous / Next on plant pages.
- `style.css`: colour tokens on `:root`, overridden for dark mode and high contrast. Additions are appended in blocks headed with the version that added them.
- **Charts:** hand-drawn SVG using a palette checked for colour-blind readers (see the CHANGELOG for 1.5.0).

## Known constraints
- Files saved to Ethan's computer from a chat must be under 30 MB. From 1.8.0 the release zip carries no plant photos; they ship in photo packs (one per upgrade batch, split if over 28 MB), and only new packs are sent with a release. See `tools/make-release.py` and the updater.
- The tests run in a sandbox without Docker Hub, so the Docker image itself is only built on Ethan's PC.
