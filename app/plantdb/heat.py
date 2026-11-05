"""1.34.0: summer heat where the plants are, from the place's own weather history. The American Horticultural Society (AHS)
heat zone of a place is the number of days a year whose high is above 86°F (30°C), the point where many plants start to
suffer: zone 1 has less than one such day a year, zone 12 more than 210. It is the summer counterpart of the USDA hardiness
zone (winter cold), and sits next to it on the Weather page and on plant pages."""
from .core import *   # noqa: F401,F403

AHS_HEAT_ZONES = [(1, 1), (2, 8), (3, 15), (4, 31), (5, 46), (6, 61), (7, 91), (8, 121), (9, 151), (10, 181), (11, 211)]   # (zone, days below which it applies)
HEAT_LINE_F = 86
PLACE_HEAT = {}

def ahs_heat_zone(days):
    """AHS heat zone (1 to 12) for an average number of days a year above 86°F."""
    if days is None: return None
    for z, below in AHS_HEAT_ZONES:
        if days < below: return z
    return 12

def place_highs(c, L):
    """Each observed day's high at a place, as {year: [(month, high), ...]}. Worked out at most every 6 hours."""
    hit = PLACE_HEAT.get(L['id'])
    if hit and time.time() - hit[0] < 6 * 3600: return hit[1]
    try: rows = c.execute("SELECT date, json_extract(data, '$.temperature_2m_max') FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],)).fetchall()
    except sqlite3.OperationalError:            # an SQLite without JSON functions
        rows = [(d, (json.loads(x) if x else {}).get('temperature_2m_max')) for d, x in c.execute("SELECT date, data FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],))]
    years = {}
    for d, t in rows:
        if isinstance(t, (int, float)): years.setdefault(int(d[:4]), []).append((int(d[5:7]), t))
    PLACE_HEAT[L['id']] = (time.time(), years)
    return years

def heat_level(reach):
    """How hard a usual summer is on a plant, from the days a year that reach its heat-damage temperature:
    'fine' (under half a day), 'few' (under 10 days) or 'hard'."""
    if reach is None: return None
    return 'fine' if reach < 0.5 else 'few' if reach < 10 else 'hard'

def heat_zone_fit(zone, hi, lo):
    """Where the place's heat zone sits against a plant's AHS range: 'hotter' (above its hottest zone), 'cooler' or 'within'."""
    if zone is None or hi is None or lo is None: return None
    hi, lo = max(hi, lo), min(hi, lo)
    return 'hotter' if zone > hi else 'cooler' if zone < lo else 'within'

def plants_heat(c, L):
    """1.36.0: each active plant's summer verdict at a place, for the Summer here filter and the Weather page."""
    years = place_highs(c, L)
    try: this_year = local_today(c).year
    except Exception: this_year = datetime.now(timezone.utc).year
    whole = [y for y, v in years.items() if len(v) >= 330 and y < this_year]
    base = place_heat(c, L)
    out = {'zone': base['zone'], 'years': base['years'], 'plants': {}}
    if len(whole) < 3: return out
    cache = {}
    for r in c.execute("SELECT code, temp_damage_above, heat_zone_high, heat_zone_low FROM plants WHERE status='active' ORDER BY code"):
        t = r['temp_damage_above']
        if t not in (None, '') and t not in cache:
            cache[t] = round(sum(1 for y in whole for _, x in years[y] if x >= t) / len(whole), 1)
        reach = cache.get(t) if t not in (None, '') else None
        out['plants'][r['code']] = {'level': heat_level(reach), 'reach': reach, 'above': t if t not in (None, '') else None,
                                    'fit': heat_zone_fit(base['zone'], r['heat_zone_high'], r['heat_zone_low'])}
    return out

@app.route('/api/heat/plants')
def heat_plants_api():
    """GET /api/heat/plants[?loc=ID]: every active plant's summer verdict where the plants are (see plants_heat)."""
    c = db()
    return jsonify(plants_heat(c, req_loc(c)))

def place_heat(c, L, above=None):
    """Summer heat at a place: days above 86°F each year, the AHS heat zone (from whole years only, and at least 3 of them),
    a usual summer's hottest day, and the months that usually have hot days."""
    years = place_highs(c, L)
    try: this_year = local_today(c).year
    except Exception: this_year = datetime.now(timezone.utc).year
    whole = sorted(y for y, v in years.items() if len(v) >= 330 and y < this_year)
    def count(v): return sum(1 for _, x in v if x > HEAT_LINE_F)
    def reach(v): return sum(1 for _, x in v if x >= above)
    per = [{'year': y, 'days': len(years[y]), 'partial': y not in whole, 'over86': count(years[y]), 'hottest': round(max(x for _, x in years[y])),
            **({'reach': reach(years[y])} if above is not None else {})}
           for y in sorted(years, reverse=True) if y in whole or y == this_year][:11]
    out = {'place': L['name'], 'line': HEAT_LINE_F, 'years': len(whole), 'since': whole[0] if whole else None, 'zone': None, 'over86': None,
           'hottest': None, 'above': above, 'per_year': per, 'months': [], 'hot_months': [], 'this_year': this_year}
    if len(whole) >= 3:
        n = len(whole)
        out['over86'] = round(sum(count(years[y]) for y in whole) / n)
        out['zone'] = ahs_heat_zone(sum(count(years[y]) for y in whole) / n)
        out['hottest'] = round(sum(max(x for _, x in years[y]) for y in whole) / n)
        by_month = [0] * 12
        for y in whole:
            for m, x in years[y]:
                if x > HEAT_LINE_F: by_month[m - 1] += 1
        out['months'] = [{'month': MONTH_ABBR[i], 'days': round(by_month[i] / n)} for i in range(12) if by_month[i] / n >= 0.5]
        if above is not None:           # 1.36.0: for one plant: the days a year that reach its heat-damage temperature, and in which months
            out['reach'] = round(sum(reach(years[y]) for y in whole) / n, 1)
            bm = [0] * 12
            for y in whole:
                for m, x in years[y]:
                    if x >= above: bm[m - 1] += 1
            out['hot_months'] = [{'month': MONTH_ABBR[i], 'days': round(bm[i] / n, 1)} for i in range(12) if bm[i] / n >= 0.5]
            out['level'] = heat_level(out['reach'])
    return out

def heat_brief(c, L):
    """The few numbers plant pages show next to the USDA zone (part of /api/meta)."""
    try:
        h = place_heat(c, L)
        return {'zone': h['zone'], 'over86': h['over86'], 'hottest': h['hottest'], 'years': h['years'], 'line': HEAT_LINE_F}
    except Exception:
        return {'zone': None, 'over86': None, 'hottest': None, 'years': 0, 'line': HEAT_LINE_F}

@app.route('/api/heat')
def heat_api():
    """GET /api/heat[?above=F][&loc=ID]: summer heat where the plants are (see place_heat); with above, a plant's own count too."""
    c = db()
    above = request.args.get('above')
    if above not in (None, ''):
        try: above = int(float(above))
        except ValueError: abort(400, 'above must be a temperature in °F')
        if not 50 <= above <= 140: abort(400, 'above must be between 50 and 140°F')
    else: above = None
    return jsonify(place_heat(c, req_loc(c), above))
