# Prototype: pests that eat plants (proto/browse-risk, PR #109)

**What:** Ethan's plants are being eaten by rabbits, rats and mice (November 11, 2026). Each plant gets a browse risk, High, Some or Low, with the reason in words. Ethan answered the three open questions with yes (November 11), so it also has the following.

1. **Risk set by hand.** The plant field `browse_risk` (enum Low / Moderate / High, optional; on the Edit form under "Pests and diseases", and "Change risk" on the page and the plant's line). Empty means the usual for its kind (from the genus: `BROWSE` in `browse.py`). It saves through the ordinary plant PUT, so it is versioned and audited like any field.
2. **Pests seen**, with pictures as evidence. Table `pest_sightings(plant_code, seen_on, pest, damage, note, photos JSON, created_by, created_at)` (`BROWSE_SCHEMA`, run by `init_db()`). Pest: rabbit, rat, mouse, squirrel, deer, bird, snail or slug, insect, other, not sure. Damage: leaves eaten, stem chewed, flowers or fruit eaten, dug up, droppings or tracks only, other. Evidence: tick pictures already in the plant's record, or add new ones (`POST /api/browse/photo`, saved as `up_<hex>.jpg`, not added to the plant's own pictures). A sighting only accepts pictures that are in the record or were sent that way. `GET/POST /api/browse/sightings`, `DELETE /api/browse/sightings/<id>`; added and removed sightings are in the audit log. The page shows the last 60 days, counted by pest; each plant's line says how often it was eaten and by whom.
3. **Today, in the evening.** From 4 pm (the home's time) a block "Cover tonight" (order 64) lists the plants outside (outdoors or covered porch) that are high risk or were eaten in the last 14 days, with "Done for tonight" (kept on this device for the day).

4. **Sightings raise the risk** (Ethan, November 11: yes). In the last 60 days one sighting makes a plant at least Some risk and three make it High (`RAISE_TO_MODERATE`, `RAISE_TO_HIGH`, `raised_risk()`), even over a risk set by hand: the hand-set value stays stored and is shown ("Raised because it was eaten 3 times..."). It is worked out each time, so it falls back when the sightings are older than 60 days. Nothing is written.
5. **Evening push** (Ethan: yes). Notification kind `cover` ("Cover plants at night", on by default, each person can turn it off), sent by `push_cover()` from `push_loop()`: from 4 pm in each home's time, once a day, the same list as Today. The mock server can fire it (`/mock/push/run {what: 'cover', hour}`).

**Not changed:** nothing is stored for the usual risk; plants added later get it from their genus.

**Files:** `app/plantdb/browse.py`, `app/static/js/browse.js`, `css/browse.css`; one line each in `core.py` (field, enum, schema), `edit.js` (the field in the Edit form), `manifest.json` and `run_checks.py`. Also one line in `push.py` (the kind and the call) and `mock_server.py`; `reach_check.py` now expects six kinds. Tests: `dev/test/unit/test_browse.py`, `dev/test/browse_check.py` (43 checks: the API, the two windows with an uploaded picture, the evening block, viewers, phone width with large text).

**Where the usual data came from:** the photo review in a Claude chat on November 11, 2026, saved in Ethan's Plants project as `claude/garden-pest-resistance-plant-id-2026-11-11.md`, checked against general horticulture knowledge.

**Open questions for Ethan**
1. Should the thresholds be different (now: once = some risk, three times = high, within 60 days)?
2. Evening push is at 4 pm, the same hour as Today's block. Earlier or later?
