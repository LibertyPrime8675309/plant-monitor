"""Identify a plant, the plant library, library photos for offline use, each species near home and for pets, and the facts (uses, partners, propagation).
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
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

def picture_bytes(max_side=None):
    """The picture sent with the request (field 'image'), checked, turned upright and saved as JPEG."""
    f = request.files.get('image')
    if not f: abort(400, 'Send a picture')
    try:
        im = ImageOps.exif_transpose(Image.open(f.stream)); im.load(); im = im.convert('RGB')
    except Exception:
        abort(400, 'That is not a picture this can read (use JPG or PNG)')
    if max_side: im.thumbnail((max_side, max_side))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=88); return b.getvalue()

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

@app.route('/api/identify', methods=['POST'])
def identify():
    """A picture (field 'image') in; the closest plants in the record and the likeliest species out (from this computer)."""
    scope = vscope(db(), request.args.get('scope', 'common'))
    body, ct = multipart({}, [('image', 'picture.jpg', picture_bytes(1024), 'image/jpeg')])
    out = vision_call('/identify?scope=' + scope, body, ct, timeout=90)
    c = db()
    matches = []
    for m in out.get('matches', []):
        b = plant_brief(c, m['code'])
        if b: matches.append(b | {'score': m['score'], 'confidence': m.get('confidence'), 'matched_photo': m.get('photo')})
    out['matches'] = matches
    mark_owned(c, out.get('species', []))
    return jsonify(out)

@app.route('/api/identify/status')
def identify_status():
    c = db(); vs = vscope(c, 'state')
    try: st = vision_call('/status' + ('?' + urllib.parse.urlencode({'state': vs}) if vs.startswith('state:') else ''), timeout=5)
    except Exception as e:
        st = {'state': 'off', 'step': getattr(e, 'description', 'The picture checker is not running.')}
    if isinstance(st.get('scopes'), dict):            # 1.28.0: 'state' is the place's own state
        st['scopes']['state'] = st['scopes'].get(vs) or ({'label': '', 'count': 0})
        st['scopes'].pop('texas', None); st['scopes'].pop(vs, None)
    st['region'] = place_region(c, location(c))
    st['plantnet'] = bool(setting(c, 'plantnet_key')); st['claude'] = bool(setting(c, 'claude_key'))
    return jsonify(st)

@app.route('/api/library')
def library():
    """Search the species list (?q=, &scope=texas|us|common|world)."""
    q, scope = request.args.get('q', '').strip()[:80], request.args.get('scope', 'world')
    scope = vscope(db(), scope, 'world')
    if len(q) < 2: return jsonify(results=[], total=0)
    out = vision_call('/names?' + urllib.parse.urlencode({'q': q, 'scope': scope, 'limit': 60}), timeout=30)
    mark_owned(db(), out.get('results', []))
    out['results'].sort(key=lambda x: (not x['yours'], not x['yours_genus']))      # yours first (a stable sort keeps the rest in order)
    return jsonify(out)

# ---- library notes, tags and wishlist (shared with everyone who can open the app; viewers can read them)
@app.route('/api/library/notes', methods=['GET', 'PUT'])
def library_notes():
    c = db()
    if request.method == 'PUT':
        b = request.get_json(silent=True) or {}
        name = str(b.get('name') or '').strip()[:120]
        if not name: abort(400, 'Which species?')
        notes = str(b.get('notes') or '').strip()[:5000]
        tags = ', '.join(dict.fromkeys(t.strip().lower()[:40] for t in str(b.get('tags') or '').split(',') if t.strip()))[:500]
        old = c.execute('SELECT * FROM species_notes WHERE name=?', (name,)).fetchone()
        c.execute('INSERT OR REPLACE INTO species_notes(name,notes,tags,updated_by,updated_at) VALUES(?,?,?,?,?)', (name, notes, tags, editor(), now()))
        audit_only(c, 'library', 'notes', (old['notes'] + ' | ' + old['tags']) if old else None, notes + ' | ' + tags, editor(), f'Library notes for {name} saved')
        c.commit()
    name = request.args.get('name') or (request.get_json(silent=True) or {}).get('name') or ''
    if name:
        r = c.execute('SELECT * FROM species_notes WHERE name=?', (name.strip(),)).fetchone()
        return jsonify(dict(r) if r else {'name': name, 'notes': '', 'tags': ''})
    return jsonify(notes=[dict(r) for r in c.execute("SELECT * FROM species_notes WHERE notes<>'' OR tags<>'' ORDER BY name")],
                   tags=sorted({t.strip() for (x,) in c.execute('SELECT tags FROM species_notes') for t in x.split(',') if t.strip()}))

@app.route('/api/wishlist', methods=['GET', 'PUT', 'DELETE'])
def wishlist_api():
    c = db()
    if request.method in ('PUT', 'DELETE'):
        b = request.get_json(silent=True) or {}
        name = str(b.get('name') or request.args.get('name') or '').strip()[:120]
        if not name: abort(400, 'Which species?')
        old = c.execute('SELECT * FROM wishlist WHERE name=?', (name,)).fetchone()
        if request.method == 'PUT' and old and str(b.get('rename') or '').strip() and str(b['rename']).strip()[:120] != name:   # 1.30.0: a supply's name can change
            new_name = str(b['rename']).strip()[:120]
            if old['kind'] == 'plant': abort(400, 'A wishlist plant keeps its species name. Change its common name instead.')
            if c.execute('SELECT 1 FROM wishlist WHERE name=?', (new_name,)).fetchone(): abort(409, f'"{new_name}" is already on the list.')
            c.execute('UPDATE wishlist SET name=? WHERE name=?', (new_name, name))
            c.execute('UPDATE offers SET wish=? WHERE wish=?', (new_name, name)); c.execute('UPDATE wish_alerts SET wish=? WHERE wish=?', (new_name, name))
            name = new_name; old = c.execute('SELECT * FROM wishlist WHERE name=?', (name,)).fetchone()
        if request.method == 'DELETE':
            c.execute('DELETE FROM wishlist WHERE name=?', (name,))
            c.execute('DELETE FROM offers WHERE wish=?', (name,))
            audit_only(c, 'library', 'wishlist', name, None, editor(), f'{name} taken off ' + ('Shopping' if old and old['kind'] != 'plant' else 'the wishlist'))
        else:
            st = b.get('status', old['status'] if old else 'want')
            if st not in ('want', 'got'): abort(400, 'status must be want or got')
            vals = (str(b.get('common_name', old['common_name'] if old else '') or '')[:120], str(b.get('notes', old['notes'] if old else '') or '').strip()[:2000],
                    str(b.get('where_seen', old['where_seen'] if old else '') or '').strip()[:300], st)
            mp = b.get('max_price', old['max_price'] if old else None)          # 1.27.0: price and stock alerts, and what to search the shops for
            if mp in ('', None): mp = None
            else:
                try: mp = round(float(mp), 2)
                except (TypeError, ValueError): abort(400, 'The price to watch for must be a number of dollars, such as 25')
                if not 0 < mp < 100000: abort(400, 'The price to watch for must be more than $0')
            more = (mp, 1 if b.get('alert_stock', old['alert_stock'] if old else 0) else 0,
                    re.sub(r'[ \t]+', ' ', str(b.get('search_words', old['search_words'] if old else '') or '')).strip()[:300])
            kind = str(b.get('kind', old['kind'] if old else 'plant') or 'plant')
            if kind not in SHOP_KIND_WORD: abort(400, 'Choose what kind of thing it is: ' + ', '.join(SHOP_KIND_WORD.values()))
            per = str(b.get('price_per', old['price_per'] if old else '') or '')
            if per not in ('', 'unit'): abort(400, 'price_per must be empty (the whole listing) or unit')
            if per == 'unit' and SH.KIND_UNIT.get(kind, 'each') == 'each': per = ''
            if old and old['kind'] == 'plant' and kind != 'plant': abort(400, 'A wishlist plant stays a plant.')
            more += (kind, per, str(b.get('source', old['source'] if old else '') or '')[:60])
            if old: c.execute('UPDATE wishlist SET common_name=?, notes=?, where_seen=?, status=?, max_price=?, alert_stock=?, search_words=?, kind=?, price_per=?, source=?, updated_by=?, updated_at=? WHERE name=?',
                              vals + more + (editor(), now(), name))
            else: c.execute('INSERT INTO wishlist(name,common_name,notes,where_seen,status,max_price,alert_stock,search_words,kind,price_per,source,added_by,added_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                            (name,) + vals + more + (editor(), now()))
            if old and (old['search_words'] or '') != more[2]: c.execute('DELETE FROM offers WHERE wish=?', (name,))   # new searches: start the list again
            where = 'the wishlist' if kind == 'plant' else 'Shopping'
            audit_only(c, 'library', 'wishlist', None, name, editor(), f'{name} ' + (f'updated on {where}' if old else f'added to {where}'))
        c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishlist ORDER BY status='got', added_at DESC")]
    sp, _ = species_owned(c)
    for r in rows:
        r['yours'] = sp.get(r['name'].lower(), []) if r['kind'] == 'plant' else []
        r['terms'] = SH.terms_for(r)
        r['offers'] = offer_summary(c, r)
    return jsonify(wishlist=rows, alerts=wish_alerts_open(c), checked=setting(c, 'shops_checked_at', ''))

def shop_near_sql(c, near):
    """1.30.0: SQL (with its arguments) keeping the stores that count for a home: every online store, and the stores you can
    visit near that home. near: 'all', or a home's id."""
    if not near or near == 'all': return '', []
    try: hid = int(near)
    except (TypeError, ValueError): return '', []
    main = home_place(c)['id']
    return ' AND (s.online=1 OR s.local=0 OR COALESCE(s.home_id, ?)=?)', [main, hid]

def offer_unit(o, kind):
    return SH.unit_price(o['title'], o['price'], kind, o['size'] if 'size' in o.keys() else '')

def offer_summary(c, w, near='all'):
    """How many stores have it in stock, and the cheapest listing: by the price per quart, pound or square foot when the item is
    sold that way and the listing says its size, else by its price."""
    extra, args = shop_near_sql(c, near)
    rows = c.execute('SELECT o.*, s.name shop_name, s.local, s.online FROM offers o JOIN shops s ON s.key=o.shop WHERE o.wish=? AND o.gone=0 AND o.available=1 AND s.enabled=1' + extra,
                     [w['name']] + args).fetchall()
    kind = w['kind'] if 'kind' in w.keys() else 'plant'
    priced = []
    for o in rows:
        if o['price'] is None: continue
        d = dict(o); d['unit'] = offer_unit(o, kind); priced.append(d)
    want_unit = SH.KIND_UNIT.get(kind, 'each')
    by_unit = [d for d in priced if d['unit'] and d['unit']['unit'] == want_unit and want_unit != 'each']
    best = min(by_unit, key=lambda d: d['unit']['per']) if by_unit else (min(priced, key=lambda d: d['price']) if priced else None)
    return {'count': len(rows), 'shops': len({o['shop'] for o in rows}), 'best': best, 'unit': want_unit if want_unit != 'each' else ''}

# ---------------------------------------------------------------- 1.21.0: the library as a browsable knowledge base
# Names, classification and US states come from the picture checker (offline). Photos and the short description come from
# iNaturalist (CC-licensed photos by its members; the description is from Wikipedia), fetched once per species in the
# background, about one request a second as iNaturalist asks, and kept in data/library. Only species names are sent.
LIB_DIR = os.path.join(DATA_DIR, 'library')
INAT_URL = os.environ.get('PLANTDB_INAT_URL', 'https://api.inaturalist.org/v1').rstrip('/')
INAT_IMG_OK = tuple(x for x in os.environ.get('PLANTDB_INAT_IMG_OK', 'https://inaturalist-open-data.s3.amazonaws.com/,https://static.inaturalist.org/').split(',') if x)
LIB_RECHECK_DAYS = 30            # a species with no photo is looked up again after this many days
LIBQ = {'queue': [], 'set': set(), 'lock': threading.Lock(), 'thread': None, 'last': 0.0}

def lib_slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:120]

def lib_meta(name):
    p = os.path.join(LIB_DIR, lib_slug(name) + '.json')
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError): return None

def lib_save(name, meta):
    os.makedirs(LIB_DIR, exist_ok=True)
    p = os.path.join(LIB_DIR, lib_slug(name) + '.json')
    with open(p + '.tmp', 'w', encoding='utf-8') as f: json.dump(meta, f)
    os.replace(p + '.tmp', p)

def lib_online(c=None):
    return setting(c or db(), 'library_online', '1') == '1'

def inat_get(path):
    """One iNaturalist API call, at most one a second (shared by every request)."""
    with LIBQ['lock']:
        wait = 1.05 - (time.time() - LIBQ['last'])
        if wait > 0: time.sleep(wait)
        LIBQ['last'] = time.time()
    req = urllib.request.Request(INAT_URL + path, headers={'User-Agent': f'plant-database/{APP_VERSION} (a home plant record)', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read())

def lib_download(url, dest, big=1024):
    if not url.startswith(INAT_IMG_OK): raise ValueError('not an iNaturalist photo address')
    req = urllib.request.Request(url, headers={'User-Agent': f'plant-database/{APP_VERSION} (a home plant record)'})
    with urllib.request.urlopen(req, timeout=30) as r: raw = r.read(8_000_000)
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))); im = im.convert('RGB')
    im.thumbnail((big, big))
    im.save(dest + '.tmp', 'JPEG', quality=84, optimize=True); os.replace(dest + '.tmp', dest)

def inat_find(name):
    """The iNaturalist taxon with exactly this name, or None."""
    j = inat_get('/taxa?' + urllib.parse.urlencode({'q': name, 'is_active': 'true', 'per_page': 10, 'locale': 'en'}))
    for t in j.get('results') or []:
        if (t.get('name') or '').lower() == name.lower(): return t
    return None

def photo_meta(ph, file):
    return {'file': file, 'credit': ph.get('attribution') or '', 'license': (ph.get('license_code') or '').upper(),
            'page': f"https://www.inaturalist.org/photos/{ph['id']}" if ph.get('id') else ''}

def lib_fetch_photo(name):
    """Looks a species up on iNaturalist and keeps its main photo (and the basic facts) in data/library."""
    meta = lib_meta(name) or {}
    t = inat_find(name)
    meta.update(name=name, checked=date.today().isoformat(), taxon_id=t['id'] if t else None,
                inat_common=(t or {}).get('preferred_common_name') or '', observations=(t or {}).get('observations_count'),
                wikipedia_url=(t or {}).get('wikipedia_url') or '')
    ph = (t or {}).get('default_photo') or {}
    url = ph.get('medium_url') or ph.get('url')
    if url:
        f = lib_slug(name) + '.jpg'
        lib_download(url, os.path.join(LIB_DIR, f), big=640)
        meta['photo'] = photo_meta(ph, f)
    else:
        meta['photo'] = None
    lib_save(name, meta)
    return meta

def lib_worker():
    jid = job_start('library', 'photos and descriptions'); n = 0
    while True:
        with LIBQ['lock']:
            if not LIBQ['queue']: LIBQ['thread'] = None; job_end(jid, True, f'{n} species fetched'); return
            name = LIBQ['queue'].pop(0); left = len(LIBQ['queue'])
        n += 1; job_progress(jid, n, n + left, name)
        try:                                                          # turned off since it was queued: stop
            c2 = sqlite3.connect(DB_PATH, timeout=10)
            try: online = lib_online(c2)
            finally: c2.close()
        except Exception: online = True
        if not online:
            with LIBQ['lock']: LIBQ['queue'].clear(); LIBQ['set'].clear(); LIBQ['thread'] = None
            job_end(jid, True, 'stopped: library lookups were turned off'); return
        try: lib_fetch_photo(name)
        except Exception as e:
            problem('library', f'{name}: its photos could not be fetched', f'{type(e).__name__}: {e}')
            lib_save(name, (lib_meta(name) or {}) | {'name': name, 'checked': date.today().isoformat(), 'photo': None, 'error': str(e)[:200]})
        finally:
            with LIBQ['lock']: LIBQ['set'].discard(name)

def lib_enqueue(names, front=True):
    """Queues species for a photo. Ones someone is looking at go first (front=True); a whole-list download goes last."""
    with LIBQ['lock']:
        if front:
            queued = set(LIBQ['queue'])
            first = [n for n in dict.fromkeys(names) if n not in LIBQ['set'] or n in queued]   # in the set but not queued = being fetched now
            moving = set(first)
            LIBQ['queue'] = first + [n for n in LIBQ['queue'] if n not in moving]
            LIBQ['set'].update(first)
        else:
            for n in names:
                if n not in LIBQ['set']: LIBQ['set'].add(n); LIBQ['queue'].append(n)
        if LIBQ['queue'] and not LIBQ['thread']:
            LIBQ['thread'] = threading.Thread(target=lib_worker, daemon=True); LIBQ['thread'].start()

# ---------------------------------------------------------------- 1.28.0: library photos for offline use, by area
# An area is any place iNaturalist knows (a country, state, county, park or city). Its list is every plant species recorded
# there (research-grade and needs-ID observations, wild or planted), fetched with the area lists' one-a-second limit. Then the
# photo and short facts of each species are downloaded like any library photo. "Check for updates" fetches the list again and
# downloads what is new. Photos stay when an area is removed (another area or a page may use them).
AREA_JOB = {}            # place_id: {'names': set(), 'total': n, 'started': ts}

def area_names(pid):
    j = local_get(f'area-{pid}')
    return [x[0] for x in (j or {}).get('species', [])]

def lib_kept_files():
    try: return {f[:-4] for f in os.listdir(LIB_DIR) if f.endswith('.jpg')}
    except OSError: return set()

def lib_checked_files():
    try: return {f[:-5] for f in os.listdir(LIB_DIR) if f.endswith('.json')}
    except OSError: return set()

def area_after(pid):
    """After an area's list is fetched: note when, and queue the photos it does not have yet."""
    names, kept = area_names(pid), lib_kept_files()
    todo = [n for n in names if lib_slug(n) not in kept]
    fresh = lib_checked_files()
    todo = [n for n in todo if lib_slug(n) not in fresh or not (lib_meta(n) or {}).get('checked')
            or (date.today() - date.fromisoformat(lib_meta(n)['checked'])).days >= LIB_RECHECK_DAYS]     # no photo there, looked recently: skip
    AREA_JOB[pid] = {'names': set(todo), 'total': len(todo), 'started': now()}
    c2 = sqlite3.connect(DB_PATH, timeout=10)
    try:
        c2.execute('UPDATE lib_areas SET total=?, checked_at=? WHERE place_id=?', (len(names), now(), pid)); c2.commit()
    finally: c2.close()
    lib_enqueue(todo, front=False)

def area_queue(pid):
    params = {'place_id': pid, 'iconic_taxa': 'Plantae', 'verifiable': 'true'}
    with KNOW['lock']:
        if not any(n == f'area-{pid}' for n, _ in KNOW['queue']) and not (KNOW['now'] and KNOW['now'][0] == f'area-{pid}'):
            KNOW['queue'].append((f'area-{pid}', params))
        if not KNOW['thread']:
            KNOW['thread'] = threading.Thread(target=know_worker, daemon=True); KNOW['thread'].start()

def areas_list(c):
    kept, checked = lib_kept_files(), lib_checked_files()
    with LIBQ['lock']: queued = set(LIBQ['set'])
    with KNOW['lock']: lists_q = {n for n, _ in KNOW['queue']} | ({KNOW['now'][0]} if KNOW['now'] else set())
    out = []
    for r in c.execute('SELECT * FROM lib_areas ORDER BY name'):
        names = area_names(r['place_id']); slugs = [lib_slug(n) for n in names]
        have = sum(1 for x in slugs if x in kept)
        none = sum(1 for x in slugs if x not in kept and x in checked)            # looked up: iNaturalist has no photo
        job = AREA_JOB.get(r['place_id']) or {}
        left = len(job.get('names', set()) & queued)
        fetching = f'area-{r["place_id"]}' in lists_q
        out.append({'id': r['id'], 'place_id': r['place_id'], 'name': r['name'], 'total': len(names) or r['total'] or 0, 'kept': have, 'no_photo': none,
                    'percent': round(100 * have / len(names), 1) if names else 0, 'checked_at': r['checked_at'], 'added_at': r['added_at'], 'added_by': r['added_by'],
                    'state': 'list' if fetching else 'photos' if left else 'idle', 'left': left, 'error': KNOW['error'].get(f'area-{r["place_id"]}', {}).get('error')})
    return out

@app.route('/api/library/areas', methods=['GET', 'POST'])
def library_areas():
    """Owner only for changes (OWNER_ONLY_CHANGES). POST {place_id, name} adds an area and starts its download."""
    c = db()
    if request.method == 'POST':
        if not lib_online(c): abort(409, 'Library photos are turned off. Turn them on first.')
        b = request.get_json(silent=True) or {}
        try: pid = int(b.get('place_id'))
        except (TypeError, ValueError): abort(400, 'Choose a place from the search')
        name = str(b.get('name') or '').strip()[:120] or f'Place {pid}'
        if c.execute('SELECT 1 FROM lib_areas WHERE place_id=?', (pid,)).fetchone(): abort(409, f'{name} is already in the table')
        c.execute('INSERT INTO lib_areas(place_id,name,total,added_by,added_at) VALUES(?,?,0,?,?)', (pid, name, editor(), now()))
        audit_only(c, 'library', 'area', None, name, editor(), f'Library photos: area added and download started: {name}'); c.commit()
        area_queue(pid)
    return jsonify(areas=areas_list(c), online=lib_online(c), running=any(a['state'] != 'idle' for a in areas_list(c)))

@app.route('/api/library/areas/search')
def library_areas_search():
    q = (request.args.get('q') or '').strip()
    if len(q) < 2: abort(400, 'Type at least 2 letters')
    try: j = inat_get('/places/autocomplete?' + urllib.parse.urlencode({'q': q, 'per_page': 12}))
    except Exception as e: abort(502, f'iNaturalist could not be reached ({type(e).__name__}). Try again later.')
    kinds = {0: 'Country', 10: 'State or province', 20: 'County or district', 30: 'Town or city', 100: 'Park or reserve'}
    return jsonify([{'place_id': p['id'], 'name': p.get('display_name') or p.get('name'), 'kind': kinds.get(p.get('admin_level'), 'Area')}
                    for p in (j.get('results') or []) if p.get('id')])

@app.route('/api/library/areas/<int:aid>', methods=['POST', 'DELETE'])
def library_area_one(aid):
    """POST: check for updates (fetch the list again and download what is new). DELETE: remove from the table (photos stay)."""
    c = db()
    r = c.execute('SELECT * FROM lib_areas WHERE id=?', (aid,)).fetchone()
    if not r: abort(404, 'That area is not in the table')
    if request.method == 'DELETE':
        job = AREA_JOB.pop(r['place_id'], None)
        if job:
            with LIBQ['lock']:
                LIBQ['queue'] = [n for n in LIBQ['queue'] if n not in job['names']]; LIBQ['set'] -= job['names']
        c.execute('DELETE FROM lib_areas WHERE id=?', (aid,))
        audit_only(c, 'library', 'area', r['name'], None, editor(), f'Library photos: area removed (its photos are kept): {r["name"]}'); c.commit()
    else:
        if not lib_online(c): abort(409, 'Library photos are turned off. Turn them on first.')
        audit_only(c, 'library', 'area', None, r['name'], editor(), f'Library photos: checked for updates: {r["name"]}'); c.commit()
        area_queue(r['place_id'])
    return jsonify(areas=areas_list(c))

@app.route('/api/library/areas/stop', methods=['POST'])
def library_areas_stop():
    c = db()
    with LIBQ['lock']:
        for job in AREA_JOB.values():
            LIBQ['queue'] = [n for n in LIBQ['queue'] if n not in job['names']]; LIBQ['set'] -= job['names']
    with KNOW['lock']: KNOW['queue'] = [q for q in KNOW['queue'] if not q[0].startswith('area-')]
    audit_only(c, 'library', 'area', None, None, editor(), 'Library photos: downloads stopped'); c.commit()
    return jsonify(areas=areas_list(c))

# ---------------------------------------------------------------- 1.23.0: the library part 2 (status in Texas, near home, pets, care sheets)
# Lists about the area come from iNaturalist's species counts, fetched in the background (about one request a second, shared with
# the library photos) and kept in data/library/local: plants native to Texas, plants introduced to Texas, everything recorded wild
# within 50 km of the home place, and what flowers (plants) or fruits (fungi) there in the current month. Pet safety comes from the
# ASPCA's three lists (dogs, cats, horses), fetched once a quarter. The Texas noxious and invasive list is built in. Care sheets
# are written by Claude with the owner's key, on request, and kept in data/library/care. Nothing here is sent anywhere but those.
LOCAL_DIR = os.path.join(LIB_DIR, 'local')
CARE_DIR = os.path.join(LIB_DIR, 'care')
ASPCA_URL = os.environ.get('PLANTDB_ASPCA_URL', 'https://www.aspca.org/pet-care/animal-poison-control').rstrip('/')
NEAR_KM = 50
ASPCA_MIN = int(os.environ.get('PLANTDB_ASPCA_MIN', '50'))   # fewer plants than this means their page changed
# Texas Department of Agriculture's noxious and invasive plant list (4 TAC 19.300), as copied by EDDMapS. Under Texas Agriculture
# Code 71.152 these may not be sold, distributed or brought into Texas. A name ending in a space is a whole genus.
TX_NOXIOUS = {
    'Pueraria montana': 'kudzu', 'Solanum viarum': 'tropical soda apple', 'Alternanthera philoxeroides': 'alligatorweed', 'Salvinia molesta': 'giant salvinia',
    'Arundo donax': 'giant reed', 'Hydrilla verticillata': 'hydrilla', 'Lonicera japonica': 'Japanese honeysuckle', 'Lygodium japonicum': 'Japanese climbing fern',
    'Lythrum salicaria': 'purple loosestrife', 'Melia azedarach': 'chinaberry', 'Murdannia keisak': 'marsh dayflower', 'Myriophyllum aquaticum': 'parrotfeather',
    'Myriophyllum spicatum': 'Eurasian watermilfoil', 'Triadica sebifera': 'Chinese tallow', 'Convolvulus arvensis': 'field bindweed',
    'Monochoria hastata': 'arrowleaved monochoria', 'Commelina benghalensis': 'Benghal dayflower', 'Rottboellia cochinchinensis': 'itchgrass',
    'Phelipanche ramosa': 'branched broomrape', 'Ottelia alismoides': 'duck-lettuce', 'Asphodelus fistulosus': 'onionweed', 'Limnophila sessiliflora': 'limnophila',
    'Eichhornia azurea': 'anchored water hyacinth', 'Alhagi maurorum': 'camelthorn', 'Cardiospermum halicacabum': 'balloon vine', 'Calystegia sepium': 'hedge false bindweed',
    'Cuscuta japonica': 'Japanese dodder', 'Ipomoea aquatica': 'swamp morning-glory', 'Leucaena leucocephala': 'white leadtree', 'Senna obtusifolia': 'sicklepod',
    'Sorghum almum': 'sorghum-almum', 'Tamarix ramosissima': 'saltcedar', 'Cyperus entrerianus': 'deeprooted sedge', 'Ludwigia ': 'primrose-willow (some species)',
    'Landoltia punctata': 'dotted duckmeat', 'Paspalum distichum': 'knotgrass', 'Schinus terebinthifolia': 'Brazilian peppertree',
    'Pontederia crassipes': 'water hyacinth', 'Eichhornia crassipes': 'water hyacinth'}
TX_NOXIOUS_SRC = 'https://www.eddmaps.org/lists/list.cfm?id=26'
TX_NOXIOUS_LAW = 'https://texasagriculture.gov/Regulatory-Programs/Plant-Quality/Noxious-and-Invasive-Plants'

def binomial(name):
    """'Pueraria montana var. lobata' -> 'pueraria montana'; 'Sorghum x almum' -> 'sorghum almum'."""
    w = [x for x in re.sub(r'[×]', ' ', str(name or '')).lower().split() if x not in ('x',)]
    return ' '.join(w[:2])

def tx_noxious(name):
    b = binomial(name)
    for k, v in TX_NOXIOUS.items():
        if (k.endswith(' ') and b.split(' ')[0] == k.strip().lower()) or b == k.lower(): return v
    return None

# 1.28.0: the lists follow the place in use (the Location button), not Texas. Each place has a "region" on iNaturalist: its US state,
# Canadian province or similar (admin level 10), or else its country (level 0). It is looked up once and kept in settings.
TX_REGION = {'id': 18, 'name': 'Texas', 'level': 10, 'country': 'United States', 'usda': 'Texas'}
USDA_STATES = {'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
               'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
               'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'NewHampshire', 'NewJersey', 'NewMexico', 'NewYork', 'NorthCarolina',
               'NorthDakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'PuertoRico', 'RhodeIsland', 'SouthCarolina', 'SouthDakota', 'Tennessee',
               'Texas', 'Utah', 'Vermont', 'VirginIslands', 'Virginia', 'Washington', 'WestVirginia', 'Wisconsin', 'Wyoming'}

def place_region(c, L):
    """The iNaturalist region of a place, or None until it has been looked up (see region_fetch)."""
    v = setting(c, f'inat_region:{L["id"]}')
    if v:
        try: return json.loads(v)
        except ValueError: pass
    if L.get('lat') is not None and abs(L['lat'] - REF_PLACE[0]) < 1.5 and abs(L['lon'] - REF_PLACE[1]) < 1.5: return dict(TX_REGION)
    return None

def region_fetch(loc_id):
    """Looks up a place's state (or country) on iNaturalist and keeps it."""
    c2 = sqlite3.connect(DB_PATH, timeout=10); c2.row_factory = sqlite3.Row
    try:
        L = loc_get(c2, loc_id)
        d = 0.01
        j = inat_get('/places/nearby?' + urllib.parse.urlencode({'nelat': L['lat'] + d, 'nelng': L['lon'] + d, 'swlat': L['lat'] - d, 'swlng': L['lon'] - d, 'per_page': 50}))
        std = (j.get('results') or {}).get('standard') or []
        country = next((p for p in std if p.get('admin_level') == 0), None)
        state = next((p for p in std if p.get('admin_level') == 10), None)
        pick = state or country
        if not pick: raise ValueError('iNaturalist knows no state or country for this place')
        cn = (country or {}).get('name') or ''
        usda = pick['name'].replace(' ', '') if state and cn in ('United States', 'United States of America') else None
        R = {'id': pick['id'], 'name': pick.get('name'), 'level': pick.get('admin_level'), 'country': cn, 'usda': usda if usda in USDA_STATES else None}
        c2.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)', (f'inat_region:{loc_id}', json.dumps(R))); c2.commit()
    finally: c2.close()

def lib_place(c):
    """The place the library's lists are about: the place in use (Location button)."""
    return location(c)

def local_migrate(c):
    """Lists kept before 1.28.0 had Texas and the home place in their names: give them their new names once."""
    if not os.path.isdir(LOCAL_DIR) or setting(c, 'lists_renamed_1280'): return
    hid = home_place(c)['id']
    pairs = [('tx_native', 'native-18'), ('tx_introduced', 'introduced-18'), ('near', f'near-{hid}')]
    pairs += [(f'{k}-{m:02d}', f'{k}-{hid}-{m:02d}') for k in ('bloom', 'fungi') for m in range(1, 13)]
    for a, b in pairs:
        if os.path.exists(local_path(a)) and not os.path.exists(local_path(b)):
            try: os.replace(local_path(a), local_path(b))
            except OSError: pass
    set_setting(c, 'lists_renamed_1280', now()); c.commit()

def local_lists(c, L=None):
    """The lists about the area: their names, what they ask iNaturalist, and how long they stay fresh (days)."""
    local_migrate(c)
    L = L or lib_place(c); month = local_today(c).month; R = place_region(c, L)
    near = {'lat': round(L['lat'], 4), 'lng': round(L['lon'], 4), 'radius': NEAR_KM, 'captive': 'false', 'verifiable': 'true'}
    out = {}
    if R:
        out[f'native-{R["id"]}'] = ({'place_id': R['id'], 'native': 'true', 'iconic_taxa': 'Plantae', 'verifiable': 'true'}, 90, f'Plants native to {R["name"]}')
        out[f'introduced-{R["id"]}'] = ({'place_id': R['id'], 'introduced': 'true', 'iconic_taxa': 'Plantae', 'verifiable': 'true'}, 90, f'Plants introduced to {R["name"]}')
    else:
        out[f'region-{L["id"]}'] = (None, 3650, f'The state or country {L["name"]} is in')
    out[f'near-{L["id"]}'] = (near | {'iconic_taxa': 'Plantae,Fungi'}, 30, f'Wild plants and fungi recorded within {NEAR_KM} km ({round(NEAR_KM * 0.621)} miles) of {L["name"]}')
    out[f'bloom-{L["id"]}-{month:02d}'] = (near | {'iconic_taxa': 'Plantae', 'term_id': 12, 'term_value_id': 13, 'month': month}, 14, f'Plants seen flowering near {L["name"]} in {date(2000, month, 1):%B}')
    out[f'fungi-{L["id"]}-{month:02d}'] = (near | {'iconic_taxa': 'Fungi', 'month': month}, 14, f'Fungi recorded near {L["name"]} in {date(2000, month, 1):%B}')
    return out

KNOW = {'lock': threading.Lock(), 'queue': [], 'thread': None, 'now': None, 'error': {}, 'cache': {}}

def local_path(name): return os.path.join(LOCAL_DIR, name + '.json')

def local_get(name):
    """{'fetched', 'species': {name lower: (name, common, count)}} for a kept list, read once and kept in memory."""
    p = local_path(name)
    try: mt = os.path.getmtime(p)
    except OSError: return None
    hit = KNOW['cache'].get(name)
    if hit and hit[0] == mt: return hit[1]
    try:
        with open(p, encoding='utf-8') as f: j = json.load(f)
    except (OSError, ValueError): return None
    j['by'] = {binomial(s[0]): s for s in j.get('species', [])}
    KNOW['cache'][name] = (mt, j)
    return j

def lists_wait():
    """Lists wait while photos someone is looking at are being fetched (up to a minute), so pages fill in first. Then they stop
    if the owner has turned library lookups off meanwhile."""
    t = time.time()
    while LIBQ['queue'] and time.time() - t < 60: time.sleep(0.5)
    c2 = sqlite3.connect(DB_PATH, timeout=10)
    try: on = lib_online(c2)
    finally: c2.close()
    if not on: raise ValueError('library lookups were turned off')

def local_fetch(name, params):
    """Every species in one iNaturalist species count, 500 a page (at most 30 pages)."""
    out, page = [], 1
    while page <= 30:
        lists_wait()
        j = inat_get('/observations/species_counts?' + urllib.parse.urlencode(params | {'per_page': 500, 'page': page, 'locale': 'en'}))
        res = j.get('results') or []
        for r in res:
            t = r.get('taxon') or {}
            if t.get('rank') in ('species', 'hybrid', 'subspecies', 'variety', 'form') and t.get('name'):
                out.append([t['name'], t.get('preferred_common_name') or '', int(r.get('count') or 0)])
        KNOW['now'] = (name, len(out), int(j.get('total_results') or 0))
        if len(res) < 500 or page * 500 >= int(j.get('total_results') or 0): break
        page += 1
    merged = {}
    for n, cm, k in out:                                  # varieties count towards their species
        b = binomial(n); key = b
        if key in merged: merged[key][2] += k
        else: merged[key] = [n if len(n.split()) == 2 else n.split()[0] + ' ' + n.split()[1], cm, k]
    os.makedirs(LOCAL_DIR, exist_ok=True)
    tmp = local_path(name) + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'name': name, 'fetched': now(), 'params': {k: str(v) for k, v in params.items()}, 'species': sorted(merged.values(), key=lambda x: -x[2])}, f)
    os.replace(tmp, local_path(name))

def aspca_fetch():
    """The ASPCA's toxic and non-toxic plant lists for dogs, cats and horses, read from their web pages."""
    out = {}
    for animal, page in (('dogs', 'dogs-plant-list'), ('cats', 'cats-plant-list'), ('horses', 'horse-plant-list')):
        lists_wait()
        with LIBQ['lock']:
            wait = 1.05 - (time.time() - LIBQ['last'])
            if wait > 0: time.sleep(wait)
            LIBQ['last'] = time.time()
        req = urllib.request.Request(f'{ASPCA_URL}/{page}', headers={'User-Agent': f'plant-database/{APP_VERSION} (a home plant record)'})
        with urllib.request.urlopen(req, timeout=30) as r: raw = r.read(6_000_000).decode('utf-8', 'replace')
        raw = re.sub(r'(?is)<(script|style).*?</\1>', ' ', raw)
        raw = re.sub(r'(?i)<\s*(br|/?(div|li|p|h[1-6]|tr|ul|ol|section|article))\b[^>]*>', '\n', raw)   # one plant per line
        text = html_mod.unescape(re.sub(r'<[^>]+>', ' ', raw))
        text = re.sub(r'[ \t\r\f\v]+', ' ', text)
        cut = re.search(r'Plants\s+Non-?\s*Toxic\s+to', text, re.I)
        n = 0
        for m in re.finditer(r'([^|\n]{2,160}?)\s*\|\s*Scientific Names?\s*:\s*([^|]+?)\s*\|\s*Family\s*:\s*([A-Za-z]*)', text):
            toxic = not cut or m.start() < cut.start()
            common = re.sub(r'\s*\(\s*\)\s*$', '', m.group(1).strip())
            for sci in re.split(r'[,;]| and ', m.group(2)):
                sci = sci.strip(' .')
                if not re.match(r'^[A-Z][a-z]+', sci): continue
                genus_only = bool(re.search(r'\bspp?\b', sci)) or len(sci.split()) == 1
                key = sci.split()[0].lower() + ' ' if genus_only else binomial(sci)
                e = out.setdefault(key, {'name': sci, 'common': common, 'family': m.group(3), 'genus': genus_only})
                if e.get(animal) != 'toxic': e[animal] = 'toxic' if toxic else 'non-toxic'
                n += 1
        if n < ASPCA_MIN: raise ValueError(f'the ASPCA {animal} list could not be read (found {n} plants); their page may have changed')
    os.makedirs(LOCAL_DIR, exist_ok=True)
    with open(local_path('aspca') + '.tmp', 'w', encoding='utf-8') as f: json.dump({'fetched': now(), 'plants': out}, f)
    os.replace(local_path('aspca') + '.tmp', local_path('aspca'))

def aspca_get():
    j = local_get('aspca')
    return j.get('plants', {}) if j else {}

def pets_for(name):
    """The ASPCA's answer for a species, or for its genus when they list the genus, or None."""
    a = aspca_get()
    if not a: return None
    b = binomial(name)
    e = a.get(b) or a.get(b.split(' ')[0] + ' ')
    if not e: return None
    return {'dogs': e.get('dogs'), 'cats': e.get('cats'), 'horses': e.get('horses'), 'listed_as': e['name'], 'common': e['common'], 'genus': e['genus']}

def know_worker():
    jid = job_start('know', 'near home, pets and areas'); n = 0
    while True:
        with KNOW['lock']:
            if not KNOW['queue']: KNOW['thread'] = None; KNOW['now'] = None; job_end(jid, True, f'{n} looked up'); return
            name, params = KNOW['queue'].pop(0); left = len(KNOW['queue'])
        n += 1; job_progress(jid, n, n + left, name.replace('area-', 'area '))
        try:
            c2 = sqlite3.connect(DB_PATH, timeout=10)
            try: online = lib_online(c2)
            finally: c2.close()
        except Exception: online = True
        if not online:
            with KNOW['lock']: KNOW['queue'].clear(); KNOW['thread'] = None; KNOW['now'] = None
            job_end(jid, True, 'stopped: library lookups were turned off'); return
        KNOW['now'] = (name, 0, 0)
        try:
            if name == 'aspca': aspca_fetch()
            elif name.startswith('region-'): region_fetch(int(name[7:]))
            else:
                local_fetch(name, params)
                if name.startswith('area-'): area_after(int(name[5:]))
            KNOW['error'].pop(name, None)
        except Exception as e:
            if str(e) == 'library lookups were turned off':
                with KNOW['lock']: KNOW['queue'].clear(); KNOW['thread'] = None; KNOW['now'] = None
                return
            print(f'[library] list {name}: {e}', flush=True)
            KNOW['error'][name] = {'at': now(), 'error': str(e)[:300]}

def know_refresh(c, force=False):
    """Queues the lists that are missing or out of date (all of them with force=True)."""
    if not lib_online(c): return []
    todo = []
    for name, (params, days, _) in list(local_lists(c).items()) + [('aspca', (None, 90, ''))]:
        j = local_get(name)
        if name.startswith('region-'): j = None
        old = not j or force or (datetime.now(timezone.utc) - datetime.fromisoformat(j['fetched'].replace('Z', '+00:00'))).days >= days
        err = KNOW['error'].get(name)
        if err and not force and (datetime.now(timezone.utc) - datetime.fromisoformat(err['at'].replace('Z', '+00:00'))).total_seconds() < 6 * 3600: old = False
        if old: todo.append((name, params))
    with KNOW['lock']:
        have = {n for n, _ in KNOW['queue']} | ({KNOW['now'][0]} if KNOW['now'] else set())
        for t in todo:
            if t[0] not in have: KNOW['queue'].append(t)
        if KNOW['queue'] and not KNOW['thread']:
            KNOW['thread'] = threading.Thread(target=know_worker, daemon=True); KNOW['thread'].start()
    return [t[0] for t in todo]

ZONE_CACHE = {'at': 0, 'zone': None}
def home_zone(c):
    """The home place's hardiness zone from its weather history (kept for 10 minutes; it changes once a year)."""
    if time.time() - ZONE_CACHE['at'] > 600 or not ZONE_CACHE['zone']:
        try: ZONE_CACHE['zone'] = place_zone(c, home_place(c)).get('zone') or '9a'
        except Exception: ZONE_CACHE['zone'] = '9a'
        ZONE_CACHE['at'] = time.time()
    return ZONE_CACHE['zone']

def care_get(name):
    try:
        with open(os.path.join(CARE_DIR, lib_slug(name) + '.json'), encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError): return None

def know_of(c, name, month=None, zone=None):
    """What the lists say about one species."""
    b = binomial(name); month = month or local_today(c).month
    L = lib_place(c); R = place_region(c, L)
    tn, ti = (local_get(f'native-{R["id"]}'), local_get(f'introduced-{R["id"]}')) if R else (None, None)
    nr, bl, fu = local_get(f'near-{L["id"]}'), local_get(f'bloom-{L["id"]}-{month:02d}'), local_get(f'fungi-{L["id"]}-{month:02d}')
    k = {'tx': 'native' if tn and b in tn['by'] else 'introduced' if ti and b in ti['by'] else None,      # 'tx': the region (the name is from 1.23.0)
         'invasive': tx_noxious(name) if R and R['id'] == 18 else None, 'near': nr['by'][b][2] if nr and b in nr['by'] else 0,
         'bloom': bool(bl and b in bl['by']), 'fruiting': bool(fu and b in fu['by']), 'pets': pets_for(name)}
    cs = care_get(name)
    z = zone_num(zone) if zone else None
    zl = zone_num((cs or {}).get('sheet', {}).get('zone_low'))
    k['hardy'] = 'wild-near' if k['near'] else ('zone-yes' if zl <= z else 'zone-no') if (zl is not None and z is not None) else None
    return k

def know_mark(c, items, key='scientific_name'):
    if not items: return items
    month, zone = local_today(c).month, home_zone(c)
    for x in items: x['know'] = know_of(c, x.get(key) or '', month, zone)
    return items

def know_filters(c):
    """The library's "Your area" filters, named for the place in use (1.28.0). The invasive list is only built in for Texas."""
    R = place_region(c, lib_place(c)); rn = R['name'] if R else 'your state or country'
    f = {'native': f'Native to {rn}', 'introduced': f'Introduced to {rn}', 'invasive': 'On the Texas invasive list', 'near': 'Grows wild near here',
         'bloom': 'Flowering near here this month', 'fruiting': 'Fungi found near here this month', 'hardy': 'Likely to survive outside here',
         'petsafe': 'Safe for dogs and cats (ASPCA)', 'pettoxic': 'Toxic to dogs or cats (ASPCA)'}
    if not (R and R['id'] == 18): f.pop('invasive')
    return f

def know_names(c, f):
    """(names, genera) for a library filter."""
    month = local_today(c).month; L = lib_place(c); R = place_region(c, L) or {'id': 0}
    names = lambda n: [s[0] for s in (local_get(n) or {}).get('species', [])]
    if f == 'native': return names(f'native-{R["id"]}'), []
    if f == 'introduced': return names(f'introduced-{R["id"]}'), []
    if f == 'invasive': return ([k for k in TX_NOXIOUS if not k.endswith(' ')], [k.strip() for k in TX_NOXIOUS if k.endswith(' ')]) if R['id'] == 18 else ([], [])
    if f == 'near': return names(f'near-{L["id"]}'), []
    if f == 'bloom': return names(f'bloom-{L["id"]}-{month:02d}'), []
    if f == 'fruiting': return names(f'fungi-{L["id"]}-{month:02d}'), []
    if f == 'hardy':
        z, out = zone_num(home_zone(c)), names(f'near-{L["id"]}')
        if os.path.isdir(CARE_DIR):
            for fn in os.listdir(CARE_DIR):
                try:
                    with open(os.path.join(CARE_DIR, fn), encoding='utf-8') as fh: cs = json.load(fh)
                except (OSError, ValueError): continue
                zl = zone_num(cs.get('sheet', {}).get('zone_low'))
                if zl is not None and z is not None and zl <= z: out.append(cs['name'])
        return out, []
    if f in ('petsafe', 'pettoxic'):
        sp, gen = [], []
        for k, e in aspca_get().items():
            ok = e.get('dogs') == 'non-toxic' and e.get('cats') == 'non-toxic' if f == 'petsafe' else 'toxic' in (e.get('dogs'), e.get('cats'))
            if ok: (gen.append(k.strip()) if e['genus'] else sp.append(e['name']))
        return sp, gen
    return None, None

@app.route('/api/library/local', methods=['GET', 'POST'])
def library_local():
    """The lists about the area: what is kept, how old, and what is being fetched. POST fetches them again now."""
    c = db()
    if request.method == 'POST':
        if not lib_online(c): abort(409, 'Library lookups are turned off. The owner can turn them on at the bottom of the Library page.')
        queued = know_refresh(c, force=True)
        audit_only(c, 'library', 'lists', None, ', '.join(queued), editor(), 'Lists about the area fetched again'); c.commit()
    else:
        know_refresh(c)
    out = []
    for name, (params, days, label) in list(local_lists(c).items()) + [('aspca', (None, 90, 'Plants toxic and non-toxic to dogs, cats and horses (ASPCA)'))]:
        j = local_get(name)
        if name.startswith('region-'): j = None
        out.append({'name': name, 'label': label, 'fetched': j['fetched'] if j else None,
                    'count': (len(j.get('plants', {})) if name == 'aspca' else len(j.get('species', []))) if j else 0, 'error': KNOW['error'].get(name, {}).get('error')})
    with KNOW['lock']: queued = [n for n, _ in KNOW['queue']]
    R = place_region(c, lib_place(c))
    return jsonify(lists=out, now=KNOW['now'], queued=queued, online=lib_online(c), filters=know_filters(c), zone=home_zone(c), near_km=NEAR_KM,
                   noxious_source=TX_NOXIOUS_SRC, noxious_law=TX_NOXIOUS_LAW, region=R, place=lib_place(c)['name'], noxious=bool(R and R['id'] == 18))

@app.route('/api/library/around')
def library_around():
    """The Around home page: what flowers and fruits near home this month, and what is recorded wild nearby most often."""
    c = db(); know_refresh(c)
    month = local_today(c).month; L = lib_place(c)
    secs = []
    for key, name, title in (('bloom', f'bloom-{L["id"]}-{month:02d}', f'Flowering near {L["name"]} in {date(2000, month, 1):%B}'),
                             ('fruiting', f'fungi-{L["id"]}-{month:02d}', f'Mushrooms and other fungi found near {L["name"]} in {date(2000, month, 1):%B}'),
                             ('near', f'near-{L["id"]}', f'Recorded wild most often within {round(NEAR_KM * 0.621)} miles of {L["name"]}')):
        j = local_get(name)
        top = (j or {}).get('species', [])[:48]
        res = []
        if top:
            found = {}
            for scope in (('fungi',) if key == 'fruiting' else ('world',) if key == 'bloom' else ('world', 'fungi')):
                try:
                    r = vision_call('/browse', json.dumps({'scope': scope, 'only': [s[0] for s in top], 'limit': 120}).encode(), 'application/json', timeout=30)
                    found.update({x['scientific_name'].lower(): x for x in r.get('results', [])})
                except Exception: pass
            for n, cm, k in top:
                x = found.get(n.lower()) or {'scientific_name': n, 'common_name': cm, 'family': '', 'kind': '', 'us_states': [], 'in_texas': False}
                if not x.get('common_name') and cm: x['common_name'] = cm
                x['records'] = k; res.append(x)
            mark_owned(c, res)
            for x in res: x['own_photo'] = own_photo(c, x['yours']) if x['yours'] else None
        secs.append({'key': key, 'title': title, 'fetched': j['fetched'] if j else None, 'total': len((j or {}).get('species', [])), 'species': res})
    return jsonify(sections=secs, place=L['name'], online=lib_online(c), near_km=NEAR_KM, month=month)

# ---------- 1.27.0: uses, partners, deterrents, propagation and breeding, for each species ----------
FACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS species_facts(
  key TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'plant', data TEXT NOT NULL,
  origin TEXT NOT NULL, written_by TEXT, written_at TEXT);
CREATE TABLE IF NOT EXISTS facts_link(code TEXT PRIMARY KEY, key TEXT NOT NULL);
"""
FACTS_EVIDENCE = ('Tested', 'Traditional', 'Same needs', 'Different needs')
FACTS_COMPOST = ('Good', 'Fine in small amounts', 'Poor', 'Keep it out')
# a fungus's uses never include eating it or taking it as medicine (the app never says a wild mushroom is edible or safe)
FACTS_FUNGUS_NO = re.compile(r'edib|\beat|eaten|cook|culinar|food|meal|tea\b|tincture|medicin|supplement|extract|psychoactiv|hallucin|consum|forag|recipe|flavou?r|tast', re.I)

def facts_keys(sci):
    """The keys a species' facts can be filed under, most exact first: 'Aloe vera (spotted form)' -> ['aloe vera', 'aloe'],
    'xGraptosedum 'Francesco Baldi'' -> ['graptosedum'], "Philodendron 'Birkin'" -> ['philodendron']."""
    s = re.sub(r'^\s*[x\u00d7]\s*(?=[A-Z])', '', (sci or '').strip())
    m = re.match(r'^([A-Z][a-z]+)(?:\s+([a-z][a-z\-]+))?', s)
    if not m: return []
    g, sp = m.group(1).lower(), m.group(2)
    return ([g + ' ' + sp] if sp and sp not in ('sp', 'spp', 'x', 'cultivar', 'type', 'hybrid', 'var', 'or', 'cf') else []) + [g]

def facts_clean(a, kind='plant'):
    """Keeps only the expected keys, at sensible lengths (for batches and for what Claude writes)."""
    a = a if isinstance(a, dict) else {}
    t = lambda v, n: re.sub(r'\s+', ' ', str(v or '')).strip()[:n]
    ev = lambda v: v if v in FACTS_EVIDENCE else 'Traditional'
    def lst(k, fields, n):
        out = []
        for x in (a.get(k) or [])[:n]:
            if isinstance(x, dict):
                y = {f: (ev(x.get(f)) if f == 'evidence' else t(x.get(f), m)) for f, m in fields}
                if any(v for f, v in y.items() if f != 'evidence'): out.append(y)
        return out
    d = {'summary': t(a.get('summary'), 400),
         'uses': lst('uses', (('kind', 40), ('text', 400), ('caution', 300)), 8),
         'partners_good': lst('partners_good', (('name', 80), ('sci', 80), ('why', 300), ('evidence', 0)), 8),
         'partners_bad': lst('partners_bad', (('name', 80), ('sci', 80), ('why', 300), ('evidence', 0)), 8),
         'deters': lst('deters', (('what', 80), ('how', 300), ('evidence', 0)), 6),
         'attracts': lst('attracts', (('what', 80), ('why', 300)), 6),
         'propagation': lst('propagation', (('method', 60), ('when', 160), ('how', 500)), 6)}
    cp = a.get('compost') if isinstance(a.get('compost'), dict) else {}
    d['compost'] = {'verdict': cp.get('verdict') if cp.get('verdict') in FACTS_COMPOST else '', 'why': t(cp.get('why'), 300)}
    br = a.get('breeding') if isinstance(a.get('breeding'), dict) else {}
    d['breeding'] = {'text': t(br.get('text'), 700), 'patent': t(br.get('patent'), 300), 'same_genus': br.get('same_genus') is not False,
                     'cross_genera': [t(g, 40) for g in (br.get('cross_genera') or [])[:6] if re.fullmatch(r'[A-Za-z\u00d7 ]{3,40}', str(g or ''))]}
    d['sources'] = [{'title': t(x.get('title'), 120), 'url': t(x.get('url'), 300)} for x in (a.get('sources') or [])[:6]
                    if isinstance(x, dict) and str(x.get('url', '')).startswith('https://')]
    if kind == 'fungus':
        d['uses'] = [u for u in d['uses'] if not FACTS_FUNGUS_NO.search(u['kind'] + ' ' + u['text'] + ' ' + u['caution'])]
        d['summary'] = '' if FACTS_FUNGUS_NO.search(d['summary']) else d['summary']
    return d

def facts_row(c, sci, code=None):
    if code:
        k = c.execute('SELECT key FROM facts_link WHERE code=?', (code,)).fetchone()
        if k:
            r = c.execute('SELECT * FROM species_facts WHERE key=?', (k[0],)).fetchone()
            if r: return r
    for k in facts_keys(sci):
        r = c.execute('SELECT * FROM species_facts WHERE key=?', (k,)).fetchone()
        if r: return r
    return None

def facts_links(c, d, sci, self_code=None):
    """Marks which partner plants you have, and which of your plants could be crossed with this one."""
    mine = []
    for code, name, s in c.execute("SELECT code, common_name, scientific_name FROM plants WHERE status='active' ORDER BY code"):
        lk = c.execute('SELECT key FROM facts_link WHERE code=?', (code,)).fetchone()
        mine.append((code, name, ([lk[0]] if lk else []) + facts_keys(s)))
    def have(target):
        t = (target or '').lower().strip()
        t = re.sub(r'^[x\u00d7]\s*', '', t)
        return [{'code': code, 'name': name} for code, name, ks in mine if code != self_code and t and (t in ks or any(k.startswith(t + ' ') for k in ks))]
    for p in d.get('partners_good', []) + d.get('partners_bad', []):
        p['yours'] = have(p['sci']) if p.get('sci') else []
    ks = facts_keys(sci)
    if self_code:
        lk = c.execute('SELECT key FROM facts_link WHERE code=?', (self_code,)).fetchone()
        if lk: ks = [lk[0]] + ks
    sp = next((k for k in ks if ' ' in k), None)
    br = d.get('breeding', {})
    genera = ({k for k in ks if ' ' not in k} if br.get('same_genus', True) else set()) | {g.lower().replace('\u00d7', '').strip() for g in br.get('cross_genera', [])}
    same, other = [], []
    for code, name, pks in mine:
        if code == self_code: continue
        if sp and sp in pks: same.append({'code': code, 'name': name})
        elif genera & {k for k in pks if ' ' not in k}: other.append({'code': code, 'name': name})
    d['cross_same'], d['cross_other'] = same, other
    return d

def facts_out(c, sci, code=None, kind='plant'):
    r = facts_row(c, sci, code)
    if not r: return None
    d = facts_links(c, json.loads(r['data']), sci, code)
    d.update(key=r['key'], name=r['name'], kind=r['kind'], origin=r['origin'], written_by=r['written_by'], written_at=r['written_at'])
    return d

@app.route('/api/facts', methods=['GET', 'POST'])
def species_facts():
    """GET ?name=<scientific name>[&code=P-001]: what is kept for that species (or its genus), with your plants linked.
    POST {name, common_name, kind}: Claude writes them with the owner's key, and they are kept."""
    c = db()
    if request.method == 'GET':
        a = request.args
        code = a.get('code') or None
        sci = a.get('name') or ''
        if code and not sci:
            r = c.execute('SELECT scientific_name FROM plants WHERE code=?', (code,)).fetchone()
            sci = r[0] if r else ''
        return jsonify(facts=facts_out(c, sci, code), keys=facts_keys(sci), can_write=bool(setting(c, 'claude_key', '')))
    b = request.get_json(silent=True) or {}
    name, kind = str(b.get('name') or '').strip()[:120], 'fungus' if b.get('kind') == 'fungus' else 'plant'
    ks = facts_keys(name)
    if not ks: abort(400, 'This needs a scientific name, such as "Aloe vera", to look up.')
    old = c.execute('SELECT origin FROM species_facts WHERE key=?', (ks[0],)).fetchone()
    if old and old['origin'] == 'researched': abort(409, 'These were researched for your plants and are kept as they are.')
    key = setting(c, 'claude_key', '')
    if not key: abort(400, 'These are written by Claude. The owner can save an Anthropic API key on the Identify page, under "Second opinions".')
    L = home_place(c)
    ask = FACTS_ASK.format(name=name, common=f' ({b["common_name"]})' if b.get('common_name') else '', place=L['name'],
                           zone=home_zone(c), extra=FACTS_ASK_FUNGUS if kind == 'fungus' else FACTS_ASK_PLANT)
    body = json.dumps({'model': CLAUDE_MODEL, 'max_tokens': 3000, 'messages': [{'role': 'user', 'content': ask}]}).encode()
    st, j = outside_call(CLAUDE_URL, body, {'Content-Type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01'}, timeout=150)
    if st in (401, 403): abort(502, 'Anthropic refused the key. Check it at console.anthropic.com and save it again.')
    if st in (429, 529): abort(502, 'Claude is busy or the key has reached its limit. Try again in a minute.')
    if st != 200: abort(502, 'Could not reach Claude. Check the internet connection and try again.')
    text = ''.join(x.get('text', '') for x in j.get('content', []) if x.get('type') == 'text')
    m = re.search(r'\{.*\}', text, re.S)
    try: a = json.loads(m.group(0)) if m else {}
    except ValueError: a = {}
    d = facts_clean(a, kind)
    if not (d['uses'] or d['propagation'] or d['partners_good']): abort(502, 'Claude did not give an answer this could read. Try again.')
    c.execute('INSERT OR REPLACE INTO species_facts(key,name,kind,data,origin,written_by,written_at) VALUES(?,?,?,?,?,?,?)',
              (ks[0], name, kind, json.dumps(d), 'claude', editor(), now()))
    audit_only(c, 'library', 'uses and partners', None, name, editor(), f'Uses, partners and propagation for {name} written by Claude'); c.commit()
    return jsonify(facts=facts_out(c, name, None, kind))

FACTS_ASK = """For the species {name}{common}, grown by a home gardener in {place} (USDA zone {zone}), answer with ONE JSON object only, no other
text. Keys:
"summary": one sentence on what it is most useful for.
"uses": a list (0 to 6) of {{"kind": a short category such as "Skin and first aid", "Food for wildlife", "Dye", "Crafts", "Erosion control",
  "Cut flowers", "Ornamental", "Soil", "text": one or two sentences, "caution": safety notes, or ""}}. Traditional or folk uses must say so.
{extra}
"compost": {{"verdict": one of "Good", "Fine in small amounts", "Poor", "Keep it out", "why": one sentence}}.
"partners_good" and "partners_bad": lists (0 to 6) of {{"name": common name, "sci": its genus or "Genus species", "why": one sentence,
  "evidence": "Tested" (shown in trials), "Traditional" (gardeners' lore, not shown), "Same needs" (same light, water and soil, for pots
  and beds) or "Different needs" (for partners_bad: needs very different light, water or soil)}}.
"deters": a list (0 to 4) of {{"what": the pest or animal, "how": one sentence, "evidence": as above}}. Only real, specific claims.
"attracts": a list (0 to 4) of {{"what": pollinators, birds or beneficial insects, "why": one sentence}}.
"propagation": a list (1 to 4) of {{"method": such as "Stem cuttings", "Division", "Seed", "Spore print", "when": the best time in {place},
  "how": two or three practical sentences}}.
"breeding": {{"text": how to cross it with others and what to expect (or that it does not cross), "cross_genera": genera it is known to
  cross with besides its own (a list, often empty), "same_genus": false if it cannot practically be crossed with others of its genus at home,
  "patent": a note if named varieties are commonly patented, or ""}}.
"sources": a list (0 to 4) of {{"title", "url"}}: only well-known reference pages you are sure exist (extension services, botanic gardens).
Use plain words. If you do not know the species well, keep each list short and general, and say so in "summary"."""
FACTS_ASK_PLANT = "Medicinal or skin uses are folk or traditional information, never advice: put any toxicity to people or pets in \"caution\"."
FACTS_ASK_FUNGUS = """This is a FUNGUS. Do not say or suggest that it is edible, safe, tasty, medicinal or psychoactive, and do not list any use
that means eating it, drinking it or taking it in any form. Its uses are what it does: what it breaks down, which trees or plants it
partners with (mycorrhizal), what it tells you about the soil, compost, spore prints, dye from its color, and how it is cultivated."""

CARE_ASK = """Write a CARE SHEET for growing the plant species {name}{common} at home, for a gardener in {place} (USDA hardiness zone {zone}).
Answer with one JSON object only, no other text, with these keys, each a short plain-English string of one to three sentences unless noted:
"summary", "light", "water", "soil", "temperature", "min_temp_f" (a number: the coldest it survives, in Fahrenheit), "zone_low" and "zone_high"
(USDA zones like "8b"), "humidity", "feeding", "pruning", "propagation", "pests", "outdoors_here" (can it live outside year round in {place}, and
when to plant it there), "containers" (growing it in a pot). Do not include anything about whether it is safe for pets or people, or edible.
If you do not know this species well, say so in "summary" and keep the rest general."""

@app.route('/api/library/care', methods=['GET', 'POST'])
def library_care():
    """A care sheet for any plant species, written by Claude with the owner's key on request, and kept."""
    c = db()
    name = (request.get_json(silent=True) or {}).get('name') if request.method == 'POST' else request.args.get('name')
    name = str(name or '').strip()[:120]
    if not name: abort(400, 'Which species?')
    if request.method == 'GET': return jsonify(care=care_get(name))
    key = setting(c, 'claude_key', '')
    if not key: abort(400, 'Care sheets are written by Claude. The owner can save an Anthropic API key on the Identify page, under "Second opinions".')
    b = request.get_json(silent=True) or {}
    L = home_place(c); zone = home_zone(c)
    ask = CARE_ASK.format(name=name, common=f' ({b["common_name"]})' if b.get('common_name') else '', place=L['name'], zone=zone)
    body = json.dumps({'model': CLAUDE_MODEL, 'max_tokens': 1500, 'messages': [{'role': 'user', 'content': ask}]}).encode()
    st, j = outside_call(CLAUDE_URL, body, {'Content-Type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01'}, timeout=120)
    if st in (401, 403): abort(502, 'Anthropic refused the key. Check it at console.anthropic.com and save it again.')
    if st in (429, 529): abort(502, 'Claude is busy or the key has reached its limit. Try again in a minute.')
    if st != 200: abort(502, 'Could not reach Claude. Check the internet connection and try again.')
    text = ''.join(x.get('text', '') for x in j.get('content', []) if x.get('type') == 'text')
    m = re.search(r'\{.*\}', text, re.S)
    try: a = json.loads(m.group(0)) if m else {}
    except ValueError: a = {}
    keys = ('summary', 'light', 'water', 'soil', 'temperature', 'humidity', 'feeding', 'pruning', 'propagation', 'pests', 'outdoors_here', 'containers')
    sheet = {k: str(a.get(k) or '').strip()[:800] for k in keys}
    if not any(sheet.values()): abort(502, 'Claude did not give a care sheet this could read. Try again.')
    try: sheet['min_temp_f'] = round(float(a.get('min_temp_f')))
    except (TypeError, ValueError): sheet['min_temp_f'] = None
    for k in ('zone_low', 'zone_high'): sheet[k] = str(a.get(k) or '').strip()[:4] if zone_num(a.get(k)) is not None else None
    os.makedirs(CARE_DIR, exist_ok=True)
    rec = {'name': name, 'written_at': now(), 'asked_by': editor(), 'model': CLAUDE_MODEL, 'place': L['name'], 'zone': zone, 'sheet': sheet}
    with open(os.path.join(CARE_DIR, lib_slug(name) + '.json.tmp'), 'w', encoding='utf-8') as f: json.dump(rec, f)
    os.replace(os.path.join(CARE_DIR, lib_slug(name) + '.json.tmp'), os.path.join(CARE_DIR, lib_slug(name) + '.json'))
    audit_only(c, 'library', 'care sheet', None, name, editor(), f'Care sheet for {name} written by Claude'); c.commit()
    return jsonify(care=rec)

def lib_photo_state(name):
    """{'url', 'credit', ...} when kept, None when there is none, 'pending' while it is being fetched."""
    m = lib_meta(name)
    if m and m.get('photo'): return {'url': '/library-photos/' + m['photo']['file'], 'credit': m['photo']['credit'], 'license': m['photo']['license'], 'page': m['photo']['page']}
    fresh = m and m.get('checked') and (date.today() - date.fromisoformat(m['checked'])).days < LIB_RECHECK_DAYS
    if fresh or not lib_online(): return None
    return 'pending'

def owned_lists(c):
    sp, gn = species_owned(c)
    return '|'.join(sp), '|'.join(gn)

def own_photo(c, codes):
    for code in codes:
        b = plant_brief(c, code)
        if b and b['photo']: return '/thumbs/' + urllib.parse.quote(b['photo'])
    return None

@app.route('/api/library/browse')
def library_browse():
    """Every species in a list, filtered and sorted, a page at a time (see the picture checker's /browse)."""
    c, a = db(), request.args
    own, owngenus = owned_lists(c)
    q = {k: a.get(k, '')[:80] for k in ('scope', 'q', 'kind', 'family', 'genus', 'order', 'state', 'common', 'mine', 'sort', 'offset', 'limit')}
    q['scope'] = vscope(db(), q['scope'])
    if q['mine'] == 'wish':                        # 1.22.0: your wishlist, your notes and tags (names sent as the "own" list)
        q.update(mine='species', own='|'.join(r[0] for r in c.execute('SELECT name FROM wishlist')), owngenus='')
    elif q['mine'] == 'notes':
        q.update(mine='species', own='|'.join(r[0] for r in c.execute("SELECT name FROM species_notes WHERE notes<>'' OR tags<>''")), owngenus='')
    elif q['mine'].startswith('tag:'):
        t = q['mine'][4:].strip().lower()
        q.update(mine='species', own='|'.join(n for n, tg in c.execute("SELECT name, tags FROM species_notes WHERE tags<>''") if t in [x.strip() for x in tg.split(',')]), owngenus='')
    elif q['mine']: q.update(own=own, owngenus=owngenus)
    if q['mine'] == 'species' and not q.get('own'): q['own'] = '-'           # an empty list matches nothing
    kf = a.get('know', '')[:20]
    if kf in know_filters(c):                      # 1.23.0: the lists about the area, sent in the body (they can be long)
        only, genera = know_names(c, kf)
        body = {k: v for k, v in q.items() if v} | {'only': only or [], 'only_genera': genera or []}
        out = vision_call('/browse', json.dumps(body).encode(), 'application/json', timeout=30)
    else:
        out = vision_call('/browse?' + urllib.parse.urlencode({k: v for k, v in q.items() if v}), timeout=30)
    mark_owned(c, out.get('results', []))
    for x in out['results']:
        x['own_photo'] = own_photo(c, x['yours']) if x['yours'] else None
    return jsonify(out)

@app.route('/api/library/facets')
def library_facets():
    scope = request.args.get('scope', 'common')
    return jsonify(vision_call('/facets?' + urllib.parse.urlencode({'scope': vscope(db(), scope)}), timeout=30))

@app.route('/api/library/photos')
def library_photos():
    """?names=a|b|c: each one's photo, null when there is none, or "pending" while it is fetched in the background."""
    names = [n.strip() for n in request.args.get('names', '').split('|') if n.strip()][:150]
    out = {n: lib_photo_state(n) for n in names}
    if lib_online(): lib_enqueue([n for n, v in out.items() if v == 'pending'])
    return jsonify(photos=out, online=lib_online())

@app.route('/api/library/taxon')
def library_taxon():
    """One species in full, plus your plants of it and of its genus."""
    c, name = db(), request.args.get('name', '').strip()[:120]
    if not name: abort(400, 'Which species?')
    out = vision_call('/taxon?' + urllib.parse.urlencode({'name': name}), timeout=30)
    mark_owned(c, [out]); mark_owned(c, out.get('similar', []))
    out['your_plants'] = [plant_brief(c, x) for x in out['yours'] + out['yours_genus']]
    nt = c.execute('SELECT * FROM species_notes WHERE lower(name)=lower(?)', (out.get('scientific_name') or name,)).fetchone()
    out['notes'] = dict(nt) if nt else {'notes': '', 'tags': '', 'updated_by': None, 'updated_at': None}
    w = c.execute('SELECT * FROM wishlist WHERE lower(name)=lower(?)', (out.get('scientific_name') or name,)).fetchone()
    out['wishlist'] = dict(w) if w else None
    out['care'] = care_get(out.get('scientific_name') or name)
    out['zone'] = home_zone(c); out['home'] = home_place(c)['name']; out['near_km'] = NEAR_KM
    out['noxious_source'] = TX_NOXIOUS_SRC; out['noxious_law'] = TX_NOXIOUS_LAW; know_refresh(c)
    out['your_finds'] = [{'code': r['code'], 'name': r['name'], 'found_on': r['found_on'], 'id_status': r['id_status']}
                         for r in c.execute('SELECT * FROM fungi_finds WHERE lower(scientific_name)=lower(?) ORDER BY found_on DESC', (out.get('scientific_name') or name,))]
    m = lib_meta(name) or {}
    out['inat'] = {k: m.get(k) for k in ('inat_common', 'taxon_id', 'observations', 'wikipedia_url', 'summary', 'photos', 'detail_checked')}
    out['online'] = lib_online(c)
    return jsonify(out)

@app.route('/api/library/info', methods=['GET'])
def library_info():
    """The species' photos (up to 6) and short description, from iNaturalist, fetched on first view and then kept."""
    c, name = db(), request.args.get('name', '').strip()[:120]
    if not name: abort(400, 'Which species?')
    m = lib_meta(name) or {}
    fresh = m.get('detail_checked') and (date.today() - date.fromisoformat(m['detail_checked'])).days < LIB_RECHECK_DAYS
    if not fresh and lib_online(c):
        try:
            if 'taxon_id' not in m: m = lib_fetch_photo(name)
            if m.get('taxon_id'):
                t = (inat_get(f"/taxa/{int(m['taxon_id'])}?locale=en").get('results') or [{}])[0]
                summ = re.sub(r'<[^>]+>', '', t.get('wikipedia_summary') or '')
                photos = []
                for k, tp in enumerate((t.get('taxon_photos') or [])[:6]):
                    ph = tp.get('photo') or {}
                    url = (ph.get('medium_url') or ph.get('url') or '').replace('/medium.', '/large.')
                    if not url: continue
                    f = f'{lib_slug(name)}-{k + 1}.jpg'
                    try: lib_download(url, os.path.join(LIB_DIR, f)); photos.append(photo_meta(ph, f))
                    except Exception as e: print(f'[library] {name} photo {k + 1}: {e}', flush=True)
                m.update(summary=html_unescape(summ)[:3000], photos=photos, inat_common=t.get('preferred_common_name') or m.get('inat_common', ''),
                         observations=t.get('observations_count'), wikipedia_url=t.get('wikipedia_url') or m.get('wikipedia_url', ''))
            m['detail_checked'] = date.today().isoformat(); m.setdefault('name', name)
            lib_save(name, m)
        except Exception as e:
            return jsonify(error='Could not reach iNaturalist for the photos and description. They are tried again next time.', detail=str(e)[:200], online=True)
    return jsonify(summary=m.get('summary', ''), photos=[p | {'url': '/library-photos/' + p['file']} for p in (m.get('photos') or [])],
                   inat_common=m.get('inat_common', ''), observations=m.get('observations'), wikipedia_url=m.get('wikipedia_url', ''),
                   inat_url=f"https://www.inaturalist.org/taxa/{m['taxon_id']}" if m.get('taxon_id') else '', online=lib_online(c))

def html_unescape(t):
    import html as _h
    return _h.unescape(t).strip()

@app.route('/library-photos/<path:name>')
def library_photo_file(name):
    return send_from_directory(LIB_DIR, os.path.basename(name), max_age=86400)

@app.route('/api/library/settings', methods=['GET', 'PUT'])
def library_settings():
    """Whether the library may look up photos and descriptions on iNaturalist (owner only to change)."""
    c = db()
    if request.method == 'PUT':
        on = bool((request.get_json(silent=True) or {}).get('online'))
        set_setting(c, 'library_online', '1' if on else '0')
        audit_only(c, 'setting', 'library_online', None, 'on' if on else 'off', editor(), 'Library photos from iNaturalist turned ' + ('on' if on else 'off'))
        c.commit()
    return jsonify(online=lib_online(c))

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
        c.commit()
    pk, ck = setting(c, 'plantnet_key', ''), setting(c, 'claude_key', '')
    return jsonify(plantnet=bool(pk), plantnet_hint=key_hint(pk), claude=bool(ck), claude_hint=key_hint(ck), claude_model=CLAUDE_MODEL)

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
    c = db()
    key = setting(c, 'plantnet_key', '')
    if not key: abort(400, 'Pl@ntNet is not set up. The owner can save a key on the Identify page, under "Second opinions".')
    body, ct = multipart({'organs': 'auto'}, [('images', 'picture.jpg', picture_bytes(1280), 'image/jpeg')])
    url = PLANTNET_URL + '?' + urllib.parse.urlencode({'api-key': key, 'lang': 'en', 'nb-results': 5, 'include-related-images': 'false'})
    st, j = outside_call(url, body, {'Content-Type': ct})
    if st == 404: return jsonify(species=[], note='Pl@ntNet did not recognise a plant in that picture.')
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
    return jsonify(species=out, remaining=j.get('remainingIdentificationRequests'), source='Pl@ntNet')

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
