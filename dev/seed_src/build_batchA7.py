"""Batch A7 (1.16.1): Ethan's photos of October 25, 2026 from the covered porch shelf.
- New page: a second red Chinese evergreen (not P-028, as Ethan said on October 26), with three photos and health notes.
- P-035 Pink Princess cutting: its tag reads 'PP-1' (cropped from the Chinese evergreen photo); the stake is still in the stem.
- New page: a second curly Boston fern (grey pot in a darker grey bowl, its own hand-written tag), mostly dead with new fronds.
- New page: a young Monstera in a wide beige pot, regrowing from an old knot of roots.
Old values for the guarded updates come from a database with batches up to A6 applied (argv[1]). The new pages start from the
P-028 Chinese evergreen, P-024 fern and P-049 Monstera pages (their care and About details), with their own name, place, ID and health.
Run: python3 dev/seed_src/build_batchA7.py <plants.db>"""
import json, os, sqlite3, sys
from PIL import Image
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'app'))
RAW, PH = REPO + '/dev/photos-raw/rawA7', REPO + '/app/seed/photos'
c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
row = lambda code: c.execute('SELECT * FROM plants WHERE code=?', (code,)).fetchone()
first_photo = lambda code: c.execute('SELECT file FROM photos WHERE plant_id=(SELECT id FROM plants WHERE code=?) ORDER BY id LIMIT 1', (code,)).fetchone()[0]
L = lambda *x: '\n'.join(x)
D = 'October 25'
FIELD_NAMES = [r[1] for r in c.execute('PRAGMA table_info(plants)')
               if r[1] not in ('id', 'code', 'version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by')]

def pic(key):
    f = f'img_a7_{key}.jpg'
    im = Image.open(f'{RAW}/{key}.jpg'); im.thumbnail((1280, 1280)); im.save(f'{PH}/{f}', 'JPEG', quality=80, optimize=True)
    return f

existing_photos, updates, new_plants = [], [], []
def update(code, note, **new):
    r = row(code)
    s = {f: [r[f], v] for f, v in new.items() if r[f] != v}
    updates.append({'code': code, 'name': r['common_name'], 'photos': [first_photo(code)], 'note': note, 'set': s})

# ---------------------------------------------------------------- new: a second red Chinese evergreen (not P-028: Ethan, October 26)
agl = {k: row('P-028')[k] for k in FIELD_NAMES}
agl.update(
    common_name='Chinese evergreen, red speckled (second)', scientific_name='Aglaonema sp. (red speckled cultivar)',
    aliases="Possibly 'Red Peacock' or a similar speckled red cultivar", id_confidence=80,
    id_basis=("Red-pink leaf margins, pink leaf stalks and heavy yellow-green and red speckling over green are typical of the red Aglaonema "
              "cultivars. The speckling fits 'Red Peacock' and similar speckled kinds better than 'Siam Aurora', whose leaf centres are plain "
              "green. This is a second plant on the same shelf as P-028. Without a tag the exact cultivar stays open."),
    id_alternatives=L("Aglaonema 'Red Peacock'", "Aglaonema 'Super Red'", "Aglaonema 'Siam Aurora' (less likely: plain green leaf centres)", "Aglaonema 'Lady Valentine' (mostly pink leaves)"),
    id_improve=L('Tag or receipt, if there was one'),
    location='Covered porch pallet shelf', container='Black nursery pot on a black saucer', site='Covered porch', health_rating='Good',
    health_summary=('Healthy: bright speckled colour, firm leaves and a new pink shoot at the base. The mix has dried hard and shrunk away from '
                    'the pot wall, and white mineral crust is building up on the pot.'),
    health_observations=L('Bright red-edged, speckled leaves', 'A new pink shoot (offset) coming up at the base',
                          'Bare lower stem with dry, papery old leaf bases (normal as lower leaves drop)', 'Mix shrunk away from the pot edge (it dried out completely)',
                          'White crust on the pot rim and sides (minerals from tap water or fertilizer)', 'One leaf with a torn edge'),
    health_steps=L('Water slowly, let it drain, and water again, so the shrunken mix soaks up water. Or stand the pot in water for 15 minutes.',
                   'Once a month, water heavily to flush the minerals through, and wipe the white crust off the pot.',
                   'Bring it in before nights fall below 55°F, and keep it out of cold drafts.',
                   'Leave the dry papery leaf bases; they come away by themselves.', 'Feed at half strength in spring and summer only.'),
    notes=f'A second red Chinese evergreen on the porch shelf (not P-028), photographed on {D}, 2026, beside the PP-1 cutting (P-035).', pot_size=None)
agl['photos'] = [{'file': pic(k), 'caption': f'{D}: {cap}', 'primary': p, 'source': f'Ethan, {D}'}
                 for k, cap, p in (('agla_1', 'on the porch shelf, beside the PP-1 cutting', True), ('agla_2', 'from above', False),
                                   ('agla_3', 'stem base: a new pink shoot and dry old leaf bases', False))]
new_plants.append(agl)

# ---------------------------------------------------------------- P-035 Pink Princess cutting: the tag
existing_photos.append({'code': 'P-035', 'file': pic('pp1_tag'), 'caption': f"{D}: tag reads 'PP-1'; the stake is still in the stem", 'primary': False, 'source': f'Ethan, {D}'})
update('P-035', "Its tag reads 'PP-1' (batch A7)",
    id_confidence=70, container="Clear cup with a 'PP-1' tag",
    id_basis=("The white tag reads 'PP-1', which fits a Pink Princess label (October 25 photo). The surviving leaf is pale green with cream "
              "marbling, as young or struggling Pink Princess leaves often are."),
    id_improve=L('Photo of the node/stem under the dried leaves', 'Photo of the roots through the clear cup'),
    health_observations=L('One or two pale-green, cream-marbled leaves', 'Old cutting stem hollow', 'Bamboo stake still inside the hollow stem (October 25)', 'Several dead papery leaves'))

# ---------------------------------------------------------------- new: a second curly Boston fern
fern = {k: row('P-024')[k] for k in FIELD_NAMES}
fern.update(
    common_name='Boston fern, curly (grey bowl)', scientific_name="Nephrolepis exaltata, curly cultivar (probably 'Emina')", aliases='Second curly Boston fern',
    id_confidence=75,
    id_basis=("Upright fronds with tightly crimped, curled leaflets, the same as the 'Emina' Boston fern (P-024). This is a second pot: a light grey "
              "pot in a darker grey bowl, with its own hand-written tag that the photos do not show clearly."),
    id_alternatives=L("Nephrolepis exaltata 'Emina'", "Nephrolepis exaltata 'Fluffy Ruffles'"),
    id_improve=L('A close photo of the tag'),
    location='Covered porch pallet shelf', container='Light grey pot inside a darker grey bowl, bark mix, with a white plant marker and a hand-written tag',
    site='Covered porch', health_rating='Poor',
    health_summary='Mostly dead, crisped fronds, but healthy new curly fronds are coming from the crown, as on P-024.',
    health_observations=L('Most old fronds dry, brown and crisped', 'A few green fronds, and one fresh bright-green curly frond',
                          'Spurge weed (red stems, small oval leaves) growing in the pot', 'Chunky bark mix'),
    health_steps=L('Cut the dead fronds off at the base. Leave every green frond.', "Pull the spurge weed. Wear gloves: its milky sap irritates skin.",
                   'Keep the mix evenly moist and never let it dry out completely; ferns die back when they dry out.',
                   'Bright light without afternoon sun.', 'Bring it in before nights fall below 40°F.'),
    pests_current='Spurge weed in the pot.', notes=f'Second curly Boston fern, photographed on {D}, 2026.', pot_size=None)
fern['photos'] = [{'file': pic(k), 'caption': f'{D}: {cap}', 'primary': p, 'source': f'Ethan, {D}'}
                  for k, cap, p in (('fern_1', 'from above: crisped old fronds, new green ones', True), ('fern_2', 'a fresh curly frond, the tag and spurge weed', False),
                                    ('fern_3', 'the pot in its grey bowl', False))]
new_plants.append(fern)

# ---------------------------------------------------------------- new: a young Monstera
mon = {k: row('P-049')[k] for k in FIELD_NAMES}
mon.update(
    common_name='Monstera, young (beige pot)', scientific_name='Monstera deliciosa (young, probable)', aliases='',
    id_confidence=70,
    id_basis=("Heart-shaped young leaves that already have holes near the midrib and notches at the edge, the way young Monstera deliciosa "
              "leaves begin. The shoots come up from an old knot of roots, so it is probably regrowing from a stem cutting or an older plant that was cut back."),
    id_alternatives=L('Monstera adansonii (thinner, longer leaves with many holes)', 'Epipremnum pinnatum (young leaves can also have holes)',
                      "Rhaphidophora tetrasperma ('mini monstera'; splits to the edge, no holes)"),
    id_improve=L('How it started: a cutting, seeds, or an older plant cut back', 'A daylight photo once the next leaf opens', 'A tag, if it had one'),
    location='Covered porch pallet shelf', container='Wide beige pot, chunky mix with perlite, bark and lava rock', site='Covered porch',
    health_rating='Good',
    health_summary='Several healthy young shoots with their first holes and notches. The leaves are pale and a little puckered, which is common for new growth in cool weather.',
    health_observations=L('Three or four young shoots from an old root knot', 'First holes and edge notches on the newest leaves',
                          'Pale, slightly puckered young leaves', 'Two or three tiny seedlings in the mix (probably weeds)'),
    health_steps=L('Bring it in before nights fall below 50°F.', 'Keep the mix lightly moist, not wet, while it is small.', 'Bright light without direct afternoon sun.',
                   'Add a small moss pole or stake once a shoot starts to climb.', 'Pull the tiny seedlings unless you planted them.'),
    notes=f'Photographed on {D}, 2026, on the porch shelf.', pot_size=None)
mon['photos'] = [{'file': pic(k), 'caption': f'{D}: {cap}', 'primary': p, 'source': f'Ethan, {D}'}
                 for k, cap, p in (('mon_1', 'young leaves with their first holes', True), ('mon_2', 'shoots coming from the old root knot', False),
                                   ('mon_3', 'the beige pot on the shelf', False))]
new_plants.append(mon)

requests_add = [
    {'key': 'a7-fern-tag', 'code': 'new', 'kind': 'photo', 'photos': [fern['photos'][0]['file']], 'name': fern['common_name'],
     'text': 'A close photo of the hand-written tag in the second curly Boston fern (grey bowl), to settle its name.'},
    {'key': 'a7-monstera-start', 'code': 'new', 'kind': 'question', 'photos': [mon['photos'][0]['file']], 'name': mon['common_name'],
     'text': 'How did the young Monstera in the beige pot start: a cutting, seeds, or an older plant cut back? And did it have a tag?'},
]
requests_done = [{'key': 'p-035-pot-tag', 'answer': "The tag reads 'PP-1' (photo of October 25, 2026)."}]
b = {'id': 'batchA7', 'created': '2026-10-25', 'author': "Claude (Ethan's porch shelf photos, Oct 25, 2026)",
     'plants': new_plants, 'existing_photos': existing_photos, 'updates': updates, 'requests_add': requests_add, 'requests_done': requests_done}
json.dump(b, open(os.path.join(REPO, 'app/seed/batches/batchA7.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(new_plants), 'new plants,', len(updates), 'updates,', len(existing_photos), 'photos,', len(requests_add), 'requests')
