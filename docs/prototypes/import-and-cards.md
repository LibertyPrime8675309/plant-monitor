# Previews: updates from a file, and tighter watering cards

Branch `proto/import-and-cards` (November 13, 2026). Pictures for Ethan to choose from. **Not for merging as it is:** the option he
picks is built as a real change on its own branch, and `js/preview.js` and `css/preview.css` go away.

## What it shows

**Item 12 of the November 12 review: plant updates that arrive as a file.** Today a correction to a plant's page travels in an
upgrade batch inside a release, with his plants' details in the public code. His choice (November 13) was "a file you import": Claude
saves a small file on his computer, and a page in the app shows each change to accept or skip. The page is "Updates from Claude"
(`#/updates`, in the Plants menu while the preview is on), three ways:

- **A, every plant on one page** (`"updates": "plant"`): each plant with its picture and its changes, ticked to begin with.
- **B, one plant at a time** (`"updates": "walk"`, `"updstep": 3` for the third plant): like the health walk-through.
- **C, a short list by kind of change** (`"updates": "kind"`): one line a change; corrections, new pages, plants to archive, questions.

`"updstate": "start"` is the page before a file is chosen and `"updstate": "done"` the page after the changes are made. The file in
the pictures is made up (`UPD_FILE` in `preview.js`) to show every kind of change: a correction, one that needs a decision because the
page no longer says what the file expected, a new page with photos, a plant to archive, and a question. "Now" is read from the record
when the page draws. Nothing is changed: the last button only shows what would follow.

**The watering cards on Today, using less of the screen** (Ethan, November 13: "optimize the use of screen space", keeping the
pictures). In all four the code sits beside the name, how late a plant is opens the reason (the "Why" line is gone), and a phone has
one list to go to a spot in place of a button for each.

- **1, one run** (`"water": "flow"`): the same cards and buttons in one run, with a tile where each spot starts.
- **2, boxes** (`"water": "boxes"`): the same cards, each spot still in its box; spots with few plants share a row.
- **3, tick** (`"water": "tick"`, `"ticked": 3` to show three ticked): a card is a picture, the name and how late; press the picture
  to tick it; one bar at the bottom of the screen holds Watered and Still moist for everything ticked.
- **4, spots** (`"water": "spots"`): a spot is a row with its one button and a strip of pictures; the cards open on request.

On a wide screen the cards of 1 and 2 are wider than now (12.5rem), so the two buttons sit side by side and names take fewer lines:
a larger picture then costs no length.

## How to see it

Start the mock server, then in the browser's console:

    localStorage.setItem('plantdb.preview', '{"updates":"plant","water":"tick"}'); location.reload()

and open `#/updates` or Today. `localStorage.removeItem('plantdb.preview')` puts the app back as it was.

The gallery: `python3 dev/test/shots_preview.py OUTDIR` (see its first lines), published from `OUTDIR/gallery`.

## What it changes

Nothing in the database and nothing on the server. One line in `care.js` asks `preview.js` for the watering list when an option is on.

## Measured (November 13)

The Water part of Today, with 45 plants due on four spots (1, 1, 31 and 12 plants: the shape of Ethan's own list that day):

| | 2560 x 1440 monitor at 150% | Phone (384 x 740) |
|---|---|---|
| As it is | 3,901 px | 10,720 px |
| 1, one run | 2,522 px | 9,358 px |
| 2, boxes | 3,340 px | 9,979 px |
| 3, tick | 2,269 px | 7,455 px |
| 4, spots | 1,513 px | 3,043 px |

## Open questions for Ethan

- Which layout for the Updates page, and whether changes start ticked.
- Whether the app should notice a file by itself (a folder shared with Docker) and say so on Today, or only take a file he chooses.
- Which watering option, and whether he wants a picture-size switch remembered on each device.

## To settle when building the real thing

- The file: one `.zip` (the changes as JSON, and any photos) under 30 MB; what it expects to replace is in each change, as in a batch
  (`{field: [old, new]}`), and a plant is named by code and name, or by its photos (`find_plant()`).
- The server reads the file and says what each change would do against the record; applying goes through `apply_changes()` so every
  change is in the page history and the Audit log, signed with the file's name. A file is brought in once.
- In option 3 a pot kept in water has its own care kind (top up, fresh water): the bar logs each ticked plant's own kind.
- The picture tools on this branch (`dev/test/shots_all.py`, `build_gallery.py`, `shots_preview.py`, and the rest) are not on main.
