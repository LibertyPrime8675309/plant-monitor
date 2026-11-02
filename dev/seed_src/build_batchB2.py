"""Batch B2 (draft): Ethan's grow light model numbers and specs, November 1, 2026 onward.
- Barrina standing light (barrina-standing): label photo reads 'Barrina LED GROW LIGHT, T10F20, 100-277VAC 50/60Hz, 20W, Full spectrum',
  ETL listed (Intertek 5001217). Ethan confirmed model T10F20, 100-277 V, 20 W.
- SANSI 80 W folding bulb (sansi-80w), the 4-arm light: label reads 'SANSI LED Wing Grow Light, C21FS-BE26, 80W, AC 120V, 60Hz, 1.1A,
  4000K. Suitable for damp locations. Not for use in totally enclosed luminaires.'
- SANSI pot clip light (sansi-pot-clip): label and manual read 'C23ZW013-T0005A27, 120Vac, 60Hz, 5W, 0.05A'; input AC 120 V 60 Hz
  (adapter), DC 5 V 1 A (lamp); full spectrum, 4 brightness levels, 3/6/12 hour timer, 120 degree beam, 25,000 hours,
  works at 14-104 F; indoor damp locations; pot rim suggested within 0.4 in (1 cm). Ethan confirmed model, 120 V, 0.05 A, 5 W.
- SANSI 10 W bulbs (sansi-10w): bulb and box read 'C21GL-GE26-10W, AC120V/60Hz/0.2A/10W/E26, Date: 01.2026'; beam 60 degrees,
  not dimmable, full spectrum; suitable for damp locations; do not use with dimmers; not for totally enclosed luminaires.
- SANSI 30 W bulbs (sansi-30w): bulb reads 'C23ZW005-V0030A29/AC120V/60Hz/0.65A/30W/E26 Date:04.2025', suitable for damp
  locations, do not use with dimmers, not for totally enclosed luminaires. Ethan confirmed model, 120 V, 0.65 A, 30 W, E26.
Guarded like plant updates: each field changes only if it still holds the value the batch expects.
Run: python3 dev/seed_src/build_batchB2.py"""
import json, os
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
lights_update = [
    {'key': 'barrina-standing', 'note': 'model number from its label (batch B2)',
     'set': {'model': [None, 'T10F20'],
             'power': ['Plugs into an outlet; 4.9 ft cord with an on/off switch',
                       'Plugs into an outlet (100-277 V AC, 50/60 Hz); 4.9 ft cord with an on/off switch']}},
    {'key': 'sansi-80w', 'note': 'model number and ratings from its label (batch B2)',
     'set': {'model': [None, 'C21FS-BE26'],
             'power': ['Screws into an E26 socket (120 V); the cord or fixture is not included',
                       'Screws into an E26 socket (120 V AC, 60 Hz, 1.1 A); the cord or fixture is not included'],
             'notes': ['', 'Label: "LED Wing Grow Light", rated for damp locations (a covered porch is fine, not direct rain). '
                           'Not for totally enclosed fixtures: hang it bare or in an open shade so it can shed heat.']}},
    {'key': 'sansi-10w', 'note': 'model number and ratings from its label (batch B2)',
     'set': {'model': [None, 'C21GL-GE26-10W'],
             'power': ['Screws into an E26 socket (90 to 132 V)',
                       'Screws into an E26 socket (120 V AC, 60 Hz, 0.2 A; works from 90 to 132 V)'],
             'notes': ['', 'Not dimmable: do not put it on a dimmer switch or dimming plug. Rated for damp locations (a covered porch is fine, '
                           'not direct rain). Not for totally enclosed fixtures: use a bare socket or an open shade so it can shed heat.']}},
    {'key': 'sansi-30w', 'note': 'model number and ratings from its label (batch B2)',
     'set': {'model': [None, 'C23ZW005-V0030A29'],
             'power': ['Screws into an E26 socket (120 V). Not dimmable.',
                       'Screws into an E26 socket (120 V AC, 60 Hz, 0.65 A). Not dimmable.'],
             'notes': ['', 'Do not put it on a dimmer switch or dimming plug. Rated for damp locations (a covered porch is fine, not direct rain). '
                           'Not for totally enclosed fixtures: an open clamp-lamp shade is fine, a closed globe is not.']}},
    {'key': 'sansi-pot-clip', 'note': 'model number and ratings from its label and manual (batch B2)',
     'set': {'model': [None, 'C23ZW013-T0005A27'],
             'power': ['USB (5 V): a phone charger, power bank or computer; 78.7 in cord',
                       'USB (5 V, 1 A): its own plug adapter (120 V AC, 60 Hz, 0.05 A), a phone charger, power bank or computer; 78.7 in cord'],
             'size': ['12.8 in gooseneck; clips onto a rim up to 0.8 in thick',
                      '12.8 in gooseneck; clips onto a pot rim up to 0.4 in (1 cm) thick, the maker\'s suggestion'],
             'notes': ['', 'Buttons on the cord: on/off, brightness (4 levels) and timer (3, 6 or 12 hours; a red, green or yellow dot shows which). '
                           'Turning it off by hand cancels the timer. 120 degree beam. For indoor damp places, not rain. '
                           'Works from 14 to 104 F. The LED cannot be replaced; the whole light is replaced when it wears out (about 25,000 hours).']}},
]
b = {'id': 'B2', 'created': '2026-11-01', 'author': "Claude (Ethan's grow light details, Nov 2026)", 'lights_update': lights_update}
json.dump(b, open(os.path.join(REPO, 'app/seed/batches/batchB2.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(lights_update), 'light updates')
