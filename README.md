# Plant database

A web app for your outdoor plants: one page per plant with photos, names, temperature / humidity / sunlight ranges, winter care, ID confidence, health notes, and a full change history. It runs in Docker on your PC and is opened in a browser. Phones on your Wi-Fi can use it too.

77 plants and 108 photos are pre-loaded from the pictures you sent. Claude wrote the first version of every page (the history shows "Claude (initial analysis from photos)" for P-001 to P-040, "Claude (batch 2, from photos)" for P-041 to P-066 and "Claude (batch 6, from photos)" for P-067 to P-077).

## Start it

You need Docker Desktop running. Open a terminal in this folder (the one containing `docker-compose.yml`).

Windows (cmd.exe):

```
docker compose up -d --build
```

Windows (PowerShell):

```
docker compose up -d --build
```

macOS / Linux (bash):

```
docker compose up -d --build
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

Replace the old folder's contents with this one, but **keep your existing `data\` folder** (it holds your database and photos). Then, in the folder:

Windows (cmd.exe):

```
docker compose up -d --build
```

Windows (PowerShell):

```
docker compose up -d --build
```

macOS / Linux (bash):

```
docker compose up -d --build
```

On the first start the app adds anything new (from the first version: 26 plants, P-041 to P-066, and their photos; from 1.6.0: 11 plants, P-067 to P-077, and new photos for three existing pages; from 1.2.0: the new environment fields filled in on every plant page, see below) and each upgrade batch runs once. Version 1.2.0 also adds a new table for weather and sensor readings; the app creates it by itself. Version 1.3.0 adds a database index (the first start after upgrading takes a few seconds longer while it is built, more if you loaded many years of history) and two tables for daily weather and the update log. If you had already loaded years of history, press **Load history** once more with the same start date to fill in the extra measurements and the daily summaries; it only fetches what is missing. Anything you edited on P-040 stays as you left it: if the upgrade wants to change a field you already changed, it leaves that field alone and records a note in the change log. Back up `data\` first if you want a safety copy (see "Your data and backups").

### The updater (from 1.7.0)

Save new release zips in the folder that holds `plant-database` (for example `C:\Users\Ethan\Documents\Claude\Plants`). The updater lives in that same folder: `Update Plant Database.cmd` and `update-plant-database.ps1`. Double-click **Update Plant Database.cmd**. It:

1. finds the newest `plant-database-vX.Y.Z-YYYYMMDD-HHMM.zip` in the folder and says which version is installed and which is running. If that version is already installed and running, it stops and changes nothing.
2. asks "Update to X? Type Y" (type `Y`, press Enter).
3. makes sure Docker Desktop is running, and starts it if not.
4. makes a backup through the app (it appears on the Backups page as "Before update"). If the running app is older than 1.7.0, it stops the app and copies `data\plants.db` into `backups\` instead.
5. unzips the release and copies it over the `plant-database` folder. **`data` and `backups` are never touched.**
6. adds plant photos from any photo packs the release needs (see below).
7. runs `docker compose up -d --build` and waits until the new version answers.
8. offers to delete the previous version's Docker image to free disk space.

#### Photo packs (from 1.8.0)

From 1.8.0, plant photos travel separately from the app, in **photo packs**. The release zip itself stays well under a megabyte.

- Each photo pack holds the photos from one plant update, for example `plant-database-photos-batch9.zip`.
- A pack never changes once it is made.
- A release only comes with the packs for the plant updates that are new in it.

Save any photo packs in the same folder as the release zip. The updater adds the photos your `plant-database` folder does not have yet. Packs you already have are skipped.

If a release needs a pack that is not in the folder, the updater lists it and stops before changing anything. If photos arrive after you have updated (because you used `-Force`), run the updater again; it adds them even though the version is already up to date. You can delete a pack once it has been added.

Everything it does is written to `update-log.txt` in the same folder. Each new release carries the newest updater in `plant-database\tools`, and the updater copies it next to the zips, so it keeps itself current.

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

Options: `-Yes` (do not ask), `-Force` (re-apply the newest zip anyway), `-RemoveOldImage`, `-SkipBackup` (not recommended), `-Password <text>` (only if you set `PLANTDB_PASSWORD`), `-Url http://localhost:8080`.

## Version

The `VERSION` file holds this package's version, and `CHANGELOG.md` lists what changed in each one. Keep each zip you receive (the file name carries the version and build time) as your archive.

### Which version is running?

- **In the app**: the version shows next to "Plant record" at the top of every page (for example `v1.6.2`), and at the top of the **Display** settings.
- **In Docker Desktop**: open **Containers**; the **Image** column for `plant-database` shows `plant-database:1.6.2`. The **Images** list shows one entry per version you have built.
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

If the version in the app is older than the newest zip in your folder, that update has not been applied yet. Each update leaves the previous image behind; to free the space, remove old ones with `docker image rm plant-database:1.6.1` (any shell), using the old version number.

## Use it from your phone

1. Find your PC's address on the Wi-Fi.
   - Windows (cmd.exe): `ipconfig` and look for "IPv4 Address" (for example `192.168.1.20`).
   - Windows (PowerShell): `Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '169.*' -and $_.IPAddress -ne '127.0.0.1' } | Select-Object InterfaceAlias, IPAddress`
   - macOS: `ipconfig getifaddr en0`
   - Linux (bash): `hostname -I`
2. On the phone (same Wi-Fi), open `http://192.168.1.20:8080` (use your address).
3. If it does not load, Windows Firewall may be blocking port 8080. Allow Docker Desktop on private networks when Windows asks, or add a rule:
   - Windows (cmd.exe, run as administrator): `netsh advfirewall firewall add rule name="Plant database" dir=in action=allow protocol=TCP localport=8080 profile=private`
   - Windows (PowerShell, run as administrator): `New-NetFirewallRule -DisplayName "Plant database" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080 -Profile Private`

## Display settings and low vision

Press the **Display** button (bottom right of every page; it stays on screen) to change how everything looks. Changes apply at once and are remembered in that browser (each computer or phone keeps its own).

- **Text and button size**: Standard, Comfortable (the new default, a little bigger than before), Large, Larger, Largest. Buttons, bars, charts and spacing scale together.
- **Spacing**: Normal or Roomy (more space between lines, letters and words).
- **Contrast**: Normal or High (black and white with heavier outlines).
- **Colours**: match your device, light or dark.
- **Plant pages**: photos and details side by side, or one column.

On a plant page in side-by-side view, the photos (left) and details (right) each scroll on their own: put the pointer over the half you want to move and scroll. A "Switch to one column" button at the top of the page does the same as the Display setting. With very large text or a narrow window the page switches to one column automatically. The row of section buttons (Now, Temperature, Humidity, Light, Water and soil, ...) jumps straight to a section; in side-by-side view it steps aside while the On this page menu is open, because the menu lists the same sections. All parts of the page can also be reached with the Tab key.

On a phone the menu bar at the top scrolls away with the page (scroll back to the top to reach it), and every page fits the width of the screen at every text size. With the two largest text sizes, the Sections button sits just above the Display button.

### Read aloud and keyboard shortcuts (from 1.8.0)

Every section has a **Read aloud** button. Your browser reads that section in its own voice, the section gets a dashed outline while it is read, and a big **Stop reading** button stays at the bottom of the screen. **Read this page aloud**, under the page title, reads the whole page. In **Display** you can hide the buttons, pick the **Reading speed** (slower to fastest) and the **Voice**, with **Try this voice**. In Microsoft Edge the "Natural" voices sound the most human.

Keyboard shortcuts work on every page, except while you are typing in a box. **Display** can turn them off.

| Key | What it does |
|---|---|
| **R** | Read this page aloud |
| **Escape** | Stop reading |
| **[** and **]** | Previous and next plant |
| **E** | Edit this plant |
| **/** | Search plants |
| **H** | Go to the Plants page |
| **M** | Open or fold the section menu |
| **?** | List the shortcuts |

### Section menu ("On this page")

Every page has a menu down the side listing its sections (for example on the Weather page: Tracked history, All logged weather data, Location and updates). Choose one to jump straight to it; the section you are reading is highlighted. On plant pages it scrolls the details half, like the section buttons.

- **Hide** folds the menu away; the **Sections** button at the edge of the screen brings it back.
- **Move to the right / Move to the left** swaps its side.
- The same choices, plus **Page width: Use the full width of the window** (more room for charts and tables on a wide screen), are in **Display**. They are remembered on that computer.
- On phones, narrow windows and very large text the menu starts folded, the Sections button sits at the bottom left, and the menu closes after you choose a section.

## Previous and next plant (from 1.7.5)

Every plant page has **Previous Plant** and **Next Plant** buttons, each showing the name and code of the plant it leads to. On a wide screen they sit in the margins either side of the page; on smaller screens and phones they sit at the top of the page.

They follow the Plants page filters and sort order. The fold-out **Filters for Previous / Next** panel at the top of each plant page has the same filters (search, winter plan, health, sort, "needs something from you", ID under 70%) and shows where the plant falls in the list. Changing a filter in either place changes it in both, and this browser remembers it.

## Location: outdoors or indoors (from 1.7.0)

The label at the top of every plant page now starts with **Location**: Outdoors, Covered porch, Indoors, or Garage or shed. It is a menu. Click it (or Tab to it and use the arrow keys) and pick another place, and the change is saved straight away and recorded in the page history. The old free-text "Location" field, for example "Covered porch pallet shelf", is now called **Spot**.

On the **Winter plan** page each plant in "Plant by plant" has a **Moved indoors** button. Pressing it sets the plant's Location to Indoors and takes it off those lists. It is also left out of the frost warnings in "The next 7 days". Plants already inside are listed under **Already inside**, each with a **Moved back outside** button. After upgrading to 1.7.0, every plant started as Outdoors; 1.8.0 set the plants whose Spot is on the covered porch to Covered porch, unless you had already changed them.

## Today page, watering and care (from 1.8.0)

The **Today** link in the menu lists what to do today, most urgent first:

- **Water:** plants due or overdue for a check, each with **Watered** and **Still moist**, and **Watered all** for a whole round. "Check tomorrow" lists the next day's plants. "No watering logged yet" has one button, **I watered all today**, to start the reminders for all of them.
- **Feed:** plants due for fertilizer today, with **Log feeding** (the same schedule as the Fertilizer page).
- **Needed from you:** the open requests, with links to answer them.

Every plant page has **quick care buttons** under its label, big enough to use on a phone in the garden after scanning the plant's label: **Watered today**, **Checked: still moist**, **Log feeding**, **Add a photo** (opens the phone's camera) and **Log other care** (repotted, pruned, treated for pests, or a note, with a date). The line above them says when the plant was last watered and when to check it next. The plant's **Water and soil** section explains the reminder and has its **care log**, with a **Remove** button on each entry.

How the reminders work:

1. The starting gap comes from how dry the plant likes to be: 14 days for plants that dry out completely (cacti, aloes), 10 for plants that dry out between waterings, 7 when the top of the mix should dry, 5 for evenly moist, and 4 for constantly moist (ferns, calatheas).
2. Hot weather (highs of 85°F or more) shortens it; cool weather and being indoors lengthen it.
3. Rain of 0.25 in or more on one day counts as a watering, but only for plants whose Location is Outdoors (not the covered porch).
4. **Checked: still moist** moves the next check a third of the gap later.
5. To set the gap yourself, fill in **Check for water every (days)** on the plant's Edit page.

## Frost alert and cold-night checklist (from 1.8.0)

When a night in the 7-day forecast would hurt a plant that is outside, a banner at the top of the page says how cold it will get and on which night, how many plants could die, would be damaged or are close calls, and when to act ("before dark today"). It is called "Frost warning" at 36°F or below and "Cold warning" above that, because the tropical plants are hurt at 50 to 60°F. **Hide until the forecast changes** hides it until the forecast gets colder or more plants are at risk. Plant pages show their own **Frost risk** note instead of the banner.

**Open the cold-night checklist** (on the banner, or on the Winter plan page) shows the next 7 nights, then each plant once, most urgent first, in three groups: **Bring inside**, **Cover or move to shelter**, and **Close calls** (within 3°F of the damage point). Each plant has **Moved indoors** (sets its Location to Indoors, so it leaves every list and warning) and **Covered for tonight** (ticks it off for its next cold night only, since covers go back on each night), with **Undo**. Each group also has a button for all its plants, which asks first. Tips for a cold night are at the bottom.

Plants set to Indoors or Garage or shed are never counted. Plants on the Covered porch are.

## Plant timeline (from 1.8.0)

Each plant page has a **Timeline** section, just above Page history (also in the On this page menu):

- how the plant is doing over time, for example "Health: Critical until Oct 22, Poor now (getting better)"
- **Compare two photos:** the oldest and newest photo side by side. Pick others with the **Left photo** and **Right photo** menus, or press **Compare** under any photo in the list.
- **Everything that has happened**, newest first and grouped by day: photos, changes to the page (the important ones in words, such as "Health rating: from Fair to Poor"), feeding and care, answered requests, and when the page was created. Tick boxes under **Show** hide any kind.

## Getting plants ready to come inside (from 1.9.0)

Outdoor plants often carry ants, spider mites, mealybugs and other pests. Each plant page has a **Getting ready to come inside** section, after Winter in Round Rock, that helps keep them out of the house.

1. Under **About this plant**, check the **Leaf type** and choose the **Pot size**. Claude filled in the leaf type for every plant; change it if it is wrong.
2. Inspect the plant (the first method explains how) and tick any **Pests you found**. Leave them all unticked if you found nothing.
3. The ten methods are listed in the order to do them, each rated for this plant: **Best**, **Good**, **Use with care**, **Not needed** or **Not for this plant**, with the reason. Open **How to do it** for the steps. Methods that are not needed or not suitable are folded away under one line.
4. Press **Done today** after each one. It goes into the care log, the timeline and "Copy my answers for Claude". **Undo the last one** takes it back. To record a step done on an earlier day, use **Log other care**.
5. If a spray needs a second round, the **Today** page reminds you 5 days later.
6. When the plant comes inside, change its Location to Indoors (or press **Moved indoors**). The section then says until when to keep it apart from your other houseplants: 3 weeks, or 2 weeks after its last treatment if you found pests.

The page **Getting plants ready to come inside** (button on the Winter plan page, and links on the cold-night checklist and the Today page) lists every plant coming in, grouped as Not started, In progress, Ready to come inside, and Inside. Each one shows its next step and best methods, and **Open its plan** goes straight to that plant's section. The page also has the steps for all ten methods and advice on keeping plants apart.

Pots are never cleaned with bleach: use hot soapy water, a brush and a day in the sun, or for extra cleaning 10 minutes in 3% hydrogen peroxide (never mixed with vinegar or other cleaners), then rinse. A new pot works too.

## Photo check (from 1.8.0)

When you add photos, each one is checked in your browser first. Photos that look fine are added straight away. If any look **blurry**, **too dark**, **too bright (washed out)** or are a **very small picture**, a box shows them with what to do, and these buttons: **Take a new one** (opens the camera or file picker again), **Add only the good ones**, **Add it anyway** and **Cancel**. Nothing extra is sent anywhere.

## What Claude needs from you

When Claude needs something to finish a plant's page (a check, a question, a photo or ID details), it is listed at the top of that plant's page under **Needed from you**, with **Answer** and **Mark done** buttons. Answers are kept on the page and in the change log. To send them to Claude, use **Copy my answers for Claude** (below). On the **Plants** page, **Show plants that need something from you** filters to just those plants; plants whose identification is under 70% sure are included, with what would help. Things to photograph that are not in the database yet are on the **Photos** page.

### Copy my answers for Claude (from 1.8.0)

**Copy my answers for Claude** is on the Plants page (it says how many answers are new, for example "(2 new)") and in "Needed from you" on each plant page. It puts everything you have done since you last copied into one message: your answers first, then changes to plant pages, photos added, feeding and care, and the "Still to photograph" list. Press **Copy message**, then paste it into your chat with Claude (Ctrl+V). **Save as a text file** puts the same message in your Downloads folder instead.

Next time it starts from where the last copy ended, so nothing is sent twice. **What to include** can also be "The last 7 days", "The last 30 days" or "Everything", and **Also list what is still open** adds the open requests and photos, which helps when you start a new chat. Photos themselves can't go in the message, so attach any you want Claude to look at.

## Current conditions and the "Now" marker

Each plant page has a **Current conditions** box. Press **Set current conditions** (or **Change**) and choose where the numbers come from:

- **I will type them in**: temperature (F), humidity (%), and light as PAR or lux. The dialog lists rough light values to use if you have no meter (full midday sun 1,500 to 2,000 PAR, open shade 200 to 600, under a porch roof 100 to 400, bright window 100 to 300, lamp-lit room 5 to 30).
- **My sensor**: the newest reading your sensor sent (see below).
- **Online weather**: the latest hour from Open-Meteo for your location. This is open sky, so plants under a roof or in shade get less light than it says.

The setting is shared by all plant pages. Every gauge (temperature, humidity, light, soil moisture, soil temperature, soil pH) then shows a labelled **Now** marker. When a value is outside the plant's range, the page gets a **Getting this plant back in range** section with numbered steps for that plant and that situation (for example how to protect it from a cold night, or how to raise humidity). Readings that are old are flagged as out of date.

## Weather and sensors

The **Weather** page replaces the fixed weather table. It has:

- a 7-day forecast for your location, with freezing nights marked and a count (and list) of plants that would be damaged at each night's low;
- charts of temperature, humidity and light over the last day, 3, 7, 14, 30 or 90 days, or a year, from online weather and from your sensor, with a table of the numbers under each chart and an option to overlay one plant's comfortable range;
- an Expected-and-tracked table for October to March: the 30-year averages next to what was actually recorded;
- sensor connection details and location settings.

The Winter plan page uses the same data for its forecast and its season table.

Online weather comes from [Open-Meteo](https://open-meteo.com/) (free, no account). The app fetches it every hour, loads the last 3 months the first time, and keeps everything in your database, so the history keeps growing. The computer running Docker needs internet access for this. If an update fails the Weather page shows the reason. Location is Round Rock, TX by default; change it under **Location and updates**. To bring in older history (for example last winter), use "Load older weather history from this date". Light is estimated from solar radiation (about 2.1 PAR per W/m2).

### More than one place

The Weather page can track as many places as you like, for example Round Rock, TX and Baraboo, WI. Each place keeps its own hourly readings, daily summaries, forecast, Load history and update log.

- **Add a place**: Weather page, **Places** section. Type a town or city, press **Search**, and pick the right one from the list (it shows the state or country, coordinates, time zone and elevation). You can also type the name, latitude, longitude and time zone yourself. A new place fetches its last 3 months and forecast straight away, then updates every hour like the others.
- **Showing the weather for**: the menu at the top of the Weather page picks which place the page shows: forecast, charts, the table of logged data, the season table, Load history and the update log. The choice is remembered on that computer.
- **Compare places**: in Tracked history, open **Choose what to chart and compare places** and tick other places. Every chart then has one line per place (up to 6 places). For daily, weekly or monthly steps there are also charts of each place's lowest and highest temperature.
- **Home place**: the place your plants are at. Plant pages, current conditions ("Online weather"), frost warnings and the Winter plan use it. Round Rock is home after upgrading; **Make home** changes it.
- **Stop hourly updates** keeps a place and its weather but stops fetching. **Remove** deletes the place and all its weather (it asks first). The home place cannot be removed.
- **Update every place now** updates them one after another; the progress box names the place it is on.

Upgrading keeps every reading you already have: they become Round Rock's.

### Everything Open-Meteo offers is now collected

Version 1.3.0 asks Open-Meteo for every measurement it publishes for your location, not just temperature, humidity and sunlight: feels-like temperature, dew point, wet-bulb temperature, air dryness (VPD), temperature at 80, 120 and 180 m, rain, showers, snowfall, snow depth, chance of precipitation, weather code, cloud cover (total, low, middle, high), visibility, day or night, sunshine, solar radiation (total, direct, diffuse, direct normal, top of atmosphere), UV index, wind speed, direction and gusts (at several heights), air pressure, water loss from plants and soil (evapotranspiration), soil temperature and soil moisture at several depths, and upper-air values such as CAPE. There are also daily summaries (highest, lowest and average of most of these, plus sunrise, sunset, day length, rain and snow totals and growing degree days). Units are Fahrenheit, mph and inches.

Not every measurement exists for every period. If Open-Meteo does not offer one for old dates, the app notes it (the update log lists them), skips it, and tries again in two weeks.

**Disk use.** Every measurement every hour is about 10 MB per year. So that going back to 1940 does not make the database huge, the app keeps *every* hourly measurement only for the most recent years (3 by default; change "Years of full hourly detail to keep" under Location and updates), keeps temperature, humidity and plant light hourly for all older years, and keeps the full set as daily summaries for all years. Everything from now on is kept in full.

### Tracked history charts

Under **Tracked history** on the Weather page:

- **Period**: the last 24 hours up to the last 10 years, **Everything logged** (back to 1940 if you loaded it), or **Pick dates** for any From and To date.
- **Choose what to chart**: tick Temperature, Humidity and Light, and as many other measurements as you like (any hourly measurement, plus daily summary values such as UV index highest or growing degree days). Each group has Tick all and Untick all, and two buttons tick every hourly measurement or every daily value. Charting everything over all years can take several seconds. Measurements with the same unit share a chart, up to three per chart. Your choices are remembered on that computer.
- **Use the dates and columns from the table below**: copies the table's From and To dates and its shown columns into the charts.
- The time step grows with the period so long charts stay readable: one point per hour up to 10 days, per day up to 3 years, per week up to 15 years, per month beyond that. Rain, snow, sunshine and water loss are added up over each step; gusts and UV use the highest value; everything else is averaged. For years older than your "full hourly detail" setting, extra measurements come from the daily summaries, and the page says so.

**Section titles stay in view.** On wide screens the title of the section you are scrolling through stays at the top of the screen. **Chart settings stay in view.** The settings bar (period, dates, source, plant range, charts per row, Go to chart, Choose what to chart) sticks to the top of the screen while you scroll through the charts, so you can change it while looking at any chart. **Hide chart settings** folds it to one line (it starts folded on narrow windows and with very large text). **Charts per row** shows 1, 2 or 3 charts side by side, and **Go to chart** jumps to any chart by name.

### The table of everything logged

**All logged weather data** (Weather page) is a table of what is stored: hourly weather, daily summaries, or your own sensor readings. Pick dates and order, set how many rows load at a time (any number from 10 to 1,000; remembered on that computer), jump straight to a page by typing its number and pressing Go (or First page / Last page), choose which columns to show (your choice is remembered on that computer), and download everything for the chosen dates as a spreadsheet (CSV, all columns). "Also chart" under Tracked history draws any one extra measurement.

### Update log

Under **Location and updates** the page says when the last **Load history** ran and what it brought in (dates covered, hourly readings and daily summaries, and which measurements Open-Meteo did not offer), and the same for the last automatic update. "Every update that has run" is the full log, including the hourly automatic ones. Readings collected before this version are shown as "Before logging began".

**Load history** now runs in the background. While it runs, the Weather page shows a progress bar with the percentage, which year it is fetching, how many readings it has saved so far, how long it has been running, an estimate of the time left, and when it last heard from Open-Meteo (so you can tell it is still going; it also says when it is pausing for Open-Meteo's per-minute limit). A small box at the bottom left of every page shows the percentage and time left until it finishes. It takes about half a minute per year of history; 1940 to now takes roughly 40 minutes. It keeps going if you leave the page or close the browser. Pressing it again skips whatever is already stored, so you can stop and resume. If the connection to Open-Meteo drops part-way (an error such as `UNEXPECTED_EOF_WHILE_READING`, a timeout, or the service being busy), the app now waits and tries again by itself, up to 4 more times over about 3 minutes, and the progress box shows it. Only if all of those fail does the load stop, keeping everything fetched so far. If Open-Meteo's free daily limit is reached it says so; press the button again the next day. If you restart Docker during a load, press it again.

To stop all online lookups, add `PLANTDB_WEATHER: "0"` under `environment:` in `docker-compose.yml` and run `docker compose up -d`.

### Connecting your own sensor

Open **Weather**, then **Connect your sensor**. It shows the address and a private token. Your sensor (or a small script on the device) sends a POST with the header `X-Ingest-Token: <token>` and a JSON body. All fields are optional except that you need at least one measurement:

- `device`: a name for the sensor (for example `porch`)
- `ts`: UTC time like `2026-10-20T14:00:00Z` (default: now)
- `temp_f` or `temp_c`; `humidity` (%)
- `par` (umol/m2/s) or `lux` (converted at 54 lux per PAR)
- `soil_moisture` (%), `soil_temp_f` or `soil_temp_c`, `soil_ph`

Send up to 500 readings at once as `{"readings":[ ... ]}`. A reading with an impossible value is refused with an explanation. Use the PC's Wi-Fi address (step 1 under "Use it from your phone"), saved on the Labels page, so the address shown on the Weather page works from the sensor. Try it from the PC (replace `YOURTOKEN`):

Windows (cmd.exe):

```
curl -X POST http://localhost:8080/api/readings -H "X-Ingest-Token: YOURTOKEN" -H "Content-Type: application/json" -d "{\"device\":\"porch\",\"temp_f\":71.2,\"humidity\":58,\"par\":240}"
```

Windows (PowerShell):

```
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/readings -Headers @{"X-Ingest-Token"="YOURTOKEN"} -ContentType "application/json" -Body '{"device":"porch","temp_f":71.2,"humidity":58,"par":240}'
```

macOS / Linux (bash):

```
curl -X POST http://localhost:8080/api/readings -H "X-Ingest-Token: YOURTOKEN" -H "Content-Type: application/json" -d '{"device":"porch","temp_f":71.2,"humidity":58,"par":240}'
```

The token is the only thing protecting this address (the password option does not apply to it), so keep it private and use **Make a new token** if it leaks. When your sensor is working, choose "My sensor" in Current conditions.

## Environment fields on every plant page

Besides the temperature, humidity and light ranges, each plant now has: a feeding season and interval (months and days), heat-damage temperature, comfortable air dryness (VPD, in kPa), comfortable light as PAR and as daily light (DLI, mol/m2/day), soil mix, soil pH, soil moisture and soil temperature ranges, fertilizer and nutrients, pests and diseases to watch, what to do about them, and current pest problems. Claude filled these in as a first guess for every plant from its type; they are guesses to check against your own experience, and everything is editable (Edit this page) with the usual version history.

## Fertilizer calendar and log

Open **Fertilizer** (top menu) for the whole collection, or look at the **Nutrients** section of any plant page.

- **Should I feed today?** Every plant has a feeding season (first and last month it is fed) and a number of days between feedings, set for Round Rock by plant type. Each day is then one of: **Time to fertilize**, **Hold off** (a cold night is forecast at or below that plant's damage temperature, or its health is Poor or Critical), **Fed recently** (with the next date), **Resting** (out of season: do not fertilize), or **No feeding season set**. The Fertilizer page groups all plants this way, and each plant page shows the verdict for today and for any date you pick.
- **Calendar:** shaded days are in the plant's feeding season, hatched days are its resting season. "Fed" marks feedings you logged and "Due" the next suggested feeding. On the Fertilizer page the calendar covers all plants (how many were fed, how many are due). Click a day, or move with the arrow keys (PageUp and PageDown change month), for the details. "Show as a list" gives a plain list of days; with large text or a narrow screen it switches to the list by itself.
- **Log a feeding:** press **Log fertilizer** (or **Log a feeding for this plant**). Choose the date, the plants (one, or many at once: "All that are due", "All in season"), the fertilizer name, its type, and the N-P-K numbers printed on the package, then the amount and how much water it was mixed into (for example 1 tsp in 1 gal) and how it was applied. The form shows an estimate of how strong the mix is: parts per million of nitrogen, phosphate and potash, and the N : P : K ratio. Spoon measures are converted at 4 g per teaspoon and 12 g per tablespoon for dry products and 4.9 ml and 14.8 ml for liquids, so treat the numbers as estimates. Most potted plants do well at 50 to 200 ppm nitrogen. Logging in a resting season asks you to confirm.
- **Remembered fertilizers:** names you have used appear in a list and fill in the rest of the form next time. Entries can be changed or removed; the change log records each one.
- **Change a plant's season:** Edit this page, Nutrients group: "Feed from month", "Feed through month" (a season like October to April is fine) and "Feed every (days)". The starting values are Claude's guesses from the plant type.

## Past days: what the values were on a date

Temperature, Humidity (and air dryness), Light, and Water and soil (soil moisture, root-zone temperature, pH) each have a **Past days** box. Open it, pick the date on the calendar (or use the arrow keys), and you see that day's lowest, average and highest value, how many hours were in range, a chart of the day, and the plant's comfortable range **as it was recorded on that date** (if you changed the range later, both are shown). Each day on the calendar is marked in range, a little out, out of range or danger, and "Fed" where fertilizer was applied. Pick where the readings come from: your sensor, numbers you typed into Current conditions, or the online weather (outdoors, so for plants kept inside it only shows what the weather was). Days before any data was stored are blank; the online weather loads about 3 months back the first time, and more from the Weather page.

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

For a spreadsheet, use the **Weather** page's table (any columns, any dates) or the **Change log** page: "Download weather and sensor readings (CSV)".

## Plant links and previews

Plant codes such as P-012 written anywhere in the Still to photograph list, in requests, or in a plant page's text link to that plant. Point at a link (or Tab to it) to see a small preview with the plant's photo, name and health; Escape closes it. On the **Photos** page you can add your own entries with a note and a **Related plant**, and **Edit** any entry; codes you type are linked too.

## Plant labels

Each plant page also has a **Label** section with the same label and a **Print this label** button (it prints only the label). On the **Labels** page every label has an **Open plant page** button. The plant ID (P-001 and so on) is now large, bold and black on the white label in every theme, including dark.

Open **Labels**, type the address from step 1 into "Address the codes should open", save, and print. Each label has a QR code that opens that plant's page. Codes made with `localhost` only work on the PC itself.

## Who made a change

The first time you save something, the app asks for your name. It goes into the change log with the date and time. It is typed in, not a login, so it records who says they made the change. Click your name at the top right to change it.

If you want a password, uncomment `PLANTDB_PASSWORD` in `docker-compose.yml` and run `docker compose up -d`. The browser then asks for a password (leave the username blank or put anything). Do not expose port 8080 to the internet; this is built for your home network.

## What's in the pages

- **Plants**: all pages, filterable by winter plan, health and ID confidence; sortable.
- **Today**: what to water, feed and answer today (see above).
- **A plant page**: names, ID confidence and what to send to raise it to 100% (with a "Copy this as a request for Claude" button), temperature strip showing 20, 32 and 38 F against the plant's limits, humidity, sunlight, winter steps, how to keep it comfortable when the weather cannot, health and steps to improve, photos, quick care buttons and the care log, the timeline, and the page history (version, date, who, what changed, before and after, restore).
- **Winter plan**: the 7-day forecast, expected versus tracked weather for October to March, when to act, every plant grouped by what it needs, and the cold-night checklist.
- **Weather**: forecast, charts, sensor connection and location (see above).
- **Fertilizer**: today's feed / hold / rest verdict for every plant, a calendar, and the feeding log (see above).
- **Photos**: wide shots not yet tied to a plant, and a "still to photograph" checklist.
- **Labels**: printable QR labels.
- **Change log**: every change to every plant, with CSV and JSON downloads.

Editing a page saves a new version and keeps the old one. "Restore" puts an older version's text back as a new version (photos are not changed). Two people editing the same page at once: the second save is refused with a message, so nothing is overwritten.

## Your data and backups

Everything is in the `data` folder next to `docker-compose.yml`:

- `plants.db`: all records, versions and the change log
- `photos`: every photo
- `photos_deleted`: photos you removed (kept so you can recover them by hand)

### The Backups page (from 1.7.0)

Open **Backups** in the menu.

- **Back up now** makes a backup straight away. Add an optional note, and tick **Include the photos** if you want them too.
- **Automatic backups**: switch them on or off and choose:
  - how often: every 6 hours, every 12 hours, daily, every 3 days or weekly
  - the hour of day
  - how many automatic backups to keep (older automatic ones are deleted; backups you make yourself and the updater's backups are never deleted automatically)
  - whether to include the photos
- The **Your backups** list shows each backup with a Download and a Delete button.

Backups are zips named `plantdb-backup-YYYYMMDD-HHMMSS-<manual|auto|update>.zip`. Each holds `plants.db`, a `backup.json` describing it and, if chosen, a `photos` folder. They are saved in the `backups` folder next to `data`, so updates do not touch them. That folder is still on the same disk, so copy a few to another drive or cloud folder now and then.

The app must be running for automatic backups. If it was off when one was due, that backup runs within a few minutes of the next start.

### Restoring a backup

Stop the app, keep the current database under another name, put the backup's `plants.db` in its place, and start the app again. The example uses `plantdb-backup-20261021-030000-auto.zip`; use your file's name.

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

You can also download everything from **Change log**: plants as CSV, the change log as CSV, or all data as JSON. To start over with the original 77 plants, stop the app, delete the contents of `data`, and start it again.

## Notes

- Photos are re-saved when uploaded (JPG, max 1600 px). Location data in the photo is removed. iPhone HEIC files are not supported; use JPG or set the phone camera to "Most Compatible".
- Plant IDs are Claude's best reading of the photos. Low-confidence plants say what would settle it.
- Fonts (Spectral, Atkinson Hyperlegible) are bundled under the SIL Open Font License; nothing loads from the internet.
- "Expected" weather figures are climate averages for Round Rock / Austin; the sources are listed on the Winter plan page. Tracked figures come from Open-Meteo and your sensor.
- Plant pages and the Display settings were designed for low vision: large type, high contrast, roomy spacing and no tiny tap targets. If something is still hard to read, tell Claude which page and what size and it will be changed.
