import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))  # repository root
"""Batch 9c: Ethan says one P-055 photo (img_b2_17) shows a different plant -> new page, photo moved there."""
import json, sqlite3, sys
DB = sys.argv[1] if len(sys.argv) > 1 else '/tmp/t20/plants.db'
c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
r = c.execute("SELECT * FROM plants WHERE code='P-055'").fetchone()
L = lambda *x: '\n'.join(x)
env = ['temp_ideal_low', 'temp_ideal_high', 'temp_damage_below', 'temp_lethal_below', 'temp_notes', 'humidity_low', 'humidity_high', 'humidity_notes',
       'light_summary', 'light_hours', 'light_notes', 'winter_plan', 'winter_summary', 'winter_triggers', 'winter_steps', 'indoor_setup',
       'temp_damage_above', 'vpd_low', 'vpd_high', 'par_low', 'par_high', 'dli_low', 'dli_high', 'water_notes', 'soil_medium', 'soil_ph_low', 'soil_ph_high',
       'soil_moisture_low', 'soil_moisture_high', 'soil_temp_low', 'soil_temp_high', 'fertilizer', 'nutrients', 'fert_from_month', 'fert_to_month', 'fert_every_days',
       'pests_watch', 'pest_steps']
d = {k: r[k] for k in env}
d.update(common_name='Yellow-marbled philodendron (self-heading, unidentified)', scientific_name='Philodendron sp. (unconfirmed)', aliases='',
    plant_type='Tropical foliage (aroid)', location=r['location'], container='Black nursery pot', site='Outdoors', id_confidence=35,
    id_basis="Split from P-055: Ethan says this photo shows a different plant from the Black Cardinal. A broad, glossy, oval leaf marbled lime and yellow over green, on a long stalk from the base, so probably a self-heading philodendron. Not enough to name it from one photo.",
    id_alternatives=L("Philodendron 'Calypso' (lime-and-yellow marbled)", "Philodendron 'Painted Lady' (young leaf)", "Philodendron 'Golden Crocodile'", "Philodendron 'Prince of Orange' (green-leaf stage)"),
    id_improve=L('A photo of the whole plant from the side', 'A newly opened leaf (its colour as it opens)', 'The pot tag or price label'),
    health_rating='Fair', health_summary='Large leaf with brown, sunburned-looking patches along the edge and near the midrib; dried stalks at the base.',
    health_observations=L('Brown scorch patches on the big leaf', 'Pale yellow spots', 'Dried old leaf stalks at the base'),
    health_steps=L('Move it out of direct afternoon sun.', 'Remove the dried stalks.', 'Water when the top inch is dry.', 'Bring it inside before nights reach 55°F.'),
    notes='Split from P-055 on October 23, 2026: Ethan said the photo img_b2_17 shows a different plant.', pests_current='None seen.')
d['photos'] = []
d['take_photos'] = [{'file': 'img_b2_17.jpg', 'from': 'P-055', 'caption': 'Marbled leaf with brown patches (was on P-055)'}]
upd = {'code': 'P-055', 'name': r['common_name'], 'photos': ['img_b9_p055_3.jpg'], 'note': 'One photo was a different plant; it has its own page now (batch 9c)',
       'set': {'notes': [r['notes'], "One older photo showed a different plant (yellow-marbled leaf); it was moved to that plant's own page on October 23, 2026."]}}
ans = 'Ethan (October 23): two different plants. The yellow-marbled one has its own page now.'
b = {'id': 'batch9c', 'created': '2026-10-23', 'author': 'Claude (batch 9c, your answers)', 'plants': [d], 'existing_photos': [], 'updates': [upd],
     'to_photograph_done': [], 'to_photograph_add': [], 'requests_done': [{'key': 'p055-two-pots', 'answer': ans}]}
json.dump(b, open(REPO + '/app/seed/batches/batch9c.json', 'w'), indent=1, ensure_ascii=False)
print('ok', r['notes'])
