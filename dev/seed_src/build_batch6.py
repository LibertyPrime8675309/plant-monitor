import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))  # repository root
"""Build app/seed/batches/batch6.json from plants_d.py and the photos in raw6/.
Old values for guarded updates are read from a fresh install (FRESH_DB), so they match what earlier batches produce."""
import json, os, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageOps
from plants_d import C, UPDATES, TODO_DONE, TODO_NEW

RAW = REPO + '/dev/photos-raw/raw6'
OUT = REPO + '/app/seed'
PH = OUT + '/photos'
FRESH_DB = sys.argv[1] if len(sys.argv) > 1 else '/tmp/fresh6/plants.db'

done = set()
def convert(key):
    if key in done: return
    im = ImageOps.exif_transpose(Image.open(f'{RAW}/{key}.jpg')).convert('RGB')
    im.thumbnail((1400, 1400))
    im.save(f'{PH}/img_{key}.jpg', 'JPEG', quality=82, optimize=True)
    done.add(key)

plants = []
for r in C:
    d = {
        'common_name': r['common'], 'scientific_name': r['sci'], 'aliases': r['aliases'],
        'plant_type': r['ptype'], 'location': r['loc'], 'container': r['cont'],
        'id_confidence': r['conf'], 'id_basis': r['basis'],
        'id_alternatives': '\n'.join(r['alts']), 'id_improve': '\n'.join(r['improve']),
        'temp_ideal_low': r['temp'][0], 'temp_ideal_high': r['temp'][1], 'temp_damage_below': r['temp'][2],
        'temp_lethal_below': r['temp'][3], 'temp_notes': r['temp'][4],
        'humidity_low': r['hum'][0], 'humidity_high': r['hum'][1], 'humidity_notes': r['hum'][2],
        'light_summary': r['light'][0], 'light_hours': r['light'][1], 'light_notes': r['light'][2],
        'winter_plan': r['winter'][0], 'winter_summary': r['winter'][1], 'winter_triggers': r['winter'][2],
        'winter_steps': '\n'.join(r['winter'][3]), 'indoor_setup': '\n'.join(r['winter'][4]),
        'health_rating': r['health'][0], 'health_summary': r['health'][1],
        'health_observations': '\n'.join(r['health'][2]), 'health_steps': '\n'.join(r['health'][3]),
        'notes': r['notes'], 'pests_current': r['pests'],
        'fert_from_month': r['fert'][0], 'fert_to_month': r['fert'][1], 'fert_every_days': r['fert'][2],
    }
    for k, v in r['env'].items():
        d.setdefault(k, v)
    d['photos'] = [{'file': f'img_{k}.jpg', 'caption': cap, 'primary': i == 0, 'source': k} for i, (k, cap) in enumerate(r['photos'])]
    for k, _ in r['photos']: convert(k)
    plants.append(d)

db = sqlite3.connect(FRESH_DB); db.row_factory = sqlite3.Row
existing_photos, updates = [], []
for u in UPDATES:
    cur = db.execute('SELECT * FROM plants WHERE code=?', (u['code'],)).fetchone()
    assert cur and cur['common_name'] == u['name'], u['code']
    updates.append({'code': u['code'], 'name': u['name'], 'photos': [u['match_photo']], 'note': u['note'],
                    'set': {f: [cur[f], v] for f, v in u['fields'].items() if cur[f] != v}})
    for k, cap, primary in u['photos']:
        convert(k)
        existing_photos.append({'code': u['code'], 'file': f'img_{k}.jpg', 'caption': cap, 'primary': primary, 'source': k})

unused = sorted(f[:-4] for f in os.listdir(RAW) if f.endswith('.jpg') and f[:-4] not in done)
assert not unused, unused

batch = {'id': 'batch6', 'created': '2026-10-20', 'author': 'Claude (batch 6, from photos)',
         'plants': plants, 'existing_photos': existing_photos, 'updates': updates,
         'to_photograph_done': TODO_DONE,
         'to_photograph_add': [{'label': a, 'note': b} for a, b in TODO_NEW]}
json.dump(batch, open(OUT + '/batches/batch6.json', 'w'), indent=1, ensure_ascii=False)
print(len(plants), 'new plants,', len(updates), 'updates,', len(done), 'photos')
