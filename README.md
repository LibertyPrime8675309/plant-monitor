# Plant database

Plant record is a web app for your plants: one page per plant with photos, names, what it needs (temperature, humidity, light, water, soil, feeding), where it lives, its care log and a full change history. It also keeps the weather, grow lights, mushroom finds, a plant library and the plan for each season. It runs in Docker on your PC and is opened in a browser. Phones and tablets can use it at home and, once set up, away from home.

This file has what you need to run it: starting, stopping, updating, versions, where your data is and how it is backed up. **How to use each part of the app is in the `manual` folder** beside this file; the list is at the end.

## Start it

You need Docker Desktop running. Open a terminal in this folder (the one containing `docker-compose.yml`). From 1.46.0 this downloads the ready-built containers from GitHub (a couple of minutes the first time); add `--build` to build them from this folder instead.

Windows (cmd.exe):

```
docker compose up -d
```

Windows (PowerShell):

```
docker compose up -d
```

macOS / Linux (bash):

```
docker compose up -d
```

Then open <http://localhost:8080>.

The first build takes a few minutes. The first start loads the plants into `data\plants.db` and copies the photos into `data\photos`.

## Stop, restart, update

Windows (cmd.exe):

```
docker compose stop
docker compose start
docker compose up -d --build
docker compose logs --tail 50
```

Windows (PowerShell) and macOS / Linux (bash): the same commands.

`up -d --build` rebuilds after you change anything in `app\`. Your data is not touched.

### Upgrading from an earlier version

Replace the old folder's contents with this one, but **keep your existing `data\` folder** (it holds your database and photos). Then, in the folder (from 1.46.0 this downloads the release's containers from GitHub; add `--build` to build them here instead):

Windows (cmd.exe):

```
docker compose pull
docker compose up -d
```

Windows (PowerShell):

```
docker compose pull
docker compose up -d
```

macOS / Linux (bash):

```
docker compose pull
docker compose up -d
```

On the first start the app adds anything new (from the first version: 26 plants, P-041 to P-066, and their photos; from 1.6.0: 11 plants, P-067 to P-077, and new photos for three existing pages; from 1.2.0: the new environment fields filled in on every plant page, see below) and each upgrade batch runs once. Version 1.2.0 also adds a new table for weather and sensor readings; the app creates it by itself. Version 1.3.0 adds a database index (the first start after upgrading takes a few seconds longer while it is built, more if you loaded many years of history) and two tables for daily weather and the update log. If you had already loaded years of history, press **Load history** once more with the same start date to fill in the extra measurements and the daily summaries; it only fetches what is missing. Anything you edited on P-040 stays as you left it: if the upgrade wants to change a field you already changed, it leaves that field alone and records a note in the change log. Back up `data\` first if you want a safety copy (see "Your data and backups").

### The updater (from 1.7.0)

The updater lives in the folder that holds `plant-database` (for example `C:\Users\Ethan\Documents\Claude\Plants`): `Update Plant Database.cmd` and `update-plant-database.ps1`.

From 1.12.2, release zips and photo packs are kept in a folder of their own beside it, **`versions_plant-database`**, so they don't clutter the Plants folder. Save new zips there. If you save one straight into the Plants folder instead, the updater moves it there for you. That's also how your older zips got moved.

Double-click **Update Plant Database.cmd**. It:

0. (from 1.55.0) asks GitHub for the newest release of Plant record. If it is newer than any zip in `versions_plant-database`, it downloads that release's zip there, and later any photo pack the release needs that you do not have. Nothing has to be saved into the folder by hand any more. If GitHub cannot be reached it says so and carries on with the zips already there; `-NoDownload` skips the question.
1. moves any `plant-database-….zip` files from the Plants folder into `versions_plant-database`. It finds the newest `plant-database-vX.Y.Z-YYYYMMDD-HHMM.zip` there and says which version is installed and which is running. If that version is already installed and running, it stops and changes nothing.
2. asks "Update to X? Type Y" (type `Y`, press Enter).
3. makes sure Docker Desktop is running, and starts it if not.
4. makes a backup through the app (it appears on the Backups page as "Before update"). If the running app is older than 1.7.0, it stops the app and copies `data\plants.db` into `backups\` instead.
5. unzips the release and copies it over the `plant-database` folder. **`data` and `backups` are never touched.**
6. adds plant photos from any photo packs the release needs (see below).
7. downloads the release's ready-built containers from GitHub (from 1.46.0; it builds them on your PC only if GitHub cannot be reached), runs `docker compose up -d` and waits until the new version answers.
8. lists the Docker images that older versions left behind (the app's and, from 1.18.0, the picture checker's, about 2 GB each) and offers to delete them to free disk space. With `-RemoveOldImage` it deletes them without asking.

#### Photo packs (from 1.8.0)

From 1.8.0, plant photos travel separately from the app, in **photo packs**. The release zip itself stays well under a megabyte.

- Each photo pack holds the photos from one plant update, for example `plant-database-photos-batch9.zip`.
- A pack never changes once it is made.
- A release only comes with the packs for the plant updates that are new in it.

Save any photo packs in `versions_plant-database` too (or in the Plants folder; the updater moves them). The updater adds the photos your `plant-database` folder does not have yet. Packs you already have are skipped.

If a release needs a pack that is not in the folder, the updater lists it and stops before changing anything. If photos arrive after you have updated (because you used `-Force`), run the updater again; it adds them even though the version is already up to date. You can delete a pack once it has been added.

Everything it does is written to `update-log.txt` in the Plants folder. Each new release carries the newest updater in `plant-database\tools`, and the updater copies it into the Plants folder, so it keeps itself current.

To run it from a terminal in the Plants folder instead:

Windows (cmd.exe):

```
"Update Plant Database.cmd"
powershell -NoProfile -ExecutionPolicy Bypass -File update-plant-database.ps1 -Yes
```

Windows (PowerShell):

```
.\update-plant-database.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\update-plant-database.ps1 -Yes -RemoveOldImage
```

macOS / Linux (bash), with PowerShell 7 (`pwsh`) installed:

```
pwsh -File ./update-plant-database.ps1
```

Options: `-Yes` (do not ask), `-Force` (re-apply the newest zip anyway), `-RemoveOldImage`, `-SkipBackup` (not recommended), `-Password <text>` (only if you set `PLANTDB_PASSWORD`), `-Url http://localhost:8080`, `-NoDownload` (from 1.55.0: do not ask GitHub, use only the zips already in the folder), `-Repo owner/name` (another GitHub repository to fetch releases from).

### Releases, What's new and the restore test (from 1.55.0)

A release is made by GitHub, not by hand. When a new version reaches the main branch, GitHub builds its containers, then publishes a **release** at `https://github.com/LibertyPrime8675309/plant-monitor/releases` with the release zip, every photo pack and the list of changes attached. The updater fetches from there (step 0 above), so updating is: double-click **Update Plant Database.cmd**, type `Y`.

The rhythm from December 2026: one release with new features on the **first of each month**, and in between only small fixes for something broken. Changes that are ready earlier wait for the month's release.

In the app:

- **What's new.** After an update, Today starts with "New in <version>" and that version's changes from the list (the first line, with the rest folded under "The rest of what changed"). **Got it** puts it away; it is remembered for you (each person has their own), and "Every version's changes" opens the whole list as a plain page.
- **Opening the new version (from 1.56.5).** A page left open during an update notices the new version the next time it asks the app for anything, and reloads itself once. If you are typing or a window is open, a bar at the top says **Version … is installed** with **Reload now** instead. Every file the page loads names the version, so one reload brings all of it.
- **An update is ready.** Twice a day the app asks GitHub whether a newer release exists. When one does, the owner sees "An update is ready: <version>" on Today, with a link to what changed, until it is installed. Only the owner sees it, because only the owner's PC can install it. The container can be told not to ask with `PLANTDB_UPDATES=0` in `docker-compose.yml`.
- **Test a restore.** Backups are only as good as a restore, so once a quarter the owner's Today has "Test a restore" when none has been done for 90 days (or ever). Do it on the Backups page: **Back up now**, then **Restore** on that newest backup. The database from just before the restore is kept as another backup, so nothing is lost, and the reminder goes away for three months.

### Built on GitHub first (from November 2026)

Every change to the app on GitHub builds all three container images (the app, the picture checker and the speech service) on GitHub's own machines before it can be merged, so a broken Dockerfile is caught there rather than on your PC. The images are kept in GitHub's registry under the repository (`ghcr.io/libertyprime8675309/plant-database`, `...-vision`, `...-speech`, tagged with the version); the repository and the images are public, so no sign-in is needed.

**From 1.46.0 the updater downloads those ready-built images instead of building them on your PC.** An update takes a couple of minutes rather than ten or more, and nothing is compiled on your computer. If GitHub cannot be reached, the updater builds the images from the folder as before, which still works offline from GitHub as long as Docker Hub can be reached for the base image.

From 1.57.0 the Python libraries the app uses are fixed at known versions (`requirements.txt`), so a rebuild never picks up a new library by surprise. Once a week GitHub's Dependabot proposes updates to them, to the base images in the Dockerfiles and to GitHub's own build steps, as pull requests; each one goes through the same checks before it can be merged, and nothing changes on your PC until a release.

## Version

The `VERSION` file holds this package's version, and `CHANGELOG.md` lists what changed in each one. Keep each zip you receive (the file name carries the version and build time) as your archive; they all collect in `versions_plant-database`.

### Which version is running?

- **In the app**: the version shows next to "Plant record" at the top of every page (for example `v1.6.2`), and at the top of the **Display** settings.
- **In Docker Desktop**: open **Containers**; the **Image** column for `plant-database` shows the version, for example `ghcr.io/libertyprime8675309/plant-database:1.46.0` (before 1.46.0 the images were built on your PC and named `plant-database:1.6.2`). The **Images** list shows one entry per version you have had.
- **From a terminal** (in the project folder):

Windows (cmd.exe):

```
docker ps --filter name=plant-database --format "{{.Image}}"
curl http://localhost:8080/api/version
```

Windows (PowerShell):

```
docker ps --filter name=plant-database --format "{{.Image}}"
Invoke-RestMethod http://localhost:8080/api/version
```

macOS / Linux (bash):

```
docker ps --filter name=plant-database --format '{{.Image}}'
curl http://localhost:8080/api/version
```

If the version in the app is older than the newest zip in your folder, that update has not been applied yet.

Each update leaves the previous version's images behind until the updater deletes them (it asks at the end). To see them yourself, and to delete one by its name and version:

Windows (cmd.exe):

```
docker image ls --filter "reference=*plant-database*"
docker image rm ghcr.io/libertyprime8675309/plant-database:1.46.0 ghcr.io/libertyprime8675309/plant-database-vision:1.46.0
```

Windows (PowerShell) and bash: the same commands. Never delete the images for the version that is running.

## Where the data is stored

Everything, including weather, sensor readings and the fertilizer log, is in `data\plants.db` in this folder (the `data` folder next to `docker-compose.yml`). The tables are `readings` (every weather, sensor and typed-in reading), `fertilizer_log`, and `settings` (forecast, location, sensor token) beside the plant tables. To look inside, copy the file first and open the copy with a free viewer such as DB Browser for SQLite.

Windows (cmd.exe):

```
copy data\plants.db plants-copy.db
```

Windows (PowerShell):

```
Copy-Item data\plants.db plants-copy.db
```

macOS / Linux (bash):

```
cp data/plants.db plants-copy.db
```

The weather tables are `locations` (your places), `readings` (hourly; sensors and weather, with the place in the `device` column: `open-meteo` for the original home place, `place-2` and so on for places you add), `weather_daily` (daily summaries, by place) and `weather_runs` (the update log, by place). To see how big the database is:

Windows (cmd.exe):

```
dir data\plants.db
```

Windows (PowerShell):

```
Get-Item data\plants.db | Select-Object Name, @{n="MB";e={[math]::Round($_.Length/1MB,1)}}
```

macOS / Linux (bash):

```
ls -lh data/plants.db
```

### Saving mode (from 1.57.0, optional)

The app saves to the database in the way that is safe on every computer (SQLite's "DELETE" journal). A faster way, "WAL", lets pages keep reading while a save is being written, which helps when several people use the app at once. On some Windows folders shared with Docker it does not work, so the app tests it first: when it starts, it writes and reads a small test database in the `data` folder, and uses WAL only if that works. Otherwise it stays as it is and says why. **Settings, Health of the app** shows the saving mode in use whenever WAL was asked for.

To try it, make a backup first (**Backups**, **Make a backup now**), then add a line to the `.env` file next to `docker-compose.yml` and restart the app:

Windows (cmd.exe):

```
echo PLANTDB_JOURNAL=WAL>> .env
docker compose up -d
```

Windows (PowerShell):

```
Add-Content .env "PLANTDB_JOURNAL=WAL"
docker compose up -d
```

macOS / Linux (bash):

```
echo PLANTDB_JOURNAL=WAL >> .env
docker compose up -d
```

To go back, delete that line from `.env` (open it with `notepad .env` on Windows) and run `docker compose up -d` again. With WAL on, the database is three files while the app runs (`plants.db`, `plants.db-wal` and `plants.db-shm`), so copy it with **Backups** rather than by copying `plants.db` by hand.

For a spreadsheet, use the **Weather** page's table (any columns, any dates) or the **Audit log** page: "Download weather and sensor readings (CSV)".

## Your data and backups

Everything is in the `data` folder next to `docker-compose.yml`:

- `plants.db`: all records, versions and the change log
- `photos`: every photo
- `photos_deleted`: photos you removed (kept so you can recover them by hand)

### The Backups page (from 1.7.0)

Open **Backups** in the menu.

- **Back up now** makes a backup straight away. Add an optional note. **Include the photos** is ticked to start with (from 1.58.0, unless your photos come to more than a gigabyte); untick it for the database alone.
- **Automatic backups**: switch them on or off and choose:
  - how often: every 6 hours, every 12 hours, daily, every 3 days or weekly
  - the hour of day
  - how many automatic backups to keep (older automatic ones are deleted; backups you make yourself are never deleted automatically)
  - whether to include the photos. From 1.58.0 they are included unless you untick the box. A record that had the box unticked was switched over once when 1.58.0 was installed (the Audit log says so), unless its photos come to more than a gigabyte; untick it again and it stays unticked. If they are left out, the top of the Backups page says so, with a button to put them in.
- **Backups made before an update** (the updater makes one each time): from 1.58.0 the newest 5 are kept and older ones are deleted. Before that they were never deleted, one for every version installed.
- **Weather history** (from 1.58.0) has a backup of its own, in pieces, on its own schedule. Nearly all of the database is weather history, and little of it changes from day to day, so every backup used to carry the same 50 MB again.
  - The first piece holds everything. Each later piece holds only the days that are new or have changed. All the pieces together are the whole history.
  - Choose how often (every day, 3 days, week, 2 weeks or month; it starts as every week) and the hour. A run with nothing new makes no file. **Back up the weather now** makes a piece straight away.
  - **Combine the pieces into one** writes one new piece with everything, checks it, and only then removes the old ones. Past 26 pieces this happens by itself.
  - **Put missing weather back from the pieces** adds the days your record lacks. It never changes or removes weather the record has.
  - Once the first piece is made, the other backups leave the weather out, which makes them a few megabytes. The list says "without the weather history" on those. Restoring one of them keeps the weather your record has; if the record has none (a new computer), it is put back from the pieces.
  - Untick **Back up the weather history by itself** and the other backups carry the whole weather history again.
- The **Your backups** list shows each backup with a Download and a Delete button.

Backups are zips named `plantdb-backup-YYYYMMDD-HHMMSS-<manual|auto|update>.zip`. Each holds `plants.db`, a `backup.json` describing it and, if chosen, a `photos` folder. They are saved in the `backups` folder next to `data`, so updates do not touch them. That folder is still on the same disk, so copy a few to another drive or cloud folder now and then.

The pieces of the weather backup are zips named `plantdb-weather-YYYYMMDD-HHMMSS-<full|part>.zip` in `backups\weather`. Each holds `weather.db` (a small SQLite database with the hourly readings and the day summaries it carries) and `piece.json`, which lists the days in it. A piece is never changed once written. If a second folder is set for backups (`PLANTDB_COPY_DIR`), each piece is copied to a `weather` folder there too. Pieces are not sent to the other computer's receiver yet, so a mirror shows no weather history.

The app must be running for automatic backups. If it was off when one was due, that backup runs within a few minutes of the next start.

### Restoring a backup

Stop the app, keep the current database under another name, put the backup's `plants.db` in its place, and start the app again. The example uses `plantdb-backup-20261021-030000-auto.zip`; use your file's name.

Restoring from the Backups page is simpler and keeps your weather history. Done by hand as below, a backup made from 1.58.0 on has no weather history in it: a few minutes after the app starts it puts the weather back from the pieces in `backups\weather` by itself (or press **Put missing weather back from the pieces** on the Backups page). Anything the pieces do not hold is downloaded again over the following hours.

Windows (cmd.exe):

```
docker compose down
ren data\plants.db plants-old.db
tar -xf backups\plantdb-backup-20261021-030000-auto.zip -C data plants.db
docker compose up -d
```

If the backup has photos, also run `tar -xf backups\plantdb-backup-...zip -C data photos` before starting.

Windows (PowerShell):

```
docker compose down
Rename-Item data\plants.db plants-old.db
Expand-Archive backups\plantdb-backup-20261021-030000-auto.zip -DestinationPath restore-tmp
Copy-Item restore-tmp\plants.db data\plants.db
if (Test-Path restore-tmp\photos) { Copy-Item restore-tmp\photos\* data\photos -Recurse -Force }
Remove-Item restore-tmp -Recurse
docker compose up -d
```

macOS / Linux (bash):

```
docker compose down
mv data/plants.db data/plants-old.db
unzip -o backups/plantdb-backup-20261021-030000-auto.zip plants.db -d data
unzip -o backups/plantdb-backup-20261021-030000-auto.zip 'photos/*' -d data   # only if it has photos
docker compose up -d
```

Once the restored data looks right, you can delete `data\plants-old.db`.

### Copying the whole data folder by hand

Windows (cmd.exe):

```
docker compose stop
xcopy data data-backup /E /I /Y
docker compose start
```

Windows (PowerShell):

```
docker compose stop
New-Item -ItemType Directory -Force data-backup | Out-Null
Copy-Item data\* data-backup -Recurse -Force
docker compose start
```

macOS / Linux (bash):

```
docker compose stop
cp -r data data-backup
docker compose start
```

You can also download everything from **Audit log**: plants as CSV, the change log as CSV, or all data as JSON. To start over with the original 77 plants, stop the app, delete the contents of `data`, and start it again.

## Notes

- Photos are re-saved when uploaded (JPG, max 1600 px). Location data in the photo is removed. iPhone HEIC files are not supported; use JPG or set the phone camera to "Most Compatible".
- Plant IDs are Claude's best reading of the photos. Low-confidence plants say what would settle it.
- Fonts (Spectral, Atkinson Hyperlegible) are bundled under the SIL Open Font License; nothing loads from the internet.
- "Expected" weather figures are climate averages for Round Rock / Austin; the sources are listed on the Winter plan page. Tracked figures come from Open-Meteo and your sensor.
- Plant pages and the Display settings were designed for low vision: large type, high contrast, roomy spacing and no tiny tap targets. If something is still hard to read, tell Claude which page and what size and it will be changed.

## The manual
Each page below is a file in the `manual` folder. When the app says "see README" and names a section, find the name here.

### Display, text size and finding your way: `manual/display.md`
- Units: °F or °C, inches or centimetres
- Display settings and low vision: Pop-up windows; Read aloud and keyboard shortcuts; Section menu ("Navigation", called "On this page" before 1.42.0)
- Room for the content
- One identifier
- Finding your way, summer heat for each plant, probe calibration and the health of the app: Every page in its section's row; Summer heat for each plant; Calibrating a soil probe; Soil moisture on the plant's page; Health of the app; Clear the saved pages; Buttons that say what they do
- The top bar, rooms and spots, pots and trays, editing on the page, and settings that follow you: The top bar; Rooms and spots; Pots and trays; Editing on the page; Settings that follow you
- High Contrast, Problems, Restore, and a home per person
- What's in the pages
- Search by voice: The speech service

### Your plants and their pages: `manual/plants.md`
- Photos on the Plants page, and the main photo
- Plants page filters
- Date acquired
- Previous and next plant
- Location: outdoors or indoors
- Plant timeline
- Photo check
- Current conditions and the "Now" marker
- Location
- Environment fields on every plant page
- Past days: what the values were on a date
- Plant links and previews
- Plant labels
- Who made a change
- Groups of plants
- Homes, adding several plants, and your plant photos: Homes; A home is a site; Add several plants at once; Your plant photos (Identify page); Not tied to Texas
- About this plant
- Audit log: Debug button and the audit log console
- Large-print care cards

### Today, watering and care: `manual/care.md`
- Today page, watering and care
- Today as the home page, the shopping list, speaking a note, room labels and summer heat: Today is the page the app opens on; The shopping list for a store visit; Speak a note; Room, area and shelf labels; Summer heat next to winter cold
- Fertilizer calendar and log
- Your plant calendar: Reaching the calendar from the internet with Tailscale Funnel
- Undo right after a care button
- Repotting
- Turn the pots
- Health walk-through
- Plant-sitter sheet: Share the sheet by link
- What is in each pot
- Shopping, stores, and quicker pages
- Jobs

### Weather, cold nights and sensors: `manual/weather.md`
- Frost alert and cold-night checklist
- Getting plants ready to come inside
- Back outside in spring
- Weather and sensors: More than one place; Everything Open-Meteo offers is now collected; Tracked history charts; The table of everything logged; Update log; Connecting your own sensor
- Your sensors: An ESP32 sensor node with ESPHome
- Frost dates

### Identify, the Library, mushrooms and plant knowledge: `manual/identify-and-library.md`
- Identify a plant and the plant library: The first start; Using the camera; Names for plants that aren't yours; Second opinions: Pl@ntNet and Claude; The plant library; Stopping the picture checker; A smaller, faster model
- Better names from Identify: Two ways to identify; The checker learns from you
- Mushroom finds
- Facts and where they come from: Adding and correcting facts
- Uses, partners and propagation
- Propagation and breeding guide

### Grow lights: `manual/lights.md`
- Grow lights
- Lights that fit the room
- Compare lights

### Away from home, on the phone and offline: `manual/away-and-offline.md`
- Using the app away from home: One-time setup; Sharing it with someone (for example your girlfriend); Who can do what; Security, in short; Which user the app runs as; Opening it to your home network again (less safe); The names this computer answers to; If something doesn't work
- On the phone and offline: Watering offline; When Tailscale comes back; Back goes back to where you were; Photos on the Add a plant form; Adding a plant without a connection; Several plants from photos, on a phone
- Offline use on phones and tablets
- Photos from your phone, the year in review, and the mirror: Share a photo from your phone; The year in review; The mirror: a read-only copy on another machine
- Notifications, a second copy of backups, and search: Notifications; Second copy of backups; Search everywhere

### Working with Claude: `manual/claude.md`
- What Claude needs from you: Copy my answers for Claude
- Updates from Claude

### Missing details (prototype): `manual/missing-details.md`
- Missing details (prototype)
