"""Prototype (proto/propagation): cuttings, layers, grafts, divisions, offsets and seeds, tracked from the first cut to a new plant.

The guide (guide.py, #/guide) says how each way of making new plants is done. This records what was actually tried:

- A propagation (table `propagations`, code PR-001...) is one attempt: the way (`METHODS`), the plant it was taken from (or none,
  for seed bought or found), when it started, what it sits in, how many pieces or seeds, and how it is going. It is not a plant:
  a tray of fifteen pothos nodes should not become fifteen entries in the plant list.
- What happens is an event (`prop_events`): Checked, Changed the water, Callus formed, Roots seen, New growth, Graft holding,
  Sprouted (with a number), Lost (with a number), or a note. The clock for the next look starts again at each one.
- A seed lot is a propagation of the way "seed". Its treatment is an ordered list of stages (`prop_stages`): soak, nick the coat,
  warm and moist, cold and moist, light. Each stage has a length in days and a temperature range, is started and finished by hand,
  and tells Today when it ends. The numbers offered are only starting points, every one editable.
- When a piece is ready, "Pot it up" makes a real plant with its own P-code (`prop_make_plant`, the same steps as adding a plant),
  copies what describes the species from the parent, and links the two (`prop_children`). One propagation can make several
  plants (a tray of seedlings); it finishes by itself when every piece is a plant.
- The family tree (`/api/propagations/tree`) follows those links: original plant, what was made from it, what those made.
- What it learns (`/api/propagations/results`): for each way, how many pieces were tried and how many became plants, and the usual
  days to first roots or sprouts, from the finished attempts only.

Nothing else changes: no column is added to plants, no batch is needed. The tables are made the first time any route is used."""
from .core import *   # noqa: F401,F403

ORDER = 63

# the ways, in the order of the guide. check: days between looks. marks: what can be recorded. guide: the section of #/guide.
METHODS = {
    'stem':     dict(label='Stem cutting', guide='gd-stem', check=7, marks=('callus', 'roots', 'shoot'), ready='Roots about an inch long'),
    'leaf':     dict(label='Leaf cutting', guide='gd-leaf', check=7, marks=('callus', 'roots', 'shoot'), ready='Plantlets with their own roots'),
    'root':     dict(label='Root cutting', guide='gd-root', check=14, marks=('shoot',), ready='A shoot with roots of its own'),
    'division': dict(label='Division', guide='gd-division', check=7, marks=('shoot',), ready='Growing again'),
    'offset':   dict(label='Offset, pup, keiki or runner', guide='gd-offsets', check=14, marks=('roots', 'shoot'), ready='A few roots a few inches long'),
    'layer':    dict(label='Layering in the soil', guide='gd-layering', check=14, marks=('roots', 'shoot'), ready='Roots all round the buried part'),
    'airlayer': dict(label='Air layer', guide='gd-air-layering', check=7, marks=('roots',), ready='White roots showing through the moss'),
    'graft':    dict(label='Graft or bud', guide='gd-grafting', check=7, marks=('union', 'shoot'), ready='Scion growing on the rootstock'),
    'bulb':     dict(label='Bulb, corm or tuber', guide='gd-bulbs', check=14, marks=('roots', 'shoot'), ready='Shoots up'),
    'spores':   dict(label='Spores (ferns and mosses)', guide='gd-spores', check=14, marks=('callus', 'shoot'), ready='Tiny ferns big enough to move'),
    'tissue':   dict(label='Tissue culture', guide='gd-tissue', check=7, marks=('shoot', 'roots'), ready='Plantlets ready to harden off'),
    'seed':     dict(label='Seed', guide='gd-seed', check=7, marks=('sprouted',), ready='Seedlings with true leaves'),
}
EVENT_WORD = {'check': 'Checked, no change', 'water': 'Changed the water', 'callus': 'Callus formed', 'roots': 'Roots seen', 'shoot': 'New growth',
              'union': 'Graft holding', 'sprouted': 'Sprouted', 'lost': 'Lost', 'note': 'Note'}
COUNTED = ('sprouted', 'lost')          # events that carry a number
STAGE_KINDS = {'soak': 'Soak in water', 'scarify': 'Nick or sand the seed coat', 'warm': 'Warm and moist', 'cold': 'Cold and moist (stratification)',
               'light': 'Needs light to sprout', 'dry': 'Dry rest'}
# starting points only: (days, low °F, high °F). The species decides; every one is editable and the guide says where it came from.
STAGE_PRESET = {'soak': (1, None, None), 'scarify': (1, None, None), 'warm': (30, 70, 80), 'cold': (60, 34, 41), 'light': (14, 65, 75), 'dry': (14, None, None)}
STATUSES = {'active': 'Going', 'ready': 'Ready to pot up', 'done': 'Finished', 'failed': 'Did not work', 'gave_away': 'Given away'}
SOON_DAYS = 3                           # a stage ending within this many days is listed on Today

PROP_SCHEMA = '''
CREATE TABLE IF NOT EXISTS propagations(
  id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE, method TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
  parent_code TEXT, species TEXT NOT NULL DEFAULT '', count INTEGER NOT NULL DEFAULT 1, started_on TEXT NOT NULL,
  medium TEXT NOT NULL DEFAULT '', setup TEXT NOT NULL DEFAULT '', hormone TEXT NOT NULL DEFAULT '', place TEXT NOT NULL DEFAULT '',
  check_every INTEGER, status TEXT NOT NULL DEFAULT 'active', ended_on TEXT, outcome_note TEXT NOT NULL DEFAULT '',
  collected_on TEXT, collected_at TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
  created_by TEXT, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS propagations_parent ON propagations(parent_code);
CREATE TABLE IF NOT EXISTS prop_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, prop_id INTEGER NOT NULL, on_date TEXT NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL DEFAULT '',
  n INTEGER, by TEXT, at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS prop_events_prop ON prop_events(prop_id, on_date);
CREATE TABLE IF NOT EXISTS prop_stages(
  id INTEGER PRIMARY KEY AUTOINCREMENT, prop_id INTEGER NOT NULL, sort INTEGER NOT NULL DEFAULT 0, kind TEXT NOT NULL, days INTEGER NOT NULL,
  temp_low INTEGER, temp_high INTEGER, started_on TEXT, ended_on TEXT, note TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS prop_stages_prop ON prop_stages(prop_id, sort);
CREATE TABLE IF NOT EXISTS prop_children(
  id INTEGER PRIMARY KEY AUTOINCREMENT, prop_id INTEGER NOT NULL, plant_code TEXT NOT NULL UNIQUE, made_on TEXT NOT NULL, made_by TEXT);
'''
_READY = set()

def prop_db():
    """The connection, with the tables made (once for each database; they are not in init_db so this stays one file)."""
    c = db()
    if DB_PATH not in _READY:
        c.executescript(PROP_SCHEMA); c.commit(); _READY.add(DB_PATH)
    return c

def prop_iso(v, what, today=None, future=False):
    s = str(v or '').strip()
    try: d = date.fromisoformat(s)
    except ValueError: abort(400, f'{what} must be a date (year-month-day)')
    if today and not future and d > today: abort(400, f'{what} cannot be in the future')
    return d.isoformat()

def to_int(v, what, lo, hi, none_ok=False):
    if v in (None, ''):
        if none_ok: return None
        abort(400, f'{what} is needed')
    try: n = int(v)
    except (TypeError, ValueError): abort(400, f'{what} must be a whole number')
    if not lo <= n <= hi: abort(400, f'{what} must be between {lo} and {hi}')
    return n

def prop_row(c, pid):
    r = c.execute('SELECT * FROM propagations WHERE id=?', (pid,)).fetchone()
    if not r: abort(404, 'propagation not found')
    return r

def plant_name(c, code):
    r = c.execute('SELECT common_name FROM plants WHERE code=?', (code,)).fetchone() if code else None
    return r[0] if r else None

def prop_photo(c, code):
    r = c.execute('SELECT ph.file FROM photos ph JOIN plants p ON p.id=ph.plant_id WHERE p.code=? ORDER BY ph.is_primary DESC, ph.id LIMIT 1', (code,)).fetchone()
    return r[0] if r else None

def check_days(r):
    """How often to look: the person's number, else a week for things in water or seeds and the way's usual."""
    if r['check_every']: return r['check_every']
    if 'water' in (r['medium'] or '').lower(): return 7
    return METHODS.get(r['method'], METHODS['stem'])['check']

def prop_card(c, r, today):
    """Everything one attempt needs to be drawn: its numbers, stages, what to do next, and the plants it made."""
    m = METHODS.get(r['method'], METHODS['stem'])
    events = [dict(e) for e in c.execute('SELECT * FROM prop_events WHERE prop_id=? ORDER BY on_date DESC, id DESC', (r['id'],))]
    for e in events: e['word'] = EVENT_WORD.get(e['kind'], e['kind'])
    stages = [dict(s) for s in c.execute('SELECT * FROM prop_stages WHERE prop_id=? ORDER BY sort, id', (r['id'],))]
    for s in stages:
        s['label'] = STAGE_KINDS.get(s['kind'], s['kind'])
        s['state'] = 'done' if s['ended_on'] else 'running' if s['started_on'] else 'waiting'
        s['ends_on'] = (date.fromisoformat(s['started_on']) + timedelta(days=s['days'])).isoformat() if s['started_on'] else None
        s['days_left'] = (date.fromisoformat(s['ends_on']) - today).days if s['ends_on'] and not s['ended_on'] else None
    kids = [dict(code=k['plant_code'], made_on=k['made_on'], name=plant_name(c, k['plant_code']) or k['plant_code'])
            for k in c.execute('SELECT * FROM prop_children WHERE prop_id=? ORDER BY id', (r['id'],))]
    sprouted = sum(e['n'] or 0 for e in events if e['kind'] == 'sprouted')
    lost = sum(e['n'] or 0 for e in events if e['kind'] == 'lost')
    seen = max([e['on_date'] for e in events if e['kind'] != 'note'] + [r['started_on']])
    every = check_days(r)
    active = r['status'] in ('active', 'ready')
    needs = []
    if active:
        running = next((s for s in stages if s['state'] == 'running'), None)
        waiting = next((s for s in stages if s['state'] == 'waiting'), None)
        if running and running['days_left'] <= SOON_DAYS:
            dl = running['days_left']
            when = 'ends today' if dl == 0 else 'ended yesterday' if dl == -1 else f'ended {-dl} days ago' if dl < 0 else 'ends tomorrow' if dl == 1 else f'ends in {dl} days'
            needs.append(dict(kind='stage_end', stage=running['id'], due=True, words=f"{running['label']} {when}"))
        elif not running and waiting:
            needs.append(dict(kind='stage_start', stage=waiting['id'], due=True, words=f"Next step: {waiting['label'].lower()}, {waiting['days']} days"))
        nxt = date.fromisoformat(seen) + timedelta(days=every)
        ago = (today - date.fromisoformat(seen)).days
        last = 'today' if ago <= 0 else 'yesterday' if ago == 1 else f'{ago} days ago'
        needs.append(dict(kind='check', due=nxt <= today, on=nxt.isoformat(),
                          words=('Look at it' if r['status'] == 'active' else 'Ready to pot up') + f': last looked {last}'))
    d = {k: r[k] for k in r.keys()}
    d.update(method_label=m['label'], guide=m['guide'], marks=[dict(kind=k, word=EVENT_WORD[k]) for k in m['marks']], ready_words=m['ready'],
             status_word=STATUSES.get(r['status'], r['status']), parent_name=plant_name(c, r['parent_code']), parent_photo=prop_photo(c, r['parent_code']) if r['parent_code'] else None,
             days=(today - date.fromisoformat(r['started_on'])).days, events=events, stages=stages, children=kids, sprouted=sprouted, lost=lost,
             check_every=every, last_seen=seen, needs=needs, due=[n for n in needs if n['due']], is_seed=r['method'] == 'seed',
             left=max(0, r['count'] - len(kids) - lost))
    return d

def prop_list(c):
    today = local_today(c)
    rows = c.execute('SELECT * FROM propagations ORDER BY (status IN ("active","ready")) DESC, started_on DESC, id DESC').fetchall()
    return today, [prop_card(c, r, today) for r in rows]

def prop_audit(c, field, old, new, note, parent=None):
    r = plant_row(c, parent) if parent else None
    audit_only(c, 'propagation', field, old, new, editor(), note, r['id'] if r else None, parent)

# ---------------------------------------------------------------- the routes
@app.route('/api/propagations', methods=['GET', 'POST'])
def propagations():
    """GET: every attempt with its numbers, plus the ways, stage starting points and the plants that can be a parent.
    POST: start one. {method, title?, parent_code?, species?, count, started_on?, medium?, setup?, hormone?, place?, check_every?,
    notes?, collected_on?, collected_at?, stages?: [{kind, days?, temp_low?, temp_high?}]}"""
    c = prop_db()
    if request.method == 'GET':
        today, items = prop_list(c)
        active = [p for p in items if p['status'] in ('active', 'ready')]
        return jsonify(today=today.isoformat(), items=items, due=[p['id'] for p in active if p['due']],
                       methods={k: dict(label=v['label'], guide=v['guide'], check=v['check'], marks=[dict(kind=x, word=EVENT_WORD[x]) for x in v['marks']]) for k, v in METHODS.items()},
                       stage_kinds=STAGE_KINDS, stage_preset={k: dict(days=v[0], low=v[1], high=v[2]) for k, v in STAGE_PRESET.items()}, statuses=STATUSES,
                       counts=dict(active=len(active), due=sum(1 for p in active if p['due']), finished=len(items) - len(active)))
    b = request.get_json(silent=True) or {}
    today = local_today(c)
    method = str(b.get('method') or '')
    if method not in METHODS: abort(400, 'Choose one of the ways: ' + ', '.join(v['label'] for v in METHODS.values()))
    parent = str(b.get('parent_code') or '').strip() or None
    pr = plant_row(c, parent) if parent else None
    species = str(b.get('species') or '').strip()[:120] or (pr['scientific_name'] or pr['common_name'] if pr else '')
    title = str(b.get('title') or '').strip()[:120]
    if not title:
        base = (pr['common_name'] if pr else species) or 'Unnamed'
        title = f"{base}: {METHODS[method]['label'].lower()}"
    count = to_int(b.get('count', 1), 'How many', 1, 5000)
    started = prop_iso(b.get('started_on') or today.isoformat(), 'Started on', today)
    ce = to_int(b.get('check_every'), 'Look every (days)', 1, 120, none_ok=True)
    collected = prop_iso(b['collected_on'], 'Collected on', today) if b.get('collected_on') else None
    n = c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(code,4) AS INTEGER)),0)+1 FROM propagations").fetchone()[0]
    code, who, ts = f'PR-{n:03d}', editor(), now()
    txt = lambda k, ln=300: str(b.get(k) or '').strip()[:ln]
    cur = c.execute('''INSERT INTO propagations(code,method,title,parent_code,species,count,started_on,medium,setup,hormone,place,check_every,collected_on,collected_at,notes,
                       created_by,created_at,updated_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (code, method, title, parent, species, count, started, txt('medium', 120), txt('setup'), txt('hormone', 120), txt('place', 120), ce, collected,
                     txt('collected_at'), txt('notes', 2000), who, ts, who, ts))
    pid = cur.lastrowid
    for i, s in enumerate(b.get('stages') or []):
        add_stage(c, pid, s, i)
    prop_audit(c, 'propagation', None, code, f'Started {METHODS[method]["label"].lower()} {code}: {title}', parent)
    c.commit()
    return jsonify(prop_card(c, prop_row(c, pid), today)), 201

@app.route('/api/propagations/<int:pid>', methods=['GET', 'PUT', 'DELETE'])
def propagation_one(pid):
    c = prop_db(); r = prop_row(c, pid); today = local_today(c)
    if request.method == 'GET': return jsonify(prop_card(c, r, today))
    if request.method == 'DELETE':
        if c.execute('SELECT 1 FROM prop_children WHERE prop_id=?', (pid,)).fetchone():
            abort(409, 'This made plants, so it stays as their history. Mark it finished instead.')
        c.execute('DELETE FROM prop_events WHERE prop_id=?', (pid,)); c.execute('DELETE FROM prop_stages WHERE prop_id=?', (pid,)); c.execute('DELETE FROM propagations WHERE id=?', (pid,))
        prop_audit(c, 'propagation', r['code'], None, f'Removed {r["code"]}: {r["title"]}', r['parent_code'])
        c.commit(); return jsonify(removed=True)
    b = request.get_json(silent=True) or {}
    sets = {}
    for k, ln in (('title', 120), ('species', 120), ('medium', 120), ('setup', 300), ('hormone', 120), ('place', 120), ('collected_at', 300), ('notes', 2000), ('outcome_note', 2000)):
        if k in b: sets[k] = str(b[k] or '').strip()[:ln]
    if 'count' in b: sets['count'] = to_int(b['count'], 'How many', max(1, c.execute('SELECT COUNT(*) FROM prop_children WHERE prop_id=?', (pid,)).fetchone()[0]), 5000)
    if 'started_on' in b: sets['started_on'] = prop_iso(b['started_on'], 'Started on', today)
    if 'collected_on' in b: sets['collected_on'] = prop_iso(b['collected_on'], 'Collected on', today) if b['collected_on'] else None
    if 'check_every' in b: sets['check_every'] = to_int(b['check_every'], 'Look every (days)', 1, 120, none_ok=True)
    if 'parent_code' in b:
        pc = str(b['parent_code'] or '').strip() or None
        if pc: plant_row(c, pc)
        sets['parent_code'] = pc
    for k, v in sets.items():
        if (r[k] if r[k] is not None else '') != (v if v is not None else ''):
            prop_audit(c, k, r[k], v, f'{r["code"]}: {k.replace("_", " ")} changed', r['parent_code'])
    if sets:
        c.execute('UPDATE propagations SET ' + ','.join(f'{k}=?' for k in sets) + ',updated_by=?,updated_at=? WHERE id=?', [*sets.values(), editor(), now(), pid])
        c.commit()
    return jsonify(prop_card(c, prop_row(c, pid), today))

@app.route('/api/propagations/<int:pid>/events', methods=['POST'])
def propagation_event(pid):
    """{kind: check|water|callus|roots|shoot|union|sprouted|lost|note, n?, text?, on_date?}. Sprouted and Lost carry a number."""
    c = prop_db(); r = prop_row(c, pid); today = local_today(c)
    b = request.get_json(silent=True) or {}
    kind = str(b.get('kind') or '')
    if kind not in EVENT_WORD: abort(400, 'kind must be one of: ' + ', '.join(EVENT_WORD))
    n = to_int(b.get('n'), 'How many', 1, 5000, none_ok=kind not in COUNTED) if kind in COUNTED or b.get('n') not in (None, '') else None
    text = str(b.get('text') or '').strip()[:500]
    if kind == 'note' and not text: abort(400, 'Write the note')
    on = prop_iso(b.get('on_date') or today.isoformat(), 'Date', today)
    if on < r['started_on']: abort(400, 'That is before it started')
    cur = c.execute('INSERT INTO prop_events(prop_id,on_date,kind,text,n,by,at) VALUES(?,?,?,?,?,?,?)', (pid, on, kind, text, n, editor(), now()))
    prop_audit(c, 'event', None, EVENT_WORD[kind] + (f' ({n})' if n else ''), f'{r["code"]}: {EVENT_WORD[kind].lower()}{" " + str(n) if n else ""}', r['parent_code'])
    c.commit()
    return jsonify(id=cur.lastrowid, card=prop_card(c, prop_row(c, pid), today)), 201

@app.route('/api/propagations/events/<int:eid>', methods=['DELETE'])
def propagation_event_undo(eid):
    c = prop_db(); e = c.execute('SELECT * FROM prop_events WHERE id=?', (eid,)).fetchone()
    if not e: abort(404, 'entry not found')
    r = prop_row(c, e['prop_id'])
    c.execute('DELETE FROM prop_events WHERE id=?', (eid,))
    prop_audit(c, 'event', EVENT_WORD.get(e['kind'], e['kind']), None, f'{r["code"]}: took back "{EVENT_WORD.get(e["kind"], e["kind"]).lower()}" from {e["on_date"]}', r['parent_code'])
    c.commit()
    return jsonify(card=prop_card(c, r, local_today(c)))

def add_stage(c, pid, s, i):
    kind = str((s or {}).get('kind') or '')
    if kind not in STAGE_KINDS: abort(400, 'A step must be one of: ' + ', '.join(STAGE_KINDS.values()))
    p = STAGE_PRESET[kind]
    days = to_int(s.get('days', p[0]), 'Days', 0, 730)
    lo = to_int(s.get('temp_low', p[1]), 'Lowest °F', -20, 140, none_ok=True); hi = to_int(s.get('temp_high', p[2]), 'Highest °F', -20, 140, none_ok=True)
    if lo is not None and hi is not None and lo > hi: abort(400, 'The lowest temperature is above the highest')
    nxt = c.execute('SELECT COALESCE(MAX(sort),-1)+1 FROM prop_stages WHERE prop_id=?', (pid,)).fetchone()[0] if i is None else i
    c.execute('INSERT INTO prop_stages(prop_id,sort,kind,days,temp_low,temp_high,note) VALUES(?,?,?,?,?,?,?)', (pid, nxt, kind, days, lo, hi, str(s.get('note') or '').strip()[:300]))

@app.route('/api/propagations/<int:pid>/stages', methods=['POST'])
def propagation_stage_add(pid):
    c = prop_db(); r = prop_row(c, pid)
    add_stage(c, pid, request.get_json(silent=True) or {}, None)
    prop_audit(c, 'stage', None, 'added', f'{r["code"]}: a step was added', r['parent_code'])
    c.commit(); return jsonify(prop_card(c, r, local_today(c))), 201

@app.route('/api/propagations/stages/<int:sid>', methods=['PUT', 'DELETE'])
def propagation_stage(sid):
    """PUT {action: start | done | undo} or {days, temp_low, temp_high, note}. A step starts on a date (today unless given) and ends by itself on the
    date its days run out; "done" ends it today. DELETE removes it."""
    c = prop_db(); s = c.execute('SELECT * FROM prop_stages WHERE id=?', (sid,)).fetchone()
    if not s: abort(404, 'step not found')
    r = prop_row(c, s['prop_id']); today = local_today(c); b = request.get_json(silent=True) or {}
    word = STAGE_KINDS.get(s['kind'], s['kind']).lower()
    if request.method == 'DELETE':
        c.execute('DELETE FROM prop_stages WHERE id=?', (sid,)); prop_audit(c, 'stage', word, None, f'{r["code"]}: removed the step "{word}"', r['parent_code'])
    else:
        act = b.get('action')
        if act == 'start':
            if s['ended_on']: abort(409, 'That step is finished. Take back its finish first.')
            on = prop_iso(b.get('on_date') or today.isoformat(), 'Started on', today)
            c.execute('UPDATE prop_stages SET started_on=? WHERE id=?', (on, sid))
            prop_audit(c, 'stage', None, on, f'{r["code"]}: started "{word}", {s["days"]} days', r['parent_code'])
        elif act == 'done':
            if not s['started_on']: abort(409, 'Start the step first')
            c.execute('UPDATE prop_stages SET ended_on=? WHERE id=?', (prop_iso(b.get('on_date') or today.isoformat(), 'Finished on', today), sid))
            prop_audit(c, 'stage', None, 'finished', f'{r["code"]}: finished "{word}"', r['parent_code'])
        elif act == 'undo':
            c.execute('UPDATE prop_stages SET ended_on=NULL WHERE id=?' if s['ended_on'] else 'UPDATE prop_stages SET started_on=NULL WHERE id=?', (sid,))
            prop_audit(c, 'stage', None, 'taken back', f'{r["code"]}: took back "{word}"', r['parent_code'])
        else:
            days = to_int(b.get('days', s['days']), 'Days', 0, 730)
            lo = to_int(b.get('temp_low', s['temp_low']), 'Lowest °F', -20, 140, none_ok=True); hi = to_int(b.get('temp_high', s['temp_high']), 'Highest °F', -20, 140, none_ok=True)
            if lo is not None and hi is not None and lo > hi: abort(400, 'The lowest temperature is above the highest')
            c.execute('UPDATE prop_stages SET days=?,temp_low=?,temp_high=?,note=? WHERE id=?', (days, lo, hi, str(b.get('note', s['note']) or '').strip()[:300], sid))
            prop_audit(c, 'stage', f'{s["days"]} days', f'{days} days', f'{r["code"]}: "{word}" changed', r['parent_code'])
    c.commit()
    return jsonify(card=prop_card(c, r, today))

@app.route('/api/propagations/<int:pid>/status', methods=['POST'])
def propagation_status(pid):
    """{status: active | ready | failed | gave_away | done, note?}. Failed and given away end it today; going again reopens it."""
    c = prop_db(); r = prop_row(c, pid); today = local_today(c); b = request.get_json(silent=True) or {}
    st = str(b.get('status') or '')
    if st not in STATUSES: abort(400, 'status must be one of: ' + ', '.join(STATUSES))
    ended = today.isoformat() if st in ('failed', 'gave_away', 'done') else None
    note = str(b.get('note') or r['outcome_note'] or '').strip()[:2000]
    c.execute('UPDATE propagations SET status=?, ended_on=?, outcome_note=?, updated_by=?, updated_at=? WHERE id=?', (st, ended, note, editor(), now(), pid))
    prop_audit(c, 'status', r['status'], st, f'{r["code"]}: {STATUSES[st].lower()}', r['parent_code'])
    c.commit()
    return jsonify(prop_card(c, prop_row(c, pid), today))

# ---------------------------------------------------------------- pot it up: a piece becomes a plant
COPY_FROM_PARENT = ('scientific_name', 'aliases', 'plant_type', 'family', 'genus', 'kingdom', 'taxon_order', 'home_id', 'winter_plan', 'site')

def prop_make_plant(c, f, who):
    """The steps of adding a plant (plants.create_plant), for a plant made here: the next P-code, its first version, the audit row."""
    n = c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(code,3) AS INTEGER)),0)+1 FROM plants").fetchone()[0]
    code, ts = f'P-{n:03d}', now()
    f = place_sync(c, None, dict(f))
    vals = {k: norm(k, f.get(k)) for k in FIELD_NAMES}
    cols = ['code'] + FIELD_NAMES + ['version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by']
    cur = c.execute(f"INSERT INTO plants({','.join(cols)}) VALUES({','.join('?' * len(cols))})", [code] + [vals[k] for k in FIELD_NAMES] + [1, 'active', ts, who, ts, who])
    pid = cur.lastrowid
    c.execute('INSERT INTO plant_versions(plant_id,version,snapshot,changed_by,changed_at,summary) VALUES(?,?,?,?,?,?)', (pid, 1, json.dumps(snapshot(c, pid)), who, ts, 'Record created'))
    return pid, code

@app.route('/api/propagations/<int:pid>/promote', methods=['POST'])
def propagation_promote(pid):
    """{common_name?, scientific_name?, site?, made_on?, note?}: makes a plant with its own P-code from one piece of this attempt. What describes the
    species (temperatures, light, water, soil, feeding, size, safety) is copied from the parent plant; where it sits, its pot and its photos are
    not. The new plant's Notes say where it came from. A seed lot with no parent plant needs a name."""
    c = prop_db(); r = prop_row(c, pid); today = local_today(c); b = request.get_json(silent=True) or {}
    if r['status'] in ('failed', 'gave_away'): abort(409, 'This one is marked ' + STATUSES[r['status']].lower() + '. Mark it going again to pot something up.')
    made = c.execute('SELECT COUNT(*) FROM prop_children WHERE prop_id=?', (pid,)).fetchone()[0]
    lost = sum(e[0] or 0 for e in c.execute("SELECT n FROM prop_events WHERE prop_id=? AND kind='lost'", (pid,)))
    room = r['count'] - made - lost
    if room < 1: abort(409, 'Every piece is already a plant or marked lost')
    parent = plant_row(c, r['parent_code']) if r['parent_code'] else None
    f = {}
    if parent:
        for k in {x[0] for x in PLANT_FACT_FIELDS} | set(COPY_FROM_PARENT):
            if k in FIELD_KIND and k not in ('area_id', 'spot_id', 'pot_id', 'tray_id', 'location', 'container', 'pests_found', 'height_in', 'grow_kind', 'reservoir'): f[k] = parent[k]
        f['common_name'] = parent['common_name']
    name = str(b.get('common_name') or '').strip() or f.get('common_name') or r['species']
    if not name: abort(400, 'Give the new plant a name')
    f['common_name'] = name
    if b.get('scientific_name'): f['scientific_name'] = str(b['scientific_name']).strip()
    elif not f.get('scientific_name') and r['species'] and r['species'] != name: f['scientific_name'] = r['species']
    f['site'] = str(b.get('site') or f.get('site') or 'Indoors')
    f['winter_plan'] = f.get('winter_plan') or 'Move indoors'
    f['health_rating'] = 'Fair'
    made_on = prop_iso(b.get('made_on') or today.isoformat(), 'Potted on', today)
    way = METHODS[r['method']]['label'].lower()
    f['notes'] = (f"Made from a {way}" + (f" of {parent['code']} ({parent['common_name']})" if parent else '') + f", started {r['started_on']} ({r['code']}), potted up {made_on}."
                  + (' ' + str(b['note']).strip() if b.get('note') else ''))[:2000]
    who = editor()
    ppid, pcode = prop_make_plant(c, f, who)
    c.execute('INSERT INTO prop_children(prop_id,plant_code,made_on,made_by) VALUES(?,?,?,?)', (pid, pcode, made_on, who))
    audit_only(c, 'create', None, None, None, who, f'Record created: potted up from {r["code"]}' + (f', a {way} of {parent["code"]}' if parent else ''), ppid, pcode)
    c.execute('UPDATE audit_log SET version=1 WHERE plant_id=? AND action=?', (ppid, 'create'))
    if parent: prop_audit(c, 'propagation', None, pcode, f'{pcode} was made from {r["code"]}, a {way} of this plant', parent['code'])
    if made + 1 + lost >= r['count'] and r['method'] != 'seed':
        c.execute("UPDATE propagations SET status='done', ended_on=?, updated_by=?, updated_at=? WHERE id=?", (today.isoformat(), who, now(), pid))
    c.commit()
    return jsonify(code=pcode, card=prop_card(c, prop_row(c, pid), today)), 201

# ---------------------------------------------------------------- the family tree and what it has taught
def tree_nodes(c, today):
    """Plants that are a parent or a child of something, as a forest. A node is a plant with what was made from it (`makes`), each with the
    plants it produced; an attempt that has not made a plant yet shows with no children. An attempt with no parent plant (seed from
    outside) is a root of its own."""
    cards = {p['id']: p for p in prop_list(c)[1]}
    by_parent, rootless = {}, []
    child_of = {}
    for p in cards.values():
        if p['parent_code']: by_parent.setdefault(p['parent_code'], []).append(p)
        else: rootless.append(p)
        for k in p['children']: child_of[k['code']] = p['id']
    def short(p): return {k: p[k] for k in ('id', 'code', 'method', 'method_label', 'title', 'started_on', 'status', 'status_word', 'count', 'sprouted', 'lost', 'days')}
    def plant_node(code, depth, seen):
        pl = c.execute('SELECT common_name, scientific_name, status FROM plants WHERE code=?', (code,)).fetchone()
        node = dict(type='plant', code=code, name=pl['common_name'] if pl else code, scientific=pl['scientific_name'] if pl else '', archived=bool(pl and pl['status'] != 'active'),
                    photo=prop_photo(c, code), generation=depth, makes=[])
        if code in seen or depth > 12: return node
        for p in by_parent.get(code, []):
            node['makes'].append(dict(short(p), children=[plant_node(k['code'], depth + 1, seen | {code}) for k in p['children']]))
        return node
    roots = [plant_node(code, 1, set()) for code in by_parent if code not in child_of]
    roots.sort(key=lambda n: n['code'])
    outside = [dict(short(p), children=[plant_node(k['code'], 2, set()) for k in p['children']]) for p in rootless]
    return roots, outside

@app.route('/api/propagations/tree')
def propagation_tree():
    c = prop_db(); today = local_today(c)
    roots, outside = tree_nodes(c, today)
    return jsonify(roots=roots, outside=outside)

@app.route('/api/propagations/plant/<code>')
def propagation_plant(code):
    """For a plant's own page: where it came from, and what has been (or is being) made from it."""
    c = prop_db(); plant_row(c, code); today = local_today(c)
    _, items = prop_list(c)
    mine = [p for p in items if p['parent_code'] == code]
    origin = next((p for p in items if any(k['code'] == code for k in p['children'])), None)
    chain, cur, guard_n = [], origin, 0
    while cur and cur['parent_code'] and guard_n < 12:
        chain.append(dict(code=cur['parent_code'], name=cur['parent_name'], via=cur['method_label'], prop=cur['code'], prop_id=cur['id']))
        cur = next((p for p in items if any(k['code'] == cur['parent_code'] for k in p['children'])), None); guard_n += 1
    return jsonify(origin=origin and dict(id=origin['id'], code=origin['code'], method_label=origin['method_label'], started_on=origin['started_on'], parent_code=origin['parent_code'], parent_name=origin['parent_name']),
                   ancestors=chain, generation=len(chain) + 1, made=mine, today=today.isoformat())

@app.route('/api/propagations/results')
def propagation_results():
    """What the finished attempts show, for each way and for each species: pieces tried, pieces that became plants, and the usual days to the
    first sign (roots, sprouts or a holding graft). Attempts still going are counted apart and never change the rate."""
    c = prop_db(); today, items = prop_list(c)
    finished = [p for p in items if p['status'] in ('done', 'failed', 'gave_away')]
    def stats(group):
        tried = sum(p['count'] for p in group); made = sum(len(p['children']) for p in group)
        firsts = []
        for p in group:
            sign = [e['on_date'] for e in p['events'] if e['kind'] in ('roots', 'sprouted', 'union', 'shoot')]
            if sign: firsts.append((date.fromisoformat(min(sign)) - date.fromisoformat(p['started_on'])).days)
        firsts.sort()
        return dict(attempts=len(group), tried=tried, made=made, rate=round(100 * made / tried) if tried else None,
                    first_days=firsts[len(firsts) // 2] if firsts else None, first_n=len(firsts))
    ways = {}
    for k, v in METHODS.items():
        g = [p for p in finished if p['method'] == k]; going = sum(1 for p in items if p['method'] == k and p['status'] in ('active', 'ready'))
        if g or going: ways[k] = dict(label=v['label'], going=going, **stats(g))
    spec = {}
    for p in finished:
        key = (p['species'] or p['parent_name'] or '').strip()
        if key: spec.setdefault(key, []).append(p)
    species = [dict(species=k, **stats(g), ways=sorted({p['method_label'] for p in g})) for k, g in spec.items()]
    species.sort(key=lambda s: (-s['attempts'], s['species'].lower()))
    return jsonify(ways=ways, species=species, finished=len(finished), going=len(items) - len(finished))
