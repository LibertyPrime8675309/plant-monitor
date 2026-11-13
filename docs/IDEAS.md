# Feature ideas

One line each, most wanted first. A prototyping session takes the top one that is not already in progress, and marks it "(in progress: proto/<branch>)".

**Building work comes first (November 7, 2026).** `PLAN.md` sets out seven steps that take the app from one house to many sites. Steps 1 to 3 (the shape, a registry for features, images built on GitHub) come before any new feature, including the repotting plan and new requests made in the meantime; only fixes to what has shipped go out until they are done. Steps 1 to 3 shipped with 1.46.0 (November 8, 2026); prototyping may resume, the new way (`PROTOTYPING.md`, "Register, don't wrap"), while steps 4 to 6 are built.



## Asked for by Ethan, waiting to be built
- **Seed lots and seed treatment (asked for November 12, 2026).** Ethan has many seeds, such as acorns from trees, that need cold stratification or scarification before they germinate.
  - **A seed lot is its own record**, not a field on a plant: species, the parent plant or tree it came from (a plant of his, or a find with a place), when and where it was collected, how many, photos, and a float or cut test with the result. When seeds sprout, the lot makes plant records that link back to it, and the lot keeps its sown and germinated counts.
  - **A treatment plan is an ordered list of stages**, each with a kind (soak, warm, cold-moist, scarify by nicking, sandpaper or hot water, light), a length in days and a temperature range. One stage covers a plain stratification; several cover warm then cold. Today gets a block with "Seed lots to check" and "stratification ends in N days", with the usual push reminder and offline use. Starting points come from species facts (below), and every start is editable.
  - **It joins the Library like the other facts.** Pretreatment for a species or genus is `facts` rows (new fields in `FACT_FIELDS`, a "Seeds" group on the species page, with source, confidence and the propose/accept review of 1.54.0), keyed by `facts_keys()`. Good starting values: red oak group acorns about 30 to 90 days cold-moist at 34 to 41°F; white oak group and live oak need none and sprout in autumn; acorns must not dry out. Mark `mark_owned()` species with "you have seed" and let the Library filter on it. Mushrooms get none of this.
  - **It joins Identify through the example photos.** A seed lot's photos can be saved as `id_examples` ('yes', with its species) so the picture checker learns what his acorns look like. Tag each example with what it shows (seed, leaf, whole plant) and compare like with like, so seed pictures never pull a leaf photo toward the seed's species. Add an "A seed or fruit" choice to Identify that asks Pl@ntNet for the `fruit` organ and shows the genus first, since acorns are hard to name to species from one picture.
  - **Monitoring uses what exists.** Give the stratification fridge and the heat-mat shelf their own spots in the sensor dashboard (1.35.0) with their own limits (fridge alert above 45°F or below 31°F, mat above 85°F). Count a stratification day only when the fridge probe was in range, and show "37 of 60 days counted". The thermostat that switches the heat mat stays on the device (a plug-in thermostat or ESPHome), never in the app, so it works when the PC is off. The app only shows and alerts.
  - **Build order:** (1) seed lots, stages, Today block and plant links; (2) the Library facts and the Identify examples; (3) the fridge and mat spots with day counting. Keep to the Cuttings prototype's pattern for propagation records so the two sit side by side.

## Done
1.45.0 (November 7, 2026, pull request #65): Frost dates (the usual first and last 36°F, freeze and hard freeze from the weather history, on Weather, the Cold-night checklist, Back outside and Today).
1.43.0 and 1.44.0 (November 6 and 7, 2026, pull requests #41, #44, #47 and #58): Plant-sitter sheet, Health walk-through, Search by voice (on this computer, with Whisper; Speak a note too) and Turn the pots.
1.50.0 (November 9, 2026, pull request #70 rebuilt on the registry): Repotting plan.
1.34.0 to 1.36.0 (November 4 and 5, 2026, pull requests #51, #52 and #53): Summer heat (the AHS heat zone from the weather history, and a verdict per plant on About this plant) and Your sensors (the sensor dashboard).
1.19.0 (October 28, 2026, pull requests #23 and #26): Undo right after a quick care button, and large-print care cards for a plant or a whole group.
1.18.0 and 1.18.1 (October 26 to 28, 2026, pull request #25): Identify a plant with the camera (BioCLIP 2.5 on Ethan's PC, with Pl@ntNet and Claude as second opinions) and the plant library; the top menu fixed for iPads.
1.16.2 and 1.17.x (October 26, 2026, pull requests #22 and #24): Show, Location and eight more filters on the Plants page, and Safety for pets.
1.16.0 (October 25, 2026): groups of plants. Smart and hand-picked groups, suggestions, filter and sort by group, what suits a whole group, and care, moving and setting changes for a whole group with a preview and undo.
October 25, 2026, pull requests #18 and #13: Back outside (a spring list of plants that can go back out, from each plant's temperatures and the forecast) and a calendar of feeding days and cold nights to subscribe to.
1.14.1 (October 25, 2026, pull request #19): swipe between plants on phones, and every part of a plant page in the section menu and the row of section buttons.
1.14.0 (October 25, 2026, pull request #17): About this plant. Classification, mature size, hardiness zones with the local zone, native range, conservation status, flowers, fruit, dangers and propagation for every plant, with linked sources.

1.13.0 (October 24, 2026, pull request #16): grow lights. A light library from Ethan's photos, light spots, a suggested layout matching plants to lights by daily light, and a step-down plan from outdoor to indoor light.

Merged into 1.8.0 (October 23, 2026):
- Frost alert: when the forecast drops below a plant's damage point, show a banner listing the outdoor plants to move or cover, with "Moved indoors" buttons.
- Watering log and reminders per plant, alongside the fertilizer calendar (when last watered, when next due, based on the plant's water notes and the weather), with a "Today" list of jobs and big one-tap buttons for use in the garden after scanning a label.
- Photo add-on releases: ship new plant photos in a separate zip, so a release with many photos stays under the 30 MB limit for saving files to Ethan's PC.
- Read aloud and keyboard shortcuts: a "Read aloud" button on each section of a plant page (the browser's built-in voices, adjustable speed), and keys for previous / next plant, search and help.
- Plant timeline: each plant's photos side by side over time, with health changes, moves, feedings and answers in one dated list, to see whether a struggling plant is recovering.
- "Copy my answers for Claude": one button that gathers every request answered since last time into a message ready to paste into the chat.
- Photo check: when a photo is added, check it in the browser and say in plain words if it looks too dark, too bright or blurry, with "Use it anyway" and "Take another", so the photos sent for identification are usable.
- Plant page in two columns: on a laptop with the On this page menu open, the sticky row of section buttons wraps to three or four lines and covers much of the right-hand column. Hide that row while the menu is open (the menu lists the same sections), or let it fold.
- Fix: phones with large text (no sideways scrolling, the menu bar scrolls away).

Asked for by Ethan and built in 1.9.0:
- Getting plants ready to come inside: ten pest methods rated per plant, with steps, logging, second-round reminders and keep-apart dates.

## Suggested by Claude, waiting for review
- Health walk-through: go round the plants one at a time on a phone, with big buttons to say each one looks the same or has a new health rating, and a list of plants not looked over for two weeks. (suggested by Claude) (in progress: proto/health-walk)
