"""Batch B1 (1.27.1): Ethan's night photos of November 1, 2026, from the porch bench.
- Two new pages: philodendrons with white hand-written stakes reading "Philodendron Royal Queen" (Ethan: no pages yet; they have been
  in direct sun for a while, so the orange colour may be sun-faded).
- New page: Alocasia 'Frydek' (yellow barcode tag), a third Alocasia with velvety leaves. Ethan: this is the "fuzzy pale-green-leaved
  plant" on the Still to photograph list, which is marked done.
- New page: the pot with the 'Monstera' tag (maroon nursery pot in a grey pot): several young, unsplit Monstera deliciosa plants.
  Ethan sent these photos the same day; it closes "Pot with the 'Monstera' tag" on the Still to photograph list.
- New page: the climbing aroid beside the Monstera: Rhaphidophora tetrasperma, 'Mini Monstera' (Costa Farms tag), on bamboo stakes.
  Closes "Climbing aroid beside the Monstera"; batch B1 also adds its uses, partners and propagation.
- New photos on P-054 fountain grass, P-064 iris, P-083 curly fern and P-084 young Monstera, with guarded health notes.
The new pages start from P-055 (Black Cardinal, a self-heading philodendron) and P-061 (Alocasia) for care and About details.
Run: python3 dev/seed_src/build_batchB1.py <plants.db with batches up to A9>"""
import json, os, sqlite3, sys
from PIL import Image, ImageOps
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
RAW, PH = REPO + '/dev/photos-raw/rawB1', REPO + '/app/seed/photos'
c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
row = lambda code: c.execute('SELECT * FROM plants WHERE code=?', (code,)).fetchone()
first_photo = lambda code: c.execute('SELECT file FROM photos WHERE plant_id=(SELECT id FROM plants WHERE code=?) ORDER BY id LIMIT 1', (code,)).fetchone()[0]
L = lambda *x: '\n'.join(x)
D = 'November 1'
SRC = f'Ethan, {D}'
FIELD_NAMES = [r[1] for r in c.execute('PRAGMA table_info(plants)')
               if r[1] not in ('id', 'code', 'version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by')]

def pic(key):
    f = f'img_b1_{key}.jpg'
    im = ImageOps.exif_transpose(Image.open(f'{RAW}/{key}.jpg')); im.thumbnail((1280, 1280)); im.convert('RGB').save(f'{PH}/{f}', 'JPEG', quality=80, optimize=True)
    return f
def photos(items):
    return [{'file': pic(k), 'caption': f'{D}: {cap}', 'primary': i == 0, 'source': SRC} for i, (k, cap) in enumerate(items)]

new_plants, existing_photos, updates = [], [], []
def update(code, note, **new):
    r = row(code)
    s = {f: [r[f], v] for f, v in new.items() if r[f] != v}
    updates.append({'code': code, 'name': r['common_name'], 'photos': [first_photo(code)], 'note': note, 'set': s})

SPURGE = 'Spotted spurge (a weed with thin red stems and small maroon-spotted leaves) is growing in the pot.'
SPURGE_STEP = 'Pull the spotted spurge with gloves on, roots and all, before it sets more seed. Its milky sap irritates skin and is toxic to pets.'
RQ_BASIS = ("A white hand-written stake reads 'Philodendron Royal Queen'. It is a self-heading philodendron with thick red-pink leaf stalks. "
            "A true 'Royal Queen' (a Philodendron erubescens hybrid) has very dark, burgundy-black leaves; these are orange, peach and "
            "yellow-green. Ethan says it has been in direct sun for a while, which can bleach dark philodendron leaves toward bronze and "
            "yellow, so the tag may be right. The colours fit 'Prince of Orange' just as well.")
RQ_ALT = L("Philodendron 'Royal Queen' (as tagged, sun-faded)", "Philodendron 'Prince of Orange'", "Philodendron 'McColley's Finale'",
           "Philodendron 'Black Cardinal' (also bronze when young)")
RQ_IMPROVE = L('The colour of the next new leaf after a few weeks in bright shade (indoors, or the covered porch)',
               'Where it was bought, and the store tag or receipt')
RQ_STEPS = L('Move it out of direct sun into bright shade (indoors, or the covered porch). Sun bleaches the leaves and scorches them.',
             'Bring it in before nights fall below 55°F.', 'Water when the top inch of mix is dry; feed at half strength in spring and summer.')
base = {k: row('P-055')[k] for k in FIELD_NAMES}

# ---------------------------------------------------------------- new: the taller one, roots showing on top
a = dict(base)
a.update(common_name="Philodendron 'Royal Queen' (tag; taller, roots on top)", scientific_name="Philodendron 'Royal Queen' (tagged; possibly sun-faded)",
         aliases="Tag: 'Philodendron Royal Queen' (hand-written)", id_confidence=55, id_basis=RQ_BASIS, id_alternatives=RQ_ALT, id_improve=RQ_IMPROVE,
         location='Porch bench, in direct sun', container='Clear nursery pot inside a grey fluted pot, bark and perlite mix, white hand-written stake',
         site='Outdoors', health_rating='Fair', pot_size='Small: fits in a bucket', leaf_type='Large leaves',
         health_summary=('Growing, with several crowns and new leaves, but the leaves are sun-faded to orange and yellow-green, the lower stem '
                         'is bare with dry papery leaf bases, and roots are showing on top of the mix.'),
         health_observations=L('Leaves orange, peach and yellow-green (likely sun-faded)', 'Thick red-pink leaf stalks', 'Two or more crowns',
                               'Dry, papery old leaf sheaths at the base (normal)', 'Roots exposed on top of the mix', 'One leaf with a small hole',
                               'Two small rounded seedlings (weeds) at the base'),
         health_steps=L('Cover the exposed roots with an inch of fresh mix, or repot a little deeper.', RQ_STEPS,
                        'Pull the small seedlings at the base.'),
         pests_current='', notes=f'Photographed on {D}, 2026, on the porch bench. Ethan: no page until now.')
a['photos'] = photos([('rq_a_1', 'tall philodendron with its stake, sun-faded leaves'), ('rq_a_2', 'stem base: exposed roots and dry leaf sheaths')])
new_plants.append(a)

# ---------------------------------------------------------------- new: the compact one
b = dict(base)
b.update(common_name="Philodendron 'Royal Queen' (tag; compact)", scientific_name="Philodendron 'Royal Queen' (tagged; possibly sun-faded)",
         aliases="Tag: 'Philodendron Royal Queen' (hand-written)", id_confidence=55, id_basis=RQ_BASIS, id_alternatives=RQ_ALT, id_improve=RQ_IMPROVE,
         location='Porch bench, in direct sun', container='Clear nursery pot inside a grey fluted pot, white hand-written stake',
         site='Outdoors', health_rating='Fair', pot_size='Small: fits in a bucket', leaf_type='Large leaves',
         health_summary='Compact and full, with firm leaves, but they are sun-faded to orange and yellow-green, and a few have small spots or nicks.',
         health_observations=L('Leaves orange, peach and yellow-green (likely sun-faded)', 'New red-pink leaves at the centre',
                               'Small pale spots on a few leaves (sun or water marks)', 'One leaf with a nicked edge'),
         health_steps=RQ_STEPS, pests_current='', notes=f'Photographed on {D}, 2026, on the porch bench. Ethan: no page until now.')
b['photos'] = photos([('rq_b_1', "compact philodendron with its 'Royal Queen' stake"), ('rq_b_2', 'from above'), ('rq_b_3', 'from the side, the stake in front')])
new_plants.append(b)

# ---------------------------------------------------------------- new: Alocasia 'Frydek'
fr = {k: row('P-061')[k] for k in FIELD_NAMES}
fr.update(common_name="Alocasia 'Frydek'", scientific_name="Alocasia micholitziana 'Frydek'", aliases="Green velvet Alocasia; tag: 'Alocasia Frydek'",
          id_confidence=85,
          id_basis=("The yellow barcode tag reads 'Alocasia Frydek', and the leaves fit it: arrow-shaped, velvety (Ethan felt them), with a "
                    "pale midrib and pale main veins. Frydek leaves are usually deep green; these are lighter, which fits a young plant in "
                    "bright light. It is a third Alocasia, separate from P-056 and P-061."),
          id_alternatives=L("Alocasia micholitziana 'Frydek'", "Alocasia 'Green Velvet' (a trade name for the same plant)", "Alocasia 'Maharani' (thicker, grey leaves; less likely)"),
          id_improve=L('A daylight photo of a full-grown leaf'),
          location='Porch bench, on a terracotta saucer', container='Black nursery pot on a square terracotta saucer, with its yellow barcode tag',
          site='Outdoors', health_rating='Fair', pot_size='Small: fits in a bucket', leaf_type='Large leaves',
          health_summary=('Putting out several new leaves, but they are lighter than a Frydek should be, one has a dry pale patch at the tip, '
                          'and spotted spurge is spreading over the pot.'),
          health_observations=L('Velvety arrow-shaped leaves with pale midribs', 'Several new leaves and shoots', 'Leaves paler green than usual for Frydek',
                                'One leaf with a dry, pale patch at its tip', SPURGE),
          health_steps=L(SPURGE_STEP, 'Give it bright shade, not direct sun: Frydek leaves bleach and scorch in sun.',
                         'Keep the mix lightly moist, never soggy; Alocasias rot in cold wet soil.',
                         'Bring it in before nights fall below 60°F; it may drop leaves in winter and regrow from the corm in spring.',
                         'Wipe the leaves now and then and check the undersides for spider mites, which love Alocasias.'),
          pests_current='Spotted spurge (weed) in the pot.', notes=f"Photographed on {D}, 2026. Ethan: the third Alocasia, and the 'fuzzy pale-green-leaved plant' on the photo list.")
fr['photos'] = photos([('fry_1', 'from above, on its saucer'), ('fry_2', "the yellow tag: 'Alocasia Frydek'"), ('fry_3', 'close up: velvety leaves, pale veins, spurge in the pot'),
                       ('fry_4', 'from above, the spurge spreading over the rim'), ('fry_5', 'new leaves and shoots')])
new_plants.append(fr)

# ---------------------------------------------------------------- new: the maroon pot with the 'Monstera' tag
mm = {k: row('P-049')[k] for k in FIELD_NAMES}
mm.update(common_name="Monstera, young (maroon pot, 'Monstera' tag)", scientific_name='Monstera deliciosa (young, probable)',
          aliases="Store tag: 'Monstera' (water once a week; medium to bright indirect light; 65-85°F)", id_confidence=75,
          id_basis=("The printed store tag reads 'Monstera'. Many slim green stalks come up close together, each with one glossy, heart-shaped, "
                    "unsplit leaf, and each stalk has a winged sheath at its base: the way young Monstera deliciosa grown from seed looks before "
                    "its leaves start to split. Stores often plant several seedlings in one pot."),
          id_alternatives=L('Monstera deliciosa (young, seed-grown)', 'Monstera borsigiana (the smaller, faster form of deliciosa)',
                            'Rhaphidophora tetrasperma (less likely: its young leaves are narrower)'),
          id_improve=L('A photo of the next leaf: splits or holes would confirm deliciosa'),
          location='Porch bench (shelf with the yellow edge)', container="Maroon nursery pot inside a grey pot, peat and perlite mix, printed 'Monstera' tag",
          site='Outdoors', health_rating='Good', pot_size='Small: fits in a bucket', leaf_type='Large leaves',
          health_summary=('Healthy and full: many young plants with glossy green leaves. Several old stalks have been cut or broken off near the '
                          'base, and the pot is crowded.'),
          health_observations=L('Many young stalks in one pot, each with a heart-shaped unsplit leaf', 'Glossy, firm leaves; a few pale from bright light',
                                'Several cut or broken stalk stubs at the base', 'A few dry old leaf sheaths', 'Mix looks evenly moist'),
          health_steps=L('Give it bright light but not hours of direct afternoon sun, which pales and scorches the leaves.',
                         'Bring it in before nights fall below 55°F.', 'Water when the top inch is dry; let the outer pot drain so it never stands in water.',
                         'In spring, split it into two or three pots, or move it to a bigger pot with a moss pole: crowded seedlings stay small.',
                         'Pull off the dry sheaths and stubs once they come away easily.'),
          pests_current='', notes=f"Ethan's photos of {D}, 2026: the 'maroon Monstera pot' on the photo list.")
mm['photos'] = photos([('mm_1', "the whole plant in its maroon pot"), ('mm_2', "the 'Monstera' tag"), ('mm_3', 'from above, heart-shaped young leaves'),
                       ('mm_4', 'stalks and stubs at the base'), ('mm_5', 'the tag from the other side')])
new_plants.append(mm)

# ---------------------------------------------------------------- new: Mini Monstera (the climbing aroid beside the Monstera)
rt = {k: row('P-049')[k] for k in FIELD_NAMES}
rt.update(common_name="Mini Monstera (Rhaphidophora tetrasperma)", scientific_name='Rhaphidophora tetrasperma',
          aliases="Mini Monstera; Monstera ginny; tag: Costa Farms 'Mini Monstera, Collector's Plant' (TT-37)", id_confidence=95,
          id_basis=("The Costa Farms tags read 'Mini Monstera' and 'Rhaphidophora tetrasperma', and the plant fits: a climbing vine with "
                    "small, deeply split leaves with a few holes near the midrib, thick green stems with aerial roots, tied to bamboo stakes. "
                    "It is not a true Monstera."),
          id_alternatives=L('Rhaphidophora tetrasperma', 'Monstera adansonii (holes instead of splits; less likely)'),
          id_improve='', location='Porch bench, beside the Monstera', container='Clear nursery pot on a terracotta saucer, chunky bark mix, two bamboo stakes with plant tape',
          site='Outdoors', health_rating='Fair', pot_size='Small: fits in a bucket', leaf_type='Small or many leaves',
          health_summary=('Alive and putting out new split leaves from the base, but the main stems have been cut back and lost most of their '
                          'leaves, and the oldest stem section is dry and papery.'),
          health_observations=L('A cluster of new, split leaves low on the plant', 'Main stems cut back to bare green canes with aerial roots',
                                'Oldest stem section brown, dry and papery', 'Stems held to bamboo stakes with plant tape', 'Chunky bark mix, fairly dry on top'),
          health_steps=L('Leave the bare green canes: each node can sprout a new leaf. Remove only stem sections that are brown and hollow.',
                         'Tie the new growth up the stake as it lengthens; it climbs and gets bigger leaves when it can grip something (a moss pole is best).',
                         'Bright light, but not hours of direct afternoon sun.', 'Bring it in before nights fall below 50°F (the tag says keep above 50°F).',
                         'Water when the top inch is dry, about weekly in summer and less in winter.'),
          pests_current='', notes=f"Ethan's photos of {D}, 2026: the 'climbing aroid beside the Monstera' on the photo list.")
rt['photos'] = photos([('rt_1', 'new split leaves in Ethan\'s hand'), ('rt_2', 'the cut-back stems on bamboo stakes, Costa Farms tag'),
                       ('rt_3', "tag: 'Mini Monstera, Collector's Plant'"), ('rt_4', "tag back: 'Rhaphidophora tetrasperma', bright light, weekly water, keep above 50°F")])
new_plants.append(rt)

# ---------------------------------------------------------------- new photos on pages that already exist
for code, items in (('P-054', [('grass_1', 'mostly dried to straw, some burgundy blades still green'), ('grass_2', 'from above, one plume left')]),
                    ('P-064', [('iris_1', 'leaf tips browning, pine straw on top'), ('iris_2', 'from the side, brown tips and new fans')]),
                    ('P-084', [('mon_1', 'from the side'), ('mon_2', 'young leaves with notches and holes'), ('mon_3', 'from above'), ('mon_4', 'the whole pot')]),
                    ('P-083', [('fern_1', 'mostly dead fronds, new curly frond by the stake'), ('fern_2', 'close up: a fresh green curly frond and spurge seedlings')])):
    for k, cap in items:
        existing_photos.append({'code': code, 'file': pic(k), 'caption': f'{D}: {cap}', 'primary': False, 'source': SRC})

update('P-054', 'Photos of November 1 (batch B1)', health_rating='Fair',
       health_summary="Mostly dried to straw for the season; some burgundy blades are still green. 'Rubrum' does not survive a hard freeze.",
       health_steps=L('Cut the dry blades back to the green ones, or to about 6 inches if all of it browns.',
                      'Bring the pot into a garage or the house before a hard freeze (below about 25°F) if you want to keep it; water it a little once a month there.',
                      'In spring, cut it back to a few inches and feed it once growth starts.'))
update('P-064', 'Photos of November 1 (batch B1)',
       health_summary='Healthy fans of leaves. The browning tips are normal autumn dieback, not a disease.',
       health_steps=L('Cut the brown tips off with clean scissors.', 'Pull the pine straw back from the rhizomes: bearded iris rhizomes need sun on their tops.',
                      'Water only when the mix is dry; let the pot drain.'))
update('P-083', 'Photos of November 1 (batch B1)', health_rating='Poor',
       health_summary='Still mostly dead, crisped fronds, but fresh bright-green curly fronds are coming from the crown, so it is recovering.',
       pests_current='Spotted spurge (weed) in the pot.',
       health_steps=L('Cut off the dead fronds at the base so light reaches the new ones.', 'Keep the mix evenly moist; never let it dry out completely.',
                      SPURGE_STEP, 'Bring it in before nights fall below 50°F.'))

OX = 'Contains calcium oxalate crystals: chewing it burns the mouth. Keep it away from pets and children.'
RT_FACTS = {'key': 'rhaphidophora tetrasperma', 'name': 'Rhaphidophora tetrasperma', 'kind': 'plant', 'data': {
    'summary': "A fast climbing aroid with split leaves, sold as 'Mini Monstera'; grown for looks.",
    'uses': [{'kind': 'Ornamental', 'text': 'Climbs a pole or trellis indoors; the leaves split more as it climbs.', 'caution': OX}],
    'compost': {'verdict': 'Good', 'why': 'Soft leaves and stems rot quickly; wear gloves when chopping it.'},
    'partners_good': [{'name': 'Monstera', 'sci': 'Monstera', 'why': 'Same light, water and humidity; both climb a moss pole.', 'evidence': 'Same needs'},
                      {'name': 'Philodendron', 'sci': 'Philodendron', 'why': 'Same needs.', 'evidence': 'Same needs'}],
    'partners_bad': [{'name': 'Cacti and other succulents', 'sci': 'Opuntia', 'why': 'They need full sun and dry soil, which this plant does not.', 'evidence': 'Different needs'}],
    'deters': [], 'attracts': [],
    'propagation': [{'method': 'Stem cuttings', 'when': 'Spring to summer', 'how': 'Cut below a node with an aerial root and root it in water or moss; new leaves come in 3 to 6 weeks.'},
                    {'method': 'Layering', 'when': 'Spring to summer', 'how': 'Pin a node onto moist mix in a second pot; cut it free once it has rooted.'}],
    'breeding': {'text': 'It rarely flowers indoors, so crossing it at home is not practical.', 'cross_genera': [], 'patent': '', 'same_genus': False},
    'sources': [{'title': 'NC State Extension Plant Toolbox', 'url': 'https://plants.ces.ncsu.edu/find_a_plant/?q=Rhaphidophora+tetrasperma'},
                {'title': 'Wikipedia', 'url': 'https://en.wikipedia.org/w/index.php?search=Rhaphidophora+tetrasperma'}]}}

b1 = {'id': 'B1', 'created': '2026-11-01', 'author': "Claude (Ethan's porch bench photos, Nov 1, 2026)",
      'plants': new_plants, 'existing_photos': existing_photos, 'updates': updates,
      'to_photograph_done': ['Fuzzy pale-green-leaved plant', "Pot with the 'Monstera' tag", 'Climbing aroid beside the Monstera'],
      'species_facts_add': [RT_FACTS]}
json.dump(b1, open(os.path.join(REPO, 'app/seed/batches/batchB1.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(new_plants), 'new plants,', len(updates), 'updates,', len(existing_photos), 'photos')
