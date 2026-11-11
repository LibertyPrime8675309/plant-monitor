"""Problems in background jobs (the Problems list on Settings): problem(), problem_exc() and /api/problems.
In weather.py until 1.57.0 (review item 25), where any module could call them but nobody looked for them."""
from .core import *   # noqa: F401,F403

PROBLEM_AREA = {'weather': 'Weather update', 'backup': 'Backup', 'shops': 'Shopping check', 'stores': 'Store look-up', 'library': 'Library download',
                'know': 'Library lookups', 'offline': 'Offline changes', 'vision': 'Picture checker', 'gzip': 'Sending a page', 'start': 'Starting the app', 'push': 'Notifications', 'sensors': 'Sensors', 'mirror': 'Mirror'}
def problem(area, text, detail='', conn=None):
    """1.31.0: a problem in a background job, kept for the Problems list on Settings (the last 200). The same problem again
    within a day counts up instead of adding a line. Never raises: it is called from places that are already failing."""
    text = str(text)[:300]; detail = str(detail)[:2000]
    print(f'[{area}] {text}' + (f' ({detail[:200]})' if detail else ''), flush=True)
    try:
        c = conn or sqlite3.connect(DB_PATH, timeout=10)
        try:
            r = c.execute("SELECT id FROM problems WHERE area=? AND text=? AND cleared_at IS NULL AND at>=? ORDER BY id DESC LIMIT 1",
                          (area, text, (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ'))).fetchone()
            if r: c.execute('UPDATE problems SET times=times+1, at=?, detail=? WHERE id=?', (now(), detail, r[0]))
            else:
                c.execute('INSERT INTO problems(area,text,detail,at) VALUES(?,?,?,?)', (area, text, detail, now()))
                c.execute('DELETE FROM problems WHERE id NOT IN (SELECT id FROM problems ORDER BY id DESC LIMIT 200)')
            if conn is None: c.commit()
        finally:
            if conn is None: c.close()
    except Exception as e:
        print('[problems] could not be kept:', e, flush=True)

def problem_exc(area, e, what=''):
    """Records an exception in plain words: what was being done, then the error's own words as the detail."""
    import traceback
    problem(area, (what + ': ' if what else '') + (getattr(e, 'description', None) or f'{type(e).__name__}: {e}'), ''.join(traceback.format_exception(e))[-2000:])

@app.route('/api/problems', methods=['GET', 'POST'])
def problems_api():
    """GET: problems not cleared, newest first. POST {id} or {all: true}: clear (owner)."""
    c = db()
    if request.method == 'POST':
        b = request.get_json(silent=True) or {}
        if b.get('all'): c.execute('UPDATE problems SET cleared_at=? WHERE cleared_at IS NULL', (now(),))
        else: c.execute('UPDATE problems SET cleared_at=? WHERE id=? AND cleared_at IS NULL', (now(), int(b.get('id') or 0)))
        c.commit()
    rows = [dict(r) | {'area_word': PROBLEM_AREA.get(r['area'], r['area'])} for r in c.execute('SELECT * FROM problems WHERE cleared_at IS NULL ORDER BY at DESC, id DESC LIMIT 50')]
    if request.args.get('all') == '1': rows = [dict(r) | {'area_word': PROBLEM_AREA.get(r['area'], r['area'])} for r in c.execute('SELECT * FROM problems ORDER BY at DESC, id DESC LIMIT 200')]
    return jsonify(problems=rows, open=c.execute('SELECT COUNT(*) FROM problems WHERE cleared_at IS NULL').fetchone()[0])
