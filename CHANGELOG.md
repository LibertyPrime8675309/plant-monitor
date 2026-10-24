# Changelog

## 1.10.0 (2026-10-24)
- **Audit log page** (it replaces the Change log page, same place in the menu bar): every change to every record, with filters.
  - Search by words, plant, who made the change (one person, people, or Claude's updates), kind of change, field, and dates.
  - It shows 100 changes at a time with Previous and Next page, and says how many match.
  - **Download these changes (CSV)** saves just the ones that match. The page remembers your filters until you press **Clear filters**.
- **Debug button**, next to Display. It opens a window with:
  - **Show the audit log console**: a small window at the bottom of the screen with the newest 3, 4 or 5 changes (you choose), updated every 3 seconds. Scroll it for older ones; **Pause**, **Open the audit log** and **Close** are on it.
  - An option to let screen readers announce each new change, and details about the app and this browser.
- On phones, the Debug button sits above Display, and the Sections button moves above them whenever they would not fit side by side.
- The change log download no longer puts a stray `'` in empty cells.
- "Today" now always means today in Round Rock. Before, a phone or computer set to another time zone could be told "That date is in the future" when logging care in the evening.

## 1.9.0 (2026-10-23)
- **Getting ready to come inside.** Every plant page has a new section that helps keep ants, mites and other outdoor pests out of the house:
  - Choose the plant's **leaf type** and **pot size**, and tick any **pests you found**. The leaf type is filled in for every plant already; change it if it is wrong.
  - Ten methods (inspect, clean the pot, rinse, wipe, insecticidal soap, oil, rubbing alcohol, soak the pot, refresh the top soil, repot) are each rated **Best**, **Good**, **Use with care**, **Not needed** or **Not for this plant** for that plant, with the reason and step-by-step instructions. For example, succulents are never soaked, ferns get plain water, and struggling plants are not repotted.
  - **Done today** records each step in the care log, and **Undo the last one** takes it back.
  - When a spray needs a second round, the **Today** page reminds you 5 days later. Once a plant comes inside, it says how long to keep it apart from your other houseplants (3 weeks).
  - A new page, **Getting plants ready to come inside** (from Winter plan, the cold-night checklist or the Today page), lists every plant coming in and where each is up to, with the steps for all ten methods.
  - No bleach: pots are cleaned with hot soapy water and sun, or 3% hydrogen peroxide.
- The water hyacinth page (P-050) is archived, since it went in the trash (upgrade batch `batchA1`).
- "Log other care" now also lists these steps, so you can record one you did on an earlier day.

## 1.8.0 (2026-10-23)
Nine new features and fixes, tried out first as prototypes.

- **Frost alert.** When a night in the 7-day forecast would hurt a plant that is outside, a banner at the top of the page says how cold it will get, how many plants are at risk and when to act. Plant pages show their own "Frost risk" note instead.
  - **Cold-night checklist** (from the banner, or Winter plan): the next 7 nights, then the plants to bring inside, to cover, and the close calls, each with **Moved indoors** and **Covered for tonight** buttons.
- **Today page** (new link in the menu): plants to water or check, plants to feed, and what I need from you, most urgent first.
  - **Watering reminders** for every plant, based on how dry it likes to be, the weather and rain. Rain counts as a watering only for plants whose Location is Outdoors.
  - **Quick care buttons** under each plant's label, big enough for a phone in the garden: Watered today, Checked: still moist, Log feeding, Add a photo, Log other care.
  - A **care log** in each plant's Water and soil section, and "Check for water every (days)" on the Edit page if you want to set the gap yourself.
  - 25 plants whose spot is on the covered porch now have Location: Covered porch (upgrade batch `batch9d`). Plants whose Location you already changed were left alone.
- **Read aloud.** Every section has a **Read aloud** button that reads it in your browser's own voice, with a Stop button. Display settings has the reading speed and voice.
  - **Keyboard shortcuts:** R reads the page, Escape stops, [ and ] go to the previous and next plant, E edits, / searches, H goes to the Plants page, M opens the section menu, ? lists them all. Display settings can turn them off.
- **Timeline** on every plant page: how its health and identification have changed, two photos side by side to compare (the oldest and newest to start with), and everything that has happened to it in one dated list.
- **Copy my answers for Claude** (Plants page, and "Needed from you" on plant pages): puts everything you have answered or changed since last time into one message to paste into the chat, or to save as a text file.
- **Photo check.** When you add photos, any that look blurry, too dark, washed out or very small are shown with what to do, and **Take a new one**, **Add only the good ones**, **Add it anyway** and **Cancel**. Good photos are added straight away as before.
- **Phones with large text:** pages no longer run off the right edge at the larger text sizes, the menu bar scrolls away instead of covering the screen, and the Sections and Display buttons no longer overlap.
- **Plant pages on a laptop:** with the On this page menu open, the row of section buttons steps aside so it no longer covers the details half.
- **Smaller downloads:** the release zip no longer carries plant photos. They come in separate photo packs, only when a release adds new ones, so every file stays well under the 30 MB limit. This release adds no new photos, so there is no pack to save.
- The "Still to photograph" list now records what you tick off in the change log.

## 1.7.5 (2026-10-23)
- **Previous Plant / Next Plant** buttons on every plant page, each showing the plant's name and code.
  - On wide screens they sit in the empty margins either side of the page, halfway down.
  - Otherwise they sit in a row at the top of the page.
- **Filters for Previous / Next**: a fold-out panel at the top of each plant page with the Plants page filters (search, winter plan, health, sort, needs something from you, ID under 70%) and where this plant falls in the list ("plant 5 of 80").
  - Previous and Next follow these filters and the sort order.
  - The panel and the Plants page share the same filters, and this browser remembers them.

## 1.7.4 (2026-10-23)
- **P-055 split**: the photo of the yellow-marbled leaf was a different plant. It now has its own page, **P-081** "Yellow-marbled philodendron", and the photo moved there (P-055 keeps the Black Cardinal photos). The "one pot or two?" request is closed with your answer, and P-081 asks for a whole-plant photo (upgrade batch `batch9c`).
- Upgrade batches can now move a photo that was on the wrong page to a new page.

## 1.7.3 (2026-10-22)
- Your answer recorded: P-022 and P-075 are different roses, so both "same rose?" requests are closed with your answer (upgrade batch `batch9b`).
- Upgrade batches can now close a request with a written answer.

## 1.7.2 (2026-10-22) "October 21 photos"
- **106 new photos** from your October 21 round, added to 29 plant pages, and the pages updated from them (upgrade batch `batch9`).
- **Identified from tags and labels**:
  - P-007 Mexican bird of paradise (not a moringa; now "Hardy outside")
  - P-009 Philodendron 'Birkin'
  - P-010 Dieffenbachia seguine
  - P-015 hardy aloe, Aloe striatula ("Hardy outside")
  - P-022 rose 'Queen of Elegance'
  - P-024 Boston fern 'Emina'
  - P-029 Philodendron 'Pink Princess'
  - P-039 Philodendron 'Painted Lady'
  - P-055 Philodendron 'Black Cardinal'
  - P-056 Alocasia sold as 'Nigra'
- **Re-identified from the photos**:
  - P-004 mustang grape
  - P-005 ivy-leaf morning glory
  - P-006 sweet potato vine
  - P-011 variegated peace lily
  - P-012 pinwheel aeonium
  - P-018 Graptosedum
  - P-031 feather-striped calathea
  - P-036 possible stevia
  - P-051 variegated tradescantia
  - P-061 Alocasia 'Sarian' type
  - P-066 micans (a rooted runner of the plant above it)
- **Split**:
  - P-014 is now the largest aloe; the other two have their own pages, P-078 (teal pot) and P-079 (black pot by the prickly pear pad).
  - The speckled rosette in P-016's pot is P-080 (P-016 is the zebra haworthia).
- **Merged**: P-002 and P-044 are the same boobie cactus. P-044 is now its page, with the before-repotting photo, and P-002 is archived (nothing deleted).
- **P-030** is the Pink Princess offshoot in P-029's pot.
- **New health notes**:
  - P-042: leaf blotches
  - P-053: black specks on the leaves, possibly insects
  - P-055: white specks
  - P-035: hollow stem
  - P-039: root-bound
- **Recovering**: P-024 and P-030 go from Critical to Poor.
- **Requests**: 6 answered by the photos (tags and labels found), 7 new quick checks.
- Upgrade batches can now archive a duplicate page.

## 1.7.1 (2026-10-21)
- **P-034 identified**: from your close-ups it is a peace lily (Spathiphyllum, 70%), now "Peace lily (recovering, brown pot)". It is rated Poor (was Critical) because new shoots are coming up. Its page has new care, light, water and feeding details, recovery steps and the two new photos. It leaves the "needs something from you" list.
- Applied automatically as upgrade batch `batch8`; fields you edited yourself are left alone.

## 1.7.0 (2026-10-21) "backups, updater, indoors"
- **Backups page**:
  - **Back up now**, with an optional note and an option to include the photos.
  - **Automatic backups**: on or off, how often (6 hours to weekly), the hour, how many to keep, and whether to include photos.
  - A list of every backup with Download and Delete.
  - Backups go to the new `backups` folder next to `data`, which updates do not touch.
  - Restore steps are on the page and in the README.
- **Updater** (`Update Plant Database.cmd` in the Plants folder):
  - finds the newest release zip and checks the installed and running versions
  - makes a backup and starts Docker Desktop if needed
  - unzips and copies the new files over the old ones without touching `data` or `backups`
  - runs `docker compose up -d --build`, waits for the new version and logs to `update-log.txt`
  - optionally deletes the previous image
- **Location** on every plant page (Outdoors, Covered porch, Indoors, Garage or shed). Pick a new one from the menu in the label at the top, and it saves straight away. The free-text field formerly called Location is now **Spot**.
- **Moved indoors** button on each plant in the Winter plan's "Plant by plant" lists. Plants that are inside leave those lists and the frost warnings, and appear under "Already inside" with a **Moved back outside** button. A plant page set to Indoors notes that the outdoor weather readings do not apply to it.

## 1.6.3 (2026-10-21)
- **Plant codes become links**: any plant code such as P-012 in the Still to photograph list, in requests and in plant page text (notes, identification, health, steps) links to that plant. Pointing at a link, or reaching it with the Tab key, shows a preview with the plant's photo, name and health; Escape closes it.
- **Still to photograph**: add entries with an optional note and a "Related plant" picker (it adds the code for you), and edit existing entries with the new Edit button. Codes you type yourself link the same way.

## 1.6.2 (2026-10-21)
- **See which version is running**: shown next to "Plant record" on every page and in Display settings, at `/api/version`, and in Docker Desktop (the image is now tagged `plant-database:1.6.2` and labelled with the version).
- **"Needed from you"**: questions, checks and photo requests from Claude now appear at the top of each plant's page with Answer and Mark done buttons; answers are saved with the page and in the change log and backup. The Plants page has a **Show plants that need something from you** button (open requests plus IDs under 70%), and each card says what is needed.
- Upgrade batch `batch7` adds the current requests: P-017 spear check, P-055 one pot or two, P-022 / P-075 same rose or not, tag photos for six philodendrons, two Alocasias and two arrowhead plants.

## 1.6.1 (2026-10-21)
- **Section titles stay in view**: as you scroll, the title of the section you are in sticks to the top of the screen (on wide screens; on phones and very large text it scrolls normally to save room). On plant pages this works inside the details half.
- **Tracked history settings take less room**: the "Choose what to chart" button sits next to "Hide chart settings"; Period and Source share the first row, and Plant range, Go to chart and Per row share the second. The plant range box is a fixed, narrower width (the full name shows in the list and as a tooltip). The readings count moved below the charts.
- Section menu: tighter spacing and shorter "Move right / Move left" button, so more sections fit on screen.

## 1.6.0 (2026-10-20) "batch 6 photos"
- **11 new plants (P-067 to P-077)** from the October 20 photos: celosia 'Dracula Red', petunia 'Ray Black', white sage (Artemisia ludoviciana), bee balm (Monarda fistulosa), zexmenia, Texas star hibiscus (all identified from their tags), the yellow miniature rose in the red pot, the rose in the green pot, a sparse rose in a second black pot, and two more majesty palms (white pot, tall grey planter). Each comes with its environment details and feeding season filled in.
- **Updated pages**: P-017 is now identified as a majesty palm (Ravenea rivularis, 70%) with a warning to check its browning spear for bud rot; P-022 (rose) gets a new photo and notes; P-053 is now "Gourd-family vine (red pot)" (50%), rated Poor, with an annual winter plan.
- Still-to-photograph list: "Other palms" and "Second rose in the red pot" are ticked off; three follow-ups added.
- Applied automatically as upgrade batch `batch6`; fields you edited yourself are left alone.

## 1.5.0 (2026-10-20) "more than one place"
- **Track the weather for several places at once** (for example Round Rock, TX and Baraboo, WI). Each place has its own hourly readings, daily summaries, forecast, Load history and update log, and updates every hour.
- **Places section** on the Weather page: search for a town by name (Open-Meteo place search, no account) or type coordinates; show, make home, stop or start hourly updates, or remove (with its data, after asking).
- **"Showing the weather for"** menu at the top of the Weather page switches every section to that place.
- **Compare places** on the Tracked history charts: one line per place, up to 6.
- **Home place**: plant pages, current conditions, frost warnings and the Winter plan keep using the place your plants are at (Round Rock after upgrading). All existing readings stay with it.
- "Update every place now", and the progress box names the place being updated.
- Chart colours for the 3rd to 6th lines changed to a set checked for colour-blind readers.
- The JSON backup now includes your places.

## 1.4.2 (2026-10-20)
- **Tracked history no longer jumps to the bottom of the page** when you change a chart setting. The charts used to be swapped for a one-line "Loading charts" message while the new ones loaded, so the page shrank and the browser moved you down to Location and updates. The current charts now stay in place, dimmed, until the new ones are ready, and the view stays where it was. If you change several settings quickly, only the last choice is drawn.

## 1.4.1 (2026-10-20)
- **Plant pages fill the window**: hidden text meant for screen readers was leaking out of the photo and details halves and stretching the page to about 11,000 pixels tall. The page could then scroll on its own, pushing both halves up and leaving a large empty band below them. The halves now always fill the window to the bottom and the page itself no longer scrolls.
- Gaps from the comfortable range are rounded (it said "3.7000000000000003°F below" instead of "3.7°F below").

## 1.4.0 (2026-10-20) "section menu"
- **Section menu on every page** ("On this page"), on the left or right, highlighting where you are, with a Hide button and a Sections button to bring it back. Side, open or folded, and a new full-width page option are in Display.
- **Tracked history**: the chart settings now stay at the top of the screen while you scroll through the charts, can be folded to one line, and include Charts per row (1 to 3) and Go to chart. The list of measurements opens in a scrollable panel inside the settings bar.
- Fix: the From and To boxes showed for every period instead of only for "Pick dates".

## 1.3.3 (2026-10-20)
- **Load history survives dropped connections**: a connection that drops part-way (for example `SSL: UNEXPECTED_EOF_WHILE_READING`), a timeout, or a busy Open-Meteo (HTTP 5xx) is retried automatically after 5, 15, 45 and 90 seconds before giving up. The progress box says when it is pausing and why, and counts the retries. If it still stops, the message says everything so far was saved and pressing Load history again carries on.
- **Chart as many measurements as you like** (the limit of 24 is gone). Tick all / Untick all for each group, plus buttons to tick every hourly measurement or every daily value. Large selections are fetched in batches.

## 1.3.2 (2026-10-20)
- **Tracked history charts use all logged data**: periods up to 10 years, "Everything logged", or any From and To dates; choose which measurements to chart (temperature, humidity, light and up to 24 extra hourly or daily values), grouped by unit; a button copies the table's dates and columns into the charts. Long periods switch to daily, weekly or monthly points, with year and month labels on the axis. Older years fall back to the daily summaries. Charts are now worked out by the database (a 1940-to-now chart takes about a second on a 760,000-row history).
- Empty "My sensor" lines are no longer listed when you have no sensor readings.

## 1.3.1 (2026-10-20)
- **Weather table paging**: type a page number and press Go, or use First page and Last page; rows per page can be any number from 10 to 1,000 (remembered), and changing it keeps the same rows in view. Deep pages load quickly even with 760,000 rows (about 0.1 s in testing).
- **Load history progress**: percentage bar, year being fetched, readings saved so far, time running, estimated time left, and "last activity" (including a notice while pausing for Open-Meteo's per-minute limit). A progress box appears at the bottom left of every page until it finishes, then a message says it finished or why it stopped.

## 1.3.0 (2026-10-20) "fertilizer calendar and past days"
- **Fertilizer page and log**: a verdict for every plant today (time to fertilize, hold off for cold or poor health, fed recently, resting out of season), a calendar for all plants, and a log of every feeding with fertilizer name, type, N-P-K analysis, amount and water, method and notes. Mixed strength is estimated as ppm of nitrogen, phosphate and potash and the N : P : K ratio. Log one plant or many at once; fertilizers you used are remembered; entries can be changed or removed and are written to the change log.
- **Nutrients section of each plant page**: today's verdict, a feeding calendar (season shading, Fed and Due marks, any date selectable) and the plant's own feeding history.
- **Feeding season per plant** (new fields: first month, last month, days between feedings), filled for all 66 plants by upgrade batch `batch5` (fields you edited are left alone). Seasons can wrap the year (Aeonium: October to April).
- **Past days** for Temperature, Humidity and air dryness, Light, and Water and soil: a calendar marked by how each day compared with the plant's range, and for a chosen date the low, average and high, hours in range, a chart, and the range as recorded on that date (from the page's version history).
- Calendars have keyboard control, a list view (automatic with large text or narrow screens), and text marks as well as colour.
- Weather and sensor readings can be downloaded as CSV (Change log page). README explains where the data is stored.
- Fixes: tables no longer cause sideways scrolling on phones; long names wrap.
- **Speed fix for large weather histories**: with decades of history loaded, every plant page ran a lookup that read all the weather rows, which took seconds and kept the CPU busy. Plant pages no longer touch the history for this, the weather page's counts are cached, the season table reads only recent months, and there is a new database index. A test database with 760,000 hourly rows (1940 to now) loads plant pages in milliseconds.
- **Weather: every Open-Meteo measurement is now collected** (about 60 hourly and 80 daily values, listed in the README), stored with full hourly detail for recent years and as daily summaries for all years (see "Years of full hourly detail to keep").
- **Weather page**: a table of all logged data (hourly, daily or sensor; date filters, column chooser, paging, CSV of everything), an "Also chart" option for any extra measurement, a line stating when Load history last ran and what it brought in, the last automatic update, and a full update log.
- **Load history runs in the background** with a progress bar, in year-sized pieces that can be resumed; it recovers from the per-minute rate limit and reports the daily limit plainly.
- **Labels**: the plant ID is large, bold and black on the white label in dark mode too; every label has an "Open plant page" button; every plant page has a Label section with a "Print this label" button.

## 1.2.0 (2026-10-20) "low vision, weather and environment"
- **Display settings** (floating Display button): text size up to 190%, roomy spacing, high contrast, light/dark, one column or split plant pages. Everything is sized in rem so buttons, bars and charts scale together; default text is a little larger than before. Fonts and overall look are unchanged.
- **Plant page scrolling**: photos and details are separate scroll areas, so the half under the pointer scrolls. A "Switch to one column" button (also in Display) removes the split; narrow windows and very large text use one column automatically. Section buttons jump within the page.
- **Current conditions**: type in temperature, humidity and light (PAR or lux), or use your sensor or online weather. Gauges show a labelled "Now" marker and an out-of-range plant gets a "Getting this plant back in range" section with steps.
- **Weather page** (new) and tracked weather on the Winter plan page: Open-Meteo forecast and hourly history stored in your database, charts with table view, expected versus tracked monthly table, location settings.
- **Sensor input**: `POST /api/readings` with a private token; temperature, humidity, PAR/lux, soil moisture, soil temperature, soil pH.
- **More plant fields**: heat damage temperature, VPD, PAR, DLI, soil mix, pH, soil moisture/temperature, fertilizer, nutrients, pests to watch, pest steps, current pests. Filled in for all 66 plants by upgrade batch `batch4` (fields you edited yourself are left alone).
- Added `tzdata` to the build; new optional setting `PLANTDB_WEATHER=0` turns off online lookups.

## 1.1.2 (2026-10-19)
- Water hyacinth (P-050): owner confirmed keeping it is fine, so the page now plans to bring it indoors before 45 F instead of "check the rule first". The Texas Parks and Wildlife note stays as a reminder never to release it. Applied automatically as an upgrade batch (`batch3`); fields you edited yourself are left alone.

## 1.1.1 (2026-10-19)
- README: PowerShell commands added next to the cmd.exe and bash ones.
- Package now ships as a versioned zip (`plant-database-v<version>-<date>-<time>.zip`) with this changelog.

## 1.1.0 (2026-10-19) "batch 2"
- 26 new plants (P-041 to P-066) and 29 new photo records from the second and third photo batches.
- Upgrade mechanism: `app/seed/batches/*.json` are applied once at startup, so an existing database gains the new plants without losing edits. Fields you changed are left alone and noted in the change log.
- P-040 (crown of thorns): new primary photo, ID confidence 75 to 95, health reassessed. P-002 (boobie cactus): second photo.
- "Still to photograph" checklist: 6 items marked done, 5 added.
- Water hyacinth page notes the Texas Parks and Wildlife rule.

## 1.0.0 (2026-10-19)
- First release: 40 plants (P-001 to P-040), 48 photos, Flask + SQLite web app in Docker.
