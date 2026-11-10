"""The plant-sitter sheet: a printable plan for someone looking after the plants while Ethan is away.
Prototype proto/sitter-sheet (November 2), rebuilt on the module layout in 1.42.0. Read only: viewers can make it too.
1.49.0 (PLAN.md step 4c): the sheet by link. An editor makes a link with a long random token; /share/<token> serves the sheet for
those dates to anyone who has the link (through Tailscale Funnel on the /share path, beside /cal), lets them tick boxes, and stops
working the day after the last day away. Nothing else is reachable through it: every /share/ route checks the token and serves only
the sheet, its stylesheet, its script and the photos of the plants on it. guard() lets /share/ through like /cal/.
The names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
from werkzeug.exceptions import HTTPException
SITTER_MAX_DAYS = 42

SITTER_SCHEMA = """
CREATE TABLE IF NOT EXISTS sitter_shares(token TEXT PRIMARY KEY, from_d TEXT NOT NULL, to_d TEXT NOT NULL, group_id INTEGER, place_id INTEGER, note TEXT NOT NULL DEFAULT '',
  photos INTEGER NOT NULL DEFAULT 1, created_by TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL, revoked_at TEXT, last_seen TEXT);
CREATE TABLE IF NOT EXISTS sitter_ticks(token TEXT NOT NULL, day TEXT NOT NULL, plant_code TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'water',
  ticked_at TEXT NOT NULL, PRIMARY KEY(token, day, plant_code, kind));
"""
def sitter_tables(c): c.executescript(SITTER_SCHEMA)      # init_db() runs this too; here for a database opened by an older mock

@app.route('/api/sitter')
def sitter_api():
    """Day by day, which plants to check for water between two dates, from the same reminders as Today.
    ?from=YYYY-MM-DD&to=YYYY-MM-DD (default: tomorrow for a week), optional ?group=<id>."""
    c = db()
    return jsonify(sitter_sheet(c, request.args.get('from'), request.args.get('to'), request.args.get('group')))

def sitter_sheet(c, from_s, to_s, group_s, started=False):
    """The sheet's data. started: a shared sheet whose first day has passed still shows (the sitter is in the middle of it)."""
    today = local_today(c)
    try:
        d0 = date.fromisoformat(from_s or (today + timedelta(days=1)).isoformat())
        d1 = date.fromisoformat(to_s or (d0 + timedelta(days=6)).isoformat())
    except ValueError:
        abort(400, 'Dates must look like 2026-11-07')
    if d0 < today and not started: abort(400, 'The first day has already gone. Choose today or a later day.')
    if d1 < d0: abort(400, 'The last day is before the first day.')
    if (d1 - d0).days + 1 > SITTER_MAX_DAYS: abort(400, f'Choose {SITTER_MAX_DAYS // 7} weeks or less.')
    group, codes = None, None
    if group_s:
        gr = c.execute('SELECT * FROM plant_groups WHERE id=?', (group_s,)).fetchone()
        if not gr: abort(404, 'That group is not in your list any more')
        group, codes = {'id': gr['id'], 'name': gr['name']}, group_codes(c, gr)
        if not codes: return dict(today=today.isoformat(), start=d0.isoformat(), end=d1.isoformat(), group=group, days=[], before=[], plants=[], nights=[], rain_counts_in=RAIN_COUNTS_IN)
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
        ph = c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC, id LIMIT 1', (r['id'],)).fetchone()   # 1.47.0: a picture on the sheet, so the sitter knows which pot
        plants.append({'code': r['code'], 'name': r['common_name'], 'scientific': r['scientific_name'], 'site': w['site'], 'spot': r['location'] or '', 'photo': ph[0] if ph else None,
                       'every': w['every'], 'why': w['why'], 'state': w['state'], 'next': w['next'], 'visits': visits,
                       'water_notes': r['water_notes'] or '', 'damage_below': r['temp_damage_below'], 'damage_above': r['temp_damage_above'],
                       'winter_plan': r['winter_plan'] or '', 'open_sky': w['site'] == 'Outdoors' and w.get('action', 'water') == 'water',
                       'action': w.get('action', 'water'),            # 1.57.0: a semi-hydro pot is topped up, a water-only one gets fresh water
                       'action_words': {'topup': 'Semi-hydro: top up the water to the line (it does not dry out between)', 'waterchange': 'In water only: pour out the old water and fill with fresh'}.get(w.get('action'), '')})
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
    # 1.56.0 (PLAN.md step 8b): a photo of each room or shelf the plants on the sheet are on, so the sitter can find them
    pph, places, seen = place_photo_map(c), [], set()
    for p in plants:
        r = rows[p['code']]
        for pid in ((r['spot_id'],) if r['spot_id'] else ()) + ((-r['area_id'],) if r['area_id'] else ()):
            if pid in seen or not pph.get(pid): continue
            seen.add(pid); places.append({'label': place_label(c, pid), 'photo': pph[pid]}); break
    out_days = [{'date': d, 'high': (fc.get(d) or {}).get('high'), 'low': (fc.get(d) or {}).get('low'),
                 'plants': sorted(v, key=lambda k: walk[k])} for d, v in days.items()]
    return dict(today=today.isoformat(), start=d0.isoformat(), end=d1.isoformat(), group=group, days=out_days,
                before=sorted(before, key=lambda k: walk[k]), plants=plants, nights=nights, rain_counts_in=RAIN_COUNTS_IN, places=places,
                forecast_to=max(fc) if fc else None)

# ---------------------------------------------------------------- 1.49.0: the sheet by link
SHARE_PATH = '/share'

def share_row(c, token):
    r = c.execute('SELECT * FROM sitter_shares WHERE token=?', (token,)).fetchone()
    if r is None: abort(404, 'This link is not one of ours. Ask for a new one.')
    if r['revoked_at']: abort(410, 'This sheet has been taken down. Ask for a new link.')
    if now() > r['expires_at']: abort(410, 'This sheet has expired: the days it covered are over. Ask for a new link.')
    return r

def share_known(c, token):
    """For the page's own files (stylesheet, scripts, fonts): the token must be one of ours, live or not, so a dead link still
    shows its reason in plain words."""
    if not c.execute('SELECT 1 FROM sitter_shares WHERE token=?', (token,)).fetchone(): abort(404)

def share_dict(c, r):
    n = c.execute('SELECT COUNT(*) FROM sitter_ticks WHERE token=?', (r['token'],)).fetchone()[0]
    o = ics_saved(c)
    return {'token': r['token'], 'from': r['from_d'], 'to': r['to_d'], 'group': r['group_id'], 'note': r['note'], 'photos': bool(r['photos']),
            'created_by': r['created_by'], 'created_at': r['created_at'], 'expires_at': r['expires_at'], 'revoked_at': r['revoked_at'], 'last_seen': r['last_seen'], 'ticks': n,
            'live': not r['revoked_at'] and now() <= r['expires_at'],
            'url': (o['public_base'].rstrip('/') + SHARE_PATH + '/' + r['token']) if o['public_base'] else None,
            'local_url': (setting(c, 'base_url', '') or request.host_url.rstrip('/')) + SHARE_PATH + '/' + r['token']}

@app.route('/api/sitter/shares', methods=['GET', 'POST'])
def sitter_shares():
    """GET: the links made so far (newest first). POST {from, to, group, note, photos}: a new link (editors and the owner;
    the guard refuses viewers). Lives until the day after the last day away."""
    c = db(); sitter_tables(c)
    if request.method == 'POST':
        b = request.get_json(silent=True) or {}
        D = sitter_sheet(c, b.get('from'), b.get('to'), b.get('group') or None)          # checks the dates and the group
        tok = secrets.token_urlsafe(24)
        exp = datetime.combine(date.fromisoformat(D['end']) + timedelta(days=1), datetime.max.time(), tzinfo(location(c)['tz'])).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        c.execute('INSERT INTO sitter_shares(token,from_d,to_d,group_id,place_id,note,photos,created_by,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                  (tok, D['start'], D['end'], D['group']['id'] if D['group'] else None, location(c)['id'], str(b.get('note') or '')[:1000], 1 if b.get('photos', True) else 0, editor(), now(), exp))
        audit_only(c, 'setting', 'sitter_share', None, f'{D["start"]} to {D["end"]}', editor(), f'Plant-sitter sheet shared by link for {D["start"]} to {D["end"]}' + (f' (group {D["group"]["name"]})' if D['group'] else ''))
        c.commit()
        return jsonify(share=share_dict(c, c.execute('SELECT * FROM sitter_shares WHERE token=?', (tok,)).fetchone()), public_base=ics_saved(c)['public_base']), 201
    rows = c.execute('SELECT * FROM sitter_shares WHERE place_id=? ORDER BY rowid DESC LIMIT 50', (location(c)['id'],)).fetchall()
    return jsonify(shares=[share_dict(c, r) for r in rows], public_base=ics_saved(c)['public_base'], share_path=SHARE_PATH)

@app.route('/api/sitter/shares/<token>', methods=['DELETE'])
def sitter_share_stop(token):
    """Takes a link down: it answers "taken down" from now on. Its ticks are kept."""
    c = db(); sitter_tables(c)
    r = c.execute('SELECT * FROM sitter_shares WHERE token=?', (token,)).fetchone()
    if r is None: abort(404, 'That link is not in the list')
    c.execute('UPDATE sitter_shares SET revoked_at=? WHERE token=?', (now(), token))
    audit_only(c, 'setting', 'sitter_share', f'{r["from_d"]} to {r["to_d"]}', None, editor(), 'Plant-sitter link taken down')
    c.commit()
    return jsonify(ok=True)

@app.route('/api/sitter/ticks')
def sitter_ticks_mine():
    """The sitter's ticks, for the sheet in the app: ?from=&to=&group= finds the live links for those days (the newest is the one
    reported); the ticks of all of them count, in case two links were made and the sitter opened the first."""
    c = db(); sitter_tables(c)
    q = 'SELECT * FROM sitter_shares WHERE from_d=? AND to_d=? AND place_id=? AND revoked_at IS NULL AND expires_at>? AND ' + ('group_id=?' if request.args.get('group') else 'group_id IS NULL') + ' ORDER BY rowid DESC'
    args = [request.args.get('from'), request.args.get('to'), location(c)['id'], now()] + ([request.args.get('group')] if request.args.get('group') else [])
    rows = c.execute(q, args).fetchall()
    if not rows: return jsonify(share=None, ticks=[])
    marks = ','.join('?' * len(rows))
    return jsonify(share=share_dict(c, rows[0]), ticks=[dict(x) for x in c.execute(f'SELECT day, plant_code, kind, ticked_at FROM sitter_ticks WHERE token IN ({marks}) ORDER BY ticked_at', [r['token'] for r in rows])])

@app.route(SHARE_PATH + '/<token>/sitter-sheet.js')
def share_sheet_js(token):
    c = db(); sitter_tables(c); share_known(c, token)
    return send_from_directory(app.static_folder, 'sitter-sheet.js', max_age=0)

def share_sheet_data(c, r):
    """The sheet a link shows: the days, group and place it was made for (1.48.0 sites: the link holder sends no X-Place)."""
    with place_for(r['place_id']):
        return sitter_sheet(c, r['from_d'], r['to_d'], str(r['group_id']) if r['group_id'] else None, started=True)

# ---- what the link holder reaches: all under /share/<token>/, and nothing else
def share_page(token, status=200):
    with open(os.path.join(app.static_folder, 'share.html'), encoding='utf-8') as f: page = f.read()
    return Response(page.replace('__TOKEN__', token), status=status, mimetype='text/html', headers={'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex'})

@app.route(SHARE_PATH + '/<token>')
def share_sheet(token):
    """The page. A link taken down or expired still gets the page (with its status), so the reason reads in plain words there
    rather than as a bare error."""
    c = db(); sitter_tables(c)
    try: share_row(c, token)
    except HTTPException as e: return share_page(token, e.code)
    return share_page(token)

@app.route(SHARE_PATH + '/<token>/data')
def share_data(token):
    c = db(); sitter_tables(c)
    r = share_row(c, token)
    c.execute('UPDATE sitter_shares SET last_seen=? WHERE token=?', (now(), token)); c.commit()
    D = share_sheet_data(c, r)
    D['before'] = []                                                   # the owner's job, not the sitter's
    D['note'], D['photos'] = r['note'], bool(r['photos'])
    D['owner'] = owner_name(c)
    D['ticks'] = [dict(x) for x in c.execute('SELECT day, plant_code, kind, ticked_at FROM sitter_ticks WHERE token=?', (token,))]
    D['units'] = units_for(c, prefs_login(c))                          # the owner's units: the sitter has no sign-in
    for p in D['plants']:                                              # photos through this path only
        if p.get('photo'): p['photo'] = f'{SHARE_PATH}/{token}/photo/{p["photo"]}'
    return jsonify(D)

@app.route(SHARE_PATH + '/<token>/tick', methods=['POST'])
def share_tick(token):
    """{day, plant, kind, on}: a box ticked or unticked by the link holder."""
    c = db(); sitter_tables(c)
    r = share_row(c, token)
    b = request.get_json(silent=True) or {}
    day, code, kind, on = str(b.get('day', '')), str(b.get('plant', '')).strip().upper(), str(b.get('kind') or 'water'), bool(b.get('on'))
    if not (r['from_d'] <= day <= r['to_d']) or kind not in ('water', 'cold'): abort(400, 'That box is not on this sheet.')
    if not c.execute('SELECT 1 FROM plants WHERE code=?', (code,)).fetchone(): abort(400, 'That plant is not on this sheet.')
    if on: c.execute('INSERT OR REPLACE INTO sitter_ticks(token,day,plant_code,kind,ticked_at) VALUES(?,?,?,?,?)', (token, day, code, kind, now()))
    else: c.execute('DELETE FROM sitter_ticks WHERE token=? AND day=? AND plant_code=? AND kind=?', (token, day, code, kind))
    c.execute('UPDATE sitter_shares SET last_seen=? WHERE token=?', (now(), token)); c.commit()
    return jsonify(ok=True, on=on)

@app.route(SHARE_PATH + '/<token>/photo/<path:name>')
def share_photo(token, name):
    c = db(); sitter_tables(c)
    r = share_row(c, token)
    D = share_sheet_data(c, r)
    if os.path.basename(name) not in {p.get('photo') for p in D['plants'] + D.get('places', []) if p.get('photo')}: abort(404)
    return thumb(os.path.basename(name))

@app.route(SHARE_PATH + '/<token>/style.css')
def share_css(token):
    """The app's stylesheet, with its fonts pointed under the token (nothing outside /share/<token>/ answers a visitor)."""
    c = db(); sitter_tables(c); share_known(c, token)
    r = stylesheet()
    if r.status_code == 200:
        r.set_data(r.get_data(as_text=True).replace('url(/fonts/', f'url({SHARE_PATH}/{token}/fonts/'))
        r.headers['ETag'] = r.headers['ETag'].rstrip('"') + '-share"'
    return r

@app.route(SHARE_PATH + '/<token>/fonts/<name>')
def share_font(token, name):
    c = db(); sitter_tables(c); share_known(c, token)
    if not re.fullmatch(r'[a-z0-9-]+\.woff2', name): abort(404)
    return send_from_directory(os.path.join(app.static_folder, 'fonts'), name, max_age=86400)

@app.route(SHARE_PATH + '/<token>/share.js')
def share_js(token):
    c = db(); sitter_tables(c); share_known(c, token)
    return send_from_directory(app.static_folder, 'share.js', max_age=0)
