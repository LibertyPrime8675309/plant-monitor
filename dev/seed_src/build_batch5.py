import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))  # repository root
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envdata

OUT = REPO + '/app/seed'
seed = json.load(open(OUT + '/seed.json'))
b2 = json.load(open(OUT + '/batches/batch2.json'))

plants = []   # (code, name, [files])
for p in seed['plants']:
    plants.append([p['code'], p['common_name'], [x['file'] for x in p['photos']]])
for i, p in enumerate(b2['plants']):
    plants.append(['P-%03d' % (41 + i), p['common_name'], [x['file'] for x in p['photos']]])
by = {x[0]: x for x in plants}
for ph in b2['existing_photos']: by[ph['code']][2].append(ph['file'])
for u in b2['updates']:
    if 'common_name' in u['set']: by[u['code']][1] = u['set']['common_name'][1]

count = {}
for _, _, fs in plants:
    for f in set(fs): count[f] = count.get(f, 0) + 1

updates = []
for code, name, files in plants:
    uniq = [f for f in files if count[f] == 1]
    key = uniq[:1] if uniq else files[:2]
    d = envdata.fert_for(code)
    updates.append({'code': code, 'name': name, 'photos': key,
                    'note': 'Added feeding season (months and days between feedings) for the fertilizer calendar',
                    'set': {f: [None, v] for f, v in d.items() if v is not None}})
batch = {'id': 'batch5', 'created': '2026-10-20', 'author': 'Claude (batch 5, feeding seasons)',
         'plants': [], 'existing_photos': [], 'updates': updates, 'to_photograph_done': [], 'to_photograph_add': []}
json.dump(batch, open(OUT + '/batches/batch5.json', 'w'), indent=1, ensure_ascii=False)
print(len(updates), 'plants;', sum(1 for u in updates if len(u['photos']) > 1), 'matched by two photos;', sum(1 for u in updates if not u['photos']), 'without photo')
