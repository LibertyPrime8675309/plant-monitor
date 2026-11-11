"""The plant library: browse every species, its record and photos (from iNaturalist, kept in data/library), library photos for
offline use by area, each species near home and for pets, care sheets, notes and tags. 1.57.0: Identify moved to identify.py, the uses
and partners to speciesfacts.py and the wishlist routes to shopping.py (review item 25). Split out of server.py in 1.32.0; the names it
uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403

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
