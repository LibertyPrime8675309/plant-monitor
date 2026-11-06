"""Offline use on phones and tablets, and changes sent later.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- 1.24.0: offline use on phones and tablets, and sending changes later
# The page (app.js) keeps changes made without a connection in an outbox on the device, and sends each one later as the request it
# would have made, with X-Offline-Op (a unique id for that change), X-Offline-Made (when it was made) and X-Offline-Device. The
# server answers each id once and keeps the answer in sync_ops, so a change that is sent twice (a dropped connection, a retry) is
# only made once. Edits carry base_values, the values the device saw: if someone else changed the record since, every field the
# device changed is still applied when the server's value is the one the device saw; when both changed the same field to
# different values, both are kept in sync_conflicts and the owner or an editor chooses on the "Needs your decision" page.
SYNC_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_ops(
  op TEXT PRIMARY KEY, method TEXT NOT NULL, path TEXT NOT NULL, status INTEGER NOT NULL, response TEXT, who TEXT, device TEXT,
  made_at TEXT, received_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sync_conflicts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, code TEXT NOT NULL, field TEXT NOT NULL, label TEXT NOT NULL,
  base TEXT, server_value TEXT, server_by TEXT, server_at TEXT, phone_value TEXT, phone_by TEXT, phone_made_at TEXT, device TEXT,
  created_at TEXT NOT NULL, resolved_at TEXT, resolved_by TEXT, choice TEXT);
"""
OFFLINE_PAGES = ['/api/meta', '/api/plants', '/api/plants?status=all', '/api/frost', '/api/groups', '/api/to-photograph', '/api/for-claude?range=last',
                 '/api/fertilizer', '/api/fertilizer/needs', '/api/fertilizer/products', '/api/outside', '/api/prep', '/api/requests?open=1', '/api/water',
                 '/api/weather', '/api/reference', '/api/weather/monthly', '/api/lights', '/api/current', '/api/settings', '/api/photos/unassigned',
                 '/api/identify/status', '/api/library/browse?scope=common&sort=known&offset=0&limit=48', '/api/library/facets?scope=common', '/api/library/notes',
                 '/api/library/settings', '/api/library/around', '/api/wishlist', '/api/wishlist/alerts', '/api/shops', '/api/fungi?status=active', '/api/fungi?status=all', '/api/fungi?status=archived',
                 '/api/fungi?status=none', '/api/conflicts?all=1']        # what the pages ask for (recorded by visiting each page)
OFFLINE_PLANT = ['/api/plants/{code}', '/api/care?n=12&plant={code}', '/api/fertilizer/needs?plant={code}', '/api/lights?plant={code}',
                 '/api/plants/{code}/history', '/api/plants/{code}/prep', '/api/plants/{code}/timeline', '/api/plants/{code}/qr.svg', '/api/facts?code={code}']
OFFLINE_FIND = ['/api/fungi/{code}']
OFFLINE_OP_RE = re.compile(r'^[A-Za-z0-9_-]{8,64}$')

def offline_op():
    op = request.headers.get('X-Offline-Op', '')
    return op if request.method not in ('GET', 'HEAD', 'OPTIONS') and OFFLINE_OP_RE.match(op) else None

def offline_replay():
    """The kept answer when this change was already made (called at the end of guard())."""
    op = offline_op()
    if not op: return None
    c = db()
    # claim the id first (status 0), so two copies arriving at once can't both be made
    claimed = c.execute('INSERT OR IGNORE INTO sync_ops(op,method,path,status,received_at) VALUES(?,?,?,0,?)', (op, request.method, request.path[:300], now())).rowcount
    c.commit()
    if not claimed:
        r = c.execute('SELECT status, response FROM sync_ops WHERE op=?', (op,)).fetchone()
        if not r['status']: abort(503, 'This change is being made right now. It will be checked again shortly.')
        return Response(r['response'] or '{}', r['status'], mimetype='application/json', headers={'X-Offline-Replayed': '1'})
    g.offline_op = op
    return None

def offline_remember(resp):
    """Keeps the answer to a change sent with X-Offline-Op, so sending it again does not make it twice (after_request)."""
    op = g.get('offline_op')
    if not op: return resp
    try:
        c = db()
        if resp.status_code >= 500:                # not made: let it be sent again
            c.rollback(); c.execute('DELETE FROM sync_ops WHERE op=? AND status=0', (op,)); c.commit()
            return resp
        body = resp.get_data(as_text=True) if resp.mimetype == 'application/json' else '{}'
        c.execute('UPDATE sync_ops SET status=?, response=?, who=?, device=?, made_at=? WHERE op=?',
                  (resp.status_code, body[:200_000], editor(), request.headers.get('X-Offline-Device', '')[:60], request.headers.get('X-Offline-Made', '')[:40], op))
        c.commit()
    except Exception as e:
        problem_exc('offline', e, 'The answer to a change sent from a phone could not be kept')
    return resp

def same_value(a, b):
    """Two field values are the same when they read the same (None, '' and numbers written either way)."""
    if a is None: a = ''
    if b is None: b = ''
    if isinstance(a, (int, float)) or isinstance(b, (int, float)):
        try: return float(a) == float(b)
        except (TypeError, ValueError): pass
    return str(a).strip() == str(b).strip()

def merge_fields(c, kind, code, row, fields, base_values, label_of, norm_fn, last_change):
    """Splits a device's edit into the fields to apply and the clashes to keep for a decision. A field the device did not change
    (its new value is the one it saw) is left out; a field nobody else changed is applied; a field changed to the same value by
    both is left as it is."""
    apply, clashes = {}, []
    for n, v in fields.items():
        if n not in row.keys(): continue
        if n not in base_values: apply[n] = v; continue
        base, cur, new = base_values[n], row[n], norm_fn(n, v)
        if same_value(new, base): continue
        if same_value(cur, base): apply[n] = v
        elif same_value(cur, new): continue
        else: clashes.append((n, base, cur, new))
    who, at = last_change
    for n, base, cur, new in clashes:
        c.execute('INSERT INTO sync_conflicts(kind,code,field,label,base,server_value,server_by,server_at,phone_value,phone_by,phone_made_at,device,created_at) '
                  'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (kind, code, n, label_of(n), None if base is None else str(base), None if cur is None else str(cur), who, at,
                   None if new is None else str(new), editor(), request.headers.get('X-Offline-Made', '')[:40] or now(), request.headers.get('X-Offline-Device', '')[:60], now()))
        audit_only(c, 'sync', n, None if cur is None else str(cur)[:500], None if new is None else str(new)[:500], editor(),
                   f'{code}: {label_of(n)} was changed on {request.headers.get("X-Offline-Device") or "another device"} and here; waiting for a decision', None, code)
    return apply, len(clashes)

def conflict_dict(r):
    d = dict(r)
    d['open'] = r['resolved_at'] is None
    return d

@app.route('/api/conflicts')
def conflicts_list():
    c = db()
    rows = c.execute('SELECT * FROM sync_conflicts ' + ('WHERE resolved_at IS NULL ' if request.args.get('all') != '1' else '') + 'ORDER BY id DESC LIMIT 300').fetchall()
    return jsonify(conflicts=[conflict_dict(r) for r in rows], open=c.execute('SELECT COUNT(*) FROM sync_conflicts WHERE resolved_at IS NULL').fetchone()[0])

@app.route('/api/conflicts/<int:i>', methods=['POST'])
def conflict_decide(i):
    """Keeps one side of a clash: 'phone' writes the device's value now; 'server' keeps what the server has."""
    c = db()
    r = c.execute('SELECT * FROM sync_conflicts WHERE id=?', (i,)).fetchone()
    if not r: abort(404, 'That decision is not on the list')
    if r['resolved_at']: abort(409, 'That one was already decided by ' + (r['resolved_by'] or 'someone') + '.')
    choice = (request.get_json(silent=True) or {}).get('choice')
    if choice not in ('phone', 'server'): abort(400, 'choice must be phone or server')
    who = editor()
    if choice == 'phone':
        if r['kind'] == 'plant':
            p = plant_row(c, r['code'])
            apply_changes(c, p, {r['field']: r['phone_value'] or ''}, who, 'update', f"{FIELD_LABEL.get(r['field'], r['field'])}: kept the change made on {r['device'] or 'another device'}")
        elif r['kind'] == 'fungi':
            f = find_row(c, r['code'])
            v = fungi_norm(c, r['field'], r['phone_value'])
            c.execute(f"UPDATE fungi_finds SET {r['field']}=?, version=version+1, updated_by=?, updated_at=? WHERE id=?", (v, who, now(), f['id']))
            audit_only(c, 'fungi', r['field'], f[r['field']], v, who, f"{r['code']}: {r['label']}: kept the change made on {r['device'] or 'another device'}", None, r['code'])
    else:
        audit_only(c, 'sync', r['field'], r['phone_value'], r['server_value'], who, f"{r['code']}: {r['label']}: kept the value that was here", None, r['code'])
    c.execute('UPDATE sync_conflicts SET resolved_at=?, resolved_by=?, choice=? WHERE id=?', (now(), who, choice, i))
    c.commit()
    return jsonify(conflict_dict(c.execute('SELECT * FROM sync_conflicts WHERE id=?', (i,)).fetchone()))

@app.route('/api/offline/status')
def offline_status():
    """What a device needs to know when it comes back online (never kept by the service worker)."""
    c = db()
    return jsonify(version=APP_VERSION, conflicts=c.execute('SELECT COUNT(*) FROM sync_conflicts WHERE resolved_at IS NULL').fetchone()[0], now=now())

@app.route('/api/offline/manifest')
def offline_manifest():
    """Everything a device saves for offline use: the answers its pages ask for, and every photo (full size and thumbnail)."""
    c = db()
    codes = [r[0] for r in c.execute("SELECT code FROM plants ORDER BY code")]
    active = [r[0] for r in c.execute("SELECT code FROM plants WHERE status='active' ORDER BY code")]
    finds = [r[0] for r in c.execute('SELECT code FROM fungi_finds ORDER BY id')]
    groups = [r[0] for r in c.execute('SELECT id FROM plant_groups ORDER BY id')]
    urls = OFFLINE_PAGES + [u.format(code=urllib.parse.quote(x)) for x in codes for u in OFFLINE_PLANT] + \
        [u.format(code=urllib.parse.quote(x)) for x in finds for u in OFFLINE_FIND] + [f'/api/groups/{gid}' for gid in groups]
    names = sorted({r[0] for r in c.execute("SELECT scientific_name FROM plants WHERE status='active' AND scientific_name<>''")} |
                   {r[0] for r in c.execute("SELECT scientific_name FROM fungi_finds WHERE scientific_name<>''")} | {r[0] for r in c.execute('SELECT name FROM wishlist')})
    urls += [f'/api/library/taxon?name={urllib.parse.quote(n)}' for n in names]
    photos = [r[0] for r in c.execute('SELECT file FROM photos ORDER BY id')] + [r[0] for r in c.execute('SELECT file FROM fungi_photos ORDER BY id')]
    sizes = 0
    for f in photos:
        try: sizes += os.path.getsize(os.path.join(PHOTO_DIR, f))
        except OSError: pass
    return jsonify(urls=urls, photos=photos, photo_bytes=sizes, plants=len(active), finds=len(finds), version=APP_VERSION)

@app.route('/api/library/offline-index')
def library_offline_index():
    """Every species in the library's download areas (1.28.0; the Texas list before) in short (name, common name, family, kind,
    tags) and its kept photo, so the library can be searched and browsed on a device without a connection."""
    c = db()
    names = list(dict.fromkeys(n for r in c.execute('SELECT place_id FROM lib_areas') for n in area_names(r[0])))
    rows = []
    for i in range(0, len(names), 400):
        part = names[i:i + 400]; off = 0
        while True:
            r = vision_call('/browse', json.dumps({'scope': 'world', 'only': part, 'sort': 'known', 'offset': off, 'limit': 120}).encode(), 'application/json', timeout=60)
            rows += r.get('results', []); off += 120
            if off >= r.get('total', 0) or not r.get('results'): break
    mark_owned(c, rows); know_mark(c, rows)
    R = place_region(c, lib_place(c)) or {}
    out = []
    for x in rows:
        ph = lib_photo_state(x['scientific_name'])
        out.append({'n': x['scientific_name'], 'c': x.get('common_name') or '', 'f': x.get('family') or '', 'k': x.get('kind') or '', 'g': x.get('genus') or '',
                    'st': len(x.get('us_states') or []), 'tx': bool(R.get('usda') and R['usda'] in (x.get('us_states') or [])), 'y': x.get('yours') or [], 'w': x.get('wish'), 't': x.get('tags') or [],
                    'kn': x.get('know') or {}, 'p': ph['url'] if isinstance(ph, dict) else None})
    return jsonify(scope='areas', species=out, made=now(), areas=[r[0] for r in c.execute('SELECT name FROM lib_areas ORDER BY name')])

@app.route('/sw.js')
def service_worker():
    """1.24.0: the service worker, with the version in it so every update replaces the saved copy of the app."""
    with open(os.path.join(app.static_folder, 'sw.js'), encoding='utf-8') as f: js = f.read().replace('__VERSION__', APP_VERSION)
    return Response(js, mimetype='application/javascript', headers={'Cache-Control': 'no-cache', 'Service-Worker-Allowed': '/'})

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')
