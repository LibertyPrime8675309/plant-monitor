"""Past days on a plant's page: what the readings were, and what the plant's ranges were then (/api/plants/<code>/daily and /day).
Split out of weather.py in 1.57.0 (review item 25)."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- past days: what the values were, and what the ranges were then
HIST = {  # metric -> (column, low field, high field, unit, label)
    'temp': ('temp_f', 'temp_ideal_low', 'temp_ideal_high', '°F', 'Temperature'),
    'humidity': ('humidity', 'humidity_low', 'humidity_high', '%', 'Humidity'),
    'vpd': (None, 'vpd_low', 'vpd_high', ' kPa', 'Air dryness (VPD)'),
    'light': ('par', 'par_low', 'par_high', ' PAR', 'Light'),
    'soil_moisture': ('soil_moisture', 'soil_moisture_low', 'soil_moisture_high', '%', 'Soil moisture'),
    'soil_temp': ('soil_temp_f', 'soil_temp_low', 'soil_temp_high', '°F', 'Soil temperature'),
    'soil_ph': ('soil_ph', 'soil_ph_low', 'soil_ph_high', '', 'Soil pH'),
}
SOURCE_ORDER = ['sensor', 'manual', 'weather']
SOURCE_NAME = {'sensor': 'Your sensor', 'manual': 'Typed in by you', 'weather': 'Online weather (outdoors)'}

def versions_of(c, pid):
    out = []
    for v in c.execute('SELECT version,changed_at,snapshot FROM plant_versions WHERE plant_id=? ORDER BY version', (pid,)):
        try: out.append((parse_ts(v['changed_at']), v['version'], json.loads(v['snapshot'])['fields']))
        except (ValueError, KeyError): pass
    return out

def fields_at(vers, cur, when_utc):
    """Plant fields in effect at a moment: the newest saved version at or before it (the oldest one if the moment is earlier)."""
    pick = None
    for t, n, f in vers:
        if t <= when_utc: pick = (n, f)
    if pick is None and vers: pick = (vers[0][1], vers[0][2])
    return pick if pick else (None, cur)

def hourly(rows, col, tz):
    """{(local date, hour): mean} for one column"""
    acc = {}
    for r in rows:
        v = r[col] if col else None
        if v is None: continue
        d = parse_ts(r['ts']).astimezone(tz)
        acc.setdefault((d.date().isoformat(), d.hour), []).append(v)
    return {k: sum(v) / len(v) for k, v in acc.items()}

def grade_day(metric, hrs, lo, hi, f):
    """ok: every hour in range. near: some hours out, or the average is a little outside. bad: the average is well outside. danger: past the damage point."""
    if not hrs: return 'none'
    vals = list(hrs)
    if lo is None and hi is None: return 'info'
    if metric == 'temp':
        db_, da = f.get('temp_damage_below'), f.get('temp_damage_above')
        if (db_ is not None and min(vals) < db_) or (da is not None and max(vals) > da): return 'danger'
    out = [v for v in vals if (lo is not None and v < lo) or (hi is not None and v > hi)]
    if not out: return 'ok'
    avg = sum(vals) / len(vals)
    width = (hi - lo) if lo is not None and hi is not None else max(1.0, abs(lo if lo is not None else hi) * 0.4)
    dev = max((lo - avg) if lo is not None else 0, (avg - hi) if hi is not None else 0)
    return 'bad' if dev > 0.25 * width else 'near'

def grade_light(hrs_all, f):
    """Daily light from the hourly means: DLI when most of the day has readings, otherwise daytime average PAR.
    Returns (status, dli, kind judged on, low, high)."""
    vals = list(hrs_all.values())
    if not vals: return 'none', None, None, None, None
    dli = round(sum(vals) * 3600 / 1e6, 1) if len(vals) >= 18 else None
    day = [v for v in vals if v >= 20]
    use_dli = dli is not None and (f.get('dli_low') is not None or f.get('dli_high') is not None)
    lo, hi, kind = (f.get('dli_low'), f.get('dli_high'), 'dli') if use_dli else (f.get('par_low'), f.get('par_high'), 'par')
    x = dli if kind == 'dli' else (round(sum(day) / len(day), 1) if len(day) >= 3 else None)
    if x is None: return 'none', dli, kind, lo, hi
    if lo is None and hi is None: return 'info', dli, kind, lo, hi
    if lo is not None and x < lo: return ('bad' if x < lo * 0.5 else 'near'), dli, kind, lo, hi
    if hi is not None and x > hi: return ('bad' if x > hi * 1.3 else 'near'), dli, kind, lo, hi
    return 'ok', dli, kind, lo, hi

def month_bounds(c, month, tz):
    try: y, m = (int(x) for x in month.split('-')); first = datetime(y, m, 1).date()
    except (ValueError, AttributeError): abort(400, 'month must look like 2026-10')
    last = (datetime(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).date()
    return first, last

@app.route('/api/plants/<code>/daily')
def plant_daily(code):
    """One entry per day of a month: how that day's readings compared with the plant's range as recorded at the time."""
    c = db()
    r = plant_row(c, code)
    metric = request.args.get('metric', 'temp')
    if metric not in HIST: abort(400, 'unknown metric')
    want = request.args.get('source', 'auto')
    col, lof, hif, unit, label = HIST[metric]
    loc = location(c); tz = tzinfo(loc['tz'])
    first, last = month_bounds(c, request.args.get('month', local_today(c).strftime('%Y-%m')), tz)
    a = datetime(first.year, first.month, first.day, tzinfo=tz).astimezone(timezone.utc) - timedelta(hours=1)
    z = datetime(last.year, last.month, last.day, tzinfo=tz).astimezone(timezone.utc) + timedelta(days=1, hours=1)
    rows = c.execute("SELECT ts,source,temp_f,humidity,par,soil_moisture,soil_temp_f,soil_ph FROM readings WHERE ts>=? AND ts<=? AND (source!='weather' OR device=?) ORDER BY ts",
                     (iso(a.timestamp()), iso(z.timestamp()), loc['device'])).fetchall()
    by_src = {s: [x for x in rows if x['source'] == s] for s in SOURCE_ORDER}
    hours = {}
    for s, rs in by_src.items():
        if metric == 'vpd':
            h = {}
            t, rh = hourly(rs, 'temp_f', tz), hourly(rs, 'humidity', tz)
            for k in t:
                if k in rh:
                    v = vpd_kpa(t[k], rh[k])
                    if v is not None: h[k] = v
            hours[s] = h
        else:
            hours[s] = hourly(rs, col, tz)
    vers = versions_of(c, r['id']); cur = {n: r[n] for n in FIELD_NAMES}
    fert = {}
    for f_ in c.execute('SELECT applied_on,product FROM fertilizer_log WHERE plant_code=? AND applied_on>=? AND applied_on<=?', (code, first.isoformat(), last.isoformat())):
        fert.setdefault(f_['applied_on'], []).append(f_['product'])
    days, d = [], first
    while d <= last:
        ds = d.isoformat()
        src = None
        for s in ([want] if want in SOURCE_ORDER else SOURCE_ORDER):
            if any(k[0] == ds for k in hours[s]): src = s; break
        end = datetime(d.year, d.month, d.day, 23, 59, tzinfo=tz).astimezone(timezone.utc)
        ver, f = fields_at(vers, cur, end)
        lo, hi = f.get(lof), f.get(hif)
        fallback = False
        if lo is None and hi is None and (cur.get(lof) is not None or cur.get(hif) is not None):
            lo, hi, fallback = cur.get(lof), cur.get(hif), True
        day = {'date': ds, 'source': src, 'lo': lo, 'hi': hi, 'version': ver, 'range_from_now': fallback, 'status': 'none', 'fed': fert.get(ds, [])}
        if src:
            hh = {k: v for k, v in hours[src].items() if k[0] == ds}
            vals = list(hh.values())
            day.update(n=len(vals), min=round(min(vals), 1), max=round(max(vals), 1), avg=round(sum(vals) / len(vals), 1))
            if metric == 'light':
                day['status'], dli, kind, jl, jh = grade_light(hh, f if not fallback else {**f, lof: lo, hif: hi})
                day['dli'] = dli; day['judged_on'] = kind; day['lo'], day['hi'] = jl, jh
                day['daytime_avg'] = round(sum(v for v in vals if v >= 20) / max(1, sum(1 for v in vals if v >= 20)), 1) if any(v >= 20 for v in vals) else None
            else:
                day['status'] = grade_day(metric, vals, lo, hi, f)
                day['hours_in'] = sum(1 for v in vals if (lo is None or v >= lo) and (hi is None or v <= hi))
        days.append(day)
        d += timedelta(days=1)
    return jsonify(metric=metric, label=label, unit=unit, month=first.strftime('%Y-%m'), tz=loc['tz'], days=days,
                   sources={s: SOURCE_NAME[s] for s in SOURCE_ORDER}, today=local_today(c).isoformat())

@app.route('/api/plants/<code>/day')
def plant_day(code):
    """Everything known about one local day: readings in 15-minute steps from each source, the plant's ranges then, and feedings."""
    c = db()
    r = plant_row(c, code)
    loc = location(c); tz = tzinfo(loc['tz'])
    ds = request.args.get('date') or local_today(c).isoformat()
    try: d = datetime.strptime(ds, '%Y-%m-%d').date()
    except ValueError: abort(400, 'date must look like 2026-10-20')
    a = datetime(d.year, d.month, d.day, tzinfo=tz).astimezone(timezone.utc)
    z = a + timedelta(days=1)
    rows = c.execute("SELECT * FROM readings WHERE ts>=? AND ts<? AND (source!='weather' OR device=?) ORDER BY ts", (iso(a.timestamp()), iso(z.timestamp()), loc['device'])).fetchall()
    out = {}
    for s in SOURCE_ORDER:
        bins = {}
        for x in rows:
            if x['source'] != s: continue
            t = parse_ts(x['ts']); k = int(t.timestamp() // 900)
            bins.setdefault(k, []).append(x)
        pts = []
        for k in sorted(bins):
            g = bins[k]; p = {'t': iso(k * 900)}
            for m in ('temp_f', 'humidity', 'par', 'soil_moisture', 'soil_temp_f', 'soil_ph'):
                v = [q[m] for q in g if q[m] is not None]
                p[m] = round(sum(v) / len(v), 2) if v else None
            p['vpd'] = vpd_kpa(p['temp_f'], p['humidity']) if p['temp_f'] is not None and p['humidity'] is not None else None
            pts.append(p)
        if pts: out[s] = pts
    ver, f = fields_at(versions_of(c, r['id']), {n: r[n] for n in FIELD_NAMES}, a + timedelta(days=1) - timedelta(minutes=1))
    fert = [dict(x) for x in c.execute('SELECT * FROM fertilizer_log WHERE plant_code=? AND applied_on=? ORDER BY id', (code, ds))]
    last = c.execute('SELECT applied_on FROM fertilizer_log WHERE plant_code=? AND applied_on<=? ORDER BY applied_on DESC LIMIT 1', (code, ds)).fetchone()
    return jsonify(date=ds, tz=loc['tz'], version=ver, current_version=r['version'], ranges={n: f.get(n) for n in FIELD_NAMES if n.split('_')[0] in ('temp', 'humidity', 'vpd', 'par', 'dli', 'soil', 'fert')},
                   sources=out, source_names=SOURCE_NAME, fertilized=fert, last_fed=last[0] if last else None)
