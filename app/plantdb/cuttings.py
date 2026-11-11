"""Prototype (proto/cuttings): cuttings and new plants. Keep track of cuttings, divisions and offsets taken from your plants, from
the day you take them until they have roots and are potted up (or given away, or did not take).

Each batch of cuttings is one row: the plant it came from, the day it was taken, how (stem cuttings, leaf cuttings, division ...),
what it is rooting in (water, moss, soil mix ...), how many pieces, and where it is up to: rooting, has roots, potted up, given
away, or did not take. A cutting still rooting, or rooted and waiting for a pot, is due a look once a week; "No roots yet" (or
"Not yet") records that look, so it drops off Today for another week.

Stored in its own table, cuttings, created here when the module first needs it (CREATE TABLE IF NOT EXISTS), so an existing
database is upgraded in place and init_db() does not need to know about it. A removed batch only gets removed_at, so the audit log
still makes sense. Cuttings follow the plant they came from to its home."""
from .core import *   # noqa: F401,F403

CUT_SCHEMA = """
CREATE TABLE IF NOT EXISTS cuttings(
  id INTEGER PRIMARY KEY AUTOINCREMENT, parent_code TEXT NOT NULL, started_on TEXT NOT NULL, method TEXT NOT NULL,
  medium TEXT NOT NULL DEFAULT '', how_many INTEGER NOT NULL DEFAULT 1, stage TEXT NOT NULL DEFAULT 'rooting', stage_on TEXT,
  checked_on TEXT, given_to TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
  created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT, removed_by TEXT, removed_at TEXT);
CREATE INDEX IF NOT EXISTS cuttings_parent ON cuttings(parent_code);
"""
CUT_METHODS = ['Stem cuttings', 'Leaf cuttings', 'Division', 'Offsets or pups', 'Air layering', 'Seed']
CUT_MEDIA = ['Water', 'Potting mix', 'Sphagnum moss', 'Perlite', 'LECA', 'Still on the plant', 'Other']
CUT_STAGES = {'rooting': 'Rooting', 'rooted': 'Has roots', 'potted': 'Potted up', 'given': 'Given away', 'lost': 'Did not take'}
CUT_ACTIVE = ('rooting', 'rooted')
CUT_LOOK_DAYS = 7                    # how often a cutting still in progress comes up on Today for a look
CUT_DONE_DAYS = 90                   # finished batches stay on the page this long
CUT_NOTE_MAX = 300
# Rough times, for the line under each batch. Plain guidance, not a promise: warmth and light change them a lot.
CUT_USUAL = {'Stem cuttings': 'Most stem cuttings root in 2 to 6 weeks.',
             'Leaf cuttings': 'Leaf cuttings are slow: roots in 3 to 8 weeks, and new leaves can take months.',
             'Division': 'A division already has roots. Pot it up and keep it out of strong sun for a week or two.',
             'Offsets or pups': 'Pups with a few roots of their own settle in 2 to 4 weeks.',
             'Air layering': 'Air layers root in 4 to 8 weeks. Cut it off when you can see roots through the moss.',
             'Seed': 'Most seeds come up in 1 to 4 weeks; some take much longer.'}

def cut_tables(c):
    """Create the table when it is missing (a new database, an older one, or one just restored from an older backup)."""
    if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cuttings'").fetchone(): return
    c.executescript(CUT_SCHEMA); c.commit()

def cut_last_look(r):
    """The latest of the day it was taken, the day its stage last changed, and the last look. Pure."""
    return max(x for x in (r['started_on'], r['stage_on'], r['checked_on']) if x)

def cut_state(r, today):
    """For one batch: days since it was taken, whether it is due a look, and when the next look is. Pure.
    today is a date; r has started_on, stage, stage_on and checked_on (ISO dates)."""
    started = date.fromisoformat(r['started_on'])
    out = {'days': (today - started).days, 'active': r['stage'] in CUT_ACTIVE, 'look_due': False, 'next_look': None}
    if out['active']:
        nxt = date.fromisoformat(cut_last_look(r)) + timedelta(days=CUT_LOOK_DAYS)
        out['next_look'] = nxt.isoformat()
        out['look_due'] = nxt <= today
    if r['stage'] == 'rooted' and r['stage_on']:
        out['rooted_after'] = (date.fromisoformat(r['stage_on']) - started).days
    return out

def cut_clean(b, today, partial=False):
    """The fields of a new or changed batch from a request body, checked. Pure apart from abort()."""
    out = {}
    def day(k, label):
        s = str(b.get(k) or '').strip()
        try: d = date.fromisoformat(s)
        except ValueError: abort(400, f'{label} must look like 2026-11-20')
        if d > today: abort(400, f'{label} cannot be a day still to come')
        if (today - d).days > 366 * 10: abort(400, f'{label} must be within the last ten years')
        return d.isoformat()
    if not partial or 'started_on' in b:
        out['started_on'] = day('started_on', 'The day it was taken') if b.get('started_on') else today.isoformat()
    if not partial or 'method' in b:
        m = str(b.get('method') or '').strip()
        if m not in CUT_METHODS: abort(400, 'Choose how it was taken: ' + ', '.join(CUT_METHODS))
        out['method'] = m
    if not partial or 'medium' in b:
        m = str(b.get('medium') or '').strip()
        if m and m not in CUT_MEDIA: abort(400, 'Choose what it is rooting in: ' + ', '.join(CUT_MEDIA))
        out['medium'] = m
    if not partial or 'how_many' in b:
        try: n = int(b.get('how_many') if b.get('how_many') not in (None, '') else 1)
        except (TypeError, ValueError): abort(400, 'How many must be a number')
        if not 1 <= n <= 500: abort(400, 'How many must be between 1 and 500')
        out['how_many'] = n
    if not partial or 'notes' in b:
        out['notes'] = re.sub(r'\s+', ' ', str(b.get('notes') or '')).strip()[:CUT_NOTE_MAX]
    if 'given_to' in b:
        out['given_to'] = re.sub(r'\s+', ' ', str(b.get('given_to') or '')).strip()[:80]
    if 'stage' in b:
        s = str(b.get('stage') or '')
        if s not in CUT_STAGES: abort(400, 'Stage must be one of: ' + ', '.join(CUT_STAGES))
        out['stage'] = s
        if b.get('stage_on'): out['stage_on'] = day('stage_on', 'The day')
    return out

def cut_kv(d):
    """Changed values in words for the audit log: "stage: Has roots; how many: 3". Pure."""
    return '; '.join(f"{k.replace('_', ' ')}: {CUT_STAGES.get(v, v) if k == 'stage' else v}" for k, v in d.items() if v not in (None, ''))

def cut_words(r):
    """A short description for the audit log: "3 stem cuttings in water"."""
    n, m = r['how_many'], r['method']
    what = m.lower() if n != 1 else {'Stem cuttings': 'stem cutting', 'Leaf cuttings': 'leaf cutting', 'Offsets or pups': 'offset or pup',
                                     'Division': 'division', 'Air layering': 'air layer', 'Seed': 'seed'}.get(m, m.lower())
    return f"{n} {what}" + (f" in {r['medium'].lower()}" if r.get('medium') and r['medium'] != 'Still on the plant' else '')

def cut_report(c, code=None):
    cut_tables(c)
    today = local_today(c)
    at, args = plants_at(c, location(c))
    if code: at, args = ' AND code=?', [code]
    plants = {r['code']: r for r in c.execute('SELECT id, code, common_name, status FROM plants WHERE 1=1' + at, args)}
    photo = lambda pid: (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
    since = (today - timedelta(days=CUT_DONE_DAYS)).isoformat()
    rows = c.execute('SELECT * FROM cuttings WHERE removed_at IS NULL ORDER BY started_on DESC, id DESC').fetchall()
    out, photos = [], {}
    for r in rows:
        p = plants.get(r['parent_code'])
        if not p: continue
        d = {k: r[k] for k in ('id', 'started_on', 'method', 'medium', 'how_many', 'stage', 'stage_on', 'checked_on', 'given_to', 'notes', 'created_by')}
        d.update(cut_state(r, today))
        if not d['active'] and (r['stage_on'] or r['started_on']) < since and not code: continue    # finished long ago: off the page
        if p['id'] not in photos: photos[p['id']] = photo(p['id'])
        d.update(plant=p['code'], name=p['common_name'], photo=photos[p['id']], archived=p['status'] != 'active',
                 stage_word=CUT_STAGES[r['stage']], usual=CUT_USUAL.get(r['method'], ''))
        out.append(d)
    n = lambda f: sum(1 for x in out if f(x))
    return {'today': today.isoformat(), 'look_days': CUT_LOOK_DAYS, 'done_days': CUT_DONE_DAYS, 'methods': CUT_METHODS, 'media': CUT_MEDIA,
            'stages': CUT_STAGES, 'cuttings': out,
            'counts': {'due': n(lambda x: x['look_due']), 'rooting': n(lambda x: x['stage'] == 'rooting'), 'rooted': n(lambda x: x['stage'] == 'rooted'),
                       'done': n(lambda x: not x['active']), 'pieces': sum(x['how_many'] for x in out if x['active'])}}

def cut_row(c, i):
    cut_tables(c)
    r = c.execute('SELECT * FROM cuttings WHERE id=? AND removed_at IS NULL', (i,)).fetchone()
    if not r: abort(404, 'Those cuttings are not in the record')
    return r

@app.route('/api/cuttings', methods=['GET', 'POST'])
def cuttings():
    """GET (?plant=CODE for one plant's): the cuttings in progress and those finished lately. POST {plant, method, started_on?,
    medium?, how_many?, notes?}: a new batch (not for viewers, by the usual rule)."""
    c = db()
    if request.method == 'GET': return jsonify(cut_report(c, request.args.get('plant') or None))
    cut_tables(c)
    b = request.get_json(silent=True) or {}
    p = plant_row(c, str(b.get('plant') or ''))
    f = cut_clean(b, local_today(c))
    who, t = editor(), now()
    cur = c.execute('INSERT INTO cuttings(parent_code, started_on, method, medium, how_many, notes, stage, created_by, created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                    (p['code'], f['started_on'], f['method'], f['medium'], f['how_many'], f['notes'], 'rooting', who, t))
    audit_only(c, 'care', 'cutting', None, cut_words(f), who, f"Cuttings taken on {f['started_on']}: {cut_words(f)}", p['id'], p['code'])
    c.commit()
    return jsonify({'id': cur.lastrowid, 'report': cut_report(c)})

@app.route('/api/cuttings/<int:i>', methods=['PUT', 'DELETE'])
def cutting_one(i):
    """PUT {stage?, stage_on?, checked?: true, started_on?, method?, medium?, how_many?, notes?, given_to?}; DELETE removes it."""
    c = db()
    r = cut_row(c, i)
    p = c.execute('SELECT id, code FROM plants WHERE code=?', (r['parent_code'],)).fetchone()
    pid, code = (p['id'], p['code']) if p else (None, r['parent_code'])
    who, t, today = editor(), now(), local_today(c)
    if request.method == 'DELETE':
        c.execute('UPDATE cuttings SET removed_by=?, removed_at=? WHERE id=?', (who, t, i))
        audit_only(c, 'care', 'cutting', cut_words(dict(r)), None, who, f"Cuttings removed from the record: {cut_words(dict(r))}, taken on {r['started_on']}", pid, code)
        c.commit()
        return jsonify({'ok': True, 'report': cut_report(c)})
    b = request.get_json(silent=True) or {}
    f = cut_clean(b, today, partial=True)
    notes = []
    if b.get('checked'):
        f['checked_on'] = today.isoformat()
        notes.append('Looked at the cuttings: ' + ('no roots yet' if r['stage'] == 'rooting' else 'not ready to pot up yet'))
    if 'stage' in f and f['stage'] != r['stage']:
        f.setdefault('stage_on', today.isoformat())
        notes.append(f"Cuttings: {CUT_STAGES[f['stage']].lower()}" + (f" (to {f['given_to']})" if f['stage'] == 'given' and f.get('given_to') else ''))
    elif 'stage' in f: f.pop('stage'); f.pop('stage_on', None)
    if f.get('started_on') and date.fromisoformat(f['started_on']) > date.fromisoformat(f.get('stage_on') or r['stage_on'] or f['started_on']):
        abort(400, 'The day it was taken must come before the day its stage changed')
    changed = {k: v for k, v in f.items() if r[k] != v}
    if not changed: return jsonify({'ok': True, 'report': cut_report(c)})
    for k in ('method', 'medium', 'how_many', 'started_on', 'notes', 'given_to'):
        if k in changed and not (k == 'given_to' and 'stage' in changed): notes.append(f"Cuttings: {k.replace('_', ' ')} changed")
    sets = ', '.join(f'{k}=?' for k in changed)
    c.execute(f'UPDATE cuttings SET {sets}, updated_by=?, updated_at=? WHERE id=?', list(changed.values()) + [who, t, i])
    audit_only(c, 'care', 'cutting', cut_kv({k: r[k] for k in changed}), cut_kv(changed), who, '; '.join(notes) or 'Cuttings changed', pid, code)
    c.commit()
    return jsonify({'ok': True, 'report': cut_report(c)})
