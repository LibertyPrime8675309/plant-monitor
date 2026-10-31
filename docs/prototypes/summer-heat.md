# Prototype: summer heat (AHS heat zones)

Branch `proto/summer-heat`.

## What it does and why
The USDA hardiness zone on About this plant says whether a plant survives a usual Round Rock **winter**. Many of your plants struggle in the **summer** instead. This adds a "Summer heat (AHS heat zones)" part right after the hardiness zones on every plant page:

- **Where you are.** From the weather history: how many days a usual year go above 86°F at the place in use, and the American Horticultural Society heat zone that gives (1 = cool summers, 12 = very hot), plus how hot a usual year's hottest day is.
- **What it means for this plant.** It uses the plant's own "Heat damage above" temperature (already filled in for every plant, under Temperature) and counts how many days a usual year reach it, and in which months:
  - "✓ Summer heat is fine for it here" when a usual year never gets that hot.
  - "▲ A few days a summer are too hot for it" (under 10 days): shade it on those afternoons.
  - "■ Summer heat is hard on it here" (10 days or more): afternoon shade or inside through those months.
  - For a plant that is indoors or in the garage, it adds that this matters when it goes outside.
- **Hot days each year.** A table of this year so far and the last 10 whole years: days over 86°F (with a bar on wide screens), days at the plant's damage temperature or more, and the hottest day.

Each verdict starts with a symbol and words, so nothing depends on colour. With very large text, the table turns into a short list per year so nothing scrolls sideways.

## How it looks
Laptop, high contrast (Aeonium, heat damage at 90°F):

![Laptop](summer-heat/laptop.png)

Phone, dark theme, the whole part:

![Phone, dark](summer-heat/phone-dark.png)

Phone with the largest text (the table becomes a list):

![Phone, largest text](summer-heat/phone-large-text.png)

The screenshots use made-up weather in the test copy, so the numbers are not Round Rock's real ones. Yours come from the weather history your app has already loaded.

## What it changes in your database
Nothing. It only reads the daily weather history and each plant's heat-damage temperature. If a place has under 3 whole years of history, it says so and links to the Weather page.

## How it works (for Claude)
- `server.py`, block "prototype proto/summer-heat" after `place_climate()`: `ahs_heat_zone()`, `place_highs()` (cached 6 hours per place), `place_heat()` and `GET /api/heat[?above=F][&loc=ID]`. Whole years have 330 or more days of highs; the zone needs 3 whole years. "Above 86°F" is strictly above, as the AHS defines it; the plant count is "at or above" its damage temperature.
- `app.js`, block after `aboutBlock()`: a MutationObserver puts `#heat-box` after the hardiness zones and fills it (`loadHeat()`, `heatBlock()`, `heatVerdict()`, `heatTable()`, `heatFit()`). No edits to shared code.
- `style.css`: its own block after the 1.14.0 block.
- Test: `dev/test/heat_check.py` (zones, counts, refusals, placement, the three verdicts, phone, dark, large text, high contrast).

## How to try it
Start the mock server with a fresh data folder in one window, then run the check in a second window (it loads ten years of made-up highs first):

cmd.exe:
```
set DATA_DIR=%CD%\dev\tmp\heat-data
python dev\test\mock_server.py
set SERVER_DATA=dev\tmp\heat-data
python dev\test\heat_check.py
```

PowerShell:
```
$env:DATA_DIR = "$PWD\dev\tmp\heat-data"; python dev\test\mock_server.py
$env:SERVER_DATA = "dev\tmp\heat-data"; python dev\test\heat_check.py
```

bash:
```
DATA_DIR=$PWD/dev/tmp/heat-data python3 dev/test/mock_server.py
SERVER_DATA=dev/tmp/heat-data python3 dev/test/heat_check.py
```

## Open questions for Ethan
1. Is the plant's "Heat damage above" temperature the right line for the verdict, or would you rather it counted days above the top of its comfortable range (usually 85°F to 95°F), which would warn about far more plants?
2. Should the verdict also show on the Plants page (for example a "Struggles in summer heat" filter), or is the plant page enough?
3. Would you like the heat zone and the hot-days table on the Weather page too, next to the winter numbers?
4. The AHS also gives each plant a heat-zone range (like "zones 9 to 1"). I could add that as a field and fill it for your plants in an upgrade batch, if you find it useful.
