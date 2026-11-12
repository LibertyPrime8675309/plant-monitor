"""Batch C8 (1.58.0): the Baraboo cutting in water is P-094 (Ethan, November 11, 2026).
- Ethan: P-094 is the cutting itself, cut around July 31, 2026 from the mother plant at a coffee shop in Baraboo, Wisconsin; it rooted in Round Rock
  and was potted. His November 11 photos show it in a jar of filtered water on an east window sill (root nub, firm, green, odourless; one leaf
  browned and collapsed), so they go on P-094's page (no new page).
- The H-E-B tag belongs to P-095 (bought in Round Rock), which shares P-094's pot. P-094's tag mentions are removed, its ID confidence drops
  from 95 to 75 (it rested on the tag) and its origin is recorded. Guarded field by field.
Run: python3 dev/seed_src/build_batchC8.py <plants.db with batches up to C7>"""
import json, os, sqlite3, sys
from PIL import Image, ImageOps
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
RAW, PH = REPO + '/dev/photos-raw/rawC8', REPO + '/app/seed/photos'
c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
row = lambda code: c.execute('SELECT * FROM plants WHERE code=?', (code,)).fetchone()
L = lambda *x: '\n'.join(x)
D = 'November 11'
SRC = f'Ethan, {D}'
FIELD_NAMES = [r[1] for r in c.execute('PRAGMA table_info(plants)')
               if r[1] not in ('id', 'code', 'version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by')]

def pic(key):
    f = f'img_c8_{key}.jpg'
    im = ImageOps.exif_transpose(Image.open(f'{RAW}/{key}.jpg')); im.thumbnail((1280, 1280)); im.convert('RGB').save(f'{PH}/{f}', 'JPEG', quality=80, optimize=True)
    return f
def photos(items):
    return [{'file': pic(k), 'caption': f'{D}: {cap}', 'primary': i == 0, 'source': SRC} for i, (k, cap) in enumerate(items)]

# The cutting in the water is P-094 itself (Ethan, November 11): cut about July 31, 2026 from the Baraboo mother plant. Its photos go on P-094's page.
existing_photos = photos([('leaf_a', 'the cutting in water: a healthy green leaf with cream splashes and speckles'), ('window', 'the cutting in water on the east window sill'),
                          ('leaves', 'the cutting: both leaves, one browned and sagging'), ('leaf_dead', 'the browned leaf, from the front'),
                          ('under_dead', 'underside of the browned leaf'), ('under_ok', 'underside of the healthier leaf'),
                          ('nub', 'the root nub, firm and green-tan'), ('base', 'the cut end: dry callus, firm, no film'), ('water', 'how far the stem sits in the water')])
for ph in existing_photos: ph['code'] = 'P-094'; ph['primary'] = False

# P-094 came from the Baraboo coffee shop plant; the H-E-B tag belongs to P-095 (bought in Round Rock), which shares P-094's pot (Ethan, November 11).
r94 = row('P-094')
def g(f, old, new): return {f: [r94[f], new]} if r94[f] == old else {}
S94 = {}
S94.update(g('aliases', "Tag: H-E-B 'Monstera Thai Constellation, Monstera deliciosa'; Swiss cheese plant (variegated); 'Thai Constellation' left plant",
             "Swiss cheese plant (variegated); 'Thai Constellation' left plant; from the Baraboo coffee shop plant (cut about July 31, 2026)"))
S94.update(g('container', r94['container'], r94['container'].replace('; H-E-B tag', '; no tag (the H-E-B tag in the pot belongs to P-095)')))
S94.update(g('id_basis', r94['id_basis'],
             "Grown from a cutting of the mother plant at a coffee shop in Baraboo, Wisconsin (Ethan: cut about July 31, 2026). It has no tag of its own: the H-E-B tag in "
             "the pot belongs to P-095, which was bought in Round Rock. The leaves match 'Thai Constellation': heart-shaped juvenile Monstera leaves "
             "speckled and splashed with cream, on a moss pole in sphagnum. 'Thai Constellation' is the tissue-cultured variegated form of Monstera "
             "deliciosa with stable cream speckling."))
S94.update(g('id_improve', r94['id_improve'], "A tag or name from the Baraboo coffee shop, if they know it. A photo when the first split leaf opens would be nice for the record."))
S94.update(g('id_confidence', 95, 75))
S94.update(g('notes', r94['notes'], "Grown from a cutting taken around July 31, 2026 from the mother plant at a coffee shop in Baraboo, Wisconsin; it rooted in Round Rock and was potted (Ethan, November 11). On November 11 Ethan also photographed the cutting in a jar of filtered water on an east window sill (root nub, firm and odourless; one leaf browned and collapsed). " + r94['notes']))
updates = [{'code': 'P-094', 'name': r94['common_name'], 'photos': [c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY id LIMIT 1', (r94['id'],)).fetchone()[0]],
            'note': "Ethan, November 11: this plant came from the Baraboo coffee shop plant; the H-E-B tag is P-095's", 'set': S94}]
batch = {'id': 'C8', 'created': '2026-11-11', 'author': "Ethan's photos and checks of the variegated Monstera cutting (November 11, 2026)", 'existing_photos': existing_photos, 'updates': updates}
json.dump(batch, open(os.path.join(REPO, 'app/seed/batches/batchC8.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(existing_photos), 'photos on P-094,', len(updates), 'update')
