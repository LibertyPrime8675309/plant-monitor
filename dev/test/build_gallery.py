"""Builds the layout preview gallery (1.26.0) from shots_all.py output folders.
python3 dev/test/build_gallery.py OUTDIR AFTER_DIR[,AFTER_DIR...] [BEFORE_DIR]
GALLERY_TEXT=file.json gives the page its own words (title, intro, notes, the names of the two layouts, a line about each page): see
the top of the script in gallery_template.html. Without it the page reads as the 1.26 review did.
Writes OUTDIR/index.html and OUTDIR/data/<page>__<device>.json (each picture as a data: URI, WebP), one file per page and device,
so the page only loads the pictures being looked at."""
import base64, io, json, os, sys
from PIL import Image
OUT = sys.argv[1]; AFTER = sys.argv[2].split(','); BEFORE = sys.argv[3] if len(sys.argv) > 3 else ''
os.makedirs(os.path.join(OUT, 'data'), exist_ok=True)
WIDTH = {'pc1080': 1200, 'pc1440': 1200, 'ipad6p': 680, 'ipad6l': 860, 'firep': 680, 'firel': 900, 's21u': 520, 'iphone11': 520}
def load(d):
    ix = json.load(open(os.path.join(d, 'index.json')))
    return ix, {k: dict(v, path=os.path.join(d, k)) for k, v in ix['shots'].items() if os.path.exists(os.path.join(d, k))}
meta = {'devices': {}, 'combos': {}, 'pages': {}}
after = {}
for d in AFTER:
    ix, sh = load(d); after.update(sh)
    for k in meta: meta[k].update(ix[k])
before = load(BEFORE)[1] if BEFORE else {}
def uri(path, dev):
    im = Image.open(path).convert('RGB'); w = WIDTH.get(dev, 800)
    if im.width > w: im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'WEBP', quality=50, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode(), im.width, im.height
bundles, have = {}, {}
for src, tag in ((after, 'after'), (before, 'before')):
    for k, v in src.items():
        key = f"{v['page']}__{v['device']}"
        u, w, h = uri(v['path'], v['device'])
        bundles.setdefault(key, {}).setdefault(tag, {})[v['combo']] = {'src': u, 'w': w, 'h': h, 'screens': v['screens'], 'sideways': v['sideways']}
        have.setdefault(key, {}).setdefault(tag, []).append(v['combo'])
total = 0
for key, b in bundles.items():
    s = json.dumps(b, separators=(',', ':')); total += len(s)
    open(os.path.join(OUT, 'data', key + '.json'), 'w').write(s)
# the order Ethan reads them in: computers, then tablets, then phones
DEV_ORDER = ['pc1080', 'pc1440', 'ipad6l', 'ipad6p', 'firel', 'firep', 's21u', 'iphone11']
got_dev = {k.split('__')[1] for k in have}; got_combo = {c for h in have.values() for c in h.get('after', [])}     # only what there are pictures of
manifest = {'devices': [[k, meta['devices'][k]] for k in DEV_ORDER if k in meta['devices'] and k in got_dev],
            'combos': [[k, meta['combos'][k]] for k in ('usual', 'largest', 'stress') if k in meta['combos'] and k in got_combo],
            'pages': [[k, v] for k, v in meta['pages'].items()], 'have': have}
tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gallery_template.html')).read()
text = json.load(open(os.environ['GALLERY_TEXT'])) if os.environ.get('GALLERY_TEXT') else None
if text and text.get('order'): manifest['pages'].sort(key=lambda kv: text['order'].index(kv[0]) if kv[0] in text['order'] else 99)
open(os.path.join(OUT, 'index.html'), 'w').write(tpl.replace('/*MANIFEST*/null', json.dumps(manifest, separators=(',', ':'))).replace('/*TEXT*/null', json.dumps(text, separators=(',', ':')) if text else 'null'))
print(f'{len(bundles)} files, {total / 1e6:.1f} MB of data')
