"""Batch C5 (PLAN.md step 9, 1.57.0): the amendments, each species' "mix it wants", and what Ethan's semi-hydro and bark pots are in.

- amendments_add: Ethan's eight (November 10, 2026) and the ones Claude suggested that day, each with its grades and its
  properties on a relative scale (1 low to 5 very high for holding water and letting in air; months before it breaks down,
  0 for never; food 0 to 2; pH -1 lowers, +1 raises; weight 1 to 3). These are rules of thumb for comparing amendments, not lab
  values; Ethan and his editors can change any of them.
- facts_add: each species' "mix it wants", read from the potting-mix text on its care sheet (fast-draining for chunky, gritty,
  cactus and orchid mixes; moisture-holding where the sheet says so; balanced otherwise). Plants in water culture are skipped.
- Ethan's pots (November 10): P-032 is now in clay pebbles in a glass jar (it was water); P-092, P-094 and P-095 are clay pebbles
  with a sphagnum top layer in pots with drainage holes over a catch pot or tray; P-096 is mostly orchid bark; P-097 and P-098
  are perlite in glass. Their growing kind and what holds their water are set guarded on empty, and their mix only where none
  is recorded. Codes P-092 to P-098 are Ethan's own records: if one is missing the batch skips it and says so."""
import glob, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
OUT = os.path.join(ROOT, 'app', 'seed', 'batches', 'batchC5.json')
SRC = "Claude's summary of common growing guidance (November 2026): a rough guide for comparing amendments, not measured values"
A = lambda key, name, role, grades, w, a, lasts, feeds, ph, weight, notes='': {
    'key': key, 'name': name, 'role': role, 'grades': grades, 'holds_water': w, 'airy': a, 'lasts_months': lasts, 'feeds': feeds, 'ph': ph,
    'weight': weight, 'source': SRC, 'notes': notes}
AMENDMENTS = [
    A('orchid-bark', 'Orchid bark', 'part', ['small', 'medium', 'large'], 2, 5, 18, 0, -1, 1, 'Fir or pine bark. Chunky and airy; breaks down and packs down over a year or two.'),
    A('coco-coir', 'Coco coir', 'part', ['chunks', 'ground'], 4, 3, 24, 0, 0, 1, 'Chunks are airy; ground coir holds more water. Rinse well: some is salty.'),
    A('charcoal', 'Horticultural charcoal', 'part', ['small', 'medium', 'large'], 2, 4, 0, 0, 1, 1, 'Light and airy; does not break down.'),
    A('pumice', 'Horticultural pumice', 'part', ['1/8 in', '1/4 in', '3/8 in'], 2, 5, 0, 0, 0, 2, 'Porous stone: airy, holds a little water inside, never breaks down.'),
    A('worm-castings', 'Worm castings', 'part', [], 4, 2, 6, 2, 0, 2, 'Gentle food and holds water; use a small share.'),
    A('perlite', 'Horticultural perlite', 'part', ['fine', 'medium', 'coarse'], 1, 5, 0, 0, 0, 1, 'Very light, opens a mix; floats when watered. Also used on its own for semi-hydro.'),
    A('vermiculite', 'Horticultural vermiculite', 'part', ['fine', 'medium', 'coarse'], 5, 2, 24, 0, 0, 1, 'Holds a lot of water; the opposite of perlite in a mix.'),
    A('leca', 'Clay pebbles (LECA)', 'medium', ['4 to 8 mm', '8 to 16 mm'], 2, 5, 0, 0, 0, 2, 'Fired clay balls for semi-hydro: they wick water up from a reservoir and never break down. No food: the water carries it.'),
    A('sphagnum', 'Sphagnum moss (long-fibre)', 'part', [], 5, 3, 12, 0, -1, 1, 'Holds a lot of water but stays airy. Often a top layer on semi-hydro pots.'),
    A('peat', 'Peat moss', 'part', [], 5, 2, 24, 0, -1, 1, 'The base of most bagged mixes; hard to wet again once dry.'),
    A('potting-mix', 'Bagged potting mix', 'part', [], 4, 2, 12, 1, 0, 2, 'As a base to add to. Most have peat or coir and a little starter food.'),
    A('lava-rock', 'Lava rock (scoria)', 'part', ['small', 'medium'], 2, 5, 0, 0, 0, 3, 'Like pumice but heavier and rougher.'),
    A('calcined-clay', 'Calcined clay', 'part', [], 3, 4, 0, 0, 0, 2, 'Fired clay granules (sold for bonsai and sports turf); holds some water inside the grain.'),
    A('grit', 'Coarse sand or grit', 'part', [], 1, 3, 0, 0, 0, 3, 'For cacti and succulents; adds weight so tall plants do not tip. Not fine play sand.'),
    A('zeolite', 'Zeolite', 'part', [], 3, 4, 0, 1, 0, 2, 'Holds nutrients and lets them go slowly; also used in semi-hydro.'),
    A('rice-hulls', 'Rice hulls (parboiled)', 'part', [], 1, 4, 12, 0, 0, 1, 'A perlite substitute that breaks down in about a year.'),
    A('tree-fern', 'Tree fern fibre', 'part', [], 2, 5, 36, 0, 0, 1, 'For orchids and other epiphytes.'),
    A('cork', 'Cork', 'part', ['nuggets'], 1, 5, 60, 0, 0, 1, 'For orchids and epiphytes; lasts for years.'),
    A('compost', 'Compost or leaf mould', 'part', [], 4, 2, 6, 2, 0, 2, 'A little food and structure, like worm castings.'),
    A('slow-release', 'Slow-release fertilizer', 'additive', [], None, None, None, 2, 0, None, 'A pinch, not a part: follow the label for how much per gallon of mix.'),
    A('dolomite', 'Dolomite lime', 'additive', [], None, None, None, 1, 1, None, 'Raises pH and adds calcium and magnesium. A little per gallon of a peat mix.'),
    A('mycorrhizae', 'Mycorrhizal inoculant', 'additive', [], None, None, None, 0, 0, None, 'Beneficial fungi for the roots; dust onto the roots or into the mix.'),
    A('pon', 'Pon', 'medium', [], 3, 4, 0, 0, 0, 2, 'A ready semi-hydro mix of pumice, zeolite and lava.'),
]

def wants(text):
    t = (text or '').lower()
    if not t or 'water culture' in t or 'roots hang in the water' in t: return None
    if 'moisture-holding' in t or 'moist' in t.split('mix')[0]: return 'Moisture-holding'
    if t.startswith(('medium orchid bark', 'coarse orchid bark')): return 'Fast-draining'      # an orchid potted in bark
    if any(k in t for k in ('fast-draining', 'gritty', 'mineral', 'cactus', 'succulent', 'orchid-type', 'chunky', 'orchid bark or sphagnum')): return 'Fast-draining'
    return 'Balanced'

def species():
    """{scientific name: [soil texts]} from the seed and every batch, with later updates applied."""
    by_code, soil = {}, {}
    files = [os.path.join(ROOT, 'app', 'seed', 'seed.json')] + sorted(glob.glob(os.path.join(ROOT, 'app', 'seed', 'batches', 'batch*.json')))
    out = {}
    for f in files:
        if f.endswith('batchC5.json'): continue
        d = json.load(open(f, encoding='utf-8'))
        for p in d.get('plants', []):
            sci, txt = p.get('scientific_name'), p.get('soil_medium')
            if p.get('code'): by_code[p['code']] = sci; soil[p['code']] = txt
            elif sci and txt: out.setdefault(sci, []).append(txt)
        for u in d.get('updates', []):
            st = u.get('set') or {}
            if u.get('code') and 'soil_medium' in st: soil[u['code']] = st['soil_medium'][1]
            if u.get('code') and 'scientific_name' in st: by_code[u['code']] = st['scientific_name'][1]
    for code, sci in by_code.items():
        if sci and soil.get(code): out.setdefault(sci, []).append(soil[code])
    return out

facts = []
for sci, texts in sorted(species().items()):
    if re.match(r'^(not identified|none|unknown)', sci.strip().lower()): continue
    ws = [w for w in (wants(t) for t in texts) if w]
    if not ws: continue
    w = max(set(ws), key=ws.count)
    facts.append({'name': sci, 'kind': 'plant', 'field': 'mix_wants', 'value': w, 'source': 'Upgrade batch C5: read from the potting-mix advice on its care sheet',
                  'source_kind': 'batch', 'confidence': 'likely'})
L = lambda key, grade=None, depth=None: {'key': key, 'grade': grade or '', 'depth_in': depth}
POTS = [
    {'code': 'P-032', 'grow_kind': 'Semi-hydro', 'reservoir': 'The pot itself (no holes)', 'parts': [{'key': 'leca', 'parts': 1}], 'notes': 'In a glass jar (Ethan, November 10, 2026).'},
    {'code': 'P-092', 'grow_kind': 'Semi-hydro', 'reservoir': 'A catch pot', 'parts': [{'key': 'leca', 'parts': 1}], 'top': L('sphagnum'), 'notes': 'Pot with drainage holes in a catch pot (Ethan, November 10).'},
    {'code': 'P-094', 'grow_kind': 'Semi-hydro', 'reservoir': 'A tray under it', 'parts': [{'key': 'leca', 'parts': 1}], 'top': L('sphagnum'), 'notes': 'Pot with drainage holes on a terracotta tray (Ethan, November 10).'},
    {'code': 'P-095', 'grow_kind': 'Semi-hydro', 'reservoir': 'A tray under it', 'parts': [{'key': 'leca', 'parts': 1}], 'top': L('sphagnum'), 'notes': 'Pot with drainage holes on a terracotta tray (Ethan, November 10).'},
    {'code': 'P-096', 'grow_kind': 'Soil mix', 'reservoir': 'A catch pot', 'parts': [{'key': 'orchid-bark', 'parts': 1}], 'notes': 'Chunky, mostly orchid bark; the rest is not recorded yet (Ethan, November 10). Plastic drainage pot in a catch pot.'},
    {'code': 'P-097', 'grow_kind': 'Semi-hydro', 'reservoir': 'The pot itself (no holes)', 'parts': [{'key': 'perlite', 'parts': 1}], 'notes': 'Perlite in a glass container (Ethan, November 10).'},
    {'code': 'P-098', 'grow_kind': 'Semi-hydro', 'reservoir': 'The pot itself (no holes)', 'parts': [{'key': 'perlite', 'parts': 1}], 'notes': 'Perlite in a glass container (Ethan, November 10).'},
]
seed32 = 'None right now (water culture). The usual medium is coarse orchid bark or sphagnum moss in a clear pot with side holes.'
batch = {
    'id': 'C5', 'created': '2026-11-10', 'author': "Claude (Ethan's pots and amendments, November 10, 2026)",
    'amendments_add': AMENDMENTS,
    'facts_add': facts,
    'updates': [{'code': p['code'], 'set': {'grow_kind': [None, p['grow_kind']], 'reservoir': [None, p['reservoir']]}, 'note': 'What it grows in (step 9)'} for p in POTS]
               + [{'code': 'P-032', 'name': 'Moth orchid in water', 'set': {'container': ['Glass jar with water', 'Glass jar with clay pebbles (semi-hydro)'],
                   'soil_medium': [seed32, 'Clay pebbles (LECA), semi-hydro: the jar holds the water. The usual alternatives are coarse orchid bark or sphagnum moss in a clear pot with side holes.']},
                   'note': 'Moved from water into clay pebbles (Ethan, November 10)'}],
    'pot_mixes_add': [{'code': p['code'], 'mixed_on': '2026-11-10', 'parts': p['parts'], 'top': p.get('top'), 'notes': p['notes']} for p in POTS],
}
json.dump(batch, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('wrote', OUT, len(AMENDMENTS), 'amendments,', len(facts), 'species facts')
for f in facts: print('  ', f['name'][:50], '->', f['value'])
