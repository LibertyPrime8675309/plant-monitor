"""Batch C8 (1.57.0): a new page for the variegated Monstera cutting rooting in water (Ethan, November 11, 2026).
- Ethan: it is a cutting from a larger mother plant, in a tall clear container of filtered water on an east-facing window sill. It has a root
  nub and no roots yet. His checks the same day: the node, the nub and the cut end are firm, green and odourless, with no film; the water was
  3 days old. One leaf has browned and collapsed, the other has brown patches.
- The pattern (green leaves with cream splashes and fine speckles) matches the two 'Thai Constellation' pages (P-094, P-095), so the page starts
  from P-094 and says it is probable, not tagged. Which plant it came from is not recorded: Ethan can say.
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

p = {k: row('P-094')[k] for k in FIELD_NAMES}
p.update(
    common_name="Monstera 'Thai Constellation' cutting (rooting in water)",
    scientific_name="Monstera deliciosa 'Thai Constellation' (probable)",
    aliases='Variegated Monstera cutting; Swiss cheese plant (variegated); cutting from the Baraboo coffee shop mother plant (same line as P-094)',
    id_confidence=70,
    id_basis=("Ethan: it came from the mother plant at a coffee shop in Baraboo, Wisconsin (July 2026), the same line as P-094, which grew from a cutting of "
              "that plant. Large heart-shaped, unsplit leaves, green with irregular cream splashes and fine cream speckles, which is how 'Thai Constellation' "
              "looks and matches P-094 and P-095. A plain albo has big clean white sectors and no speckling, so it fits less well. There is no tag on the "
              "cutting or on the Baraboo plant that Ethan knows of, so the name rests on the leaves."),
    id_alternatives=L("Monstera deliciosa 'Thai Constellation'", "Monstera deliciosa 'Albo Variegata' (less likely: no speckling)", "Monstera deliciosa 'Aurea' (cream-yellow, not speckled)"),
    id_improve=L('A tag or label on the Baraboo mother plant, if the coffee shop knows its name', "The first new leaf once it roots: 'Thai Constellation' keeps the speckles and splashes"),
    location='East-facing window sill, in a tall clear container of filtered water',
    container='Tall clear plastic jar of filtered water, with the root nub and cut end underwater, leaves in the air',
    site='Indoors', grow_kind='Water only', reservoir='The pot itself (no holes)', water_every_days=None,
    health_rating='Fair', pot_size='Small: fits in a bucket', leaf_type='Large leaves',
    light_summary='Bright indirect light; the east window is gentle enough, but no hot direct sun on the cream parts',
    height_pot=None, width_pot=None,
    health_summary=("A rootless cutting with two leaves and one root nub. One leaf has browned, dried and collapsed; the other holds up better but has "
                    "brown patches. The node, the nub and the cut end were all checked on November 11 and are firm, green and odourless, with no slime, "
                    "so the cutting itself is alive. A cutting with no roots cannot replace the water its leaves lose, so sag and leaf loss are common; "
                    "the exact cause here is not confirmed."),
    health_observations=L('Two leaves on long stalks; one browned, dry and collapsed', 'The other leaf has brown patches and a limp tip',
                          'Node where the leaf meets the stem: green, firm, no smell', 'One root nub, firm, no film, no smell',
                          'Cut end: dry brown callus, firm, no film, no smell', 'Water 3 days old and clear',
                          'Only the lower stem is under water; the leaves stay dry'),
    health_steps=L('Change the water every 3 to 5 days and keep only the root nub and cut end under water.',
                   'Bright indirect light; keep it out of hot direct sun, which scorches the cream parts.',
                   'Keep it warm: rooting slows a lot below about 70°F.',
                   'Cut off the collapsed leaf once it is fully dead, so it cannot rot in the water or touch the other leaf.',
                   'Be patient: variegated cuttings often take 4 to 8 weeks or more to root.',
                   'If the node ever turns soft, dark or smelly, trim back to firm tissue and change the water.',
                   'When roots are about an inch long, move it into perlite, sphagnum or a gritty mix; water roots are fragile in soil.'),
    pests_current='',
    notes=("A cutting from the mother plant at a coffee shop in Baraboo, Wisconsin (July 2026, Ethan). P-094 grew from a cutting of the same mother plant. "
           "In water in Round Rock since before November 11, 2026 (the exact day it was cut is not recorded). Photographed and checked on November 11: node, "
           "nub and cut end firm and odourless."))
p['photos'] = photos([('leaf_a', 'the healthier leaf: green with cream splashes and speckles'), ('window', 'the whole cutting on the east window sill'),
                      ('leaves', 'both leaves, one browned and sagging'), ('leaf_dead', 'the browned leaf, from the front'),
                      ('under_dead', 'underside of the browned leaf'), ('under_ok', 'underside of the healthier leaf'),
                      ('nub', 'the root nub, firm and green-tan'), ('base', 'the cut end: dry callus, firm, no film'), ('water', 'how far the stem sits in the water')])

# P-094 came from the Baraboo coffee shop plant; the H-E-B tag belongs to P-095 (bought in Round Rock), which shares P-094's pot (Ethan, November 11).
r94 = row('P-094')
def g(f, old, new): return {f: [r94[f], new]} if r94[f] == old else {}
S94 = {}
S94.update(g('aliases', "Tag: H-E-B 'Monstera Thai Constellation, Monstera deliciosa'; Swiss cheese plant (variegated); 'Thai Constellation' left plant",
             "Swiss cheese plant (variegated); 'Thai Constellation' left plant; from the Baraboo coffee shop plant (July 2026)"))
S94.update(g('container', r94['container'], r94['container'].replace('; H-E-B tag', '; no tag (the H-E-B tag in the pot belongs to P-095)')))
S94.update(g('id_basis', r94['id_basis'],
             "Grown from a cutting of the mother plant at a coffee shop in Baraboo, Wisconsin (Ethan, July 2026). It has no tag of its own: the H-E-B tag in "
             "the pot belongs to P-095, which was bought in Round Rock. The leaves match 'Thai Constellation': heart-shaped juvenile Monstera leaves "
             "speckled and splashed with cream, on a moss pole in sphagnum. 'Thai Constellation' is the tissue-cultured variegated form of Monstera "
             "deliciosa with stable cream speckling."))
S94.update(g('id_improve', r94['id_improve'], "A tag or name from the Baraboo coffee shop, if they know it. A photo when the first split leaf opens would be nice for the record."))
S94.update(g('id_confidence', 95, 75))
S94.update(g('notes', r94['notes'], "Grown from a cutting taken in July 2026 from the mother plant at a coffee shop in Baraboo, Wisconsin (Ethan, November 11). " + r94['notes']))
updates = [{'code': 'P-094', 'name': r94['common_name'], 'photos': [c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY id LIMIT 1', (r94['id'],)).fetchone()[0]],
            'note': "Ethan, November 11: this plant came from the Baraboo coffee shop plant; the H-E-B tag is P-095's", 'set': S94}]
batch = {'id': 'C8', 'created': '2026-11-11', 'author': "Ethan's photos and checks of the variegated Monstera cutting (November 11, 2026)", 'plants': [p], 'updates': updates}
json.dump(batch, open(os.path.join(REPO, 'app/seed/batches/batchC8.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('1 new plant,', len(p['photos']), 'photos')
