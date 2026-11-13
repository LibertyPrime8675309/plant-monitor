"""1.58.0, from Ethan (November 13, 2026): the weather history has a backup of its own, on its own schedule, in pieces.

Nearly all of a database is weather history (about a million hourly rows in his, 400 of 418 MB), so every backup carried the
same 50 MB again. Now the weather is backed up apart from the rest:

- A **piece** is a zip in backups/weather/: `plantdb-weather-<stamp>-full.zip` or `...-part.zip`. It holds `weather.db` (the
  tables `readings`, `weather_daily` and `locations`, with the app's own columns) and `piece.json`. A piece never changes once
  it is written.
- The first piece is everything. Each later one holds only the **days whose weather is new or has changed** since the pieces
  before it: hourly rows are revised when a forecast hour becomes an observed one or when detail is added, so "new rows" alone
  would miss changes. A day is compared by a checksum of its rows; `piece.json` lists the checksum of every day it holds.
- All the pieces together are the whole history: read oldest first, a later piece's day replaces an earlier one's. **Combine**
  writes them into one new full piece and only then removes the ones it replaced. It happens by itself past WX_COMBINE_AT pieces.
- **Put back** (wx_fill) adds to the record whatever the pieces hold that the record lacks. It never changes or removes a row
  the record has. Places are matched by their weather device name, else by position.
- The other backups (backups.py) leave the weather out once it is covered here (wx_covered()), which makes them a few MB.
  Restoring one of those keeps the weather the record has (wx_carry()); with none to keep it is put back from the pieces.

The schedule is its own ('wx_backup' in settings): every day, 3 days, week, 2 weeks or month, at an hour. backup_loop() calls
wx_backup_tick(). Each new piece is copied to the second folder (copies.py), under weather/ there."""
from .core import *   # noqa: F401,F403
import hashlib, zipfile

WX_DIR = os.path.join(BACKUP_DIR, 'weather')
WX_RE = re.compile(r'^plantdb-weather-\d{8}-\d{6}-(full|part)\.zip$')
WX_FREQ = {'daily': 1, '3d': 3, 'weekly': 7, '2w': 14, 'monthly': 30}       # days between runs
WX_DEFAULTS = {'enabled': True, 'freq': 'weekly', 'hour': 4}
WX_COMBINE_AT = 26               # more pieces than this are combined into one after a run (half a year of weekly pieces)
WX_LOCK = threading.Lock()
WX_JOB = {'running': False}
WX_HOURLY = ('ts', 'source', 'device', 'temp_f', 'humidity', 'par', 'lux', 'soil_moisture', 'soil_temp_f', 'soil_ph', 'note', 'extra')
WX_DAILY = ('loc_id', 'date', 'data', 'kind', 'updated_at')
WX_SCHEMA = """
CREATE TABLE readings(ts TEXT NOT NULL, source TEXT NOT NULL, device TEXT NOT NULL DEFAULT '', temp_f REAL, humidity REAL, par REAL, lux REAL,
  soil_moisture REAL, soil_temp_f REAL, soil_ph REAL, note TEXT, extra TEXT, PRIMARY KEY(source, device, ts));
CREATE TABLE weather_daily(loc_id INTEGER NOT NULL, date TEXT NOT NULL, data TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'observed', updated_at TEXT NOT NULL,
  PRIMARY KEY(loc_id, date));
CREATE TABLE locations(id INTEGER PRIMARY KEY, name TEXT, lat REAL, lon REAL, tz TEXT, device TEXT);
"""

def wx_settings(c):
    try: d = json.loads(setting(c, 'wx_backup', '') or '{}')
    except ValueError: d = {}
    return {**WX_DEFAULTS, **d}

def wx_dir():
    os.makedirs(WX_DIR, exist_ok=True)
    return WX_DIR

def wx_pieces():
    """The pieces, oldest first, each with what its piece.json says (and broken: True for a zip that cannot be read)."""
    out = []
    try: names = sorted(f for f in os.listdir(WX_DIR) if WX_RE.match(f))
    except OSError: names = []
    for f in names:
        p = os.path.join(WX_DIR, f); meta = {}
        try:
            with zipfile.ZipFile(p) as z:
                meta = json.loads(z.read('piece.json'))
                if 'weather.db' not in z.namelist(): meta = {'broken': True}
        except (zipfile.BadZipFile, OSError, ValueError, KeyError): meta = {'broken': True}
        out.append({'file': f, 'bytes': os.path.getsize(p), 'kind': WX_RE.match(f).group(1), 'created_at': meta.get('created_at') or iso(os.path.getmtime(p)),
                    'version': meta.get('version'), 'by': meta.get('by', ''), 'rows': meta.get('rows', 0), 'days': meta.get('days', 0), 'first': meta.get('first', ''),
                    'last': meta.get('last', ''), 'broken': bool(meta.get('broken')), 'sigs': meta.get('sigs') or {}})
    return out

def wx_have(pieces=None):
    """{day key: checksum} of everything the pieces hold; a later piece's day replaces an earlier one's."""
    have = {}
    for p in (wx_pieces() if pieces is None else pieces):
        if not p['broken']: have.update(p['sigs'])
    return have

def wx_scan(c):
    """{day key: [checksum, rows]} of the weather in a database. Keys: 'h|<device>|<date>' for a place's hourly rows of one day,
    'd|<loc_id>|<date>' for its day summary. One pass over the hourly rows, in the order of their index."""
    out = {}; key = None; h = None; n = 0
    for r in c.execute(f"SELECT {','.join(WX_HOURLY)} FROM readings WHERE source='weather' ORDER BY device, ts"):
        k = f'h|{r[2]}|{r[0][:10]}'
        if k != key:
            if key: out[key] = [h.hexdigest()[:16], n]
            key, h, n = k, hashlib.md5(), 0
        h.update(repr(tuple(r)).encode()); n += 1
    if key: out[key] = [h.hexdigest()[:16], n]
    for r in c.execute(f"SELECT {','.join(WX_DAILY)} FROM weather_daily WHERE kind<>'forecast'"):       # a forecast is not history: it changes every hour until the day is over
        out[f'd|{r[0]}|{r[1]}'] = [hashlib.md5(repr((r[2], r[3])).encode()).hexdigest()[:16], 1]      # not updated_at: a rewrite of the same day is no change
    return out

def wx_live(c):
    r = c.execute("SELECT COUNT(*), MIN(ts), MAX(ts) FROM readings WHERE source='weather'").fetchone()
    return {'rows': r[0], 'first': (r[1] or '')[:10], 'last': (r[2] or '')[:10], 'days': c.execute('SELECT COUNT(*) FROM weather_daily').fetchone()[0]}

def wx_covered(c=None, t=None):
    """Is the weather looked after here, so the other backups may leave it out? The weather backup is on, there is a piece that can
    be read, and it has run (or made a piece) within twice its interval and a day: a weather backup that has stopped working must
    not leave the weather in no backup at all. A record with no weather is covered too: there is nothing to leave out."""
    own = c is None
    if own: c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    try:
        S = wx_settings(c)
        if not S['enabled']: return False
        good = [p for p in wx_pieces() if not p['broken']]
        if good:
            newest = max([setting(c, 'wx_backup_last', '') or ''] + [p['created_at'] for p in good])
            return ((t or datetime.now(timezone.utc)) - parse_ts(newest)).days <= 2 * WX_FREQ.get(S['freq'], 7) + 1
        return not c.execute("SELECT 1 FROM readings WHERE source='weather' LIMIT 1").fetchone() and not c.execute("SELECT 1 FROM weather_daily WHERE kind<>'forecast' LIMIT 1").fetchone()
    finally:
        if own: c.close()

def _wx_name(kind):
    """A name that sorts after every piece there is: the pieces are read in the order of their names, so a clock that was set
    back, or two pieces within one second, must not put a new piece before an old one."""
    t = datetime.now(timezone.utc).replace(microsecond=0)
    names = sorted(f for f in os.listdir(wx_dir()) if WX_RE.match(f))
    if names:
        last = datetime.strptime(names[-1][len('plantdb-weather-'):len('plantdb-weather-') + 15], '%Y%m%d-%H%M%S').replace(tzinfo=timezone.utc)
        if t <= last: t = last + timedelta(seconds=1)
    return f"plantdb-weather-{t.strftime('%Y%m%d-%H%M%S')}-{kind}.zip"

def _wx_write(name, fill, kind, by, note=''):
    """Writes one piece: fill(conn) puts the rows into an empty weather.db and returns nothing; the checksums are read back from
    what was written. Returns the piece's facts, or None when fill() put nothing in."""
    d = wx_dir(); stamp = name[len('plantdb-weather-'):-len(f'-{kind}.zip')]
    tmpdb = os.path.join(d, f'.tmp-{stamp}.db'); tmpzip = os.path.join(d, f'.tmp-{stamp}.zip')
    try:
        w = sqlite3.connect(tmpdb)
        try:
            w.executescript(WX_SCHEMA); fill(w); w.commit()
            sigs = {k: v[0] for k, v in wx_scan(w).items()}
            rows = w.execute('SELECT COUNT(*) FROM readings').fetchone()[0]; days = w.execute('SELECT COUNT(*) FROM weather_daily').fetchone()[0]
            if not rows and not days: return None
            dates = sorted(k.rsplit('|', 1)[1] for k in sigs)
            w.execute('VACUUM')
        finally: w.close()
        meta = {'created_at': now(), 'version': APP_VERSION, 'kind': kind, 'by': by, 'note': note[:300], 'rows': rows, 'days': days, 'first': dates[0], 'last': dates[-1], 'sigs': sigs,
                'about': 'One piece of the weather history. All the pieces together, read oldest first (a later piece\'s day replaces an earlier one\'s), are the whole history. See README, Backups.'}
        with zipfile.ZipFile(tmpzip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            z.write(tmpdb, 'weather.db'); z.writestr('piece.json', json.dumps(meta, separators=(',', ':')))
        with zipfile.ZipFile(tmpzip) as z:                         # read it back before it counts
            if z.testzip() is not None: raise OSError('The piece just written could not be read back.')
        os.replace(tmpzip, os.path.join(d, name))
        return {'file': name, 'rows': rows, 'days': days, 'first': dates[0], 'last': dates[-1], 'bytes': os.path.getsize(os.path.join(d, name))}
    finally:
        for t in (tmpdb, tmpzip):
            try: os.remove(t)
            except OSError: pass

def _wx_copy_days(w, src, keys):
    """Copies the whole days named in keys from the attached database `src` into the piece being written."""
    w.execute('CREATE TEMP TABLE want(k TEXT PRIMARY KEY)')
    w.executemany('INSERT OR IGNORE INTO want VALUES(?)', [(k,) for k in keys])
    cols = ','.join(WX_HOURLY)
    w.execute(f"INSERT OR REPLACE INTO readings({cols}) SELECT {cols} FROM {src}.readings r WHERE r.source='weather' AND ('h|' || r.device || '|' || substr(r.ts,1,10)) IN (SELECT k FROM want)")
    cols = ','.join(WX_DAILY)
    w.execute(f"INSERT OR REPLACE INTO weather_daily({cols}) SELECT {cols} FROM {src}.weather_daily d WHERE d.kind<>'forecast' AND ('d|' || d.loc_id || '|' || d.date) IN (SELECT k FROM want)")
    w.execute(f'INSERT OR REPLACE INTO locations(id,name,lat,lon,tz,device) SELECT id,name,lat,lon,tz,device FROM {src}.locations')
    w.execute('DROP TABLE want')

def wx_make(by='Automatic backup', note=''):
    """Makes the next piece: every day of weather that is new or has changed since the pieces before it. The first is everything.
    Returns the piece's facts with what was compared, or {'file': None, ...} when nothing is new."""
    with WX_LOCK:
        pieces = wx_pieces(); have = wx_have(pieces)
        c = sqlite3.connect(DB_PATH, timeout=60)
        try: scan = wx_scan(c)
        finally: c.close()
        changed = [k for k, v in scan.items() if have.get(k) != v[0]]
        res = {'file': None, 'compared': len(scan), 'changed': len(changed)}
        if not changed: return res
        kind = 'part' if any(not p['broken'] for p in pieces) else 'full'
        name = _wx_name(kind)
        def fill(w):
            w.execute('ATTACH DATABASE ? AS live', (DB_PATH,))            # read only here; the record is in WAL mode, so the app keeps writing meanwhile
            try: _wx_copy_days(w, 'live', changed); w.commit()
            finally: w.execute('DETACH DATABASE live')
        made = _wx_write(name, fill, kind, by, note)
        if made: res.update(made)
        return res

def _wx_apply(w, zpath, tmpdir, mode='REPLACE'):
    """Reads one piece into the open database `w` (tables with the piece's columns). mode REPLACE: the piece's rows win;
    IGNORE: rows `w` already has are left as they are. Returns the piece's locations."""
    tmp = os.path.join(tmpdir, '.apply-' + os.path.basename(zpath) + '.db')
    try:
        with zipfile.ZipFile(zpath) as z, z.open('weather.db') as src, open(tmp, 'wb') as dst: shutil.copyfileobj(src, dst)
        w.execute('ATTACH DATABASE ? AS piece', (tmp,))
        try:
            if mode == 'REPLACE':                      # the piece's day takes the place of the whole day, not only of the hours it has
                w.execute("DELETE FROM readings WHERE (device || '|' || substr(ts,1,10)) IN (SELECT DISTINCT device || '|' || substr(ts,1,10) FROM piece.readings)")
            cols = ','.join(WX_HOURLY); w.execute(f'INSERT OR {mode} INTO readings({cols}) SELECT {cols} FROM piece.readings')
            cols = ','.join(WX_DAILY); w.execute(f'INSERT OR {mode} INTO weather_daily({cols}) SELECT {cols} FROM piece.weather_daily')
            locs = [dict(zip(('id', 'name', 'lat', 'lon', 'tz', 'device'), r)) for r in w.execute('SELECT id,name,lat,lon,tz,device FROM piece.locations')]
            w.commit()
        finally: w.execute('DETACH DATABASE piece')
        return locs
    finally:
        try: os.remove(tmp)
        except OSError: pass

def wx_combine(by='Automatic backup'):
    """All the pieces into one new full piece. The old ones are removed only after the new one is written, read back and holds
    every day they held. Returns {'file', 'replaced': n} or {'file': None} when there is nothing to combine."""
    with WX_LOCK:
        pieces = [p for p in wx_pieces() if not p['broken']]
        if len(pieces) < 2: return {'file': None, 'replaced': 0}
        have = wx_have(pieces); d = wx_dir(); locs = {}
        name = _wx_name('full')
        def fill(w):
            for p in pieces:
                for L in _wx_apply(w, os.path.join(d, p['file']), d): locs[L['id']] = L
            w.executemany('INSERT OR REPLACE INTO locations(id,name,lat,lon,tz,device) VALUES(:id,:name,:lat,:lon,:tz,:device)', list(locs.values()))
        made = _wx_write(name, fill, 'full', by, f'Combined from {len(pieces)} pieces')
        if not made: return {'file': None, 'replaced': 0}
        new = next(p for p in wx_pieces() if p['file'] == name)
        if new['broken'] or new['sigs'] != have:                   # never remove a piece unless the new one holds exactly what they held
            try: os.remove(os.path.join(d, name))
            except OSError: pass
            raise ValueError('The combined piece did not match the pieces it was made from, so nothing was removed.')
        for p in pieces:
            try: os.remove(os.path.join(d, p['file']))
            except OSError: pass
        return {**made, 'replaced': len(pieces)}

def _wx_place_map(c, locs):
    """Piece place id -> (this record's place id, its device), by device name, else by position (to about 100 m)."""
    mine = [dict(r) for r in c.execute('SELECT id, lat, lon, device FROM locations')]
    out = {}
    for L in locs:
        m = next((x for x in mine if x['device'] and x['device'] == L['device']), None) \
            or next((x for x in mine if L['lat'] is not None and abs(x['lat'] - L['lat']) < 0.001 and abs(x['lon'] - L['lon']) < 0.001), None)
        if m: out[L['id']] = (m['id'], m['device'], L['device'])
    return out

def wx_fill(by='Unknown', conn=None):
    """Puts back what the pieces hold and the record lacks. Nothing the record has is changed or removed. Weather of a place the
    record no longer has is left in the pieces. Returns {'pieces', 'hourly', 'days', 'skipped_places'}."""
    with WX_LOCK:
        pieces = [p for p in wx_pieces() if not p['broken']]
        res = {'pieces': len(pieces), 'hourly': 0, 'days': 0, 'skipped_places': 0}
        if not pieces: return res
        d = wx_dir(); tmp = os.path.join(d, f".fill-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.db")
        try:
            w = sqlite3.connect(tmp)
            try:
                w.executescript(WX_SCHEMA); locs = {}
                for p in pieces:
                    for L in _wx_apply(w, os.path.join(d, p['file']), d): locs[L['id']] = L
            finally: w.close()
            c = conn or sqlite3.connect(DB_PATH, timeout=60)
            try:
                c.row_factory = sqlite3.Row
                pm = _wx_place_map(c, list(locs.values())); res['skipped_places'] = len(locs) - len(pm)
                c.execute('ATTACH DATABASE ? AS wxp', (tmp,))
                try:
                    hc = [x for x in WX_HOURLY if x != 'device']
                    for pid, (mid, mdev, pdev) in pm.items():
                        res['hourly'] += c.execute(f"INSERT OR IGNORE INTO readings(device,{','.join(hc)}) SELECT ?,{','.join(hc)} FROM wxp.readings WHERE device=?", (mdev, pdev)).rowcount
                        res['days'] += c.execute("INSERT OR IGNORE INTO weather_daily(loc_id,date,data,kind,updated_at) SELECT ?,date,data,kind,updated_at FROM wxp.weather_daily WHERE loc_id=?", (mid, pid)).rowcount
                    c.commit()
                finally: c.execute('DETACH DATABASE wxp')
                if res['hourly'] or res['days']:
                    audit_only(c, 'backup', 'weather', None, f"{res['hourly']} hourly rows, {res['days']} days", by, f"Weather history put back from its backup ({len(pieces)} file{'' if len(pieces) == 1 else 's'})"); c.commit()
            finally:
                if not conn: c.close()
        finally:
            try: os.remove(tmp)
            except OSError: pass
        return res

def wx_strip(conn):
    """Takes the weather history out of a copy of the database (the copy a backup is about to zip). The log of weather updates stays."""
    idx = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='readings' AND sql IS NOT NULL").fetchall()
    for name, _ in idx: conn.execute(f'DROP INDEX "{name}"')          # a million rows leave much faster without their four indexes; they come straight back
    conn.execute("DELETE FROM readings WHERE source='weather'"); conn.execute('DELETE FROM weather_daily')
    for _, sql in idx: conn.execute(sql)
    conn.commit(); conn.execute('VACUUM')

def wx_carry(tmpdb):
    """Before a backup without weather takes the place of the database in use: copies the weather the record has now into it, for
    the places the backup knows. Returns the number of hourly rows carried. Never raises: a restore must not fail over weather."""
    try:
        t = sqlite3.connect(tmpdb, timeout=60)
        try:
            t.execute('ATTACH DATABASE ? AS cur', (DB_PATH,))
            cols = lambda db, tb: [r[1] for r in t.execute(f'PRAGMA {db}.table_info({tb})')]
            hc = [x for x in cols('main', 'readings') if x != 'id' and x in cols('cur', 'readings')]
            n = t.execute(f"INSERT OR IGNORE INTO readings({','.join(hc)}) SELECT {','.join(hc)} FROM cur.readings WHERE source='weather' AND device IN (SELECT device FROM main.locations)").rowcount
            dc = [x for x in cols('main', 'weather_daily') if x in cols('cur', 'weather_daily')]
            t.execute(f"INSERT OR IGNORE INTO weather_daily({','.join(dc)}) SELECT {','.join(dc)} FROM cur.weather_daily WHERE loc_id IN (SELECT m.id FROM main.locations m JOIN cur.locations o ON o.id=m.id AND o.device IS m.device)")
            t.commit(); t.execute('DETACH DATABASE cur')
            return n
        finally: t.close()
    except sqlite3.Error as e:
        problem_exc('backup', e, 'The weather history could not be carried over during a restore; it can be put back from its own backup on the Backups page')
        return 0

def wx_copy_out(name=None, removed=()):
    """The second folder (copies.py) gets each new piece under weather/, and loses the pieces a combine replaced. Never raises."""
    try:
        if not copy_dir_ok(): return ''
        dst = os.path.join(COPY_DIR, 'weather'); os.makedirs(dst, exist_ok=True)
        todo = [name] if name else [p['file'] for p in wx_pieces() if not os.path.exists(os.path.join(dst, p['file']))]
        for f in todo:
            tmp = os.path.join(dst, f + '.part'); shutil.copyfile(os.path.join(WX_DIR, f), tmp); os.replace(tmp, os.path.join(dst, f))
        for f in removed:
            try: os.remove(os.path.join(dst, f))
            except OSError: pass
        return 'copied'
    except Exception as e:
        problem_exc('backup', e, 'The second copy of the weather backup failed')
        return 'failed'

def wx_run(what='make', by='Automatic backup'):
    """One run, as a job on the Jobs list: 'make' (and a combine when the pieces have piled up), 'combine' or 'fill'. Returns False
    when a run is already going."""
    if WX_JOB.get('running'): return False
    WX_JOB.clear(); WX_JOB.update(running=True, what=what, started=now())
    jid = job_start('wxbackup', {'make': 'Weather history backup', 'combine': 'Weather backup: combine the pieces', 'fill': 'Weather history: put back from its backup'}[what])
    def work():
        try:
            c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
            try:
                if what == 'fill':
                    r = wx_fill(by); text = f"{r['hourly']:,} hourly readings and {r['days']:,} day summaries put back from {r['pieces']} piece{'' if r['pieces'] == 1 else 's'}" if r['pieces'] else 'There is no weather backup to put back from yet'
                    if r['skipped_places']: text += f"; {r['skipped_places']} place{'' if r['skipped_places'] == 1 else 's'} in the backup {'is' if r['skipped_places'] == 1 else 'are'} no longer in the record"
                else:
                    before = [p['file'] for p in wx_pieces()]; text = ''; made = None
                    if what == 'make':
                        made = wx_make(by)
                        text = (f"Saved {'everything' if made['file'].endswith('-full.zip') else str(made['changed']) + ' new or changed days'}: {made['rows']:,} hourly readings and {made['days']:,} day summaries"
                                if made['file'] else f"Nothing new since the last piece ({made['compared']:,} days compared)" if made['compared'] else 'There is no weather history in the record yet')
                        if made['file']: audit_only(c, 'backup', 'weather', None, made['file'], by, f"Weather history backed up ({made['changed']} new or changed days)")
                        set_setting(c, 'wx_backup_last', now()); set_setting(c, 'wx_backup_result', text)
                    if what == 'combine' or len(wx_pieces()) > WX_COMBINE_AT:
                        cb = wx_combine(by)
                        if cb['file']:
                            text += ('. ' if text else '') + f"{cb['replaced']} pieces combined into one"
                            audit_only(c, 'backup', 'weather', None, cb['file'], by, f"Weather backup: {cb['replaced']} pieces combined into one")
                        elif what == 'combine': text = 'There is only one piece, so there is nothing to combine'
                    c.commit()
                    after = [p['file'] for p in wx_pieces()]
                    wx_copy_out(removed=[f for f in before if f not in after])
            finally: c.close()
            WX_JOB.update(running=False, ok=True, text=text, finished=now()); job_end(jid, True, text)
        except Exception as e:
            WX_JOB.update(running=False, ok=False, error=f'{type(e).__name__}: {e}'[:300], finished=now())
            job_end(jid, False, f'{type(e).__name__}: {e}'); problem_exc('backup', e, 'The weather history backup failed')
    threading.Thread(target=work, daemon=True).start()
    return True

def wx_due(c, t=None):
    S = wx_settings(c)
    if not S['enabled']: return False
    last = setting(c, 'wx_backup_last')
    if not last: return True
    t = t or datetime.now(timezone.utc); lt = parse_ts(last)
    tz = tzinfo(location(c)['tz']); lt_l, t_l = lt.astimezone(tz), t.astimezone(tz)
    days = WX_FREQ.get(S['freq'], 7); due_day = lt_l.date() + timedelta(days=days)
    return t_l.date() > due_day or (t_l.date() == due_day and t_l.hour >= int(S['hour']))

WX_AUTOFILL = {'tried': False}

def wx_backup_tick(c):
    """Called by backup_loop() every few minutes. A record with no weather at all and pieces to hand (a database put in place by
    hand, a new computer with the backups folder copied over) gets its weather back first, once per run of the app."""
    if WX_JOB.get('running') or BK_JOB.get('running'): return
    if not WX_AUTOFILL['tried'] and not c.execute("SELECT 1 FROM readings WHERE source='weather' LIMIT 1").fetchone() and any(not p['broken'] for p in wx_pieces()):
        WX_AUTOFILL['tried'] = True; wx_run('fill', 'Plant record'); return
    WX_AUTOFILL['tried'] = True
    if wx_due(c): wx_run('make', 'Automatic backup')

@app.route('/api/backups/weather', methods=['GET', 'POST'])
def wx_backup_api():
    """GET: the pieces, the settings and where things stand. POST {what: make | combine | fill}: start that run (owner, like every
    address under /api/backups)."""
    c = db()
    if request.method == 'POST':
        what = str((request.get_json(silent=True) or {}).get('what') or 'make')
        if what not in ('make', 'combine', 'fill'): abort(400, 'Unknown action')
        if BK_JOB.get('running'): abort(409, 'A backup is being made. Try again in a moment.')
        started = wx_run(what, editor())
        return jsonify(started=started, job=dict(WX_JOB)), (202 if started else 409)
    pieces = wx_pieces(); have = wx_have(pieces)
    for p in pieces: p.pop('sigs')
    return jsonify(settings=wx_settings(c), freqs=list(WX_FREQ), pieces=pieces[::-1], total_bytes=sum(p['bytes'] for p in pieces), held_days=len(have), live=wx_live(c),
                   last=setting(c, 'wx_backup_last', ''), result=setting(c, 'wx_backup_result', ''), covered=wx_covered(c), combine_at=WX_COMBINE_AT, job=dict(WX_JOB), dir=WX_DIR)

@app.route('/api/backups/weather/settings', methods=['PUT'])
def wx_backup_settings_put():
    c = db(); b = request.get_json(silent=True) or {}; S = wx_settings(c)
    if 'enabled' in b: S['enabled'] = bool(b['enabled'])
    if 'freq' in b:
        if b['freq'] not in WX_FREQ: abort(400, 'Unknown frequency')
        S['freq'] = b['freq']
    if 'hour' in b:
        try: v = int(b['hour'])
        except (TypeError, ValueError): abort(400, 'hour must be a whole number')
        if not 0 <= v <= 23: abort(400, 'hour must be between 0 and 23')
        S['hour'] = v
    old = setting(c, 'wx_backup', '')
    set_setting(c, 'wx_backup', json.dumps(S))
    audit_only(c, 'setting', 'wx_backup', old, json.dumps(S), editor(), 'Weather history backup settings changed'); c.commit()
    return jsonify(settings=S)

@app.route('/api/backups/weather/job')
def wx_backup_job():
    return jsonify(dict(WX_JOB))

@app.route('/api/backups/weather/<name>')
def wx_backup_file(name):
    if not WX_RE.match(name) or not os.path.exists(os.path.join(WX_DIR, name)): abort(404, 'No such file')
    return send_from_directory(WX_DIR, name, as_attachment=True, mimetype='application/zip')
