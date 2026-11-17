# Weather, cold nights and sensors

Part of the Plant record manual. The README in the folder above has how to start, stop, update and back up the app, and the list of every manual page.

## Frost alert and cold-night checklist (from 1.8.0)

A night in the 7-day forecast may be cold enough to hurt a plant that is outside. Then a banner at the top of the page says how cold it will get, and on which night. It says how many plants could die, would be damaged or are close calls, and when to act ("before dark today"). From 1.58.0 each night has its own numbers: the banner leads with the coldest night. Then it says what the first cold night would do, if that is a different night. The time to act is the evening before the first night that would damage a plant. A night with close calls only says that nothing is forecast to be damaged. Plants you marked as covered are not counted again. It is called "Frost warning" at 36°F or below and "Cold warning" above that, because the tropical plants are hurt at 50 to 60°F. **Hide until the forecast changes** hides it until the forecast gets colder or more plants are at risk. Plant pages show their own **Frost risk** note instead of the banner.

From 1.58.0 the banner on pages other than Today is one line. It has the warning, and how many plants to bring in or cover, and by when. It has **Open the cold-night checklist** and **Hide until the forecast changes** (on a phone, **Open the checklist** and **Hide**). The numbers for each night are on Today and on the checklist.

**Open the cold-night checklist** (on the banner, or on the Winter plan page) shows the next 7 nights. Then it lists each plant once, most urgent first, in three groups: **Bring inside**, **Cover or move to shelter**, and **Close calls** (within 3°F of the damage point). Each plant has two buttons, with **Undo**:

- **Moved indoors** sets its Location to Indoors, so it leaves every list and warning.
- **Covered for tonight** ticks it off for its next cold night only, since covers go back on each night.

 Each group also has a button for all its plants, which asks first. Tips for a cold night are at the bottom.

From 1.58.0 the checklist is shorter. In each group, what most plants share is said once at the top: the nights ahead, what to do, and the porch note. A plant's own row then shows only what is its own: its damage and death temperatures, and its nights or advice when they differ from the group's. On a phone, or an iPad held upright, a plant's words run beside its photo and then under it, and **Moved indoors** and **Covered** sit side by side. The Back outside list uses the same rows. At the largest text on a phone the checklist went from 156 screens to 100 (78 plants on it).

Plants set to Indoors or Garage or shed are never counted. Plants on the Covered porch are.

## Getting plants ready to come inside (from 1.9.0)

Outdoor plants often carry ants, spider mites, mealybugs and other pests. Each plant page has a **Getting ready to come inside** section, after Winter in Round Rock, that helps keep them out of the house.

**Start the checklist** (from 1.40.1) sits right under the plant's status, on its page and inside its fold on the Coming inside page. Once started, the plant shows as In progress. **Undo the start** takes it back until you have done a step, and **Go to the checklist** jumps to the list.

**Folded until you start (from 1.58.0).** On a plant's page, About this plant and the checklist fold into one line, such as **About this plant, and the checklist (10 steps)**. Press it to open them. They open by themselves when you press **Start the checklist**, and **Go to the checklist** opens them too. Once open, they stay open while you tick steps.

**The checklist is tick boxes (from 1.41.1).** All 10 steps are listed in order, each with a tick box, its rating, why, and "How to do it". Tick a step when you have done it (it is logged for today); untick it to take back the last time. Steps rated Not needed or Not for this plant are marked **Not recommended** with a dashed border, and can still be ticked. A spray that needs a second round says when, with a **Round 2 done today** button. A plant that is already inside can be started too, such as a new plant from a store, or one that came in without a check. It is then kept apart for 3 weeks from the day you started.

1. Under **About this plant**, check the **Leaf type** and choose the **Pot size**. Claude filled in the leaf type for every plant; change it if it is wrong.
2. Inspect the plant (the first method explains how) and tick any **Pests you found**. Leave them all unticked if you found nothing.
3. The ten methods are listed in the order to do them, each rated for this plant: **Best**, **Good**, **Use with care**, **Not needed** or **Not for this plant**, with the reason. Open **How to do it** for the steps. Methods that are not needed or not suitable are folded away under one line.
4. Press **Done today** after each one. It goes into the care log, the timeline and "Copy my answers for Claude". **Undo the last one** takes it back. To record a step done on an earlier day, use **Log other care**.
5. If a spray needs a second round, the **Today** page reminds you 5 days later.
6. When the plant comes inside, change its Location to Indoors (or press **Moved indoors**). The section then says until when to keep it apart from your other houseplants: 3 weeks, or 2 weeks after its last treatment if you found pests.

The page **Getting plants ready to come inside** lists every plant coming in, grouped as Not started, In progress, Ready to come inside, and Inside. It opens from the Winter plan page, the cold-night checklist and the Today page. From 1.41.1 each plant is folded shut: its photo, name, next step and how many recommended steps are done. Open it for its tick boxes, Start the checklist and **Open its plan** (straight to that plant's section). **Open every plant** and **Close every plant** are at the top, and a plant you opened stays open while you tick. The page also has the steps for all ten methods and advice on keeping plants apart.

Pots are never cleaned with bleach. Use hot soapy water, a brush and a day in the sun. For extra cleaning, soak them 10 minutes in 3% hydrogen peroxide, never mixed with vinegar or other cleaners, then rinse. A new pot works too.

## Back outside in spring (from 1.15.0)

In spring, open **Winter plan** and press **Which can go back outside?** (or go to the **Back outside** page). It checks every plant whose Location is Indoors, or Garage or shed, against its own temperatures and the 7-day forecast:

- **Ready:** every night in the forecast is at or above the low it likes.
- **Safe, but cool:** no night comes within 3°F of its damage point, but some nights are cooler than it likes.
- **Too early:** this week is fine, but in most years colder nights still come after this date.
- **Not yet:** a night in the forecast is too cold. The page says which night and how cold.

Each label is a word in a box, not just a colour. With 3 or more years of weather history, each plant also gets the date the nights usually stay warm enough. **Moved to the porch** and **Moved outside** change its Location, like the Moved indoors button. From late autumn to winter the page says plants should stay in until spring. In spring the Today page says how many can go back out.

## Weather and sensors

The **Weather** page replaces the fixed weather table. It has:

- a 7-day forecast for your location, with freezing nights marked and a count (and list) of plants that would be damaged at each night's low;
- charts of temperature, humidity and light over the last day, 3, 7, 14, 30 or 90 days, or a year, from online weather and from your sensor, with a table of the numbers under each chart and an option to overlay one plant's comfortable range;
- an Expected-and-tracked table for October to March: the 30-year averages next to what was actually recorded;
- sensor connection details and location settings.

The Winter plan page uses the same data for its forecast and its season table.

From 1.58.0 the Winter plan's **Plant by plant** list is shorter. Each plan (Move indoors, Cover in place and so on) runs across the page, one under the other, with its plants in as many columns as fit. Before, each plan was a column, so the longest one set the page's length. On a phone, or an iPad held upright, a plant's words run beside its photo and then under it, and **Moved indoors** is only as wide as its words. Already inside works the same way.

Online weather comes from [Open-Meteo](https://open-meteo.com/) (free, no account). The app fetches it every hour, loads the last 3 months the first time, and keeps everything in your database, so the history keeps growing. The computer running Docker needs internet access for this. If an update fails the Weather page shows the reason. Location is Round Rock, TX by default; change it under **Location and updates**. To bring in older history (for example last winter), use "Load older weather history from this date". Light is estimated from solar radiation (about 2.1 PAR per W/m2).

### More than one place

The Weather page can track as many places as you like, for example Round Rock, TX and Baraboo, WI. Each place keeps its own hourly readings, daily summaries, forecast, Load history and update log.

- **Add a place**: Weather page, **Places** section. Type a town or city, press **Search**, and pick the right one from the list (it shows the state or country, coordinates, time zone and elevation). You can also type the name, latitude, longitude and time zone yourself. A new place fetches its last 3 months and forecast straight away, then updates every hour like the others.
- **Location**: the menu at the top of the Weather page is the same choice as the **Location** button at the top of every page (see "Location" below). It picks which place the page shows: forecast, charts, the table of logged data, the season table, Load history and the update log.
- **Compare places**: in Tracked history, open **Choose what to chart and compare places** and tick other places. Every chart then has one line per place (up to 6 places). For daily, weekly or monthly steps there are also charts of each place's lowest and highest temperature.
- **Home place**: the place a computer or phone uses until it chooses its own location, and the one the hourly updates and backups use. Round Rock is home after upgrading; **Make home** changes it.
- **Stop hourly updates** keeps a place and its weather but stops fetching. **Remove** deletes the place and all its weather (it asks first). The home place cannot be removed.
- **Update every place now** updates them one after another; the progress box names the place it is on.

Upgrading keeps every reading you already have: they become Round Rock's.

### Everything Open-Meteo offers is now collected

Version 1.3.0 asks Open-Meteo for every measurement it publishes for your location, not just temperature, humidity and sunlight. They include:

- feels-like temperature, dew point, wet-bulb temperature and air dryness (VPD)
- temperature at 80, 120 and 180 m
- rain, showers, snowfall, snow depth, chance of precipitation and weather code
- cloud cover (total, low, middle, high), visibility, day or night, and sunshine
- solar radiation (total, direct, diffuse, direct normal, top of atmosphere) and UV index
- wind speed, direction and gusts, at several heights, and air pressure
- water loss from plants and soil (evapotranspiration)
- soil temperature and soil moisture at several depths
- upper-air values such as CAPE

There are also daily summaries. They hold the highest, lowest and average of most of these, plus sunrise, sunset, day length, rain and snow totals and growing degree days. Units are Fahrenheit, mph and inches.

Not every measurement exists for every period. If Open-Meteo does not offer one for old dates, the app notes it (the update log lists them), skips it, and tries again in two weeks.

**Disk use.** Every measurement every hour is about 10 MB per year. Going back to 1940 would make the database huge. So the app keeps *every* hourly measurement only for the most recent years: 3 to start with. Change that with "Years of full hourly detail to keep" under Location and updates. For older years it keeps temperature, humidity and plant light hourly. It keeps the full set as daily summaries for all years. Everything from now on is kept in full.

### Tracked history charts

Under **Tracked history** on the Weather page:

- **Period**: the last 24 hours up to the last 10 years, **Everything logged** (back to 1940 if you loaded it), or **Pick dates** for any From and To date.
- **Choose what to chart**: tick Temperature, Humidity and Light, and as many other measurements as you like (any hourly measurement, plus daily summary values such as UV index highest or growing degree days). Each group has Tick all and Untick all, and two buttons tick every hourly measurement or every daily value. Charting everything over all years can take several seconds. Measurements with the same unit share a chart, up to three per chart. Your choices are remembered on that computer.
- **Use the dates and columns from the table below**: copies the table's From and To dates and its shown columns into the charts.
- The time step grows with the period so long charts stay readable: one point per hour up to 10 days, per day up to 3 years, per week up to 15 years, per month beyond that. Rain, snow, sunshine and water loss are added up over each step; gusts and UV use the highest value; everything else is averaged. For years older than your "full hourly detail" setting, extra measurements come from the daily summaries, and the page says so.

**Section titles stay in view.** On wide screens the title of the section you are scrolling through stays at the top of the screen. **Chart settings stay in view.** The settings bar (period, dates, source, plant range, charts per row, Go to chart, Choose what to chart) sticks to the top of the screen while you scroll through the charts. So you can change it while looking at any chart. **Hide chart settings** folds it to one line (it starts folded on narrow windows and with very large text). **Charts per row** shows 1, 2 or 3 charts side by side, and **Go to chart** jumps to any chart by name.

### The table of everything logged

**All logged weather data** (Weather page) is a table of what is stored: hourly weather, daily summaries, or your own sensor readings. You can:

- pick dates and order
- set how many rows load at a time, from 10 to 1,000
- jump straight to a page by typing its number and pressing Go, or use First page and Last page
- choose which columns to show
- download everything for the chosen dates as a spreadsheet (CSV, all columns)

That computer remembers the rows and columns you chose. "Also chart" under Tracked history draws any one extra measurement.

### Update log

Under **Location and updates** the page says when the last **Load history** ran, and what it brought in. That is the dates covered, the hourly readings and daily summaries, and which measurements Open-Meteo did not offer. It says the same for the last automatic update. "Every update that has run" is the full log, including the hourly automatic ones. Readings collected before this version are shown as "Before logging began".

**Load history** now runs in the background. While it runs, the Weather page shows a progress bar with the percentage. It shows which year it is fetching, how many readings it has saved so far, how long it has been running, and an estimate of the time left. It shows when it last heard from Open-Meteo, so you can tell it is still going. It also says when it is pausing for Open-Meteo's per-minute limit. A small box at the bottom left of every page shows the percentage and time left until it finishes. It takes about half a minute per year of history; 1940 to now takes roughly 40 minutes. It keeps going if you leave the page or close the browser. Pressing it again skips whatever is already stored, so you can stop and resume. The connection to Open-Meteo may drop part-way, with an error such as `UNEXPECTED_EOF_WHILE_READING`, a timeout, or the service being busy. Then the app waits and tries again by itself, up to 4 more times over about 3 minutes. The progress box shows it. Only if all of those fail does the load stop, keeping everything fetched so far. If Open-Meteo's free daily limit is reached it says so; press the button again the next day. If you restart Docker during a load, press it again.

To stop all online lookups, add `PLANTDB_WEATHER: "0"` under `environment:` in `docker-compose.yml` and run `docker compose up -d`.

### Connecting your own sensor

Open **Weather**, then **Connect your sensor**. It shows the address and a private token. Your sensor (or a small script on the device) sends a POST with the header `X-Ingest-Token: <token>` and a JSON body. All fields are optional except that you need at least one measurement:

- `device`: a name for the sensor (for example `porch`)
- `ts`: UTC time like `2026-10-20T14:00:00Z` (default: now)
- `temp_f` or `temp_c`; `humidity` (%)
- `par` (umol/m2/s) or `lux` (converted at 54 lux per PAR)
- `soil_moisture` (%), `soil_temp_f` or `soil_temp_c`, `soil_ph`
- `weight_g`: the weight of the pot on a weighing cell (from 1.35.0; the app shows how it changes as the pot dries)

Send up to 500 readings at once as `{"readings":[ ... ]}`. A reading with an impossible value is refused with an explanation.

From 1.12.0 sensors send to their own port, **8082**. It only takes readings with the token; nothing else of the app answers there. It is shut until you open it to your home network. Put the line `PLANTDB_SENSOR_BIND=0.0.0.0` in the `.env` file next to `docker-compose.yml` and run `docker compose up -d` (from the `plant-database` folder):

- Windows (cmd.exe): `(echo PLANTDB_SENSOR_BIND=0.0.0.0)>>.env` then `docker compose up -d`
- Windows (PowerShell): `Add-Content .env 'PLANTDB_SENSOR_BIND=0.0.0.0'; docker compose up -d`
- bash: `echo 'PLANTDB_SENSOR_BIND=0.0.0.0' >> .env && docker compose up -d`

The sensor then sends to `http://<your PC's Wi-Fi address>:8082/api/readings` ("Opening it to your home network again" shows how to find that address). Try it from the PC (replace `YOURTOKEN`):

Windows (cmd.exe):

```
curl -X POST http://localhost:8082/api/readings -H "X-Ingest-Token: YOURTOKEN" -H "Content-Type: application/json" -d "{\"device\":\"porch\",\"temp_f\":71.2,\"humidity\":58,\"par\":240}"
```

Windows (PowerShell):

```
Invoke-RestMethod -Method Post -Uri http://localhost:8082/api/readings -Headers @{"X-Ingest-Token"="YOURTOKEN"} -ContentType "application/json" -Body '{"device":"porch","temp_f":71.2,"humidity":58,"par":240}'
```

macOS / Linux (bash):

```
curl -X POST http://localhost:8082/api/readings -H "X-Ingest-Token: YOURTOKEN" -H "Content-Type: application/json" -d '{"device":"porch","temp_f":71.2,"humidity":58,"par":240}'
```

The token is the only thing protecting this address (the password option does not apply to it). So keep it private and use **Make a new token** if it leaks. When your sensor is working, choose "My sensor" in Current conditions.

## Your sensors (from 1.35.0)

**Weather → Sensors** (`#/sensors`) shows every sensor that sends readings, one card each, the ones that need a look first. Each card has:

- its newest values in large type: soil moisture, air temperature, humidity, light now, root-zone temperature, soil pH, pot weight
- a small line of the last 24 hours for each, with the lowest and highest of the day
- how much the soil moisture and weight changed since a day before

 Daily light is worked out once a day of light readings is in.

Press **Change name, spot or plant** to give a sensor a name you will recognise. Say where it sits (a room, area or spot from Rooms and spots), and which plant's pot it is in. Once it is in a plant, each value is compared with that plant's ranges, in words with a mark. The marks are **✓ In range**, **↓ Dry**, **↑ Wet**, **Cool**, **Warm**, **Dry air**, **Humid**, **Too dim** and **Too bright**. **! Too cold** means the air is below the plant's damage point. The same card shows under **Water and soil** on the plant's page. A sensor that has sent nothing for longer than its quiet hours (3 to start with) says **Quiet** with a dashed border. The owner can **Forget this sensor** (its readings go too).

- **Today** lists the sensors that need a look or have gone quiet, with a jump button; "Quiet today" says when all are in range.
- **Watering from the sensor:** a sensor in a plant's pot may see the soil moisture jump by 15 points or more within 3 hours. Then the app logs a watering for that plant for the day, once a day, signed "Sensor". So the Today page stops asking. Turn it off per sensor in its window.
- **Notifications:** a new kind, **Sensor alerts**: a dry pot, dangerous cold at a sensor, or a sensor gone quiet, once a day each (Settings → Notifications).

### An ESP32 sensor node with ESPHome

The easiest build is an ESP32 running [ESPHome](https://esphome.io): no code, a short text file. `sensors/esphome-plant-sensor.yaml` in the app folder is ready for these:

- a capacitive soil moisture probe
- an SHT31 air temperature and humidity sensor
- a BH1750 light sensor
- a DS18B20 soil temperature probe
- an HX711 weighing cell under the pot

 Delete the sensors you do not have. It posts one reading every 10 minutes to port 8082.

1. Open port 8082 to your home network (see "Connecting your own sensor" above) and copy the token from Weather → Connect your sensor.
2. Install ESPHome on the PC and start its dashboard (it runs in Docker, like the app):
   - Windows (cmd.exe): `docker run -d --name esphome -p 6052:6052 -v %USERPROFILE%\esphome:/config ghcr.io/esphome/esphome`
   - Windows (PowerShell): `docker run -d --name esphome -p 6052:6052 -v $env:USERPROFILE\esphome:/config ghcr.io/esphome/esphome`
   - bash: `docker run -d --name esphome -p 6052:6052 -v ~/esphome:/config ghcr.io/esphome/esphome`
3. Copy `sensors/esphome-plant-sensor.yaml` into that `esphome` folder, and make `secrets.yaml` next to it with your Wi-Fi name and password, `plantdb_url` (`http://<your PC's Wi-Fi address>:8082/api/readings`) and `plantdb_token`. Change `device` at the top of the file to the name you want to see in the app.
4. Open `http://localhost:6052`, plug the ESP32 into the PC by USB, and press **Install** → **Plug into this computer** (the first flash is over USB; after that, updates go over Wi-Fi).
5. The sensor appears on the Sensors page with its first reading. Name it and put it in its plant.

Calibrate the soil probe once: note its raw voltage in dry air and in a glass of water and put those two numbers in the `calibrate_linear` lines (the file says where).

## Frost dates (from 1.45.0)

How long have you got before the first freeze, and when is the last one usually over? The app answers from Round Rock's own weather history (Load history on the Weather page), not a general table. "Usual" is the middle date of the winters that had such a night. Plan for the earliest date in the fall and the latest in the spring.

- **Weather page, Frost dates in Round Rock, TX:** this winter so far. The usual first and last **frost possible (36°F)**, **freeze (32°F)** and **hard freeze (28°F)**, each with the earliest and latest seen. And a table, one row per winter (first 36°F night, first and last freeze, how many freezing nights and hard freezes, the coldest night). On a phone the rows become boxes.
- **Cold-night checklist, When cold nights usually come:** your plants outside grouped by the temperature that damages them, earliest first, with when that night usually comes. One plant a line with its photo and a link; a long group shows 5 and a **Show the other N plants** button.
- **Back outside, When the cold nights usually end:** the usual last hard freeze, freeze and 36°F night, with the earliest and latest. From January to June how many days to go.
- **Today:** in October and November, until the first freeze, "No freeze yet. The usual first freeze is N days away". In February and March, "The usual last freeze (date) is N days away", with a link to Back outside. Nothing shows without 3 whole winters of history.
