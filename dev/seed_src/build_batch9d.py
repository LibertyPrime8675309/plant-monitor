"""Batch 9d: set Location to "Covered porch" for plants whose own spot text says they are on the covered porch
("Covered porch ..." or "Porch shelf / bench / edge ..."), so rain is not counted as watering for them and the
cold-night list can say they are sheltered. Spots that name two places ("Porch shelf / front table") are left alone.
Run against a fresh install with batches up to 9c applied:  python3 dev/seed_src/build_batch9d.py <plants.db>"""
import json, os, sqlite3, sys
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
ups = []
for r in c.execute("SELECT code, common_name, location, site FROM plants WHERE status='active' ORDER BY code"):
    loc = (r['location'] or '').strip(); low = loc.lower()
    if not low.startswith(('covered porch', 'porch')) or (r['site'] or 'Outdoors') != 'Outdoors': continue
    if '/' in loc and not low.startswith('covered porch'): continue
    f = c.execute('SELECT file FROM photos WHERE plant_id=(SELECT id FROM plants WHERE code=?) ORDER BY id LIMIT 1', (r['code'],)).fetchone()
    ups.append({'code': r['code'], 'name': r['common_name'], 'photos': [f[0]] if f else [],
                'note': 'Location set to Covered porch from its spot description (batch 9d)', 'set': {'site': ['Outdoors', 'Covered porch']}})
b = {'id': 'batch9d', 'created': '2026-10-23', 'author': 'Claude (batch 9d, covered porch locations)', 'plants': [], 'existing_photos': [],
     'updates': ups, 'to_photograph_done': [], 'to_photograph_add': []}
json.dump(b, open(os.path.join(REPO, 'app/seed/batches/batch9d.json'), 'w'), indent=1, ensure_ascii=False)
print(len(ups), 'plants')
