# Prototype: pests that eat plants (proto/browse-risk, PR #109)

**What:** Ethan's plants are being eaten by rabbits, rats and mice (November 11, 2026). Each plant gets a browse risk, High, Some or Low, with the reason in words. Ethan answered the three open questions with yes (November 11), so it also has the following.

1. **Risk set by hand.** The plant field `browse_risk` (enum Low / Moderate / High, optional; on the Edit form under "Pests and diseases", and "Change risk" on the page and the plant's line). Empty means the usual for its kind (from the genus: `BROWSE` in `browse.py`). It saves through the ordinary plant PUT, so it is versioned and audited like any field.
2. **Pests seen**, with pictures as evidence. Table `pest_sightings(plant_code, seen_on, pest, damage, note, photos JSON, created_by, created_at)` (`BROWSE_SCHEMA`, run by `init_db()`). Pest: rabbit, rat, mouse, squirrel, deer, bird, snail or slug, insect, other, not sure. Damage: leaves eaten, stem chewed, flowers or fruit eaten, dug up, droppings or tracks only, other. Evidence: tick pictures already in the plant's record, or add new ones (`POST /api/browse/photo`, saved as `up_<hex>.jpg`, not added to the plant's own pictures). A sighting only accepts pictures that are in the record or were sent that way. `GET/POST /api/browse/sightings`, `DELETE /api/browse/sightings/<id>`; added and removed sightings are in the audit log. The page shows the last 60 days, counted by pest; each plant's line says how often it was eaten and by whom.
3. **Today, in the evening.** From 4 pm (the home's time) a block "Cover tonight" (order 66) lists the plants outside (outdoors or covered porch) that are high risk or were eaten in the last 14 days, with "Done for tonight" (kept on this device for the day).

**Not changed:** nothing is stored for the usual risk; plants added later get it from their genus.

**Files:** `app/plantdb/browse.py`, `app/static/js/browse.js`, `css/browse.css`; one line each in `core.py` (field, enum, schema), `edit.js` (the field in the Edit form), `manifest.json` and `run_checks.py`. Tests: `dev/test/unit/test_browse.py`, `dev/test/browse_check.py` (35 checks: the API, the two windows with an uploaded picture, the evening block, viewers, phone width with large text).

**Where the usual data came from:** the photo review in a Claude chat on November 11, 2026, saved in Ethan's Plants project as `claude/garden-pest-resistance-plant-id-2026-11-11.md`, checked against general horticulture knowledge.

**Open questions for Ethan**
1. Should a push notification go out in the evening too (the app has push per account), not only the Today block?
2. A sighting could count towards the risk itself (a plant eaten three times becomes High). Wanted, or keep the risk in your hands?
3. Still not in the top bar (the row would wrap): fine?
