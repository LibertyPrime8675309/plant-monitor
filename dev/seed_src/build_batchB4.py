"""Batch B4 (draft): more grow light details from Ethan's label photos (November 2026).
- SANSI T8 strip (sansi-t8): label reads 'T8 plant grow light, C21GL-LT01-25W, AC120V, 60Hz, 0.5A, 25W', suitable for damp locations,
  do not use with dimmers, not for totally enclosed luminaires, date 12.2024. Ethan: he has just the one strip, 32 LEDs, 25 W,
  120 V, 0.5 A. Its control box has only an on/off button and a timer button (4, 8 or 12 hours), so it has no brightness steps.
Guarded like plant updates: each field changes only if it still holds the value the batch expects. 1.28.1 lets a batch rename a light.
Run: python3 dev/seed_src/build_batchB4.py"""
import json, os
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
lights_update = [
    {'key': 'sansi-t8', 'note': 'model number, watts and ratings from its label; one strip (batch B4)',
     'set': {'name': ['SANSI 2 ft T8 strip set', 'SANSI 2 ft T8 strip'],
             'kind': ['Strip lights', 'Strip light'],
             'model': [None, 'C21GL-LT01-25W'],
             'watts': [None, 25],
             'power': ['Plugs into an outlet; 6 ft cord. Splash-proof (IP54).',
                       'Plugs into an outlet (120 V AC, 60 Hz, 0.5 A); 6 ft cord. Splash-proof (IP54).'],
             'dimming': [[25, 50, 75, 100], [100]],
             'ppfd_note': ['The maker\'s figures. Claude does not know yet how many strips the set has or their watts.',
                           'The maker\'s figures, for one 25 W strip with 32 LEDs.'],
             'notes': ['', 'The control box has an on/off button and a timer button (4, 8 or 12 hours a day; a red, green or yellow dot shows which). '
                           'There is no brightness button. Do not put it on a dimmer. Rated for damp locations (a covered porch is fine, not direct rain). '
                           'Not for totally enclosed fixtures.']}},
]
b = {'id': 'B4', 'created': '2026-11-03', 'author': "Claude (Ethan's grow light details, Nov 2026)", 'lights_update': lights_update}
json.dump(b, open(os.path.join(REPO, 'app/seed/batches/batchB4.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(lights_update), 'light updates')
