# Plan: from one house to many sites

Agreed with Ethan on November 7, 2026 (the review copy is the doc "Plant record: plan for many sites" in his Plants project).

Seven steps take Plant record from an app for one house in Round Rock to a product for plant collections at several sites, with Ethan's house as the first site. The first three steps change how the app is built and shipped, not what it does, and they come before any new feature, including the repotting plan (#70) and anything new Ethan asks for while they are under way. Small fixes to what has already shipped still go out. Sizes are Claude's working days; releases are what Ethan installs.

## Decisions (Ethan, November 7, 2026)

| Question | Answer |
| --- | --- |
| Shape | One app with many sites. |
| Order | Steps 1, 2 and 3 before any new feature, including the repotting plan and new requests made in the meantime. |
| Units | A site default with a per-person override. A person picks a region (which sets every unit) and can still change each unit by hand. |
| Identify default | Ask each time which mode to use, unless the person has set a default in their settings; then do not ask. |
| Images | Yes: updates pull ready-built images from GitHub's registry instead of building on the PC. The repository went public on November 7, 2026 (no paid plan), so the images are public and need no login, and GitHub's branch rule enforces green checks before a merge. |
| Who accepts knowledge edits | Any editor. |
| Release day | The first day of the month. |
| Where the plan lives | Here, `docs/PLAN.md`, with `docs/IDEAS.md` pointing at it. |

## The order at a glance

Steps 1 to 3 come first and in that order; 4 to 6 then run one at a time, 4 before 5 because Identify's "new find" mode needs the site's country. Step 7 is a habit, not a build.

| Step | What changes | Size | Releases | Needs first | Touches |
| --- | --- | --- | --- | --- | --- |
| 1. Decide the shape | A decision (made: one app, many sites) and a section in the architecture notes | Half a day | None | Done (PR #72) | `docs/ARCHITECTURE.md`, `CLAUDE.md` |
| 2. A registry for features | Modules register their Today and plant-page sections, care kinds and routes instead of wrapping functions or watching the page | 3 to 4 days | One minor (1.46.0) | Done in 1.46.0 | `care.js`, `core.js`, `events.js`, `turning.js`, `checkup.js`, `sitter.js`, `frostdates.js`, `sensors.js`, `server.py`, `index.html`, `sw.js`, `style.css`, both docs, the checks |
| 3. Images built on GitHub | Every pull request builds the app, vision and speech images; merges wait for green; images published to GitHub's registry so the updater pulls | 1.5 days | None for the workflow (`.github/` is not in the zip); the updater change shipped in 1.46.0 | Done (PR #72 and 1.46.0) | `.github/workflows`, `docker-compose.yml`, the updater, `tools/make-release.py`, README; a branch rule on GitHub |
| 4. Sites and units | Units per site and per person; plants belong to a site; weather, frost, seasons and roles per site | 8 to 10 days | Two minors (units, then sites) | Done in 1.47.0 and 1.48.0 | `core.py` schema, `weather.py`, `frost.py`, `frostdates.py`, `care.py`, `heat.py`, `lights.py`, `where.py`, `push.py`, `prefs.js`, `plant.js`, `weather.js`, `edit.js`, `index.html`, a new check |
| 4c. The sitter sheet by link | A link a sitter outside the Tailnet opens, with boxes that tick back | 2 to 3 days | One minor (1.49.0) | Done in 1.49.0 | `sitter.py`, `sitter-sheet.js`, `share.html`, `share.js`, `core.py` (`guard()`), README |
| 5. Identify: two modes and a scoreboard | A baseline measured on Ethan's PC; "one of my plants" and "a new find" modes; country data instead of USDA; confirmed photos feed the look-alike step; mushroom fields | 10 to 12 days plus runs on the PC | Two minors and one patch | Step 3; step 4 for the site's country. All done: 5a Nov 8, 5b 1.51.0, 5d 1.51.1, 5c 1.52.0 | `vision/service.py`, the vision lists, `library.py`, `fungi.py`, `discover.js`, `plant.js`, `dev/vision/*`, a GPU option in `docker-compose.yml` |
| 6. Knowledge with provenance | One fact per row with source, date and confidence; editors add and correct; any editor reviews; export | 6 to 8 days | Two minors | Step 2; step 4 helps. Done: 6a in 1.53.0, 6b in 1.54.0 | `library.py`, `fungi.py`, `core.py` schema, `library.js`, `review.js`, the batch tooling in `dev/seed_src`, docs |
| 7. Release rhythm | A minor release on the first of each month, patches only for breakage; install by pulling images | Ongoing | None | Step 3 | `tools/make-release.py`, the updater, `CHANGELOG.md` |
| 8. Lights that fit the room (proposed) | A light model says how it holds, a room or shelf says what it offers and has photos, a plant has a height; a spot says fits / does not fit before PAR; a setup card and a "Set up and checked" tick | 6 to 7 days | One minor (the December 1 release) | Steps 2 and 4; waiting for Ethan's yes | `lights.py`, `where.py`, `core.py` schema, `lights.js`, `where.js`, `plant.js`, `edit.js`, a batch for the light models, a new check |

About six to eight weeks of Claude's time if done one after another, delivered as six or seven releases over two or three months. Steps 1 to 7 were done by November 9, 2026; step 8 was proposed that day and waits for Ethan's review.

## Step 1: decide the shape (done)

One app with many sites, each with its own weather, seasons and people, rather than one copy of the app per site that syncs with the others.

**What exists.** The database already has a `locations` table (name, latitude, longitude, time zone, a device, a forecast) and keeps daily weather per location, because the sensors and the second home were built on it. Plants do not point at a location: they have a site word (Indoors, Outdoors and so on) and a place within the house. Roles (owner, editor, viewer) are for the whole app, not per place. The mirror (1.37.0) is a read-only second copy fed from backups, the nearest thing to sync the app has.

**Why one app.** It reuses what is there, keeps one database to back up and one place for the knowledge base, and the mirror already covers "a read-only copy somewhere else". One copy per site that syncs would need change tracking and conflict rules on every table (SQLite has no merge), which is months, not weeks. If a site ever needs to work with no connection at all, that is the point to revisit, and one app does not make it harder.

**Touches.** `docs/ARCHITECTURE.md` (the "Sites" section), `CLAUDE.md` (the first paragraph).

## Step 2: a registry for features (done in 1.46.0)

New features should declare what they add; today they take it. `turning.js` replaces `viewToday` and `loadCarePlant` with wrapped copies; `checkup.js`, `frostdates.js` and `sensors.js` each run a MutationObserver that watches the whole page redraw and inserts their part when they spot it. Each works alone. Together they are why four prototypes merged in one week conflicted on the same lines every time, and why the Today page's order depends on which script loaded last.

**Front end.** One `features.js`, loaded after `core.js`, with a small `addFeature({...})` call that a module makes once:

- `today`: a section (id, title, where it goes relative to the standard sections, a render function that returns HTML, the data it needs), so `viewToday` in `care.js` builds the page from a list instead of being wrapped. The jump buttons at the top come from the same list.
- `plant`: the same for a plant's page (a line under the quick buttons, a block in the care part), so `loadCarePlant` calls the registered parts after it draws.
- `care_kinds`: the word for the care log and the quick button, so `CARE_WORD` is filled from registrations.
- `nav` and `sections`: the route and the `SECTIONS` entry, so `core.js` stops listing every page by hand.

The five modules above move onto it and lose their wrappers and observers; `sitter.js` keeps its own page but registers its route. Fold state, Read aloud and the Navigation menu already work from section headings, so they need nothing new.

**Server.** `server.py` imports 27 modules by name in one line that every prototype edits. `plantdb/__init__.py` finds the modules itself (every `.py` in the folder, `core` first, the rest in a fixed order each module states as `ORDER = 40`). The same for `index.html`'s script list and `sw.js`'s shell list: one generated list from a manifest, so a new module is one new file plus one line in the manifest.

**Styles.** `style.css` is 1,907 lines in one file, which is what the content policy and the "one CSS file" rule want, but it is where every merge collides. Keep one URL and one file in the browser, built at container start from `static/css/*.css` (core first, then one file per feature). The rule stays true for the browser and false for git, which is where it hurts.

**Cost.** Three to four days, one minor release (1.46.0), no visible change except that the Today page keeps a fixed order. The browser checks for today, plant, turning, checkup, sitter, frostdates and sensors cover the risk; the full set runs before shipping. `docs/PROTOTYPING.md` is rewritten around "register, don't wrap", which also makes each future prototype smaller.

**Touches.** `care.js`, `core.js`, `events.js`, `turning.js`, `checkup.js`, `sitter.js`, `frostdates.js`, `sensors.js`, new `features.js`, `server.py`, `plantdb/__init__.py`, `index.html`, `sw.js`, `style.css` split into `static/css/`, `start.py` (builds the CSS), `docs/ARCHITECTURE.md`, `docs/PROTOTYPING.md`, the unit test that checks the module list, `run_checks.py`.

## Step 3: build the images on GitHub (done: workflow in PR #72, updater in 1.46.0)

Ethan's PC should never be the first place a Dockerfile fails. Claude cannot build images in its sandbox (Docker Hub is not reachable), so 1.44.0's speech service and 1.18.0's picture checker both shipped with a Dockerfile nobody had built. GitHub's runners can reach Docker Hub, and the checks already run there on every pull request.

- A second workflow, `images.yml`, builds the app, vision and speech images on every pull request and on main, with a layer cache so a rebuild takes minutes rather than the 20 the vision image takes cold. It does not start the models; it proves the images build.
- A branch rule so main only takes a pull request whose checks and image builds are green. Claude's GitHub access cannot write repository settings, so Ethan sets it (steps given in the chat on November 7, 2026).
- Publish the built images to GitHub's registry (ghcr.io) under the repository (public, like the repository since November 7, 2026). Done. One consequence: a release must be merged to main (which publishes its images) before Ethan installs it; the updater builds locally if the images are not there yet. The mirror (`mirror/docker-compose.yml`) still builds its own image and could pull the same one later. The updater pulls a ready image instead of building one, turning a ten-minute install with a large download of Python wheels into a two-minute pull. `docker-compose.yml` gets image names, the updater gets a pull step, and the release zip shrinks to the compose file, the updater, the seed batches and the docs. Photo packs stay as they are.

**Cost.** One day for the workflow and the branch rule, half a day for publishing and the updater change (one patch release for the updater). The README gets a note under "Updating".

**Touches.** `.github/workflows/images.yml` (new), `.github/workflows/checks.yml` (job names), `docker-compose.yml`, `tools/Update Plant Database.cmd`, `tools/update-plant-database.ps1`, `tools/make-release.py`, `README.md`.

## Step 4: sites and units

Two releases: units first, because it is self-contained and useful on its own, then sites, which is the real change.

**4a. Units (one minor, 3 to 4 days; done in 1.47.0).** The front end writes °F in 96 places (37 in `weather.js`, 33 in `plant.js`, 14 in `frostdates.js`) and the server in 31 more, in sentences it sends to the page, to push notifications and to the sitter sheet. Lengths are inches throughout: pot sizes, distance from a light, rainfall.

- The database and the weather pipeline keep working in °F and inches; nothing stored changes, so no batch and no migration.
- One pair of formatters, `fmtTemp()` and `fmtLen()` in `core.js` and `temp_text()` / `len_text()` in `core.py`, replace every hand-written unit. Every call site changes, which is the bulk of the work and why it is its own release.
- In Display, a person picks a region (United States; metric; United Kingdom, which mixes them) that sets every unit at once, and can then change each unit by hand (temperature, length, volume, rainfall). Saved in `/api/me/prefs`; a viewer can set it. Each site has a default region that applies to anyone who has not chosen.
- The pot-size list stays as it is (4 in, 6 in and so on) but shows its metric equivalent. New pots can be entered either way.

**4b. Sites (one minor, 5 to 6 days; done in 1.48.0, smaller than planned because the homes model of 1.28.0 already held plants, people, weather and the place in use per home).** A site is a `locations` row grown up: it gains a country, a units default and a grow-season setting (temperate with a winter, tropical wet and dry, no cold season). Plants get a `site_id` (existing plants all land on site 1, which is what the first install does). People get roles per site, with the owner still over all of them.

- Today, All plants, Coming inside, Back outside, Grow lights, Weather and Frost show the site the person chose, remembered per person, with a site switch in the Navigation menu. One person at one site never sees another site's chores unless they ask.
- Weather already runs per location; frost dates, the cold-night checklist, the heat page and the watering model read the plant's site instead of location 1. A site with no frost season gets no Coming inside page at all; a tropical site gets wet-season notes instead, which is new content and a smaller follow-up.
- Winter plans (Move indoors, Hardy outside, Let it go) become "cold-season plans" and only apply where the site has a cold season; the enum and the batches are untouched, so existing records stay as they are.
- The sitter sheet, the push messages and the sensors already know a location; they switch to the plant's site.
- A new browser check, `sites`, creates a second site and walks the pages for both.

**Cost.** Eight to ten days in all; two minor releases; an in-place upgrade that adds columns and backfills site 1, which `init_db()` already knows how to do. This is the step most likely to turn up small things on pages nobody thought of, so a full browser run and a day of Ethan's use come before it goes further.

**Touches.** `core.py` (schema, roles per site, the current-site helper), `weather.py`, `frost.py`, `frostdates.py`, `heat.py`, `care.py`, `lights.py`, `where.py`, `push.py`, `sitter.py`, `sensors.py`; `core.js`, `prefs.js`, `plant.js`, `weather.js`, `edit.js`, `care.js`, `lights.js`, `ui.js` (Display), `index.html`; `dev/test/sites_check.py` (new), `mock_server.py`; README, ARCHITECTURE, CHANGELOG.

## Step 4c: the plant-sitter sheet by link (added November 8, 2026; done in 1.49.0)

Ethan's sitters are outside his Tailnet, so the sheet needs one page reachable from the public internet without exposing anything else. Through Tailscale Funnel (already half set up for the calendar): a **Share by link** button on the sitter page (owner or editor) makes `https://<tailnet host>/share/<long random token>`; that path serves only the sheet for its dates and group, lets the holder tick each box (ticks are saved against the token and shown to Ethan), and stops working the day after the last day away. Nothing else is reachable through it; `guard()` lets `/share/` through the way it lets `/cal/` through, and the token is checked there. Finishing step 3 of the Funnel test is the prerequisite (done November 8). About 2 to 3 days, one minor release. Touches `sitter.py` (tokens, ticks), `sitter.html`/`sitter.js` (the share button and the read-only, tick-only mode), `core.py` (`guard()`), the Funnel configuration in `tailscale/`, README, a `share` browser check.

Built as planned in 1.49.0, with two differences: the sitter's page is its own `share.html` (large print, its own text-size, dark and contrast buttons, no sign-in and no Display settings to sync) with the renderer shared through `static/sitter-sheet.js`, and the Funnel path is added with one more `tailscale funnel` command on the PC rather than a change in `tailscale/` (the PC's own Tailscale, not the container, publishes `/cal` and `/share`). The browser check is `sitlink` (`share` was already taken by the 1.37.0 shared-photos check).

## Step 5: Identify in two modes, with a scoreboard

"Ever improving" needs a number first. The picture checker has been changed several times (the prior over Ethan's own species, houseplant genera and Texas plants; the look-alike step; the confidence fit) without an accuracy figure before or after, because `dev/vision/prior_test.py` and `eval_photos.py` need the model and have not been run on Ethan's PC.

**5a. Baseline (no release, an hour of the PC's time; done November 8, 2026, see `dev/vision/README.md`: species first 40% / top 5 61% on the common-or-US list with the prior, 33% / 54% without; the prior stays).** Run the two scripts against Ethan's own photos, which have known answers, and record top-1 and top-5 accuracy in `dev/vision/README.md`. Every later change to the checker reports the same two numbers in its CHANGELOG entry, and a change that lowers them does not ship. Commands are given for cmd.exe, PowerShell and bash.

**5b. Two modes (one minor, 4 to 5 days; done in 1.51.0).** The current prior is right for "which of my plants is this?" and wrong for "what is this, in a wood in another country?".

- "One of my plants": the checker as it is.
- "A new find": no lift for the person's own species or for houseplants; instead a lift for species recorded in the site's country, from GBIF occurrence counts cached in `data/vision` the way the USDA state list is now.
- Every page that identifies asks which mode to use, with the last answer offered first. A person can set a default per page in Display ("Don't ask on Identify: always a new find"), and then it does not ask there.
- The vision service takes a `scope` and a `country` with each request; the app sends them from the page and the site (step 4b; until then, the country is a setting).
- As built (1.51.0): the service takes `mode=mine|new` and `country=CC`; "new" drops the record's lifts (own species and genus, houseplants, look-alike photos) and lifts species GBIF records in the country, scaled by how often (`vision/gbif_country.py`: the `scientificName` facet of GBIF's occurrence search, paged 5,000 names at a time, about 50 s and 48,696 species for the US; kept as `data/vision/gbif-<CC>.json`, fetched in the background on first use). The question is a window with two big buttons, the last answer first, and a box that makes the answer the rule for that page; Display → Identify holds the rules (`plantdb.idmode`, synced). `prior_test.py` gained a "new find" row; Ethan runs it once the US list exists to measure the mode against the baseline.

**5c. The loop (one minor, 4 to 5 days; done in 1.52.0).** The checker learns from what people confirm.

- Every accepted identification keeps its photo's embedding with the name in `data/vision`, and the look-alike step searches those first. Ethan's 80 plants become 80 known examples; a second site adds its own.
- A rejection (`id_rejections` exists) lowers that name for photos that look like the rejected one, instead of only hiding it.
- Library pages get a "Confirm this is right" and "This is wrong" pair, so other people's confirmations count too, and the audit log says who.
- As built (1.52.0): the pair lives where there is a picture to confirm, on Identify's result cards ("This is right" beside "Not this") and on a plant's own page (the plant's main photo), not on library species pages, which have no picture of the person's to attach the answer to. Confirmations and picture rejections are rows in `id_examples` with the picture kept as `data/photos/ex_<hex>.jpg`; the checker reads them (and named mushroom finds) and keeps fingerprints in `examples-<MODEL>.npz`; a 'yes' lifts like the record's own look-alike photos, a 'no' lowers by the same amount. Editors and the owner only.

**5d. Mushrooms (one patch, 1 to 2 days; done in 1.51.1).** A photo is a weak lead for a fungus. The find record gets the fields a person uses to check a lead: substrate (wood, soil, dung, a named tree), habitat, cap, gills or pores, stem, spore print colour, smell, bruising. Plain fields with pick-lists, shown on the find's page and in its export. The rule that nothing in the app says a mushroom is edible or safe stays, and the field help text says so. As built (1.51.1): 1.22.0 already had substrate, cap, underside, ring, volva, spore print, bruising and smell; added `habitat` (a pick-list) and `stem` (text), pick-lists (a text box with the usual answers offered, any words allowed) on spore print, bruising and smell, the safety line in the form, `/api/fungi.csv`, and the finds in `/api/export.json`.

**Hardware.** Ethan's Radeon RX 7900 XTX can run BioCLIP through ROCm, which would make a batch identification of a whole folder of finds seconds instead of minutes. It is a second vision image (`vision/Dockerfile.rocm`) and a compose profile, not a change to the app, and it can wait until the CPU path feels slow.

**Touches.** `vision/service.py`, `vision/requirements.txt`, a GBIF fetcher beside `fetch_usda()`, `library.py`, `fungi.py` (schema and fields), `core.py` (schema), `discover.js`, `plant.js`, `gallery.js` (Add several), the fungi pages in `discover.js`, `prefs.js`, `dev/vision/*`, `docker-compose.yml` (GPU profile), `dev/test/identify_check.py` and `mushrooms_check.py`, README, ARCHITECTURE.

## Step 6: knowledge with provenance

A knowledge repository is only as good as its sources, and today most of the app's knowledge has one: Claude. Plant facts arrive in upgrade batches written from Ethan's photos and the care profiles in `dev/seed_src`, with sources listed in one text file. The `species_facts` table is a step in the right direction, but it stores each species as one blob with one origin, so a fact cannot be corrected on its own, and nobody but Claude can add one.

**6a. Facts as rows (one minor, 3 to 4 days; done in 1.53.0).** A `facts` table with one row per fact: species key, field (light, water, hardiness, toxicity, soil, origin, and so on), value, source (a link or a book), source kind (reference, trial, grower, own observation), who noted it, when, a confidence (certain, likely, unsure) and a status (accepted, proposed, retired).

- The Library page shows the accepted value per field with its source, and the history behind it when the field is opened.
- A plant's card reads from the species' accepted facts unless the plant has its own value, which is what `{field: [old, new]}` already protects.
- Existing `species_facts` blobs and the batch files are loaded into rows once, in place, with source "batch B4" and so on. Nothing anyone typed changes.
- As built (1.53.0): `app/plantdb/facts.py`. The field list (`FACT_FIELDS`) is the plant columns that describe a species rather than one pot (temperatures, humidity, light, water, soil, feeding, size and growth, hardiness, origin and safety, pests, propagation), the sections of the `species_facts` blob as `about_*`, and the sections of a Claude care sheet as `sheet_*`. The one-time load (`facts_migrate`, guarded by the setting `facts_loaded`) traces each plant value to the batch or first list that set it by replaying `seed.json` and `seed/batches/*.json` (`batch_sources`, `value_source`); a value no batch set is "Edited in the app on P-003 by Ethan" (own observation). A species fact is made only where every plant of the species agrees; genus-only names get none (a genus-wide fact from one pot would be a guess). On Ethan's record this gives about 2,800 rows, all but a handful traced. The plant page asks `/api/plants/<code>?fill=1` to read the species' facts for empty fields (`species_fill`); the edit form does not. `/api/facts/rows`, `/api/facts/export[.csv]`; batches add rows with `facts_add`. The front end is `js/facts.js`, two registered adds.

**6b. Editing and review (one minor, 3 to 4 days; done in 1.54.0).** Editors propose a fact or a correction from the Library or from a plant's page; any editor accepts or rejects it from a review queue (nobody accepts their own), and the audit log keeps who did what. Mushroom species notes (`species_notes`) join the same table with their own fields, under the same "never edible or safe" rule, enforced by the field list rather than by wording.

- An export (`/api/facts/export`, JSON and CSV) so the knowledge can move to another install or be shared, and an import that only adds proposed rows, never accepted ones.
- Batches keep working for the data Claude prepares, but they become one source among several.
- As built (1.54.0): `POST /api/facts/rows` (a proposed row; a source is required; numbers checked; a mushroom proposal is screened by `FACTS_FUNGUS_NO` and gets no care fields), `POST /api/facts/rows/<id>/accept` (not one's own unless owner; retires the old accepted row), `/reject` (with a reason), `GET /api/facts/queue`, `POST /api/facts/import` (proposals only). Front end in `js/facts.js`: "Suggest a change" and "Add a fact" on the species page, proposals as highlighted boxes with Accept/Reject for others, the "Facts to review" page (Plants section) and a Today block (order 72) for editors. The seed tooling rewrite (`dev/seed_src`) is left for the next batch that needs it: batches already add rows with `facts_add`.

**Cost.** Six to eight days, two minor releases, one in-place migration. The seed tooling in `dev/seed_src` gets a small rewrite so new batches write facts as rows directly.

**Touches.** `core.py` (schema), `library.py`, `fungi.py`, `audit.py`, `review.js` or a new `facts.js`, `plant.js` (the card), `events.js`, `style.css` (viewer block for the propose buttons), `dev/seed_src/*.py`, the batch format note in `app/seed/batches`, `dev/test/library_check.py`, README, ARCHITECTURE.

## Step 7: release rhythm

Eight releases in three days suits one user who installs them himself. With people at other sites it means several people updating weekly, and a change list written for them. This step is a habit, and most of it starts after step 3.

- One minor release a month, on the first day of the month; patch releases only for something broken. Prototypes still arrive as pull requests whenever they are ready, and merge when their checks and image builds are green; they wait for the month's release to ship.
- The CHANGELOG entry stays written for the people who use the app, with a line per site when a change only touches one kind of site.
- Install by pulling the images (step 3), so an update is a two-minute pull and restart rather than a build.
- A "What's new" line on Today after an update, read from the CHANGELOG, so nobody has to go looking.
- Backups before every update stay; a restore test once a quarter (the backups page has a restore) gets a reminder in the app.

**Touches.** `tools/make-release.py`, the two updater scripts, `docker-compose.yml`, `CHANGELOG.md`, a small Today line through the registry from step 2, README.

## Step 8 (proposed November 9, 2026, for Ethan's review): lights that fit the room

**The gap, in Ethan's words.** Every grow light holds itself in the room in its own way, and the Grow lights page does not know it. The SANSI 80 W folding bulb, 30 W and 10 W bulbs screw into an E26 socket, which itself comes as a lamp with a solid base, a clamp lamp or a bare socket on a cord. The SANSI tripod floor light has a three-legged base that takes floor space and a gooseneck arm that cannot point straight down. The Barrina 2 ft standing light has a wide flat base, lights sideways only, and any plant over a foot tall shades the ones behind it. The GooingTop two-bar clamp lights and the SANSI pot clips have short goosenecks and must clamp to a horizontal edge (a clamp on a vertical surface falls off). The Barrina 1 ft T5 strips and the SANSI 2 ft T8 strip screw under a surface, so they need something above the plants: the living room side table has nothing above it, the two brown shelves have levels, and the tall brown shelf's levels take a 1 ft T5 but not the 2 ft T8. So a light that is "technically enough" for the plants under it may have no way to be mounted where they are, and a plant may not fit the level it was given. Today he finds this out while carrying pots.

**What the page knows today.** A light model is PAR at a distance and a cone of coverage; a spot is one kind of light, how many, how far above or beside the plants, hours and dimming, assigned to a room or a shelf (`light_spots.place_id`, from `areas` and `spots`). The page already checks that the pots fit in the lit area (`room_needed_sqft` against `area_sqft`) and suggests a better spot for a plant that does not fit. It knows nothing about how the light mounts, what the place offers, how high the level is, or how tall the plant is. The app will never see the room, so the aim is not to replace the physical check: it is to catch most mismatches before a pot is carried, and to keep what the physical check found.

**8a. How a light holds (one upgrade batch for the light models, half a day).** Each light model gets a *mount* with a kind and a few numbers, in the model's `data` (no new table):
- `screw_socket`: screws into an E26 socket; the bulb inherits the mount of whatever fixture it sits in. A fixture is a small light model of its own (clamp lamp, lamp with a base, bare socket on a cord, the four-head gooseneck) with its own mount; `needs_socket` already exists for the bulbs, and the `fixture` column on a light already names it.
- `floor_stand`: footprint (inches across, the tripod's spread), height range (low and high), and how it points: `down`, `angled` (not straight down), `side`.
- `surface_stand`: footprint, fixed height, points `side` (the Barrina 2 ft standing light).
- `clamp_edge`: clamp opening (the thickest edge it grips), arm reach from the clamp to the light, points `down` or `angled`.
- `under_surface`: length and width it needs above the plants (the T5 and T8 strips, the 4 ft shop light), points `down`.
- `none` for a room light or anything that hangs from the ceiling by its own means.
The Lights page shows the mount in words on each light's card ("Screws under a surface at least 24 in long"; "Clamps to a horizontal edge up to 2 in thick, reaches 14 in"). The batch (C4) fills the mounts for the eleven known models (batch A3, plus the disk light) from their listings and from what Ethan has said; anything not known is left for Ethan to fill in on the light's page.

**8b. What a room or shelf offers (one minor's worth of fields, 1 to 2 days).** A room (`areas`) and a shelf or table in it (`spots`) get a *place sheet*: what is above it (nothing, a shelf at N inches, the ceiling at N inches), its width and depth, free surface or floor around it (inches), an edge to clamp to (yes/no, thickness), a socket within reach (yes/no), and whether it is a level in a stack (then its height to the next level). All optional; a place with no sheet behaves as today. **Photos of the place** (Ethan, November 9): a room and a shelf each take photos the way a pot does (`container_photos`, 1.27.0): a `place_photos` table (`area_id` or `spot_id`, file, caption, is_primary, added_by, added_at), the same shrink-and-save as plant photos, a main photo on the place's card on Rooms and spots, the whole set on the place's own page, and the main photo on the setup card (8e) and beside the place's name when a spot is set up, so "tall brown shelf, middle level" is a picture and not a memory. Photos go in `data/photos` with the rest, into backups and the mirror, and the sitter sheet by link gets the place photo next to its room heading. Set on the Rooms and spots page (`where.js`), one small form per place, and seeded for Ethan's known places by a batch where he has described them (the side table: one level, nothing above; the tall brown shelf: levels 11 in wide, 12 in apart, from his measurements once he gives them).

**8c. How tall a plant is (half a day).** Plants get a `height_in` (the plant today, pot included), set on the plant's page and on Add a plant, with "Taller than the last photo?" as a nudge in the monthly check-up rather than a chore of its own. `height_pot` already holds the *mature* height as text; this is the current one, a number, so the app can compare it with a level's clearance and with a sideways light's height.

**8d. Fits or does not (2 days).** When a spot is set up or a plant is added to one, the page runs the mount against the place before it runs PAR, and says so in words at the top of the spot:
- *Fits*: the mount has what it needs (a surface above long enough for an under-surface strip; an edge for a clamp within arm reach of the plants; floor or surface room for a stand's footprint; a socket for a bulb's fixture).
- *Does not fit because…*: one plain sentence naming the missing thing ("The tall brown shelf's levels are 11 in wide; the SANSI 2 ft T8 needs 24 in. A Barrina 1 ft T5 fits." / "The side table has nothing above it, so a strip cannot hang there. A floor light beside it or a clamp light on its edge would reach it.").
- *Shaded*: a sideways light lower than a plant in front of another ("The Barrina 2 ft standing light is 24 in tall; P-041 is 16 in and stands between it and P-052.").
- *Cannot point at them*: a stand whose arm cannot point down placed above the plants rather than beside them.
- *Too tall for the level*: a plant's height against the level's clearance.
The "It would suit … better" suggestion (1.41.0) takes the same test into account, so it never proposes a light that cannot be mounted where the plant is. A place with no sheet, or a light with no mount, gives "Not checked: fill in the shelf's measurements" rather than a false Fits, and the words never rely on colour.

**8e. The setup card and the tick (1 day).** Each spot gets a printable **setup card**: the light, how it mounts, at what height or distance, pointed where, which plants in which order (front to back for a sideways light), hours and dimming, with the Fits lines. Under it, **Set up and checked** records who ticked it and when, with a notes box for what reality said ("the gooseneck does not reach the back row"); the tick clears when the spot's light, place, distance or plants change, so a spot that was checked and then rearranged asks again. Today shows "N light spots not checked yet" only while there are some. The sitter sheet and the shelf labels take the spot's name as they do now.

**Cost.** Six to seven days in all (a day for the photos); one minor release, in the December 1 release under the rhythm from step 7; one in-place upgrade adding columns (`plants.height_in`, the place-sheet columns on `areas` and `spots`, the mount in `lights.data`) and the `place_photos` table and one upgrade batch (C4) for the light models. The fits test is pure arithmetic on the three sheets, so it gets unit tests of its own; a `mounting_check.py` browser check sets up the side-table and tall-shelf cases from Ethan's description and reads the sentences back.

**Touches.** `lights.py` (mount, fits test, setup card, tick), `where.py` (place sheet, place photos), `sitter.py` (the place photo on the sheet), `plants.py` and `core.py` (schema, `height_in` in the field list and export), `lights.js`, `where.js`, `plant.js`, `edit.js` (height on Add a plant), `checkup.js` (the nudge), `today` through the registry, `app/seed/batches/batchC4.json`, `dev/seed_src/build_batchC4.py`, `dev/test/mounting_check.py` (new), unit tests, README ("Grow lights"), ARCHITECTURE, CHANGELOG.

**Questions for Ethan.**
1. Measurements: the level widths, heights between levels and depths of the two brown shelves and the side table (a tape measure in inches is enough), and whether anything else holds plants indoors under lights.
2. Fixtures: which E26 fixtures you own (clamp lamps, lamps with a base, bare sockets), how many of each, and what each can clamp to or stand on.
3. Heights: is "plant plus pot, from the surface it stands on" the right height to record, and is once a month at the check-up often enough?
4. Would a sideways light shading plants behind a taller one (the Barrina 2 ft case) be worth a line of its own, or is "front to back by height" on the setup card enough?
