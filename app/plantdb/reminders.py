"""Prototype (proto/reminders): your own reminders. A note to yourself with a date, for one plant or for no plant in particular:
"Check the cutting for roots", "Spray again for mealybugs", "Buy potting mix". On the day it is due it shows on Today (and stays
there until it is done), and a plant's page lists its own. A reminder can repeat: done, and the next one is set that many days
after the day it was done.

Stored in its own table, plant_reminders, created here when the module first needs it (CREATE TABLE IF NOT EXISTS, so an existing
database is upgraded in place and nothing else changes). Done, snoozed and removed reminders are kept, so Undo and the audit log
work: a removed one only gets removed_at. A repeating reminder is one row per time round; done_next points at the row made when it
was done, so "Not done yet" can take that one back as long as nobody has changed it."""
from .core import *   # noqa: F401,F403

REMIND_SCHEMA = """
CREATE TABLE IF NOT EXISTS plant_reminders(
  id INTEGER PRIMARY KEY AUTOINCREMENT, plant_code TEXT, loc_id INTEGER, text TEXT NOT NULL, due_on TEXT NOT NULL,
  repeat_days INTEGER NOT NULL DEFAULT 0, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
  done_by TEXT, done_at TEXT, done_on TEXT, done_next INTEGER, removed_by TEXT, removed_at TEXT);
CREATE INDEX IF NOT EXISTS plant_reminders_due ON plant_reminders(due_on);
"""
REMIND_REPEATS = {0: 'Does not repeat', 7: 'Every week', 14: 'Every 2 weeks', 30: 'Every month', 60: 'Every 2 months',
                  90: 'Every 3 months', 182: 'Every 6 months', 365: 'Every year'}
REMIND_TEXT_MAX = 200
REMIND_DONE_DAYS = 30                       # how long done reminders stay listed (Done lately)

def remind_tables(c):
    """Create the table when it is missing (a new database, an older one, or one just restored from an older backup), so
    init_db() does not need to know about it."""
    if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='plant_reminders'").fetchone(): return
    c.executescript(REMIND_SCHEMA); c.commit()

def remind_repeat_word(n):
    return REMIND_REPEATS.get(int(n or 0), f'Every {n} days')

def remind_state(due_on, today):
    """'late' (past its day), 'today' or 'later'. Pure."""
    return 'late' if due_on < today else 'today' if due_on == today else 'later'

def remind_clean(b, today, partial=False):
    """The fields of a new or changed reminder from a request body, checked. Pure apart from abort()."""
    out = {}
    if not partial or 'text' in b:
        t = re.sub(r'\s+', ' ', str(b.get('text') or '')).strip()
        if not t: abort(400, 'Say what the reminder is for')
        out['text'] = t[:REMIND_TEXT_MAX]
    if not partial or 'due_on' in b:
        d = str(b.get('due_on') or '').strip()
        try: dd = date.fromisoformat(d)
        except ValueError: abort(400, 'The date must look like 2026-11-20')
        if (dd - today).days > 366 * 5: abort(400, 'Choose a date within the next five years')
        if not partial and dd < today: abort(400, 'Choose today or a day still to come')
        out['due_on'] = dd.isoformat()
    if not partial or 'repeat_days' in b:
        try: n = int(b.get('repeat_days') or 0)
        except (TypeError, ValueError): abort(400, 'Repeat must be a number of days')
        if n not in REMIND_REPEATS: abort(400, 'Repeat must be one of: ' + ', '.join(map(str, REMIND_REPEATS)) + ' days')
        out['repeat_days'] = n
    return out

def remind_here(c):
    """SQL (and arguments) keeping the reminders of the home in use: a plant's follows the plant; one for no plant follows the
    home it was written at (the main home when that is empty)."""
    L, H = location(c), home_place(c)
    if not (L.get('is_home') or L.get('plants_here')): L = H
    return (' AND ((r.plant_code IS NOT NULL AND COALESCE(p.home_id, ?)=?) OR (r.plant_code IS NULL AND COALESCE(r.loc_id, ?)=?))',
            [H['id'], L['id'], H['id'], L['id']])

def remind_rows(c, plant=None, done=True):
    remind_tables(c)
    today = local_today(c).isoformat()
    w, args = remind_here(c)
    if plant: w, args = ' AND r.plant_code=?', [plant]
    q = ('SELECT r.*, p.common_name AS plant_name, p.id AS pid, p.status AS plant_status FROM plant_reminders r '
         'LEFT JOIN plants p ON p.code=r.plant_code WHERE r.removed_at IS NULL')
    open_ = c.execute(q + ' AND r.done_at IS NULL' + w + ' ORDER BY r.due_on, r.id', args).fetchall()
    since = (local_today(c) - timedelta(days=REMIND_DONE_DAYS)).isoformat()
    shut = c.execute(q + ' AND r.done_at IS NOT NULL AND r.done_on>=?' + w + ' ORDER BY r.done_at DESC, r.id DESC LIMIT 50', [since] + args).fetchall() if done else []
    photo = {}
    def pic(pid):
        if pid not in photo: photo[pid] = (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
        return photo[pid]
    def one(r):
        d = {k: r[k] for k in ('id', 'plant_code', 'text', 'due_on', 'repeat_days', 'created_by', 'created_at', 'done_by', 'done_on', 'done_next')}
        d.update(plant_name=r['plant_name'], photo=pic(r['pid']) if r['pid'] else None, repeat_word=remind_repeat_word(r['repeat_days']),
                 state='done' if r['done_at'] else remind_state(r['due_on'], today), archived=r['plant_status'] not in (None, 'active'))
        # "Not done yet" works while the next one (if any) is untouched
        if r['done_at']:
            nx = c.execute('SELECT done_at, removed_at FROM plant_reminders WHERE id=?', (r['done_next'],)).fetchone() if r['done_next'] else None
            d['can_undo'] = not nx or (nx['done_at'] is None and nx['removed_at'] is None)
        return d
    rows = [one(r) for r in open_]
    n = lambda s: sum(1 for x in rows if x['state'] == s)
    return {'today': today, 'repeats': [[k, v] for k, v in REMIND_REPEATS.items()], 'open': rows, 'done': [one(r) for r in shut],
            'counts': {'late': n('late'), 'today': n('today'), 'later': n('later'), 'due': n('late') + n('today')}}

def remind_get(c, rid):
    remind_tables(c)
    r = c.execute('SELECT * FROM plant_reminders WHERE id=? AND removed_at IS NULL', (rid,)).fetchone()
    if not r: abort(404, 'That reminder is not there any more')
    u = getattr(g, 'user', None)                       # an editor limited to some homes: reminders of plants elsewhere are not theirs to change
    if u and u.get('role') == 'editor' and u.get('edit_homes') and r['plant_code']:
        h = plant_home_of(c, r['plant_code'])
        if h is not None and h not in u['edit_homes']: abort(403, f"{r['plant_code']} is at another home, so you cannot change its reminders.")
    return r

def remind_audit(c, r, field, old, new, note):
    pid = None
    if r['plant_code']:
        p = c.execute('SELECT id FROM plants WHERE code=?', (r['plant_code'],)).fetchone()
        pid = p[0] if p else None
    audit_only(c, 'care', field, old, new, editor(), note, pid, r['plant_code'])

@app.route('/api/reminders', methods=['GET', 'POST'])
def reminders_api():
    """GET: the reminders at the home in use (?plant=CODE for one plant's, ?done=0 to leave out Done lately).
    POST {text, due_on, repeat_days, plant}: a new one (plant may be empty: a reminder for no plant in particular)."""
    c = db(); remind_tables(c)
    if request.method == 'GET':
        return jsonify(remind_rows(c, (request.args.get('plant') or '').strip().upper() or None, request.args.get('done') != '0'))
    b = request.get_json(silent=True) or {}
    f = remind_clean(b, local_today(c))
    code = str(b.get('plant') or '').strip().upper() or None
    pid = None
    if code:
        p = plant_row(c, code); code, pid = p['code'], p['id']
    cur = c.execute('INSERT INTO plant_reminders(plant_code,loc_id,text,due_on,repeat_days,created_by,created_at) VALUES(?,?,?,?,?,?,?)',
                    (code, None if code else location(c)['id'], f['text'], f['due_on'], f['repeat_days'], editor(), now()))
    rep = '' if not f['repeat_days'] else ', ' + remind_repeat_word(f['repeat_days']).lower()
    audit_only(c, 'care', 'reminder', None, f['text'], editor(), f"Reminder set for {f['due_on']}{rep}: {f['text']}", pid, code)
    c.commit()
    return jsonify({'id': cur.lastrowid, **remind_rows(c, code)})

@app.route('/api/reminders/<int:rid>', methods=['PUT', 'DELETE'])
def reminder_one(rid):
    """PUT {text?, due_on?, repeat_days?}: change it (a later day is "Remind me later"). DELETE: remove it (kept, marked removed)."""
    c = db(); r = remind_get(c, rid)
    if request.method == 'DELETE':
        c.execute('UPDATE plant_reminders SET removed_by=?, removed_at=? WHERE id=?', (editor(), now(), rid))
        remind_audit(c, r, 'reminder', r['text'], None, f"Reminder removed: {r['text']}")
        c.commit(); return jsonify({'ok': True})
    if r['done_at']: abort(409, 'That reminder is already done')
    f = remind_clean(request.get_json(silent=True) or {}, local_today(c), partial=True)
    ch = {k: v for k, v in f.items() if r[k] != v}
    if ch:
        c.execute('UPDATE plant_reminders SET ' + ','.join(f'{k}=?' for k in ch) + ' WHERE id=?', list(ch.values()) + [rid])
        words = []
        if 'due_on' in ch: words.append(f"moved from {r['due_on']} to {ch['due_on']}")
        if 'text' in ch: words.append(f"now reads \"{ch['text']}\"")
        if 'repeat_days' in ch: words.append(remind_repeat_word(ch['repeat_days']).lower())
        remind_audit(c, r, 'reminder', r['text'], ch.get('text', r['text']), f"Reminder {', '.join(words)}: {ch.get('text', r['text'])}")
        c.commit()
    return jsonify({'ok': True, 'changed': list(ch)})

@app.route('/api/reminders/<int:rid>/done', methods=['POST', 'DELETE'])
def reminder_done(rid):
    """POST: done today (a repeating one gets its next row, repeat_days after today). DELETE: "Not done yet", which takes back
    the next row too while it is untouched."""
    c = db(); r = remind_get(c, rid)
    today = local_today(c)
    if request.method == 'POST':
        if r['done_at']: return jsonify({'ok': True, 'next': None, 'already': True})
        nxt = None
        if r['repeat_days']:
            due = (today + timedelta(days=int(r['repeat_days']))).isoformat()
            nxt = c.execute('INSERT INTO plant_reminders(plant_code,loc_id,text,due_on,repeat_days,created_by,created_at) VALUES(?,?,?,?,?,?,?)',
                            (r['plant_code'], r['loc_id'], r['text'], due, r['repeat_days'], editor(), now())).lastrowid
        c.execute('UPDATE plant_reminders SET done_by=?, done_at=?, done_on=?, done_next=? WHERE id=?', (editor(), now(), today.isoformat(), nxt, rid))
        remind_audit(c, r, 'reminder_done', None, today.isoformat(), f"Reminder done: {r['text']}" + (f' (next one {due})' if nxt else ''))
        c.commit()
        return jsonify({'ok': True, 'next': due if nxt else None})
    if not r['done_at']: return jsonify({'ok': True})
    if r['done_next']:
        nx = c.execute('SELECT done_at, removed_at FROM plant_reminders WHERE id=?', (r['done_next'],)).fetchone()
        if nx and (nx['done_at'] or nx['removed_at']): abort(409, 'The next one has been changed since, so this cannot be taken back.')
        c.execute('DELETE FROM plant_reminders WHERE id=?', (r['done_next'],))
    c.execute('UPDATE plant_reminders SET done_by=NULL, done_at=NULL, done_on=NULL, done_next=NULL WHERE id=?', (rid,))
    remind_audit(c, r, 'reminder_done', r['done_on'], None, f"Reminder not done after all: {r['text']}")
    c.commit()
    return jsonify({'ok': True})
