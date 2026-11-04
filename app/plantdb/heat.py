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

def place_heat(c, L):
    """Summer heat at a place: days above 86°F each year, the AHS heat zone (from whole years only, and at least 3 of them),
    a usual summer's hottest day, and the months that usually have hot days."""
    years = place_highs(c, L)
    try: this_year = local_today(c).year
    except Exception: this_year = datetime.now(timezone.utc).year
    whole = sorted(y for y, v in years.items() if len(v) >= 330 and y < this_year)
    def count(v): return sum(1 for _, x in v if x > HEAT_LINE_F)
    per = [{'year': y, 'days': len(years[y]), 'partial': y not in whole, 'over86': count(years[y]), 'hottest': round(max(x for _, x in years[y]))}
           for y in sorted(years, reverse=True) if y in whole or y == this_year][:11]
    out = {'place': L['name'], 'line': HEAT_LINE_F, 'years': len(whole), 'since': whole[0] if whole else None, 'zone': None, 'over86': None,
           'hottest': None, 'per_year': per, 'months': [], 'this_year': this_year}
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
    """GET /api/heat[?loc=ID]: summer heat where the plants are (see place_heat)."""
    c = db()
    return jsonify(place_heat(c, req_loc(c)))
