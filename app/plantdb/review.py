"""1.37.0: a year in review. One page per year, one card per plant, from what the app already holds: the first and last photo
of the year, how the health went, moves (site changes), waterings and feedings, cold nights and hot days it sat through outside,
requests answered. Meant for deciding what to keep, move or give away. Everything is read from the logs; nothing is written."""
from .core import *   # noqa: F401,F403

def review_years(c):
    """The years the app has anything for, newest first."""
    ys = set()
    for t, col in (('audit_log', 'changed_at'), ('care_log', 'done_on'), ('fertilizer_log', 'applied_on'), ('photos', 'added_at')):
        for (y,) in c.execute(f'SELECT DISTINCT substr({col}, 1, 4) FROM {t} WHERE {col} IS NOT NULL'):
            if y and y.isdigit(): ys.add(int(y))
    return sorted(ys, reverse=True)

def review_weather(c, L, year):
    """The year's cold nights (below 32°F) and hot days (above 86°F) at a place, with the dates, from the daily history."""
    cold, hot = [], []
    try:
        rows = c.execute("SELECT date, json_extract(data, '$.temperature_2m_min'), json_extract(data, '$.temperature_2m_max') FROM weather_daily WHERE loc_id=? AND kind='observed' AND date>=? AND date<=?",
                         (L['id'], f'{year}-01-01', f'{year}-12-31')).fetchall()
    except sqlite3.OperationalError:
        rows = [(d, (json.loads(x) if x else {}).get('temperature_2m_min'), (json.loads(x) if x else {}).get('temperature_2m_max'))
                for d, x in c.execute("SELECT date, data FROM weather_daily WHERE loc_id=? AND kind='observed' AND date>=? AND date<=?", (L['id'], f'{year}-01-01', f'{year}-12-31'))]
    for d, lo, hi in rows:
        if isinstance(lo, (int, float)) and lo <= 32: cold.append((d, lo))
        if isinstance(hi, (int, float)) and hi > 86: hot.append((d, hi))
    return {'days': len(rows), 'cold': cold, 'hot': hot, 'coldest': min((x for _, x in cold), default=None), 'hottest': max((x for _, x in hot), default=None)}

def review_plant(c, r, year, wx):
    code, pid = r['code'], r['id']
    lo, hi = f'{year}-01-01', f'{year}-12-31T23:59:59Z'
    audits = c.execute('SELECT * FROM audit_log WHERE plant_id=? AND changed_at>=? AND changed_at<=? ORDER BY id', (pid, lo, hi)).fetchall()
    health = [(a['changed_at'], a['old_value'], a['new_value']) for a in audits if a['field'] == 'health_rating']
    sites = [(a['changed_at'], a['old_value'], a['new_value']) for a in audits if a['field'] == 'site']
    spots = [(a['changed_at'], a['old_value'], a['new_value']) for a in audits if a['field'] == 'location']
    created = c.execute("SELECT MIN(changed_at) FROM audit_log WHERE plant_id=? AND action='create'", (pid,)).fetchone()[0]
    if not created:
        created = c.execute('SELECT MIN(changed_at) FROM audit_log WHERE plant_id=?', (pid,)).fetchone()[0]
    photos = c.execute('SELECT file, caption, added_at FROM photos WHERE plant_id=? AND added_at>=? AND added_at<=? ORDER BY added_at, id', (pid, lo, hi)).fetchall()
    water = c.execute("SELECT COUNT(*) FROM care_log WHERE plant_code=? AND kind='water' AND done_on>=? AND done_on<=?", (code, lo, f'{year}-12-31')).fetchone()[0]
    care_other = c.execute("SELECT kind, COUNT(*) FROM care_log WHERE plant_code=? AND kind!='water' AND done_on>=? AND done_on<=? GROUP BY kind", (code, lo, f'{year}-12-31')).fetchall()
    fed = c.execute('SELECT COUNT(*) FROM fertilizer_log WHERE plant_code=? AND applied_on>=? AND applied_on<=?', (code, lo, f'{year}-12-31')).fetchone()[0]
    reqs = c.execute('SELECT COUNT(*), SUM(done) FROM requests WHERE plant_code=? AND created_at>=? AND created_at<=?', (code, lo, hi)).fetchone()
    # health at the start of the year and at the end (or now)
    h_start = health[0][1] if health else r['health_rating']
    h_end = health[-1][2] if health else r['health_rating']
    order = {h: i for i, h in enumerate(HEALTH[::-1])}       # Critical 0 .. Good 3
    trend = None
    if h_start in order and h_end in order: trend = 'better' if order[h_end] > order[h_start] else 'worse' if order[h_end] < order[h_start] else 'same'
    # cold nights and hot days it sat through outside: the site at each date, walked from the site changes (current site before the first change)
    def site_on(d):
        s = r['site'] or 'Outdoors'
        for at, old, new in reversed(sites):
            if at[:10] > d: s = old or 'Outdoors'
        return s
    out_cold = [d for d, x in wx['cold'] if site_on(d) in ('Outdoors', 'Covered porch') and (r['temp_damage_below'] is None or x < r['temp_damage_below'])]
    out_hot = [d for d, x in wx['hot'] if site_on(d) in ('Outdoors', 'Covered porch') and r['temp_damage_above'] is not None and x >= r['temp_damage_above']]
    moves = [{'at': at, 'from': old or 'Outdoors', 'to': new or 'Outdoors'} for at, old, new in sites]
    return {'code': code, 'name': r['common_name'], 'status': r['status'], 'site': r['site'] or 'Outdoors', 'winter_plan': r['winter_plan'],
            'new_this_year': bool(created and created[:4] == str(year)), 'created': created,
            'health': {'start': h_start, 'end': h_end, 'trend': trend, 'changes': len(health)},
            'photos': {'n': len(photos), 'first': dict(photos[0]) if photos else None, 'last': dict(photos[-1]) if len(photos) > 1 else None},
            'moves': moves, 'spot_changes': len(spots), 'water': water, 'fed': fed, 'care': {k: n for k, n in care_other},
            'requests': {'asked': reqs[0] or 0, 'answered': reqs[1] or 0},
            'cold_nights': len(out_cold), 'cold_first': out_cold[0] if out_cold else None, 'hot_days': len(out_hot),
            'edits': sum(1 for a in audits if a['action'] in ('update', 'edit', 'change')),
            'archived': r['status'] == 'archived'}

@app.route('/api/review')
def review_api():
    """GET /api/review[?year=YYYY]: the year in review for every plant that existed in that year."""
    c = db(); L = location(c)
    years = review_years(c)
    try: year = int(request.args.get('year') or (years[0] if years else local_today(c).year))
    except ValueError: abort(400, 'year must be a number')
    wx = review_weather(c, L, year)
    plants = []
    for r in c.execute('SELECT * FROM plants ORDER BY code'):
        created = c.execute('SELECT MIN(changed_at) FROM audit_log WHERE plant_id=?', (r['id'],)).fetchone()[0]
        if created and created[:4] > str(year): continue              # did not exist yet
        plants.append(review_plant(c, r, year, wx))
    n = len(plants)
    totals = {'plants': n, 'new': sum(1 for p in plants if p['new_this_year']), 'archived': sum(1 for p in plants if p['archived']),
              'better': sum(1 for p in plants if p['health']['trend'] == 'better'), 'worse': sum(1 for p in plants if p['health']['trend'] == 'worse'),
              'photos': sum(p['photos']['n'] for p in plants), 'water': sum(p['water'] for p in plants), 'fed': sum(p['fed'] for p in plants),
              'moves': sum(len(p['moves']) for p in plants), 'answered': sum(p['requests']['answered'] for p in plants)}
    return jsonify(year=year, years=years, place=L['name'], weather={'days': wx['days'], 'cold_nights': len(wx['cold']), 'coldest': wx['coldest'], 'hot_days': len(wx['hot']), 'hottest': wx['hottest']},
                   totals=totals, plants=plants)

# ---- 1.37.0: the share sheet target. The service worker normally answers this itself (it keeps the pictures on the device);
# this is the fallback when there is no service worker (the first visit, or a browser without one): the pictures are added
# as unassigned photos straight away.
# 1.58.0: it lives at /share-in. It was /share, the prefix Tailscale Funnel publishes for plant-sitter links, so anyone on the
# internet could post pictures to it with no sign-in. Nothing under /share takes pictures now; /share itself only sends a
# person on to the page (an installed app that still has the old address is answered by its service worker, as before).
SHARE_IN = '/share-in'

@app.route('/share')
def share_page():
    return Response('', 302, {'Location': '/#/share'})

@app.route(SHARE_IN, methods=['GET', 'POST'])
def share_target():
    if request.method == 'GET': return Response('', 302, {'Location': '/#/share'})
    c = db(); n = 0
    for f in request.files.getlist('photos'):
        if not f or not f.filename: continue
        name = save_image(f)
        c.execute('INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(NULL,?,?,?,0,?,?,?)',
                  (name, (request.form.get('title') or request.form.get('text') or f.filename or '')[:200], 'other', f.filename, editor(), now()))
        audit_only(c, 'photo_add', 'photo', None, name, editor(), 'Photo shared from a phone')
        n += 1
    c.commit()
    return Response('', 303, {'Location': '/#/photos'})
