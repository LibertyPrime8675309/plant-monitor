# Today, watering and care

Part of the Plant record manual. The README in the folder above has how to start, stop, update and back up the app, and the list of every manual page.

## Today page, watering and care (from 1.8.0)

The **Today** page (the page the app opens on, from 1.34.0) lists what to do today, most urgent first:

- **Water:** plants due or overdue for a check, with **Watered** and **Still moist**, and **Watered all** for a whole round. "Check tomorrow" lists the next day's plants. "No watering logged yet" has one button, **I watered all today**, to start the reminders for all of them.
  - From 1.58.0 the lists are grouped **by room and spot**, in the order of Rooms and spots, so you can water spot by spot. The cards are one run: a tile where each spot starts, with the spot's name and **Watered all N here**, then that spot's plants. Each plant is a card: its picture, its name and how late it is.
  - **Press a picture to tick the plant** (the picture gets a tick, the word "Ticked" and a heavier border). **Watered** and **Still moist** for the ticked plants are in a bar that stays at the bottom of the screen while anything is ticked, with **Untick** to clear them. A ticked semi-hydro pot is topped up and a plant kept in water gets fresh water; Still moist is for the plants in soil. The ticks stay while you open a plant's page and come back, and start empty the next day.
  - Press how late a plant is ("4 days overdue") to read the reason. Press its name to open its page.
  - **Picture size** (Medium, Large or Extra large), beside the order buttons, sets how large the pictures are. Each device remembers its own choice.
  - With three spots or more, a phone has one list, **Go to a spot**, that goes straight to a spot.
  - With a keyboard: Tab to a picture and press Space to tick it. From a ticked card, the next Tab is **Go to the buttons for the ticked plants**.
  - **Most overdue first**, beside **By room and spot**, shows one row a plant with its reason and its own two buttons, as before 1.58.0. The choice is remembered on that device.
  - To change the order of the spots, use **Move up** and **Move down** on Rooms and spots.
- **Feed:** plants due for fertilizer today, with **Log feeding** (the same schedule as the Fertilizer page). From 1.58.0 a plant counts here once a feeding has been logged for it. For plants in their feeding season with no feeding ever logged, Today asks once, under **Feeding reminders**, whether you want reminders, with those plants folded under the question. **Yes, remind me** counts each plant from that day, so it comes up when its next feeding is due. **No reminders for these** keeps Today quiet about them. The Fertilizer page says where the answer stands and has a button to change it.
- **Semi-hydro and water-only care:** a flush or a root check that is due. In the same way, for the ones never logged Today asks once, under **Flush and root-check reminders**; the Potting mixes page has the button to change the answer.
- **Needed from you:** the open requests, with links to answer them.

From 1.56.5 a part with nothing due (Turn the pots, Getting ready to come inside, Feed) is one line in the box at the top, "Nothing due today: …", instead of a part of its own. From 1.58.0 the first sentence names only what there is (no "0 to feed"), and the **Cold night** button counts the plants of the next cold night that are not marked as covered yet. **What's new** shows in full the first time after an update; on later visits it is one line you can open, until you press **Got it**. **Going away? Make a plant-sitter sheet** is at the end of the page.

Every plant page has **quick care buttons** straight under the plant's name (from 1.58.0; they were further down, under its label), big enough to use on a phone in the garden after scanning the plant's label: **Watered today**, **Checked: still moist**, **Log feeding**, **Add photos** (from the phone's camera or its photos) and **Log other care** (repotted, pruned, treated for pests, or a note, with a date). The line beside or above them is short from 1.58.0 ("Water: 4 days overdue. Watered Nov 2."): how late the plant is and what it last had. Under the buttons, **All plants**, **Previous Plant**, **Next Plant**, their filters and the layout switch share one row. What other parts of the app add about a plant's care (repotting, turning the pot, pests) is in a box of its own at the top of the details. The plant's **Water and soil** section explains the reminder and has its **care log**, with a **Remove** button on each entry.

How the reminders work:

1. The starting gap comes from how dry the plant likes to be: 14 days for plants that dry out completely (cacti, aloes), 10 for plants that dry out between waterings, 7 when the top of the mix should dry, 5 for evenly moist, and 4 for constantly moist (ferns, calatheas).
2. Hot weather (highs of 85°F or more) shortens it; cool weather and being indoors lengthen it.
3. Rain of 0.25 in or more on one day counts as a watering, but only for plants whose Location is Outdoors (not the covered porch).
4. **Checked: still moist** moves the next check a third of the gap later.
5. To set the gap yourself, fill in **Check for water every (days)** on the plant's Edit page.

**Once a day** (from 1.21.0): after you press **Watered today** on a plant page, the button changes to **✓ Watered today** and is switched off until tomorrow, so a second press can't log it twice. Undo, or Remove in the care log, switches it back on. The app never logs two waterings for the same plant on the same day.

**Water all** (from 1.21.0): on the Plants page, **Water all … shown** marks every plant the filters show as watered today, after asking. Plants already watered today are skipped, and the message has **Undo**. For example, choose Location: Covered porch, then **Water all**.

From 1.58.0, with more than one home, Water all waters the plants at **one home**: the one chosen in the **Home** filter, or, with "All homes", the home you are using (the Location button). The button names it ("Water all 28 shown at Round Rock, TX"), and the note under it says how many plants at other homes it leaves out. A home whose care is **Done outside the app** (see "A home is a site" below) is never watered in bulk: with that home chosen in the filter, the button is off and says why. **Log care for all of them** on a group works the same way: plants at other homes start unticked, and you can tick them. Each care entry is dated by the day where the plant lives, so a Nevada City plant logged late on a Texas evening keeps its own date.

## Today as the home page, the shopping list, speaking a note, room labels and summer heat (from 1.34.0)

### Today is the page the app opens on

The app now opens on **Today**: one line says what needs you (a cold night, plants to water and feed, Shopping alerts, my requests), with a button to jump to each part. The cold-night warning is a section of the page here, not a banner, so the sections menu lists it. **Quiet today** at the bottom says what is not due: pest rounds, when the stores were last checked, the last backup, and whether there are problems to look at. **All plants** is one click away in the Plants section (its address is now `#/plants`; the old `#/today` address still opens Today). The `H` shortcut still goes to the Plants page.

### The shopping list for a store visit

On **Shopping**, press **Shopping list for a store visit** (`#/shopping/list`). Choose a store: the items it carries (from what you set under Stores, and listings found there) come first with what you are watching for; the rest are under "Not carried here, as far as the app knows". Add anything else you need (twine, a trowel), tick what you bought, and press **Done shopping**: the ticked items are marked **got it** on Shopping and the extra lines are crossed off. **Large print** makes the list bigger for the store; **Print** prints it. Ticks are kept on this device until you are done; the extra lines follow your sign-in like the other settings.

### Speak a note

Every box that takes several lines of text (notes, change notes, answers) has a **Speak** button that appears when you are in the box. Press it and say what you want. From 1.44.0 it records until you press it again, pause for about 3 seconds, or reach a minute; it then says **Working out what you said…** and adds the words after what is already there, as a new sentence. Your voice goes to the speech service on your own computer (the same one as Search by voice, below), not to Google or Microsoft, so it works in Brave and Firefox too. If the speech service is still getting ready, Speak says so.

### Room, area and shelf labels

The **Labels** page now also has a label for every room or area and every spot under **Rooms and spots**. Stick one on the shelf or by the door: scanning it opens the Plants page showing just the plants that live there, with a **Show every place** button to clear it.

### Summer heat next to winter cold

The **Weather** page has a **Your climate** section: the USDA hardiness zone (how cold a usual winter gets) and, from the same weather history, the **AHS heat zone**: how many days a usual year go above 86°F (zone 1 has less than one, zone 12 more than 210), the hottest day, which months the hot days fall in, and a table of each year's count. Plant pages say the heat zone next to the winter zone under "About this plant". It appears once the app has 3 whole years of weather for the place.

## Fertilizer calendar and log

Open **Fertilizer** (top menu) for the whole collection, or look at the **Nutrients** section of any plant page.

- **Should I feed today?** Every plant has a feeding season (first and last month it is fed) and a number of days between feedings, set by plant type. Each day is then one of: **Time to fertilize**, **Hold off** (a cold night is forecast at or below that plant's damage temperature, or its health is Poor or Critical), **Fed recently** (with the next date), **Resting** (out of season: do not fertilize), or **No feeding season set**. The Fertilizer page groups all plants this way, and each plant page shows the verdict for today and for any date you pick.
- **Calendar:** shaded days are in the plant's feeding season, hatched days are its resting season. "Fed" marks feedings you logged and "Due" the next suggested feeding. On the Fertilizer page the calendar covers all plants (how many were fed, how many are due). Click a day, or move with the arrow keys (PageUp and PageDown change month), for the details. "Show as a list" gives a plain list of days; with large text or a narrow screen it switches to the list by itself.
- **Log a feeding:** press **Log fertilizer** (or **Log a feeding for this plant**). Choose the date, the plants (one, or many at once: "All that are due", "All in season"), the fertilizer name, its type, and the N-P-K numbers printed on the package, then the amount and how much water it was mixed into (for example 1 tsp in 1 gal) and how it was applied. The form shows an estimate of how strong the mix is: parts per million of nitrogen, phosphate and potash, and the N : P : K ratio. Spoon measures are converted at 4 g per teaspoon and 12 g per tablespoon for dry products and 4.9 ml and 14.8 ml for liquids, so treat the numbers as estimates. Most potted plants do well at 50 to 200 ppm nitrogen. Logging in a resting season asks you to confirm.
- **Remembered fertilizers:** names you have used appear in a list and fill in the rest of the form next time. Entries can be changed or removed; the change log records each one.
- **What each plant needs (from 1.11.0):** every plant on the Fertilizer page has a line under its code and "last fed" line, for example "Needs N-P-K ratio 2-7-7, at half strength". The same box, **What to feed it**, is in each plant page's Nutrients section.
  - **Best match you have:** the fertilizer of yours whose N-P-K ratio is closest to what the plant needs, with its numbers and how close it is: **✔ Matches**, **✔ Close**, **▲ Usable** or **■ Not a good match** (it then says what to look for). It also says what is different, for example "It has more nitrogen (N) and less potash (K) than this plant needs".
  - **How much:** for a liquid or powder, how much to mix into how much water, for example "Mix ⅝ tsp into 1 gallon of water (0.8 ml per liter)", and about how many ppm of nitrogen that gives. Full strength aims for about 150 ppm of the strongest of N, P and K, half strength 75 and a quarter 40, which is a usual rate for plants in pots. If the label says to use less, use the label. Granular, slow-release, spikes and organic solids go on or into the mix, so it says what share of the label amount to use.
  - **Your fertilizers** (Fertilizer page): every fertilizer you have logged, plus any you add with **Add a fertilizer you have** (name, type and the N-P-K numbers from the package), even before you use it. **Change** corrects one; **Remove** takes off one you added.
  - **Log** next to a plant starts the feeding form with its best match and the amount already filled in.
  - Each plant's ratio and strength (None needed, Quarter strength, Quarter to half strength, Half strength or Full strength) are on its Edit page, under Nutrients. Claude filled them in for every plant from its fertilizer note (upgrade batch `batchA2`).
- **Change a plant's season:** Edit this page, Nutrients group: "Feed from month", "Feed through month" (a season like October to April is fine) and "Feed every (days)". The starting values are Claude's guesses from the plant type.

## Your plant calendar (from 1.15.0)

Feeding days and cold nights can go into Google, Outlook, Samsung or Apple calendars, with reminders. Open **Today**, **Fertilizer** or the **Cold-night checklist**, go to **Add to your calendar** at the bottom, and press **Set up your calendar**.

- **Choices** (saved as you make them):
  - feeding days, cold nights and close calls
  - one feeding day a week on the day you choose, or each day a plant is due. A plant is never moved earlier than it is due.
  - how far ahead (1 to 12 months)
  - your own reminder times: one on feeding days, one on the day before a cold night
- **Subscribe** with the calendar link, so the calendar updates by itself. The link works without your password. Keep it private; **Make a new link** stops the old one working.
- Google Calendar uses its own reminder settings for subscribed calendars: in Google Calendar's Settings, choose Plant record under "Other calendars" and set its notifications.
- **Save calendar file** adds the events once instead, without updates.

### Reaching the calendar from the internet with Tailscale Funnel

Google Calendar, Outlook.com and iCloud fetch the link from the internet. Tailscale Funnel lets them reach the calendar link only (the `/cal/` path on port 8443), not the rest of Plant record. From 1.49.0 the plant-sitter sheet by link uses the same door for its `/share` path (see "Share the sheet by link"). Anything you share in your tailnet on port 443 with Tailscale Serve stays private.

From 1.58.0 the app checks this itself as well. Tailscale marks every request that comes in from the internet through Funnel, and Plant record answers such a request only if it is the calendar link or a live plant-sitter link. Everything else gets "Not found", whatever the visitor sends with it. (Before 1.58.0, the address the phone's share sheet used sat under `/share` too, so a visitor who knew it could add pictures to your unassigned photos without signing in. If you run an older version with the `/share` Funnel on, turn that Funnel off until you update: the command is under "Share the sheet by link".)

1. Turn on Funnel for the calendar, on the PC that runs Plant record. If Tailscale says Funnel or HTTPS is not turned on for your tailnet, open the link it shows, turn it on, and run the command again.

   Windows (cmd.exe):

   ```
   tailscale funnel --bg --https=8443 --set-path=/cal http://127.0.0.1:8080/cal
   ```

   Windows (PowerShell):

   ```
   tailscale funnel --bg --https=8443 --set-path=/cal http://127.0.0.1:8080/cal
   ```

   macOS / Linux (bash):

   ```
   tailscale funnel --bg --https=8443 --set-path=/cal http://127.0.0.1:8080/cal
   ```

   If Windows says `tailscale` is not recognized, use the full path: `"C:\Program Files\Tailscale\tailscale.exe"` in cmd.exe, or `& "C:\Program Files\Tailscale\tailscale.exe"` in PowerShell, followed by the same words from `funnel` on.

2. See the address it made. The command is the same in cmd.exe, PowerShell and bash:

   ```
   tailscale funnel status
   ```

   It looks like `https://your-pc.tail1234.ts.net:8443`. Type it into **Internet address of this PC** in the calendar window and press **Save address**. The calendar link then starts with it.
3. Check it: on your phone, turn Wi-Fi off and open the calendar link in the browser. It should show or download a calendar file.
4. Subscribe with that link. The window's "How to subscribe in each calendar" has the steps.

Funnel keeps running after a restart. To turn it off (the same in cmd.exe, PowerShell and bash):

```
tailscale funnel --https=8443 --set-path=/cal off
```

## Undo right after a care button (from 1.19.0)

After you press **Watered** or **Still moist** (on the Today page or a plant page), **Watered all**, or save **Log other care**, the message at the bottom says what was saved and has **Undo** and **Close** buttons. It stays for 30 seconds, and says how long is left. The countdown pauses while the pointer or the keyboard focus is on the message. With a keyboard, press **U** while it shows (Display settings can turn keyboard shortcuts off).

Undo removes only the entries that press made, so the rest of the care log is untouched. For "Watered all" it removes all of them and says how many. If someone else already removed the entry, it says "Nothing to undo". The change log records it as "Undone right after it was logged". To remove an older entry, use the care log on the plant's page.

## Repotting (from 1.50.0)

A plant in a pot slowly fills it with roots and wears out its soil. Most want a pot one size bigger, or fresh soil, every one to three years, best done in spring (March to May) as they start to grow. **Today → Repotting** turns the "Repotted" entries in your care logs into a plan.

- **How often** comes from each plant's growth rate (About this plant): fast growers every year, moderately fast every 18 months, moderate every 2 years, slow growers every 3 years; 2 years when the growth rate is empty. **Change** on any plant sets 12, 18, 24 or 36 months, or no reminders. Plants that grow in water are left out.
- **The page:** one line saying how many plants are due and whether it is repotting season; **Due this spring** (or **Due in spring 2027**, out of season) with **Repotted today** and **Change** for each; **Not recorded yet**, with **When was it repotted?** for each plant and **Save for all** to give the whole list the same rough year; **Later**; **Signs a plant cannot wait for spring**, with short steps for when you repot; and **Left out**.
- **When was it repotted?** takes Today, this year, last year, two years ago, three or more years ago, or an exact date. A year is saved as April 15 of that year with the note "Date estimated", so you can tell it was a guess. A plant due by the end of August goes in that year's spring; one due from September on waits for the next.
- **On a plant's page:** a line under the care buttons ("Repotting: next due in spring 2028. Last repotted …") with **Change**.
- **On Today:** a **Repot this spring** section and a **Repot (N)** jump button from four weeks before the season until the end of May; the rest of the year Today says nothing about it.
- Each repotting is a "Repotted" entry in the care log, with the usual **Undo**. The plan follows the home you are looking at. The season is spring in the northern hemisphere for now; a home with no winter (1.48.0) still gets the March-to-May words.

## Turn the pots (from 1.44.0)

A plant by a window grows toward the light and leans. A quarter turn every week or two, always the same way round, keeps it straight and full. **Care → Turn the pots** reminds you, the way watering reminders do.

- **Remind me to turn each pot every** 7, 10, 14 (the usual), 21 or 30 days.
- **Due today**, with a **Turned** button for each plant and **Turned all**; **Not turned yet** (folded), with **I turned all … today**; **Coming up**; and **Left out**, with the reason and **Remind me**.
- **Which plants:** those Indoors or on the Covered porch. Left out: plants out in the open, in the garage or shed, and plants under a grow light that shines down from above. A plant just brought inside starts under Not turned yet, not as due.
- **On Today:** a **Turn the pots** section and a **Turn (2)** jump button.
- **On a plant's page:** **Turned today** next to **Watered today**, with a line saying when it is next due. **Turned** saves "Turned the pot" in the care log, with the usual Undo message.

## Health walk-through (from 1.44.0)

Go round your plants one at a time, on the phone in the garden or at the computer, and say how each one looks today. **Today → Health walk-through** (and a line on Today saying how many are due).

- **Choose** which plants (the due ones or all), where, which group, and the order (longest since looked over, worst health first, or by code).
- **One plant at a time:** its photo (from 1.47.0, every photo of the plant is under it as a row of small ones; press one to see it big), where it is, its rating now and when it was last looked over. **Take a photo** adds a photo to the plant. **How does it look now?** has four big buttons (Good, Fair, Poor, Critical), with the current one already chosen, and a box for a short note. **Looks the same: save and go on**, or **Save "Poor" and go on**; **Skip this plant**; **Back**; **Stop and see what you've done**.
- **What is saved:** a "Looked over" entry in the care log; a new rating on the plant (in its change log and timeline); and your note at the end of the plant's Health summary, with the date.
- **How often plants are due:** every 14 days, or every 7 for plants in Poor or Critical health (both can be changed at the bottom of the page). A group can have its own number (on the group's page, **Days between looks for this group**), and it wins even for Poor or Critical plants, so cacti can be looked at once a month. A plant in several such groups goes by the shortest.
- With no connection, saves and photos wait on the device and are sent when the connection is back.
- On a narrow window (an iPad held upright with large text, a phone) the card is one column: the photo, then the questions (1.47.0).
- On an iPhone or iPad, a tap made while the page is still gliding after a scroll only stops the glide; that is how iOS works, and the second tap is the one that presses the button.

## Plant-sitter sheet (from 1.43.0)

A large-print plan to print for whoever looks after your plants while you are away.

- **Where:** on **Today**, **Going away? Make a plant-sitter sheet**; on a group's page, **Plant-sitter sheet for this group**.
- **Choices above the sheet** (remembered in that browser): **First day** and **Last day** (up to 6 weeks), **Which plants** (all, or one of your groups), **Printing** (**Each day on its own page**, off to start with; **A photo of each plant beside its name**, on to start with, from 1.47.0), and a **Note for the sitter** printed at the top.
- **Before you go** (on screen only): the plants due before your first day away, or with no watering logged. The sheet assumes you water these the day before you leave.
- **On the sheet:** the dates, your note and four short instructions; **Cold nights in the forecast**, with each plant outside to bring in or cover, the low each night and the temperature that harms or kills it; **Day by day**, each day's high and low and a tick box for every plant to check, in walking order (outdoors, then the porch, indoors and the garage); and **The plants**, one short entry each: where it is, how often to check it and the first line of its watering notes.
- Each plant's line on a day carries a tick box, its photo, its name and code, where it is, and the first sentence of its watering notes, so the sitter can find the pot and judge it without looking anything up (1.47.0; the separate plant list at the end is gone). Temperatures and rain are in your units.
- It uses the same watering reminders as Today (each plant's "check every N days", the recent weather and your care log), carried forward over the days you are away.
- **Print** opens the browser's print window; choose "Save as PDF" there to email it. The printout is always black on white, about 15.5 point and up. People who can only view the app can make it too.
- From the app saved to an iPhone or iPad home screen, printing is not possible (iOS gives such apps no print window), so the button there reads **Open in the browser to print** and opens the sheet in Safari (1.47.0).

### Share the sheet by link (from 1.49.0)

Instead of a printout, the sitter can open the sheet on their own phone and tick the boxes as they go. They need no Tailscale and no sign-in: the link itself is the key (a long random code, like the calendar link).

- Under the choices, **Share the sheet by link** (editors and the owner; people who can only view do not see it). **Make a link** makes one for the days, plants and note chosen above. Press **Copy the link** and send it however you like (a text message, say); **Open it** shows you what the sitter will see.
- The sitter's page has **Smaller text**, **Larger text**, **Dark**, **High contrast** and **Print** buttons, large print to start with, and a real check box on every line. Each tick is saved at once and shows on your own sheet (filled in, with "Ticked by the sitter" for a screen reader) and in the link's row: how many boxes are ticked and when the page was last opened.
- The link stops working the day after your last day away. **Take the link down** stops it at once; whoever opens it then sees "This sheet has been taken down" in plain words. The ticks are kept.
- Nothing else is reachable through a link: only that sheet, its photos and its own page files. A link for one group shows only that group's plants, and a link made while another place is chosen shows that place's plants. From 1.58.0 the app also refuses everything that comes in from the internet except these links and the calendar link (see "Reaching the calendar from the internet with Tailscale Funnel").
- **From outside your home network** the link needs Tailscale Funnel for the `/share` path, exactly like the calendar (see "Reaching the calendar from the internet with Tailscale Funnel" above). Until the public address is saved in the calendar window, the page says so and the link works at home only. Run this once on the PC that runs Plant record:

  Windows (cmd.exe):

  ```
  tailscale funnel --bg --https=8443 --set-path=/share http://127.0.0.1:8080/share
  ```

  Windows (PowerShell):

  ```
  tailscale funnel --bg --https=8443 --set-path=/share http://127.0.0.1:8080/share
  ```

  macOS / Linux (bash):

  ```
  tailscale funnel --bg --https=8443 --set-path=/share http://127.0.0.1:8080/share
  ```

  `tailscale funnel status` should then list both `/cal` and `/share`. To stop sharing sheets from the internet: `tailscale funnel --https=8443 --set-path=/share off` (the same in all three shells).

## What is in each pot (from 1.56.0)

**Potting mixes** holds what goes into your pots. Open it from **Care → Pots and trays** (the line under the title), or from **Potting mixes** in any plant's What it is in. It has no link of its own in the top bar, so the Care row stays on one line; Search finds it too.

- **Recipes.** **New recipe** takes a name and its parts by volume, the way you scoop them: 3 parts orchid bark, 2 parts perlite, 1 part coir (halves are fine). Each part can have a grade (orchid bark small, medium or large). An additive such as slow-release fertilizer asks **How much** ("1 teaspoon a gallon") instead of parts. Each recipe shows the share of each part and an **estimate** of the whole mix: how much water it holds, how much air it lets in, and when it will want freshening (set by the part that breaks down first). It is an estimate because fine bits fill the gaps between coarse ones. Once three plants in a recipe have six or more waterings logged, the recipe says how many days they go between waterings.
- **Amendments.** Grouped as parts of a mix, semi-hydro media and additives, each with its grades and how it behaves in words (holds water, lets in air, breaks down in, feeds the plant, pH, weight). The numbers behind the words are a rough guide for comparing them, not measurements: **Change** any that your pots disagree with, or **Add an amendment**.
- **Semi-hydro and water-only care.** How often the app reminds you to top up, flush, change the water and check the roots, in days (weekly, and the root check every 30 days, to start).

On each plant's page, **What it is in** (after Soil) shows:

- **How it grows**: soil mix, semi-hydro or water only. **What holds its water**: it drains freely, a tray under it, a catch pot, or the pot itself (no holes). **Mix its species wants**: fast-draining, balanced or moisture-holding; "Same as its species" uses what is known about the species. Each saves as soon as you choose.
- **In it now**: the mix, any top or bottom layer, and the estimate. **What is it in now?** records it for a plant you have not repotted lately (choose a recipe to fill in its parts, then change any that differ). **Repotted: record the new mix** does the same and logs Repotted on that day. **Save as a recipe** makes a recipe from a pot's mix. Earlier mixes are folded under **Earlier**.
- For a semi-hydro pot, **Topping up** and **Flushing**; for a water-only plant, **Fresh water** and **Checking the roots**: when each was last done and when it is next due, with a button to log it. A flush counts as a top-up too.
- If the mix does not suit what its species wants (a wet mix for a species that wants fast drainage, say), a note says so and what would help.

Semi-hydro and water-only plants say **Top up** or **Change the water** instead of Water in Today's Water list, on their watering button, on the plant-sitter sheet and in the morning notification. Today also lists the pots due a flush or a root check. The repotting plan brings a pot forward when its mix is due for freshening.

## Shopping, stores, and quicker pages (from 1.30.0)

**Shopping** (under Discover) is where the stores are checked: for the plants on your wishlist, and for garden supplies.

- **Show** picks one kind: Wishlist plants, Pots and trays, Potting mixes, Amendments, Fertilizers, Pest control, Frost cloth and covers, Grow lights and timers, Tools and labels. On a phone it is a dropdown.
- **Stores near** picks a home: online stores count for every home, and stores you can visit count only for the home they are near.
- **Add something to watch** adds a supply: what it is, its kind, what to search the stores for, and alerts.
- **Cheapest now** shows the price per quart (potting mixes and amendments), per pound (fertilizers) or per square foot (frost cloth) when a listing says its size, so an 8 qt bag and a 2 cu ft bag can be compared. A price alert can be for the whole listing or per unit.
- **Stores near you that carry it** lists the stores you can visit for that kind, with their phone numbers.
- Buttons elsewhere start watching for you: **Watch for more on Shopping** on each pot or tray, **Watch for it on Shopping** for each N-P-K ratio on the Fertilizer page, and **Watch the stores for frost cloth** on the cold-night checklist.
- The Wishlist page keeps the plants you want, and points to Shopping for the stores, prices and alerts.

**Stores** (the button on Shopping, or Settings, Stores and keys) lists every store: near Round Rock, near Nevada City, and online. Choose one to open its page:

- its address with a map link and the distance from home, its phone numbers (tap to call on a phone), its hours, email and website, and where those details came from;
- what it carries, how it is checked, and its last check;
- **What you are watching that it has**, with each price, the price before, and the price per unit;
- **What they had**: notes after you call or visit, which everyone sees.

**Edit details** changes the address, phone, hours, what it carries and the home it is near. **Look them up on OpenStreetMap** fills in what is still empty (hours, phone, website and its map position). The owner turns stores on and off, adds stores, chooses how often they are checked, and keeps the eBay and Etsy keys, all at the bottom of the Stores page.

The details for the stores near Round Rock and six stores near Nevada City (Peaceful Valley, B&C Ace, Weiss Brothers, Prospector's, Nevada City Blooms and Double Dogwood) came from their own websites in November 2026. Hours change, so call before a long drive.

**Quicker pages:**

- The page you choose shows at once: its name and "Loading" if it takes more than a moment.
- A page you have opened before shows what this device had from last time straight away, then quietly checks for anything newer and redraws if something changed (not while you are typing on it).
- Pointing at a link, or moving to it with the keyboard, starts loading that page, and once a page is open the other pages in its section are fetched in the background.
- Answers from the plant server are sent squeezed (about five times smaller).
- **Settings, Debug, Page timings** shows how long each of the last pages took: waiting for the server, drawing the page, and the slowest answers. If pages are slow on your computer, these numbers show where the time goes.

## Jobs (from 1.32.0)

**Settings, Jobs** shows what the app is doing in the background: what is running now (with how far it has got), what runs on a schedule (the hourly weather update, the store check, the automatic backup) with when each is next due and when it last ran, and what has finished since the app started, with how long each took. The owner has a **Run now** button for the weather update, the store check and a backup. The window keeps itself up to date while it is open.
