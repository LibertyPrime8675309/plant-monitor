"""Homes and places; where a plant is (inside or outside, the area or room, the spot); the Rooms and spots lists.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- 1.29.0: where a plant is: inside or outside, the area or room, the spot
# Each home has areas: outside (Yard, Covered porch...) and inside (Living room, Garage...). An outside area can be sheltered (a roof
# over it); an inside one can be heated. Those two decide the old Location field (Outdoors, Covered porch, Indoors, Garage or shed),
# which frost warnings, watering and the Winter plan still use, so it is always set from the area. Spots are inside an area.
SIDE_WORD = {'out': 'Outside', 'in': 'Inside'}
WHERE_DEFAULTS = [('out', 'Yard', 0), ('out', 'Covered porch', 1), ('in', 'Living room', 1)]

def site_of(side, sheltered):
    return ('Covered porch' if sheltered else 'Outdoors') if side == 'out' else ('Indoors' if sheltered else 'Garage or shed')

def side_of_site(site):
    return ('out', 1) if site == 'Covered porch' else ('in', 1) if site == 'Indoors' else ('in', 0) if site == 'Garage or shed' else ('out', 0)

def area_home(c, hid):
    """A plant's home id as areas store it: None for the main home."""
    if not hid: return None
    r = c.execute('SELECT is_home FROM locations WHERE id=?', (hid,)).fetchone()
    return None if (r is None or r[0]) else int(hid)

def area_for_site(c, hid, site, make=True):
    """The first area at a home that matches an old Location value; one is added if there is none."""
    side, sh = side_of_site(site or 'Outdoors')
    q = 'SELECT id FROM areas WHERE side=? AND sheltered=? AND ' + ('home_id IS NULL' if hid is None else 'home_id=?') + ' ORDER BY sort, id'
    r = c.execute(q, (side, sh) + (() if hid is None else (hid,))).fetchone()
    if r or not make: return r[0] if r else None
    name = {('out', 0): 'Yard', ('out', 1): 'Covered porch', ('in', 1): 'Living room', ('in', 0): 'Garage'}[(side, sh)]
    n = c.execute('SELECT COALESCE(MAX(sort),0)+1 FROM areas').fetchone()[0]
    return c.execute('INSERT INTO areas(home_id,side,name,sheltered,sort,created_by,created_at) VALUES(?,?,?,?,?,?,?)', (hid, side, name, sh, n, 'Plant record', now())).lastrowid

def where_seed(c):
    """Every home gets areas the first time; Rooms and shelves from the Grow lights page (and any a batch adds) become inside rooms
    and spots at the main home, and light spots follow them; every plant without an area gets the one matching its Location.
    Safe to run on every start."""
    ts = now(); changed = False
    if 'moved' not in {r[1] for r in c.execute('PRAGMA table_info(indoor_places)')}: c.execute('ALTER TABLE indoor_places ADD COLUMN moved INTEGER NOT NULL DEFAULT 0')
    for h in homes(c):
        hid = None if h['is_home'] else h['id']
        if c.execute('SELECT 1 FROM areas WHERE ' + ('home_id IS NULL' if hid is None else 'home_id=?'), (() if hid is None else (hid,))).fetchone(): continue
        has_rooms = hid is None and c.execute('SELECT 1 FROM indoor_places WHERE moved=0').fetchone()
        for k, (side, name, sh) in enumerate(x for x in WHERE_DEFAULTS if not (has_rooms and x[0] == 'in')):
            c.execute('INSERT INTO areas(home_id,side,name,sheltered,sort,created_by,created_at) VALUES(?,?,?,?,?,?,?)', (hid, side, name, sh, k + 1, 'Plant record', ts))
        changed = True
    rooms = c.execute('SELECT * FROM indoor_places WHERE moved=0 ORDER BY sort, id').fetchall()
    if rooms:
        first = not setting(c, 'where_lights_1290')
        lone = c.execute("SELECT id FROM areas WHERE home_id IS NULL AND side='in'").fetchall()
        if len(lone) == 1 and not c.execute('SELECT 1 FROM plants WHERE area_id=?', (lone[0][0],)).fetchone() and \
                c.execute("SELECT created_by FROM areas WHERE id=?", (lone[0][0],)).fetchone()[0] == 'Plant record' and \
                not c.execute('SELECT 1 FROM spots WHERE area_id=?', (lone[0][0],)).fetchone():
            c.execute('DELETE FROM areas WHERE id=?', (lone[0][0],))          # the stand-in "Living room": the real rooms replace it
        remap = {}
        for r in rooms:
            a = c.execute("SELECT id FROM areas WHERE home_id IS NULL AND side='in' AND name=?", (r['room'],)).fetchone()
            aid = a[0] if a else c.execute('INSERT INTO areas(home_id,side,name,sheltered,sort,created_by,created_at) VALUES(NULL,?,?,?,(SELECT COALESCE(MAX(sort),0)+1 FROM areas),?,?)',
                                           ('in', r['room'], 0 if re.search(r'garage|shed|barn', r['room'], re.I) else 1, 'Plant record', ts)).lastrowid
            if r['name']:
                sp = c.execute('SELECT id FROM spots WHERE area_id=? AND name=?', (aid, r['name'])).fetchone()
                remap[r['id']] = sp[0] if sp else c.execute('INSERT INTO spots(area_id,name,sort,created_by,created_at) VALUES(?,?,?,?,?)', (aid, r['name'], r['sort'], 'Plant record', ts)).lastrowid
            else: remap[r['id']] = -aid
            c.execute('UPDATE indoor_places SET moved=1 WHERE id=?', (r['id'],))
        if first:                                         # light spots set up before 1.29.0 named the old rows
            for sid, pid in c.execute('SELECT id, place_id FROM light_spots WHERE place_id IS NOT NULL').fetchall():
                c.execute('UPDATE light_spots SET place_id=? WHERE id=?', (remap.get(pid), sid))
        changed = True
    if not setting(c, 'where_lights_1290'): set_setting(c, 'where_lights_1290', ts); changed = True
    for r in c.execute('SELECT id, home_id, site FROM plants WHERE area_id IS NULL').fetchall():
        c.execute('UPDATE plants SET area_id=? WHERE id=?', (area_for_site(c, area_home(c, r['home_id']), r['site'] or 'Outdoors'), r['id'])); changed = True
    if changed: c.commit()

def place_sync(c, r, f):
    """Keeps a plant's home, area, spot and old Location in step, whichever of them a change names. f is the change (a dict)."""
    get = lambda k: f[k] if k in f else (r[k] if r is not None else None)
    hid = area_home(c, get('home_id') or None)
    def area_row(a):
        try: return c.execute('SELECT * FROM areas WHERE id=?', (int(a),)).fetchone() if a not in (None, '', 0, '0') else None
        except (TypeError, ValueError): return None
    if f.get('spot_id') not in (None, '', 0, '0') and 'area_id' not in f:
        try: sp = c.execute('SELECT area_id FROM spots WHERE id=?', (int(f['spot_id']),)).fetchone()
        except (TypeError, ValueError): sp = None
        if sp: f['area_id'] = sp[0]
    A = area_row(get('area_id'))
    if 'area_id' in f and A is not None:
        f['site'] = site_of(A['side'], A['sheltered'])
    elif ('site' in f or 'home_id' in f) and (A is None or A['home_id'] != hid or site_of(A['side'], A['sheltered']) != (get('site') or 'Outdoors')):
        f['area_id'] = area_for_site(c, hid, get('site') or 'Outdoors'); A = area_row(f['area_id'])
    if A is not None and get('spot_id') not in (None, '', 0, '0'):
        try: ok = c.execute('SELECT 1 FROM spots WHERE id=? AND area_id=?', (int(get('spot_id')), A['id'])).fetchone()
        except (TypeError, ValueError): ok = None
        if not ok: f['spot_id'] = None
    return f

def homes(c):
    """1.28.0: the places where plants live: the main home first, then any place marked "Plants live here"."""
    return [loc_dict(r) for r in c.execute('SELECT * FROM locations WHERE is_home=1 OR plants_here=1 ORDER BY is_home DESC, name')]

def plants_at(c, L):
    """1.28.0: SQL (and its argument) that keeps the plants at the place in use. A place where no plants live (a weather place
    you are only watching) shows the main home's plants, as before homes existed."""
    H = home_place(c)
    if not (L.get('is_home') or L.get('plants_here')): L = H
    return ' AND COALESCE(home_id, ?)=?', [H['id'], L['id']]

def home_place(c):
    """The home place: the one every browser starts with, and the one background work (hourly updates, backups) uses."""
    return loc_get(c)

FORCED_PLACE = threading.local()
class place_for:
    """1.33.0: `with place_for(home_id):` makes location() answer that place in this thread, so background work (notifications)
    can use the same reports the pages use, home by home."""
    def __init__(self, loc_id): self.id = loc_id
    def __enter__(self): self.was = getattr(FORCED_PLACE, 'id', None); FORCED_PLACE.id = self.id
    def __exit__(self, *a): FORCED_PLACE.id = self.was

def location(c):
    """The place in use (1.11.0): the one chosen with the Location button in this browser, which the page sends as the
    X-Place header on every request; the home place when none is chosen, or the chosen one has been removed.
    Weather, frost warnings, watering, the Winter plan and "today" all follow it."""
    forced = getattr(FORCED_PLACE, 'id', None)
    if forced is not None:
        L = loc_get(c, forced)
        if L is not None: return L
    if has_request_context():
        v = request.headers.get('X-Place', '').strip()
        if v.isdigit():
            L = loc_get(c, v)
            if L is not None: return L
    return loc_get(c)

PLACE_CLIMATE = {}
USDA_MAP_URL = 'https://planthardiness.ars.usda.gov/'

def usda_zone(f):
    """USDA hardiness zone for an average yearly coldest night (F): zone 1a starts at -60 F, each half zone is 5 F."""
    if f is None: return None
    n = math.floor((f + 60) / 5)
    if n < 0: return '1a'
    if n > 25: return '13b'
    return '%d%s' % (n // 2 + 1, 'ab'[n % 2])

def zone_num(z):
    """'9a' -> 9.0, '9b' -> 9.5, '10' -> 10.0; None if it is not a zone."""
    m = re.match(r'^\s*(\d{1,2})\s*([ab])?\s*$', str(z or ''), re.I)
    return int(m.group(1)) + (0.5 if (m.group(2) or '').lower() == 'b' else 0.0) if m else None

def place_zone(c, L):
    """1.14.0: the hardiness zone where the plants are, from the place's own weather history (the average of each winter's
    coldest night, which is how the USDA defines zones), and for the Round Rock area the 2023 USDA map's zone too."""
    cl = place_climate(c, L)
    near_ref = L.get('lat') is not None and abs(L['lat'] - REF_PLACE[0]) < 0.25 and abs(L['lon'] - REF_PLACE[1]) < 0.25
    return {'zone': usda_zone(cl['winter_low']) if cl else None, 'winter_low': cl['winter_low'] if cl else None, 'years': cl['years'] if cl else 0,
            'map_zone': '8b to 9a' if near_ref else None, 'map_note': 'Round Rock is on the line between zones 8b and 9a on the 2023 USDA map.' if near_ref else None,
            'map_url': USDA_MAP_URL}

def place_climate(c, L):
    """Typical winter cold at a place, from its daily weather history: the average of each winter's coldest night, and the
    average night in its coldest month. Needs at least 3 whole years of history; worked out at most every 6 hours."""
    hit = PLACE_CLIMATE.get(L['id'])
    if hit and time.time() - hit[0] < 6 * 3600: return hit[1]
    lows, winters = {}, {}
    try: rows = c.execute("SELECT date, json_extract(data, '$.temperature_2m_min') FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],)).fetchall()
    except sqlite3.OperationalError:            # an SQLite without JSON functions
        rows = [(d, (json.loads(x) if x else {}).get('temperature_2m_min')) for d, x in c.execute("SELECT date, data FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],))]
    for d, t in rows:
        if not isinstance(t, (int, float)): continue
        y, m = int(d[:4]), int(d[5:7])
        lows.setdefault(m, []).append(t)
        winters.setdefault(y if m >= 7 else y - 1, []).append(t)        # a winter runs from July to June
    whole = [v for v in winters.values() if len(v) >= 330]
    out = None
    if len(whole) >= 3 and len(lows) == 12:
        cold = min(lows, key=lambda m: sum(lows[m]) / len(lows[m]))
        warm = max(lows, key=lambda m: sum(lows[m]) / len(lows[m]))
        winter = sorted(m for m in range(1, 13) if min(abs(m - cold), 12 - abs(m - cold)) <= 1)     # the coldest month and the ones either side
        rh = None
        try:
            r = c.execute(f"SELECT AVG(json_extract(data, '$.relative_humidity_2m_mean')) FROM weather_daily WHERE loc_id=? AND kind='observed' "
                          f"AND CAST(substr(date, 6, 2) AS INTEGER) IN ({','.join('?' * len(winter))})", (L['id'], *winter)).fetchone()
            rh = round(r[0]) if r and r[0] is not None else None
        except sqlite3.OperationalError: pass
        out = {'winter_low': round(sum(min(v) for v in whole) / len(whole)), 'cold_month': cold, 'warm_month': warm,
               'cold_month_low': round(sum(lows[cold]) / len(lows[cold])), 'winter_months': winter, 'winter_rh': rh, 'years': len(whole)}
    PLACE_CLIMATE[L['id']] = (time.time(), out)
    return out

def place_brief(L):
    return {k: L.get(k) for k in ('id', 'name', 'tz', 'is_home', 'enabled', 'plants_here', 'country', 'units', 'season')}   # 1.48.0: a home is a site

def tzinfo(name):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        return timezone(timedelta(hours=-6))

def iso(t): return datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def parse_ts(s):
    s = str(s).strip().replace('Z', '+00:00')
    d = datetime.fromisoformat(s)
    if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)

def vpd_kpa(temp_f, rh):
    if temp_f is None or rh is None: return None
    t = (temp_f - 32) / 1.8
    es = 0.6108 * math.exp(17.27 * t / (t + 237.3))
    return round(es * (1 - rh / 100.0), 2)

class OMError(Exception):
    def __init__(self, code, reason=''):
        super().__init__(f'HTTP {code}: {reason}'[:300]); self.code, self.reason = code, reason

NET_RETRY_WAITS = (5, 15, 45, 90)     # seconds to wait before each retry after a dropped connection or a busy server

def _wait(sec, why):
    WX_JOB.update(waiting_until=time.time() + sec, waiting_why=why, beat=time.time())
    time.sleep(sec)
    WX_JOB.pop('waiting_until', None); WX_JOB.pop('waiting_why', None)

def http_json(url, tries=3):
    """Fetch JSON from Open-Meteo. Dropped connections, timeouts and server hiccups (5xx) are retried up to 4 times
    with growing pauses (5 s, 15 s, 45 s, 90 s); the per-minute limit is waited out. Other refusals raise OMError."""
    req = urllib.request.Request(url, headers={'User-Agent': 'plant-database/1.3 (home garden record)'})
    minute_waits = 0
    for attempt in range(len(NET_RETRY_WAITS) + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            WX_JOB['retries_in_a_row'] = 0
            return json.loads(data.decode('utf-8'))
        except urllib.error.HTTPError as e:
            try: reason = json.loads(e.read().decode('utf-8')).get('reason', '')
            except Exception: reason = str(e.reason)
            if e.code == 429 and 'minutely' in reason.lower() and minute_waits < tries:
                minute_waits += 1; _wait(62, "Open-Meteo's per-minute limit"); continue
            if e.code >= 500 and attempt < len(NET_RETRY_WAITS):
                WX_JOB['retries'] = WX_JOB.get('retries', 0) + 1
                _wait(NET_RETRY_WAITS[attempt], f'Open-Meteo was busy (HTTP {e.code}); trying again'); continue
            raise OMError(e.code, reason)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError) as e:
            # the connection dropped part-way (for example "UNEXPECTED_EOF_WHILE_READING"), timed out, or came back garbled
            if attempt < len(NET_RETRY_WAITS):
                WX_JOB['retries'] = WX_JOB.get('retries', 0) + 1
                _wait(NET_RETRY_WAITS[attempt], 'the connection to Open-Meteo dropped; trying again'); continue
            raise

# ---------------------------------------------------------------- 1.29.0: Rooms and spots (the lists behind a plant's place)
def where_list(c):
    H = home_place(c)
    cnt_a = {k: n for k, n in c.execute("SELECT area_id, COUNT(*) FROM plants WHERE status='active' GROUP BY area_id")}
    cnt_s = {k: n for k, n in c.execute("SELECT spot_id, COUNT(*) FROM plants WHERE status='active' AND spot_id IS NOT NULL GROUP BY spot_id")}
    lights_at = {k: n for k, n in c.execute('SELECT place_id, COUNT(*) FROM light_spots WHERE place_id IS NOT NULL GROUP BY place_id')}
    pph = place_photo_map(c)                   # 1.56.0: the main photo of each room and shelf
    out = []
    for h in homes(c):
        hid = None if h['is_home'] else h['id']
        areas = c.execute('SELECT * FROM areas WHERE ' + ('home_id IS NULL' if hid is None else 'home_id=?') + ' ORDER BY side DESC, sort, id', (() if hid is None else (hid,))).fetchall()
        out.append({'home': place_brief(h), 'areas': [{'id': a['id'], 'side': a['side'], 'name': a['name'], 'sheltered': bool(a['sheltered']), 'site': site_of(a['side'], a['sheltered']),
                    'plants': cnt_a.get(a['id'], 0), 'lights': lights_at.get(-a['id'], 0), 'photo': pph.get(-a['id']), 'sheet': sheet_words(sheet_of(a)),
                    'spots': [{'id': sp['id'], 'name': sp['name'], 'plants': cnt_s.get(sp['id'], 0), 'lights': lights_at.get(sp['id'], 0), 'photo': pph.get(sp['id']), 'sheet': sheet_words(sheet_of(sp))}
                              for sp in c.execute('SELECT * FROM spots WHERE area_id=? ORDER BY sort, id', (a['id'],))]} for a in areas]})
    return out

def where_area_delete(c, aid, who):
    a = c.execute('SELECT * FROM areas WHERE id=?', (aid,)).fetchone()
    if not a: abort(404, 'That area is not in the list')
    n = c.execute('SELECT COUNT(*) FROM plants WHERE area_id=?', (aid,)).fetchone()[0]
    if n: abort(409, f'{n} plant{"s are" if n != 1 else " is"} in {a["name"]}. Move {"them" if n != 1 else "it"} somewhere else first.')
    ids = [r[0] for r in c.execute('SELECT id FROM spots WHERE area_id=?', (aid,))]
    for sid in ids: c.execute('UPDATE light_spots SET place_id=NULL WHERE place_id=?', (sid,))
    c.execute('UPDATE light_spots SET place_id=NULL WHERE place_id=?', (-aid,))
    place_photos_drop(c, 'area_id=?', aid)                 # 1.56.0: its photos and its shelves' photos
    c.execute('DELETE FROM spots WHERE area_id=?', (aid,)); c.execute('DELETE FROM areas WHERE id=?', (aid,))
    audit_only(c, 'where', 'area', a['name'], None, who, f'Area or room removed: {a["name"]}'); c.commit()
    return jsonify(ok=True)

def where_spot_delete(c, sid, who):
    sp = c.execute('SELECT s.*, a.name AS area FROM spots s JOIN areas a ON a.id=s.area_id WHERE s.id=?', (sid,)).fetchone()
    if not sp: abort(404, 'That spot is not in the list')
    n = c.execute('SELECT COUNT(*) FROM plants WHERE spot_id=?', (sid,)).fetchone()[0]
    c.execute('UPDATE plants SET spot_id=NULL WHERE spot_id=?', (sid,)); c.execute('UPDATE light_spots SET place_id=? WHERE place_id=?', (-sp['area_id'], sid))
    place_photos_drop(c, 'spot_id=?', sid)
    c.execute('DELETE FROM spots WHERE id=?', (sid,))
    audit_only(c, 'where', 'spot', f'{sp["area"]}, {sp["name"]}', None, who, f'Spot removed: {sp["area"]}, {sp["name"]}' + (f' ({n} plant{"s" if n != 1 else ""} there now just say {sp["area"]})' if n else ''))
    c.commit()
    return jsonify(ok=True, plants=n)

def place_photos_drop(c, where, v):
    for (f,) in c.execute(f'SELECT file FROM place_photos WHERE {where}', (v,)).fetchall():
        try: os.remove(os.path.join(PHOTO_DIR, f))
        except OSError: pass
    c.execute(f'DELETE FROM place_photos WHERE {where}', (v,))

def where_name(b, what):
    n = re.sub(r'\s+', ' ', str(b.get('name', ''))).strip()[:60]
    if not n: abort(400, f'Give the {what} a name')
    return n

@app.route('/api/where')
def where_get():
    return jsonify(homes=where_list(db()), sides=SIDE_WORD)

@app.route('/api/where/areas', methods=['POST'])
def where_area_add():
    """{home_id, side: 'in'|'out', name, sheltered}: sheltered is a roof overhead outside, or heated inside."""
    c = db(); b = request.get_json(silent=True) or {}; who = editor()
    side = b.get('side'); name = where_name(b, 'area or room')
    if side not in SIDE_WORD: abort(400, 'Choose inside or outside')
    hid = area_home(c, b.get('home_id') or None)
    if c.execute('SELECT 1 FROM areas WHERE side=? AND name=? AND ' + ('home_id IS NULL' if hid is None else 'home_id=?'), (side, name) + (() if hid is None else (hid,))).fetchone():
        abort(409, f'"{name}" is already there')
    aid = c.execute('INSERT INTO areas(home_id,side,name,sheltered,sort,created_by,created_at) VALUES(?,?,?,?,(SELECT COALESCE(MAX(sort),0)+1 FROM areas),?,?)',
                    (hid, side, name, 1 if b.get('sheltered') else 0, who, now())).lastrowid
    audit_only(c, 'where', 'area', None, name, who, f'Area or room added: {name} ({SIDE_WORD[side].lower()})'); c.commit()
    return jsonify(id=aid, homes=where_list(c)), 201

@app.route('/api/where/areas/<int:aid>', methods=['PUT', 'DELETE'])
def where_area_one(aid):
    c = db(); who = editor()
    if request.method == 'DELETE': return where_area_delete(c, aid, who)
    a = c.execute('SELECT * FROM areas WHERE id=?', (aid,)).fetchone()
    if not a: abort(404, 'That area is not in the list')
    b = request.get_json(silent=True) or {}
    name = where_name(b, 'area or room') if 'name' in b else a['name']
    sh = (1 if b['sheltered'] else 0) if 'sheltered' in b else a['sheltered']
    c.execute('UPDATE areas SET name=?, sheltered=? WHERE id=?', (name, sh, aid))
    if sh != a['sheltered']:                         # the plants there now count as sheltered (or not) for frost and watering
        for r in c.execute('SELECT * FROM plants WHERE area_id=?', (aid,)).fetchall():
            apply_changes(c, r, {'site': site_of(a['side'], sh), 'area_id': aid}, who, 'update', f'{name} is now {"sheltered" if sh else "open"}')
    audit_only(c, 'where', 'area', a['name'], name, who, f'Area or room changed: {name}'); c.commit()
    return jsonify(homes=where_list(c))

@app.route('/api/where/spots', methods=['POST'])
def where_spot_add():
    c = db(); b = request.get_json(silent=True) or {}; who = editor()
    name = where_name(b, 'spot')
    a = c.execute('SELECT * FROM areas WHERE id=?', (int(b.get('area_id') or 0),)).fetchone()
    if not a: abort(400, 'Choose the area or room it is in')
    if c.execute('SELECT 1 FROM spots WHERE area_id=? AND name=?', (a['id'], name)).fetchone(): abort(409, f'"{name}" is already in {a["name"]}')
    sid = c.execute('INSERT INTO spots(area_id,name,sort,created_by,created_at) VALUES(?,?,(SELECT COALESCE(MAX(sort),0)+1 FROM spots),?,?)', (a['id'], name, who, now())).lastrowid
    audit_only(c, 'where', 'spot', None, f'{a["name"]}, {name}', who, f'Spot added: {a["name"]}, {name}'); c.commit()
    return jsonify(id=sid, homes=where_list(c)), 201

@app.route('/api/where/spots/<int:sid>', methods=['PUT', 'DELETE'])
def where_spot_one(sid):
    c = db(); who = editor()
    if request.method == 'DELETE': return where_spot_delete(c, sid, who)
    sp = c.execute('SELECT s.*, a.name AS area FROM spots s JOIN areas a ON a.id=s.area_id WHERE s.id=?', (sid,)).fetchone()
    if not sp: abort(404, 'That spot is not in the list')
    name = where_name(request.get_json(silent=True) or {}, 'spot')
    c.execute('UPDATE spots SET name=? WHERE id=?', (name, sid))
    audit_only(c, 'where', 'spot', f'{sp["area"]}, {sp["name"]}', f'{sp["area"]}, {name}', who, f'Spot renamed: {sp["area"]}, {name}'); c.commit()
    return jsonify(homes=where_list(c))

def spot_guess(text):
    """'Black bench, yard' -> 'Black bench'; 'On the pallet shelf by the door' -> 'Pallet shelf by the door'."""
    t = re.split(r'[,;(]| - ', str(text or ''))[0].strip()
    t = re.sub(r'^(on|in|under|beside|by|at)\s+(the\s+)?', '', t, flags=re.I).strip()
    return (t[:1].upper() + t[1:])[:60] if t else ''

@app.route('/api/where/sort', methods=['GET', 'POST'])
def where_sort():
    """GET: each "Spot (where exactly)" text of plants with no spot yet, with a suggested spot name. POST {items: [{text, area_id, name}]}
    makes the spots (or uses ones already there) and puts those plants in them. The text itself is kept."""
    c = db()
    if request.method == 'GET':
        out = {}
        for r in c.execute("SELECT id, code, common_name, location, area_id FROM plants WHERE status='active' AND spot_id IS NULL AND TRIM(COALESCE(location,''))<>'' ORDER BY location, code"):
            k = (r['location'].strip(), r['area_id'])
            out.setdefault(k, {'text': k[0], 'area_id': k[1], 'name': spot_guess(k[0]), 'plants': []})['plants'].append(
                {'code': r['code'], 'name': r['common_name'], 'photo': plant_photo(c, r['id'])})         # 1.56.1: a small photo of each
        return jsonify(items=list(out.values()))
    b = request.get_json(silent=True) or {}; who = editor(); n = 0
    for it in b.get('items') or []:
        name = re.sub(r'\s+', ' ', str(it.get('name') or '')).strip()[:60]
        if not name: continue
        a = c.execute('SELECT * FROM areas WHERE id=?', (int(it.get('area_id') or 0),)).fetchone()
        if not a: continue
        sp = c.execute('SELECT id FROM spots WHERE area_id=? AND name=?', (a['id'], name)).fetchone()
        sid = sp[0] if sp else c.execute('INSERT INTO spots(area_id,name,sort,created_by,created_at) VALUES(?,?,(SELECT COALESCE(MAX(sort),0)+1 FROM spots),?,?)', (a['id'], name, who, now())).lastrowid
        for r in c.execute("SELECT * FROM plants WHERE status='active' AND spot_id IS NULL AND TRIM(location)=? AND area_id IS ?", (str(it.get('text') or '').strip(), a['id'])).fetchall():
            apply_changes(c, r, {'spot_id': sid, 'area_id': a['id']}, who, 'update', f'Put in the spot {a["name"]}, {name}'); n += 1
    c.commit()
    return jsonify(moved=n, homes=where_list(c))

def light_fields(b, old=None):
    d = dict(old or {})
    name = re.sub(r'\s+', ' ', str(b.get('name', ''))).strip()[:80]
    if not name: abort(400, 'Type the name of the light')
    count = int(_num(b, 'count', 0, 100, 'How many you have', required=True))
    if 'watts' in b: d['watts'] = _num(b, 'watts', 0, 2000, 'Watts')
    if 'points' in b:                  # "12 in 719, 24 in 234 ..." or "12: 719 (0.5 sq ft)"
        pts = []
        text = re.sub(r'(?<=\d),(?=\d{3}(?!\d))', '', str(b.get('points') or ''))   # 1.56.2: "2,496" is two thousand four hundred and ninety-six
        for part in re.split(r'[,;\n]+', text):
            nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', part)]
            if not part.strip(): continue
            if len(nums) < 2: abort(400, f'"{part.strip()}" needs a distance in inches and a PPFD, like "12 in 719"')
            pts.append([nums[0], nums[1], nums[2] if len(nums) > 2 else None])
        d['ppfd'] = pts
    if 'kind' in b: d['kind'] = str(b.get('kind') or '').strip()[:40]
    if 'model' in b: d['model'] = str(b.get('model') or '').strip()[:80]       # 1.13.1: the maker's model number
    if 'timer' in b: d['timer'] = str(b.get('timer') or '').strip()[:120]
    if 'dimming' in b: d['dimming'] = sorted({int(x) for x in re.findall(r'\d+', str(b.get('dimming') or '')) if 0 < int(x) <= 100}) or [100]
    for k, n in (('brand', 60), ('url', 400), ('cri', 20)):          # 1.56.0 (PLAN.md step 10b): what a listing gives
        if k in b:
            v = str(b.get(k) or '').strip()[:n]
            if k == 'url' and v and not re.match(r'^https?://', v): abort(400, 'The link must start with http:// or https://')
            if v: d[k] = v
            else: d.pop(k, None)
    if 'kelvin' in b: d['kelvin'] = int(_num(b, 'kelvin', 1000, 10000, 'Colour temperature (K)') or 0) or None
    if 'price' in b:
        d['price'] = _num(b, 'price', 0, 100000, 'Price')
        if d['price'] is None: d.pop('price_on', None)
        else:
            on = str(b.get('price_on') or '')[:10] or date.today().isoformat()
            try: date.fromisoformat(on)
            except ValueError: abort(400, 'The date of the price must be a date')
            d['price_on'] = on
    if 'direction' in b:
        v = str(b.get('direction') or '')
        if v not in ('', 'down', 'side', 'angled'): abort(400, 'Choose down, sideways or at an angle')
        d['direction'] = v or None
    for k in ('timer_repeats', 'timer_keeps', 'needs_socket'):
        if k in b: d[k] = None if b.get(k) in (None, '') else b.get(k) in (True, 1, '1', 'true', 'yes')
    if 'mount' in b:                   # 1.56.0 (PLAN.md step 8a): how it holds (fit.py)
        m = mount_clean(b.get('mount'))
        if m: d['mount'] = m
        else: d.pop('mount', None)
    return name, count, str(b.get('fixture', '')).strip()[:600], str(b.get('notes', '')).strip()[:2000], d      # 1.29.0: longer, so batch text is never cut

def light_text(name, count, fixture):
    return '%s (%d)%s' % (name, count, ', ' + fixture if fixture else '')

@app.route('/api/lights', methods=['POST'])
def light_add():
    """A light you have: {name, count, watts, points, kind, timer, dimming, fixture, notes}"""
    c = db()
    b = request.get_json(silent=True) or {}
    status = str(b.get('status') or 'owned')                   # 1.56.0 (PLAN.md step 10b): a light you are considering has none yet
    if status not in ('owned', 'considering'): abort(400, 'A new light is one you have or one you are considering')
    if status == 'considering': b = {**b, 'count': 0}
    name, count, fixture, notes, d = light_fields(b)
    if c.execute('SELECT 1 FROM lights WHERE name=?', (name,)).fetchone(): abort(409, f'"{name}" is already in your lights')
    who = editor()
    lid = c.execute('INSERT INTO lights(lkey,name,data,count,fixture,notes,sort,status,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (None, name, json.dumps(d), count, fixture, notes, 1000, status, who, now())).lastrowid
    audit_only(c, 'light', 'light', None, light_text(name, count, fixture), who, ('Grow light being considered: ' if status == 'considering' else 'Grow light added: ') + light_text(name, count, fixture))
    c.commit()
    return jsonify(id=lid), 201

@app.route('/api/lights/<int:i>', methods=['PUT', 'DELETE'])
def light_one(i):
    c = db()
    old = c.execute('SELECT * FROM lights WHERE id=?', (i,)).fetchone()
    if not old: abort(404, 'That light is not in your list')
    who = editor()
    if request.method == 'DELETE':
        n = c.execute('SELECT COUNT(*) FROM light_spots WHERE light_id=?', (i,)).fetchone()[0]
        if n: abort(409, f'"{old["name"]}" is used by {n} spot{"s" if n != 1 else ""}. Change or remove those spots first.')
        c.execute('DELETE FROM lights WHERE id=?', (i,))
        audit_only(c, 'light', 'light', light_text(old['name'], old['count'], old['fixture']), None, who, 'Grow light removed: ' + old['name'])
        c.commit()
        return jsonify(ok=True)
    b = {'name': old['name'], 'count': old['count'], 'fixture': old['fixture'] or '', 'notes': old['notes'] or '', **(request.get_json(silent=True) or {})}   # 1.29.0: one field at a time
    name, count, fixture, notes, d = light_fields(b, light_specs(old))
    if old['status'] != 'owned' and count: abort(400, 'Use "Bought it" to say how many you have of a light you were considering')
    if c.execute('SELECT 1 FROM lights WHERE name=? AND id<>?', (name, i)).fetchone(): abort(409, f'"{name}" is already in your lights')
    c.execute('UPDATE lights SET name=?,count=?,fixture=?,notes=?,data=?,updated_by=?,updated_at=? WHERE id=?', (name, count, fixture, notes, json.dumps(d), who, now(), i))
    a, z = light_text(old['name'], old['count'], old['fixture']), light_text(name, count, fixture)
    audit_only(c, 'light', 'light', a, z, who, 'Grow light changed: ' + z + ('' if light_specs(old) == d else ' (specs changed)'))
    c.commit()
    return jsonify(ok=True)

# ---------- 1.34.0: labels for rooms, areas and spots (a code that opens the Plants page showing what lives there) ----------
@app.route('/api/where/qr.svg')
def where_qr():
    """GET /api/where/qr.svg?area=ID or ?spot=ID[&base=URL]: the code for a room or area, or for a spot (shelf, bench, window)."""
    c = db()
    base = request.args.get('base', '').rstrip('/') or request.host_url.rstrip('/')
    if not re.match(r'^https?://[\w.\-]+(:\d+)?$', base): abort(400, 'bad base url')
    spot, area = request.args.get('spot'), request.args.get('area')
    if spot:
        if not c.execute('SELECT 1 FROM spots WHERE id=?', (spot,)).fetchone(): abort(404, 'No such spot')
        target = f'{base}/#/plants?spot={int(spot)}'
    elif area:
        if not c.execute('SELECT 1 FROM areas WHERE id=?', (area,)).fetchone(): abort(404, 'No such area')
        target = f'{base}/#/plants?area={int(area)}'
    else: abort(400, 'area or spot is needed')
    buf = io.BytesIO()
    segno.make(target, error='m').save(buf, kind='svg', scale=6, border=2, dark='#000', light='#fff', xmldecl=False, svgns=True)
    return Response(buf.getvalue(), mimetype='image/svg+xml')
