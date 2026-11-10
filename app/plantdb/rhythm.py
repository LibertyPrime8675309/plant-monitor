"""Prototype (proto/water-rhythm): how often you really water. For each plant, the gaps between the waterings in its care log over
the last RHYTHM_WINDOW days (for a plant out in the open, a day of rain of RAIN_COUNTS_IN or more counts as a watering, as it does
for the reminder), the typical gap (the median), and how that compares with the watering reminder (water_report in care.py).
When the two differ by a lot, the person can make the reminder match what they do: that sets the plant's "Check for water every
(days)" so that, with today's weather and being indoors or out, the reminder comes round at about their own gap.

Nothing new is stored. GET /api/rhythm[?plant=CODE] reads the care log and the weather; PUT /api/rhythm {plant, every} changes one
plant field (water_every_days) through apply_changes(), so it has a page version, an audit row and Undo in the history like any edit.
{plant, every: null} empties the field again, so the app works the gap out from the soil moisture range as before."""
from statistics import median
from .core import *   # noqa: F401,F403
from .care import RAIN_COUNTS_IN, water_base_days, water_factor, water_weather

ORDER = 60
RHYTHM_WINDOW = 120         # days of care log to look at
RHYTHM_MAX_GAP = 45         # a longer gap is a time nobody logged (away, or forgot), not a rhythm, so it is left out
RHYTHM_MIN_GAPS = 3         # fewer gaps than this and there is not enough to say
WATER_KINDS = ('water', 'prep_soak', 'prep_repot')      # the same entries the reminder counts as a watering

def rhythm_rain(c, start):
    """{date: inches} for days of rain that count as a watering, at the place in use, since start."""
    out = {}
    for d, data in c.execute('SELECT date, data FROM weather_daily WHERE loc_id=? AND date>=? ORDER BY date', (location(c)['id'], start)):
        try: x = json.loads(data)
        except ValueError: continue
        pr = x.get('precipitation_sum', x.get('rain_sum'))
        if pr is not None and pr >= RAIN_COUNTS_IN: out[d] = round(pr, 2)
    return out

def rhythm_state(gap, every):
    """'often' (watered well before the reminder), 'seldom' (well after) or 'matches'."""
    if gap <= every * 0.75 and every - gap >= 2: return 'often'
    if gap >= every * 1.33 and gap - every >= 2: return 'seldom'
    return 'matches'

def rhythm_setting_for(n, f):
    """The "Check for water every (days)" value that makes the reminder about n days with weather factor f: (value, the reminder it gives)."""
    # the reminder is round(base * f) (care.py), so try the whole numbers either side of n / f and keep the one that lands nearest n
    import math
    tries = {max(1, min(60, b)) for b in (math.floor(n / f), math.ceil(n / f), round(n / f))}
    base = min(tries, key=lambda b: (abs(max(1, round(b * f)) - n), -b))
    return base, max(1, round(base * f))

def rhythm_report(c, code=None):
    today = local_today(c)
    start = (today - timedelta(days=RHYTHM_WINDOW)).isoformat()
    avg_high, _ = water_weather(c, today)          # recent highs, the same the reminder uses
    if code: at, at_args = ' AND code=?', [code]
    else: at, at_args = plants_at(c, location(c))
    rows = c.execute("SELECT * FROM plants WHERE status='active'" + at + ' ORDER BY code', at_args).fetchall()
    days, checks = {}, {}
    q = 'SELECT plant_code, kind, done_on FROM care_log WHERE done_on>=? AND done_on<=? AND kind IN (%s)' % ','.join('?' * (len(WATER_KINDS) + 1))
    for pc, kind, d in c.execute(q, [start, today.isoformat(), *WATER_KINDS, 'check']):
        if kind == 'check': checks[pc] = checks.get(pc, 0) + 1
        else: days.setdefault(pc, set()).add(d)
    rain = None
    photo = lambda pid: (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
    out = []
    for r in rows:
        site = r['site'] or 'Outdoors'
        own = sorted(days.get(r['code'], ()))
        rained = []
        if site == 'Outdoors':
            if rain is None: rain = rhythm_rain(c, start)
            # rain only counts once the plant's own log starts, so a plant added last week is not credited with last month's storms
            rained = [d for d in rain if own and d >= own[0] and d not in own]
        ds = sorted(set(own) | set(rained))
        gaps_all = [(date.fromisoformat(b) - date.fromisoformat(a)).days for a, b in zip(ds, ds[1:])]
        gaps = [g for g in gaps_all if g <= RHYTHM_MAX_GAP]
        base, base_why = water_base_days(r)
        f, f_why = water_factor(avg_high, site in INSIDE_SITES)
        every = max(1, round(base * f))
        p = {'code': r['code'], 'name': r['common_name'], 'photo': photo(r['id']), 'site': site, 'every': every, 'base': base,
             'base_why': base_why, 'own_setting': r['water_every_days'], 'weather': f_why, 'factor': f,
             'waterings': len(own), 'rain_days': len(rained), 'first': ds[0] if ds else None, 'checks': checks.get(r['code'], 0),
             'gaps': gaps[-8:], 'left_out': len(gaps_all) - len(gaps)}
        if len(gaps) < RHYTHM_MIN_GAPS:
            p.update(state='few', gap=None, suggest=None)
        else:
            gap = median(gaps)
            n = max(1, round(gap))
            p.update(gap=round(gap, 1), state=rhythm_state(gap, every))
            setting, gives = rhythm_setting_for(n, f)
            p['suggest'] = {'every': gives, 'setting': setting} if gives != every else None
        out.append(p)
    order = {'often': 0, 'seldom': 1, 'matches': 2, 'few': 3}
    out.sort(key=lambda p: (order[p['state']], -abs(p['gap'] - p['every']) if p['gap'] is not None else 0, p['code']))
    n = lambda s: sum(1 for p in out if p['state'] == s)
    return {'today': today.isoformat(), 'window': RHYTHM_WINDOW, 'max_gap': RHYTHM_MAX_GAP, 'min_gaps': RHYTHM_MIN_GAPS,
            'rain_counts_in': RAIN_COUNTS_IN, 'plants': out,
            'counts': {'often': n('often'), 'seldom': n('seldom'), 'matches': n('matches'), 'few': n('few')}}

@app.route('/api/rhythm', methods=['GET', 'PUT'])
def rhythm():
    """GET: how often each plant is watered, against its reminder (?plant=CODE: one plant, for its own page).
    PUT {plant, every: N}: make the reminder about N days; {plant, every: null}: let the app work it out again. Not for viewers."""
    c = db()
    if request.method == 'GET': return jsonify(rhythm_report(c, request.args.get('plant') or None))
    b = request.get_json(silent=True) or {}
    r = plant_row(c, str(b.get('plant') or ''))
    if 'setting' in b:                       # Undo: put back exactly what the field held before (a number, or null for empty)
        apply_changes(c, r, {'water_every_days': '' if b['setting'] is None else b['setting']}, editor(), 'update', 'How often you water: undone')
    elif b.get('every') is None:
        if r['water_every_days'] is None: return jsonify(rhythm_report(c, r['code']))
        apply_changes(c, r, {'water_every_days': ''}, editor(), 'update', 'How often you water: back to the app\'s own estimate')
    else:
        try: n = int(b['every'])
        except (TypeError, ValueError): abort(400, 'every must be a number of days')
        if not 1 <= n <= 60: abort(400, 'every must be between 1 and 60 days')
        avg_high, _ = water_weather(c, local_today(c))
        f, _ = water_factor(avg_high, (r['site'] or 'Outdoors') in INSIDE_SITES)
        setting, gives = rhythm_setting_for(n, f)
        apply_changes(c, r, {'water_every_days': setting}, editor(), 'update',
                      f'How often you water: reminder set to about every {gives} days ("Check for water every" {setting} days)')
    c.commit()
    return jsonify(rhythm_report(c, r['code']))
