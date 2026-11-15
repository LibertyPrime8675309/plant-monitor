# Identify, the Library, mushrooms and plant knowledge

Part of the Plant record manual. The README in the folder above has how to start, stop, update and back up the app, and the list of every manual page.

## Identify a plant and the plant library (from 1.18.0)

**Identify** (in the top menu) tells you which of your plants the camera is pointing at, and how sure it is. If the plant isn't one of yours, it suggests what it could be. **Library** looks up any plant species by name.

Everything is worked out on this computer, by a second container called `plant-vision`. It runs **BioCLIP 2.5 Huge**, a free AI model (MIT licence) trained on over 200 million pictures of living things. It runs on the processor and doesn't need the graphics card. Only the app can talk to it; it has no address of its own on this computer, your network or Tailscale. It can read your database and photos but can't change them.

### The first start

The first update to 1.18.0 takes longer than usual:

1. **Building the container** downloads about 1 GB of Python packages (PyTorch). The updater waits for this.
2. **Its first start** downloads about 5 GB into `data\vision`:
   - the BioCLIP 2.5 model (3.9 GB);
   - its fingerprints for 349,000 plant species (0.7 GB), from the Tree of Life list;
   - the USDA PLANTS lists of which plants grow wild in each state (9 MB).

   It then fingerprints your photos, well under a second each on your processor. The Identify page shows how far it has got. Plan on 20 to 40 minutes in all, mostly downloading. After that it starts in under a minute and needs no internet.

`data\vision` is safe to delete; it downloads everything again on the next start. Backups leave it out.

**From 1.22.0** it also knows about 49,000 fungi (mushrooms, lichens, moulds). The first start after that update downloads their fingerprints, about 100 MB, which takes a few minutes. Until then Identify and the Library still work for plants.

### Using the camera

- Open **Identify** and press **Start camera**. It checks about once a second.
- When it has seen the same plant twice and is at least 80% sure, a window names it: for example "Very likely P-020: Fiddle-leaf fig, 93% sure". It shows your picture next to that plant's closest photo. From there you can:
  - press **Open its page**;
  - press **Add this picture to its photos**;
  - press **Not this one** to keep looking.
- **Check this picture** holds the picture still and shows everything it found:
  - **Which one is it?** with three photos when it is unsure between plants;
  - **Probably not one of your plants** with species suggestions when it doesn't recognise the plant.
- **Use a photo instead** checks a photo you already have. On a phone it can also open the camera app.
- **Plant labels:** the QR codes on labels from the Labels page are read too, and open the plant straight away.

**How sure is "sure"?** The percentage comes from tests on your own 213 photos, each checked against all the others. It said 80% or more for a third of them, and was right 92% of those times. Over all your photos, the right plant came first 70% of the time and was in the top three 80% of the time. If a picture looks unlike all your photos, it says it is probably not one of yours. Similar plants are the hard cases, such as your Monsteras or two plants of the same kind. A clear daylight photo of the leaves, from about the distance of your other photos, works best.

**The browser only allows the camera on a secure address:** `http://localhost:8080` on this computer, or the Tailscale address `https://plants...` on your phone. On any other address, use **Use a photo instead**.

### Names for plants that aren't yours

Under **When it is not one of your plants, suggest names from**, choose:

- **Your state's plants**, such as **Texas plants** (about 4,750 species) or **California plants**, from the USDA lists. It follows the Location button (from 1.28.0), and is only offered for places in the US. Best for wild plants and weeds in your yard.
- **Plants with a common name, and all US plants** (about 34,000; the usual choice). Good for houseplants and garden plants.
- **US plants** (about 19,000).
- **All plants worldwide** (about 349,000).

Names guessed from a picture are often wrong at the species level; the genus is right more often. In tests on your photos with the usual list, the right species came first 43% of the time and was in the top five 65% of the time. The right genus came first 56% of the time. With the Texas list, for plants that grow wild in Texas, the right species came first 74% of the time. So treat the names as leads, and check them with the links (USDA PLANTS, Kew's Plants of the World Online and Wikipedia) or a second opinion.

**Add as a new plant** opens the Add a plant form with the names filled in and the picture attached when you save.

### Second opinions: Pl@ntNet and Claude

When this computer is unsure, the results have **Ask Pl@ntNet** and **Ask Claude** buttons. Ask Pl@ntNet first: it is free and very good with plants. They only see a picture when you press their button. You set them up once, as the owner, under **Second opinions** at the bottom of the Identify page:

- **Pl@ntNet:** a free account at my.plantnet.org gives an API key for 500 pictures a day. Pl@ntNet doesn't keep the pictures.
- **Claude:** an Anthropic API key from console.anthropic.com. It is billed to that account, about a cent or two per picture. Claude also says what it based its answer on, and what photo would make it surer.

The keys are kept in the database on this computer, and so in its backups. The app never shows them again, only their last 4 characters. People who can only view can use Identify and the library, but not the second opinions.

### The plant library

**Library** lists every species in the list chosen under **Look in**, straight away, with no search needed: about 34,000 in the usual list, up to 349,000 worldwide. From 1.21.0 it works like the Plants page:

- **Search** narrows the list as you type, by scientific or common name.
- **Filters:**
  - **Kind of plant:** broadleaf flowering plants, monocots (grasses, lilies, palms, orchids), ferns, conifers, cycads, mosses, algae and so on.
  - **Family:** type it, or pick from the list, which shows how many species each family has.
  - **Grows wild in:** the US, Texas, or any state.
  - **Show:** only the ones you have, or the ones you have plus others of the same genus.
  - **Only plants with a common name.**
- **Sort by:** best known first (common name, then how widespread in the US), common name, scientific name, or family.
- **Show as** cards with photos, or a table. **Show more** adds the next 48.
- The filters are remembered in this browser, and **Clear search and filters** starts over.

**Each species has its own page.** Click a card to open it. It has:

- Photos: yours first if you have the plant, then up to six from iNaturalist, each naming its photographer and licence.
- A short description from Wikipedia, and how often iNaturalist members have recorded it.
- Its common names.
- Its classification. Each order, family and genus is a link to the library filtered to it.
- The US states and territories where it grows wild.
- Your plants of that species or genus.
- **Looks like:** the species the BioCLIP model finds closest. They are the easiest to mix up with it, though not always close relatives.
- Links to USDA PLANTS, Kew, iNaturalist and Wikipedia, and **Add to my plants**.

**Where the photos come from.** Library photos and descriptions come from iNaturalist, whose members share their photos under Creative Commons licences. Only the species name is sent. The app fetches about one species a second, as iNaturalist asks, so a page of cards fills in over a minute the first time. Each photo is kept in `data\library`, so it is only fetched once. The owner can turn this off at the bottom of the Library page, and the library then works fully offline, without photos.

The names come from the Tree of Life list that BioCLIP was trained with (Imageomics Institute, free to use), and the states from the USDA PLANTS state lists (public domain).

#### Fungi in the library (from 1.22.0)

Choose **Fungi worldwide: mushrooms, lichens and moulds** under **Look in** (on the Library or the Identify page). **Kind of fungus** then filters to mushrooms (with brackets, puffballs and jelly fungi), cup fungi, lichens, rusts and smuts, or moulds and mildews. The USDA state lists include lichens but no other fungi, so **Grows wild in** only works for lichens.

A fungus page has a safety note at the top, your finds of that species, and **Record a find of this** instead of **Add to my plants**. Nothing in the app ever says a mushroom is safe to eat.

#### Your notes and tags (from 1.22.0)

Every species page has **Your notes and tags**. Press **Add notes and tags**, write anything, and add tags separated by commas (for example `shade, gift idea`). Tags are saved in lower case. Each tag is a link that lists every species with that tag, and the tags show on the library cards. Everyone you have given access to the app can read them; people who can only view can't change them.

#### Your wishlist (from 1.22.0)

On any species page, press **Add to my wishlist**. The Library page has a **Your wishlist** button, which opens the list:

- **Got it** moves a plant to "Got them" (and **Move back to wanted** undoes that).
- **Edit** adds where to find it (a nursery, a website) and notes.
- **Take it off the list** asks first.

In the library, **Show** can be set to **On my wishlist**, **Ones with notes or tags**, or any one of your tags.

#### Prices, stock and alerts (from 1.27.0)

From 1.30.0 this is on the **Shopping** page, with the stores on the **Stores** page (see "Shopping, stores, and quicker pages"). The plant record checks the stores for everything you still want: every 12 hours, or when you press **Check the stores now**.
- **On each wanted plant:** the cheapest listing now (with a link to it), how many shops have it, and **Every listing found, with past prices**.
- **Edit, and set alerts** sets:
  - **Search the shops for**: one search per line, such as a variety ("Monstera Thai Constellation"). If it's left empty, the common and scientific names are used.
  - **Alert me when the price is at or under** $X, shipping not included.
  - **Alert me when a shop has it in stock**.
- **Alerts** appear at the top of the Wishlist page and on Today, and the top bar shows how many beside **Library**. Each check makes at most one alert per plant. A price alert comes again only if the price drops further, and a stock alert comes again only if it sold out and came back. **Dismiss** clears an alert.
- **Shops checked** (at the bottom of the Wishlist page) lists every shop, how it is read, and its last check, or what went wrong. The owner can turn shops on and off, change an address, add a shop, and choose how often:
  - **Online stores** (Steve's Leaves, Logee's, North Spore and others) are read for names, prices and stock. The kind of store is worked out on the first check.
  - **Local nurseries with no online store** (Round Rock Garden Center, Snooper's, Cantu Imports, Barry Hill) have their plant pages read for the names on your wishlist, with the price if it's on the same line. Call them to be sure.
  - **eBay and Etsy** are searched through their official services, which need free keys from developer.ebay.com and etsy.com/developers. The owner pastes them under **eBay and Etsy keys**. They're kept on your computer and never shown again.
- Walmart, Home Depot, Lowe's, Amazon and Facebook Marketplace are left out on purpose.
- Each shop gets at most one request every 2 seconds, a few times a day, and the requests say they come from a home plant record.

#### Your area, pets and care sheets (from 1.23.0; from 1.28.0 for any place)

From 1.28.0 everything here is about the place chosen with the **Location** button (Round Rock or Nevada City, or any other place), not always Texas. Each place's state (or, outside the US, its country) is looked up on iNaturalist once. Below, "Texas" means that state or country.


Each plant's page in the library now has three more sections:

- **Here at home:**
  - whether it is native or introduced in Texas;
  - how often people have recorded it growing wild within 31 miles of home, and whether it is flowering there this month;
  - a warning if it is on the Texas noxious and invasive plant list (Texas law says those may not be sold, distributed or brought into Texas).
- **Will it survive outside here all year?** "Likely" if it grows wild near home, or if its care sheet's hardiness zones include yours (worked out from your own weather history; 9a for Round Rock). Otherwise it says it doesn't know.
- **Pets:** what the ASPCA's lists say for dogs, cats and horses. A plant not on their lists is not called safe.
- **Care sheet:** press **Write a care sheet with Claude**. Claude writes one for your place and zone in about half a minute, using the owner's Anthropic key (the one on the Identify page; a cent or two each). It covers light, water, soil, temperature, feeding, pruning, propagation, pests, pots, hardiness and growing it outdoors here. It is kept, everyone with access can read it, and it is marked "not checked by a person". People who can only view can read care sheets but not ask for them.

The cards show the same things as tags (for example "Native to Texas", "Flowering near home now", "⚠ Toxic to dogs and cats", "⚠ Texas invasive list"). The filter **Your area** (called "Texas and home" before 1.28.0) lists only:
- the ones native to or introduced in Texas;
- the ones on the invasive list;
- the ones that grow wild near home, or are flowering there this month (or, for fungi, found there this month);
- the ones likely to survive outside here;
- the ones safe for, or toxic to, dogs and cats.

**Around home** (a button at the top of the Library page, and on the Mushrooms page) shows three lists, with photos:
- what is flowering near home this month;
- the mushrooms and other fungi found there this month;
- the plants and fungi recorded wild there most often.

**Where this comes from.** These lists are fetched in the background, about one request a second, and kept in `data\library\local`. **Lists about your area**, at the bottom of the Library page, shows each one, when it was fetched, and **Fetch the lists again now**. The lists are fetched again by themselves when they get old (Texas lists and pets every 3 months, near home every month, this month's flowers and fungi every 2 weeks).

- **iNaturalist:** what is native or introduced in Texas, and what people have recorded wild near home (only species names and the home place's position are sent).
- **The ASPCA's** toxic and non-toxic plant lists, read from their web pages.
- **The Texas Department of Agriculture's** noxious and invasive list, which is built in. It is only used for places in Texas: the app has no such list for other states or countries yet, and says so.

When the owner turns library lookups off, none of this is fetched.

#### Photos for offline use (from 1.22.0; by area from 1.28.0)

At the bottom of the Library page, **Photos for offline use** has a table of areas. An area is any country, state, county, city or park that iNaturalist knows. For each area the app gets the list of every plant species recorded there, then downloads each one's photo and short facts, so the library shows them without the internet.

The table shows, for each area:
- **Photos downloaded**, out of how many species there are (and how many have no photo on iNaturalist);
- **Percent** downloaded, as a number and a bar;
- **Last updated**: when its list was last fetched;
- while it runs, how many are left and about how long it will take.

The owner can:
- **Add an area:** type a name (for example "California"), press **Search**, then **Add and download** beside the right place;
- **Check for updates:** fetch the area's list again and download only what is new;
- **Remove** an area: it leaves the table, but its photos stay (another area may use them);
- **Stop all downloads.**

Downloads go at about one species a second, after anything someone is looking at, so a state with 5,000 species takes about an hour and a half and uses about 350 MB in `data\library`. Species already kept are skipped. You can leave the page while it runs. If the app restarts part way through, press **Check for updates** to carry on.

### Stopping the picture checker

The rest of the app works without it. Identify and Library then say it isn't running. It uses about 6 GB of memory while running, and no processor time when idle. From the `plant-database` folder:

Windows (cmd.exe):

```
docker compose stop vision
docker compose start vision
docker compose logs --tail 30 vision
```

Windows (PowerShell) and bash: the same commands.

`docker compose up -d` (and the updater) starts it again. To keep it stopped for good, put the line `PLANTDB_VISION=0` in the `.env` file:

- Windows (cmd.exe): `(echo PLANTDB_VISION=0)>>.env` then `docker compose up -d`
- Windows (PowerShell): `Add-Content .env 'PLANTDB_VISION=0'; docker compose up -d`
- bash: `echo 'PLANTDB_VISION=0' >> .env && docker compose up -d`

### A smaller, faster model

If the computer is busy or short of memory, BioCLIP 2 is about half the size. It recognises your own plants nearly as well, but is much weaker at naming plants that aren't yours: with the usual list, the right species came first 17% of the time instead of 43%. To use it, put `PLANTDB_VISION_MODEL=bioclip-2` in the `.env` file and restart. It downloads its own 2.2 GB the first time.

- Windows (cmd.exe): `(echo PLANTDB_VISION_MODEL=bioclip-2)>>.env` then `docker compose up -d`
- Windows (PowerShell): `Add-Content .env 'PLANTDB_VISION_MODEL=bioclip-2'; docker compose up -d`
- bash: `echo 'PLANTDB_VISION_MODEL=bioclip-2' >> .env && docker compose up -d`

To go back, delete that line from `.env` and run `docker compose up -d` again.

## Better names from Identify (from 1.39.0)

The picture checker (BioCLIP, on this computer) used to rank every species by the picture alone, which put three wrong names on the screen often enough. From 1.39.0 it weighs the names toward what you are likely to be looking at:

- **Your record:** a species already named in your plants, or its genus, is lifted. A new pot of a plant you have gets its name.
- **Your photos:** when one of your named plants' photos looks like the picture, that species is lifted (the closer, the more).
- **Houseplants** (about 150 genera grown indoors) and **the plants of your state** (with the state list chosen) are lifted a little.
- Each lifted name says why on its card ("Lifted: a houseplant", "Lifted: looks like your photos"). The line under the result says the names are weighted. To turn the weighting off, put `VISION_PRIOR=0` in `.env` and restart.
- **Ten names** come back, five shown; **Show 5 more names** unfolds the rest. The three likeliest **genera** are on the line above: when no species fits, the genus is the safer answer.
- **Several pictures of one plant:** after a result, **Add another photo of the same plant** (or **Add a camera shot of it**) checks them all together. Each picture is also looked at three ways (as it is, the whole picture letterboxed, and its middle).
- **Pl@ntNet first when unsure:** under Second opinions, tick **Ask Pl@ntNet on its own whenever this computer is unsure**. With the Pl@ntNet key saved, a picture the computer is not sure about (no sure match among your plants, best name under 50%) goes to Pl@ntNet at once and its answer shows above the computer's own. Each costs one of Pl@ntNet's 500 free pictures a day.

The weights were measured on your photos on November 8, 2026 (`dev/vision/README.md`): with them the right species comes first for 40% of photos instead of 33%, and is in the top five for 61% instead of 54%.

### Two ways to identify (from 1.51.0)

The weighting above is right for "which of my plants is this?" and wrong for a plant met in a garden or the wild, so every page that identifies now asks **What are you looking at?** first:

- **One of my plants:** a plant in the record, a cutting or a new pot of one. The names you already have, houseplants and your plants' photos count, as above.
- **A new find:** a plant met in a garden, a shop or the wild. Nothing you have counts; instead the plants recorded in this home's country (from GBIF, the world's occurrence records) are lifted, the more often recorded the more. The country is the one set for the home on **Weather → Homes and places**. The first time a country is asked for, its list is downloaded (about a minute for the United States, 48,000 species) and the result says so; until it is there, no country is favoured.
- The question offers your **last answer first**, so Enter repeats it. Tick **Do not ask again on this page** to make the answer the rule for that page, or set the rule in **Display settings → Identify**, one choice for each page (Identify, adding plants, a plant's own page). The rule follows you to every device you sign in on.
- On Identify, **What you are looking at** above the camera shows the way in use and can be changed any time. Every result says how it was checked ("Checked as a new find. Plants recorded in US (48,696 species) come first.") and each lifted name says why ("Lifted: recorded in this country").
- The checker is measured against the November 8 baseline (`dev/vision/README.md`); `prior_test.py` now has a "new find" row too, which needs the country's list from `data\vision`.
- Also fixed: **suggest names from** on Identify (the species list) was never saved, so the list went back to the first choice on every visit.

### The checker learns from you (from 1.52.0)

- **This is right** sits beside **Not this** on every name Identify offers (editors and the owner). Press it and the picture is kept as a confirmed example of that species; from then on, a picture that looks like it lifts that name ("Lifted: looks like your photos or a confirmed picture"). On a plant's own page, **This is right** keeps the plant's main photo as the example.
- **Not this** now keeps the picture too, as an example of what the name does *not* look like: a later picture that looks like it has that name lowered ("Lowered: looks like a picture that was not this"). Saying no to a whole genus is words only, as before.
- Your named plants' photos always counted; now **named mushroom finds** (fairly sure or confirmed by an expert) count as examples as well.
- The status line on Identify says how many confirmed and rejected pictures it has learned from. Every confirmation and rejection is in the Audit log with who made it. The pictures are kept in `data\photos` as `ex_….jpg` and go into backups with everything else.

## Mushroom finds (from 1.22.0)

**Mushrooms** in the top menu is a page of its own for the mushrooms you spot: in the yard, in a plant pot, or anywhere else. Each find gets a code, F-001, F-002 and so on.

**Adding a find.** Press **Add a find**.

- **Photos:** take photos of the cap from above, the underside (gills or pores), the whole stem and the very base. On a phone the button can open the camera. If a photo carries its location (most phone photos do, if location is on for the camera), the find gets that location.
- **Where and when:** the date, and whether it was in the yard, in a plant pot (then pick which plant) or somewhere else, plus a description. **Use my location now** asks the phone or browser for where you are. Locations are seen by everyone you have given access to the app.
- **What it grew on:** soil, mulch, dead wood, a living tree, potting mix and so on; what kind of place (lawn, under trees, a garden bed, a field, wet ground, indoors; from 1.51.1); trees nearby; how many.
- **What it looks like:** cap width and colour, gills or pores, the stem (length, thickness, colour, hollow or solid; from 1.51.1), a ring on the stem, a cup or sac at the base, spore print colour, colour change when cut, smell. From 1.51.1 the spore print, colour change and smell boxes offer the usual answers a field guide asks for (white, cream, pink, rusty brown, purple-brown, black; blue, red then black; anise, almond, flour, rotten, and so on) and still take your own words. The help text there says it plainly: nothing recorded, and nothing the app says, means a mushroom is safe to eat.
- **Name:** a common name or your own description, the scientific name, and how sure the name is: not identified yet, a guess, fairly sure, or confirmed by an expert.

Only the photos and the place really matter at first; you can fill in the rest any time with **Edit this find**.

**A find's page** shows its photos (**Previous photo** and **Next photo**, **Make this the main photo**, **Edit caption**, **Remove photo**), where and when (with a link to the map), and what you noted. **Identify the photo shown** compares the photo on screen with the 49,000 fungi, on this computer. **Use this name (as a guess)** saves a suggestion as the scientific name, marked "A guess". **Archive this find** takes it off the list without deleting it.

**The list of finds** can be searched and filtered by how sure the name is, where, and year. **Show** includes archived finds.

**Safety.** Every mushroom page has a short safety note, and **Read more** opens the full one. Never eat a wild mushroom because of an app, a photo, or this record. If a pet may have eaten one, call your vet or ASPCA Animal Poison Control at (888) 426-4435. If a person may have, call Poison Control at 1-800-222-1222 (or 911 if they are very ill).

Changes to finds are in the Audit log under "Mushroom finds", and the finds and their photos are in your backups like everything else. **Download the finds (CSV)** on the Mushrooms page gives every field for a spreadsheet or to send to an expert, and **Download all data (JSON)** on Settings now includes the finds and their photo records (1.51.1).

## Facts and where they come from (from 1.53.0)

Everything the app says about a species now has a source you can see. Open a species page (from a plant's page, the Library or Search) and the section **Facts and where they come from** lists every fact the record holds for it, in groups (Temperature, Light, Water, Soil, Feeding, Size and growth, Hardiness, Origin and safety, Pests, Propagation, Uses and partners, Care sheet). Each fact shows its value, where it came from, who noted it, when, and how sure it is (certain, likely, unsure); a field that has changed shows its **History**.

- **Where the first facts came from.** When 1.53.0 starts it reads what the record already knew and files it once, in place: the uses, partners and propagation Claude wrote for each species; Claude's care sheets from the Library; and, for every species in your record, the care values its plants agree on (temperatures, humidity, light, water, soil, feeding, size, hardiness, origin, safety, pests). Each care value is traced back to the upgrade batch or the first plant list that set it, or, if you changed it yourself, to you ("Edited in the app on P-003 by Ethan", your own observation). Nothing you typed is changed, and your plants' own values stay as they are.
- **A plant's page reads the species' facts** for any care field the plant leaves empty, and says so in a line under the identification ("Not set for this plant, so shown from *Ficus carica*'s facts: soil or potting mix, hours of light"), with a link to the species. A plant's own value always wins, and the edit form shows only what is really on the plant.
- **Download every fact (CSV)** at the bottom of the section (`/api/facts/export.csv`; `/api/facts/export` for JSON), so the knowledge can be checked in a spreadsheet or moved to another install.
- New upgrade batches can add facts as rows (`facts_add`), with the batch as their source.

### Adding and correcting facts (from 1.54.0)

- Anyone who can edit may press **Suggest a change** under a fact, or **Add a fact** at the bottom of the section. The form asks for the value, where it comes from (a link, a book and page, a grower, or your own observation), what kind of source that is, and how sure you are. It goes in as a **proposal**: it shows on the species page in a highlighted box, not as the value.
- **Someone else accepts or rejects it**: another editor, or the owner (the owner may also accept their own). **Accept** makes it the value every page shows and moves the old value into the history; **Reject** asks for a reason, which is kept. Nobody but the owner can accept their own proposal, so every fact that shows was seen by two people.
- **Facts to review** (Plants → Facts to review, and a block on Today while anything waits) lists every open proposal with the value it would replace. Each change is in the Audit log under "fact", with who proposed and who accepted.
- **Mushrooms** have facts too (their description, where they grow, what they do), under the same rule as everywhere else: a proposal that says a mushroom is edible, safe, tasty or medicinal is refused, and there is no field for care values.
- **Moving facts between installs:** send the JSON from `/api/facts/export` to `/api/facts/import` (editors and the owner); every row arrives as a proposal, never as an accepted fact, and duplicates are skipped.

## Uses, partners and propagation (from 1.27.0)

Every plant page has a section **Uses, partners and propagation** (the **Uses** button in the row of section buttons). Species pages in the Library have it too, and mushroom finds have **What it does, and growing it**.
- **Uses**: what people use it for (food, skin and first aid, dye, crafts, ground cover, cut flowers...), each with its safety warnings. Traditional uses are labelled as such and are not medical advice.
- **In the compost**: good, fine in small amounts, poor, or keep it out, and why.
- **Keeps away** and **Brings in**: pests or animals it deters, and the pollinators, birds and helpful insects it feeds.
- **Good partners** and **Keep apart from**: each with how sure it is ("shown in trials", "gardeners' lore, not proven", "same light, water and soil", or "needs different light, water or soil"). When you have a partner plant, it says **You have it** and links to it.
- **Propagation**: the ways to make more of it, and the best time of year here.
- **Breeding**: how it crosses, then links to **your plants of the same species** and **your plants it may cross with**. Patented varieties are flagged: propagating a patented plant isn't allowed while the patent lasts, even for yourself.

For your plants, Claude wrote these from general horticultural knowledge (upgrade batch A9, about 50 species, plus their genus for named hybrids). Nothing was checked by a person. For any other species, press **Write them with Claude** on its page. Like care sheets, it uses the owner's Anthropic key (saved on the Identify page) and keeps the result. For mushrooms, uses never include eating them.

## Propagation and breeding guide (from 1.57.0)

A reference for making more plants, and for making plants that are new. Open it from the **Library** (the **Propagation and breeding guide** button beside Around home and Wishlist), from the **Uses, partners and propagation** part of a plant page or a species page, or with **Search**. It has no link of its own in the top bar.

- **Which way should I do it?** goals such as "an exact copy of a woody or large plant" or "a copy that keeps its variegation", each linked to the ways that suit it.
- **Before you start**: clean tools, rooting hormone, humidity, warmth, labels and patience.
- **Copying a plant: propagation**: stem cuttings, leaf cuttings, root cuttings, division, offsets, pups, keikis and runners, layering in the soil, air layering, grafting and budding, bulbs, corms and tubers, spores, tissue culture and seed. Each is folded until you open it, and gives what it suits, the steps, and things worth knowing.
- **Your plants** are listed under each way: the ones that have it in their own propagation notes or in their species' facts. Each is a link, with its code beside the name.
- **Breeding: making plants that are new**: the genetics you need, making a cross step by step, selecting and fixing traits, other ways to get something new (sports, chimeras, doubling chromosomes, hybrids between species), orchid breeding, and plant patents.
- **Keeping a mother plant.**
- **"How to" links.** In a plant's or a species' list of propagation methods, **How to** beside a method opens the guide at that method.
- Lengths and temperatures follow your units (**Display → Units**). **Read this page aloud** and **Read aloud** on each section work as on other pages, and the page works offline; only the list of your plants needs the plant server.

The words were written by Claude from general gardening knowledge, and a person has not checked them against a source. The page says so. What one species needs, with where each fact comes from, is on its own page.
