# Swipe between plants, and a complete section menu (1.14.1)

Asked for by Ethan on October 25, 2026, with two phone screenshots:
- **Swipe.** He wanted to change plant pages without scrolling to the top for the Previous and Next buttons.
- **Section menu.** The card at the top of a plant page (code, name, location, aliases) was not in the "On this page" menu. He asked for it, and for sections added later, to be included.

## What it does
- **Swipe left** for the next plant and **swipe right** for the previous one, following the same filters and sort as the buttons.
  - A label names the plant that is coming, and turns solid with "Let go to open it" when the swipe is far enough.
  - Nothing happens for:
    - vertical scrolling, short nudges or slow drags;
    - swipes from the screen edges (Back on Android and iOS);
    - swipes that start on form fields, menus, dialogs, charts, the main photo, thumbnails, or anything that scrolls sideways.
  - It can be turned off in Display ("Swipe between plants").
- **The menu** now has "Photos" and "Name and details". The jump row (the buttons at the top of the details half) had a fixed list that had fallen behind: it was missing Coming inside, Notes and Timeline. It is now built from the same list as the menu.

## Screenshots
- `dev/tmp/shots/swipe-1-menu.png`: the menu, after choosing Name and details.
- `dev/tmp/shots/swipe-2-hint.png`: the label mid-swipe.

## Tests
`dev/test/swipe_check.py` (17 checks) uses real touch events through Chrome's DevTools protocol.
