# Feature ideas

One line each, most wanted first. A prototyping session takes the top one that is not already in progress, and marks it "(in progress: proto/<branch>)".

- Search by voice: a button beside every search box (and the V key) that fills the box from what you say, tidies spoken plant codes and opens a plant or page with "open ...", turned into words on this computer by its own Whisper service. (suggested by Claude) (in progress: proto/voice-search)
- Summer heat: an AHS heat-zone style "days above 86°F" count from the weather history, next to the USDA zone on About this plant, for plants that struggle in Texas summers.
- Sensor dashboard for the DIY plant monitor (soil moisture, temperature, light) once hardware is posting to `/api/readings`.

## Done
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
