"""Batch C4 (PLAN.md step 8a, 1.56.0): how each of Ethan's lights holds, and the side table's measurements.

Mounts come from the listings in build_batchA3.py and from Ethan's note of November 9, 2026: the tripod's gooseneck cannot point
straight down; the 2 ft standing light lights sideways from a flat base; the clamp lights need a horizontal edge; the T5 and T8
strips screw under a surface. A number that no listing gives (the tripod's leg spread, the GooingTop's clamp opening) is left
out rather than guessed: the app then says "Not checked" for what it needs. Guarded: a mount is only set where none is."""
import json, os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'app', 'seed', 'batches', 'batchC4.json')
M = {
    'sansi-80w':        {'kind': 'socket', 'points': 'down', 'socket': 'E26'},
    'sansi-30w':        {'kind': 'socket', 'points': 'down', 'socket': 'E26'},
    'sansi-10w':        {'kind': 'socket', 'points': 'down', 'socket': 'E26'},
    'sansi-tripod':     {'kind': 'floor', 'points': 'angled', 'height_lo': 33, 'height_hi': 58},
    'sansi-gooseneck':  {'kind': 'clamp', 'points': 'down', 'grip_in': 2, 'reach_in': 15.8},
    'barrina-standing': {'kind': 'surface', 'points': 'side', 'footprint_in': 5, 'height_hi': 24},
    'gooingtop-clip':   {'kind': 'clamp', 'points': 'down'},
    'barrina-t5':       {'kind': 'under', 'points': 'down', 'length_in': 12},
    'sansi-t8':         {'kind': 'under', 'points': 'down', 'length_in': 24},
    'sansi-pot-clip':   {'kind': 'clamp', 'points': 'down', 'grip_in': 0.8, 'reach_in': 12.8, 'pot_rim': True},
    'disk-light':       {'kind': 'none', 'points': 'down'},
}
batch = {
    'id': 'C4', 'created': '2026-11-10', 'author': "Claude (the listings, and Ethan's note on mounting, Nov 9, 2026)",
    'lights_update': [{'key': k, 'set': {'mount': [None, m]}, 'note': 'how it holds (step 8)'} for k, m in M.items()],
    'place_sheets': [
        {'room': 'Downstairs Living Room', 'name': 'Side Table', 'sheet': {'levels': 1, 'top': 'nothing',
         'notes': 'One level with open space above (Ethan, November 9): a strip has nowhere to be fixed over it.'}},
        {'room': 'Downstairs Living Room', 'name': 'Tall Brown Shelf', 'sheet': {
         'notes': 'Two or more levels (Ethan, November 9). The levels take a 1 ft T5 strip but are not wide enough for the 2 ft T8. Measurements to come.'}},
        {'room': 'Downstairs Living Room', 'name': 'Short Brown Shelf', 'sheet': {'notes': 'Two or more levels (Ethan, November 9). Measurements to come.'}},
    ],
}
json.dump(batch, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('wrote', OUT)
