"""1.35.0: your sensors at a glance. Each sensor (a `device` name in readings) can get a name you recognise, the spot it sits
at, the plant whose pot it is in, and how long it may stay quiet before the app says so. Its newest values are compared with
that plant's ranges, in words with a mark (never colour alone). A sensor in a pot can log a watering when the soil moisture
jumps; sensor alerts (dry, too cold, gone quiet) go out as notifications once a day each. Grown from the proto/sensor-dashboard
prototype (October 2026)."""
from .core import *   # noqa: F401,F403

SENSOR_METRICS = (   # key, label, unit, plant fields for low / high
    ('soil_moisture', 'Soil moisture', '%', 'soil_moisture_low', 'soil_moisture_high'),
    ('temp_f', 'Air temperature', '°F', 'temp_ideal_low', 'temp_ideal_high'),
    ('humidity', 'Humidity', '%', 'humidity_low', 'humidity_high'),
    ('par', 'Light now', ' PAR', None, None),
    ('soil_temp_f', 'Root-zone temperature', '°F', 'soil_temp_low', 'soil_temp_high'),
    ('soil_ph', 'Soil pH', '', 'soil_ph_low', 'soil_ph_high'),
    ('weight_g', 'Pot weight', ' g', None, None),
)
SENSOR_WORDS = {   # key -> (word when low, word when high)
    'soil_moisture': ('Dry', 'Wet'), 'temp_f': ('Cool', 'Warm'), 'humidity': ('Dry air', 'Humid'),
    'soil_temp_f': ('Cold roots', 'Warm roots'), 'soil_ph': ('Too acid', 'Too alkaline'), 'dli': ('Too dim', 'Too bright')}
SENSOR_QUIET_DEFAULT = 3
SENSOR_WATER_JUMP = 15          # soil moisture points up within SENSOR_WATER_HOURS: the pot was watered
SENSOR_WATER_HOURS = 3
SENSOR_SCHEMA = """
CREATE TABLE IF NOT EXISTS sensor_devices(device TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '',
  plant_id INTEGER REFERENCES plants(id) ON DELETE SET NULL, spot_id INTEGER, area_id INTEGER, quiet_hours INTEGER NOT NULL DEFAULT 3,
  auto_water INTEGER NOT NULL DEFAULT 1, cal_dry REAL, cal_wet REAL, updated_by TEXT, updated_at TEXT);
"""

def sensor_judge(key, v, lo, hi, p=None):
    """In words: how a value compares with the plant's range. level is ok / low / high / bad (bad = in the damage range)."""
    if v is None: return None
    unit = next((m[2] for m in SENSOR_METRICS if m[0] == key), ' mol/m²' if key == 'dli' else '')
    fmt = lambda x: (f'{x:g}' if isinstance(x, (int, float)) else str(x)) + unit
    if key == 'temp_f' and p is not None and p['temp_damage_below'] is not None and v < p['temp_damage_below']:
        return {'level': 'bad', 'word': 'Too cold', 'text': f"Below {fmt(p['temp_damage_below'])}, where damage starts. Move it somewhere warmer."}
    if lo is None and hi is None: return None
    lw, hw = SENSOR_WORDS.get(key, ('Low', 'High'))
    rng = f'{fmt(lo)} to {fmt(hi)}' if lo is not None and hi is not None else (f'at least {fmt(lo)}' if lo is not None else f'at most {fmt(hi)}')
    if lo is not None and v < lo:
        return {'level': 'low', 'word': lw, 'text': f'Below its range ({rng}).' + (' Time to check it and water.' if key == 'soil_moisture' else '')}
    if hi is not None and v > hi:
        return {'level': 'high', 'word': hw, 'text': f'Above its range ({rng}).' + (' Let it dry out before watering again.' if key == 'soil_moisture' else '')}
    return {'level': 'ok', 'word': 'In range', 'text': f'Within its range ({rng}).'}

def sensor_place(c, conf):
    """Where a sensor sits: {spot, area, home} names, from its spot or area."""
    if not conf: return None
    if conf['spot_id']:
        r = c.execute('SELECT s.id sid, s.name spot, a.id aid, a.name area, a.home_id FROM spots s JOIN areas a ON a.id=s.area_id WHERE s.id=?', (conf['spot_id'],)).fetchone()
        if r: return {'spot_id': r['sid'], 'spot': r['spot'], 'area_id': r['aid'], 'area': r['area'], 'text': f"{r['spot']}, {r['area']}"}
    if conf['area_id']:
        r = c.execute('SELECT id, name FROM areas WHERE id=?', (conf['area_id'],)).fetchone()
        if r: return {'spot_id': None, 'spot': '', 'area_id': r['id'], 'area': r['name'], 'text': r['name']}
    return None

def sensor_spark(c, dev, key, since, bins=48):
    """Up to `bins` averages since `since`, oldest first (the little chart on the card)."""
    rows = c.execute(f"SELECT ts, {key} FROM readings WHERE source='sensor' AND device=? AND {key} IS NOT NULL AND ts>=? ORDER BY ts", (dev, since)).fetchall()
    if not rows: return []
    t0, t1 = parse_ts(rows[0][0]).timestamp(), parse_ts(rows[-1][0]).timestamp()
    span = max(t1 - t0, 1)
    sums = [[0.0, 0] for _ in range(bins)]
    for ts, v in rows:
        i = min(bins - 1, int((parse_ts(ts).timestamp() - t0) / span * bins))
        sums[i][0] += v; sums[i][1] += 1
    return [round(s / n, 1) if n else None for s, n in sums]

def sensor_card(c, dev, conf, now_t, full=True):
    sw = "source='sensor' AND device=?"
    st = c.execute(f'SELECT COUNT(*), MIN(ts), MAX(ts) FROM readings WHERE {sw}', (dev,)).fetchone()
    name = (conf['name'] if conf else '') or dev
    quiet_h = conf['quiet_hours'] if conf and conf['quiet_hours'] else SENSOR_QUIET_DEFAULT
    p = c.execute('SELECT * FROM plants WHERE id=?', (conf['plant_id'],)).fetchone() if conf and conf['plant_id'] else None
    last = st[2]
    mins = round((now_t - parse_ts(last).timestamp()) / 60) if last else None
    day_ago = iso(now_t - 86400)
    metrics = []
    for key, label, unit, flo, fhi in SENSOR_METRICS:
        r = c.execute(f'SELECT {key}, ts FROM readings WHERE {sw} AND {key} IS NOT NULL ORDER BY ts DESC LIMIT 1', (dev,)).fetchone()
        if not r: continue
        a = c.execute(f'SELECT MIN({key}), MAX({key}), COUNT({key}) FROM readings WHERE {sw} AND ts>=?', (dev, day_ago)).fetchone()
        m = {'key': key, 'label': label, 'unit': unit, 'value': r[0], 'ts': r[1],
             'day_min': a[0], 'day_max': a[1], 'day_n': a[2], 'judge': None, 'range': None, 'change': None,
             'spark': sensor_spark(c, dev, key, day_ago) if full else []}
        if p is not None and flo:
            lo, hi = p[flo], p[fhi]
            m['range'] = [lo, hi] if lo is not None or hi is not None else None
            m['judge'] = sensor_judge(key, r[0], lo, hi, p)
        if key in ('soil_moisture', 'weight_g'):      # how much it changed in about a day (the reading closest to 24 hours before the newest)
            t0 = parse_ts(r[1]).timestamp()
            b = c.execute(f"""SELECT {key}, ts FROM readings WHERE {sw} AND {key} IS NOT NULL AND ts BETWEEN ? AND ?
                              ORDER BY ABS(strftime('%s', ts) - ?) LIMIT 1""", (dev, iso(t0 - 30 * 3600), iso(t0 - 18 * 3600), int(t0 - 86400))).fetchone()
            if b: m['change'] = {'by': round(r[0] - b[0], 1), 'hours': round((t0 - parse_ts(b[1]).timestamp()) / 3600)}
        metrics.append(m)
    # daily light over the last 24 hours from the hourly averages of PAR, when most hours have a reading
    hrs = c.execute(f'SELECT substr(ts,1,13), AVG(par) FROM readings WHERE {sw} AND par IS NOT NULL AND ts>=? GROUP BY 1', (dev, day_ago)).fetchall()
    dli = None
    if len(hrs) >= 18:
        v = round(sum(h[1] for h in hrs) / len(hrs) * 0.0864, 1)
        dli = {'value': v, 'hours': len(hrs), 'judge': sensor_judge('dli', v, p['dli_low'], p['dli_high']) if p is not None else None,
               'range': [p['dli_low'], p['dli_high']] if p is not None and (p['dli_low'] is not None or p['dli_high'] is not None) else None}
    alerts = [m for m in metrics if m['judge'] and m['judge']['level'] != 'ok'] + ([dli] if dli and dli['judge'] and dli['judge']['level'] != 'ok' else [])
    quiet = mins is None or mins > quiet_h * 60
    return {'device': dev, 'name': name, 'named': bool(conf and conf['name']), 'count': st[0], 'first': st[1], 'last': last, 'minutes_ago': mins,
            'quiet_hours': quiet_h, 'quiet': quiet, 'auto_water': bool(conf['auto_water']) if conf else True,
            'plant': {'code': p['code'], 'common_name': p['common_name'], 'site': p['site'], 'status': p['status']} if p is not None else None,
            'place': sensor_place(c, conf), 'metrics': metrics, 'dli': dli, 'needs_look': bool(alerts),
            'raw': bool(c.execute(f'SELECT 1 FROM readings WHERE {sw} AND soil_raw IS NOT NULL LIMIT 1', (dev,)).fetchone()), 'calibrated': bool(conf and conf['cal_dry'] is not None and conf['cal_wet'] is not None),
            'words': ('Quiet: last heard ' + ago_words(mins) + '. Check its battery, power or Wi-Fi.') if quiet and mins is not None else 'Quiet: nothing received yet.' if quiet else
                     ('Needs a look: ' + ', '.join((x['judge']['word'].lower() + ' ' + (x.get('label') or 'daily light').lower()) for x in alerts) + '.') if alerts else 'All in range.' if p is not None else 'Sending.'}

def ago_words(mins):
    if mins is None: return 'never'
    if mins < 60: return f'{mins} minute{"s" if mins != 1 else ""} ago'
    h = round(mins / 60)
    if h < 48: return f'{h} hour{"s" if h != 1 else ""} ago'
    return f'{round(h / 24)} days ago'

def sensor_confs(c):
    return {r['device']: r for r in c.execute('SELECT * FROM sensor_devices').fetchall()}

def sensor_devices(c, conf):
    devs = [r[0] for r in c.execute("SELECT device FROM readings WHERE source='sensor' GROUP BY device ORDER BY MAX(ts) DESC").fetchall()]
    return devs + [d for d in conf if d not in devs]

def sensors_summary(c):
    """For Today and the Weather page: how many sensors, how many need a look, how many are quiet."""
    conf = sensor_confs(c); devs = sensor_devices(c, conf)
    if not devs: return {'n': 0, 'look': 0, 'quiet': 0, 'cards': []}
    t = time.time()
    cards = [sensor_card(c, d, conf.get(d), t, full=False) for d in devs]
    return {'n': len(cards), 'look': sum(1 for s in cards if s['needs_look']), 'quiet': sum(1 for s in cards if s['quiet']),
            'cards': [{'device': s['device'], 'name': s['name'], 'words': s['words'], 'needs_look': s['needs_look'], 'quiet': s['quiet'], 'plant': s['plant']} for s in cards if s['needs_look'] or s['quiet']]}

@app.route('/api/sensors/summary')
def sensors_summary_api():
    """For Today: how many sensors need a look or have gone quiet, and which."""
    return jsonify(sensors_summary(db()))

@app.route('/api/sensors')
def sensors_list():
    """Every sensor that has sent a reading or been set up, the ones that need a look first. ?plant=CODE: only the ones in that plant;
    ?spot=ID: at that spot."""
    c = db()
    conf = sensor_confs(c); devs = sensor_devices(c, conf)
    code, spot = request.args.get('plant'), request.args.get('spot')
    if code:
        pid = plant_row(c, code)['id']
        devs = [d for d in devs if d in conf and conf[d]['plant_id'] == pid]
    if spot:
        devs = [d for d in devs if d in conf and str(conf[d]['spot_id']) == str(spot)]
    t = time.time()
    cards = [sensor_card(c, d, conf.get(d), t) for d in devs]
    cards.sort(key=lambda s: (not s['needs_look'], s['quiet'], s['name'].lower()))
    return jsonify(sensors=cards, quiet_default=SENSOR_QUIET_DEFAULT, metrics=[{'key': k, 'label': l, 'unit': u} for k, l, u, _, _ in SENSOR_METRICS])

@app.route('/api/sensors/<path:device>', methods=['PUT'])
def sensor_save(device):
    """Name a sensor, say where it is (spot or area id, '' for none), which plant it is in ('' for none), how many hours it may
    stay quiet, and whether a jump in soil moisture logs a watering."""
    c = db()
    dev = re.sub(r'[^\w .\-@]', '', device)[:40]
    if not dev: abort(400, 'unknown sensor')
    known = c.execute("SELECT 1 FROM readings WHERE source='sensor' AND device=? LIMIT 1", (dev,)).fetchone()
    old = c.execute('SELECT * FROM sensor_devices WHERE device=?', (dev,)).fetchone()
    if not known and not old: abort(404, 'no sensor by that name has sent a reading')
    b = request.get_json(silent=True) or {}
    name = re.sub(r'\s+', ' ', str(b.get('name') or '')).strip()[:60]
    pid, pcode = None, ''
    if b.get('plant'):
        pr = plant_row(c, str(b['plant'])); pid, pcode = pr['id'], pr['code']
    spot_id = area_id = None
    if b.get('spot'):
        sp = c.execute('SELECT id, area_id FROM spots WHERE id=?', (b['spot'],)).fetchone()
        if not sp: abort(400, 'No such spot')
        spot_id, area_id = sp['id'], sp['area_id']
    elif b.get('area'):
        if not c.execute('SELECT 1 FROM areas WHERE id=?', (b['area'],)).fetchone(): abort(400, 'No such room or area')
        area_id = int(b['area'])
    try: qh = int(b.get('quiet_hours') or SENSOR_QUIET_DEFAULT)
    except (TypeError, ValueError): abort(400, 'quiet hours must be a whole number')
    if not 1 <= qh <= 168: abort(400, 'quiet hours must be between 1 and 168')
    aw = 1 if b.get('auto_water', True) else 0
    c.execute("""INSERT INTO sensor_devices(device,name,plant_id,spot_id,area_id,quiet_hours,auto_water,updated_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(device) DO UPDATE SET name=excluded.name, plant_id=excluded.plant_id, spot_id=excluded.spot_id, area_id=excluded.area_id,
                 quiet_hours=excluded.quiet_hours, auto_water=excluded.auto_water, updated_by=excluded.updated_by, updated_at=excluded.updated_at""",
              (dev, name, pid, spot_id, area_id, qh, aw, editor(), now()))
    oldcode = ''
    if old and old['plant_id']:
        r = c.execute('SELECT code FROM plants WHERE id=?', (old['plant_id'],)).fetchone(); oldcode = r[0] if r else ''
    was = f"{old['name'] or dev}, in {oldcode or 'no plant'}, quiet after {old['quiet_hours']} h" if old else ''
    audit_only(c, 'setting', 'sensor:' + dev, was or None, f"{name or dev}, in {pcode or 'no plant'}, quiet after {qh} h", editor(),
               f'Sensor "{dev}" set up', pid, pcode or None)
    c.commit()
    return jsonify(ok=True)

@app.route('/api/sensors/<path:device>/calibrate', methods=['GET', 'POST'])
def sensor_calibrate(device):
    """1.36.0: calibrate a soil probe in the app. GET: the newest raw volts and the two numbers saved. POST {step: 'dry' | 'wet' | 'clear'}:
    takes the newest raw reading (under 20 minutes old) as dry air or water; 'clear' forgets both."""
    c = db()
    dev = re.sub(r'[^\w .\-@]', '', device)[:40]
    cf = c.execute('SELECT * FROM sensor_devices WHERE device=?', (dev,)).fetchone()
    raw = c.execute("SELECT soil_raw, ts FROM readings WHERE source='sensor' AND device=? AND soil_raw IS NOT NULL ORDER BY ts DESC LIMIT 1", (dev,)).fetchone()
    if not cf and not raw: abort(404, 'no sensor by that name has sent a reading')
    if request.method == 'POST':
        step = (request.get_json(silent=True) or {}).get('step')
        if step not in ('dry', 'wet', 'clear'): abort(400, 'step must be dry, wet or clear')
        if step != 'clear':
            if not raw: abort(400, 'This sensor has not sent its raw probe volts (soil_raw) yet.')
            if time.time() - parse_ts(raw['ts']).timestamp() > 20 * 60: abort(400, f'The newest raw reading is from {ago_words(round((time.time() - parse_ts(raw["ts"]).timestamp()) / 60))}; wait for a fresh one.')
        if not cf:
            c.execute('INSERT INTO sensor_devices(device,name,quiet_hours,updated_by,updated_at) VALUES(?,?,?,?,?)', (dev, '', SENSOR_QUIET_DEFAULT, editor(), now()))
        if step == 'clear': c.execute('UPDATE sensor_devices SET cal_dry=NULL, cal_wet=NULL, updated_by=?, updated_at=? WHERE device=?', (editor(), now(), dev))
        else: c.execute(f"UPDATE sensor_devices SET cal_{step}=?, updated_by=?, updated_at=? WHERE device=?", (raw['soil_raw'], editor(), now(), dev))
        cf = c.execute('SELECT * FROM sensor_devices WHERE device=?', (dev,)).fetchone()
        if cf['cal_dry'] is not None and cf['cal_wet'] is not None: sensor_apply_cal(c, dev, cf)
        audit_only(c, 'setting', 'sensor:' + dev, None, f"dry {cf['cal_dry']}, wet {cf['cal_wet']}", editor(), f'Soil probe "{cf["name"] or dev}" calibrated: ' + ('cleared' if step == 'clear' else step))
        c.commit()
    return jsonify(device=dev, raw=raw['soil_raw'] if raw else None, raw_at=raw['ts'] if raw else None, raw_minutes=round((time.time() - parse_ts(raw['ts']).timestamp()) / 60) if raw else None,
                   cal_dry=cf['cal_dry'] if cf else None, cal_wet=cf['cal_wet'] if cf else None,
                   done=bool(cf and cf['cal_dry'] is not None and cf['cal_wet'] is not None))

@app.route('/api/sensors/<path:device>', methods=['DELETE'])
def sensor_forget(device):
    """Owner: forget a sensor's set-up and its readings (for a probe that was retired or renamed)."""
    c = db()
    dev = re.sub(r'[^\w .\-@]', '', device)[:40]
    n = c.execute("DELETE FROM readings WHERE source='sensor' AND device=?", (dev,)).rowcount
    c.execute('DELETE FROM sensor_devices WHERE device=?', (dev,))
    audit_only(c, 'setting', 'sensor:' + dev, None, None, editor(), f'Sensor "{dev}" forgotten ({n} readings removed)')
    c.commit()
    return jsonify(ok=True, removed=n)

# ---- the watering tie-in: a jump in soil moisture means the pot was watered
def sensor_apply_cal(c, dev, cf, since=None):
    """1.36.0: a probe calibrated in the app: its raw volts become soil moisture (dry air = 0 %, water = 100 %)."""
    if not cf or cf['cal_dry'] is None or cf['cal_wet'] is None or cf['cal_dry'] == cf['cal_wet']: return
    dry, wet = cf['cal_dry'], cf['cal_wet']
    c.execute("""UPDATE readings SET soil_moisture = MAX(0, MIN(100, ROUND((? - soil_raw) / (? - ?) * 100, 1)))
                 WHERE source='sensor' AND device=? AND soil_raw IS NOT NULL""" + (' AND ts>=?' if since else ''), (dry, dry, wet, dev) + ((since,) if since else ()))

def sensor_after_readings(c, rows):
    """Called after readings arrive. A calibrated probe's raw volts become soil moisture first. Then, for a sensor in a
    plant's pot with auto_water on: when the soil moisture rose by SENSOR_WATER_JUMP points or more within
    SENSOR_WATER_HOURS, log a watering for today (once a day, like the button)."""
    conf = sensor_confs(c)
    for dev in {r['device'] for r in rows if r.get('soil_raw') is not None}:
        sensor_apply_cal(c, dev, conf.get(dev), min(r['ts'] for r in rows if r['device'] == dev))
    devs = {r['device'] for r in rows if r.get('soil_moisture') is not None or r.get('soil_raw') is not None}
    if not devs: return
    for dev in devs:
        cf = conf.get(dev)
        if not cf or not cf['plant_id'] or not cf['auto_water']: continue
        p = c.execute('SELECT code FROM plants WHERE id=?', (cf['plant_id'],)).fetchone()
        if not p: continue
        latest = c.execute("SELECT soil_moisture, ts FROM readings WHERE source='sensor' AND device=? AND soil_moisture IS NOT NULL ORDER BY ts DESC LIMIT 1", (dev,)).fetchone()
        if not latest: continue
        t1 = parse_ts(latest['ts']).timestamp()
        low = c.execute("SELECT MIN(soil_moisture) FROM readings WHERE source='sensor' AND device=? AND soil_moisture IS NOT NULL AND ts>=? AND ts<?",
                        (dev, iso(t1 - SENSOR_WATER_HOURS * 3600), latest['ts'])).fetchone()[0]
        if low is None or latest['soil_moisture'] - low < SENSOR_WATER_JUMP: continue
        day = local_today(c).isoformat()
        if c.execute("SELECT 1 FROM care_log WHERE plant_code=? AND kind='water' AND done_on=?", (p['code'], day)).fetchone(): continue
        note = f"Seen by the sensor {cf['name'] or dev}: soil moisture up {round(latest['soil_moisture'] - low)} points."
        c.execute('INSERT INTO care_log(plant_code,kind,done_on,note,created_by,created_at) VALUES(?,?,?,?,?,?)', (p['code'], 'water', day, note, 'Sensor', now()))
        audit_only(c, 'care', 'care_log', None, f'Watered {day}: {note}', 'Sensor', 'Watered (seen by the sensor)', cf['plant_id'], p['code'])

# ---- notifications: once a day per sensor and kind
def push_sensors(c):
    """Dry pots, dangerous cold at a sensor, and sensors gone quiet: one message a day each, to everyone who wants sensor alerts."""
    conf = sensor_confs(c); devs = sensor_devices(c, conf)
    if not devs: return
    t = time.time(); today = local_today(c).isoformat()
    for d in devs:
        s = sensor_card(c, d, conf.get(d), t, full=False)
        if s['quiet'] and s['last'] and push_once(c, f'sensor:{d}:quiet:{today}'):
            push_send(c, 'sensors', f'{s["name"]} has gone quiet', f'Nothing since {ago_words(s["minutes_ago"])}. Check its battery, power or Wi-Fi.', '#/sensors', tag='sensor-' + d)
        for m in s['metrics']:
            j = m['judge']
            if not j or j['level'] == 'ok': continue
            if m['key'] == 'soil_moisture' and j['level'] == 'low' and push_once(c, f'sensor:{d}:dry:{today}'):
                push_send(c, 'sensors', f'{s["plant"]["common_name"]} is dry', f'{s["name"]}: soil moisture {m["value"]:g}%. {j["text"]}', '#/sensors', tag='sensor-' + d)
            if j['level'] == 'bad' and push_once(c, f'sensor:{d}:cold:{today}'):
                push_send(c, 'sensors', f'Too cold at {s["name"]}', f'{m["value"]:g}°F. {j["text"]}', '#/sensors', tag='sensor-' + d)
