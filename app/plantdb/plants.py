"""The plants themselves: the API, requests from Claude, Copy my answers, adding several at once, the timeline, photos, the to-photograph list, QR labels and export, and /api/meta.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- api: meta/reference
@app.route('/api/meta')
def meta():
    c = db()
    L = location(c)
    return jsonify(fields=[{'name': n, 'kind': k, 'label': l} for n, k, l in FIELDS], winter_plans=WINTER_PLANS, health=HEALTH, sites=SITES, inside_sites=INSIDE_SITES,
                   enums=ENUMS, optional_enums=OPTIONAL_ENUMS, pests=PESTS,
                   counts={'plants': c.execute("SELECT COUNT(*) FROM plants WHERE status='active'").fetchone()[0],
                           'photos': c.execute('SELECT COUNT(*) FROM photos').fetchone()[0]},
                   password_protected=bool(PASSWORD), int_ranges=INT_RANGES, num_ranges=NUM_RANGES, version=APP_VERSION,
                   home_tz=L['tz'],              # the browser uses this for "today", so dates match the server's
                   place=place_brief(L), climate=place_climate(c, L), zone=place_zone(c, L), heat=heat_brief(c, L), me=me_dict(c), runs_as=runs_as(), mirror=mirror_info(c),   # 1.37.0: mirror
                   places=[place_brief(loc_dict(r)) for r in c.execute('SELECT * FROM locations ORDER BY is_home DESC, name')],
                   homes=[place_brief(h) for h in homes(c)], region=place_region(c, L),
                   where=where_list(c),                                                      # 1.29.0: rooms and spots
                   containers=[{k: d[k] for k in ('id', 'kind', 'name', 'size', 'sqft', 'qty', 'free')} for d in (cont_dict(c, x) for x in c.execute('SELECT * FROM containers ORDER BY kind, name'))])

REF_PLACE = (30.5083, -97.6789)       # the written winter reference (climate table and notes) is for Round Rock, TX

@app.route('/api/reference')
def reference():
    """The written winter reference, plus (1.11.0) whether it is about the place in use, and that place's own monthly
    averages from its weather history when it has 3 years or more, so the Winter plan works for any place."""
    c = db()
    r = c.execute("SELECT value FROM settings WHERE key='reference'").fetchone()
    ref = json.loads(r[0]) if r else {}
    L = location(c)
    ref['applies'] = abs(L['lat'] - REF_PLACE[0]) < 0.5 and abs(L['lon'] - REF_PLACE[1]) < 0.5
    ref['place'] = place_brief(L)
    ref['normals'] = place_normals(c, L)
    return jsonify(ref)

PLACE_NORMALS = {}
def place_normals(c, L):
    """Average low, high, freezing nights and humidity for each month at a place, from its daily weather history."""
    hit = PLACE_NORMALS.get(L['id'])
    if hit and time.time() - hit[0] < 6 * 3600: return hit[1]
    out = None
    try:
        rows = c.execute("""SELECT CAST(substr(date, 6, 2) AS INTEGER) m, COUNT(DISTINCT substr(date, 1, 4)) years,
              AVG(json_extract(data, '$.temperature_2m_min')), AVG(json_extract(data, '$.temperature_2m_max')),
              SUM(CASE WHEN json_extract(data, '$.temperature_2m_min') <= 32 THEN 1 ELSE 0 END), AVG(json_extract(data, '$.relative_humidity_2m_mean'))
              FROM weather_daily WHERE loc_id=? AND kind='observed' GROUP BY m ORDER BY m""", (L['id'],)).fetchall()
        if len(rows) == 12 and min(r[1] for r in rows) >= 3:
            out = {'years': min(r[1] for r in rows), 'since': c.execute("SELECT MIN(date) FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],)).fetchone()[0],
                   'months': [{'month': MONTH_ABBR[r[0] - 1], 'low': round(r[2]) if r[2] is not None else None, 'high': round(r[3]) if r[3] is not None else None,
                               'freeze_nights': round(r[4] / r[1], 1), 'rh': round(r[5]) if r[5] is not None else None} for r in rows]}
    except sqlite3.OperationalError: out = None
    PLACE_NORMALS[L['id']] = (time.time(), out)
    return out
MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

@app.route('/api/settings', methods=['GET', 'PUT'])
def settings():
    c = db()
    if request.method == 'PUT':
        base = str((request.get_json(silent=True) or {}).get('base_url', '')).strip().rstrip('/')
        if base and not re.match(r'^https?://[\w.\-]+(:\d+)?$', base): abort(400, 'Base URL must look like http://192.168.1.20:8080')
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('base_url',?)", (base,))
        audit_only(c, 'setting', 'base_url', None, base, editor(), 'Label QR base URL changed')
        c.commit()
    r = c.execute("SELECT value FROM settings WHERE key='base_url'").fetchone()
    return jsonify(base_url=r[0] if r else '')

# ---------------------------------------------------------------- api: plants
@app.route('/api/plants')
def list_plants():
    c = db()
    q = request.args.get('q', '').strip().lower()
    status = request.args.get('status', 'active')          # 'active', 'archived', or 'all' (1.16.2: both, for the Status filter)
    rows = c.execute('SELECT * FROM plants ORDER BY code').fetchall() if status == 'all' else c.execute('SELECT * FROM plants WHERE status=? ORDER BY code', (status,)).fetchall()
    open_req = {k: n for k, n in c.execute('SELECT plant_code, COUNT(*) FROM requests WHERE done=0 AND plant_code IS NOT NULL GROUP BY plant_code')}
    spots = plant_spots(c)
    out = []
    for r in rows:
        hay = ' '.join(str(r[n] or '') for n in ('code', 'common_name', 'scientific_name', 'aliases', 'location', 'container', 'plant_type', 'notes')).lower()
        if q and q not in hay: continue
        files = [x[0] for x in c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id', (r['id'],))]
        p = {'file': files[0]} if files else None
        pn, pat = c.execute('SELECT COUNT(*), MAX(added_at) FROM photos WHERE plant_id=?', (r['id'],)).fetchone()
        out.append({'code': r['code'], 'common_name': r['common_name'], 'scientific_name': r['scientific_name'], 'plant_type': r['plant_type'],
                    'location': r['location'], 'aliases': r['aliases'], 'id_confidence': r['id_confidence'], 'winter_plan': r['winter_plan'], 'health_rating': r['health_rating'],
                    'site': r['site'] or 'Outdoors', 'version': r['version'], 'updated_at': r['updated_at'], 'updated_by': r['updated_by'], 'photo': p['file'] if p else None,
                    'temp_damage_below': r['temp_damage_below'], 'temp_ideal_low': r['temp_ideal_low'], 'temp_ideal_high': r['temp_ideal_high'],
                    'fert_from_month': r['fert_from_month'], 'fert_to_month': r['fert_to_month'], 'fert_every_days': r['fert_every_days'], 'fertilizer': r['fertilizer'],
                    'requests_open': open_req.get(r['code'], 0), 'status': r['status'],
                    # 1.17.0: for the filters on the Plants page
                    'dli_low': r['dli_low'], 'dli_high': r['dli_high'], 'zone_low': r['zone_low'], 'pet_safety': r['pet_safety'] or '',
                    'leaf_type': r['leaf_type'] or '', 'pot_size': r['pot_size'] or '', 'photo_count': pn, 'photo_at': pat,
                    'light_spot': spots.get(r['code']), 'home_id': r['home_id'], 'area_id': r['area_id'], 'spot_id': r['spot_id'],   # 1.34.0: room and shelf labels
                    'photos': files})                      # 1.20.0: every photo, main photo first, to browse on the Plants page
    return jsonify(out)

@app.route('/api/plants/<code>')
def get_plant(code):
    c = db()
    r = plant_row(c, code)
    p = plant_dict(c, r)
    if request.args.get('fill') == '1': species_fill(c, p)        # 1.53.0: the plant's page reads the species' facts for what the plant leaves empty (not the edit form)
    return jsonify(p | {'requests': [dict(x) for x in c.execute('SELECT * FROM requests WHERE plant_code=? ORDER BY done, id', (r['code'],))]})

# ---------------------------------------------------------------- requests: what Claude needs from you
REQUEST_KINDS = ('check', 'question', 'photo', 'info')

@app.route('/api/requests', methods=['GET', 'POST'])
def requests_list():
    c = db()
    if request.method == 'POST':
        b = request.get_json(silent=True) or {}
        text = str(b.get('text', '')).strip()[:1000]
        if not text: abort(400, 'Write what is needed')
        code = (b.get('plant_code') or '').strip() or None
        if code: plant_row(c, code)
        kind = b.get('kind') if b.get('kind') in REQUEST_KINDS else 'question'
        rid = c.execute('INSERT INTO requests(plant_code,kind,text,created_by,created_at) VALUES(?,?,?,?,?)', (code, kind, text, editor(), now())).lastrowid
        audit_only(c, 'request', 'request', None, text, editor(), 'Request added', None, code)
        c.commit()
        return jsonify(dict(c.execute('SELECT * FROM requests WHERE id=?', (rid,)).fetchone())), 201
    q, a = 'SELECT * FROM requests', []
    if request.args.get('open') == '1': q += ' WHERE done=0'
    return jsonify([dict(r) for r in c.execute(q + ' ORDER BY done, plant_code IS NULL, plant_code, id', a)])

@app.route('/api/requests/<int:rid>', methods=['PUT'])
def request_one(rid):
    c = db()
    r = c.execute('SELECT * FROM requests WHERE id=?', (rid,)).fetchone()
    if not r: abort(404, 'request not found')
    b = request.get_json(silent=True) or {}
    done = 1 if b.get('done', True) else 0
    answer = str(b.get('answer', '') or '').strip()[:2000] or None
    c.execute('UPDATE requests SET done=?, answer=COALESCE(?, answer), done_by=?, done_at=? WHERE id=?',
              (done, answer, editor() if done else None, now() if done else None, rid))
    pr = c.execute('SELECT id FROM plants WHERE code=?', (r['plant_code'],)).fetchone() if r['plant_code'] else None
    audit_only(c, 'request', 'request', r['text'], (answer or 'Done') if done else 'Reopened', editor(),
               ('Request answered' if answer else 'Request marked done') if done else 'Request reopened', pr['id'] if pr else None, r['plant_code'])
    c.commit()
    return jsonify(dict(c.execute('SELECT * FROM requests WHERE id=?', (rid,)).fetchone()))

# ---------------------------------------------------------------- copy my answers for Claude (added in 1.8.0)
FC_KEY = 'claude_copied_at'                       # settings: when the message was last copied or saved
FC_EPOCH = '1970-01-01T00:00:00Z'
FC_PAGE = ('create', 'update', 'edit', 'restore', 'archive', 'unarchive')
FC_PHOTO = ('photo_add', 'photo_assign', 'photo_move', 'photo_remove', 'photo_caption', 'photo_primary')
FC_CARE = ('fertilizer', 'care', 'frost')         # care and frost come from the watering and frost prototypes, if merged

def fc_person(who):
    """Changes made by people. Upgrade batches and the first import are signed "Claude (...)" and Claude knows those."""
    return not (who or '').startswith('Claude')

def fc_when(c, ts, with_time=True):
    """'2026-10-23T20:40:00Z' -> 'Friday, Oct 23, 3:40 PM', in the home place's time zone."""
    d = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(tzinfo(location(c)['tz']))
    day = f'{d:%A}, {d:%b} {d.day}'
    return day + f', {d.hour % 12 or 12}:{d:%M} {"AM" if d.hour < 12 else "PM"}' if with_time else day

def fc_clip(v, n=300):
    v = re.sub(r'\s+', ' ', str(v if v is not None else '')).strip()
    return v if len(v) <= n else v[:n - 1].rstrip() + '…'

def fc_since(c, rng):
    if rng in ('7', '30'): return (datetime.now(timezone.utc) - timedelta(days=int(rng))).strftime('%Y-%m-%dT%H:%M:%SZ')
    if rng == 'all': return FC_EPOCH
    return setting(c, FC_KEY) or FC_EPOCH        # 'last': since it was last copied, or everything the first time

def for_claude_message(c, since, until, with_open=False):
    """The message to paste into the chat: what people did since `since` (answers first), as plain text."""
    names = {r['code']: r['common_name'] for r in c.execute('SELECT code, common_name FROM plants')}
    nm = lambda code: f'{code} {names.get(code, "")}'.strip() if code else 'General'
    cap = {r['file']: r['caption'] for r in c.execute('SELECT file, caption FROM photos')}
    out, n = [], {'answers': 0, 'pages': 0, 'photos': 0, 'care': 0, 'todo': 0}

    ans = [r for r in c.execute('SELECT * FROM requests WHERE done=1 AND done_at > ? AND done_at <= ? ORDER BY plant_code IS NULL, plant_code, done_at',
                                (since, until)) if fc_person(r['done_by'])]
    if ans:
        n['answers'] = len(ans)
        out.append(f'Answers ({len(ans)}):')
        for r in ans:
            out += [f'- {nm(r["plant_code"])} ({fc_when(c, r["done_at"])})', f'  Asked: {fc_clip(r["text"], 800)}',
                    f'  Answer: {fc_clip(r["answer"], 2000)}' if r['answer'] and r['answer'] != 'Done' else '  Marked done, with no answer written.']
        out.append('')

    log = [a for a in c.execute('SELECT * FROM audit_log WHERE changed_at > ? AND changed_at <= ? ORDER BY id', (since, until)) if fc_person(a['changed_by'])]

    pages = {}                                     # one entry per save: same plant, time, note and action
    for a in log:
        if a['action'] in FC_PAGE and a['plant_code']: pages.setdefault((a['plant_code'], a['changed_at'], a['note'] or '', a['action']), []).append(a)
    if pages:
        n['pages'] = len(pages)
        out.append(f'Changes to plant pages ({len(pages)}):')
        for (code, ts, note, act), rows in pages.items():
            if act == 'create': out.append(f'- New page: {nm(code)} ({fc_when(c, ts)})'); continue
            out.append(f'- {nm(code)} ({fc_when(c, ts)})' + (f': {fc_clip(note, 300)}' if note else ''))
            for a in rows:
                if not a['field']: continue
                label = FIELD_LABEL.get(a['field']) or a['field'].replace('_', ' ').capitalize()
                old, new = fc_clip(a['old_value'], 1000), fc_clip(a['new_value'], 1000)
                if len(old) <= 60 and len(new) <= 60: out.append(f'  {label}: from {old or "(empty)"} to {new or "(empty)"}')
                else: out.append(f'  {label}, now: {new or "(empty)"}')
        out.append('')

    ph = {}                                        # per plant (None = the Photos page, no plant)
    for a in log:
        if a['action'] not in FC_PHOTO: continue
        p = ph.setdefault(a['plant_code'], {'added': [], 'in': [], 'out': [], 'removed': 0, 'captions': 0, 'main': 0})
        if a['action'] == 'photo_add': p['added'].append(a['new_value'])
        elif a['action'] == 'photo_assign': p['in'].append((a['old_value'] or '').replace('from ', '', 1))
        elif a['action'] == 'photo_move': p['out'].append((a['new_value'] or '').replace('moved to ', '', 1))
        elif a['action'] == 'photo_remove': p['removed'] += 1
        elif a['action'] == 'photo_caption': p['captions'] += 1
        elif a['action'] == 'photo_primary': p['main'] += 1
    if ph:
        n['photos'] = len(ph)
        out.append('Photos:')
        for code, p in sorted(ph.items(), key=lambda x: (x[0] is None, x[0] or '')):
            bits = []
            if p['added']:
                caps = [f'"{fc_clip(cap.get(f), 80)}"' for f in p['added'] if cap.get(f)]
                bits.append(f'{len(p["added"])} photo{"s" if len(p["added"]) > 1 else ""} ' + ('uploaded without a plant' if code is None else 'added')
                            + (f' ({", ".join(caps[:6])})' if caps else ''))
            if p['in']: bits.append(f'{len(p["in"])} moved here from ' + ', '.join(sorted(set(x if x.startswith('P-') else 'the Photos page' for x in p['in']))))
            if p['out']: bits.append(f'{len(p["out"])} moved to ' + ', '.join(sorted(set(x if x.startswith('P-') else 'the Photos page' for x in p['out']))))
            if p['removed']: bits.append(f'{p["removed"]} removed')
            if p['captions']: bits.append(f'{p["captions"]} caption{"s" if p["captions"] > 1 else ""} edited')
            if p['main']: bits.append('main photo changed')
            out.append(f'- {"Photos page" if code is None else nm(code)}: ' + '; '.join(bits))
        if any(p['added'] for p in ph.values()):
            out.append("  The photos themselves can't go in this message. Attach the ones you want me to look at, or send a backup made with photos.")
        out.append('')

    care = {}                                      # same note on the same day for several plants reads as one line
    for a in log:
        if a['action'] in FC_CARE: care.setdefault((fc_when(c, a['changed_at'], False), a['note'] or a['action']), []).append(a['plant_code'])
    if care:
        n['care'] = sum(len(v) for v in care.values())
        out.append('Feeding and care:')
        for (day, note), codes in care.items():
            codes = sorted(set(x for x in codes if x))
            who = ', '.join(nm(x) for x in codes) if len(codes) <= 3 else ', '.join(codes)
            out.append(f'- {day}: {fc_clip(note, 300)}' + (f' ({who})' if who else ''))
        out.append('')

    todo = [a for a in log if a['action'] == 'todo']
    if todo:
        n['todo'] = len(todo)
        out.append('"Still to photograph" list:')
        out += [f'- {fc_clip(a["note"], 300)}' for a in todo]
        out.append('')

    open_req = c.execute('SELECT * FROM requests WHERE done=0 ORDER BY plant_code IS NULL, plant_code, id').fetchall()
    open_todo = c.execute('SELECT * FROM to_photograph WHERE done=0 ORDER BY id').fetchall()
    if with_open and (open_req or open_todo):
        out.append(f'Still open ({len(open_req)} requests, {len(open_todo)} to photograph):')
        out += [f'- {nm(r["plant_code"])}: {fc_clip(r["text"], 300)}' for r in open_req]
        out += [f'- To photograph: {fc_clip(t["label"], 200)}' + (f' ({fc_clip(t["note"], 200)})' if t['note'] else '') for t in open_todo]
        out.append('')
    elif open_req or open_todo:
        out.append(f'Still open: {len(open_req)} request{"" if len(open_req) == 1 else "s"} and {len(open_todo)} thing{"" if len(open_todo) == 1 else "s"} to photograph.')
        out.append('')

    span = 'everything so far' if since == FC_EPOCH else f'{fc_when(c, since)} to {fc_when(c, until)}'
    head = [f'Plant record update for Claude (version {APP_VERSION})', f'Covers {span}.', '']
    if not any(n.values()): head.append('Nothing new from me in that time.\n')
    return '\n'.join(head + out).rstrip() + '\n', n, {'requests': len(open_req), 'todo': len(open_todo)}

@app.route('/api/for-claude')
def for_claude():
    c = db()
    rng = request.args.get('range', 'last')
    if rng not in ('last', '7', '30', 'all'): abort(400, "range must be last, 7, 30 or all")
    since, until, last = fc_since(c, rng), now(), setting(c, FC_KEY)
    text, counts, still = for_claude_message(c, since, until, request.args.get('open') == '1')
    return jsonify(range=rng, since=since, until=until, last_copied=last, last_copied_words=fc_when(c, last) if last else None,
                   text=text, counts=counts, still_open=still)

@app.route('/api/for-claude.txt')
def for_claude_txt():
    c = db()
    rng = request.args.get('range', 'last')
    if rng not in ('last', '7', '30', 'all'): abort(400, "range must be last, 7, 30 or all")
    text = for_claude_message(c, fc_since(c, rng), now(), request.args.get('open') == '1')[0]
    name = 'plant-record-for-claude-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M') + '.txt'
    return Response(text, mimetype='text/plain; charset=utf-8', headers={'Content-Disposition': f'attachment; filename={name}'})

@app.route('/api/for-claude/copied', methods=['POST'])
def for_claude_copied():
    """Remember that the message up to `until` has been copied or saved, so next time starts from there."""
    c = db()
    until = str((request.get_json(silent=True) or {}).get('until') or now())
    if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', until) or until > now(): abort(400, 'until must be a time that has passed, like 2026-10-23T20:40:00Z')
    old = setting(c, FC_KEY)
    if not old or until > old:
        set_setting(c, FC_KEY, until)
        audit_only(c, 'setting', FC_KEY, old, until, editor(), 'Copied my answers for Claude')
        c.commit()
    return jsonify(last_copied=setting(c, FC_KEY), last_copied_words=fc_when(c, setting(c, FC_KEY)))

@app.route('/api/plants', methods=['POST'])
def create_plant():
    c = db()
    body = request.get_json(silent=True) or {}
    f = body.get('fields', {})
    if not str(f.get('common_name', '')).strip(): abort(400, 'Common name is required')
    n = c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(code,3) AS INTEGER)),0)+1 FROM plants").fetchone()[0]
    code, who, ts = f'P-{n:03d}', editor(), now()
    f = dict(f)
    f['winter_plan'] = f.get('winter_plan') or 'Move indoors'
    f['health_rating'] = f.get('health_rating') or 'Fair'
    f['site'] = f.get('site') or 'Outdoors'
    f = place_sync(c, None, f)                                 # 1.29.0: the area and spot go with the Location
    vals = {k: norm(k, f.get(k)) for k in FIELD_NAMES}
    cols = ['code'] + FIELD_NAMES + ['version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by']
    cur = c.execute(f"INSERT INTO plants({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                    [code] + [vals[k] for k in FIELD_NAMES] + [1, 'active', ts, who, ts, who])
    pid = cur.lastrowid
    c.execute('INSERT INTO plant_versions(plant_id,version,snapshot,changed_by,changed_at,summary) VALUES(?,?,?,?,?,?)',
              (pid, 1, json.dumps(snapshot(c, pid)), who, ts, 'Record created'))
    audit_only(c, 'create', None, None, None, who, 'Record created', pid, code)
    c.execute('UPDATE audit_log SET version=1 WHERE plant_id=? AND action=?', (pid, 'create'))
    c.commit()
    return jsonify(plant_dict(c, plant_row(c, code))), 201

# ---------------------------------------------------------------- 1.28.0: add several plants at once, from photos
# Each photo is sent on its own: it is kept in photos/pending (not yet in the record), checked by the picture checker, and its
# date taken (from the photo) comes back so the page can group photos of one plant. Nothing is added until the review is saved;
# pending photos left behind are deleted after two days.
PENDING_DIR = os.path.join(PHOTO_DIR, 'pending')

def pending_tidy():
    try:
        for f in os.listdir(PENDING_DIR):
            p = os.path.join(PENDING_DIR, f)
            if time.time() - os.path.getmtime(p) > 2 * 86400: os.remove(p)
    except OSError: pass

def photo_taken(im):
    try:
        ex = im.getexif(); v = ex.get_ifd(0x8769).get(36867) or ex.get(306)        # DateTimeOriginal, else DateTime
        return datetime.strptime(str(v).strip()[:19], '%Y:%m:%d %H:%M:%S').isoformat() if v else None
    except Exception: return None

def pets_word(name):
    """ASPCA's answer for a species as the Safety for pets field (1.17.0's words), or '' when they do not list it."""
    p = pets_for(name or '')
    if not p: return ''
    if 'toxic' in (p.get('dogs'), p.get('cats')): return PET_SAFETY[0]
    if p.get('dogs') == 'non-toxic' and p.get('cats') == 'non-toxic': return PET_SAFETY[3]
    return ''

@app.route('/api/plants/several/photo', methods=['POST'])
def several_photo():
    c = db()
    f = request.files.get('image')
    if not f: abort(400, 'Send a picture')
    raw = f.read(30_000_000)
    try:
        im0 = Image.open(io.BytesIO(raw)); taken = photo_taken(im0)
        im = ImageOps.exif_transpose(im0).convert('RGB')
    except Exception: abort(400, f'{f.filename or "That file"} is not a picture this can read (use JPG or PNG)')
    os.makedirs(PENDING_DIR, exist_ok=True); pending_tidy()
    keep = im.copy(); keep.thumbnail((1600, 1600))
    name = f'up_{uuid.uuid4().hex[:16]}.jpg'
    keep.save(os.path.join(PENDING_DIR, name), 'JPEG', quality=84, optimize=True)
    small = im.copy(); small.thumbnail((1024, 1024)); b = io.BytesIO(); small.save(b, 'JPEG', quality=88)
    out = {'file': name, 'taken': taken, 'name': (f.filename or '')[:120], 'species': [], 'matches': [], 'error': None}
    try:                                            # 1.40.0: the same identifier as the Identify page (one picture here; the plant's photos together after sorting)
        r = identify_pictures(c, [b.getvalue()], vscope(c, request.args.get('scope', 'common')), plantnet='no', n=5, mode=id_mode())
        out['species'] = [sev_species(x) for x in r.get('species') or []]
        out['matches'] = [m for m in r.get('matches') or [] if m.get('confidence') and m['confidence'] >= 0.6][:3]
        out['likely_new'] = r.get('likely_new')
    except Exception as e:
        out['error'] = getattr(e, 'description', None) or 'The picture checker could not look at it.'
    return jsonify(out)

def sev_species(x):
    return {k: x.get(k) for k in ('scientific_name', 'common_name', 'family', 'genus', 'order', 'kind', 'probability', 'sources', 'plantnet_probability', 'basis_words', 'yours', 'yours_genus', 'us_states', 'in_texas', 'kingdom')} | {'pets': pets_word(x.get('scientific_name'))}

@app.route('/api/plants/several/identify', methods=['POST'])
def several_identify():
    """1.40.0: {photos: [pending file names], exclude: [names], exclude_genera: [genera], plantnet: 'auto'|'yes'|'no'} -> the names for one
    plant from all its photos together, Pl@ntNet included when its key is saved, with the likeliest genus and family."""
    c = db()
    b = request.get_json(silent=True) or {}
    pics = []
    for ph in (b.get('photos') or [])[:6]:
        if not re.match(r'^up_[0-9a-f]{16}\.jpg$', str(ph)): abort(400, 'That photo is not waiting here')
        path = os.path.join(PENDING_DIR, ph)
        if not os.path.exists(path): abort(400, 'A photo is no longer waiting here (they are kept for two days). Add the photos again.')
        with open(path, 'rb') as f: pics.append(f.read())
    if not pics: abort(400, 'Choose at least one photo')
    r = identify_pictures(c, pics, vscope(c, request.args.get('scope', 'common')), exclude=b.get('exclude') or [], exclude_genera=b.get('exclude_genera') or [],
                          plantnet=b.get('plantnet') or 'auto', n=10, mode=id_mode())
    r['species'] = [sev_species(x) for x in r['species']]
    r['matches'] = [m for m in r['matches'] if m.get('confidence') and m['confidence'] >= 0.6][:3]
    return jsonify(r)

@app.route('/api/plants/several', methods=['POST'])
def several_create():
    """{plants: [{fields: {...}, photos: [pending file names, main photo first]}]} -> the new plants, all added together."""
    c = db()
    b = request.get_json(silent=True) or {}
    items = b.get('plants') or []
    if not items: abort(400, 'There are no plants to add')
    if len(items) > 200: abort(400, 'Add at most 200 plants at a time')
    shared = [str(x) for x in (b.get('shared') or [])][:20]           # 1.38.0: wide shots of several plants together: a copy goes on every plant
    for ph in shared:
        if not re.match(r'^up_[0-9a-f]{16}\.jpg$', ph) or not os.path.exists(os.path.join(PENDING_DIR, ph)):
            abort(400, 'A photo marked "Shows all of them" is no longer waiting here (they are kept for two days). Add the photos again.')
    who, ts, made = editor(), now(), []
    for i, it in enumerate(items):
        f = dict(it.get('fields') or {})
        if not str(f.get('common_name', '')).strip(): abort(400, f'Plant {i + 1} needs a common name')
        for ph in it.get('photos') or []:
            if not re.match(r'^up_[0-9a-f]{16}\.jpg$', str(ph)) or not os.path.exists(os.path.join(PENDING_DIR, ph)):
                abort(400, f'A photo for plant {i + 1} is no longer waiting here (they are kept for two days). Add the photos again.')
        f['winter_plan'] = f.get('winter_plan') or 'Move indoors'
        f['health_rating'] = f.get('health_rating') or 'Fair'
        f['site'] = f.get('site') or 'Outdoors'
        if not f.get('pet_safety'): f['pet_safety'] = pets_word(f.get('scientific_name'))
        f = place_sync(c, None, f)
        items[i] = (it, {k: norm(k, f.get(k)) for k in FIELD_NAMES})        # every plant is checked before any is added
    cols = ['code'] + FIELD_NAMES + ['version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by']
    for it, vals in items:
        n = c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(code,3) AS INTEGER)),0)+1 FROM plants").fetchone()[0]
        code = f'P-{n:03d}'
        pid = c.execute(f"INSERT INTO plants({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                        [code] + [vals[k] for k in FIELD_NAMES] + [1, 'active', ts, who, ts, who]).lastrowid
        own = list(it.get('photos') or [])
        for j, ph in enumerate(own):
            os.replace(os.path.join(PENDING_DIR, ph), os.path.join(PHOTO_DIR, ph))
            c.execute('INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(?,?,?,?,?,?,?,?)',
                      (pid, ph, '', 'plant', 1 if j == 0 else 0, ph, who, ts))
        for j, ph in enumerate(shared):
            name = f'up_{uuid.uuid4().hex[:16]}.jpg'
            shutil.copyfile(os.path.join(PENDING_DIR, ph), os.path.join(PHOTO_DIR, name))
            c.execute('INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(?,?,?,?,?,?,?,?)',
                      (pid, name, 'Several plants together', 'plant', 1 if not own and j == 0 else 0, ph, who, ts))
        c.execute('INSERT INTO plant_versions(plant_id,version,snapshot,changed_by,changed_at,summary) VALUES(?,?,?,?,?,?)',
                  (pid, 1, json.dumps(snapshot(c, pid)), who, ts, 'Record created (added with several others from photos)'))
        audit_only(c, 'create', None, None, None, who, 'Record created (added with several others from photos)', pid, code)
        c.execute('UPDATE audit_log SET version=1 WHERE plant_id=? AND action=?', (pid, 'create'))
        made.append(code)
    for ph in shared:
        try: os.remove(os.path.join(PENDING_DIR, ph))
        except OSError: pass
    c.commit()
    return jsonify(codes=made), 201

@app.route('/api/plants/<code>/identify', methods=['POST'])
def plant_identify(code):
    """1.40.0: the names for a plant from its own photos (newest six, main photo first), with the plant's own "Not this" list applied.
    {plantnet: 'auto'|'yes'|'no'}"""
    c = db()
    r = plant_row(c, code)
    b = request.get_json(silent=True) or {}
    files = [x[0] for x in c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC, id DESC LIMIT 6', (r['id'],))]
    pics = []
    for f in files:
        path = os.path.join(PHOTO_DIR, f)
        if os.path.exists(path):
            with open(path, 'rb') as fh: pics.append(fh.read())
    if not pics: abort(400, 'This plant has no photos to check')
    out = identify_pictures(c, pics, vscope(c, request.args.get('scope', 'common')), plant_code=code, plantnet=b.get('plantnet') or 'auto', n=10, mode=id_mode())
    out['matches'] = [m for m in out['matches'] if m['code'] != code]          # its own photos are not a find
    return jsonify(out)

@app.route('/api/plants/<code>', methods=['PUT'])
def update_plant(code):
    c = db()
    r = plant_row(c, code)
    body = request.get_json(silent=True) or {}
    nclash = 0
    if int(body.get('base_version', -1)) != r['version']:
        if not isinstance(body.get('base_values'), dict):
            return jsonify(error='This page was changed by someone else since you opened it. Reload to see version %d.' % r['version'],
                           current=plant_dict(c, r)), 409
        # 1.24.0: a change from a device that saw an older version: merge it field by field
        body['fields'], nclash = merge_fields(c, 'plant', r['code'], r, body.get('fields') or {}, body['base_values'], lambda n: FIELD_LABEL.get(n, n),
                                              lambda n, v: norm(n, v) if n in FIELD_KIND else v, (r['updated_by'], r['updated_at']))
    if 'common_name' in body.get('fields', {}) and not str(body['fields']['common_name']).strip(): abort(400, 'Common name is required')
    ver, changed = apply_changes(c, r, body.get('fields', {}), editor(), 'update', (body.get('note') or '').strip()[:300])
    c.commit()
    return jsonify(plant_dict(c, plant_row(c, code)) | {'changed': changed, 'conflicts': nclash})

@app.route('/api/plants/<code>/site', methods=['POST'])
def plant_site(code):
    """Change only where the plant is (Outdoors, Indoors...). No version check: one field, chosen from a list."""
    c = db()
    r = plant_row(c, code)
    site = str((request.get_json(silent=True) or {}).get('site', ''))
    if site not in SITES: abort(400, 'Location must be one of: ' + ', '.join(SITES))
    apply_changes(c, r, {'site': site}, editor(), 'update', ('Moved ' + site.lower()) if site in ('Indoors', 'Outdoors') else 'Moved to ' + site.lower())
    c.commit()
    return jsonify(plant_dict(c, plant_row(c, code)))

@app.route('/api/plants/<code>/status', methods=['POST'])
def plant_status(code):
    c = db()
    r = plant_row(c, code)
    new = 'archived' if (request.get_json(silent=True) or {}).get('archived') else 'active'
    if new != r['status']:
        c.execute('UPDATE plants SET status=? WHERE id=?', (new, r['id']))
        bump(c, r['id'], code, editor(), 'archive' if new == 'archived' else 'unarchive', 'Record ' + new, [('status', r['status'], new)])
        c.commit()
    return jsonify(plant_dict(c, plant_row(c, code)))

# ---------------------------------------------------------------- plant timeline (added in 1.8.0)
TL_KEY_FIELDS = ('common_name', 'health_rating', 'id_confidence', 'site', 'winter_plan')
TL_KIND = {'create': 'created', 'update': 'change', 'edit': 'change', 'restore': 'change', 'archive': 'change', 'unarchive': 'change',
           'photo_add': 'photo', 'photo_assign': 'photo', 'photo_remove': 'photo', 'photo_move': 'photo',
           'fertilizer': 'care', 'care': 'care', 'frost': 'care'}

def tl_title(a):
    """A plain title for one change-log row."""
    act, note = a['action'], a['note'] or ''
    if act == 'photo_assign':
        src = (a['old_value'] or '').replace('from ', '', 1)
        return 'Photo moved here from ' + src if src.startswith('P-') else 'Photo added from the Photos page'
    if act == 'photo_move' and note.endswith('moved away'):
        dst = (a['new_value'] or '').replace('moved to ', '', 1)
        return 'Photo moved to ' + dst if dst.startswith('P-') else 'Photo moved to the Photos page'
    return note or FIELD_LABEL.get(a['field'], a['field'] or 'Changed')

@app.route('/api/plants/<code>/timeline')
def plant_timeline(code):
    """One dated list for a plant, built from its change log and its answered requests: page changes (with the ones
    that matter picked out), photos, feedings and other care. Several fields saved together are one event."""
    c = db()
    r = plant_row(c, code)
    photos = {x['file']: dict(x) for x in c.execute('SELECT id, file, caption, added_at, is_primary FROM photos WHERE plant_id=?', (r['id'],))}
    events, by_key = [], {}
    for a in c.execute('SELECT * FROM audit_log WHERE plant_id=? ORDER BY id', (r['id'],)):
        kind = TL_KIND.get(a['action'])
        if not kind: continue
        key = (a['changed_at'], 'photos' if a['action'] == 'photo_add' else a['note'] or '', a['action'])
        e = by_key.get(key)
        if not e:
            e = {'at': a['changed_at'], 'kind': kind, 'action': a['action'], 'title': tl_title(a), 'by': a['changed_by'], 'changes': [], 'other': 0, 'photos': []}
            by_key[key] = e; events.append(e)
        if kind == 'photo':
            f = a['new_value'] or a['old_value']
            if f in photos and photos[f] not in e['photos']: e['photos'].append(photos[f])
        elif a['field'] in TL_KEY_FIELDS:
            e['changes'].append({'field': a['field'], 'label': FIELD_LABEL.get(a['field'], a['field']), 'old': a['old_value'], 'new': a['new_value']})
        elif kind == 'change' and a['field']:
            e['other'] += 1
    for q in c.execute('SELECT * FROM requests WHERE plant_code=? AND done=1 AND done_at IS NOT NULL', (r['code'],)):
        said = q['answer'] if q['answer'] and q['answer'] != 'Done' else None   # answered here or settled by an update
        events.append({'at': q['done_at'], 'kind': 'request', 'action': 'request', 'title': 'Request answered' if said else 'Request marked done',
                       'by': q['done_by'] or '', 'changes': [], 'other': 0, 'photos': [], 'question': q['text'], 'answer': said})
    events.sort(key=lambda e: e['at'] or '')
    for e in events:                                  # several photos added together read as one entry
        if e['action'] == 'photo_add' and len(e['photos']) > 1: e['title'] = f"{len(e['photos'])} photos added"
    seen = {x['file'] for e in events for x in e['photos']}
    rest = [x for x in photos.values() if x['file'] not in seen]
    if rest:                                          # photos that came with the page when it was created
        first = next((e for e in events if e['kind'] == 'created'), None)
        if first: first['photos'] = sorted(rest, key=lambda x: x['id'])
    health = [{'at': e['at'], 'old': ch['old'], 'new': ch['new']} for e in events for ch in e['changes'] if ch['field'] == 'health_rating']
    conf = [{'at': e['at'], 'old': ch['old'], 'new': ch['new']} for e in events for ch in e['changes'] if ch['field'] == 'id_confidence']
    events.reverse()
    return jsonify(code=r['code'], events=events, health=health, confidence=conf, current={'health': r['health_rating'], 'id_confidence': r['id_confidence']},
                   photos=sorted(photos.values(), key=lambda x: (x['added_at'] or '', x['id'])))

@app.route('/api/plants/<code>/history')
def history(code):
    c = db()
    r = plant_row(c, code)
    audit = [dict(x) for x in c.execute('SELECT * FROM audit_log WHERE plant_id=? ORDER BY id DESC', (r['id'],))]
    vers = [dict(x) for x in c.execute('SELECT version,changed_by,changed_at,summary FROM plant_versions WHERE plant_id=? ORDER BY version DESC', (r['id'],))]
    for a in audit: a['label'] = FIELD_LABEL.get(a['field'], a['field'])
    return jsonify(audit=audit, versions=vers, current=r['version'])

@app.route('/api/plants/<code>/versions/<int:n>')
def get_version(code, n):
    c = db()
    r = plant_row(c, code)
    v = c.execute('SELECT * FROM plant_versions WHERE plant_id=? AND version=?', (r['id'], n)).fetchone()
    if not v: abort(404, 'version not found')
    return jsonify(version=n, changed_by=v['changed_by'], changed_at=v['changed_at'], summary=v['summary'], snapshot=json.loads(v['snapshot']))

@app.route('/api/plants/<code>/restore/<int:n>', methods=['POST'])
def restore(code, n):
    c = db()
    r = plant_row(c, code)
    v = c.execute('SELECT snapshot FROM plant_versions WHERE plant_id=? AND version=?', (r['id'], n)).fetchone()
    if not v: abort(404, 'version not found')
    fields = json.loads(v['snapshot'])['fields']
    ver, changed = apply_changes(c, r, fields, editor(), 'restore', f'Restored text fields from version {n} (photos are not changed)')
    c.commit()
    return jsonify(plant_dict(c, plant_row(c, code)) | {'changed': changed})

# ---------------------------------------------------------------- photos
def save_image(file_storage):
    try:
        im = Image.open(file_storage.stream)
        im = ImageOps.exif_transpose(im).convert('RGB')        # re-encode: strips EXIF incl. GPS
    except Exception:
        abort(400, f'{file_storage.filename or "file"} is not a supported image (use JPG or PNG)')
    im.thumbnail((1600, 1600))
    name = f'up_{uuid.uuid4().hex[:16]}.jpg'
    im.save(os.path.join(PHOTO_DIR, name), 'JPEG', quality=84, optimize=True)
    return name

@app.route('/api/plants/<code>/photos', methods=['POST'])
def add_photos(code):
    c = db()
    r = plant_row(c, code)
    files = request.files.getlist('files')
    if not files: abort(400, 'no files')
    who, cap = editor(), request.form.get('caption', '').strip()[:200]
    has_primary = c.execute('SELECT 1 FROM photos WHERE plant_id=? AND is_primary=1', (r['id'],)).fetchone()
    changes = []
    for i, f in enumerate(files):
        name = save_image(f)
        prim = 0 if has_primary or i else 1
        c.execute('INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(?,?,?,?,?,?,?,?)',
                  (r['id'], name, cap or (f.filename or '')[:80], 'plant', prim, f.filename, who, now()))
        changes.append(('photo', None, name))
    bump(c, r['id'], code, who, 'photo_add', f'Added {len(files)} photo(s)', changes)
    c.commit()
    return jsonify(plant_dict(c, plant_row(c, code))), 201

@app.route('/api/photos', methods=['POST'])
def add_unassigned():
    c = db()
    files = request.files.getlist('files')
    if not files: abort(400, 'no files')
    who, cap = editor(), request.form.get('caption', '').strip()[:200]
    for f in files:
        name = save_image(f)
        c.execute('INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(NULL,?,?,?,0,?,?,?)',
                  (name, cap or (f.filename or '')[:80], 'other', f.filename, who, now()))
        audit_only(c, 'photo_add', 'photo', None, name, who, 'Unassigned photo uploaded')
    c.commit()
    return jsonify(ok=True), 201

@app.route('/api/photos/unassigned')
def unassigned():
    return jsonify([dict(r) for r in db().execute('SELECT id,file,caption,kind,added_by,added_at FROM photos WHERE plant_id IS NULL ORDER BY id')])

@app.route('/api/photos/<int:pid>', methods=['PATCH'])
def patch_photo(pid):
    c = db()
    ph = c.execute('SELECT * FROM photos WHERE id=?', (pid,)).fetchone()
    if not ph: abort(404, 'photo not found')
    body, who = request.get_json(silent=True) or {}, editor()
    owner = c.execute('SELECT * FROM plants WHERE id=?', (ph['plant_id'],)).fetchone() if ph['plant_id'] else None
    if 'plant_code' in body:                                   # assign / move
        tgt = c.execute('SELECT * FROM plants WHERE code=?', (body['plant_code'],)).fetchone() if body['plant_code'] else None
        if body['plant_code'] and not tgt: abort(404, 'target plant not found')
        old_code = owner['code'] if owner else None
        c.execute('UPDATE photos SET plant_id=?, is_primary=0, kind=? WHERE id=?', (tgt['id'] if tgt else None, 'plant' if tgt else 'other', pid))
        if owner: _fix_primary(c, owner['id']); bump(c, owner['id'], owner['code'], who, 'photo_move', f'Photo {ph["file"]} moved away', [('photo', ph['file'], f'moved to {body["plant_code"] or "unassigned"}')])
        if tgt: _fix_primary(c, tgt['id']); bump(c, tgt['id'], tgt['code'], who, 'photo_assign', f'Photo {ph["file"]} assigned', [('photo', f'from {old_code or "unassigned"}', ph['file'])])
        if not owner and not tgt: pass
    if 'caption' in body and str(body['caption']) != ph['caption']:
        c.execute('UPDATE photos SET caption=? WHERE id=?', (str(body['caption'])[:200], pid))
        if owner: bump(c, owner['id'], owner['code'], who, 'photo_caption', 'Photo caption edited', [('photo caption', ph['caption'], str(body['caption'])[:200])])
        else: audit_only(c, 'photo_caption', 'photo caption', ph['caption'], str(body['caption'])[:200], who, 'Unassigned photo caption edited')
    if body.get('is_primary') and owner:
        c.execute('UPDATE photos SET is_primary=0 WHERE plant_id=?', (owner['id'],))
        c.execute('UPDATE photos SET is_primary=1 WHERE id=?', (pid,))
        bump(c, owner['id'], owner['code'], who, 'photo_primary', 'Main photo changed', [('main photo', None, ph['file'])])
    c.commit()
    return jsonify(ok=True)

def _fix_primary(c, plant_id):
    if not c.execute('SELECT 1 FROM photos WHERE plant_id=? AND is_primary=1', (plant_id,)).fetchone():
        c.execute('UPDATE photos SET is_primary=1 WHERE id=(SELECT id FROM photos WHERE plant_id=? ORDER BY id LIMIT 1)', (plant_id,))

@app.route('/api/photos/<int:pid>', methods=['DELETE'])
def delete_photo(pid):
    c = db()
    ph = c.execute('SELECT * FROM photos WHERE id=?', (pid,)).fetchone()
    if not ph: abort(404, 'photo not found')
    who = editor()
    c.execute('DELETE FROM photos WHERE id=?', (pid,))
    if not c.execute('SELECT 1 FROM photos WHERE file=?', (ph['file'],)).fetchone():       # keep file if another record shares it
        src = os.path.join(PHOTO_DIR, ph['file'])
        if os.path.exists(src): shutil.move(src, os.path.join(TRASH_DIR, ph['file']))
    if ph['plant_id']:
        o = c.execute('SELECT * FROM plants WHERE id=?', (ph['plant_id'],)).fetchone()
        _fix_primary(c, o['id'])
        bump(c, o['id'], o['code'], who, 'photo_remove', 'Photo removed (file kept in photos_deleted)', [('photo', ph['file'], None)])
    else:
        audit_only(c, 'photo_remove', 'photo', ph['file'], None, who, 'Unassigned photo removed')
    c.commit()
    return jsonify(ok=True)

@app.route('/photos/<path:name>')
def photo(name):
    return send_from_directory(PHOTO_DIR, name, max_age=3600)

@app.route('/thumbs/<path:name>')
def thumb(name):
    safe = os.path.basename(name)
    src, dst = os.path.join(PHOTO_DIR, safe), os.path.join(THUMB_DIR, safe)
    if not os.path.exists(src): abort(404)
    if not os.path.exists(dst):
        # 1.21.0: the short side is at least 640 px, so a wide photo cropped to fill a tall card (or shown whole) stays sharp on
        # high-resolution screens. Before, wide photos were 520 x 390 and blurry when cropped.
        im = ImageOps.exif_transpose(Image.open(src)); im = im.convert('RGB') if im.mode not in ('RGB', 'L') else im
        k = min(1.0, 640 / min(im.size), 1400 / max(im.size))
        if k < 1: im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        os.makedirs(THUMB_DIR, exist_ok=True)
        im.save(dst + '.tmp', 'JPEG', quality=82, optimize=True); os.replace(dst + '.tmp', dst)
    return send_from_directory(THUMB_DIR, safe, max_age=3600)

# ---------------------------------------------------------------- to-photograph list
@app.route('/api/to-photograph', methods=['GET', 'POST'])
def to_photograph():
    c = db()
    if request.method == 'POST':
        b = request.get_json(silent=True) or {}
        if not str(b.get('label', '')).strip(): abort(400, 'label required')
        c.execute('INSERT INTO to_photograph(label,note) VALUES(?,?)', (str(b['label']).strip()[:200], str(b.get('note', '') or '').strip()[:1000]))
        audit_only(c, 'todo', 'to_photograph', None, str(b['label']).strip()[:200], editor(), 'Added: ' + str(b['label']).strip()[:200])
        c.commit()
    return jsonify([dict(r) for r in c.execute('SELECT * FROM to_photograph ORDER BY done, id')])

@app.route('/api/to-photograph/<int:i>', methods=['PATCH', 'DELETE'])
def to_photograph_item(i):
    c = db()
    t = c.execute('SELECT * FROM to_photograph WHERE id=?', (i,)).fetchone()
    if request.method == 'DELETE':
        c.execute('DELETE FROM to_photograph WHERE id=?', (i,))
        if t: audit_only(c, 'todo', 'to_photograph', t['label'], None, editor(), 'Removed from the list: ' + t['label'])
    else:
        b = request.get_json(silent=True) or {}
        if 'done' in b:
            c.execute('UPDATE to_photograph SET done=? WHERE id=?', (1 if b.get('done') else 0, i))
            if t and bool(t['done']) != bool(b.get('done')):
                audit_only(c, 'todo', 'to_photograph', t['label'], 'done' if b.get('done') else 'open', editor(), ('Ticked off: ' if b.get('done') else 'Unticked: ') + t['label'])
        if 'label' in b:
            if not str(b['label']).strip(): abort(400, 'label required')
            c.execute('UPDATE to_photograph SET label=? WHERE id=?', (str(b['label']).strip()[:200], i))
        if 'note' in b: c.execute('UPDATE to_photograph SET note=? WHERE id=?', (str(b['note'] or '').strip()[:1000], i))
    c.commit()
    return jsonify(ok=True)

# ---------------------------------------------------------------- qr, export
@app.route('/api/plants/<code>/qr.svg')
def qr(code):
    c = db(); plant_row(c, code)
    base = request.args.get('base', '').rstrip('/') or request.host_url.rstrip('/')
    if not re.match(r'^https?://[\w.\-]+(:\d+)?$', base): abort(400, 'bad base url')
    buf = io.BytesIO()
    segno.make(f'{base}/#/plant/{code}', error='m').save(buf, kind='svg', scale=6, border=2, dark='#000', light='#fff', xmldecl=False, svgns=True)
    return Response(buf.getvalue(), mimetype='image/svg+xml')

@app.route('/api/export.json')
def export_json():
    c = db()
    data = {'exported_at': now(), 'plants': [plant_dict(c, r) for r in c.execute('SELECT * FROM plants ORDER BY code')],
            'unassigned_photos': [dict(r) for r in c.execute('SELECT * FROM photos WHERE plant_id IS NULL')],
            'audit_log': [dict(r) for r in c.execute('SELECT * FROM audit_log ORDER BY id')],
            'fertilizer_log': [dict(r) for r in c.execute('SELECT * FROM fertilizer_log ORDER BY applied_on, id')],
            'requests': [dict(r) for r in c.execute('SELECT * FROM requests ORDER BY id')],
            'weather_places': [loc_dict(r) for r in c.execute('SELECT * FROM locations ORDER BY id')],
            'mushroom_finds': [dict(r) for r in c.execute('SELECT * FROM fungi_finds ORDER BY id')],          # 5d (1.51.1)
            'mushroom_photos': [dict(r) for r in c.execute('SELECT * FROM fungi_photos ORDER BY id')]}
    return Response(json.dumps(data, indent=1), mimetype='application/json', headers={'Content-Disposition': 'attachment; filename=plants-export.json'})

def _csv_safe(v):
    s = '' if v is None else str(v)
    return "'" + s if s and s[0] in '=+-@\t\r' else s           # neutralise spreadsheet formulas

@app.route('/api/export.csv')
def export_csv():
    c = db()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(['code', 'version', 'status', 'updated_at', 'updated_by'] + FIELD_NAMES)
    for r in c.execute('SELECT * FROM plants ORDER BY code'):
        w.writerow([_csv_safe(r[k]) for k in ['code', 'version', 'status', 'updated_at', 'updated_by'] + FIELD_NAMES])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=plants.csv'})

@app.route('/api/readings.csv')
def export_readings():
    """All stored readings (online weather, sensor and typed-in) for spreadsheets. Optional ?source=weather|sensor|manual"""
    c = db()
    out = io.StringIO(); w = csv.writer(out)
    cols = ['ts', 'source', 'device'] + list(METRICS)
    w.writerow(['when_utc', 'source', 'device', 'temp_f', 'humidity_pct', 'par', 'lux', 'soil_moisture_pct', 'soil_temp_f', 'soil_ph'])
    q, a = 'SELECT * FROM readings', []
    if request.args.get('source'): q += ' WHERE source=?'; a.append(request.args['source'])
    for r in c.execute(q + ' ORDER BY ts', a):
        w.writerow([_csv_safe(r[k]) for k in cols])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=readings.csv'})

@app.route('/api/audit.csv')
def export_audit():
    c = db()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(['when_utc', 'plant', 'version', 'action', 'field', 'before', 'after', 'by', 'note'])
    sql, args = audit_query(c, request.args)                 # the Audit log page's filters, if any (all changes otherwise)
    if request.args.get('order') != 'desc': sql = sql.replace(' ORDER BY a.id DESC', ' ORDER BY a.id ASC')
    for r in c.execute(sql, args):
        w.writerow([_csv_safe(x) for x in (r['changed_at'], r['plant_code'], r['version'], r['action'], audit_label(r['field']), r['old_value'], r['new_value'], r['changed_by'], r['note'])])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=audit-log.csv'})
