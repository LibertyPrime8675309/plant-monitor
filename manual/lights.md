# Grow lights

Part of the Plant record manual. The README in the folder above has how to start, stop, update and back up the app, and the list of every manual page.

## Grow lights (from 1.13.0)

The **Grow lights** page (in the top menu) holds your grow lights, the spots they light indoors, and how much light each plant gets there. Your 11 lights arrive with the update, from the photos and listings you saved in `Plants\Grow Lights`. Each has a photo, how many you have, its timer and brightness steps, and the maker's light figures. Where the maker gives none, Claude's estimates are used and marked.

How much light a plant gets is its **daily light (DLI)**, in mol/m² a day. It is the light at its leaves (PAR, in µmol/m²/s) times the hours the light is on. 100 PAR for 12 hours is about 4.3. Each plant page lists the range it wants, under Sunlight.

- **Light spots.** A spot is one of your lights over some plants: how many of that light, how far it is from the top leaves, hours a day and brightness. Press **Set up a spot**. While you choose, the window shows the light at the leaves and says for every plant whether that is too dim, a bit dim, good, a bit bright or too bright. The setting is shown in words and with a symbol, not by colour alone.
- **Suggested layout.** For plants that live inside or are coming in and are not in a spot yet. Plants that need the most light are placed first. Each goes under the smallest of your lights that can give it enough, sharing a light with plants whose needs overlap, while there is room under it. Pot sizes count, if they are set. **Set up this spot** opens the suggestion so you can rename it (for example "Living room shelf") or change anything first.
- **The light spot window (from 1.41.0).**
  - **Light** is A to Z, grow lights first and the disk light under Room lights. Each light says its type, watts, its most light (PAR, at its closest measured distance) and how many are free.
  - Under it is a card on the chosen light. It gives the type, power and colour, brightness steps, and how many are free. It gives its light at the leaves from closest to farthest (PAR). The daily light that makes, on 12 hours and from 8 to 16 hours. The figures stay within the distances the maker (or Claude) measured; a light measured at one distance only says so.
  - **Best setting for the ticked plants** picks the distance, hours and brightness that put the most ticked plants in their range, and says how many fit.
    - Its light may be drawn on the layout of its room or shelf. Then the plants drawn there get their own light from the drawing at each setting it tries. The distance is only for the plants that are not drawn.
    - The hours and brightness are the layout's to set. Best setting says what is best, and **Set ... on the layout** sets them there with one press. The spot follows.
  - **Plants in this spot** is one plant a row. Each row has its photo, its name (tick the box or the name), its light needs, whether it lives inside or is coming in, and the spot it is in now. **Open P-0xx** opens its page in a new tab, so the window stays open. The tag on the right says how this light, at this setting, suits it, and changes as you change the setting.
  - Above the list:
    - **Search plants**
    - **Show**: all, fits this setting, fits or nearly fits, not in a spot yet, ticked, lives inside, coming inside
    - **Sort**: name, code, most light needed first, best fit first
    - **Hide plants already in another spot**: on unless you turn it off, and this device remembers which. Plants ticked for this spot always show.

    It says how many are showing, how many are ticked, and how many in other spots are hidden.
  - **How many of this light (from 1.56.1).** Over plants that fit under fewer of them, the lights' light adds up: two bulbs over one small group give about twice the light at the leaves. Over plants that need the room, they sit side by side and light more area at the strength of one; in between, they partly overlap. The window says which. For a light with no area figures from its maker, the lights are taken to shine on the same plants.
  - **Level** lists the levels of the chosen place: a table or a one-level shelf has only its one level.
  - Under the light at the leaves, how much room the ticked pots take against what the light covers, and for a plant that does not fit, one of your other spots that would suit it.
- **Add plants (from 1.41.0)** on each spot opens it at the search box, showing the plants not in a spot yet. A plant that does not suit its spot says which of your spots would.
- **The top of the page (from 1.42.0)** stays in view as you scroll. It has the title, the short description and a table. The table shows **Inside**, **Coming in**, **Assigned light spot**, **No assigned light spot**, and the **7-day mol/m² average** outdoors in the open. **Hide the summary** folds the description and table, leaving the title; the app remembers which you chose. On a phone it scrolls with the page.
- **Add a light** sits by the Your lights title and **Set up a spot** by the Your light spots title (1.42.0; the "This winter" box is gone, its numbers are in the table).
- **Your light spots (from 1.42.0)** fold one by one. Shut, each still shows its name, where it is, its mol/m² per day and how many plants (and how many are not in their range). Open it for the light, the setting and its plants. The plants are two to a row on a wide screen, or one on a phone. Each has its code and its range per day ("6–12 mol/m² per day") on lines of their own. **Open every spot** and **Close every spot** are above them; the app remembers which you left open.
- **Your lights, the suggested spots, the rooms and the list of plants with no light left fold too (1.58.0).** Shut, a light shows how many you have, what kind it is and its most light. A suggested spot shows its light, its daily light and how many plants. A room shows how many shelves and light spots it has. Each list has **Open every** and **Close every** buttons. What you open stays open on that device.
- **Rooms and shelves (from 1.42.0):** each room's title has **New Shelf**, **Rename** and **Remove room**. Each shelf has its own **Rename** and **Remove**, and removing a shelf (even the last one) leaves the room. **New Room** at the bottom, and New Shelf, open the **Build-A-Room** window. After a change the page stays where you were.
- **Set up all suggested spots (from 1.41.0)** sets up the whole suggested layout in one go, named "Bright light 1" and so on. Rename, move or change each one afterwards.
- **No light left for these** lists the plants your lights cannot cover, with the reason.
- **Easing them in.** Under a spot, "Easing them in from outdoor light" gives a first and second week brighter and longer than the spot's own setting. So plants used to the sun do not drop their leaves all at once.
- **Timers.** Each spot says whether to use the light's own timer or a plug-in outlet timer. Some lights forget their timer after a power cut.
- **Your lights.** Press **Change this light** to note where it is (for a bulb, the lamp or socket it screws into), correct how many you have, or fix its figures. **Add a light** adds one you buy later. Type its figures as distance and PAR, for example "12 in 719, 24 in 234".
- **Plant pages** show the plant's spot, or what the suggested layout gives it, under Sunlight. Some plants live inside or are coming in, and are not in a spot yet. Their pages have **Set up the suggested spot**, **Add it to one of your spots** and **Set up a new spot for it**. Each spot says how its light suits the plant.
- **Rooms and shelves (from 1.13.1).** The rooms, shelves and tables where plants go inside. Yours are listed already: the Downstairs Living Room (Tall Black Shelf, Tall Brown Shelf, Short Brown Shelf, Large Brown Hutch, Side Table), My Bedroom (Shelves), the Garage and the Upstairs Living Room. Press **Add a room or shelf** to add more, for example each new bedroom shelf, and choose one under **Where** when you set up a light spot.
- **Manufacturer model (from 1.13.1).** Each light has a field for the model number on its box or label. Fill it in with **Change this light**. From 1.27.2, the Barrina standing light, the SANSI 80 W, 30 W and 10 W bulbs and the SANSI pot clip lights have theirs filled in from your label photos.

Changes to lights, spots, rooms and shelves appear in the audit log under "Grow lights". People who can only view see everything but cannot change it.

## Lights that fit the room (from 1.56.0)

Every grow light holds itself in the room in its own way: a bulb screws into a lamp, a clamp or a socket on a cord. The tripod stands on the floor and cannot point straight down. The 2 ft standing light lights sideways. Clamp lights need a horizontal edge. Strips screw under a shelf, which a one-level table does not have. The Grow lights page now checks that before it counts the light.

- **How it holds.** Each light's card under **Your lights** says how it holds ("Screws under a shelf or other surface at least 24 in long, pointing down"). Your lights came filled in from their listings. **How it holds** changes it:
    - the kind: screws into a bulb socket, stands on the floor, stands on a shelf or table, clamps to an edge, screws under a shelf, hangs from something above, or a room light
    - which way it points
    - the numbers that kind has: the base across, its height, the thickest edge a clamp grips, the arm's reach, or the length a strip needs

  Leave a number empty when you do not know it.
- **Measurements and photos.** Under **Rooms and shelves**, each room and each shelf or table has **Measurements and photos**:
    - how many levels, and the clear height between them
    - the width and depth of a level, and what is above the top level
    - free surface beside the plants, and free floor beside it
    - an edge to clamp to and how thick, and an outlet within reach

  Fill in what you know; the rest can wait. **Add photos** takes photos of the shelf (on a phone, the camera). The first is the main photo. It is shown beside the shelf's name, on its light spots' setup cards, and on the plant-sitter sheet ("Where the plants are"). Your measurements of November 10 are filled in: the tall brown shelf, short brown shelf, tall black shelf, hutch and side table, and the pallet shelf if it is a spot of its own. Sometimes a shelf's levels differ. Then **Clear height of each level, from the bottom** takes one height for each level with another above it, bottom first ("23, 13, 27" for the tall brown shelf). Leave it empty when they are all the same. Every spot on **Plants → Rooms and spots** has the same **Measurements and photos** button, outside spots too.
- **A plant's height.** Each plant has **Height now, with its pot**: from the surface the pot stands on to the top of the plant. It is on its page and its edit page. The **Health walk-through** asks it as "Taller than last time?".
- **Does it fit?** Each light spot now opens with **Fits**, **Does not fit** or **Not checked yet**, then a sentence for each thing found: "The Side Table has nothing above it. So a strip has nowhere to be fixed". "The Tall Brown Shelf's levels are 16 in wide. The SANSI 2 ft T8 strip needs 24 in. The Barrina 1 ft T5 strips fit". A plant **too tall for the level**. A sideways light **shading** the plants behind a tall one, with the order to put them in. A light that **cannot point straight down**. When a measurement is missing it says which one to fill in, rather than guessing. The same check runs in **Set up a spot** and **Change this spot**, as you choose the place and the **Level**. On a shelf with several levels, choose the top, or a level counted from the bottom, with its clear height. For a bulb, choose **What the bulb screws into** too. "It would suit … better" never points a plant at a spot it cannot go.
- **The setup card.** **Setup card** on a spot opens a page to print or keep on the phone. It has where, the light and how it holds, how far from the leaves, the hours, the fit, and the plants. For a sideways light, the shortest plant comes first, nearest the light.
- **Set up and checked.** Once the light is up and the plants are under it, press **Set up and checked** (with a note of what you found, if anything). Changing the spot's light, place, level, distance or plants takes the tick off by itself ("Changed since it was checked"). The hours and brightness do not. Today lists the spots with plants that are not set up and checked yet.

## Compare lights (from 1.56.0)

**Compare lights** puts your grow lights and the ones you are thinking of buying side by side. Open it with **Compare lights** at the top of Your lights on **Care → Grow lights**, or find it with Search.

- **One distance for all.** Makers measure at different distances (one at 8 in, another at 12 in). So choose **Compare at** (6, 12, 18 or 24 in, in your units) and **Hours a day**. Every light's light (PAR), the area it lights and its daily light are worked out at that distance. A light whose maker did not measure that far, or that close, says "Beyond its chart" instead of a stretched guess.
- **Worked-out columns**: light per watt and price per light, both marked rough (they treat the whole area as getting the centre's light). **Numbers from** says whether the figures are the maker's, Claude's estimate, or doubtful (a listing that contradicts itself, like the 4-head gooseneck and the 30 W bulb). So a guess is never quietly at the top.
- **Search** by name, brand or kind. **Sort** with **Sort by** and **Order**, or with the column headings (they are buttons; press again to turn the order round). The sentence above the table says how it is sorted. Lights with a value not known always go last.
- **Filters** (open the Filters box): owned or considering, which way it points, needs a socket, how it holds, colour range, at least so much PAR, can be dimmed, timer repeats every day. Each filter that is on shows as a button above the table; press it to remove that filter, or **Clear all filters**.
- **Columns** chooses what the table shows; your choice follows you to any device you sign in on.
- **Pick** two to four lights to see them side by side, one row for each thing.
- On a phone, or with large text, each light is a card of label and value, so the page never scrolls sideways.

Press a light's name for everything about it, and:

- **Try it in a spot**: choose one of your light spots. For each plant there, see how it does now, and how it would do with this light at the spot's distance, hours and brightness. It also says whether the light fits there.
- **On a layout (1.58.0).** The list under **Where** also has each light drawn on one of your layouts. Choose one to see each plant drawn there now and with this light in its place. Each plant gets its own light from where it stands, with its daily light.
  - The new light is drawn the same size and in the same place as the one it replaces.
  - A light spot whose light is drawn on its layout does the same for its plants that are drawn there. The others get the spot's one setting, as before.
- **Add a light you are considering** (top of the page) takes what a listing gives. That is the name, brand, link, price (with the date, since prices move), watts, and the PAR chart (two or more distances). It also takes which way it points, colour, CRI, brightness steps and timer. It stays off Grow lights until you press **Bought it**, which asks how many and when, and moves it to Your lights with everything you entered. So there is nothing to type again.
- **Change the listing details** adds a price or a link to any light, including ones you own. **No longer used** takes a light off Grow lights (it must not be in a spot) and keeps it here.
