"""Batch C7 (1.56.0): the measurements of every shelf and table plants stand on, from Ethan (November 10, 2026).

Inches. "Height" is the clear height of a level (to the underside of the one above); every top level has open air above it. The
tall brown shelf's levels differ, so it gets a height for each lower level from the bottom (gaps_in); its two middle levels can be
moved up or down or taken out, which the notes say. Guarded field by field (place_sheets_update): a value is set only where the
shelf still holds what batch C4 left (its placeholder notes) or nothing, so anything Ethan has typed himself stays. The pallet
shelf is outside; it is found as the one outside spot with "pallet" in its name, and left alone if there is not exactly one."""
import json, os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'app', 'seed', 'batches', 'batchC7.json')
ROOM = 'Downstairs Living Room'
C4_SIDE = 'One level with open space above (Ethan, November 9): a strip has nowhere to be fixed over it.'
C4_TALL = 'Two or more levels (Ethan, November 9). The levels take a 1 ft T5 strip but are not wide enough for the 2 ft T8. Measurements to come.'
C4_SHORT = 'Two or more levels (Ethan, November 9). Measurements to come.'
def shelf(levels, width, depth, gap=None, gaps=None, notes=None, old_notes=None, old_levels=None, old_top=None):
    s = {'levels': [old_levels, levels], 'width_in': [None, width], 'depth_in': [None, depth], 'top': [old_top, 'nothing']}
    if gap: s['gap_in'] = [None, gap]
    if gaps: s['gaps_in'] = [None, gaps]
    if notes: s['notes'] = [old_notes, notes]
    return s
U = [
    {'room': ROOM, 'name': 'Tall Brown Shelf', 'set': shelf(4, 22, 11, gaps=[23, 13, 27], old_notes=C4_TALL,
        notes='Four levels; the two middle ones can be moved up or down, or taken out (Ethan, November 10). The levels take a 1 ft T5 strip but are not wide enough for the 2 ft T8.')},
    {'room': ROOM, 'name': 'Short Brown Shelf', 'set': shelf(2, 28, 11, gap=25, old_notes=C4_SHORT, notes='Two levels (Ethan, November 10).')},
    {'room': ROOM, 'name': 'Tall Black Shelf', 'set': shelf(5, 23, 9, gap=11)},
    {'room': ROOM, 'name': 'Large Brown Hutch', 'aka': ['Hutch', 'Brown hutch'], 'set': shelf(2, 44, 13, gap=24)},
    {'room': ROOM, 'name': 'Side Table', 'set': {'levels': [1, 1], 'width_in': [None, 26], 'depth_in': [None, 9], 'top': ['nothing', 'nothing'], 'notes': [C4_SIDE, C4_SIDE]}},
    {'side': 'out', 'contains': 'pallet', 'set': shelf(3, 39, 12, gap=14, notes='Three levels, outside (Ethan, November 10).')},
]
batch = {'id': 'C7', 'created': '2026-11-10', 'author': "Ethan's measurements of his shelves and tables (November 10, 2026)", 'place_sheets_update': U}
json.dump(batch, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('wrote', OUT)
