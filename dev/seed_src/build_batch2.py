import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))  # repository root
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageOps
from plants_c import C, UPDATES, TODO_DONE, TODO_NEW

RAW = REPO + '/dev/photos-raw/raw2'
OUT = REPO + '/app/seed'
PH = OUT + '/photos'
ROTATE_CCW = {'b2_01', 'b2_02', 'b2_03', 'b2_04', 'b2_05'}   # saved sideways with no EXIF orientation
os.makedirs(OUT + '/batches', exist_ok=True)

done = set()
def convert(key):
    if key in done: return
    im = ImageOps.exif_transpose(Image.open(f'{RAW}/{key}.jpg')).convert('RGB')
    if key in ROTATE_CCW: im = im.rotate(90, expand=True)
    im.thumbnail((1400, 1400))
    im.save(f'{PH}/img_{key}.jpg', 'JPEG', quality=82, optimize=True)
    done.add(key)

seed = json.load(open(OUT + '/seed.json'))
by_code = {p['code']: p for p in seed['plants']}

plants = []
for r in C:
    plants.append({
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
        'notes': r['notes'],
        'photos': [{'file': f'img_{k}.jpg', 'caption': cap, 'primary': i == 0, 'source': k} for i, (k, cap) in enumerate(r['photos'])],
    })
    for k, _ in r['photos']: convert(k)

existing_photos, updates = [], []
for u in UPDATES:
    old = by_code[u['code']]
    if u['fields']:
        updates.append({'code': u['code'], 'note': u['note'],
                        'set': {f: [old[f], v] for f, v in u['fields'].items()}})
    for k, cap, primary in u['photos']:
        convert(k)
        existing_photos.append({'code': u['code'], 'file': f'img_{k}.jpg', 'caption': cap, 'primary': primary, 'source': k})

# every raw photo must be used at least once
unused = sorted(f[:-4] for f in os.listdir(RAW) if f.endswith('.jpg')) 
unused = [k for k in unused if k not in done]
assert not unused, unused

batch = {'id': 'batch2', 'created': '2026-10-19', 'author': 'Claude (batch 2, from photos)',
         'plants': plants, 'existing_photos': existing_photos, 'updates': updates,
         'to_photograph_done': TODO_DONE,
         'to_photograph_add': [{'label': a, 'note': b} for a, b in TODO_NEW]}
json.dump(batch, open(OUT + '/batches/batch2.json', 'w'), indent=1, ensure_ascii=False)
print(len(plants), 'plants,', len(done), 'photos')
