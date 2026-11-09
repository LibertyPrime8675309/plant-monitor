"""Plant record vision service (1.18.0): identifies plants in camera pictures with BioCLIP 2.5 Huge (or BioCLIP 2), on this computer.

It runs in its own container next to the app (docker-compose.yml, service "vision"). Only the app talks to it, on the
private Docker network: it is never published to the computer, the home network or Tailscale.

What it does
- On first start it downloads, into /cache (the data/vision folder):
  - the BioCLIP model from Hugging Face (MIT licence);
  - BioCLIP's name fingerprints for every plant species it knows (TreeOfLife-200M, CC0), plant rows only;
  - the USDA PLANTS state lists (public domain), to tell which species grow in Texas and in the US.
  /status says how far it has got.
- It fingerprints every photo in Plant record (read-only /data/photos and /data/plants.db) and keeps the fingerprints in
  /cache, so a camera picture can be compared with them. New photos are picked up within a minute.
- POST /identify with a picture returns the closest plants in the records, with a confidence worked out from how far ahead
  the best match is, and the likeliest species from the chosen list (Texas, US, plants with a common name, or worldwide).
- GET /names?q= searches the species list for the library page.
- 1.39.0: a picture is looked at three ways (as is, letterboxed whole, and its middle), several pictures of one plant are
  averaged (fields image + images), and the names are weighted by a prior: species and genera already named in the record,
  houseplant genera, the state's plants, and the record's own photos that look like the picture (a new pot of a plant you
  have). Ten names come back, each with the reasons ('basis') for its lift. VISION_PRIOR=0 turns the prior off.
Nothing leaves the computer except the downloads above."""
import csv, html, io, json, math, os, re, sqlite3, threading, time, urllib.request
import numpy as np
from flask import Flask, request, jsonify, abort

CACHE = os.environ.get('VISION_CACHE', '/cache')
DATA = os.environ.get('DATA_DIR', '/data')
MODEL = os.environ.get('VISION_MODEL', 'bioclip-2.5-vith14')   # BioCLIP 2.5 Huge; or bioclip-2 (smaller and faster, weaker at naming species)
os.environ.setdefault('HF_HOME', os.path.join(CACHE, 'hf'))
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
EMB_BASE = 'https://huggingface.co/datasets/imageomics/TreeOfLife-200M/resolve/main/embeddings/'
USDA_BASE = 'https://huggingface.co/datasets/Solshine/USDA_Plants_Database_By_State_WorkingGroupList/resolve/main/'
STATES = ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
          'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
          'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'NewHampshire', 'NewJersey', 'NewMexico', 'NewYork', 'NorthCarolina',
          'NorthDakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'PuertoRico', 'RhodeIsland', 'SouthCarolina', 'SouthDakota', 'Tennessee',
          'Texas', 'Utah', 'Vermont', 'VirginIslands', 'Virginia', 'Washington', 'WestVirginia', 'Wisconsin', 'Wyoming']
SCOPES = {'common': 'Plants with a common name, plus all US plants', 'texas': 'Texas plants', 'us': 'US plants', 'world': 'All plants worldwide',
          'fungi': 'Fungi worldwide: mushrooms, lichens and moulds'}

app = Flask(__name__)
S = {'state': 'starting', 'step': 'Starting', 'done': 0, 'total': 0, 'error': None, 'model': MODEL}
LOCK = threading.Lock()
M = {}            # model, preprocess, logit scale
NAMES = {}        # rows, emb (float16), masks, index by genus species
PHOTOS = {'files': [], 'codes': [], 'emb': None, 'mtime': 0}

def say(step, done=0, total=0, state='setting up'):
    S.update(step=step, done=done, total=total, state=state)
    print(f'[vision] {step}' + (f' {done}/{total}' if total else ''), flush=True)

def get(url, rng=None, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'Range': 'bytes=%d-%d' % rng} if rng else {})
            with urllib.request.urlopen(req, timeout=180) as r: return r.read()
        except Exception:
            if i == tries - 1: raise
            time.sleep(3 + 5 * i)

# ---------------------------------------------------------------- downloads (once)
def fetch_names(kingdom='Plantae', stem='names', J=None):
    """One kingdom's rows of BioCLIP's name fingerprints: <stem>.json and <stem>.npy (N x D float16, unit length).
    Plants are names.*; from 1.22.0 fungi are fungi.* (fetched the same way, so an existing plant download is kept)."""
    d = os.path.join(CACHE, MODEL); os.makedirs(d, exist_ok=True)
    out_n, out_e = os.path.join(d, stem + '.json'), os.path.join(d, stem + '.npy')
    if os.path.exists(out_n) and os.path.exists(out_e): return out_n, out_e, J
    word = 'plant' if kingdom == 'Plantae' else 'fungus'
    say(f'Downloading the {word} species list')
    if J is None: J = json.loads(get(EMB_BASE + f'txt_emb_{MODEL}.json'))
    idx = [i for i, x in enumerate(J) if x[0][0] == kingdom]
    a, b = idx[0], idx[-1] + 1
    if idx != list(range(a, b)): raise RuntimeError(f'the {kingdom} rows of the species list are not in one block')
    npy = EMB_BASE + f'txt_emb_{MODEL}.npy'
    head = get(npy, (0, 255)).decode('latin1')
    hl = 10 + int.from_bytes(head[8:10].encode('latin1'), 'little')        # .npy v1 header length
    D = int(re.search(r"'shape': \((\d+), %d\)" % len(J), head).group(1))
    E = np.zeros((b - a, D), dtype=np.float32)
    for k in range(D):                       # stored as D rows across all taxa: take this kingdom's block of each row
        s = hl + (k * len(J) + a) * 4
        E[:, k] = np.frombuffer(get(npy, (s, s + (b - a) * 4 - 1)), dtype='<f4')
        say(f'Downloading the {word} species fingerprints', k + 1, D)
    n = np.linalg.norm(E, axis=1, keepdims=True); n[n == 0] = 1
    np.save(out_e + '.tmp.npy', (E / n).astype(np.float16)); os.replace(out_e + '.tmp.npy', out_e)
    json.dump(J[a:b], open(out_n, 'w'))
    return out_n, out_e, J

def fetch_usda():
    """{'Genus species': set of states} from the USDA PLANTS state lists (accepted names only)."""
    p = os.path.join(CACHE, 'usda_states.json')
    if os.path.exists(p): return
    where = {}
    for i, st in enumerate(STATES):
        say('Downloading the USDA state plant lists', i + 1, len(STATES))
        t = get(USDA_BASE + st + '.csv').decode('utf-8', 'replace')
        body = html.unescape(t.split('<pre>', 1)[1].split('</pre>', 1)[0]) if '<pre>' in t else t
        for r in csv.DictReader(io.StringIO(body)):
            if r.get('Synonym Symbol'): continue
            w = (r.get('Scientific Name with Author') or '').split()
            if len(w) >= 2 and w[1][:1].islower(): where.setdefault(w[0] + ' ' + w[1], {})[st] = (r.get('State Common Name') or '', r.get('Symbol') or '', r.get('Family') or '')
    json.dump(where, open(p + '.tmp', 'w')); os.replace(p + '.tmp', p)

# ---------------------------------------------------------------- PLAN.md step 5b: the plants recorded in a country (GBIF)
# For "a new find" (mode=new): no lift for the record's own plants or for houseplants; instead a lift for species that GBIF has
# occurrences of in the site's country. The list ({'Genus species': count}) is fetched once per country into gbif-<CC>.json,
# in the background the first time a request names the country; until it is there the answer says so and no country lift applies.
COUNTRY = {}      # CC -> {'state': 'fetching'|'ready'|'error', 'mask': bool array over NAMES rows, 'weight': float array, 'species': int}
CLOCK = threading.Lock()
def country_path(cc): return os.path.join(CACHE, f'gbif-{cc}.json')
def country_fetch(cc):
    try:
        from gbif_country import fetch_country                 # beside this file (vision/gbif_country.py)
        sp = fetch_country(cc, lambda m, n: print(f'[vision] {m}', flush=True))
        json.dump(sp, open(country_path(cc) + '.tmp', 'w')); os.replace(country_path(cc) + '.tmp', country_path(cc))
        country_load(cc)
    except Exception as e:
        print('[vision] country list failed', cc, repr(e), flush=True)
        COUNTRY[cc] = {'state': 'error', 'error': f'{type(e).__name__}: {e}', 'mask': None, 'weight': None, 'species': 0}
def country_load(cc):
    counts = json.load(open(country_path(cc)))
    mask = np.array([s in counts for s in NAMES['sp']])
    # the lift grows with how often the species is recorded there: full at 1,000 records or more, a third at 10
    w = np.array([min(1.0, math.log10(counts.get(s, 0) + 1) / 3) if s in counts else 0.0 for s in NAMES['sp']], dtype=np.float32)
    COUNTRY[cc] = {'state': 'ready', 'mask': mask, 'weight': w, 'species': int(mask.sum())}
def country(cc):
    """The country's entry, starting the download if needed. None when the code is missing or not two letters."""
    cc = (cc or '').strip().upper()
    if not re.fullmatch(r'[A-Z]{2}', cc) or not NAMES: return None
    with CLOCK:
        if cc in COUNTRY: return COUNTRY[cc]
        if os.path.exists(country_path(cc)):
            try: country_load(cc); return COUNTRY[cc]
            except Exception as e: print('[vision] country list unreadable', cc, repr(e), flush=True); os.remove(country_path(cc))
        COUNTRY[cc] = {'state': 'fetching', 'mask': None, 'weight': None, 'species': 0}
        threading.Thread(target=country_fetch, args=(cc,), daemon=True).start()
        return COUNTRY[cc]

def load_all():
    try:
        say('Loading the model (the first time, it downloads about %s)' % ('3.9 GB' if '2.5' in MODEL else '1.7 GB'))
        import torch, open_clip
        torch.set_num_threads(max(1, (os.cpu_count() or 2) - 1))
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file
        model, _, pre = open_clip.create_model_and_transforms('hf-hub:imageomics/' + MODEL, load_weights=False)
        # the weights are memory-mapped from the cache instead of copied: it starts faster and needs about half the memory
        model.load_state_dict(load_file(hf_hub_download('imageomics/' + MODEL, 'open_clip_model.safetensors')), assign=True)
        model.eval()
        M.update(model=model, pre=pre, torch=torch, scale=float(model.logit_scale.exp().item()))
        n_json, n_npy, J = fetch_names()
        rows = json.load(open(n_json)); emb = np.load(n_npy); n_plants = len(rows)
        try:                                     # 1.22.0: fungi too (mushrooms, lichens, moulds); the plants work without them
            f_json, f_npy, J = fetch_names('Fungi', 'fungi', J)
            rows = rows + json.load(open(f_json)); emb = np.concatenate([emb, np.load(f_npy)])
        except Exception as e:
            print('[vision] fungi not loaded:', repr(e), flush=True)
        del J
        usda_path = os.path.join(CACHE, 'usda_states.json'); fetch_usda()
        usda = json.load(open(usda_path))
        sp = [r[0][5] + ' ' + r[0][6] for r in rows]
        has = np.abs(emb).sum(1) > 0
        plant = np.arange(len(rows)) < n_plants; fung = ~plant
        common = np.array([bool(re.search(r'[A-Za-z]', r[1] or '')) for r in rows])
        in_us = np.array([s in usda for s in sp]); in_tx = np.array([s in usda and 'Texas' in usda[s] for s in sp])
        hay = [(s + ' ' + (r[1] or '') + ' ' + ' '.join({v[0] for v in usda.get(s, {}).values()})).lower() for s, r in zip(sp, rows)]
        NAMES.update(rows=rows, sp=sp, emb=emb, usda=usda, hay=hay, by_sp={s: i for i, s in enumerate(sp)},
                     masks={'world': has & plant, 'us': has & in_us & plant, 'texas': has & in_tx & plant,
                            'common': has & (common | in_us) & plant, 'fungi': has & fung}, n_plants=n_plants)
        build_browse()
        say('Fingerprinting your photos'); index_photos()
        S.update(state='ready', step='Ready')
        threading.Thread(target=watch_photos, daemon=True).start()
    except Exception as e:
        S.update(state='error', error=f'{type(e).__name__}: {e}', step='Could not start')
        print('[vision] ERROR', repr(e), flush=True)

# ---------------------------------------------------------------- your photos
def embed_one(img):
    t = M['torch']
    with t.no_grad():
        x = M['pre'](img).unsqueeze(0)
        e = M['model'].encode_image(x)[0].float().numpy()
    return e / np.linalg.norm(e)

def views_of(img):
    """1.39.0: three looks at one picture: the model's own (short side resized, the middle cut square), the whole picture
    letterboxed into a square (nothing cut off a wide shot), and the middle 60% (the plant, when it sits in the middle
    of a busy picture). Their fingerprints are averaged."""
    from PIL import Image
    w, h = img.size
    out = [img]
    if abs(w - h) > min(w, h) * 0.1:
        side = max(w, h); box = Image.new('RGB', (side, side), (128, 128, 128)); box.paste(img, ((side - w) // 2, (side - h) // 2)); out.append(box)
    cw, ch = int(w * 0.6), int(h * 0.6)
    out.append(img.crop(((w - cw) // 2, (h - ch) // 2, (w - cw) // 2 + cw, (h - ch) // 2 + ch)))
    return out

def embed(img, views=False):
    from PIL import ImageOps
    img = ImageOps.exif_transpose(img).convert('RGB')
    if not views: return embed_one(img)
    e = np.mean([embed_one(v) for v in views_of(img)], axis=0)
    return e / np.linalg.norm(e)

def embed_many(imgs):
    """Several pictures of one plant: the average of their fingerprints (each with its views)."""
    e = np.mean([embed(im, views=True) for im in imgs], axis=0)
    return e / np.linalg.norm(e)

def photo_rows():
    db = os.path.join(DATA, 'plants.db')
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=10)
    try:
        return c.execute("SELECT ph.file, p.code, COALESCE(p.scientific_name, '') FROM photos ph JOIN plants p ON p.id=ph.plant_id WHERE p.status='active' ORDER BY ph.id").fetchall()
    finally:
        c.close()

def index_photos():
    from PIL import Image
    path = os.path.join(CACHE, f'photos-{MODEL}.npz')
    known = {}
    if os.path.exists(path):
        z = np.load(path, allow_pickle=False)
        known = {f: e for f, e in zip(z['files'].tolist(), z['emb'])}
    rows = photo_rows()
    new = [f for f, _, _ in rows if f not in known and os.path.exists(os.path.join(DATA, 'photos', f))]
    def save():
        if known: np.savez(path + '.tmp.npz', files=np.array(list(known)), emb=np.stack(list(known.values()))); os.replace(path + '.tmp.npz', path)
    for i, f in enumerate(new):
        try: known[f] = embed(Image.open(os.path.join(DATA, 'photos', f)))
        except Exception as e: print('[vision] skipped', f, e, flush=True)
        if S['state'] != 'ready': say('Fingerprinting your photos', i + 1, len(new))
        if i % 25 == 24: save()                       # so a restart part way through does not start over
    files = [f for f, _, _ in rows if f in known]
    if new: save()
    with LOCK:
        PHOTOS.update(files=files, codes=[c for f, c, _ in rows if f in known], emb=np.stack([known[f] for f in files]) if files else None,
                      sp=[species_index(n) for f, _, n in rows if f in known],          # 1.39.0: which species each photo is a confirmed example of
                      mtime=os.path.getmtime(os.path.join(DATA, 'plants.db')))
        own_names()
    try: index_examples()                           # 5c: the examples people confirmed or rejected, and named mushroom finds
    except Exception as e: print('[vision] examples index', e, flush=True)
    return len(new)

def species_index(name):
    """The species list row for a plant's scientific name ('Epipremnum aureum', ignoring cultivar and author), or -1."""
    m = re.match(r"^\s*([A-Z][a-z]+)\s+([a-z][a-z\-]+)", name or '')
    if not m or m.group(2) in ('sp', 'spp', 'x', 'hybrid'): return -1
    return NAMES['by_sp'].get(m.group(1) + ' ' + m.group(2), -1) if NAMES else -1

# ---------------------------------------------------------------- PLAN.md step 5c (1.52.0): the loop
# Examples the checker learns from, beyond the record's own plant photos: what people confirmed ("This is right": kind 'yes') or
# said no to ("Not this" with a picture: kind 'no') in the app (table id_examples), and the photos of named mushroom finds. A 'yes'
# example lifts its species for pictures that look like it (the same look-alike step as the record's photos); a 'no' example lowers
# it by the same amount. Fingerprints are kept in examples-<MODEL>.npz and made once per file.
EXAMPLES = {'files': [], 'emb': None, 'sp': [], 'kind': [], 'n_yes': 0, 'n_no': 0}
def examples_rows():
    """[(file, species index, kind)] from id_examples and from named mushroom finds (kind 'yes'); only names the list knows."""
    db = os.path.join(DATA, 'plants.db')
    out = []
    try:
        c = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=10)
        try:
            if c.execute("SELECT 1 FROM sqlite_master WHERE name='id_examples'").fetchone():
                for f, n, k in c.execute("SELECT file, name, kind FROM id_examples ORDER BY id"): out.append((f, species_index(n), k))
            if c.execute("SELECT 1 FROM sqlite_master WHERE name='fungi_finds'").fetchone():
                for f, n in c.execute("SELECT ph.file, ff.scientific_name FROM fungi_photos ph JOIN fungi_finds ff ON ff.id=ph.find_id WHERE ff.status='active' AND ff.scientific_name<>'' AND ff.id_status IN ('Fairly sure', 'Confirmed by an expert') ORDER BY ph.id"):
                    out.append((f, species_index(n), 'yes'))
        finally: c.close()
    except Exception as e: print('[vision] examples', e, flush=True)
    return [(f, i, k) for f, i, k in out if i >= 0]

def index_examples():
    from PIL import Image
    path = os.path.join(CACHE, f'examples-{MODEL}.npz')
    known = {}
    if os.path.exists(path):
        z = np.load(path, allow_pickle=False)
        known = {f: e for f, e in zip(z['files'].tolist(), z['emb'])}
    rows = examples_rows()
    new = [f for f, _, _ in rows if f not in known and os.path.exists(os.path.join(DATA, 'photos', f))]
    for f in new:
        try: known[f] = embed(Image.open(os.path.join(DATA, 'photos', f)))
        except Exception as e: print('[vision] skipped example', f, e, flush=True)
    if new and known: np.savez(path + '.tmp.npz', files=np.array(list(known)), emb=np.stack(list(known.values()))); os.replace(path + '.tmp.npz', path)
    rows = [(f, i, k) for f, i, k in rows if f in known]
    with LOCK:
        EXAMPLES.update(files=[f for f, _, _ in rows], emb=np.stack([known[f] for f, _, _ in rows]) if rows else None, sp=[i for _, i, _ in rows], kind=[k for _, _, k in rows],
                        n_yes=sum(1 for _, _, k in rows if k == 'yes'), n_no=sum(1 for _, _, k in rows if k == 'no'))
    return len(new)

def own_names():
    """1.39.0: the species and genera already in the record (named plants), for the prior on what a new picture is."""
    sp = {i for i in PHOTOS.get('sp', []) if i >= 0}
    db = os.path.join(DATA, 'plants.db')
    try:
        c = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=10)
        try: names = [r[0] for r in c.execute("SELECT scientific_name FROM plants WHERE status='active'")]
        finally: c.close()
    except Exception: names = []
    gen = set()
    for n in names:
        i = species_index(n)
        if i >= 0: sp.add(i)
        m = re.match(r"^\s*([A-Z][a-z]+)", n or '')
        if m: gen.add(m.group(1))
    PHOTOS['own_sp'] = sp; PHOTOS['own_gen'] = gen

def watch_photos():
    while True:
        time.sleep(60)
        try:
            if os.path.getmtime(os.path.join(DATA, 'plants.db')) != PHOTOS['mtime']: index_photos()
        except Exception as e: print('[vision] index', e, flush=True)

# Logistic fits on 181 of Ethan's photos, leaving each one out in turn (October 2026, vision tests): (w0, w_margin, w_score).
# BioCLIP 2.5 Huge: said 80% or more for a third of the photos and was right 92% of those times. BioCLIP 2: 25%, right 87%.
CONF = {'bioclip-2.5-vith14': (0.21, 10.43, 3.2), 'bioclip-2': (-0.21, 17.29, 3.32)}
# Below this best score the picture is probably of a plant that is not in the record: with every photo of one plant left out,
# 2.5 scored under 0.65 for 28% of them, and only 2% of right answers scored that low (BioCLIP 2 scores higher overall).
NOVEL = {'bioclip-2.5-vith14': 0.65, 'bioclip-2': 0.75}

# 1.39.0: the prior. Added to a name's score (BioCLIP logits: the scale times the cosine, so a difference of 1 is about 0.01 in
# cosine, the gap between close candidates). 'own_sp': a species already named in the record; 'own_gen': its genus is;
# 'house': a genus grown as a houseplant; 'state': grows in the place's state (only for a state list); 'looks': one of the
# record's photos of a named plant looks like this picture (scaled by how close, up to the full value).
PRIOR = {'own_sp': 1.5, 'own_gen': 1.0, 'house': 0.7, 'state': 0.3, 'looks': 3.0, 'country': 1.0}
# PLAN.md step 5b: two modes. 'mine' (the default, as before): the lifts above, for "which of my plants is this?".
# 'new': a plant met somewhere, not one of the record's: no lift for the record's own species and genera, houseplants or
# look-alike photos; instead a lift for species GBIF records in the site's country (scaled by how often, see country_load).
MODES = {'mine': ('own_sp', 'own_gen', 'house', 'state', 'looks'), 'new': ('state', 'country')}
PRIOR_ON = os.environ.get('VISION_PRIOR', '1') != '0'
HOUSE = set("""Adiantum Aechmea Aeonium Agave Aglaonema Alocasia Aloe Alpinia Anthurium Aphelandra Araucaria Ardisia Asparagus Aspidistra Asplenium
Begonia Beaucarnea Billbergia Brassaia Bromelia Caladium Calathea Calliandra Carex Ceropegia Chamaedorea Chlorophytum Chrysalidocarpus Cissus Citrus
Clivia Codiaeum Coffea Coleus Colocasia Cordyline Crassula Cryptanthus Ctenanthe Curcuma Cycas Cyclamen Cyperus Davallia Dieffenbachia Dionaea
Dischidia Dracaena Dypsis Echeveria Epipremnum Episcia Euphorbia Fatsia Ficus Fittonia Gardenia Gasteria Goeppertia Guzmania Gynura Haworthia
Haworthiopsis Hedera Hibiscus Hippeastrum Howea Hoya Hypoestes Impatiens Jasminum Kalanchoe Lithops Livistona Mammillaria Maranta Medinilla
Monstera Musa Nematanthus Neoregelia Nephrolepis Nepenthes Oxalis Pachira Pachypodium Pandanus Pelargonium Peperomia Philodendron Phalaenopsis
Phlebodium Phoenix Pilea Platycerium Plectranthus Polyscias Portulacaria Pothos Radermachera Raphidophora Rhaphidophora Rhipsalis Rhododendron
Saintpaulia Sansevieria Sarracenia Saxifraga Schefflera Schlumbergera Scindapsus Sedum Selaginella Sempervivum Senecio Soleirolia Spathiphyllum
Stephanotis Strelitzia Streptocarpus Stromanthe Syngonium Tillandsia Tradescantia Vriesea Yucca Zamia Zamioculcas Zantedeschia Zingiber
Opuntia Cereus Echinocactia Echinocereus Ferocactus Gymnocalycium Astrophytum Parodia Rebutia Cylindropuntia Stapelia Huernia Adenium Plumeria
Dendrobium Cattleya Oncidium Paphiopedilum Vanda Cymbidium Lavandula Rosmarinus Salvia Ocimum Mentha Thymus Origanum Capsicum Solanum Fragaria""".split())

def prior_why(i, scope, mode='mine', C=None):
    """The reasons a name is lifted, for this mode. C is the country entry (country()) or None."""
    why, allowed = [], MODES.get(mode, MODES['mine'])
    if 'own_sp' in allowed and i in PHOTOS.get('own_sp', ()): why.append('own_sp')
    elif 'own_gen' in allowed and NAMES['rows'][i][0][5] in PHOTOS.get('own_gen', ()): why.append('own_gen')
    if 'house' in allowed and NAMES['rows'][i][0][5] in HOUSE: why.append('house')
    if 'state' in allowed and isinstance(scope, str) and scope.startswith('state:') and NAMES['sp'][i] in NAMES['usda'] and scope[6:].replace(' ', '') in NAMES['usda'][NAMES['sp'][i]]: why.append('state')
    if 'country' in allowed and C and C.get('mask') is not None and C['mask'][i]: why.append('country')
    return why
def prior_bonus(why, i, C=None):
    b = 0.0
    for w in why:
        if w == 'country': b += PRIOR['country'] * float(C['weight'][i])
        elif w not in ('looks', 'unlike'): b += PRIOR[w]
    return b

def confidence(score, margin):
    """How often the first choice was right, from tests on Ethan's own photos (October 2026): mostly the margin between
    the best plant and the next, a little the score itself. Rounded, and never shown as certain."""
    w = CONF.get(MODEL, CONF['bioclip-2.5-vith14'])
    z = w[0] + w[1] * margin + w[2] * (score - 0.85)
    return max(0.05, min(0.97, 1 / (1 + np.exp(-z))))

# ---------------------------------------------------------------- routes
@app.get('/status')
def status():
    cc = request.args.get('country'); C = country(cc) if S['state'] == 'ready' and cc else None
    return jsonify(S | {'country': ({'code': cc.upper(), 'state': C['state'], 'species': C['species']} if C else None), 'examples': {'yes': EXAMPLES['n_yes'], 'no': EXAMPLES['n_no']}} | {'photos': len(PHOTOS['files']), 'species': int(NAMES['masks']['world'].sum()) if NAMES else 0,
                        'prior': PRIOR_ON, 'named': len(PHOTOS.get('own_sp', ())), 'genera_known': len(PHOTOS.get('own_gen', ())),
                        'fungi': int(NAMES['masks']['fungi'].sum()) if NAMES else 0,
                        'scopes': {k: {'label': v, 'count': int(NAMES['masks'][k].sum()) if NAMES else 0} for k, v in SCOPES.items()}
                                  | ({request.args['state']: {'label': request.args['state'][6:], 'count': int(mask_for(request.args['state']).sum()) if NAMES else 0}}
                                     if NAMES and str(request.args.get('state', '')).startswith('state:') else {})})

@app.post('/identify')
def identify():
    if S['state'] == 'off': return jsonify(error=S['step'], status=S), 503
    if S['state'] != 'ready': return jsonify(error='The picture checker is still setting up: ' + S['step'], status=S), 503
    from PIL import Image
    raws = [f.read() for f in request.files.getlist('images')] if request.files.getlist('images') else []     # 1.39.0: several pictures of one plant
    if 'image' in request.files: raws.insert(0, request.files['image'].read())
    if not raws: raws = [request.get_data()]
    raws = [r for r in raws if r]
    if not raws: abort(400, 'Send a picture')
    imgs = []
    for raw in raws[:6]:
        try: imgs.append(Image.open(io.BytesIO(raw)))
        except Exception: abort(400, 'That is not a picture this can read')
    t0 = time.time()
    v = embed_many(imgs) if len(imgs) > 1 else embed(imgs[0], views=request.args.get('views', '1') != '0')
    out = {'model': MODEL, 'matches': [], 'species': [], 'pictures': len(imgs)}
    with LOCK: P = dict(PHOTOS)
    if P['emb'] is not None and len(P['files']):
        sims = P['emb'] @ v
        best = {}
        for i in np.argsort(-sims):
            c = P['codes'][i]
            if c not in best: best[c] = (float(sims[i]), P['files'][i])
            if len(best) >= 5: break
        ranked = sorted(best.items(), key=lambda kv: -kv[1][0])
        for j, (code, (sc, f)) in enumerate(ranked):
            nxt = ranked[j + 1][1][0] if j + 1 < len(ranked) else sc - 0.1
            out['matches'].append({'code': code, 'score': round(sc, 4), 'photo': f,
                                   'confidence': round(float(confidence(sc, sc - nxt)), 2) if j == 0 else None})
        if out['matches']: out['likely_new'] = out['matches'][0]['score'] < NOVEL.get(MODEL, 0.65)
    scope = request.args.get('scope', 'common')
    mode = request.args.get('mode', 'mine'); mode = mode if mode in MODES else 'mine'       # 5b: 'mine' or 'new'
    C = country(request.args.get('country')) if mode == 'new' else None
    mask = mask_for(scope, 'common')
    idx = np.where(mask)[0]
    logits = dot_rows(idx, v) * M['scale']
    top = np.argsort(-logits)[:80]
    # 1.39.0: what the picture is likely to be, before looking: a species or genus already in the record, a houseplant, a plant
    # of the place's state; and the species of the record's own photos that look like this one (a new pot of a plant you have).
    # Each adds to the name's score (log odds); PRIOR_OFF=1 turns it off for tests and comparisons.
    cand = {int(idx[t]): float(logits[t]) for t in top}
    basis = {}
    if PRIOR_ON:
        looks, unlike = {}, {}                    # species index -> best similarity with a photo of a named plant in the record (or a confirmed example); with a rejected example
        nov = NOVEL.get(MODEL, 0.65)
        if 'looks' in MODES[mode] and P['emb'] is not None and len(P['files']) and P.get('sp'):
            sims = P['emb'] @ v
            for j in np.argsort(-sims)[:8]:
                i, sim = P['sp'][j], float(sims[j])
                if i >= 0 and mask[i] and sim >= nov: looks[i] = max(looks.get(i, 0), sim)
        E = EXAMPLES
        if E['emb'] is not None and len(E['files']):   # 5c: what people confirmed ('yes') or said no to ('no'), in both modes
            sims = E['emb'] @ v
            for j in np.argsort(-sims)[:12]:
                i, sim, kind = E['sp'][j], float(sims[j]), E['kind'][j]
                if i < 0 or not mask[i] or sim < nov: continue
                if kind == 'yes': looks[i] = max(looks.get(i, 0), sim)
                else: unlike[i] = max(unlike.get(i, 0), sim)
        for i in looks:
            if i not in cand: cand[i] = float(dot_rows(np.array([i]), v)[0]) * M['scale']
        for i in list(cand):
            why = prior_why(i, scope, mode, C)
            if i in looks: why.append('looks')
            if i in unlike: why.append('unlike')
            bonus = prior_bonus(why, i, C)
            if i in looks: bonus += PRIOR['looks'] * (looks[i] - nov) / (1 - nov)
            if i in unlike: bonus -= PRIOR['looks'] * (unlike[i] - nov) / (1 - nov)
            if why: cand[i] += bonus; basis[i] = why
    order = sorted(cand, key=lambda i: -cand[i])
    sc = np.array([cand[i] for i in order]); p = np.exp(sc - sc.max()); p /= p.sum()
    n_out = max(3, min(40, int(request.args.get('n', 10))))      # 1.40.0: the app asks for more when some names are excluded
    for k in range(min(n_out, len(order))):
        i = order[k]
        out['species'].append(species_dict(i) | {'probability': round(float(p[k]), 3), 'basis': basis.get(i, [])})
    gen = {}                                      # the genus is right more often than the species: add up the top 50
    for k in range(min(50, len(order))):
        g = NAMES['rows'][order[k]][0][5]; gen[g] = gen.get(g, 0) + float(p[k])
    out['genera'] = [{'genus': g, 'probability': round(q, 3)} for g, q in sorted(gen.items(), key=lambda kv: -kv[1])[:5]]
    out['prior'] = PRIOR_ON
    out['seconds'] = round(time.time() - t0, 2)
    out['scope'] = scope
    out['mode'] = mode                            # 5b
    out['country'] = ({'code': request.args.get('country', '').upper(), 'state': C['state'], 'species': C['species']} | ({'error': C['error']} if C.get('error') else {})) if C else None
    return jsonify(out)

def dot_rows(idx, v, chunk=40000):
    """Name fingerprints of rows idx times v, a block at a time (a float32 copy of all 349,000 rows would need 1.4 GB)."""
    out = np.empty(len(idx), dtype=np.float32)
    for a in range(0, len(idx), chunk):
        out[a:a + chunk] = NAMES['emb'][idx[a:a + chunk]].astype(np.float32) @ v
    return out

# ---------------------------------------------------------------- 1.21.0: browsing the library
# Kinds of plant, from the class (or the phylum for mosses, liverworts, hornworts and algae) in the Tree of Life list.
KINDS = [('dicot', 'Flowering plants: broadleaf (dicots)', {'Magnoliopsida'}, set()),
         ('monocot', 'Flowering plants: grasses, lilies, palms, orchids (monocots)', {'Liliopsida'}, set()),
         ('fern', 'Ferns and horsetails', {'Polypodiopsida'}, set()),
         ('lycophyte', 'Clubmosses, spikemosses and quillworts', {'Lycopodiopsida'}, set()),
         ('conifer', 'Conifers', {'Pinopsida'}, set()),
         ('cycad', 'Cycads', {'Cycadopsida'}, set()),
         ('ginkgo', 'Ginkgo', {'Ginkgoopsida'}, set()),
         ('gnetophyte', 'Joint-firs, Welwitschia and relatives', {'Gnetopsida'}, set()),
         ('moss', 'Mosses', set(), {'Bryophyta'}),
         ('liverwort', 'Liverworts', set(), {'Marchantiophyta'}),
         ('hornwort', 'Hornworts', set(), {'Anthocerotophyta'}),
         ('alga', 'Algae (green, red and others)', set(), {'Rhodophyta', 'Chlorophyta', 'Charophyta', 'Glaucophyta', 'Langiophytophyta'}),
         ('other', 'Other or not classified', set(), set()),
         # 1.22.0: fungi
         ('mushroom', 'Mushrooms, brackets, puffballs and jelly fungi', {'Agaricomycetes', 'Dacrymycetes', 'Tremellomycetes'}, set()),
         ('cupfungus', 'Cup fungi, morels and truffles', {'Pezizomycetes'}, set()),
         ('lichen', 'Lichens', {'Lecanoromycetes', 'Arthoniomycetes', 'Lichinomycetes', 'Candelariomycetes', 'Coniocybomycetes'}, set()),
         ('rust', 'Rusts and smuts', {'Pucciniomycetes', 'Ustilaginomycetes', 'Exobasidiomycetes', 'Microbotryomycetes'}, set()),
         ('mould', 'Moulds, mildews and other small fungi', {'Sordariomycetes', 'Dothideomycetes', 'Leotiomycetes', 'Eurotiomycetes', 'Saccharomycetes',
                                                              'Orbiliomycetes', 'Geoglossomycetes', 'Laboulbeniomycetes', 'Taphrinomycetes'}, set()),
         ('otherfungus', 'Other fungi', set(), set())]
SORTS = ('known', 'sci', 'common', 'family')
KIND_IX = {k[0]: i for i, k in enumerate(KINDS)}
B = {}            # browse arrays: kind, family code, genus, order, common flag, number of US states, sort orders, family names

def kind_of(row):
    t = row[0]
    for i, (k, _, classes, phyla) in enumerate(KINDS):
        if t[2] in classes or t[1] in phyla: return i
    return KIND_IX['otherfungus' if t[0] == 'Fungi' else 'other']

def common_of(i):
    """The common name to show: the USDA one (English) when there is one, else the Tree of Life one."""
    us = NAMES['usda'].get(NAMES['sp'][i])
    if us:
        n = next((v[0] for v in us.values() if v[0]), '')
        if n: return n[0].upper() + n[1:]
    return NAMES['rows'][i][1] or ''

def build_browse():
    say('Preparing the library')
    rows, sp = NAMES['rows'], NAMES['sp']
    n = len(rows)
    fams = sorted({r[0][4] for r in rows if r[0][4]})
    fcode = {f: i for i, f in enumerate(fams)}
    commons = [common_of(i) for i in range(n)]
    B.update(kind=np.array([kind_of(r) for r in rows], dtype=np.int8), fams=fams,
             fam=np.array([fcode.get(r[0][4], -1) for r in rows], dtype=np.int32),
             genus=np.array([r[0][5].lower() for r in rows]), order=np.array([r[0][3].lower() for r in rows]),
             common=np.array([bool(c) for c in commons]), commons=commons,
             nstates=np.array([len(NAMES['usda'].get(x, {})) for x in sp], dtype=np.int16))
    low = [x.lower() for x in sp]
    B['sort'] = {
        'known': np.array(sorted(range(n), key=lambda i: (not commons[i], -int(B['nstates'][i]), low[i])), dtype=np.int32),
        'sci': np.array(sorted(range(n), key=lambda i: low[i]), dtype=np.int32),
        'common': np.array(sorted(range(n), key=lambda i: (not commons[i], commons[i].lower(), low[i])), dtype=np.int32),
        'family': np.array(sorted(range(n), key=lambda i: (rows[i][0][4] or '~', low[i])), dtype=np.int32)}
    B['facets'] = {}

def browse_mask(a):
    scope = a.get('scope', 'world')
    m = mask_for(scope).copy()
    if a.get('kind'):
        k = next((i for i, x in enumerate(KINDS) if x[0] == a['kind']), None)
        if k is not None: m &= B['kind'] == k
    if a.get('family'):
        f = next((i for i, x in enumerate(B['fams']) if x.lower() == a['family'].strip().lower()), None)
        m &= (B['fam'] == f) if f is not None else False
    if a.get('genus'): m &= B['genus'] == a['genus'].strip().lower()
    if a.get('order'): m &= B['order'] == a['order'].strip().lower()
    if a.get('common') == '1': m &= B['common']
    st = a.get('state', '')
    if st == 'us': m &= B['nstates'] > 0
    elif st:
        idx = np.where(m & (B['nstates'] > 0))[0]
        m[:] = False
        m[[i for i in idx if st in NAMES['usda'][NAMES['sp'][i]]]] = True
    own = [x for x in (a.get('own') or '').lower().split('|') if x]
    if a.get('mine') in ('species', 'genus') and own:
        ok = set(own)
        gen = {x for x in (a.get('owngenus') or '').lower().split('|') if x} if a['mine'] == 'genus' else set()
        idx = np.where(m)[0]
        m[:] = False
        m[[i for i in idx if NAMES['sp'][i].lower() in ok or (gen and B['genus'][i] in gen)]] = True
    elif a.get('mine') in ('species', 'genus'):
        m[:] = False
    only, genera = a.get('only'), a.get('only_genera')     # 1.23.0: lists the app keeps (native to Texas, near home, ASPCA...)
    if only is not None or genera:
        keep = np.zeros(len(m), bool)
        if only:
            low = NAMES.get('by_low') or NAMES.setdefault('by_low', {k.lower(): v for k, v in NAMES['by_sp'].items()})
            ix = [low[n.lower()] for n in only if isinstance(n, str) and n.lower() in low]
            if ix: keep[ix] = True
        if genera:
            keep |= np.isin(B['genus'], [g.lower() for g in genera if isinstance(g, str)])
        m &= keep
    q = (a.get('q') or '').strip().lower()
    if q:
        hay = NAMES['hay']
        idx = np.where(m)[0]
        m[:] = False
        m[[i for i in idx if q in hay[i]]] = True
    return m

def mask_for(scope, default='world'):
    """1.28.0: the mask for a list: world, us, common, fungi, or any US state as 'state:California' (USDA spelling without
    spaces also works, such as 'state:NewYork'). 'texas' still means Texas, for settings saved before 1.28.0."""
    M = NAMES['masks']
    if scope == 'texas': scope = 'state:Texas'
    if isinstance(scope, str) and scope.startswith('state:'):
        if scope not in M:
            want = scope[6:].replace(' ', '').lower()
            st = next((x for x in STATES if x.lower() == want), None)
            if st is None: return M.get(default, M['world'])
            usda = NAMES['usda']
            M[scope] = np.array([s in usda and st in usda[s] for s in NAMES['sp']]) & M['us']
        return M[scope]
    return M.get(scope, M.get(default, M['world']))

@app.get('/scope_names')
def scope_names():
    """1.22.0: every scientific name in a list, for downloading the library photos of a whole list."""
    if not B: return jsonify(error='The picture checker is still setting up: ' + S['step']), 503
    m = mask_for(request.args.get('scope', 'world'))
    return jsonify(names=[NAMES['sp'][int(i)] for i in np.where(m)[0]])

def req_args():
    """The query string, plus a JSON body for POST (1.23.0: name lists too long for an address)."""
    a = dict(request.args)
    if request.method == 'POST': a.update(request.get_json(silent=True) or {})
    return a

@app.route('/browse', methods=['GET', 'POST'])
def browse():
    """Every species in a list, filtered and sorted, a page at a time: ?scope=&q=&kind=&family=&genus=&order=&state=&common=1
    &mine=species|genus&own=a|b&owngenus=x|y&sort=known|sci|common|family&offset=&limit="""
    if not B: return jsonify(error=S['step'] if S['state'] == 'off' else 'The picture checker is still setting up: ' + S['step'], status=S), 503
    a = req_args()
    m = browse_mask(a)
    order = B['sort'].get(a.get('sort'), B['sort']['known'])
    hits = order[m[order]]
    off = max(0, int(a.get('offset', 0) or 0)); lim = max(1, min(120, int(a.get('limit', 48) or 48)))
    return jsonify(total=int(len(hits)), offset=off, results=[species_dict(int(i)) for i in hits[off:off + lim]])

@app.get('/facets')
def facets():
    """What the filters can offer in a list: the kinds and families with their counts."""
    if not B: return jsonify(error='Still setting up', status=S), 503
    scope = request.args.get('scope', 'world')
    if scope not in B['facets']:
        m = mask_for(scope)
        kc = np.bincount(B['kind'][m], minlength=len(KINDS)); fc = np.bincount(B['fam'][m][B['fam'][m] >= 0], minlength=len(B['fams']))
        B['facets'][scope] = {'total': int(m.sum()), 'kinds': [{'key': k[0], 'label': k[1], 'count': int(kc[i])} for i, k in enumerate(KINDS) if kc[i]],
                              'families': [{'name': f, 'count': int(fc[i])} for i, f in enumerate(B['fams']) if fc[i]],
                              'states': list(STATES)}
    return jsonify(B['facets'][scope])

@app.get('/taxon')
def taxon():
    """One species in full: names, classification, US states, and the species whose name fingerprints are closest
    (BioCLIP places species that look alike near each other, so these are lookalikes, not necessarily relatives)."""
    if not B: return jsonify(error='Still setting up', status=S), 503
    i = NAMES['by_sp'].get((request.args.get('name') or '').strip())
    if i is None: abort(404, 'That species is not in the list')
    d = species_dict(i)
    t = NAMES['rows'][i][0]
    us = NAMES['usda'].get(NAMES['sp'][i], {})
    d['classification'] = [{'rank': r, 'name': n} for r, n in zip(('Kingdom', 'Phylum', 'Class', 'Order', 'Family', 'Genus'), t[:6]) if n]
    d['common_names'] = sorted({x for x in [NAMES['rows'][i][1]] + [v[0] for v in us.values()] if x}, key=str.lower)
    d['kind'] = KINDS[int(B['kind'][i])][1]
    sims = []
    if np.abs(NAMES['emb'][i]).sum() > 0:
        idx = np.where(NAMES['masks']['fungi' if i >= NAMES['n_plants'] else 'world'])[0]        # fungi look like fungi
        sc = dot_rows(idx, NAMES['emb'][i].astype(np.float32))
        for j in np.argsort(-sc)[:13]:
            k = int(idx[j])
            if k != i and NAMES['sp'][k] != NAMES['sp'][i]: sims.append(species_dict(k) | {'similarity': round(float(sc[j]), 3)})
            if len(sims) >= 8: break
    d['similar'] = sims
    return jsonify(d)

def species_dict(i):
    r, sp = NAMES['rows'][i], NAMES['sp'][i]
    us = NAMES['usda'].get(sp, {})
    first = next(iter(us.values())) if us else ('', '', '')
    return {'scientific_name': sp, 'common_name': B['commons'][i] if B else (r[1] or first[0]), 'genus': r[0][5], 'family': r[0][4] or first[2],
            'order': r[0][3], 'in_texas': 'Texas' in us, 'us_states': sorted(us), 'usda_symbol': first[1],
            'kind': KINDS[int(B['kind'][i])][0] if B else '', 'kingdom': r[0][0]}

@app.get('/names')
def names():
    """Search the species list: ?q=part of a scientific or common name, &scope=, &limit="""
    if not NAMES: return jsonify(error=S['step'] if S['state'] == 'off' else 'The picture checker is still setting up: ' + S['step'], status=S), 503
    q = (request.args.get('q') or '').strip().lower()
    scope = request.args.get('scope', 'world'); lim = min(100, int(request.args.get('limit', 40)))
    if len(q) < 2: return jsonify(results=[], total=0)
    mask = mask_for(scope)
    res = []
    for i in np.where(mask)[0]:
        if q in NAMES['hay'][i]:
            res.append(species_dict(i))
            if len(res) >= 400: break
    # names that start with the search first, then the better-known plants (with a common name, growing in the US)
    res.sort(key=lambda x: (not (x['scientific_name'].lower().startswith(q) or (x['common_name'] or '').lower().startswith(q)),
                            not x['common_name'], not x['us_states'], x['scientific_name']))
    return jsonify(results=res[:lim], total=len(res))

@app.get('/healthz')
def healthz():
    return jsonify(ok=True, state=S['state'])

if os.environ.get('PLANTDB_VISION', '1') == '0':          # turned off in the .env file: answer, but load nothing
    S.update(state='off', step='The picture checker is turned off (PLANTDB_VISION=0 in the .env file). See README, "Identify a plant".')
else:
    threading.Thread(target=load_all, daemon=True).start()
