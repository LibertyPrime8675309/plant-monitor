"""The plant-sitter sheet: a printable plan for someone looking after the plants while Ethan is away.
Prototype proto/sitter-sheet (November 2), rebuilt on the module layout in 1.42.0. Read only: viewers can make it too.
The names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
SITTER_MAX_DAYS = 42

@app.route('/api/sitter')
def sitter_api():
    """Day by day, which plants to check for water between two dates, from the same reminders as Today.
    ?from=YYYY-MM-DD&to=YYYY-MM-DD (default: tomorrow for a week), optional ?group=<id>."""
    c = db()
    today = local_today(c)
    try:
        d0 = date.fromisoformat(request.args.get('from') or (today + timedelta(days=1)).isoformat())
        d1 = date.fromisoformat(request.args.get('to') or (d0 + timedelta(days=6)).isoformat())
    except ValueError:
        abort(400, 'Dates must look like 2026-11-07')
    if d0 < today: abort(400, 'The first day has already gone. Choose today or a later day.')
    if d1 < d0: abort(400, 'The last day is before the first day.')
    if (d1 - d0).days + 1 > SITTER_MAX_DAYS: abort(400, f'Choose {SITTER_MAX_DAYS // 7} weeks or less.')
    group, codes = None, None
    if request.args.get('group'):
        gr = c.execute('SELECT * FROM plant_groups WHERE id=?', (request.args.get('group'),)).fetchone()
        if not gr: abort(404, 'That group is not in your list any more')
        group, codes = {'id': gr['id'], 'name': gr['name']}, group_codes(c, gr)
        if not codes: return jsonify(today=today.isoformat(), start=d0.isoformat(), end=d1.isoformat(), group=group, days=[], before=[], plants=[], nights=[], rain_counts_in=RAIN_COUNTS_IN)
    W = water_report(c, codes)
    rows = {r['code']: r for r in c.execute("SELECT * FROM plants WHERE status='active'")}
    days = {(d0 + timedelta(days=i)).isoformat(): [] for i in range((d1 - d0).days + 1)}
    plants, before = [], []
    for w in W['plants']:
        r = rows.get(w['code'])
        if not r: continue
        nxt = date.fromisoformat(w['next']) if w['next'] else None
        if d0 > today and (nxt is None or nxt < d0):     # due (or never logged) before the sitter starts: water it before leaving,
            before.append(w['code'])                     # and the plan assumes that happens the day before
            nxt = d0 - timedelta(days=1) + timedelta(days=w['every'])
        d, visits = max(nxt or d0, d0), []
        while d <= d1:
            days[d.isoformat()].append(w['code']); visits.append(d.isoformat())
            d += timedelta(days=w['every'])
        plants.append({'code': r['code'], 'name': r['common_name'], 'scientific': r['scientific_name'], 'site': w['site'], 'spot': r['location'] or '',
                       'every': w['every'], 'why': w['why'], 'state': w['state'], 'next': w['next'], 'visits': visits,
                       'water_notes': r['water_notes'] or '', 'damage_below': r['temp_damage_below'], 'damage_above': r['temp_damage_above'],
                       'winter_plan': r['winter_plan'] or '', 'open_sky': w['site'] == 'Outdoors'})
    order = {s: i for i, s in enumerate(SITES)}
    walk = {p['code']: (order.get(p['site'], 9), p['spot'].lower(), p['code']) for p in plants}     # one walk round: place, then spot
    plants.sort(key=lambda p: walk[p['code']])
    fc = {x['date']: x for x in (loc_json(c, location(c)['id'], 'forecast').get('days') or [])}
    want = set(p['code'] for p in plants)
    nights = []
    for n in frost_report(c)['nights']:
        if not (d0.isoformat() <= n['date'] <= d1.isoformat()) or not n['level']: continue
        at = [{'code': x['code'], 'name': x['name'], 'level': x['level'], 'damage': x['damage'], 'lethal': x['lethal'], 'site': x['site']}
              for x in n['plants'] if x['code'] in want]
        if at: nights.append({'date': n['date'], 'low': n['low'], 'plants': at})
    out_days = [{'date': d, 'high': (fc.get(d) or {}).get('high'), 'low': (fc.get(d) or {}).get('low'),
                 'plants': sorted(v, key=lambda k: walk[k])} for d, v in days.items()]
    return jsonify(today=today.isoformat(), start=d0.isoformat(), end=d1.isoformat(), group=group, days=out_days,
                   before=sorted(before, key=lambda k: walk[k]), plants=plants, nights=nights, rain_counts_in=RAIN_COUNTS_IN,
                   forecast_to=max(fc) if fc else None)
