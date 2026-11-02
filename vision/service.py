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
Nothing leaves the computer except the downloads above."""
import csv, html, io, json, os, re, sqlite3, threading, time, urllib.request
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
def embed(img):
    from PIL import ImageOps
    t = M['torch']
    with t.no_grad():
        x = M['pre'](ImageOps.exif_transpose(img).convert('RGB')).unsqueeze(0)
        e = M['model'].encode_image(x)[0].float().numpy()
    return e / np.linalg.norm(e)

def photo_rows():
    db = os.path.join(DATA, 'plants.db')
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=10)
    try:
        return c.execute("SELECT ph.file, p.code FROM photos ph JOIN plants p ON p.id=ph.plant_id WHERE p.status='active' ORDER BY ph.id").fetchall()
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
    new = [f for f, _ in rows if f not in known and os.path.exists(os.path.join(DATA, 'photos', f))]
    def save():
        if known: np.savez(path + '.tmp.npz', files=np.array(list(known)), emb=np.stack(list(known.values()))); os.replace(path + '.tmp.npz', path)
    for i, f in enumerate(new):
        try: known[f] = embed(Image.open(os.path.join(DATA, 'photos', f)))
        except Exception as e: print('[vision] skipped', f, e, flush=True)
        if S['state'] != 'ready': say('Fingerprinting your photos', i + 1, len(new))
        if i % 25 == 24: save()                       # so a restart part way through does not start over
    files = [f for f, _ in rows if f in known]
    if new: save()
    with LOCK:
        PHOTOS.update(files=files, codes=[c for f, c in rows if f in known], emb=np.stack([known[f] for f in files]) if files else None,
                      mtime=os.path.getmtime(os.path.join(DATA, 'plants.db')))
    return len(new)

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

def confidence(score, margin):
    """How often the first choice was right, from tests on Ethan's own photos (October 2026): mostly the margin between
    the best plant and the next, a little the score itself. Rounded, and never shown as certain."""
    w = CONF.get(MODEL, CONF['bioclip-2.5-vith14'])
    z = w[0] + w[1] * margin + w[2] * (score - 0.85)
    return max(0.05, min(0.97, 1 / (1 + np.exp(-z))))

# ---------------------------------------------------------------- routes
@app.get('/status')
def status():
    return jsonify(S | {'photos': len(PHOTOS['files']), 'species': int(NAMES['masks']['world'].sum()) if NAMES else 0,
                        'fungi': int(NAMES['masks']['fungi'].sum()) if NAMES else 0,
                        'scopes': {k: {'label': v, 'count': int(NAMES['masks'][k].sum()) if NAMES else 0} for k, v in SCOPES.items()}})

@app.post('/identify')
def identify():
    if S['state'] == 'off': return jsonify(error=S['step'], status=S), 503
    if S['state'] != 'ready': return jsonify(error='The picture checker is still setting up: ' + S['step'], status=S), 503
    from PIL import Image
    raw = request.files['image'].read() if 'image' in request.files else request.get_data()
    if not raw: abort(400, 'Send a picture')
    try: img = Image.open(io.BytesIO(raw))
    except Exception: abort(400, 'That is not a picture this can read')
    t0 = time.time()
    v = embed(img)
    out = {'model': MODEL, 'matches': [], 'species': []}
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
    mask = NAMES['masks'].get(scope, NAMES['masks']['common'])
    idx = np.where(mask)[0]
    logits = dot_rows(idx, v) * M['scale']
    top = np.argsort(-logits)[:50]
    p = np.exp(logits[top] - logits[top].max()); p /= p.sum()
    for k in range(5):
        out['species'].append(species_dict(idx[top[k]]) | {'probability': round(float(p[k]), 3)})
    gen = {}                                      # the genus is right more often than the species: add up the top 50
    for k in range(len(top)):
        g = NAMES['rows'][idx[top[k]]][0][5]; gen[g] = gen.get(g, 0) + float(p[k])
    out['genera'] = [{'genus': g, 'probability': round(q, 3)} for g, q in sorted(gen.items(), key=lambda kv: -kv[1])[:3]]
    out['seconds'] = round(time.time() - t0, 2)
    out['scope'] = scope
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
    m = NAMES['masks'].get(scope, NAMES['masks']['world']).copy()
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
    q = (a.get('q') or '').strip().lower()
    if q:
        hay = NAMES['hay']
        idx = np.where(m)[0]
        m[:] = False
        m[[i for i in idx if q in hay[i]]] = True
    return m

@app.get('/scope_names')
def scope_names():
    """1.22.0: every scientific name in a list, for downloading the library photos of a whole list."""
    if not B: return jsonify(error='The picture checker is still setting up: ' + S['step']), 503
    m = NAMES['masks'].get(request.args.get('scope', 'texas'), NAMES['masks']['texas'])
    return jsonify(names=[NAMES['sp'][int(i)] for i in np.where(m)[0]])

@app.get('/browse')
def browse():
    """Every species in a list, filtered and sorted, a page at a time: ?scope=&q=&kind=&family=&genus=&order=&state=&common=1
    &mine=species|genus&own=a|b&owngenus=x|y&sort=known|sci|common|family&offset=&limit="""
    if not B: return jsonify(error=S['step'] if S['state'] == 'off' else 'The picture checker is still setting up: ' + S['step'], status=S), 503
    a = request.args
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
        m = NAMES['masks'].get(scope, NAMES['masks']['world'])
        kc = np.bincount(B['kind'][m], minlength=len(KINDS)); fc = np.bincount(B['fam'][m][B['fam'][m] >= 0], minlength=len(B['fams']))
        B['facets'][scope] = {'total': int(m.sum()), 'kinds': [{'key': k[0], 'label': k[1], 'count': int(kc[i])} for i, k in enumerate(KINDS) if kc[i]],
                              'families': [{'name': f, 'count': int(fc[i])} for i, f in enumerate(B['fams']) if fc[i]],
                              'states': [x for x in STATES if x != 'Texas']}
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
    mask = NAMES['masks'].get(scope, NAMES['masks']['world'])
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
