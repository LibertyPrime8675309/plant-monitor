"""Batch B2 (draft): Ethan's grow light model numbers and specs, November 1, 2026 onward.
- Barrina standing light (barrina-standing): label photo reads 'Barrina LED GROW LIGHT, T10F20, 100-277VAC 50/60Hz, 20W, Full spectrum',
  ETL listed (Intertek 5001217). Ethan confirmed model T10F20, 100-277 V, 20 W.
Guarded like plant updates: each field changes only if it still holds the value the batch expects.
Run: python3 dev/seed_src/build_batchB2.py"""
import json, os
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
lights_update = [
    {'key': 'barrina-standing', 'note': 'model number from its label (batch B2)',
     'set': {'model': [None, 'T10F20'],
             'power': ['Plugs into an outlet; 4.9 ft cord with an on/off switch',
                       'Plugs into an outlet (100-277 V AC, 50/60 Hz); 4.9 ft cord with an on/off switch']}},
]
b = {'id': 'B2', 'created': '2026-11-01', 'author': "Claude (Ethan's grow light details, Nov 2026)", 'lights_update': lights_update}
json.dump(b, open(os.path.join(REPO, 'app/seed/batches/batchB2.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(lights_update), 'light updates')
