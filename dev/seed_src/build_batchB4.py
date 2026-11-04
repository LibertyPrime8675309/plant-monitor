"""Batch B4 (draft): more grow light details from Ethan's label photos (November 2026).
- SANSI T8 strip (sansi-t8): label reads 'T8 plant grow light, C21GL-LT01-25W, AC120V, 60Hz, 0.5A, 25W', suitable for damp locations,
  do not use with dimmers, not for totally enclosed luminaires, date 12.2024. Ethan: he has just the one strip, 32 LEDs, 25 W,
  120 V, 0.5 A. Its control box has a power button and a timer button (4, 8 or 12 hours). Ethan: the power button also steps the
  brightness (low, medium, high, full; nothing shows which), and holding it down turns the strip off.
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
             'ppfd_note': ['The maker\'s figures. Claude does not know yet how many strips the set has or their watts.',
                           'The maker\'s figures, for one 25 W strip with 32 LEDs.'],
             'notes': ['', 'Press the power button to step the brightness: low, medium, high, full (nothing shows which step it is on). '
                           'Press and hold the power button until the LEDs go out to turn it off. The timer button sets 4, 8 or 12 hours a day '
                           '(a red, green or yellow dot shows which). Do not put it on a dimmer. Rated for damp locations (a covered porch is fine, not direct rain). '
                           'Not for totally enclosed fixtures.']}},
]
updates = [
    {'code': 'P-036', 'name': 'Young shrub with toothed leaves (not stevia)', 'note': 'Ethan: the stems are round (batch B4)',
     'set': {'id_basis': ['Thin, woody brown stems with opposite pairs of light-green leaves that narrow to the base and are coarsely toothed toward the tip. It was taken for stevia, but the leaves have no sweetness at all (taste test, October 23), so it is not stevia. A square stem would point to the mint family (salvia); a round one to a hydrangea cutting or a eupatorium.',
                          'Thin, woody brown stems with opposite pairs of light-green leaves that narrow to the base and are coarsely toothed toward the tip. It was taken for stevia, but the leaves have no sweetness at all (taste test, October 23), so it is not stevia. The stems are round (Ethan, November 3), so it is not in the mint family (salvia and mint have square stems). That leaves a hydrangea cutting, a eupatorium or ageratina, or a chrysanthemum cutting.'],
             'id_alternatives': ['Hydrangea cutting\nSalvia (mint family: square stems, scented leaves)\nEupatorium or Ageratina (boneset, snakeroot)\nChrysanthemum cutting',
                                 'Hydrangea cutting\nEupatorium or Ageratina (boneset, snakeroot)\nChrysanthemum cutting'],
             'id_improve': ['Roll the stem between your fingers: square or round?\nCrush a leaf: does it smell of sage, mint, or nothing?\nA flower\nWhere the cutting or seed came from',
                            'Crush a leaf: does it smell of anything (sharp and herby like a chrysanthemum, or nothing)?\nA flower\nWhere the cutting or seed came from']}},
]
requests_done = [{'key': 'p036-stem-smell', 'answer': 'Round stems (Ethan, November 3). The smell is asked again on its own.'}]
requests_add = [{'key': 'p036-smell', 'code': 'P-036', 'name': 'Young shrub with toothed leaves (not stevia)',
                 'text': 'Crush a leaf between your fingers: does it smell of anything? (Sharp and herby, like a chrysanthemum, or of nothing at all.)'}]
b = {'id': 'B4', 'created': '2026-11-03', 'author': "Claude (Ethan's grow light details, Nov 2026)", 'lights_update': lights_update, 'updates': updates, 'requests_done': requests_done, 'requests_add': requests_add}
json.dump(b, open(os.path.join(REPO, 'app/seed/batches/batchB4.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(lights_update), 'light updates')
