# Changelog

## 1.40.0 (2026-11-05)
- **One identifier** behind Identify, Add a plant and Add several plants: every photo of the plant is checked together, Pl@ntNet is part of the answer whenever its key is saved (always with "Ask Pl@ntNet on its own", or when this computer is unsure), and the two lists are merged into one, each name saying who said so and how sure. The likeliest **family** joins the likeliest genus.
- **Not this** and **Not this genus** on every name, on all three pages: the name leaves the list, the photos are checked again without it, and the choice is logged. On a plant's page (coming next) the rejection sticks to the plant.
- **Add several plants:** once you have sorted the photos, each plant's photos are checked together (that is what should have turned six guesses into two); **Check the photos again** and **Ask Pl@ntNet about this plant** on each plant.
- **Add a plant:** "Fill in the names from the first photo" now uses all the photos on the form, shows the full list with **Use this name** on each, and the same Not this buttons.
- The name a plant gets says which checker suggested it ("Suggested by the picture checker on this computer and Pl@ntNet from 3 photos").

## 1.39.1 (2026-11-05)
- **Room for the content** (Ethan, November 5): list pages keep one row of controls (search, the one or two that matter most, sort) and fold the rest under **More filters**, which opens by itself while a folded filter is on. Plants page: Search, Home, Location, Sort on the row; Health, Group, Show, ID confidence and the rest folded. Library: Search, Look in, Sort; the rest folded. Identify → Your plant photos: the six extra selects that stood one under another, full width, are in the fold with the others (that was a mistake in 1.28.0). Audit log: the search and filters box starts folded unless a filter is on.
- **Read this page aloud** sits beside the page title on a computer instead of on a row of its own.
- A page with no sections (the Plants page, the Audit log and others) no longer shows the empty "On this page" menu; its width goes to the content.
- Plants page: a shorter line under the title; "Plants that need something from you", "Copy my answers for Claude" and "N to photograph" on one row.
- Grow lights: a light's name, count, model and place are text until you press **Edit the name, count, model and where it is**.
- Weather: the Location box is one line.

## 1.39.0 (2026-11-05)
- **Better names from Identify.** The picture checker now weighs its names toward what you are likely to be looking at: species and genera already in your record, houseplant genera, and the plants of your state, plus a lift for a name when one of your own named plants' photos looks like the picture (a new pot of a plant you have gets its name). Each lifted name says why ("Lifted: a houseplant", "looks like your photos").
- **Ten names, not three** (five shown, "Show 5 more names"), and the three likeliest genera: when no species fits, the genus is the safer answer.
- **Several pictures of one plant:** "Add another photo of the same plant" (or a camera shot) checks them together.
- **Three looks at each picture:** as it is, the whole picture letterboxed (nothing cut off a wide shot), and its middle, averaged.
- **Pl@ntNet first when unsure:** a new choice under Second opinions asks Pl@ntNet on its own whenever this computer is not sure, and shows its answer above the computer's own. Needs the Pl@ntNet key; one of its 500 free pictures a day each time.
- The updater rebuilds the picture checker container for this version; its first start re-reads the photo fingerprints it already has (no new download).
- The weights are a first setting by judgment, not yet measured on your photos: `dev/vision/prior_test.py` measures them on the PC when you want to tune them.

## 1.38.0 (2026-11-05)
- **Watering offline:** on Today, Watered and Still moist take the plant off the list at once without a connection; the care log shows the entry as "not sent yet" until it is sent.
- **Reconnecting:** the app notices when the plant server can be reached again (every 30 seconds, when the app comes to the front, when the network returns), sends what was waiting and redraws the page; **Try to connect now** on the offline note and the Offline use page. "Offline" now also means "the plant server cannot be reached" (Tailscale off, computer asleep), not only "no network".
- **Back returns to where you were** on a page; photo boxes have their size before the photo loads, so pages do not jump.
- **Photos on the Add a plant form**, with **Fill in the names from the first photo**. Identify's "Choose a photo" and the plant page's "Add photos" let the phone offer its photos instead of forcing the camera.
- **Adding a plant without a connection:** it is kept on the device (stand-in name allowed when there is a photo), sent later, and its first photo is then checked, with the names offered on the Offline use page.
- **Several plants from photos:** small previews made on the phone (no more white patches); under each photo you say "Same plant as the photo above", "A different plant", "Shows all of them" (a wide shot copied to every plant) or "Leave this photo out". The "minutes apart" grouping is gone.
- **The other changes made from a phone now wait offline too, and show at once:** "Log other care" and Remove on a care entry, Moved indoors and Covered on the cold-night list, Fed (a feeding), answers and "done" on requests from Claude, the Still-to-photograph ticks, photo captions, main photo and photo removal, the porch reminder, wishlist and species notes. Edits to a plant now show on the Plants page cards too, and photos added offline show as thumbnails in the "Not sent yet" line.
- On a phone the Save bar of a form sits above the bottom bar instead of under it.

## 1.37.1 (2026-11-05)
- Grow lights, from the labels Ethan photographed (batch B7): the SANSI tripod is model C23ZW016-H0045A27 (45 W, 120 V, 0.7 A, 4000 K, rated for wet locations); the Barrina T5 strips are model NC05 (5 W a strip, 100 to 277 V, up to 16 linked); the 4-head gooseneck has no model label, only "Max: 4 x 10 W" on its clamp, and its four bulbs are SANSI C21GL-GE26-10W, the same as the six spare 10 W bulbs. The request for the disk light's model stays open on its own.

## 1.37.0 (2026-11-05)
- **Share a photo from your phone:** with the app on an Android phone's Home Screen, "Plants" is in the share sheet; shared pictures open a page where you choose the plant and press Add.
- **Year in review** (Plants → Year in review): one card per plant for a year: health, moves, waterings, feedings, cold nights and hot days outside, requests, first and last photo; the hardest years first.
- **The mirror:** `mirror/` sets up a read-only copy of the app on another machine, kept current from the backups the receiver gets, on Tailscale as plants-mirror. Every page on it says so and links to the main app.

## 1.36.0 (2026-11-05)
- **Every page in its section's row:** the cold-night checklist, Coming inside and Back outside under Care; Around home under Discover; Offline decisions under Settings. Plant pages, plant cards and Today lead to Coming inside as well. The search window lists the same pages. (Ethan, November 4: "Getting plants ready to come inside" was only reachable from a button on the Winter plan.)
- **Summer heat for each plant** (About this plant): a verdict from the plant's heat-damage temperature and the weather history, and its AHS heat zone range against yours (batch B6 adds ranges with sources for 20 plants). "Summer here" filter on the Plants page; counts on the Weather page.
- **Calibrate the soil probe** in the app: dry air, then a glass of water; the app then works out the moisture from the probe's volts.
- **Soil moisture on the plant's page:** the last 60 days drawn on the Timeline with the waterings marked; each day's average on the fertilizer calendar.
- **Health of the app** card on Settings: version, backups and their copies, weather and store checks, problems, disk space.
- **Clear the saved pages** on the Offline page.
- Every Remove, Change, Delete and Download button says what it acts on; the smoke test checks for bare names.

## 1.35.0 (2026-11-04)
- **Your sensors** (Weather → Sensors): one card per sensor with its newest values in large type (soil moisture, air and root-zone temperature, humidity, light, soil pH, pot weight), a small line of the last 24 hours for each, and the day's lowest and highest. Name a sensor, say where it sits (a room or spot) and which plant's pot it is in: its values are then compared with that plant's ranges, in words with a mark (✓ In range, ↓ Dry, ! Too cold…), on the Sensors page and under Water and soil on the plant's page. A sensor that stops sending says Quiet.
- **Today** lists the sensors that need a look or have gone quiet.
- **Watering from the sensor:** a jump in soil moisture logs a watering for the plant (once a day; turn it off per sensor).
- **Sensor alerts** as notifications: a dry pot, dangerous cold, a sensor gone quiet, once a day each.
- **Pot weight:** readings can carry `weight_g` from a weighing cell under the pot.
- **ESPHome:** `sensors/esphome-plant-sensor.yaml`, a ready file for an ESP32 node with a soil probe, air sensor, light sensor, soil thermometer and weighing cell; the README says how to flash it.

## 1.34.0 (2026-11-04)
- **Today is the page the app opens on.** One line says what needs you, with a button to jump to each part; the cold-night warning is a section of the page; "Quiet today" says what is not due (pest rounds, the last store check and backup, problems). All plants is one click away (its address is now `#/plants`).
- **Shopping list for a store visit** (Shopping → Shopping list): choose a store; what it carries comes first with what you are watching for, the rest under "Not carried here". Add extra lines, tick what you bought, and "Done shopping" marks them as got it. Large print and Print.
- **Speak a note:** a Speak button on every box that takes several lines, when the browser has voice typing (Chrome, Edge, Safari). The words are added after what is there.
- **Room, area and shelf labels** on the Labels page: scanning one opens the Plants page showing just that place's plants.
- **Summer heat next to winter cold:** the Weather page's new "Your climate" section gives the USDA zone and the AHS heat zone (days above 86°F a year, hottest day, the hot months, each year's count) from your own weather history; plant pages say the heat zone next to the winter zone.

## 1.33.0 (2026-11-04)
- **Notifications** (Settings): messages on your phone or computer even when the app is closed. Turn them on per device; choose for your own sign-in which kinds reach you: cold nights (when the forecast turns, and a reminder at 3 pm the day before), Shopping alerts, what is due today (at 8 am), and requests from Claude. Cold nights and what is due are for the home you start on. They go through the browser's own push service and need the app's Tailscale address (or this computer itself).
- **Second copy of backups** (Backups page): each new backup is also copied to a folder on another drive (`PLANTDB_COPY_DIR` in `.env`; until then a `backups-copy` folder next to the data), and to another computer over Tailscale that runs the small **receiver** included in the release (`receiver` folder, with its own README). **Copy the newest backup now** tries it.
- **Search everywhere**: the Search button in the top bar, or the `/` key. Finds plants, pages, groups, rooms and spots, stores, mushroom finds, Shopping items and species in the library, grouped, with the arrow keys to move and Enter to open.
- The image build installs one more Python package (cryptography) for the notifications; the Dockerfile itself is unchanged.
- Top bar: when Search, Online, Location and Editing no longer fit beside the name, the Search button keeps only its magnifier and the Location button only its pin and place name (their full names stay for screen readers) before the bar grows another row. And when the bar is tall enough to scroll with the page, the open "On this page" menu no longer covers its left end.

## 1.32.0 (2026-11-04)
- **Jobs** (Settings): one list of what the app is doing in the background (weather updates, store checks, backups, library downloads, store map positions), when each scheduled one is next due and last ran, and what finished, with how long it took. The owner can start the weather update, the store check or a backup from there.
- **Under the hood:** the server's code is now in modules, one per feature, and the page's code in twelve files instead of one, so changes are smaller and safer. Nothing you see has changed.
- **Tests:** unit tests that run in a second, a runner for the browser checks, and GitHub runs both on every pull request.

## 1.31.0 (2026-11-04)
- **Windows High Contrast mode.** When Windows is set to a high-contrast theme, the chosen filter, the page you are on, keyboard focus, tags and alerts are all drawn with the theme's own colours and an outline, so nothing disappears.
- **Problems** (Settings): anything that went wrong in the background (a weather update, a backup, a store check, a library download) is listed in plain words, with the details folded away and a **Copy the list for Claude** button. The owner can clear them.
- **Restore** on the Backups page: puts a backup's database back in place. A backup of how things are now is made first, photos are never removed (ones in the backup that are missing are put back), and an older backup is brought up to this version. A backup made by a newer version is refused.
- **Starts on:** on the people list, the owner can choose which home each person starts on. Someone whose plants are at Nevada City opens the app there, and their own choice stands after that.
- **An older version will not change a newer database.** If an older zip is ever installed over a newer one, the app only shows a page saying which version to install, and leaves your data alone.
- Faster weather pages on a large history: indexes on the readings, listings and photos tables.

## 1.30.0 (2026-11-04)
- **Shopping** (under Discover): the stores are checked for your wishlist plants and for garden supplies.
  - Watch for pots and trays, potting mixes, amendments, fertilizers, pest control, frost cloth and covers, grow lights and timers, and tools and labels, each with its own alerts.
  - **Show** picks one kind (a dropdown on a phone), and **Stores near** picks Round Rock or Nevada City.
  - **Cheapest now** gives the price per quart, pound or square foot when a listing says its size, and a price alert can be per unit.
  - Each item lists the stores near you that carry that kind, with phone numbers you can tap.
  - **Watch for more on Shopping** on each pot or tray, **Watch for it on Shopping** for each N-P-K ratio on the Fertilizer page, and **Watch the stores for frost cloth** on the cold-night checklist.
  - The Wishlist page keeps your plants and points to Shopping for prices and alerts. The alert count is now beside Shopping.
- **Stores**: every store, grouped near Round Rock, near Nevada City, and online. Each store has its own page with its address and a map link, how far it is, phone numbers, hours, email, website, what it carries, the listings it has for you with the price before, and **What they had** notes after you call or visit.
  - **Edit details** and **Look them up on OpenStreetMap** fill in what is missing.
  - Details for the five stores near Round Rock, and six new stores near Nevada City (including Peaceful Valley Farm & Garden Supply, which is also an online store), come from their websites (batch B5).
  - The owner's store settings (on and off, how often, adding a store, the eBay and Etsy keys) moved to the Stores page.
- **Quicker pages:**
  - The page you choose shows at once, with its name and "Loading" if it takes a moment.
  - A page you opened before shows straight away from what this device had, then checks for anything newer.
  - Pointing at a link starts loading it, and the other pages of the section load in the background.
  - The plant list, frost and groups no longer hold up every page.
  - Answers are sent squeezed, about five times smaller, and the server handles more requests at once.
  - **Settings, Debug, Page timings** shows how long each page took and why.
- The third extra palm and "any plants not yet photographed" are ticked off the Still to photograph list (batch B5).
- No new photo pack. The picture checker is unchanged.

## 1.29.0 (2026-11-04)
- **A clearer top bar.** Six sections: **Today**, **Plants**, **Care**, **Weather**, **Discover** and **Settings**. The pages of the section you're in are on a second row:
  - Plants: All plants, Groups, Add plants, Mushrooms, Rooms and spots, Photos, Labels.
  - Care: Winter plan, Fertilizer, Grow lights, Pots and trays.
  - Weather: Weather, Homes and places.
  - Discover: Identify, Library, Wishlist (its own link now, with the alert count).
  - Settings: a new Settings page (people, Display, Debug, keys and more), Offline use, Backups, Audit log.
  - The version number stays beside the name on every page. The Location button now says **Home: Round Rock, TX**. Debug has moved to the Settings page.
- **Where a plant is, in three steps:** outside or inside, then the area or room, then the spot.
  - Each home has its own list on the new **Rooms and spots** page (under Plants). Rename anything by typing over it; add and remove areas, rooms and spots.
  - Outside areas can have a **roof overhead** (counts as a covered porch) and inside rooms can be **heated** or not (not heated counts as a garage or shed), so frost warnings and watering keep working.
  - Your Rooms and shelves from the Grow lights page are now rooms and spots here, and light spots choose from the same list.
  - Your plants are already in the right area for their old Location. **Spots to sort out** suggests a spot for each place written on your plants; check the names and press **Make these spots**.
- **Pots and trays** (under Care): each pot and catch tray you keep, with shape, sizes in inches, drainage holes (pots), material (or your own words), photos and how many you have. A **3 / 5 in use** count sits next to the quantity, with links to the plants using them. The square feet are worked out (a round one counts as the square around it). Choose a plant's pot and tray on its page.
- **Grow lights use them:** a plant takes up the floor of its catch tray, or its pot when it has no tray, when the suggested layout works out how many plants fit under a light.
- **Edit right on the page.** On the light cards, the pots and trays, Rooms and spots, and a plant's main details, type or choose a new value: it saves when you leave the box or press Enter, Escape puts back what was there, and the message that follows has **Undo**. Longer text (notes) has a small **Edit** button. People who can only view see the values but cannot change them.
- **Your lights** is at the top of the Grow lights page and folds; it remembers how you left it.
- **Settings follow you.** The Plants filters, the Library's choices, folded sections, the Location button and Identify's list are saved for your sign-in, so any device you sign in on picks them up. Display settings stay on each device unless you tick **Use these on every device I sign in on** in that part of Display.
- **Grow lights (batch B4):** the SANSI T8 strip's model (C21GL-LT01-25W), 25 W, 120 V and 0.5 A. It is one strip, not a set, and its note says the power button steps the brightness and holding it turns the strip off.
- **P-036:** the stems are round, so it is not in the mint family. It now asks only about the smell.
- No new photo pack.
- Includes everything in 1.28.0 below.

## 1.28.0 (2026-11-03)
- **A second home: Nevada City, California.** It has its own weather, frost warnings, watering and hardiness zone.
  - Every plant has a **Home**. Your plants stay at Round Rock.
  - The Plants page has a **Home** filter, and each card says its home.
  - Choose a home with the **Location** button: its frost warnings, watering and Back outside list only its own plants.
  - On the Weather page, each place says whether plants live there, and how many.
- **Add several plants at once.** Add a plant now has **Several plants from photos**:
  - choose all the photos at once, and the picture checker looks at each one;
  - photos taken close together that look alike become one plant;
  - names, family, genus, plant type, safety for pets and ID confidence are filled in from the likeliest species;
  - a review screen lets you pick another name, fix anything, and move or leave out photos. A plant that looks like one you already have is flagged and not ticked;
  - nothing is added until you press **Add N plants**.
- **Your plant photos on the Identify page:** one row per plant with its photos in a strip, and the same search and filters as the Plants page.
- **Not tied to Texas any more.** The Library's lists, filters and tags (now **Your area**), Identify's state list and the question sent to Claude follow the place in use. Nevada City gets California's lists. The Texas invasive list only shows for places in Texas.
- **Photos for offline use, by area.** The Library downloads the plants of any country, state, county, city or park, in a table showing photos downloaded out of how many, the percent, **Check for updates** and the date last updated. The offline copy on phones keeps these areas.
- Fixed in 1.27.3 and included here: the "On this page" menu marks the section you chose.
- No new photo pack. The picture checker container is rebuilt by the updater (its code changed; nothing new to download).
- Includes everything in 1.27.3 below.

## 1.27.3 (2026-11-03)
- **Fixed: the "On this page" menu.** Choosing a section near the end of a short page (such as "How groups work" on Groups) now marks that section in the menu. Before, the page could not scroll far enough, so the menu kept marking the section above it, or seemed to ignore the click.
  - The section you choose stays marked until you scroll the page yourself.
  - The section you jump to gets a thick outline for a couple of seconds, so you can see where it is, even when the page did not need to move.
  - The same goes for the row of section buttons on plant pages.
- Includes everything in 1.27.2 below.

## 1.27.2 (2026-11-02)
- **Grow light details from your labels.** Six of your lights now have their model numbers and power ratings on the Grow lights page:
  - **Barrina standing light:** model T10F20, 100 to 277 V.
  - **SANSI 80 W folding bulb** (the 4-arm light): model C21FS-BE26, 120 V, 1.1 A.
  - **SANSI 30 W bulbs:** model C23ZW005-V0030A29, 120 V, 0.65 A.
  - **SANSI 10 W bulbs:** model C21GL-GE26-10W, 120 V, 0.2 A.
  - **SANSI pot clip lights:** model C23ZW013-T0005A27, a 120 V adapter (0.05 A) and a 5 V USB lamp. The clip fits a pot rim up to 0.4 in thick (the page said 0.8 in).
  - **GooingTop 2-bar clip lights:** 40 LEDs on each bar. The light estimate is adjusted to match.
- **Notes from the labels** on each of the SANSI lights: none of them work on a dimmer, they are fine in damp places such as a covered porch but not in rain, and they need an open fixture or shade, not a closed globe.
- Anything you changed on these lights yourself is left as you set it.
- No new photo pack this time.
- Includes everything in 1.27.1 below.

## 1.27.1 (2026-11-01)
- **Five new plant pages** from your photos of November 1:
  - **P-085** and **P-086**: the two philodendrons with "Philodendron Royal Queen" stakes. A true 'Royal Queen' has near-black leaves, and these are orange from the sun, so each page says the name may be 'Prince of Orange' instead. A new leaf grown in bright shade will tell.
  - **P-087**: **Alocasia 'Frydek'**, your third Alocasia (the "fuzzy pale-green-leaved plant").
  - **P-088**: the **young Monstera** in the maroon pot with the 'Monstera' tag.
  - **P-089**: the **Mini Monstera** (Rhaphidophora tetrasperma) beside it, the "climbing aroid". It has its own uses, partners and propagation.
- **New photos and health notes** for the purple fountain grass (P-054), the iris (P-064), the curly Boston fern (P-083) and the young Monstera in the beige pot (P-084).
- **Still to photograph:** three items ticked off (the fuzzy plant, the 'Monstera' pot and the climbing aroid).
- **Photos:** this release comes with a new photo pack, `plant-database-photos-B1.zip`. Keep it next to the release zip.
- Includes everything in 1.27.0 below.

## 1.27.0 (2026-11-01)
- **New section on every plant page: Uses, partners and propagation.** It's also on Library species pages, and on mushroom finds as "What it does, and growing it".
  - **Uses** with their safety warnings (aloe gel for minor burns, prickly pear pads, fig fruit, dye from cosmos and gardenia...), and whether it's good for **compost**, and why.
  - **Keeps away** (deer, animals, aphids...) and **Brings in** (bees, hummingbirds, butterflies, helpful insects).
  - **Good partners** and **Keep apart from**, each saying how well it's known: shown in trials, gardeners' lore, or simply the same (or different) light and water. Partners you already have are linked.
  - **Propagation**: methods and the best time of year in Round Rock.
  - **Breeding**: how it crosses, with links to your plants of the same species and the ones it may cross with (your three aloes, the haworthias and the hardy aloe, for example). Patented varieties such as the Queen of Elegance rose are flagged.
- These are filled in for your plants (about 50 species). For any other species, **Write them with Claude** on its page uses the owner's key and keeps the result. For mushrooms they never include eating them.
- **Wishlist prices and stock.** The shops you chose are checked every 12 hours (or when you press **Check the shops now**) for everything you still want.
  - **Shops:** eBay, Etsy, Steve's Leaves, Gabriella Plants, Logee's, Costa Farms, Wildseed Farms, Native American Seed, Baker Creek, Burpee and North Spore, plus Round Rock Garden Center, Snooper's, Cantu Imports, Mind's Eye Plants and Barry Hill. The owner can add more.
  - **On the Wishlist page:** the cheapest listing now, how many shops have it, and every listing with its past prices.
  - **Alerts:** set a price to watch for, or ask to hear when it's in stock. Alerts show on the Wishlist page and on Today, with a count beside Library in the top bar.
  - **eBay and Etsy** need free keys, which the owner saves at the bottom of the Wishlist page.
- Includes everything in 1.26.1 below.

## 1.26.1 (2026-11-01)
- **The top bar on a computer uses the whole width of the window.** It used to stop well short of both edges.
  - "Plant record" and its version are on the left, and **Online**, **Location** and **Editing as** (or **Signed in as**) are side by side on the right.
  - The page links have a line of their own underneath, all in one row, spread evenly across the window. On your 1920 × 1080 and 2560 × 1440 (150%) monitors they no longer wrap onto a second row.
  - On a window wide enough for everything, it is all on one line.
- Includes everything in 1.26.0 below.

## 1.26.0 (2026-10-31)
- **Pages use more of the screen.**
  - Paragraphs and lists run the full width of the page instead of stopping about two thirds of the way across. On the Groups page, for example, the groups now sit three or more across on your monitor.
  - **Today** shows its jobs in two columns on a wide screen.
  - Species pages, mushroom finds, Identify and the edit forms put their sections side by side when there is room.
- **New Display setting: Line length** (under Page layout). **Use the full width** is the usual choice. **Shorter lines** brings back the old limit of about 70 letters, which some people find easier to read.
- **Large text on a computer:** when the list of pages would take more than two rows (or the top bar more than a fifth of the window), it folds behind the same **Pages** button, so the bar at the top is one row. If the bar is still tall, it scrolls away with the page instead of staying pinned.
- **Phones and tablets with large text:**
  - The list of pages folds behind one **Pages** button at the top, which names the page you're on. Press it to see all the pages.
  - **Sections**, **Debug** and **Display** share one bar along the bottom of the screen instead of piling up over the page.
  - Smaller margins at the sides, so more words fit on each line.
  - Tables too wide for the screen (the cold-night checklist, the 7-day forecast, Fertilizer, Grow lights, Backups) turn into one box per row, with each value next to its column's name, instead of scrolling sideways. The long weather log still scrolls.
  - The "Shortcut: R" note under **Read this page aloud** is left out on phones and tablets, which have no keyboard.
- **Fixed:** photos on the Plants page and in the Library were about three times taller than they should be.
- Includes everything in 1.25.0 below.

## 1.25.0 (2026-10-31)
- **Display settings, rearranged as you chose (option C):**
  - The settings are in five parts (Text and colours, Page layout, Reading aloud, Photos and touch, Keyboard), listed on the left. Press one to jump to it.
  - The window fills most of the screen, and the settings sit side by side, so you scroll much less.
  - **Done** and **Reset to defaults** stay at the top, however far you scroll. Reset to defaults now leaves the window open.
  - On a phone or an upright tablet it covers the screen, with the parts as a row of buttons.
- **All pop-up windows:**
  - are wider;
  - keep their buttons in view at the bottom while you scroll;
  - close when you click or tap outside them, the same as Cancel or Done. Confirmations stay small.
- Includes everything in 1.24.0 below.

## 1.24.0 (2026-10-31)
- **Works without a connection on phones and tablets.**
  - Press **Online** at the top of the page and tick **Keep a copy on this device**. The phone then keeps every plant, mushroom find, care log and photo (full size) and opens the plant record with no signal at all.
  - Offline you can log care, edit and move plants, add photos and mushroom finds, and use your notes and wishlist. Pictures for Identify are checked once you're back online.
- **Changes are sent by themselves when the phone is back online**, each one only once. If someone changed other things on the same plant meanwhile, both are kept. If you both changed the same thing, nothing is overwritten: **Needs your decision** shows both side by side, and you choose.
- The **Online / Offline** button at the top says, in words, how many changes are waiting and how many need a decision.
- **iPhone and iPad:** add the plant record to the Home Screen (Share, then Add to Home Screen) and open it from there, so iOS keeps the saved copy. See README, "Offline use on phones and tablets".
- A mushroom find now takes its location from its photo on the computer, so this also works for finds added offline.
- Includes everything in 1.23.0 below.

## 1.23.0 (2026-10-31)
- **Every species page in the library now has more sections:**
  - **Here at home:** native or introduced in Texas, how often it's been recorded growing wild within 31 miles of home, whether it's flowering there now, and a warning if it's on the Texas invasive plant list.
  - **Will it survive outside here all year?** It answers from whether it grows wild nearby, or from its care sheet's hardiness zones against your zone (9a).
  - **Pets:** the ASPCA's answer for dogs, cats and horses.
  - **Care sheet:** **Write a care sheet with Claude** writes one for Round Rock, using the owner's key. It is kept, and marked as not checked by a person.
- **A new library filter, Texas and home:** native to Texas, introduced, invasive, grows wild near home, flowering near home this month, fungi found near home this month, likely to survive outside here, and safe for (or toxic to) dogs and cats. The cards show the same things as tags.
- **Around home:** what's flowering and the fungi found near home this month, and what's recorded wild there most often.
- These lists come from iNaturalist and the ASPCA. They are fetched in the background the first time you open the library after updating, and kept on your computer. **Lists about your area**, at the bottom of the Library page, shows them.
- Includes everything in 1.22.0 below.

## 1.22.0 (2026-10-31)
- **Mushrooms, on a page of their own.** **Mushrooms** in the top menu keeps a record of each mushroom you find (F-001, F-002…), in the yard, a plant pot or anywhere else:
  - photos from your phone's camera, with the location taken from the photo or from **Use my location now**;
  - where and when, what it grew on, and what it looks like (gills or pores, ring, cup at the base, spore print and so on);
  - its name, and how sure it is;
  - **Identify the photo shown** compares a find's photo with about 49,000 fungi, on your computer.
  - A safety note on every mushroom page. The app never says a mushroom is safe to eat.
- **Fungi in Identify and the Library.** Choose **Fungi worldwide** under **Look in**. Fungus pages offer **Record a find of this**.
- **A wishlist.** **Add to my wishlist** on any species page, and **Your wishlist** on the Library page, with **Got it**, where to find it and notes.
- **Your own notes and tags on any species**, shared with everyone who has access. Tags show on the library cards, and **Show** can list your wishlist, your notes or one tag.
- **Photos for offline use.** The owner can download the photo and facts for every Texas plant in the background (about an hour and a half, about 300 MB).
- **The first start after this update** downloads about 100 MB of fungus fingerprints for the picture checker, which takes a few minutes. Its container is rebuilt too.
- Includes everything in 1.21.0 below.

## 1.21.0 (2026-10-31)
- **"Watered today" works once a day.** After you press it on a plant page it says **✓ Watered today** and is switched off until tomorrow. Undo, or Remove in the care log, switches it back on. A plant can't get two waterings logged for the same day any more, from any button.
- **Water all** on the Plants page marks every plant shown (with your filters) as watered today. Plants already watered today are skipped. It asks first, and the message has Undo.
- **Wide photos are no longer blurry on the Plants page.** They used to be cut down to a tall slice and stretched. Now they're shown whole, with a plain band above and below, and every card photo is sharper. Display, "Photos on the Plants page", changes this: you can always fill the card, or always show the whole photo.
- **The library is now a browsable reference.** It lists every species in the chosen list without a search. You can search as you type, filter by kind of plant, family, where it grows wild, yours, and common name, sort, and switch between cards and a table. Each species has its own page with photos, a description, names, classification, US states, your plants, lookalikes and links. Photos and descriptions come from iNaturalist and Wikipedia, fetched once and kept on your computer; the owner can turn that off at the bottom of the Library page. See README, "The plant library".
- Includes everything in 1.20.0 below.

## 1.20.0 (2026-10-31)
- **Browse a plant's photos on the Plants page.** Each card with more than one photo has **‹** and **›** buttons and says "2 of 5". On a phone or tablet you can swipe left or right on the photo. This doesn't open the plant; clicking anywhere else on the card still does.
- **Choosing the main photo is easier to find.** On a plant page, the main photo now says "★ This is the main photo" under it, and its thumbnail is marked **★ Main**. Pick any other photo and press **Make this the main photo**. The Plants page, the care cards and plant link previews then show it.
- **Care cards, as you asked:**
  - **4 × 6 inch cards** are now the usual size: one line each for water, light, temperature, humidity, feeding and dangers, in large print. They print sideways on 4 × 6 inch paper. 78 of the 82 plants fit on one card; the rest run onto a second. The full page is still there under **Size**.
  - **Dangers to pets and people are shown to start with.** (Your earlier choices on that page start over once, so the new defaults apply.)
  - **The smallest text is bigger.** The "Printed on" line and "Scan for the full page" are now the same size as the notes. Nothing on a printed card is smaller than about 16 point.
  - **Print care cards for all plants** is on the Labels page.
- Includes everything in 1.19.1 below.

## 1.19.1 (2026-10-31)
- **Fixed: the updater can delete old Docker images again.** At the end of an update it offers to delete the images older versions left behind. When you answered yes, it said "invalid reference format: repository name (library/Stop) must be lowercase" and deleted nothing, because a name mix-up in the updater asked Docker for an image called "Stop". Your app and data were never affected.
- The updater now lists every older image, including the picture checker's (about 2 GB each), and deletes all of them when you say yes. The fix takes effect from the update after this one, because each update runs the updater that was already installed. While installing 1.19.1, just press Enter at that question.
- Includes everything in 1.19.0 below.

## 1.19.0 (2026-10-28)
- **Undo right after a care button.** After you press **Watered**, **Still moist**, **Watered all** or save **Log other care**, the message that appears says what was saved and has an **Undo** button (and **Close**).
  - It stays for 30 seconds and counts down, and the countdown pauses while the pointer or keyboard focus is on it.
  - With a keyboard, **U** undoes it while the message shows.
  - Undo removes only the entries that press made. For "Watered all" it says how many.
  - The change log records it as "Undone right after it was logged".
- **Large-print care cards.** Plant pages have a new **Large-print care card** button, and group pages have **Large-print care cards** (one card for each plant).
  - Each card has the plant's name, code, place and winter plan, its photo, and a code to scan that opens its page.
  - Boxes headed Water, Light, Temperature, Humidity, Feeding and, if you tick it, Careful (dangers to pets and people).
  - Above the cards you choose short or full notes, and whether to show the photo, the scan code and the dangers. Then press **Print**.
  - The printout is always black on white, large print (about 16 point notes, 20 point main facts), one plant per page.
- Includes everything in 1.18.1 below.

## 1.18.1 (2026-10-28)
- **The top menu fits on iPads again.** On an iPad mini (and other mid-size screens with larger text) the menu links were squeezed into one narrow column, one link per line, so the menu filled the whole screen. Now the links sit side by side and wrap onto a few rows. On narrower screens the menu gets its own full-width row under the name, and the Location and "Editing as" buttons sit side by side when they fit.
- Includes everything in 1.18.0 below.

## 1.18.0 (2026-10-26)
- **Identify a plant** (new page in the top menu). Point your phone or computer camera at a plant:
  - If it's one of yours, a window names it and says how sure it is, for example "Very likely P-020: Fiddle-leaf fig, 93% sure". It shows your picture next to the plant's closest photo, with **Open its page** and **Add this picture to its photos**.
  - When it is unsure between a few of your plants, it asks **Which one is it?** with their photos.
  - When it's probably not one of yours, it suggests what it could be. You choose the list it names from: Texas plants, plants with a common name and all US plants, US plants, or all plants worldwide. Each suggestion links to USDA PLANTS, Kew and Wikipedia, and has **Add as a new plant**, which fills in the names and attaches the picture.
  - It also reads the QR codes on plant labels.
  - **Use a photo instead** checks a photo you already have.
- **It all runs on this computer**, in a new container called `plant-vision`, with the free BioCLIP 2.5 model. The first start downloads about 5 GB into `data\vision` and takes 20 to 40 minutes; the page shows how far it has got. After that it needs no internet. See README, "Identify a plant and the plant library", which also says how to stop it or use a smaller model.
- **Second opinions:** when it is unsure you can press **Ask Pl@ntNet** (free key, 500 pictures a day) or **Ask Claude** (your Anthropic API key, a cent or two a picture). Save the keys once at the bottom of the Identify page. They are never shown again, only their last 4 characters.
- **Plant library** (new page in the top menu): look up any of 349,000 plant species by scientific or common name. It shows the family, whether the plant grows wild in Texas or other US states, and whether you have it. It has the same links and an **Add to my plants** button.
- People who can only view can use Identify and the library, but can't add pictures or plants or ask for second opinions.
- If the picture checker can't be built during an update (for example, the internet drops), the updater now starts the rest of Plant record without it and says so.

## 1.17.1 (2026-10-26)
- **Fixed: "Add a plant" works again.** The form stopped with "Something went wrong: Assignment to constant variable" instead of opening. It had been broken for a while; plants added by upgrade batches were not affected.
- Includes everything in 1.17.0 below.

## 1.17.0 (2026-10-26)
- **More filters on the Plants page,** in a fold-out under the filter row (it says how many are on):
  - **Light needs:** low light, bright indirect light, some direct sun, or full sun.
  - **Pets:** safe for pets (only where the ASPCA lists the plant as non-toxic), not known to be toxic, mildly toxic, or toxic.
  - **Winter here:** hardy here, not hardy here, or annual / no zone set, comparing each plant's zone with yours.
  - **Care today:** water or feeding due, as on the Today page.
  - **Grow light:** under a grow light spot, or not.
  - **Leaf type** and **pot size.**
  - **Photos:** no photo yet, or the newest photo is over a month old.

  They are also in the Previous / Next panel on plant pages, and are remembered like the other filters.
- **Safety for pets** is a new field on every plant, filled in for all of them. It shows in the Dangers box on each plant page, and you can change it under Edit, "About this plant".
- **Your answers:** the young Monstera's page now says it started with at least five larger leaves without holes, before an animal ate them. The fern's tag request is closed.

## 1.16.2 (2026-10-26)
- **Plants page filters:**
  - **Show:** active plants only (the usual), active and archived together, or archived only. Archived plants say "Archived" on their card. It replaces the "Show archived plants instead" box at the bottom of the page.
  - **Location:** only the plants outdoors, on the covered porch, indoors, or in the garage or shed.
  - Both are also in the Previous / Next panel on plant pages, and are remembered like the other filters.
- **Your porch shelf photos are in.** This replaces 1.16.1, which you can ignore.
  - **New page: Chinese evergreen, red speckled (second).** The second one on the shelf, not P-028. It is healthy and has a new pink shoot at the base. The mix has dried hard and shrunk from the pot wall, and white mineral crust is building up on the pot; its steps say how to fix both.
  - **New page: Boston fern, curly (grey bowl).** A second curly fern, mostly dead fronds but with healthy new ones coming. Spurge weed is growing in its pot.
  - **New page: Monstera, young (beige pot).** Young shoots with their first holes, coming from an old knot of roots.
  - **Pink Princess cutting (P-035):** its tag reads "PP-1", so that request is answered. The bamboo stake is still down in the hollow stem; pulling it out is still the first step.
- Two new requests: a close photo of the fern's tag, and how the young Monstera started.
- Photos come in the photo pack `plant-database-photos-batchA7.zip`, already in your `versions_plant-database` folder.

## 1.16.0 (2026-10-25)
- **Groups of plants.** A new **Groups** page, in the top menu. A plant can be in several groups.
  - **Smart groups** have a rule, such as "Genus is Philodendron" or "Location is Covered porch". Plants that fit join by themselves. While you make one, the window lists the plants that fit.
  - **Hand-picked groups** hold the plants you choose.
  - **Suggested groups** are ready to add with one press. They cover plants of the same genus (Philodendrons, Roses, Majesty palms and more), families that share care (Aroids, Cacti, Aloes and haworthias) and plants under the same grow light.
- **On the Plants page,** choose a group to see only its plants, or sort by group. Previous and Next Plant follow the same choice.
- **On each plant page,** the card at the top lists the plant's groups. **Change groups** adds it to hand-picked groups or makes a new one.
- **Each group's page** shows its plants and what suits all of them: temperature, humidity, light, soil, how warm to keep them, and their potting mixes and fertilizer. Where the plants disagree, it names the odd ones out.
- **Do something to all of them:**
  - **Log care** (watered, fed, repotted, sprayed and so on) for every plant you tick.
  - **Move them:** a new Location or Spot, or under a grow light spot.
  - **Change a setting**, such as the potting mix or how often to water. You see each plant's current value first and choose which to change. **Undo this change** puts them back, except any plant changed again since.
- Anyone who can edit can make and change groups. People who can only view see them.

## 1.15.0 (2026-10-25)
- **Your plant calendar.** Feeding days and cold nights can go into Google, Outlook, Samsung or Apple calendars, with reminders at times you choose.
  - Find it at the bottom of the **Today**, **Fertilizer** and **Cold-night checklist** pages: **Set up your calendar**.
  - One feeding day a week on the day you choose. A plant is never fed early: it goes on the first feeding day on or after it is due.
  - Subscribe with a private link so it updates by itself. For Google, Outlook.com and iCloud to reach it, the README and the window have the Tailscale Funnel steps. Funnel shares only the calendar link.
- **Back outside.** A spring page, from **Winter plan**, that says which indoor plants can go back out, using each plant's own temperatures and the 7-day forecast: Ready, Safe but cool, Too early, or Not yet.
- **Your lamps and sockets recorded.** You have 14 sockets for 9 bulbs, so every bulb can be used. Each bulb's "Where it is" has a suggestion you can change:
  - the 80 W bulb on the long-cable socket, hung bare;
  - the two 30 W bulbs in two clamp lamps;
  - the six 10 W bulbs in the third clamp lamp and five bare sockets, leaving five bare sockets spare.

## 1.14.1 (2026-10-25)
- **Swipe between plants.** On a phone or tablet, swipe left on a plant page for the next plant, or right for the previous one.
  - A label shows which plant is coming, and says "Let go to open it" once the swipe is far enough.
  - It ignores up-and-down scrolling, short nudges, swipes that start on a menu or the photo, and swipes from the very edge of the screen, which your phone uses for Back.
  - Turn it off in **Display** if it gets in your way.
- **The section menu lists every part of a plant page.** It now includes **Photos** and **Name and details**, the card at the top with the name, location and ID.
  - The row of section buttons now has every section too, including "Details", "Coming inside" and "Timeline", which were missing.
  - Both lists are made from the page itself, so sections added in future updates appear in them by themselves.

## 1.14.0 (2026-10-25)
- **About this plant**, a new section on every plant page, after Identification. For all 81 plants it gives:
  - type of plant (tree, shrub, vine, succulent and so on) and its classification: kingdom, order, family, genus and species;
  - mature height and width in the ground and in a pot, growth rate and lifespan;
  - USDA hardiness zones, and whether it is hardy where you are. Round Rock works out to **zone 9a** from your own weather history (a coldest night of about 22°F in a usual winter), and is on the line between 8b and 9a on the 2023 USDA map;
  - native range around the world, conservation status (IUCN Red List and CITES where they apply) and invasive risk;
  - flowers, fruit (and whether it is edible), and propagation, step by step;
  - dangers to people and to pets, in their own box with the Poison Control and ASPCA numbers.
- **Sources with links** under every plant: the extension services, botanic gardens and references the details came from. They open in a new tab.
- Where a plant's identification is less than 85% sure, the section says the details are for the closest match.
- Everything here can be changed with **Edit**, under "About this plant". The update only fills fields that are empty, so nothing you typed is replaced.

## 1.13.1 (2026-10-24)
- **Rooms and shelves** on the Grow lights page. Your rooms and shelves are listed, ready to use:
  - Downstairs Living Room: Tall Black Shelf, Tall Brown Shelf, Short Brown Shelf, Large Brown Hutch and Side Table
  - My Bedroom: Shelves
  - Garage
  - Upstairs Living Room

  Add more at any time, for example each bedroom shelf you put up. A light spot now has **Where**, so you choose which room and shelf it is on.
- **Manufacturer model** for every light, to fill in from its box or label.
- **Your answers recorded:** all the bulbs use the E26 base, and the disk light is new and can go anywhere. Two new questions are in the open requests: what will hold the bulbs, and the model numbers.

## 1.13.0 (2026-10-24)
- **Grow lights page.** Your 11 grow lights are in the app, from the photos and listings you saved:
  - each with a photo, how many you have, its timer and brightness steps, and the maker's light figures (or Claude's estimates, marked, where the maker gives none);
  - the maker's charts open as pictures.
- **Light spots.** Say which light is over which plants, how far away, for how many hours and how bright. The app works out the daily light at the leaves and says for each plant whether it is too dim, good or too bright, as you change the setting.
- **Suggested layout.** For the 41 plants that live inside or are coming in, a plan that shares your lights out. Plants needing the most light go first, each under the smallest light that gives it enough, with room for its pot. Set up any suggested spot with one press and rename it.
- **Easing plants in.** Each spot has a first and second week brighter and longer than its own setting, so plants used to the sun adjust.
- **On each plant page**, under Sunlight: its light spot, or what the plan gives it.
- **Questions for you** about the lights are in the open requests: which lamps the bulbs screw into, the T8 set, the disk light, and where the plants will go.

## 1.12.2 (2026-10-24)
- **Update zips have a folder of their own.** Release zips and photo packs now live in `versions_plant-database`, inside your Plants folder, instead of cluttering the Plants folder itself.
  - The updater moves every `plant-database-….zip` it finds in the Plants folder into that folder, including your older ones, then looks for the newest version there.
  - If a zip is already there under the same name, a copy that matches exactly is removed from the Plants folder. A copy that doesn't match is left where it is, and the updater says so.
  - The updater, `Update Plant Database.cmd` and `update-log.txt` stay in the Plants folder, next to `plant-database`.

## 1.12.1 (2026-10-24)
- **The app starts on any computer after updating.** On yours, 1.12.0 stopped straight away: its new ordinary user wasn't allowed to write to the photos folder that older versions made.
  - Now the app checks this itself each time it starts. If it may, it runs as that ordinary user. If not, it runs as root inside its container, as before 1.12.0.
  - Nothing needs doing either way, and your plants and photos aren't changed.
  - The first line of its log says which way it runs, and so does the **Debug** window (owner only). README: "Which user the app runs as".
  - The `docker-compose.override.yml` file that fixed this by hand is no longer needed, and the updater removes it.
- **A busy port no longer stops the update.** If port 8080 is still in use when the app restarts, the updater:
  - tells you to close any browser tabs with Plant record open
  - waits, and tries again for about a minute
  - if the port is still busy, names the program that has it and moves the app to a free port (for example `http://localhost:8090`). The Tailscale address stays the same.
- **No more "Control server error" lines in the log.** The new gunicorn version wanted to make a control file on the read-only container. That part is now switched off; the app never used it.

## 1.12.0 (2026-10-24)
- **Use the app away from home, safely.** The app now has its own Tailscale device, "plants". With Tailscale on, you open it at `https://plants.<your-tailnet>.ts.net` from anywhere: encrypted, with a real certificate, and without opening anything on your router.
  - Run **Set Up Remote Access** once (in `plant-database\tools`; README: "Using the app away from home"). It signs the device in, checks HTTPS and makes you the owner.
- **Share it with someone.** Share just the plants device in Tailscale. They reach the plant app and nothing else of yours.
- **Signed in by Tailscale.** The top right says "Signed in as …", and the audit log names people by their Tailscale account instead of a typed name.
- **What people may do.** Press your name to see everyone who has opened the app and choose what each can do:
  - **Can view only:** sees everything, changes nothing. Everyone starts here.
  - **Can edit:** also makes changes.
  - **Owner:** also backups, settings and this list.
  - The app enforces this on every request, not just by hiding buttons.
- **Closed to the home network.** Only this computer can open `http://localhost:8080` now; everyone else comes in through Tailscale. Your old `http://<your PC>:8080` address (on the Wi-Fi or through Tailscale) stops working. A line in a `.env` file opens it again if you need it (README).
- **Sensors** get their own port (8082). It only takes readings with the token, and it stays shut until you open it.
- **A tighter container.** The app no longer runs as root, has no special privileges, and its program files are read-only. Each update now rebuilds it on a freshly downloaded base image and fetches the newest Tailscale container, so the security fixes Docker warns about keep arriving.

## 1.11.0 (2026-10-23)
- **What each plant needs, on the Fertilizer page.** Under each plant's code and "last fed" line:
  - the N-P-K ratio it needs and how strong to mix it, for example "Needs N-P-K ratio 2-7-7, at half strength";
  - the fertilizer of yours that matches it best, with its N-P-K numbers and how close it is (✔ Matches, ✔ Close, ▲ Usable or ■ Not a good match);
  - how much to use: for a liquid or powder, how much to mix into how much water ("Mix ⅝ tsp into 1 gallon of water"); for granular or slow-release, what share of the label amount.
  - The same box, **What to feed it**, is in the Nutrients section of each plant page. **Log** for one plant starts with that fertilizer and amount filled in.
- **Your fertilizers** (Fertilizer page): every fertilizer you have logged, plus any you add with **Add a fertilizer you have**, even before you use one. You have not logged any yet, so add the ones you own to see the matches.
- Every plant has its ratio and strength filled in (upgrade batch `batchA2`). Change them on the Edit page, under Nutrients.
- **Location, on every page.** A **Location** button at the top of every page (or the **L** key) chooses the place used for weather, frost warnings, watering, the Winter plan and "today". This browser remembers it; other computers and phones keep their own. You can also add a town by name there, and make a place the home place for everyone.
  - Nothing is tied to Round Rock any more: headings say "Winter in Baraboo", the frost banner names the place, and the marks on the temperature and humidity strips come from that place's own weather history.
  - The Winter plan's written Round Rock notes show only when Round Rock is in use. Elsewhere, its expected weather comes from that place's own history.
- **Your answers of October 23** (upgrade batch `batchA2`):
  - P-017 Majesty palm: the spear holds firm, so no bud rot. Health is now Fair.
  - P-036 is not stevia (no sweetness). It is now "Young shrub with toothed leaves (not stevia)", with a new quick check: is the stem square or round, and does a crushed leaf smell?
  - P-042 Agave: the yellow leaf is firm, an old leaf dying back, and the roots are healthy. Health is now Good.
  - P-053 gourd vine: the black specks are insects, probably aphids, with steps to treat it.
  - P-055 Black Cardinal: the specks are sun scorch, not pests.
  - P-060 is Syngonium 'Black Velvet', from its tag.
  - P-081 is Philodendron 'Ring of Fire', from its HEB tag.
  - P-025, P-048 and P-066: blank, wrong or missing tags noted.
  - Notes from the new photos of P-006, P-031 and P-061.
  - The 10 answered requests are closed, and 2 items on "Still to photograph" are ticked off.

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
