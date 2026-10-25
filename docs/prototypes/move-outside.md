# Prototype: Back outside (spring list)

Branch `proto/move-outside`. Idea from `docs/IDEAS.md`: when the nights stay above each indoor plant's comfortable low, list the plants that can go back out.

## What it does and why
Over winter many plants are inside. In spring each one can go back out at a different time: a fig is safe long before a dieffenbachia. This page checks every plant that is inside against its own temperatures and the 7-day forecast, so Ethan does not have to compare numbers plant by plant.

- **New page, Back outside** (`#/outside`), under Winter plan. It is linked from the "Already inside" list on the Winter plan page ("Which can go back outside?").
- **Who is listed:** active plants whose Location is Indoors or Garage or shed.
- **Each plant gets one of four labels** (words in a box, not colour alone):
  - **Ready:** every night in the forecast is at or above its ideal low (`temp_ideal_low`).
  - **Safe, but cool:** no night comes within 3°F (`FROST_MARGIN`, the same as the cold-night checklist) of its damage point (`temp_damage_below`), but some nights are cooler than it likes.
  - **Too early:** the forecast is safe, but the weather history says colder nights usually still come. In spring: today is before the date after which, in most years, nights stayed above its safe temperature. In autumn: within a week of, or after, the usual first night below it.
  - **Not yet:** a night in the forecast is too cold. It says which night and how cold.
- **The usual date**, when there are 3 years or more of weather history: "In most of the last 6 years, the nights stayed above 53°F from April 5 on (in the latest year, from April 9)". Without history the page says how to load it.
- **Buttons:** "Moved to the porch" (Location becomes Covered porch, the gentle first step) and "Moved outside" (Outdoors). They use the existing Location change, so the audit log, timeline and cold-night checklist all follow. Focus moves to the next plant's button. Hidden from viewers.
- **The next 7 nights** as a small table, and a short "Going back out" section: ease plants in from shade, pots dry faster outside, start feeding with new growth.
- **Today page, in spring only:** a note "5 plants inside can go back outside" with a link, when any are Ready or Safe.

## How it looks
Made-up test data: today is March 20, coldest forecast night 50°F, six years of made-up history. The frost banner at the top is from the same made-up forecast.

![The list on a laptop](move-outside/1-the-list.jpg)

![Phone, dark theme, larger text](move-outside/2-phone-dark.jpg) ![Phone, light theme](move-outside/3-phone-light.jpg)

![The note on the Today page in spring](move-outside/4-today-note.jpg)

## How to try it
- `python3 dev/test/outside_check.py` runs its own copy of the app with the spring test data, checks the levels and the page (laptop and phone, light and dark, keyboard), and saves screenshots to `dev/tmp/shots/outside-*.png`.
- With the mock server, move a few plants to Indoors and open `#/outside`. In October everything shows the autumn note, and only very cold-hardy plants would be Safe.

## Changes to the database
None. It only reads plants, the forecast and the daily weather history. The buttons change a plant's Location through the existing `POST /api/plants/<code>/site`.

## For Claude: where the code is
- `server.py`: a block before "getting plants ready to come inside": `BO_LEVELS`, `bo_daily_lows()` (cached 6 h per place), `bo_md()`, `bo_usual(lows, t)`, `outside_report(c)` and `GET /api/outside`.
- `app.js`: a block after `viewWinter()` (`loadOutside()`, `boRow()`, `viewOutside()`, `boMove()`, the Today-page MutationObserver); one line each in `route()` and the nav mapping; the link in the Winter plan's "Already inside"; `Object.assign(acts, {boporch, boout})` after `changeActs`.
- `style.css`: its own block after the 1.8.0 cold-night styles, including its viewer rule.
- `dev/test/smoke.py` now also opens `#/outside`.

## Open questions for Ethan
1. **Which low should "Ready" use?** It uses each plant's ideal low. For tropical plants that is 65°F, which in Round Rock is late May. "Safe, but cool" already lets them out once nights stay 3°F above their damage point. Is that the right split, or should Ready be, say, 10°F above the damage point?
2. **Porch first?** "Moved to the porch" is the main button because leaves grown indoors scorch in full sun. Would you like a reminder a week later to move them on to their summer spot?
3. **Today page note:** only in spring (January to June). Is that useful, or would you rather it only lived on the Winter plan page?
4. **Plants in the garage or shed** are included. Should they be left out?
