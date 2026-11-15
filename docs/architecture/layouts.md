# Room and shelf layouts (prototype, `proto/layouts`)

Notes for the next session. What it is for, with pictures and Ethan's answers, is in `docs/prototypes/layouts.md`; how to use it is in `manual/layouts.md`.

## The model
Everything on a layout is a box in inches: a place (`x` from the left, `y` from the back, `z` off the floor: its left, back, bottom corner) and a size (`w`, `d`, `h`), with shape `box` or `round` (a circle from above). Kinds: `plant`, `light`, `shelf`, `other`, `zone` (an area to keep clear). The top view draws x and y, the front view x and z. A view in three dimensions needs nothing more stored.

## Server: `app/plantdb/layouts.py` (`ORDER = 66`)
- Tables `layouts` and `layout_items`, made on first use by `layout_tables(c)` (which also adds `hours` and `dim_pct` to a table made before them). Nothing in `init_db()`: when the prototype becomes a release, the tables move there.
- `layout_start(c, area, spot)`: what a layout of a place starts with. A shelf: its width and depth, its levels as locked boards 0.75 in thick (`layout_boards`, from the measurements `levels` and `gaps_in` or `gap_in`), and 24 in of headroom. A room: 144 by 120 in (ceiling from its measurements, else 96) with its spots as blocks along the back wall.
- `layout_item_dict(c, it)`: a thing as the page gets it. What only the record knows is added here:
  - a plant: `page_h` (its page's `height_in`; `h` is that when the page has one), `need` (`plant_need`), `rec` and `rec_label` (where the record has it; a place is a `pid`: a spot's id, or minus an area's id);
  - a light: `pts` (its maker's figures), `dims`, `hours`, `dim_pct`, `near_in`, `far_in`, `owned`;
  - one of the record's shelves: `place`, and `levels` (`layout_levels`: `[{n, name, z, room}]`, the height of each level's top above the shelf's foot and the clear height above it) with `board_in`.
- Routes: `GET/POST /api/layouts`, `GET/PUT/DELETE /api/layouts/<id>`, `POST /api/layouts/<id>/items`, `PUT/DELETE /api/layouts/items/<id>`, `POST /api/layouts/<id>/record`.
- **What a layout changes in the record**, both through `apply_changes()` (a version, History, the home limit):
  - a plant's `height_in`, when the item PUT carries `h` (`layout_plant_height`; `page_h` in the body says what the page is to say instead, which Undo uses, and `null` takes the height off the page);
  - a plant's home, area and spot, in `layout_record` (`{moves: [{plant, place}]}`; every move is checked before any is made).
- A layout belongs to its place's home (`layout_home_check`). `test_home_limit.py` tries all five routes, and a height and a move made through a layout for a plant at another home.

## Page: `app/static/js/layouts.js`, `app/static/css/layouts.css`
State is `LY`; the drawings are SVG; one `addFeature()` call adds the page, the buttons on Rooms and spots and the line on a plant's page.

- **`lyFindings(L)`** is the one place that decides every mark. Hard: `outside`, `overlap`. Soft: `tight`, `nearlight`, `zone`, `floating`, `count`, and the light kinds `toodim`, `dim`, `bright`, `toobright` (`lyIsLv`). It returns the list with the light Map on it (`F.light`).
- **Shelves with levels.** A shelf item with `levels` is not solid: its boards are. `lySolids(b)` gives a thing's solid parts, `lySurf(b)` the places on it to stand, `lyRoom(t, b)` the room above a thing, and `lyUp(a, b)` the gap between the nearest solid parts of two things. `lyUnder`, `lyOver`, `lyFree`, `lyPlace`, `lyStops` and the light's "something in the way" all go through these, so a plant can stand on a level inside a block, be too tall for it, or be lit through its open side.
- **Landing.** `lyLand(L, it, was)` runs after a sideways move (a drag or the arrow keys in the top view, a typed place): a thing that rested on something stays at its height while still over it, goes onto the shelf or thing now under its middle (the lowest level it fits on that is free), or down to the floor. A thing in the air keeps its height. `lyPutOn(L, it, q)` puts a thing on one chosen surface: "Stands on" lists every shelf and level (`lyStandOpts`).
- **`lyLight(L)`**: each plant's daily light from the drawn lights. `lyLightOn` takes the light from a light's underside if it hangs and from its top if it stands, reads its figure at the straight-line distance to the plant's top (`lyPar` is `lights.py`'s `_loglog`), multiplies by the square of (how far below over how far away), and by the light's hours and brightness. A board between shuts it out. `lyVerdict` is `light_verdict`. A plant is `reached` at 1 mol/m² a day or straight under a light that is on; only then does it get a verdict, a mark and a sign (`lyLvAt`, `.ly-lvb`).
- **The record.** `lyRecTo(L, it)` says where the drawing puts a plant; `lyRecList` the plants the record has elsewhere; action `lyrec` moves them.
- **Undo and Redo.** `LY.undo` and `LY.redo` hold `{label, short, undo, redo}`. `lyUndoPush` and `lyCommit` add one and empty `LY.redo`. A thing that is taken off and put back gets a new id: `LY.ids` maps the old to the new and `lyCur(id)` follows it, so older entries still find the thing. Ctrl+Z, Ctrl+Y and Ctrl+Shift+Z are heard by the whole page except in a box being typed in.
- **Saving.** `lyCommit` draws, keeps the change for Undo and sends it (`lySaveItem`, chained on `LY.q`). `lyset` reads a box's value before it waits for earlier saves. A failed save shows the layout as it is saved (`lyNotSaved`).
- **Sizes on screen.** `lyMeasure()` sets each view's scale and the arrangement (`one`, `stack`, `pair`, `tall`). On a shelf unit the top view shows one level (`lyLevelNow`).

## Checks
- `dev/test/unit/test_layouts.py` and the layout cases in `test_home_limit.py`.
- `dev/test/layouts_check.py` (in `run_checks.py` as `layouts`; it takes a base address): the geometry, the light, landing and the record are each asked directly with made-up things, then tried on the page; a viewer; a phone in the dark theme at the largest text.
