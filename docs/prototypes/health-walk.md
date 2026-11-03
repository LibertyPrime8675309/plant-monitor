# Prototype: Health walk-through

Branch: `proto/health-walk`

## What it does and why
Each plant has a health rating (Good, Fair, Poor or Critical). With about 85 plants, it's easy for the ratings to go stale, and there was no quick way to go round and check them. The health walk-through lets you go round your plants one at a time, on a phone in the garden or at the computer, and say how each one looks today.

- **Today page:** a new line near the top says how many plants haven't been looked over for 14 days or more, with a **Health walk-through** button.
- **Choosing the plants** (`#/checkup`). Three rows of big buttons:
  - **Which plants:** the due ones, or all of them.
  - **Where:** everywhere, or one location (Outdoors, Covered porch...).
  - **In what order:** longest since looked over first, worst health first, or by plant code.
  - It says how many plants the walk will have as you choose, and remembers your choices.
  - Below that, a folded list of the plants that are due, with links.
- **One plant at a time:**
  - "Plant 3 of 28" and a progress bar.
  - Its main photo, its code and name, where it is, its health rating now, and when it was last looked over.
  - Its health notes, folded away until you open them.
  - **How does it look now?** Four big buttons. The current rating is already chosen and says "(as before)".
  - **Anything you noticed? (optional)** for a short note.
  - The main button says what it will do: **Looks the same: save and go on**, or **Save "Poor" and go on** when you choose another rating.
  - **Skip this plant**, **Back to the previous plant**, and **Stop and see what you've done**.
  - After each save, the keyboard focus goes to the next plant's name, so a screen reader reads it.
- **What gets saved:**
  - **Looks the same:** a "Looked over" entry in the plant's care log, with your note.
  - **A new rating:** saved on the plant page (it shows in the change log and on the plant timeline like any edit), plus a "Looked over" entry saying "Health Good to Poor" and your note.
  - If someone changed the plant while you were walking round, nothing is written over it: you're told its rating now, and you choose again.
- **At the end, or when you stop:** how many you looked over, which have new ratings, which you skipped, and **Carry on** if you stopped part-way.
- A health rating changed on the Edit page also counts as looking the plant over. Ratings set by Claude's upgrade batches don't.
- People with view-only access can see the list of due plants, but can't start a walk.

## How it looks
Choosing the plants, on a laptop:

![Choosing the plants](health-walk/laptop-choose.png)

One plant, on a laptop. (The sandbox has no plant photos, so the photo is blank here; on your PC it shows the plant's main photo.)

![One plant](health-walk/laptop-plant.png)

On a phone with the largest text, dark and light:

![Phone, dark, largest text](health-walk/phone-dark-plant.png) ![Phone, light](health-walk/phone-light-plant.png)

After stopping part-way:

![Walk-through paused](health-walk/laptop-done.png)

The new line on the Today page, on a phone:

![Today page](health-walk/phone-today.png)

## How to try it
1. Start the app with `dev/test/mock_server.py` and a fresh data folder under `dev/tmp/`.
2. Open Today and press **Health walk-through**, or go to `#/checkup`.
3. `python3 dev/test/checkup_check.py` runs the focused checks (choosing, saving, skipping, going back, a change made elsewhere, stopping and carrying on, the care log, phone widths).

## What it changes in your database
Nothing in its structure: no new tables or columns. It adds a new kind of care log entry, "Looked over", and new health ratings are ordinary edits to the plant page. Nothing changes until you use it.

## Open questions for Ethan
1. Is **14 days** right for a plant to be due again? It could be a setting, or different for indoor and outdoor plants.
2. Should the note you type also be added to the plant's **Health summary**, or is the care log enough?
3. Would you like a **Take a photo** button on each plant during the walk, so the timeline gets a new photo at the same time?
4. Should **Poor** and **Critical** plants be due sooner (say every 7 days)?
