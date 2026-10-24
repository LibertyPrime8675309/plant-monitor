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
- **1.11.0 additions:**
  - **Place in use:** `location(c)` is now the place the browser chose, sent as the `X-Place` header on every request (falling back to the home place). `home_place(c)` is the home place, used outside requests (hourly updates). `req_loc()` falls back to `location(c)`. Everything that used the home place (frost, watering, prep weather, current conditions, `local_today`, `/api/reference`, `/api/meta`) follows the header. `/api/meta` returns `place`, `places` and `climate` (`place_climate()`: a usual winter's coldest night and coldest-month night, from 3+ years of `weather_daily`, cached 6 hours). `/api/reference` adds `applies` (the written notes are for Round Rock, `REF_PLACE`) and `normals` (`place_normals()`, monthly averages from history).
  - **Fertilizer needs:** plant fields `npk_ratio` (text, normalised to `a-b-c` by `parse_ratio()`) and `fert_strength` (optional enum `FERT_STRENGTHS`). Table `fertilizers` (saved products). `fert_products()` merges saved ones with every product in `fertilizer_log`; `fert_match()` compares N-P-K as shares of the total (largest difference: ≤0.05 Matches, ≤0.12 Close, ≤0.22 Usable); `fert_dose()` aims the strongest nutrient at `STRENGTH_PPM` (150/75/55/40 ppm) and rounds to spoon measures (`nice_amount()`). Routes: `GET/POST /api/fertilizer/products`, `PUT/DELETE /api/fertilizer/products/<id>`, `GET /api/fertilizer/needs[?plant=]`.
- **1.12.0 additions (remote access):**
  - **Ports:** gunicorn listens on three ports in the container.
    - 8080 is "this computer". It is published on 127.0.0.1 only (`PLANTDB_BIND` in `.env` opens it). It has full access, with the optional `PLANTDB_PASSWORD`.
    - 8081 (`TS_PORT`) is reached only by the `tailscale` container. It is never published.
    - 8082 (`SENSOR_PORT`) accepts only `POST /api/readings`. It is published on 127.0.0.1 unless `PLANTDB_SENSOR_BIND` opens it.
    - `via_tailscale()` compares `SERVER_PORT` (the real listener, not the Host header).
  - **Identity:** Tailscale Serve (`tailscale/config/serve.json`: HTTPS on 443, proxy to `http://plants:8081`, Funnel off) adds `Tailscale-User-Login`/`-Name` and strips spoofed copies. `ts_user()` keeps the table `people(login, name, role, first_seen, last_seen)`. The first person is the owner (or the one the setup script sets); the rest start as `viewer`. Requests on 8081 with no login are refused.
  - **Roles:** `role_refusal()` enforces them in `guard()`.
    - Viewers can't make changes.
    - `/api/backups*`, `/api/ingest*` and `/api/people` are owner only, as are changes to `/api/settings`, `/api/weather/settings` and `/api/places/<id>`.
    - `editor()` returns the Tailscale name for Tailscale requests.
    - Routes: `GET/PUT /api/me`, `GET/PUT/DELETE /api/people`. `/api/meta` includes `me`. HSTS is sent on 8081.
  - **Container:** user 10001, `read_only`, tmpfs `/tmp`, `cap_drop: ALL`, `no-new-privileges`. `_check_writable()` prints `PLANTDB_NOT_WRITABLE` if the data folders can't be written. The updater then writes `docker-compose.override.yml` (user root plus the file capabilities it needs) and restarts.
  - **Updater:** runs `docker compose build --pull`, then `pull --ignore-buildable` (the tailscale image), then `up -d`.
- **1.12.1 additions (starting the container):**
  - **Which user:** the container starts as root and runs `app/start.py`.
    - A brand-new, empty `data` or `backups` folder is chowned to 10001; nothing else is changed.
    - A forked child switches to 10001 (`setgroups([])`, `setgid(0)`, `setuid(10001)`) and runs `writable.problem()`: every data folder takes a test file, and the database and its SQLite side files open read-write.
    - If that passes, the process switches to 10001 and execs gunicorn with no capabilities left. If not, it stays root (logged as `PLANTDB_RUNNING_AS_ROOT: …`).
    - `PLANTDB_RUN_AS=root` skips the check. `PLANTDB_RUNS_AS` passes the result to the app, and `/api/meta.runs_as` shows it to owners (Debug window).
    - Compose grants SETUID and SETGID (to switch), plus CHOWN, DAC_OVERRIDE and FOWNER (for the root case), on top of `cap_drop: ALL`.
  - `_check_writable()` in server.py uses the same `writable.problem()`. `PLANTDB_NOT_WRITABLE` now means even root can't write.
  - **gunicorn settings** live in `app/gunicorn.conf.py`, so unknown settings are ignored by older versions. `control_socket_disable = True`: gunicorn 25.1+ otherwise tries to make `~/.gunicorn/gunicorn.ctl` on the read-only filesystem.
  - **Updater:**
    - removes the `docker-compose.override.yml` that 1.12.0 (or Claude) wrote, recognised by its first line; a person's own override is kept.
    - On a busy port (`Start-App`): first tells the person to close Plant record tabs, then retries after 5, 10, 15 and 30 s. Then it moves the port (`PLANTDB_PORT` 8090–8099, `PLANTDB_SENSOR_PORT` 8180–8189, in `.env`).
    - `setup-remote-access.ps1` reads `PLANTDB_PORT`.
  - **Setup script:** `tools/setup-remote-access.ps1` reads `tailscale status --json` in the `plant-tailscale` container (AuthURL, CertDomains, Self.DNSName, User) and makes the signed-in login the owner via `PUT /api/people` on localhost. `tailscale/state` and `.env` are never in a release.
- **API:** `/api/plants`, `/api/plants/<code>` and its sub-routes (`site`, `status`, `history`, `timeline`, `versions`, `restore`, `photos`, `qr.svg`, `daily`, `day`), plus `/api/requests`, `/api/photos`, `/api/to-photograph`, `/api/fertilizer`, `/api/water`, `/api/care`, `/api/frost`, `/api/for-claude`, `/api/weather*`, `/api/places*`, `/api/current`, `/api/backups*`, `/api/export.json|csv`, `/api/audit*`, `/api/meta`, `/api/version` and `/healthz`.

## Front end: `app/static/`
- `index.html`: the shell, with the top bar, `#app`, the section menu (`#sidenav`), the audit log console (`#console`) and `#corner`, which holds the Debug and Display buttons.
- `prefs.js`: display preferences (size, spacing, contrast, theme, menu side, width, plant layout, read-aloud buttons, reading speed, voice, keyboard shortcuts), stored in localStorage `plantdb.display` and set as `data-*` attributes on `<html>`.
- `app.js`:
  - A hash router (`route()`) and one `view*()` function per page: gallery, plant, edit, today, winter, frost, inside, weather, fertilizer, photos, labels, history and backups. Each returns `{title, html, after}`.
  - 1.8.0 modules, each in its own block: frost banner and checklist, watering and Today, read aloud and shortcuts (`addReadButtons()`, Web Speech API), timeline (filled by a `MutationObserver` on `#app`), copy for Claude (`forClaudeDialog()`), and the photo check (`photoCheck()`, which runs before every upload).
  - 1.10.0: the Audit log page (`viewHistory()`, state in `AUD`, filters remembered in localStorage `plantdb.auditf`), the Debug window (`debugDialog()`, settings in `DBG`, localStorage `plantdb.debug`, change events with `data-dbg`) and the console (`conPoll()` every 3 s via `/api/audit?after=`, `conAdd()`, `conLayout()`). `conLayout()` sizes the console to the newest 3, 4 or 5 rows, places it clear of the side menu and of every button pinned to the bottom, and sets `--console-space`, which `fitPanes()` and `main` use to leave room. `pinLayout()` stacks the Sections button and the job note above Debug and Display on phones when they would otherwise overlap.
  - 1.11.0: the Location button and window (`PLACE` in localStorage `plantdb.place`, sent by `api()` as `X-Place`; `placeDialog()`, `placeChanged()`, `paintPlace()`, `plcHomeRow()`; the L key). `META` is reloaded when the place changes, and `tempMarks()`/`humMarks()` come from `META.climate`. Fertilizer needs: `needLines()`, `loadNeeds()` (into `FERT.needs`), `productsBlock()` and `productDialog()`; `fertState0()` fills the feeding form from a plant's match.
  - 1.12.0: `ME()` (from `META.me`), `paintWho()`, `whoDialog()` (name, and for owners the people list with role menus: `data-f="prole"`, `data-act="pdel"`). Viewers get `html[data-role=viewer]`, which hides change buttons in one CSS block. They also get a "View only" note, and a MutationObserver switches off menus that save straight away. `api()` refuses their changes before sending.
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
