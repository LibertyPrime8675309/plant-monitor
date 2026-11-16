# Your plants and their pages

Part of the Plant record manual. The README in the folder above has how to start, stop, update and back up the app, and the list of every manual page.

## Photos on the Plants page, and the main photo (from 1.20.0)

- **On the Plants page,** a plant with more than one photo has **‹** and **›** buttons on its photo, with "2 of 5" between them. They step through all its photos without opening the plant. On a phone or tablet you can also swipe left or right on the photo. With the keyboard, move to a photo button with Tab, then use the Left and Right arrow keys. Click anywhere else on the card to open the plant, as before.
- **The main photo** is the one the Plants page shows first, and the one on care cards and in plant link previews. On a plant page, the photo panel says "★ This is the main photo" under it, and its thumbnail is marked **★ Main**. To change it, pick another photo and press **Make this the main photo**.

- **Wide photos** (from 1.21.0): a photo taken sideways used to be cut down to a tall slice of its middle and stretched, so it looked blurry. Now the Plants page shows wide photos whole, with a plain band above and below, and every card photo is sharper. To change this, open **Display** and choose **Photos on the Plants page**: show wide photos whole (the usual choice), always fill the card, or always show the whole photo.

## Plants page filters

From 1.58.0 the Plants page starts with its plants. The count ("101 of 101 active plants shown") sits beside the title. Under it is one row of tools: **Search**, **Home** (with more than one home), **Location**, **Winter plan** and **Sort by**. Under that is one row of small buttons: **More filters**, **Plants that need something from you**, **Copy my answers for Claude**, the photos still to take, and **Water all**. **What Water all does** opens its explanation. Then the plants. On a phone only the search box stays out: the lists are in **More filters** and the buttons are in **More to do here**. Before 1.58.0 the first plant was most of a screen down on a computer and more than two screens down on a phone.

The filter row on the Plants page narrows the list. Every filter is remembered in this browser, and **Clear filters** resets them.

- **Search:** name, code, location or plant type.
- **Winter plan:** a list in the row of tools, with how many plants have each plan (from 1.58.0; it was a row of five coloured buttons). **Health** is in More filters.
- **Location (from 1.16.2):** outdoors, covered porch, indoors, or garage or shed.
- **Group (from 1.16.0):** only the plants in one group.
- **Show (from 1.16.2):** active plants only (the usual), active and archived together, or archived only. Archived plants say "Archived" on their card. Archiving hides a plant without deleting anything; **Move back to the main list** on its page undoes it.
- **More filters (from 1.17.0),** in the fold-out under the filter row:
  - **Light needs:** low light, bright indirect light, some direct sun, or full sun, from each plant's daily light range.
  - **Pets:** safe for pets (only where the ASPCA lists the plant as non-toxic), not known to be toxic, mildly toxic, or toxic. This comes from the plant's "Safety for pets" field (Edit, "About this plant").
  - **Winter here:** hardy here, not hardy here, or annual / no zone set. It compares the plant's coldest zone with yours.
  - **Care today:** water or feeding due, the same as the Today page.
  - **Grow light:** under a grow light spot, or not.
  - **Leaf type** and **pot size.**
  - **Photos:** no photo yet, or the newest photo is over a month old.
- **Sort by:** code, health, ID confidence, recently updated, name, or group.
- **Needs something from you** and **ID confidence under 70%.**

## Date acquired (from 1.58.0)
Every plant page has a **Date acquired**: the day the plant came to you.

- **Set it** on **Edit this page**, under **Names and place**, or on **Add a plant**. It is a date box, so you can type the date or choose it from the calendar. If you only know the month, choose its first day. If you do not know, leave it empty.
- **See it** on the plant's page with its other details, such as "May 17, 2024 (2 years and 6 months ago)". A page with no date does not show the line.
- A date in the future is refused. Changing it is in the page history like any other edit, and Undo there puts the old date back.
- An update file from Claude can set it too (field `acquired_on`, written as `2024-05-17`).

## Previous and next plant (from 1.7.5)

Every plant page has **Previous Plant** and **Next Plant** buttons, each showing the name and code of the plant it leads to. On a wide screen they sit in the margins either side of the page; on smaller screens and phones they sit at the top of the page, under the plant's name (from 1.56.5 the name comes first).

**Swipe (from 1.14.1).** On a phone or tablet, swipe left anywhere on a plant page for the next plant, or right for the previous one. While you swipe, a label names the plant that is coming; once it says "Let go to open it", lifting your finger opens it. Start the swipe away from the very edge of the screen, because your phone uses edge swipes for Back. Swipes that start on a menu, a form field or the photo are left alone, and so is scrolling up and down. To turn it off, open **Display** and set **Swipe between plants** to Off.

They follow the Plants page filters and sort order. The fold-out **Filters for Previous / Next** panel at the top of each plant page has the same filters (search, winter plan, health, location, group, show, sort, "needs something from you", ID under 70%) and shows where the plant falls in the list. Changing a filter in either place changes it in both, and this browser remembers it.

## Location: outdoors or indoors (from 1.7.0)

The label at the top of every plant page now starts with **Location**: Outdoors, Covered porch, Indoors, or Garage or shed. It is a menu. Click it (or Tab to it and use the arrow keys) and pick another place, and the change is saved straight away and recorded in the page history. The old free-text "Location" field, for example "Covered porch pallet shelf", is now called **Spot**.

On the **Winter plan** page each plant in "Plant by plant" has a **Moved indoors** button. Pressing it sets the plant's Location to Indoors and takes it off those lists. It is also left out of the frost warnings in "The next 7 days". Plants already inside are listed under **Already inside**, each with a **Moved back outside** button. After upgrading to 1.7.0, every plant started as Outdoors; 1.8.0 set the plants whose Spot is on the covered porch to Covered porch, unless you had already changed them.

## Plant timeline (from 1.8.0)

Each plant page has a **Timeline** section, just above Page history (also in the On this page menu):

- how the plant is doing over time, for example "Health: Critical until Oct 22, Poor now (getting better)"
- **Compare two photos:** the oldest and newest photo side by side. Pick others with the **Left photo** and **Right photo** menus, or press **Compare** under any photo in the list.
- **Everything that has happened**, newest first and grouped by day: photos, changes to the page (the important ones in words, such as "Health rating: from Fair to Poor"), feeding and care, answered requests, and when the page was created. Tick boxes under **Show** hide any kind.

## Photo check (from 1.8.0)

When you add photos, each one is checked in your browser first. Photos that look fine are added straight away. If any look **blurry**, **too dark**, **too bright (washed out)** or are a **very small picture**, a box shows them with what to do, and these buttons: **Take a new one** (opens the camera or file picker again), **Add only the good ones**, **Add it anyway** and **Cancel**. Nothing extra is sent anywhere.

## Current conditions and the "Now" marker

Each plant page has a **Current conditions** box. Press **Set current conditions** (or **Change**) and choose where the numbers come from:

- **I will type them in**: temperature (F), humidity (%), and light as PAR or lux. The dialog lists rough light values to use if you have no meter (full midday sun 1,500 to 2,000 PAR, open shade 200 to 600, under a porch roof 100 to 400, bright window 100 to 300, lamp-lit room 5 to 30).
- **My sensor**: the newest reading your sensor sent (see below).
- **Online weather**: the latest hour from Open-Meteo for your location. This is open sky, so plants under a roof or in shade get less light than it says.

The setting is shared by all plant pages. Every gauge (temperature, humidity, light, soil moisture, soil temperature, soil pH) then shows a labelled **Now** marker. When a value is outside the plant's range, the page gets a **Getting this plant back in range** section with numbered steps for that plant and that situation (for example how to protect it from a cold night, or how to raise humidity). Readings that are old are flagged as out of date.

## Location (from 1.11.0)

Nothing in the app is tied to Round Rock any more. The **Location** button at the top right of every page (on a phone, at the top of the page) shows the place in use, for example "Location: Round Rock, TX". Press it, or press **L**, to choose another.

- **Everything weather-related follows it:**
  - the frost banner and the cold-night checklist ("Frost warning for Baraboo: …")
  - current conditions and the "Now" marker on plant pages
  - the marks on the temperature and humidity strips: the coldest night of a usual winter there, and its usual coldest-month night, worked out from that place's own weather history
  - "Winter in …" on plant pages
  - the Winter plan, the Today page's watering reminders and rain
  - the Weather page
  - what "today" means
- **This browser remembers the choice.** Each computer or phone keeps its own, so someone else using the app somewhere else can pick their own place without changing yours.
- **Add a place** in the same window: type a town or city, press **Search** (or Enter) and choose **Add and use** next to the right one. Its last 3 months of weather and its forecast arrive within a minute.
- **Make … the home place for everyone**: the home place is what a computer or phone uses until it chooses its own location, and what the hourly updates and backups use.
- The Winter plan's written notes, sources and expected-weather table are for Round Rock, so they show only when the place in use is Round Rock. For other places the expected columns come from that place's own weather history, once it has 3 years or more (use **Load history** on the Weather page).

## Environment fields on every plant page

Besides the temperature, humidity and light ranges, each plant now has: a feeding season and interval (months and days), heat-damage temperature, comfortable air dryness (VPD, in kPa), comfortable light as PAR and as daily light (DLI, mol/m2/day), soil mix, soil pH, soil moisture and soil temperature ranges, fertilizer and nutrients, pests and diseases to watch, what to do about them, and current pest problems. Claude filled these in as a first guess for every plant from its type; they are guesses to check against your own experience, and everything is editable (Edit this page) with the usual version history.

## Past days: what the values were on a date

Temperature, Humidity (and air dryness), Light, and Water and soil (soil moisture, root-zone temperature, pH) each have a **Past days** box. Open it, pick the date on the calendar (or use the arrow keys), and you see that day's lowest, average and highest value, how many hours were in range, a chart of the day, and the plant's comfortable range **as it was recorded on that date** (if you changed the range later, both are shown). Each day on the calendar is marked in range, a little out, out of range or danger, and "Fed" where fertilizer was applied. Pick where the readings come from: your sensor, numbers you typed into Current conditions, or the online weather (outdoors, so for plants kept inside it only shows what the weather was). Days before any data was stored are blank; the online weather loads about 3 months back the first time, and more from the Weather page.

## Plant links and previews

Plant codes such as P-012 written anywhere in the Still to photograph list, in requests, or in a plant page's text link to that plant. Point at a link (or Tab to it) to see a small preview with the plant's photo, name and health; Escape closes it. On the **Photos** page you can add your own entries with a note and a **Related plant**, and **Edit** any entry; codes you type are linked too.

## Plant labels

Each plant page also has a **Label** section with the same label and a **Print this label** button (it prints only the label). On the **Labels** page every label has an **Open plant page** button. The plant ID (P-001 and so on) is now large, bold and black on the white label in every theme, including dark.

Open **Labels**, type the address from step 1 into "Address the codes should open", save, and print. Each label has a QR code that opens that plant's page. Codes made with `localhost` only work on the PC itself.

## Who made a change

People who open the app through Tailscale (from 1.12.0) are named by Tailscale: the top right says "Signed in as …", and their changes show under that name. Press it to change the name shown for you, and (owner) to see who can use the app.

On this computer (`http://localhost:8080`), the first time you save something the app asks for your name. It goes into the audit log with the date and time. It is typed in, not a login, so it records who says they made the change. Click your name at the top right to change it.

If you open the app to your home network again (see "Using the app away from home"), you can also require a password there: uncomment `PLANTDB_PASSWORD` in `docker-compose.yml` and run `docker compose up -d`. The browser then asks for it (leave the username blank or put anything). Never open port 8080 to the internet.

## Groups of plants (from 1.16.0)

The **Groups** page (in the top menu) gathers plants that are alike or kept together, so you can see what suits all of them and look after them in one go. A plant can be in several groups.

- **Smart groups** have a rule. For example "Genus is Philodendron", "Location is Covered porch", or "Name contains palm". A rule can have several parts, and plants join when every part fits, or when any part fits. Plants that fit join by themselves, and leave when they stop fitting. While you make or change the rule, the window lists the plants that fit.
- **Hand-picked groups** hold the plants you tick. Add or take out plants on the group's page, or from a plant's own page with **Change groups**.
- **Suggested groups** are listed under your own. They cover plants of the same genus, families whose plants share care (such as the Aroids, which use the same chunky potting mix), and plants under the same grow light. Press **Add this group**, or **Add all suggested groups**.
- **On the Plants page,** choose a group under **Group** to show only its plants, or choose **Sort by: Group A to Z**. Previous and Next Plant on plant pages follow the same choice.
- **On a plant page,** the card at the top lists the plant's groups, with links.

Each group's page has:

- **Plants in this group**, with where each one is.
- **What suits all of them**: the temperature, humidity, light, soil pH and soil moisture that suit the most plants, with the odd ones out named. It also shows how warm to keep the group, and because of which plants, and their winter plans, fertilizer ratios and potting mixes.
- **Do something to all of them** (for people who can edit):
  - **Log care for all of them:** what you did, the date, an optional note, and which plants (all are ticked to start with).
  - **Move them:** a new Location, a Spot such as "Tall Black Shelf", or a grow light spot (or take them out of their grow light spots).
  - **Change a setting for all of them:** choose the setting and the new value, and the next window shows each plant's current value. Plants already set to it are not ticked. Plants with a value different from the rest are marked, so you can leave them out. Only the ticked plants change. If someone changed a plant in the meantime, it is skipped so nothing is overwritten unseen.
- **Recent changes to the whole group,** each with **Undo this change**. Undo puts each plant back as it was, unless it was changed again since.

Removing a group never changes the plants in it. Group changes appear in the audit log under "Groups and changes to a whole group", and each plant's page history shows its own changes.

## Homes, adding several plants, and your plant photos (from 1.28.0)

### Homes

Plants can live at more than one home: Round Rock, and Nevada City in California (added with this update). Each home has its own weather, frost warnings, watering and hardiness zone.

- **Every plant has a Home** (under Names and place when you edit it). Plants you already had are at the main home, Round Rock.
- **The Plants page** has a **Home** filter, and each card says which home the plant is at (⌂ Nevada City, CA). The Identify photo table and Previous / Next follow the same filter.
- **Choose a home with the Location button** to see its weather, frost warnings, watering and Back outside. Each of those only lists the plants at that home. A place where no plants live (one you only watch the weather for) shows the main home's plants, as before.
- **The Weather page's Places table** has a **Plants** column, and **Plants live here** or **No plants live here** for each place. A home with plants in it can't be removed or turned back into a weather-only place until its plants are moved.
- Hourly updates and backups still use the main home.

### A home is a site (from 1.48.0)

Each home now carries these settings, on **Weather → Homes and places**, in its Plants column (the owner changes them):

- **Country** (a two-letter code, filled in from the search when you add a place).
- **Units there**: what people see who have not chosen units of their own in Display. Your own choice always wins.
- **Care** (from 1.58.0, not on the main home): **Logged in this app** (the usual) or **Done outside the app**, for a home where nobody records care in the app, such as Baraboo. Water all, a group's care and Today's water-them-all buttons leave its plants out; you can still log care for one of its plants on that plant's page. Baraboo starts as Done outside the app.
- **Seasons**: a winter with frost (the usual), a cool season where frost is rare, or wet and dry seasons with no frost. At a home with no frost, the Care section has no Winter plan, Cold-night checklist, Coming inside or Back outside, and Today has no cold-night, coming-inside or frost-dates blocks; the Care button opens the first page that applies there.

Today follows the home chosen with the Location button for everything now: water, feed, Needed from you, coming inside, turning, the health walk-through and the frost blocks all list only that home's plants. The Plants page keeps its own Home filter.

**Editors at some homes only.** In the people list (Settings → people and names), an editor's row lists your homes with a tick box each. Untick a home and that person can still see everything, but cannot change plants at that home (their pages, care log, photos, requests). The owner is never limited. Lights, pots, groups and places are shared between homes and are not limited this way. From 1.58.0 the limit is checked wherever a plant is changed: its photos, questions, fertilizer and potting-mix entries, pest sightings, grow light spot and shelf follow the plant's home too, and such an editor can add plants, or move them, only at their own homes. Before 1.58.0 some of those went through when the request did not carry the plant's code.

### Add several plants at once

**Add a plant** now starts with two buttons: **One plant** (the form, as before) and **Several plants from photos**.

1. Choose the home and the location (Outdoors, Indoors...) for the plants.
2. Choose all the photos at once. A photo of a plant's label or tag helps.
3. Press **Check these photos**. Each photo is checked by the picture checker on this computer, one at a time ("Checking photo 3 of 12").
4. **The review screen** shows one box per plant:
   - From 1.38.0, under each photo you say what it shows: **Same plant as the photo above**, **A different plant**, **Shows all of them** (a wide shot that goes on every plant) or **Leave this photo out**. The photos are in the order they were taken; the first guess is "same plant" when the picture checker sees the same species in both, and the plant boxes follow your answers. (The old "taken within 3 minutes" grouping is gone.)
   - **What the picture checker thinks it is**: the 3 likeliest species, with how likely each is. The names, family, genus, plant type, safety for pets and ID confidence are filled in from the one chosen. Choose another, or **None of these** to type them yourself. Anything you type is kept.
   - **This may be a plant you already have** appears when a plant looks like one in the record. It starts unticked, so it isn't added twice.
5. Press **Add N plants**. Nothing is added until then. Each plant gets its photos (the first is the main photo), and its page says where its name came from.

The care details (temperature, water, light...) start empty, as with one plant. Photos waiting on the review screen are kept for two days.

### Your plant photos (Identify page)

At the bottom of the Identify page, **Your plant photos** lists every plant, one row per plant, with its photos in a strip, its home and spot, and the date of its newest photo. These are the photos Identify compares your pictures with. Choose a plant or a photo to open its page. It has the same search and filters as the Plants page (changing them here changes them there), plus **Only plants with no photos**. It shows 30 plants at a time, with **Show more**.

### Not tied to Texas

From 1.28.0 the Library's lists, filters and tags, Identify's state list, and the question sent to Claude all follow the place chosen with the Location button. The cleaning-the-pot tip no longer mentions Central Texas, and the mushroom safety page points to a local mycological society anywhere. The written winter notes for Round Rock are still only used near Round Rock; other places use their own weather history. The wishlist's local nurseries are near Round Rock; the owner can add others under Shops.

## About this plant (from 1.14.0)

Every plant page has an **About this plant** section after Identification (also in the jump row and the "On this page" menu):

- **Type of plant and classification:** for example "Evergreen tropical tree", then kingdom, order, family, genus and species.
- **Mature size:** a table of height and width in the ground and in a pot, plus growth rate and lifespan.
- **Hardiness zones (USDA):** the coldest and warmest zones it grows in outdoors all year, and a line saying **✓ Hardy here** or **▼ Not hardy here** with how much colder a usual winter is than the plant can take. Your zone comes from the weather history the app keeps for your place: the average of each winter's coldest night, which is how the USDA defines zones. For Round Rock that is about 22°F, zone 9a. The 2023 USDA map puts Round Rock on the line between 8b and 9a; the link opens the map so you can look up a ZIP code. Annual plants have no zone.
- **Native range, conservation status and invasive risk.** Conservation status is the IUCN Red List category where Claude could confirm one, and notes CITES (which only controls international trade, not growing a plant at home).
- **Flowers and fruit,** including whether the fruit is edible.
- **Dangers** to people and to pets, in a box with the Poison Control number (1-800-222-1222) and the ASPCA Animal Poison Control Center (888-426-4435).
- **Propagation,** as numbered steps.
- **Sources and further reading:** links to the pages the details came from. They open in a new tab.

If the identification is less than 85% sure, a note says the details are for the closest match. Change anything with **Edit**, under "About this plant". In the **Sources** field, put one source per line as `Title | https://link`, and it shows as a link.

## Audit log (from 1.10.0)

The **Audit log** page (in the menu bar; it used to be called Change log) lists every change to every record, newest first: edits to plant pages, plants added or archived, photos added, moved or removed, feeding and care, requests and answers, the "Still to photograph" list, settings and backups. Each change shows when, which plant (with a link), who, what changed, and the value before and after.

- **Filters** (at the top; on a phone, open **Filters** first):
  - **Search**: any words, a plant code, a name or a value, for example `hyacinth`, `P-024` or `Poor`.
  - **Plant**: one plant, or "Not about one plant" for settings, backups and the like.
  - **Who**: one person, "People" (everyone but Claude's updates) or "Claude's updates".
  - **Kind of change**: for example Photos, or Feeding, watering and care.
  - **Field**: one detail, such as Health rating or Location.
  - **From** and **To**: dates, in your time zone.
  - **Order**: newest or oldest first.
- The line under the filters says how many changes match, for example "Showing 1 to 100 of 2,253 changes". **Previous page** and **Next page** go through them 100 at a time.
- **Clear filters** shows everything again. This browser remembers the filters until you clear them.
- **Download these changes (CSV)** saves just the changes that match, for a spreadsheet.

### Debug button and the audit log console (from 1.10.0)

The **Debug** button sits next to **Display** at the bottom right of every page, and opens a window of tools for seeing what the app is doing:

- **Show the audit log console**: a small window at the bottom of the screen with the newest changes to any record. It checks for new ones every 3 seconds, so you can watch a change appear as you, someone else or an update makes it.
  - **Changes it shows before you scroll**: 3, 4 or 5. Scroll it up for older ones (it keeps the last 200), or click into it and use the arrow keys.
  - If you have scrolled up when a new change comes in, it stays where you are and shows a **new changes below** button instead of jumping.
  - **Pause** stops it checking until you press **Resume**. **Open the audit log** goes to the full page. **Close** turns it off.
- **Let screen readers announce each new change**: off to start with, so a screen reader is not interrupted every time something is saved.
- **About this browser and the app**: the version, window size, text size, layout and how many changes are logged.

These choices are remembered in that browser. The console never covers the Debug, Display or Sections buttons, and plant pages leave room for it.

## Large-print care cards (from 1.19.0)

A printable card with a plant's needs in big type, to tape to a pot or shelf or keep beside the plants indoors, and read without opening the app.

- On a plant page, press **Large-print care card**. On a group's page, **Large-print care cards** makes one card for each plant in the group. On the **Labels** page, **Print care cards for all plants** makes one for every active plant (from 1.20.0).
- **Size** (from 1.20.0):
  - **4 × 6 inch card** (the usual choice): the plant's name, code and spot, its main photo and a code to scan that opens its page. Under that is one line each for **Water** (how often to check, the same figure as the Today list), **Light**, **Temp**, **Humidity**, **Feeding** and **Careful** (pets and people). It prints on 6 × 4 inch paper, turned sideways: choose 4 × 6 inch paper (or index cards) in the print window. Most plants fit on one card; a few with long wording run onto a second.
  - **Full page (Letter):** the same, plus the plant's winter plan and notes in boxes, with **Short** or **Full** notes.
- Under **Also show**, choose whether to show the photo, the scan code and the dangers to pets and people (on to start with). The choices are remembered in this browser. **Print** opens the browser's print window, where you can pick a printer or "Save as PDF".
- The printout is always black on white and large print. Nothing on it is smaller than about 16 point (from 1.20.0, the "Printed on" line and "Scan for the full page" are as big as the notes). The name is about 21 point on a card and 30 point on a page.
- People who can only view the app can print cards too.
