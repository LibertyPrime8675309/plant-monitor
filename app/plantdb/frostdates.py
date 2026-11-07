"""Prototype (proto/frost-dates): frost dates where the plants are, from the place's own weather history.
For each whole winter (July to June) it finds the first and last night at or below a temperature, then gives the usual
(middle) date, the earliest and latest seen, and how many winters never got that cold. The Weather page shows it for a
freeze (32°F), a hard freeze (28°F) and, from Ethan's answer of November 6, "frost possible" (36°F: frost can form in low
spots on a clear, still night); the Cold-night checklist shows it for each damage temperature of the plants that are outside
(one plant a line, with its photo); Back outside shows when the cold nights usually end; Today has a line in October and
November (the usual first freeze) and February and March (the usual last). It reads weather_daily only and changes nothing."""
from .core import *   # noqa: F401,F403
from .lights import plant_photo

FREEZE_F, HARD_FREEZE_F, FROST_POSSIBLE_F = 32, 28, 36
FROST_SEASON_MIN_DAYS = 330          # a winter counts once this many of its days have a low
FROST_SEASON_MIN = 3                 # whole winters needed before dates are given (like the winter and summer zones)
PLACE_LOWS = {}

def season_of(d):
    """The winter a date belongs to, named by the year it starts in: July 2025 to June 2026 is 2025."""
    return d.year if d.month >= 7 else d.year - 1

def season_day(d):
    """Days since July 1 of the date's winter (0 to 364), on a calendar without a leap day (February 29 counts as the 28th),
    so March 1 is the same day of the winter every year."""
    return (date(2001 if d.month >= 7 else 2002, d.month, 28 if (d.month, d.day) == (2, 29) else d.day) - date(2001, 7, 1)).days

def season_label(n):
    """A day of the winter as a month and day ("Dec 4"), on a calendar without a leap day."""
    d = date(2001, 7, 1) + timedelta(days=int(round(n)))
    return d.strftime('%b ') + str(d.day)

def place_lows(c, L):
    """Each observed night's low at a place, as {winter: [(date, low), ...]} in date order. Worked out again when the place's
    daily weather changes (an hourly update or Load history), and at least every 6 hours."""
    stamp = tuple(c.execute("SELECT COUNT(*), MAX(updated_at) FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],)).fetchone())
    hit = PLACE_LOWS.get(L['id'])
    if hit and hit[2] == stamp and time.time() - hit[0] < 6 * 3600: return hit[1]
    try: rows = c.execute("SELECT date, json_extract(data, '$.temperature_2m_min') FROM weather_daily WHERE loc_id=? AND kind='observed' ORDER BY date", (L['id'],)).fetchall()
    except sqlite3.OperationalError:            # an SQLite without JSON functions
        rows = [(d, (json.loads(x) if x else {}).get('temperature_2m_min')) for d, x in c.execute("SELECT date, data FROM weather_daily WHERE loc_id=? AND kind='observed' ORDER BY date", (L['id'],))]
    out = {}
    for d, t in rows:
        if not isinstance(t, (int, float)): continue
        try: dd = date.fromisoformat(d[:10])
        except ValueError: continue
        out.setdefault(season_of(dd), []).append((dd, t))
    PLACE_LOWS[L['id']] = (time.time(), out, stamp)
    return out

def cold_nights(nights, below, strict=False):
    """The nights of one winter at or below a temperature (below it, with strict: the way the frost alert counts damage)."""
    return [(d, t) for d, t in nights if (t < below if strict else t <= below)]

def middle(v):
    v = sorted(v); n = len(v)
    return None if not n else v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2

def season_stats(seasons, below, strict=False):
    """First and last nights at or below a temperature over whole winters ({winter: nights}): the usual date (middle of the
    winters that had one), the earliest and latest seen, and how many winters had none. Dates are days since July 1."""
    firsts, lasts, none = [], [], 0
    for s in sorted(seasons):
        cold = cold_nights(seasons[s], below, strict)
        if not cold: none += 1; continue
        firsts.append(season_day(cold[0][0])); lasts.append(season_day(cold[-1][0]))
    n = len(seasons)
    def pack(v, early_word, late_word):
        if not v: return None
        return {'usual': season_label(middle(v)), 'usual_day': round(middle(v)), early_word: season_label(min(v)), late_word: season_label(max(v))}
    return {'below': below, 'winters': n, 'had': n - none, 'none': none, 'most_none': none * 2 > n,
            'first': pack(firsts, 'earliest', 'latest'), 'last': pack(lasts, 'earliest', 'latest')}

def frost_dates(c, L):
    """Frost dates at a place: usual first and last freeze and hard freeze, the frost-free days between, each whole winter,
    this winter so far, and the usual first damaging night for each damage temperature of the plants that are outside."""
    by = place_lows(c, L)
    today = datetime.now(tzinfo(L['tz'])).date()
    now_s = season_of(today)
    whole = {s: v for s, v in by.items() if len(v) >= FROST_SEASON_MIN_DAYS and s < now_s}
    out = {'place': L['name'], 'today': today.isoformat(), 'winters': len(whole), 'need': FROST_SEASON_MIN,
           'since': f'{min(whole)}' if whole else None, 'ready': len(whole) >= FROST_SEASON_MIN}
    # this winter so far (from July 1), whether or not there is enough history for the usual dates
    cur = by.get(now_s, [])
    cur_freeze, cur_possible = cold_nights(cur, FREEZE_F), cold_nights(cur, FROST_POSSIBLE_F)
    coldest = min(cur, key=lambda x: x[1]) if cur else None
    night = lambda x: {'date': x[0].isoformat(), 'low': round(x[1])}
    out['now'] = {'winter': f'{now_s} to {now_s + 1}', 'nights': len(cur),
                  'first_freeze': night(cur_freeze[0]) if cur_freeze else None, 'last_freeze': night(cur_freeze[-1]) if cur_freeze else None,
                  'freezes': len(cur_freeze), 'coldest': night(coldest) if coldest else None,
                  'first_possible': night(cur_possible[0]) if cur_possible else None, 'possibles': len(cur_possible)}
    out['month'] = today.month
    if not out['ready']: return out
    fr, hard, poss = season_stats(whole, FREEZE_F), season_stats(whole, HARD_FREEZE_F), season_stats(whole, FROST_POSSIBLE_F)
    out['freeze'], out['hard'], out['possible'] = fr, hard, poss
    # frost-free days: from the last freeze of one winter to the first of the next, the middle over the years with both
    gaps = []
    for s in sorted(whole):
        a, b = cold_nights(whole[s], FREEZE_F), cold_nights(whole.get(s + 1, []), FREEZE_F)
        if a and b and s + 1 in whole: gaps.append((b[0][0] - a[-1][0]).days)
    out['frost_free_days'] = round(middle(gaps)) if gaps else None
    day = season_day(today)
    if fr['first']: out['days_to_usual'] = fr['first']['usual_day'] - day           # the usual first freeze (fall), from today
    # spring: days to the usual last night at or below each temperature (negative once it has passed)
    out['days_to_last'] = {k: S['last']['usual_day'] - day for k, S in (('freeze', fr), ('hard', hard), ('possible', poss)) if S['last']}
    out['per_winter'] = []
    for s in sorted(whole, reverse=True)[:10]:
        v = whole[s]; f = cold_nights(v, FREEZE_F); lo = min(v, key=lambda x: x[1]); f36 = cold_nights(v, FROST_POSSIBLE_F)
        out['per_winter'].append({'winter': f'{s} to {s + 1}', 'first': f[0][0].isoformat() if f else None, 'last': f[-1][0].isoformat() if f else None,
                                  'first_possible': f36[0][0].isoformat() if f36 else None, 'last_possible': f36[-1][0].isoformat() if f36 else None,
                                  'freezes': len(f), 'hard': len(cold_nights(v, HARD_FREEZE_F)), 'coldest': round(lo[1]), 'coldest_on': lo[0].isoformat()})
    # the plants outside, grouped by the temperature that damages them (the frost alert counts a night below it)
    at, at_args = plants_at(c, L)
    groups = {}
    for r in c.execute("SELECT id, code, common_name, temp_damage_below, winter_plan, site FROM plants WHERE status='active' AND temp_damage_below IS NOT NULL"
                       + at + " ORDER BY code", at_args):
        if (r['site'] or 'Outdoors') in INSIDE_SITES: continue
        groups.setdefault(r['temp_damage_below'], []).append({'code': r['code'], 'name': r['common_name'], 'plan': r['winter_plan'], 'site': r['site'] or 'Outdoors',
                                                              'photo': plant_photo(c, r['id'])})
    out['plants'] = []
    for t, ps in groups.items():
        st = season_stats(whole, t, strict=True)
        this = cold_nights(cur, t, strict=True)
        out['plants'].append({'below': t, 'plants': ps, 'first': st['first'], 'had': st['had'], 'winters': st['winters'], 'most_none': st['most_none'],
                              'this_winter': {'date': this[0][0].isoformat(), 'low': round(this[0][1])} if this else None})
    out['plants'].sort(key=lambda g: (g['first']['usual_day'] if g['first'] and not g['most_none'] else 999, -g['below']))
    return out

@app.route('/api/frost/dates')
def frost_dates_api():
    """GET /api/frost/dates[?loc=ID]: frost dates at a place (see frost_dates)."""
    c = db()
    return jsonify(frost_dates(c, req_loc(c)))
