"""Batch A5 (1.14.0): "About this plant" for every plant: type of plant, classification, mature size in the ground and in a
pot, hardiness zones, native range, conservation status, invasive risk, flowers, fruit, dangers to people and pets,
propagation, and the sources each profile was written from (with links). The profiles are in profiles_A5.py and the
sources in sources_A5.txt (key|title|url, every link taken from web search results on October 25, 2026).
Every field is only filled where still empty, so anything Ethan typed himself stays.
Run against a copy of a database with batches up to A4 applied:  python3 dev/seed_src/build_batchA5.py <plants.db>"""
import json, os, sqlite3, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from profiles_A5 import P, MAP, NO_IUCN

SRC = {}
for line in open(os.path.join(HERE, 'sources_A5.txt'), encoding='utf-8'):
    if line.strip():
        k, t, u = line.rstrip('\n').split('|')
        SRC.setdefault(k, []).append((t, u))
CITES = SRC['cites'][0]

FIELD = dict(habit='growth_habit', order='taxon_order', family='family', genus='genus', hg='height_ground', wg='width_ground',
             hp='height_pot', wp='width_pot', rate='growth_rate', life='lifespan', zl='zone_low', zh='zone_high', zn='zone_notes',
             native='native_range', cons='conservation_status', inv='invasive', bloom='bloom', fruit='fruit', dh='danger_humans',
             da='danger_animals', prop='propagation')

# notes for single plants on top of their profile
EXTRA = {
    'P-021': dict(life='Decades. These are seedlings: the swollen base (caudex) fattens over the first few years.'),
    'P-036': dict(zn='Not known until it is identified. Bring it in before frost to be safe.'),
    'P-045': dict(bloom='Cone-shaped clusters of yellow flowers from mature rosettes in late winter or spring. The burgundy colour is darkest in full sun.'),
    'P-053': dict(native='The gourd family grows wild worldwide in warm regions. The kind is not known until it is identified.'),
    'P-064': dict(zn='Hardy here; it needs some winter cold and a sunny, well-drained spot. Plant the rhizome with its top showing. Potted irises do best moved into the ground.'),
}

def lines(v): return '\n'.join(v) if isinstance(v, list) else v

c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
rows = {r['code']: r for r in c.execute('SELECT id, code, common_name FROM plants ORDER BY code')}
missing = [k for k in rows if k not in MAP]; assert not missing, f'no profile for {missing}'
first = lambda r: [x[0] for x in c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY id LIMIT 1', (r['id'],))]
ups = []
for code, r in rows.items():
    prof = dict(P[MAP[code]]); prof.update(EXTRA.get(code, {}))
    s = {'kingdom': ['', 'Plantae (plants)']}
    for k, f in FIELD.items():
        v = prof.get(k)
        if v: s[f] = ['', lines(v)]
    refs = [SRC[k] for k in prof.get('src', [])]
    refs = [x for grp in refs for x in grp] + list(prof.get('more', []))
    if 'CITES' in (prof.get('cons') or '') and CITES not in refs: refs.append(CITES)
    seen, out = set(), []
    for t, u in refs:
        if u not in seen: seen.add(u); out.append(f'{t} | {u}')
    if out: s['sources'] = ['', '\n'.join(out)]
    ups.append({'code': code, 'name': r['common_name'], 'photos': first(r), 'note': 'About this plant filled in, with sources (batch A5)', 'set': s})

batch = {'id': 'batchA5', 'created': '2026-10-25', 'author': 'Claude (plant details with sources, Oct 25, 2026)', 'updates': ups}
dst = os.path.join(REPO, 'app', 'seed', 'batches', 'batchA5.json')
json.dump(batch, open(dst, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(f'{dst}: {len(ups)} plants, {sum(len(u["set"]) for u in ups)} fields, {len({l for u in ups for l in u["set"].get("sources", ["", ""])[1].splitlines()})} distinct sources')
