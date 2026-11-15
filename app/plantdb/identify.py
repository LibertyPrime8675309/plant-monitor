"""Identify a plant or a mushroom from pictures: the picture checker, the one identifier used by Identify, Add a plant and Add
several, what the app learns from "This is right" and "Not this", and the second opinions (Pl@ntNet, Claude). Split out of library.py
in 1.57.0 (review item 25); the names it uses from other modules are linked by server.py (core.link())."""
from .core import *   # noqa: F401,F403

# ---------------------------------------------------------------- 1.18.0: identify a plant from a picture, and the plant library
# The pictures go to the vision service (container "plant-vision", vision/service.py) on Docker's private network. It runs
# BioCLIP on this computer and compares the picture with your own photos and with its species list. Pl@ntNet and Claude
# are optional second opinions, asked only when you press their buttons, with keys the owner saves on the Identify page.
VISION_URL = os.environ.get('PLANTDB_VISION_URL', 'http://vision:8090').rstrip('/')
PLANTNET_URL = os.environ.get('PLANTDB_PLANTNET_URL', 'https://my-api.plantnet.org/v2/identify/all')
CLAUDE_URL = os.environ.get('PLANTDB_CLAUDE_URL', 'https://api.anthropic.com/v1/messages')
CLAUDE_MODEL = 'claude-sonnet-5-5'
ID_SCOPES = ('common', 'state', 'us', 'world', 'fungi')   # 1.28.0: 'state' is the US state of the place in use ('texas' before)

def vscope(c, scope, default='common'):
    """1.28.0: a list name for the picture checker. 'state' (or the old 'texas') becomes the US state of the place in use,
    such as 'state:California'; outside the US it becomes 'us' is not right either, so the worldwide list is used."""
    if scope == 'texas': scope = 'state'
    if scope not in ID_SCOPES: scope = default
    if scope == 'state':
        R = place_region(c, location(c))
        return f'state:{R["usda"]}' if R and R.get('usda') else 'world'
    return scope

def vision_call(path, data=None, ctype=None, timeout=60):
    req = urllib.request.Request(VISION_URL + path, data=data, headers={'Content-Type': ctype} if ctype else {}, method='POST' if data is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read())
        except Exception: body = {}
        if e.code == 503: abort(503, body.get('error') or 'The picture checker is still setting up. Try again in a few minutes.')
        abort(502, body.get('error') or f'The picture checker could not read that ({e.code}).')
    except (urllib.error.URLError, OSError, TimeoutError):
        abort(503, 'The picture checker is not running. Start it with the updater, or see README, "Identify a plant".')

def picture_bytes(max_side=None, f=None):
    """The picture sent with the request (field 'image'), checked, turned upright and saved as JPEG."""
    f = f or request.files.get('image')
    if not f: abort(400, 'Send a picture')
    try:
        im = ImageOps.exif_transpose(Image.open(f.stream)); im.load(); im = im.convert('RGB')
    except Exception:
        abort(400, 'That is not a picture this can read (use JPG or PNG)')
    if max_side: im.thumbnail((max_side, max_side))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=88); return b.getvalue()

def pictures_bytes(max_side=None):
    """1.39.0: every picture sent (field 'image', and 'images' for more of the same plant), up to six."""
    fs = ([request.files['image']] if 'image' in request.files else []) + request.files.getlist('images')
    if not fs: abort(400, 'Send a picture')
    return [picture_bytes(max_side, f) for f in fs[:6]]

def multipart(fields, files):
    """A small multipart/form-data body: fields {name: value}, files [(name, filename, bytes, type)]."""
    bd = 'plantdb' + uuid.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, fn, data, ct in files:
        out.write(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ct}\r\n\r\n'.encode() + data + b'\r\n')
    out.write(f'--{bd}--\r\n'.encode())
    return out.getvalue(), 'multipart/form-data; boundary=' + bd

def plant_brief(c, code):
    r = c.execute('SELECT id, code, common_name, scientific_name, location, site, status FROM plants WHERE code=?', (code,)).fetchone()
    if not r: return None
    ph = c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC, id LIMIT 1', (r['id'],)).fetchone()
    return {'code': r['code'], 'common_name': r['common_name'], 'scientific_name': r['scientific_name'], 'location': r['location'],
            'site': r['site'], 'photo': ph[0] if ph else None}

def species_owned(c):
    """{'genus species' (lower case): [codes]} and {'genus': [codes]} for the plants in the record, to say "You have this"."""
    sp, gn = {}, {}
    for code, sci in c.execute("SELECT code, scientific_name FROM plants WHERE status='active'"):
        m = re.match(r'^\s*([A-Z][a-z]+)(?:\s+([a-z][a-z\-]+))?', sci or '')
        if not m: continue
        gn.setdefault(m.group(1).lower(), []).append(code)
        if m.group(2) and m.group(2) not in ('sp', 'spp', 'x'): sp.setdefault((m.group(1) + ' ' + m.group(2)).lower(), []).append(code)
    return sp, gn

def mark_owned(c, items, key='scientific_name'):
    sp, gn = species_owned(c)
    for x in items:
        n = (x.get(key) or '').lower()
        x['yours'] = sp.get(n, []); x['yours_genus'] = [] if x['yours'] else gn.get(n.split(' ')[0], [])
    if items:                                     # 1.22.0: your wishlist and your tags, shown on the cards
        wish = {r[0].lower(): r[1] for r in c.execute('SELECT name, status FROM wishlist')}
        tags = {r[0].lower(): [t.strip() for t in r[1].split(',') if t.strip()] for r in c.execute("SELECT name, tags FROM species_notes WHERE tags<>''")}
        for x in items:
            n = (x.get(key) or '').lower()
            x['wish'] = wish.get(n); x['tags'] = tags.get(n, [])
        know_mark(c, items, key)                  # 1.23.0: Texas status, near home, pets, hardy here
    return items

# ---------------------------------------------------------------- 1.40.0: one identifier for Identify, Add a plant and Add several
# identify_pictures() is the one path: every picture of the plant goes to the picture checker together (prior and look-alikes in
# the vision service), Pl@ntNet is asked when a key is saved (always, or only when this computer is unsure, by the setting),
# the two lists are merged into one, names you said "Not this" to are left out, and the likeliest genus and family come with it.
def sp_key(name):
    m = re.match(r'^\s*([A-Z][a-z]+)(?:\s+([a-z][a-z\-]+))?', name or '')
    return (m.group(1) + ' ' + (m.group(2) or '')).strip().lower() if m else (name or '').strip().lower()

def rejections(c, plant_code=None):
    """{'species': {keys}, 'genera': {lower genus}} said "Not this" for this plant, plus the ones said with no plant (session-wide picks the client sends itself)."""
    sp, gn, ssp, sgn = set(), set(), set(), set()
    q = 'SELECT name, genus FROM id_rejections WHERE plant_code=?' if plant_code else 'SELECT name, genus FROM id_rejections WHERE 0'
    for name, g in c.execute(q, (plant_code,) if plant_code else ()):
        if g: gn.add(name.strip().lower()); sgn.add(name.strip().capitalize())
        else: sp.add(sp_key(name)); ssp.add(name.strip())
    return {'species': sp, 'genera': gn, 'shown_species': ssp, 'shown_genera': sgn}

ID_MODES = ('mine', 'new')                 # PLAN.md step 5b: "one of my plants" (the record's own lifts) or "a new find" (the country's plants)
def site_country(c):
    """The two-letter country of the place in use (1.48.0), or '' when it is not set."""
    cc = (location(c).get('country') or '').strip().upper()
    return cc if re.fullmatch(r'[A-Z]{2}', cc) else ''

def id_mode():
    """?mode=mine|new on any route that identifies (5b); 'mine' when missing."""
    m = request.args.get('mode', 'mine'); return m if m in ID_MODES else 'mine'

def identify_pictures(c, pics, scope, exclude=None, exclude_genera=None, plant_code=None, plantnet='auto', n=10, mode='mine'):
    rej = rejections(c, plant_code)
    ex_sp = rej['species'] | {sp_key(x) for x in (exclude or [])}
    ex_gn = rej['genera'] | {x.strip().lower() for x in (exclude_genera or [])}
    shown = {'species': sorted({x.strip() for x in (exclude or [])} | rej['shown_species']), 'genera': sorted({x.strip().capitalize() for x in (exclude_genera or [])} | rej['shown_genera'])}
    body, ct = multipart({}, [('image', 'picture.jpg', pics[0], 'image/jpeg')] + [('images', f'picture{i + 2}.jpg', b, 'image/jpeg') for i, b in enumerate(pics[1:])])
    q = {'scope': scope, 'n': min(40, n + len(ex_sp) + 10), 'mode': mode if mode in ID_MODES else 'mine'}
    if q['mode'] == 'new' and site_country(c): q['country'] = site_country(c)
    out = vision_call('/identify?' + urllib.parse.urlencode(q), body, ct, timeout=120)
    matches = []
    for m in out.get('matches', []):
        b = plant_brief(c, m['code'])
        if b: matches.append(b | {'score': m['score'], 'confidence': m.get('confidence'), 'matched_photo': m.get('photo')})
    out['matches'] = matches
    keep = lambda x: sp_key(x.get('scientific_name')) not in ex_sp and (x.get('genus') or sp_key(x.get('scientific_name')).split(' ')[0]).lower() not in ex_gn
    local = [x | {'sources': ['this computer']} for x in out.get('species', []) if keep(x)]
    sure_match = bool(matches) and (matches[0].get('confidence') or 0) >= 0.5 and not out.get('likely_new')
    top_p = (local or [{}])[0].get('probability') or 0
    pn = None
    key = setting(c, 'plantnet_key', '')
    want = plantnet == 'yes' or (plantnet == 'auto' and setting(c, 'plantnet_auto', '') == '1' and not sure_match and top_p < 0.5)
    if key and want and plantnet != 'no':
        try: pn = plantnet_ask(c, pics[0], more=pics[1:])
        except Exception as e: pn = {'species': [], 'error': getattr(e, 'description', None) or str(e)}
    merged = []
    if pn and pn.get('species'):
        # one list: a name both agree on adds up; Pl@ntNet's score counts for more, as it names species better than the zero-shot checker
        by = {sp_key(x['scientific_name']): dict(x) for x in local}
        for x in pn['species']:
            if not keep(x): continue
            k = sp_key(x['scientific_name'])
            if k in by: by[k]['score'] = by[k].get('probability', 0) + 1.3 * (x.get('probability') or 0); by[k]['sources'] = ['this computer', 'Pl@ntNet']; by[k]['plantnet_probability'] = x.get('probability')
            else: by[k] = dict(x) | {'score': 1.3 * (x.get('probability') or 0), 'sources': ['Pl@ntNet'], 'plantnet_probability': x.get('probability'), 'basis': [], 'local_probability': None}
        for k, x in by.items():
            if 'score' not in x: x['score'] = x.get('probability', 0)
            x.setdefault('local_probability', x.get('probability') if 'Pl@ntNet' not in x['sources'] or len(x['sources']) == 2 else None)
        merged = sorted(by.values(), key=lambda x: -x['score'])
        tot = sum(x['score'] for x in merged) or 1
        for x in merged: x['probability'] = round(x['score'] / tot, 3)
    else:
        merged = local
    merged = merged[:n]
    mark_owned(c, merged)
    for x in merged: x['basis_words'] = [BASIS_WORDS.get(w, w) for w in (x.get('basis') or [])]
    out['species'] = merged
    out['plantnet'] = pn if pn is not None else None
    out['sources'] = ['this computer'] + (['Pl@ntNet'] if pn and pn.get('species') else [])
    # the genus and the family, added up over the merged names: often right when no species is
    gen, fam = {}, {}
    for x in merged:
        g = x.get('genus') or sp_key(x.get('scientific_name')).split(' ')[0].capitalize()
        gen[g] = gen.get(g, 0) + x['probability']
        if x.get('family'): fam[x['family']] = fam.get(x['family'], 0) + x['probability']
    out['genera'] = [{'genus': g, 'probability': round(q, 3)} for g, q in sorted(gen.items(), key=lambda kv: -kv[1])[:5]]
    out['families'] = [{'family': f, 'probability': round(q, 3)} for f, q in sorted(fam.items(), key=lambda kv: -kv[1])[:3]]
    out['excluded'] = shown
    out['pictures'] = len(pics)
    if pn is None: out.pop('plantnet', None)
    return out

def id_args():
    """The common request arguments of the identification routes."""
    a = request.args
    ex = [x for x in (a.get('exclude') or '').split('|') if x.strip()]
    exg = [x for x in (a.get('exclude_genera') or '').split('|') if x.strip()]
    return dict(exclude=ex, exclude_genera=exg, plant_code=a.get('plant') or None, plantnet=a.get('plantnet', 'auto'), n=max(3, min(25, int(a.get('n', 10)))),
                mode=id_mode())

@app.route('/api/identify', methods=['POST'])
def identify():
    """Pictures (field 'image', more as 'images') in; the closest plants in the record and the likeliest species out.
    ?exclude=Name|Name, ?exclude_genera=Genus, ?plant=P-001 (its own "Not this" list), ?plantnet=auto|yes|no, ?n=10."""
    c = db()
    scope = vscope(c, request.args.get('scope', 'common'))
    return jsonify(identify_pictures(c, pictures_bytes(1024), scope, **id_args()))

# ---- PLAN.md step 5c (1.52.0): the loop. What people confirm or reject becomes an example the checker learns from: a 'yes' example
# lifts its name for pictures that look like it (the look-alike step searches the record's own photos and these), a 'no' example
# lowers it. The picture is kept in data/photos as ex_<hex>.jpg and the row in id_examples; the checker reads both (service.py,
# examples_rows) and keeps the fingerprints in its cache. The record's named plants and named mushroom finds count on their own.
def example_save(c, kind, name, file, source, code=None):
    c.execute('INSERT INTO id_examples(kind,name,file,source,plant_code,added_by,added_at) VALUES(?,?,?,?,?,?,?)', (kind, name, file, source, code, editor(), now()))

def example_picture():
    """The picture sent with a confirmation or rejection (field 'image'), saved as an example file; None when none was sent."""
    f = request.files.get('image')
    if not f: return None
    from PIL import Image, ImageOps
    try: im = ImageOps.exif_transpose(Image.open(f.stream)).convert('RGB')
    except Exception: abort(400, 'That picture cannot be read (use JPG or PNG)')
    im.thumbnail((1024, 1024))
    name = f'ex_{uuid.uuid4().hex[:16]}.jpg'
    os.makedirs(PHOTO_DIR, exist_ok=True)
    im.save(os.path.join(PHOTO_DIR, name), 'JPEG', quality=84, optimize=True)
    return name

@app.route('/api/identify/confirm', methods=['POST'])
def identify_confirm():
    """5c: "This is right": the picture (field 'image') is a confirmed example of 'name' (form fields name, source). Editors and the
    owner; the guard refuses viewers. Without a picture but with ?plant=, the plant's main photo is the example."""
    c = db()
    name = str(request.form.get('name') or request.args.get('name') or '').strip()[:120]
    if not name or not re.match(r'^[A-Z][a-z]+ [a-z][a-z\-]+', name): abort(400, 'Which species? (Genus species)')
    code = str(request.form.get('plant') or request.args.get('plant') or '').strip() or None
    file = example_picture()
    if not file and code:
        r = plant_row(c, code)
        ph = c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC, id LIMIT 1', (r['id'],)).fetchone()
        if ph: file = ph[0]
    if not file: abort(400, 'Send the picture that was checked')
    example_save(c, 'yes', name, file, str(request.form.get('source') or 'identify')[:40], code)
    audit_only(c, 'library', 'identify', None, name, editor(), f'Confirmed: this picture is {name}' + (f' ({code})' if code else ''), None, code)
    c.commit()
    n = c.execute("SELECT COUNT(*) FROM id_examples WHERE kind='yes' AND name=?", (name,)).fetchone()[0]
    return jsonify(ok=True, name=name, file=file, examples=n)

@app.route('/api/identify/reject', methods=['POST'])
def identify_reject():
    """1.40.0: "Not this": {name, genus: bool, plant: code or null}. With a plant, the name never comes back for that plant; without one, the
    client keeps the list for the session and sends it as ?exclude=. Either way the rejection is logged.
    5c: sent as a form with the picture (field 'image'), the picture is kept as a 'no' example of the name, so the checker lowers that
    name for pictures that look like it; with a plant and no picture, the plant's main photo is the example."""
    c = db()
    b = request.get_json(silent=True) or (request.form.to_dict() if request.form else {})
    name = str(b.get('name') or '').strip()[:120]
    if not name: abort(400, 'Which name?')
    code = str(b.get('plant') or '').strip() or None
    if code: plant_row(c, code)
    genus = 1 if b.get('genus') in (True, 1, '1', 'true') else 0
    c.execute('INSERT INTO id_rejections(plant_code,name,genus,rejected_by,rejected_at) VALUES(?,?,?,?,?)', (code, name, genus, editor(), now()))
    audit_only(c, 'library', 'identify', name, None, editor(), f'Not this: {"genus " if genus else ""}{name}' + (f' for {code}' if code else ''), None, code)
    if not genus and re.match(r'^[A-Z][a-z]+ [a-z][a-z\-]+', name):      # 5c: a species said no to becomes a 'no' example when there is a picture
        file = example_picture()
        if not file and code:
            ph = c.execute('SELECT ph.file FROM photos ph JOIN plants p ON p.id=ph.plant_id WHERE p.code=? ORDER BY ph.is_primary DESC, ph.id LIMIT 1', (code,)).fetchone()
            if ph: file = ph[0]
        if file: example_save(c, 'no', name, file, 'identify', code)
    c.commit()
    return jsonify(ok=True, name=name, genus=bool(genus), plant=code)

@app.route('/api/identify/examples')
def identify_examples():
    """5c: what the checker has learned: how many confirmed and rejected examples, by name (newest first)."""
    c = db()
    rows = c.execute("""SELECT name, SUM(kind='yes') AS yes, SUM(kind='no') AS no, MAX(added_at) AS last FROM id_examples GROUP BY name ORDER BY last DESC LIMIT 200""").fetchall()
    return jsonify(examples=[dict(r) for r in rows], total=c.execute('SELECT COUNT(*) FROM id_examples').fetchone()[0])

BASIS_WORDS = {'own_sp': 'a species you have', 'own_gen': 'a genus you have', 'house': 'a houseplant', 'state': 'grows in this state', 'looks': 'looks like your photos or a confirmed picture',
               'country': 'recorded in this country',       # 5b
               'unlike': 'lowered: looks like a picture that was not this'}       # 5c

@app.route('/api/identify/status')
def identify_status():
    c = db(); vs = vscope(c, 'state')
    sq = ({'state': vs} if vs.startswith('state:') else {}) | ({'country': site_country(c)} if site_country(c) else {})
    try: st = vision_call('/status' + ('?' + urllib.parse.urlencode(sq) if sq else ''), timeout=5)
    except Exception as e:
        st = {'state': 'off', 'step': getattr(e, 'description', 'The picture checker is not running.')}
    if isinstance(st.get('scopes'), dict):            # 1.28.0: 'state' is the place's own state
        st['scopes']['state'] = st['scopes'].get(vs) or ({'label': '', 'count': 0})
        st['scopes'].pop('texas', None); st['scopes'].pop(vs, None)
    st['region'] = place_region(c, location(c))
    st['site_country'] = site_country(c)                      # 5b: '' means Homes and places has no country for this place yet
    st['plantnet'] = bool(setting(c, 'plantnet_key')); st['claude'] = bool(setting(c, 'claude_key'))
    return jsonify(st)


def key_hint(k):
    return ('…' + k[-4:]) if k else ''

@app.route('/api/identify/settings', methods=['GET', 'PUT'])
def identify_settings():
    """The Pl@ntNet and Claude keys (owner only to change). The keys never leave the server: only their last 4 characters."""
    c = db()
    if request.method == 'PUT':
        b = request.get_json(silent=True) or {}
        for name, word in (('plantnet_key', 'Pl@ntNet'), ('claude_key', 'Claude')):
            if name not in b: continue
            k = str(b.get(name) or '').strip()
            if k and not re.match(r'^[A-Za-z0-9_\-]{10,200}$', k): abort(400, f'That does not look like a {word} key. Copy it again, without spaces.')
            set_setting(c, name, k)
            audit_only(c, 'setting', name, None, key_hint(k) or '(removed)', editor(), f'{word} key ' + ('saved' if k else 'removed'))
        if 'plantnet_auto' in b:                  # 1.39.0: ask Pl@ntNet on its own when this computer is unsure
            v = '1' if b.get('plantnet_auto') else ''
            set_setting(c, 'plantnet_auto', v)
            audit_only(c, 'setting', 'plantnet_auto', None, v or '(off)', editor(), 'Pl@ntNet first opinion when unsure ' + ('turned on' if v else 'turned off'))
        c.commit()
    pk, ck = setting(c, 'plantnet_key', ''), setting(c, 'claude_key', '')
    return jsonify(plantnet=bool(pk), plantnet_hint=key_hint(pk), claude=bool(ck), claude_hint=key_hint(ck), claude_model=CLAUDE_MODEL,
                   plantnet_auto=setting(c, 'plantnet_auto', '') == '1')

def outside_call(url, data, headers, timeout=60):
    req = urllib.request.Request(url, data=data, headers=headers | {'User-Agent': 'plant-database (home garden record)'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, {}
    except (urllib.error.URLError, OSError, TimeoutError):
        return 0, {}

@app.route('/api/identify/plantnet', methods=['POST'])
def identify_plantnet():
    """Second opinion from Pl@ntNet (free key: 500 pictures a day). Pl@ntNet does not keep the pictures, by its terms."""
    return jsonify(plantnet_ask(db(), picture_bytes(1280)))

def plantnet_ask(c, pic, more=()):
    """Pl@ntNet's answer for one picture (JPEG bytes; up to four more of the same plant), as a dict; aborts with a readable reason when it cannot answer."""
    key = setting(c, 'plantnet_key', '')
    if not key: abort(400, 'Pl@ntNet is not set up. The owner can save a key on the Identify page, under "Second opinions".')
    files = [('images', 'picture.jpg', pic, 'image/jpeg')] + [('images', f'picture{i + 2}.jpg', b, 'image/jpeg') for i, b in enumerate(list(more)[:4])]
    body, ct = multipart({'organs': 'auto'}, files)
    url = PLANTNET_URL + '?' + urllib.parse.urlencode({'api-key': key, 'lang': 'en', 'nb-results': 5, 'include-related-images': 'false'})
    st, j = outside_call(url, body, {'Content-Type': ct})
    if st == 404: return {'species': [], 'note': 'Pl@ntNet did not recognise a plant in that picture.', 'source': 'Pl@ntNet'}
    if st in (401, 403): abort(502, 'Pl@ntNet refused the key. Check it on my.plantnet.org and save it again.')
    if st == 429: abort(502, 'The Pl@ntNet key has used all of today\'s pictures. It resets tomorrow.')
    if st != 200: abort(502, 'Could not reach Pl@ntNet. Check the internet connection and try again.')
    out = []
    for r in (j.get('results') or [])[:5]:
        sp = r.get('species') or {}
        out.append({'scientific_name': sp.get('scientificNameWithoutAuthor', ''), 'author': sp.get('scientificNameAuthorship', ''),
                    'genus': (sp.get('genus') or {}).get('scientificNameWithoutAuthor', ''), 'family': (sp.get('family') or {}).get('scientificNameWithoutAuthor', ''),
                    'common_name': ', '.join((sp.get('commonNames') or [])[:3]), 'probability': round(float(r.get('score') or 0), 3)})
    mark_owned(c, out)
    return {'species': out, 'remaining': j.get('remainingIdentificationRequests'), 'source': 'Pl@ntNet'}

CLAUDE_ASK = ('Identify the plant in this photo. It is one of the potted or garden plants of a home grower in {place} '
              '({zone}). Reply with JSON only, no other text: {"plant": true or false (is there a plant in the photo), '
              '"guesses": [up to 3 of {"scientific_name": "Genus species", "common_name": "...", "family": "...", '
              '"probability": 0 to 1, "why": "one short sentence on the features you used"}], '
              '"photo_tip": "one short sentence on what photo would make you surer, or empty"}')

def claude_ask(c):
    """1.28.0: the question names the place in use and its zone, not always Round Rock."""
    L = location(c)
    try: z = place_zone(c, L).get('zone')
    except Exception: z = None
    R = place_region(c, L)
    where = L['name'] + (f' ({R["name"]})' if R and R['name'] not in L['name'] else '')
    return CLAUDE_ASK.replace('{place}', where).replace('{zone}', f'USDA zone {z}' if z else 'climate zone not known')

@app.route('/api/identify/claude', methods=['POST'])
def identify_claude():
    """Second opinion from Claude, with the owner's Anthropic API key (paid per picture, a cent or two)."""
    import base64
    c = db()
    key = setting(c, 'claude_key', '')
    if not key: abort(400, 'Claude is not set up. The owner can save an Anthropic API key on the Identify page, under "Second opinions".')
    pic = base64.b64encode(picture_bytes(1280)).decode()
    body = json.dumps({'model': CLAUDE_MODEL, 'max_tokens': 800, 'messages': [{'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': pic}}, {'type': 'text', 'text': claude_ask(c)}]}]}).encode()
    st, j = outside_call(CLAUDE_URL, body, {'Content-Type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01'}, timeout=90)
    if st in (401, 403): abort(502, 'Anthropic refused the key. Check it at console.anthropic.com and save it again.')
    if st == 429 or st == 529: abort(502, 'Claude is busy or the key has reached its limit. Try again in a minute.')
    if st != 200: abort(502, 'Could not reach Claude. Check the internet connection and try again.')
    text = ''.join(b.get('text', '') for b in j.get('content', []) if b.get('type') == 'text')
    m = re.search(r'\{.*\}', text, re.S)
    try: a = json.loads(m.group(0)) if m else {}
    except ValueError: a = {}
    out = [{'scientific_name': str(x.get('scientific_name', ''))[:120], 'common_name': str(x.get('common_name', ''))[:120], 'family': str(x.get('family', ''))[:80],
            'probability': max(0.0, min(1.0, float(x.get('probability') or 0))), 'why': str(x.get('why', ''))[:300]}
           for x in (a.get('guesses') or [])[:3] if isinstance(x, dict)]
    mark_owned(c, out)
    return jsonify(species=out, plant=a.get('plant', True), tip=str(a.get('photo_tip', ''))[:300], source='Claude (' + CLAUDE_MODEL + ')',
                   note='' if out or a else 'Claude did not give an answer this could read. Try again.')
