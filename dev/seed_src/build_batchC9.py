"""Batch C9 (1.57.0): Ethan's repotted moth orchid from his mother's house in Baraboo, Wisconsin (photos of July 31, 2026; told to Claude on November 11).

A new page, since the plant had none. Ethan's account (chat, November 11), dated July 31 like his photos: he removed the rotted roots, set the healthy aerial roots
so most of them are in the medium instead of hanging out of the pot, drilled drainage holes in the grey pot (it had none), and
the medium is almost entirely orchid bark. The page starts from the other moth orchid's care profile (the white geometric pot:
temperature, light, humidity, feeding, pests) and says what is different about this plant: how it grows now, the repot, the photos.
The repot is logged as Repotted on 2026-07-31 with the bark mix it was done with (the batch can carry a care log and a pot mix
for a new page: 'care' and 'pot_mix' on the plant, see apply_batches). Photos: all from July 31 (before and after). The page itself ('dated') is dated July 31, not the day it was added.
Run: python3 dev/seed_src/build_batchC9.py <plants.db with batches up to C7>"""
import json, os, sqlite3, sys
from PIL import Image, ImageOps
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
RAW, PH = REPO + '/dev/photos-raw/rawC9', REPO + '/app/seed/photos'
c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
FIELD_NAMES = [r[1] for r in c.execute('PRAGMA table_info(plants)')
               if r[1] not in ('id', 'code', 'version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by')]
base = c.execute("SELECT * FROM plants WHERE common_name='Moth orchid (white geometric pot)'").fetchone()
assert base, 'run this on a database with batch B8 applied'
L = lambda *x: '\n'.join(x)
D, SRC = 'July 31', 'Ethan, July 31'

def pic(key):
    f = f'img_c9_{key}.jpg'
    im = ImageOps.exif_transpose(Image.open(f'{RAW}/{key}.jpg')).convert('RGB'); im.thumbnail((1280, 1280)); im.save(f'{PH}/{f}', 'JPEG', quality=80, optimize=True)
    return f
photos = [
    {'file': pic('after_front'), 'caption': f'{D}: after the repot, from the front: roots set into the bark, the old stake and a clip holding the new upright leaf', 'primary': True, 'source': SRC},
    {'file': pic('after_side'), 'caption': f'{D}: after the repot, from the side: a few healthy roots over the rim', 'primary': False, 'source': SRC},
    {'file': pic('crown_roots'), 'caption': f'{D}: close up of the crown: fresh green root tips, dried leaf bases beside the stake', 'primary': False, 'source': SRC},
    {'file': pic('crown_clip'), 'caption': f'{D}: close up of the crown with the clip on the upright leaf; dried, browning leaf bases to watch for rot', 'primary': False, 'source': SRC},
    {'file': pic('before'), 'caption': 'July 31: before the repot: no drainage holes, on a white saucer, roots hanging out of the pot and over the rim', 'primary': False, 'source': 'Ethan, July 31'},
]
p = {k: base[k] for k in FIELD_NAMES}
p.update(
    common_name='Moth orchid (grey pot, from Baraboo)', scientific_name='Phalaenopsis hybrid',
    aliases='Baraboo orchid (from Ethan\'s mother\'s house in Baraboo, Wisconsin)',
    site='Covered porch', location="At his mother's house in Baraboo, Wisconsin (last seen July 31, 2026, on a covered porch)",
    home_near={'lat': 43.4711, 'lon': -89.7443},
    container='Grey plastic pot with drainage holes (drilled July 31), almost entirely orchid bark, an old wooden flower stake with a clip',
    grow_kind='Soil mix', reservoir='Drains freely', mix_wants='Fast-draining',
    id_confidence=85,
    id_basis=("Broad, thick, glossy strap-shaped leaves in two opposite rows from a single short stem, and thick silver-green aerial roots with "
              "bright green growing tips: a moth orchid (Phalaenopsis). There is no tag and no flower in the photos, so the hybrid and its "
              "flower colour are not known. It came from Ethan's mother's house in Baraboo, Wisconsin."),
    id_alternatives=L('Phalaenopsis hybrid (store orchid)', 'Doritaenopsis (an older name for some hybrids)'),
    id_improve=L('A photo of the flowers when it blooms (colour, size, markings)', 'Any tag or the receipt, if his mother has it'),
    health_rating='Fair',
    health_summary=("As of July 31, 2026 (Ethan has not seen it since). Repotted July 31: rotted roots removed, drainage holes added, healthy roots set into orchid bark. The leaves are firm and glossy "
                    "with a reddish tint at the edges, and there are fresh green root tips, so it is putting out new roots. There is no flower spike and "
                    "no keiki right now, and dried, browning leaf bases at the crown need watching for rot."),
    health_observations=L('Leaves broad, glossy and firm, with reddish edges (can mean strong light)', 'Fresh bright-green root tips after the repot',
                          'Healthy silver-green roots, most now in the bark; a few rest over the rim, which is normal',
                          'Rotted roots removed at the repot (July 31)', 'Dried, brown leaf bases at the crown beside the stake',
                          'No flower spike or keiki seen', 'The pot had no drainage holes until July 31'),
    health_steps=L('It is a tropical orchid and this is Wisconsin: it must be indoors, in a bright window, well before nights fall below 55°F.',
                   'Water when the bark is dry and the roots look silver; water at the pot edge, not into the crown.',
                   'Blot any water out of the crown with a paper towel, and keep the leaf bases in the crown dry.',
                   'Let a few aerial roots stay in open air; do not bend or cram them into the bark.',
                   'Check the crown and the roots when next seen; trim dried leaf bases only once they come away easily.',
                   'Check whether the old flower spike is still green: a live node can grow a keiki, with keiki paste on it.',
                   'Put a saucer or catch pot under the pot, and empty it after watering.'),
    pests_current='',
    notes=("It lives at Ethan's mother's house in Baraboo, Wisconsin, and Ethan has not seen it since July 31, 2026, so its health and spot here are as of then. Photographed July 31, 2026, before and after the repot. "
           "Identified from the photos alone. Moth orchids do not divide, so a keiki on an old flower spike is the way to propagate it."),
    care=[{'kind': 'repot', 'done_on': '2026-07-31',
           'note': 'Removed the rotted roots, set the healthy aerial roots into the mix, drilled drainage holes in the grey pot; almost entirely orchid bark (Ethan, July 31)'}],
    pot_mix={'mixed_on': '2026-07-31', 'parts': [{'key': 'orchid-bark', 'parts': 1}],
             'notes': 'Almost entirely orchid bark; the rest is not recorded (Ethan, July 31); he does not know what else is in it. Grey pot with drainage holes added (no saucer in the after photos).'},
    requests=[{'key': 'c9-orchid-update', 'kind': 'question',
               'text': "Next time you see it, or ask your mother: where is it now (indoors, in a bright window?), is the old flower spike still green (a live node can grow a keiki), what else is in the bark mix, and has it flowered since July?"}],
    dated='2026-07-31', photos=photos)
batch = {'id': 'C9', 'created': '2026-11-11', 'author': "Ethan's repotted moth orchid from Baraboo (photos of July 31, 2026)",
         'homes_add': [{'name': 'Baraboo, WI', 'lat': 43.4711, 'lon': -89.7443, 'tz': 'America/Chicago'}], 'plants': [p]}
json.dump(batch, open(os.path.join(REPO, 'app/seed/batches/batchC9.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('wrote batchC9.json:', len(photos), 'photos')
