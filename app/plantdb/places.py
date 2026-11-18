"""Places: the homes and weather places (the locations table), loc_get() and friends, and the /api/places routes.
Split out of weather.py in 1.57.0 (review item 25); the names it uses from other modules are linked by server.py (core.link())."""
from .core import *   # noqa: F401,F403
import functools
from zoneinfo import ZoneInfo
# ---------------------------------------------------------------- places (1.5: several; 1.28.0: homes; 1.48.0: sites)
def migrate_places(c):
    """Version 1.5: weather can be tracked for several places. The place used until now becomes the home place
    (the one your plants are at) and keeps all its readings: its rows are tagged device 'open-meteo', as before."""
    if 'loc_id' not in {r[1] for r in c.execute('PRAGMA table_info(weather_runs)')}:
        c.execute('ALTER TABLE weather_runs ADD COLUMN loc_id INTEGER NOT NULL DEFAULT 1')
    if 'loc_id' not in {r[1] for r in c.execute('PRAGMA table_info(weather_daily)')}:
        c.execute('ALTER TABLE weather_daily RENAME TO weather_daily_v13')
        c.execute("""CREATE TABLE weather_daily(loc_id INTEGER NOT NULL DEFAULT 1, date TEXT NOT NULL, data TEXT NOT NULL,
                     kind TEXT NOT NULL DEFAULT 'observed', updated_at TEXT NOT NULL, PRIMARY KEY(loc_id, date))""")
        c.execute('INSERT INTO weather_daily(loc_id,date,data,kind,updated_at) SELECT 1,date,data,kind,updated_at FROM weather_daily_v13')
        c.execute('DROP TABLE weather_daily_v13')
    if not c.execute('SELECT 1 FROM locations LIMIT 1').fetchone():
        def st(k, d=None):
            r = c.execute('SELECT value FROM settings WHERE key=?', (k,)).fetchone()
            return r[0] if r else d
        try: old = {**DEFAULT_LOC, **json.loads(st('location', '') or '{}')}
        except ValueError: old = dict(DEFAULT_LOC)
        c.execute('INSERT INTO locations(id,name,lat,lon,tz,enabled,is_home,device,forecast,status,detail_since,created_at) VALUES(1,?,?,?,?,?,1,?,?,?,?,?)',
                  (old['name'], old['lat'], old['lon'], old['tz'], 1 if st('weather_enabled', '1') == '1' else 0, 'open-meteo',
                   st('forecast'), st('weather_status'), st('wx_detail_since'), now()))
    c.commit()

LOC_COLS = ('id', 'name', 'lat', 'lon', 'tz', 'enabled', 'is_home', 'device', 'detail_since', 'note', 'created_at', 'plants_here', 'country', 'units', 'season', 'tended')   # 1.48.0: the last three make a home a site
def loc_dict(r):
    d = {k: (r[k] if k in r.keys() else 0) for k in LOC_COLS}
    d['enabled'], d['is_home'], d['plants_here'] = bool(d['enabled']), bool(d['is_home']), bool(d['plants_here']) or bool(d['is_home'])
    d['tended'] = bool(r['tended']) if 'tended' in r.keys() else True       # 1.58.0: False = its plants are cared for outside the app
    for k in ('country', 'units'): d[k] = d[k] or ''
    d['season'] = d['season'] if d['season'] in SEASONS else 'temperate'
    d['window_dli'] = home_window_own(r['window_dli'] if 'window_dli' in r.keys() else '')     # 1.58.0: only the numbers this home gives itself
    return d

def home_window_own(v):
    """A home's own daylight at a window, by the way it faces (locations.window_dli): {facing: number}, only those it gives."""
    try: o = json.loads(v) if v else {}
    except ValueError: return {}
    return {k: float(o[k]) for k in WINDOW_DLI if isinstance(o, dict) and isinstance(o.get(k), (int, float))}

def home_window_dli(c, home_id=None):
    """The daylight at a window at a home, by the way it faces: its own numbers, else WINDOW_DLI. The main home when home_id is empty."""
    H = loc_get(c, home_id) if home_id else None
    if H is None: H = home_place(c)
    own = H.get('window_dli') or {}
    return {'dli': {k: own.get(k, v) for k, v in WINDOW_DLI.items()}, 'own': sorted(own, key=list(WINDOW_DLI).index), 'home_id': H.get('id'), 'home': H.get('name'),
            'lat': H.get('lat'), 'tz': H.get('tz')}

# ---------------------------------------------------------------- window daylight through the year, and today's weather
# 1.58.0 (Ethan, November 17, 2026: "Go ahead and implement both ideas please!", after "A window's daylight is one number all year.
# I could make it shorter in winter, or lower on cloudy days"). A home's window numbers are for a usual day across the year. How much
# of that a window gets on a given day depends on the sun's path there (its latitude and the date) and the way the window faces:
# the low winter sun comes straight in at a south window and hardly reaches a north one. window_year() works out, for each day and
# each way, the sunlight on an upright pane (sun straight in, light from the sky, and light off the ground, with the sun dimmed
# through the air when it is low), and divides by that way's average over the year. So 1 is a usual day; 0.6 is six tenths of it.
WIN_AZ = {'N': 0, 'NE': 45, 'E': 90, 'SE': 135, 'S': 180, 'SW': 225, 'W': 270, 'NW': 315}

@functools.lru_cache(maxsize=16)
def window_year(lat):
    """For latitude lat (degrees, rounded to 0.5 by the caller): {way: [366 numbers]}, day 1 first, each a share of that way's
    average day (1 = a usual day). Sun every 15 minutes."""
    phi = math.radians(max(-89.0, min(89.0, lat))); sp, cp = math.sin(phi), math.cos(phi)
    tot = {k: [0.0] * 366 for k in WIN_AZ}
    for n in range(1, 367):
        dec = math.radians(23.44) * math.sin(2 * math.pi * (284 + n) / 365); sd, cd = math.sin(dec), math.cos(dec)
        for i in range(96):
            h = math.radians(-180 + 3.75 * (i + 0.5))
            sa = sp * sd + cp * cd * math.cos(h)
            if sa <= 0.01: continue
            alt = math.asin(sa); ca = math.cos(alt)
            az = math.acos(max(-1.0, min(1.0, (sd - sa * sp) / (ca * cp))))      # from north, morning east of it
            if h > 0: az = 2 * math.pi - az
            am = 1 / (sa + 0.50572 * (math.degrees(alt) + 6.07995) ** -1.6364)
            ib = 1361 * 0.7 ** (am ** 0.678)                                       # the sun's beam through the air
            idh = 0.15 * ib                                                          # light from the sky onto the ground
            rest = 0.5 * idh + 0.5 * 0.2 * (ib * sa + idh)                           # half the sky, and the ground's light, on an upright pane
            for k, g in WIN_AZ.items():
                tot[k][n - 1] += max(0.0, ca * math.cos(az - math.radians(g))) * ib + rest
    out = {}
    for k, v in tot.items():
        avg = sum(v[:365]) / 365
        out[k] = [x / avg if avg else 1.0 for x in v]
    return out

def home_daylight(c, H):
    """How a home's window daylight changes with the time of year and today's weather (for a layout: day_k). H is home_window_dli's
    answer. {season: {way: share} for today, months: [{way: share} on the 15th of each month], today: {way: share} with the weather,
    or None, weather: today's sunlight as a share of the last 30 days', date}. The page and _ly_day multiply a window's number by
    one of them (season unless the person picks another)."""
    try: tz = ZoneInfo(H.get('tz') or 'UTC')
    except Exception: tz = timezone.utc
    day = datetime.now(tz).date()
    if H.get('lat') is None: one = {k: 1.0 for k in WIN_AZ}; return {'season': one, 'months': [one] * 12, 'today': None, 'weather': None, 'date': day.isoformat(), 'lat': None}
    Y = window_year(round(H['lat'] * 2) / 2)
    at = lambda d: {k: round(Y[k][d.timetuple().tm_yday - 1], 3) for k in WIN_AZ}
    season = at(day)
    months = [at(day.replace(month=m, day=15)) for m in range(1, 13)]
    wx = None
    if H.get('home_id'):
        rows = c.execute("SELECT date, data FROM weather_daily WHERE loc_id=? AND date<=? ORDER BY date DESC LIMIT 31", (H['home_id'], day.isoformat())).fetchall()
        sw = {}
        for d, x in rows:
            try: v = (json.loads(x) or {}).get('shortwave_radiation_sum')
            except ValueError: v = None
            if isinstance(v, (int, float)) and v >= 0: sw[d] = v
        now_v, past = sw.get(day.isoformat()), [v for d, v in sw.items() if d != day.isoformat()]
        if now_v is not None and len(past) >= 7 and sum(past) > 0: wx = round(max(0.2, min(1.6, now_v / (sum(past) / len(past)))), 2)
    today = {k: round(v * wx, 3) for k, v in season.items()} if wx is not None else None
    return {'season': season, 'months': months, 'today': today, 'weather': wx, 'date': day.isoformat(), 'lat': H['lat']}

def loc_get(c, loc_id=None):
    """A place by id; the home place when loc_id is empty. Falls back to the built-in default if the table is empty."""
    r = cur = None
    if loc_id not in (None, '', 'home'):
        try: cur = c.execute('SELECT * FROM locations WHERE id=?', (int(loc_id),)); r = cur.fetchone()
        except (TypeError, ValueError): r = None
        if r is None: return None
    else:
        cur = c.execute('SELECT * FROM locations ORDER BY is_home DESC, id LIMIT 1'); r = cur.fetchone()
    if r is not None and not isinstance(r, sqlite3.Row): r = dict(zip([d[0] for d in cur.description], r))   # works with plain connections too
    if r is None: return {**DEFAULT_LOC, 'id': 1, 'device': 'open-meteo', 'enabled': True, 'is_home': True, 'plants_here': True, 'detail_since': None, 'note': '', 'created_at': None}
    return loc_dict(r)

def loc_json(c, loc_id, col):
    r = c.execute(f'SELECT {col} FROM locations WHERE id=?', (loc_id,)).fetchone()
    try: return json.loads(r[0]) if r and r[0] else {}
    except ValueError: return {}

def loc_set(c, loc_id, **kw):
    for k, v in kw.items():
        c.execute(f'UPDATE locations SET {k}=? WHERE id=?', (v, loc_id))

def req_loc(c, key='loc'):
    """The place a request is about (?loc=ID, or loc in a JSON body); otherwise the place in use (see location())."""
    v = request.args.get(key)
    if v is None and request.is_json: v = (request.get_json(silent=True) or {}).get(key)
    if v in (None, ''): return location(c)
    L = loc_get(c, v)
    if L is None: abort(404, 'That place does not exist (it may have been removed)')
    return L

# ---- everything Open-Meteo offers for one place, gathered hourly and daily.
# Requested in imperial units (F, mph, inches). Each group is asked for separately, and a variable the service does not
# offer for a period (history has fewer than the forecast) is remembered and skipped instead of breaking the update.
def clean_place(b, old=None):
    old = old or {}
    try: lat, lon = float(b.get('lat', old.get('lat'))), float(b.get('lon', old.get('lon')))
    except (TypeError, ValueError): abort(400, 'Latitude and longitude must be numbers')
    if not (-90 <= lat <= 90 and -180 <= lon <= 180): abort(400, 'Latitude is -90 to 90 and longitude is -180 to 180')
    tz = str(b.get('tz', old.get('tz')) or '').strip()
    try:
        from zoneinfo import ZoneInfo; ZoneInfo(tz)
    except Exception: abort(400, 'Unknown time zone. Use a name like America/Chicago')
    name = str(b.get('name', old.get('name')) or '').strip()[:60]
    if not name: abort(400, 'Give the place a name')
    return {'name': name, 'lat': round(lat, 4), 'lon': round(lon, 4), 'tz': tz}

def places_list(c):
    out = []
    for r in c.execute('SELECT * FROM locations ORDER BY is_home DESC, name').fetchall():
        d = loc_dict(r)
        first, _, dd = wx_stats(c, d)
        try: st = json.loads(r['status'] or '{}')
        except ValueError: st = {}
        d.update(first=first[0], last=first[1], count=first[2], daily_first=dd[0], daily_count=dd[2], last_update=st.get('at'), last_ok=st.get('ok'), last_error=st.get('error'))
        H = home_place(c)                                # 1.28.0: how many plants live here
        d['plant_count'] = c.execute("SELECT COUNT(*) FROM plants WHERE status='active' AND COALESCE(home_id, ?)=?", (H['id'], d['id'])).fetchone()[0]
        out.append(d)
    return out

@app.route('/api/places', methods=['GET', 'POST'])
def places():
    c = db()
    if request.method == 'GET': return jsonify(places_list(c))
    b = request.get_json(silent=True) or {}
    P = clean_place(b)
    dup = c.execute('SELECT name FROM locations WHERE ABS(lat-?)<0.01 AND ABS(lon-?)<0.01', (P['lat'], P['lon'])).fetchone()
    if dup and not b.get('force'): abort(409, f'"{dup[0]}" is already at that spot')
    cur = c.execute('INSERT INTO locations(name,lat,lon,tz,enabled,is_home,created_at) VALUES(?,?,?,?,1,0,?)', (P['name'], P['lat'], P['lon'], P['tz'], now()))
    pid = cur.lastrowid
    c.execute('UPDATE locations SET device=? WHERE id=?', (f'place-{pid}', pid))
    if b.get('plants_here'): c.execute('UPDATE locations SET plants_here=1 WHERE id=?', (pid,))
    site_fields(c, pid, b)                                 # 1.48.0: country (from the search), units, season
    audit_only(c, 'setting', 'weather_place', None, json.dumps(P), editor(), f'Weather place added: {P["name"]}')
    c.commit()
    started = start_job('auto-first', None, [(pid, P['name'])])          # fetch its last 3 months and forecast straight away
    return jsonify(place=loc_get(c, pid), started=started), 201

def site_fields(c, pid, b):
    """1.48.0 (PLAN.md step 4b): what makes a home a site. country: a two-letter code ('US'); units: a region key from UNIT_REGIONS
    (the default for people who have not chosen their own); season: temperate, mild or tropical (SEASONS)."""
    if 'country' in b:
        cc = str(b.get('country') or '').strip().upper()
        if cc and not re.fullmatch(r'[A-Z]{2}', cc): abort(400, 'Country is a two-letter code, such as US or GB')
        c.execute('UPDATE locations SET country=? WHERE id=?', (cc, pid))
    if 'units' in b:
        u = str(b.get('units') or '').strip()
        if u and u not in UNIT_REGIONS: abort(400, 'Units must be one of: ' + ', '.join(UNIT_REGIONS))
        c.execute('UPDATE locations SET units=? WHERE id=?', ('' if u == 'us' else u, pid))
    if 'tended' in b:                                      # 1.58.0: is care for this home's plants logged in the app?
        on = str(b.get('tended')).strip().lower() not in ('0', 'false', 'no', '')
        c.execute('UPDATE locations SET tended=? WHERE id=?', (1 if on else 0, pid))
    if 'window_dli' in b:                                  # 1.58.0: {facing: number, or none to go back to the usual one}
        new = b.get('window_dli')
        if not isinstance(new, dict) or any(k not in WINDOW_DLI for k in new): abort(400, 'Window daylight is given by the way a window faces: ' + ', '.join(WINDOW_DLI))
        own = loc_json(c, pid, 'window_dli')
        own = own if isinstance(own, dict) else {}
        for k, v in new.items():
            if v in (None, ''): own.pop(k, None); continue
            try: v = float(v)
            except (TypeError, ValueError): abort(400, 'Window daylight must be a number')
            if not 0 <= v <= 70: abort(400, f'Daylight at a {WINDOW_FACING[k].lower()} window must be 0 to 70')
            own[k] = round(v, 1)
        c.execute('UPDATE locations SET window_dli=? WHERE id=?', (json.dumps({k: own[k] for k in WINDOW_DLI if k in own}) if own else '', pid))
    if 'season' in b:
        se = str(b.get('season') or 'temperate').strip()
        if se not in SEASONS: abort(400, 'Season must be one of: ' + ', '.join(SEASONS))
        c.execute('UPDATE locations SET season=? WHERE id=?', (se, pid))

@app.route('/api/places/<int:pid>', methods=['PUT', 'DELETE'])
def place_one(pid):
    c = db()
    L = loc_get(c, pid)
    if L is None: abort(404, 'That place does not exist')
    if request.method == 'DELETE':
        if L['is_home']: abort(400, 'This is the home place your plants use. Make another place home first.')
        if c.execute('SELECT COUNT(*) FROM plants WHERE home_id=?', (pid,)).fetchone()[0]: abort(409, 'Some plants are at this home. Move them to another home first.')
        if WX_JOB.get('running') and WX_JOB.get('place_id') == pid: abort(409, 'This place is being updated right now. Try again when it finishes.')
        n = c.execute("DELETE FROM readings WHERE source='weather' AND device=?", (L['device'],)).rowcount
        c.execute('DELETE FROM weather_daily WHERE loc_id=?', (pid,))
        c.execute('DELETE FROM weather_runs WHERE loc_id=?', (pid,))
        c.execute('DELETE FROM locations WHERE id=?', (pid,))
        audit_only(c, 'setting', 'weather_place', json.dumps({k: L[k] for k in ('name', 'lat', 'lon', 'tz')}), None, editor(), f'Weather place removed with {n} hourly readings: {L["name"]}')
        c.commit(); WX_STATS.pop(L['device'], None)
        return jsonify(ok=True, removed_readings=n)
    b = request.get_json(silent=True) or {}
    P = clean_place(b, L)
    moved = abs(P['lat'] - L['lat']) > 0.0001 or abs(P['lon'] - L['lon']) > 0.0001
    c.execute('UPDATE locations SET name=?,lat=?,lon=?,tz=? WHERE id=?', (P['name'], P['lat'], P['lon'], P['tz'], pid))
    if 'enabled' in b: c.execute('UPDATE locations SET enabled=? WHERE id=?', (1 if b['enabled'] else 0, pid))
    if b.get('is_home'):
        c.execute('UPDATE locations SET is_home=CASE WHEN id=? THEN 1 ELSE 0 END', (pid,))
    if 'plants_here' in b:                                  # 1.28.0: a home of its own (its plants follow its weather)
        if not b['plants_here'] and c.execute("SELECT COUNT(*) FROM plants WHERE home_id=? AND status='active'", (pid,)).fetchone()[0]:
            abort(409, 'Some plants are at this home. Move them to another home first.')
        c.execute('UPDATE locations SET plants_here=? WHERE id=?', (1 if b['plants_here'] else 0, pid))
    site_fields(c, pid, b)                                 # 1.48.0: country, units, season
    if 'detail_years' in b and b['detail_years'] not in (None, ''):
        try: dy = int(b['detail_years'])
        except (TypeError, ValueError): abort(400, 'Years of detail must be a whole number')
        if not 0 <= dy <= 90: abort(400, 'Years of detail must be between 0 and 90')
        set_setting(c, 'wx_detail_years', str(dy))
    audit_only(c, 'setting', 'weather_place', json.dumps({k: L[k] for k in ('name', 'lat', 'lon', 'tz', 'enabled', 'is_home')}),
               json.dumps({**P, 'enabled': b.get('enabled', L['enabled']), 'is_home': bool(b.get('is_home')) or L['is_home']}), editor(), f'Weather place changed: {P["name"]}')
    c.commit()
    return jsonify(place=loc_get(c, pid), moved=moved)

@app.route('/api/places/search')
def place_search():
    """Find a town by name with Open-Meteo's free place search (no account needed)."""
    q = (request.args.get('q') or '').strip()
    if len(q) < 2: abort(400, 'Type at least 2 letters')
    url = 'https://geocoding-api.open-meteo.com/v1/search?' + urllib.parse.urlencode({'name': q, 'count': 10, 'language': 'en', 'format': 'json'})
    try: data = http_json(url, tries=1)
    except Exception as e:
        abort(502, f'The place search could not be reached ({type(e).__name__}). You can still type the latitude, longitude and time zone yourself.')
    out = []
    for r in data.get('results') or []:
        label = ', '.join(x for x in (r.get('name'), r.get('admin1'), r.get('country')) if x)
        out.append({'label': label, 'name': ', '.join(x for x in (r.get('name'), r.get('admin1_code') or r.get('admin1')) if x) if r.get('country_code') == 'US' else ', '.join(x for x in (r.get('name'), r.get('country')) if x),
                    'lat': r.get('latitude'), 'lon': r.get('longitude'), 'tz': r.get('timezone'), 'elevation_m': r.get('elevation'), 'population': r.get('population'),
                    'country': r.get('country_code') or ''})     # 1.48.0: kept on the place
    return jsonify(out)

@app.route('/api/weather/settings', methods=['PUT'])
def weather_settings():
    """Older form of PUT /api/places/<id> for the home place (or ?loc=)."""
    c = db()
    L = req_loc(c)
    return place_one(L['id'])
