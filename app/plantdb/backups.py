"""Backups and restore.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- backups
import zipfile
BACKUP_RE = re.compile(r'^plantdb-backup-\d{8}-\d{6}-(manual|auto|update)(-photos)?\.zip$')
BK_LOCK = threading.Lock()
BK_JOB = {'running': False}
BK_FREQ = {'6h': 6, '12h': 12, 'daily': 24, '3d': 72, 'weekly': 168}
BK_DEFAULTS = {'enabled': True, 'freq': 'daily', 'hour': 3, 'keep': 14, 'photos': True}    # 1.58.0: photos are in unless turned off (they were left out)
KEEP_UPDATES = 5                 # 1.58.0: backups made before an update were never removed; the newest few are kept
PHOTOS_ONCE_MAX = 1024 ** 3      # the one-time switch to photos-included is skipped above this much (every backup carries them all)

def bk_settings(c):
    try: d = json.loads(setting(c, 'backup_settings', '') or '{}')
    except ValueError: d = {}
    return {**BK_DEFAULTS, **d}

def bk_list():
    out = []
    for f in os.listdir(BACKUP_DIR):
        if not BACKUP_RE.match(f): continue
        st = os.stat(os.path.join(BACKUP_DIR, f))
        m = BACKUP_RE.match(f)
        meta = {}
        try:
            with zipfile.ZipFile(os.path.join(BACKUP_DIR, f)) as z:
                if 'backup.json' in z.namelist(): meta = json.loads(z.read('backup.json'))
        except (zipfile.BadZipFile, OSError, ValueError): meta = {'broken': True}
        out.append({'file': f, 'bytes': st.st_size, 'kind': m.group(1), 'photos': bool(m.group(2)), 'created_at': meta.get('created_at') or iso(st.st_mtime),
                    'version': meta.get('version'), 'note': meta.get('note', ''), 'by': meta.get('by', ''), 'plants': meta.get('plants'), 'broken': meta.get('broken', False)})
    return sorted(out, key=lambda x: x['file'], reverse=True)

def make_backup(kind='manual', photos=False, note='', by='Unknown'):
    """A consistent copy of the database (SQLite's own backup, safe while the app runs), zipped, optionally with the photos."""
    with BK_LOCK:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        name = f'plantdb-backup-{stamp}-{kind}{"-photos" if photos else ""}.zip'
        tmpdb = os.path.join(BACKUP_DIR, f'.tmp-{stamp}.db')
        tmpzip = os.path.join(BACKUP_DIR, f'.tmp-{stamp}.zip')
        try:
            src = sqlite3.connect(DB_PATH, timeout=60); dst = sqlite3.connect(tmpdb)
            with dst: src.backup(dst)
            plants = dst.execute('SELECT COUNT(*) FROM plants').fetchone()[0]
            src.close(); dst.close()
            meta = {'created_at': now(), 'version': APP_VERSION, 'kind': kind, 'photos': photos, 'note': note[:300], 'by': by, 'plants': plants,
                    'restore': 'Stop the app, put plants.db in the data folder (and the photos folder, if included), then start the app. See README, Backups.'}
            with zipfile.ZipFile(tmpzip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                z.write(tmpdb, 'plants.db')
                z.writestr('backup.json', json.dumps(meta, indent=1))
                if photos:
                    for f in sorted(os.listdir(PHOTO_DIR)):
                        fp = os.path.join(PHOTO_DIR, f)
                        if os.path.isfile(fp): z.write(fp, 'photos/' + f, compress_type=zipfile.ZIP_STORED)   # photos are already compressed
            os.replace(tmpzip, os.path.join(BACKUP_DIR, name))
        finally:
            for t in (tmpdb, tmpzip):
                try: os.remove(t)
                except OSError: pass
        return name

def prune_backups(keep):
    """Removes automatic backups beyond `keep` and, from 1.58.0, backups made before an update beyond KEEP_UPDATES (they piled up:
    one for every version installed). Backups a person made are never removed."""
    lst = bk_list()
    old = [b for b in lst if b['kind'] == 'auto'][keep:] + [b for b in lst if b['kind'] == 'update'][KEEP_UPDATES:]
    removed = []
    for b in old:
        try: os.remove(os.path.join(BACKUP_DIR, b['file'])); removed.append(b['file'])
        except OSError: pass
    return removed

def photo_bytes():
    return sum(os.path.getsize(os.path.join(PHOTO_DIR, f)) for f in os.listdir(PHOTO_DIR) if os.path.isfile(os.path.join(PHOTO_DIR, f)))

def backup_photos_once(c):
    """1.58.0: automatic backups left the photos out unless a box was ticked, so a record could have weeks of backups and not
    one of them with its photos. They are in from now on (BK_DEFAULTS). A record whose saved settings still say no is switched
    over once, unless its photos are over a gigabyte (each backup carries them all; the Backups page says they are left out
    instead). Unticking the box afterwards is kept. Called by init_db()."""
    if setting(c, 'backup_photos_once'): return
    raw = setting(c, 'backup_settings', '')
    try: d = json.loads(raw or '{}')
    except ValueError: d = {}
    if d.get('photos') is False and photo_bytes() <= PHOTOS_ONCE_MAX:
        d['photos'] = True
        set_setting(c, 'backup_settings', json.dumps(d))
        audit_only(c, 'setting', 'backup_settings', raw, json.dumps(d), 'Plant record',
                   'Automatic backups now include the photos (1.58.0). Untick the box on the Backups page if you do not want that.')
    set_setting(c, 'backup_photos_once', now()); c.commit()

def backup_notes(c):
    """1.58.0: what the owner should know about how safe the backups are; [] when all is well. The pages put the words to each
    key (bkNote() in ui.js): 'off' no automatic backups, 'photos' they leave the photos out, 'one-drive' every copy is on the
    drive the record itself is on (no folder named in PLANTDB_COPY_DIR and no other computer set)."""
    S = bk_settings(c); out = []
    if not S['enabled']: out.append({'key': 'off'})
    elif not S['photos']:
        with_photos = next((b for b in bk_list() if b['photos'] and not b['broken']), None)
        out.append({'key': 'photos', 'photos': c.execute('SELECT COUNT(*) FROM photos').fetchone()[0], 'bytes': photo_bytes(),
                    'last': with_photos['created_at'] if with_photos else ''})
    if not copy_away(c): out.append({'key': 'one-drive'})
    return out

def run_backup_job(kind, photos, note, by):
    if BK_JOB.get('running'): return False
    BK_JOB.clear(); BK_JOB.update(running=True, kind=kind, started=now(), photos=photos)
    jid = job_start('backup', ('with photos' if photos else 'database only') + (', automatic' if kind == 'auto' else ''))
    def work():
        try:
            name = make_backup(kind, photos, note, by)
            c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
            try:
                removed = prune_backups(bk_settings(c)['keep']) if kind in ('auto', 'update') else []
                if kind == 'auto': set_setting(c, 'backup_last_auto', now())
                audit_only(c, 'backup', 'backup', None, name, by, f'Backup made ({kind}{", with photos" if photos else ""})' + (f'; removed {len(removed)} old automatic and before-update backup(s)' if removed else ''))
                c.commit()
            finally: c.close()
            BK_JOB.update(running=False, ok=True, file=name, finished=now())
            job_end(jid, True, name)
            copy_backup(name)                                  # 1.33.0: the second copy, if one is set up
        except Exception as e:
            BK_JOB.update(running=False, ok=False, error=f'{type(e).__name__}: {e}'[:300], finished=now())
            job_end(jid, False, f'{type(e).__name__}: {e}')
            problem_exc('backup', e, 'The backup failed')
    threading.Thread(target=work, daemon=True).start()
    return True

def backup_due(c, t=None):
    S = bk_settings(c)
    if not S['enabled']: return False
    last = setting(c, 'backup_last_auto')
    t = t or datetime.now(timezone.utc)
    if not last: return True
    lt = parse_ts(last)
    hours = BK_FREQ.get(S['freq'], 24)
    if hours < 24: return (t - lt).total_seconds() >= hours * 3600 - 60
    # daily or longer: at (or after) the chosen local hour, once enough days have passed
    tz = tzinfo(location(c)['tz'])
    lt_l, t_l = lt.astimezone(tz), t.astimezone(tz)
    due_day = lt_l.date() + timedelta(days=hours // 24)
    return t_l.date() > due_day or (t_l.date() == due_day and t_l.hour >= int(S['hour'])) or (t - lt).total_seconds() > (hours + 24) * 3600

def backup_loop():
    time.sleep(60)
    while True:
        try:
            c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
            try:
                if backup_due(c) and not BK_JOB.get('running'):
                    run_backup_job('auto', bk_settings(c)['photos'], 'Automatic backup', 'Automatic backup')
            finally: c.close()
        except Exception as e: problem_exc('backup', e, 'The automatic backup could not be started')
        time.sleep(300)

@app.route('/api/backups', methods=['GET', 'POST'])
def backups():
    c = db()
    if request.method == 'POST':
        b = request.get_json(silent=True) or {}
        kind = 'update' if b.get('kind') == 'update' else 'manual'
        if b.get('wait'):                         # the updater waits for the file before it touches anything
            if BK_JOB.get('running'): abort(409, 'A backup is already running')
            name = make_backup(kind, bool(b.get('photos')), str(b.get('note', '')), editor())
            removed = prune_backups(bk_settings(c)['keep']) if kind == 'update' else []       # 1.58.0: the newest few before-update backups are kept
            audit_only(c, 'backup', 'backup', None, name, editor(), f'Backup made ({kind})' + (f'; removed {len(removed)} old automatic and before-update backup(s)' if removed else '')); c.commit()
            return jsonify(file=name, path=os.path.join(BACKUP_DIR, name)), 201
        started = run_backup_job(kind, bool(b.get('photos')), str(b.get('note', '')), editor())
        return jsonify(started=started, job=dict(BK_JOB)), (202 if started else 409)
    S = bk_settings(c)
    lst = bk_list()
    free = shutil.disk_usage(BACKUP_DIR)
    return jsonify(backups=lst, settings=S, job=dict(BK_JOB), last_auto=setting(c, 'backup_last_auto'), dir=BACKUP_DIR,
                   mounted=BACKUP_DIR == '/backups', total_bytes=sum(x['bytes'] for x in lst), free_bytes=free.free,
                   db_bytes=os.path.getsize(DB_PATH), photo_bytes=photo_bytes(), freqs=list(BK_FREQ), keep_updates=KEEP_UPDATES, notes=backup_notes(c))

@app.route('/api/backups/settings', methods=['PUT'])
def backup_settings_put():
    c = db()
    b = request.get_json(silent=True) or {}
    S = bk_settings(c)
    if 'enabled' in b: S['enabled'] = bool(b['enabled'])
    if 'freq' in b:
        if b['freq'] not in BK_FREQ: abort(400, 'Unknown frequency')
        S['freq'] = b['freq']
    for k, lo, hi in (('hour', 0, 23), ('keep', 1, 365)):
        if k in b:
            try: v = int(b[k])
            except (TypeError, ValueError): abort(400, f'{k} must be a whole number')
            if not lo <= v <= hi: abort(400, f'{k} must be between {lo} and {hi}')
            S[k] = v
    if 'photos' in b: S['photos'] = bool(b['photos'])
    old = setting(c, 'backup_settings', '')
    set_setting(c, 'backup_settings', json.dumps(S))
    audit_only(c, 'setting', 'backup_settings', old, json.dumps(S), editor(), 'Automatic backup settings changed')
    c.commit()
    return jsonify(settings=S)

@app.route('/api/backups/job')
def backup_job():
    return jsonify(dict(BK_JOB))

@app.route('/api/backups/<name>', methods=['GET', 'DELETE'])
def backup_file(name):
    if not BACKUP_RE.match(name) or not os.path.exists(os.path.join(BACKUP_DIR, name)): abort(404, 'No such backup')
    if request.method == 'DELETE':
        os.remove(os.path.join(BACKUP_DIR, name))
        c = db(); audit_only(c, 'backup', 'backup', name, None, editor(), 'Backup deleted'); c.commit()
        return jsonify(ok=True)
    return send_from_directory(BACKUP_DIR, name, as_attachment=True, mimetype='application/zip')

def restore_backup(name, by, before=True):
    """1.31.0: puts the database from a backup zip in place of the one in use, after making a backup of that one first. Photos in
    the zip that the photos folder lacks are added; no photo is ever removed. The copy is made with SQLite's own backup, which is
    safe while the app runs, and then init_db() brings an older database up to this version. Returns what was done."""
    path = os.path.join(BACKUP_DIR, name)
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if 'plants.db' not in names: raise ValueError('That zip has no plants.db in it.')
        meta = json.loads(z.read('backup.json')) if 'backup.json' in names else {}
        if version_tuple(meta.get('version', '0')) > version_tuple(APP_VERSION):
            raise ValueError(f'That backup was made by version {meta.get("version")}, which is newer than this one ({APP_VERSION}). Install that version (or a newer one) first, then restore.')
        tmpdb = os.path.join(BACKUP_DIR, f'.restore-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}.db')
        try:
            with z.open('plants.db') as src, open(tmpdb, 'wb') as dst: shutil.copyfileobj(src, dst)
            t = sqlite3.connect(tmpdb)
            try:
                if t.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('The database in that backup is damaged and cannot be restored.')
                if not t.execute("SELECT 1 FROM sqlite_master WHERE name='plants'").fetchone(): raise ValueError('That is not a plant record database.')
                plants = t.execute('SELECT COUNT(*) FROM plants').fetchone()[0]
            finally: t.close()
            before_name = make_backup('manual', False, f'Before restoring {name}', by) if before else None
            with BK_LOCK:
                src = sqlite3.connect(tmpdb); dst = sqlite3.connect(DB_PATH, timeout=60)
                try:
                    with dst: src.backup(dst)
                finally: src.close(); dst.close()
            added = 0
            for n in names:
                if n.startswith('photos/') and not n.endswith('/'):
                    f = os.path.basename(n); fp = os.path.join(PHOTO_DIR, f)
                    if f and not os.path.exists(fp):
                        with z.open(n) as src, open(fp, 'wb') as out: shutil.copyfileobj(src, out)
                        added += 1
        finally:
            try: os.remove(tmpdb)
            except OSError: pass
    init_db()                                      # an older backup gets this version's columns, tables and batches
    c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    try:
        audit_only(c, 'backup', 'restore', None, name, by, f'Restored from {name} ({plants} plants, made {meta.get("created_at", "")[:10]} by version {meta.get("version", "?")}).' + (f' The database from before is in {before_name}.' if before_name else ' No backup was made of the database from before.'))   # 1.56.5: it said "is in True"
        c.commit()
    finally: c.close()
    try:                                                            # 1.55.0 (PLAN.md step 7): a restore is the quarterly restore test
        c2 = sqlite3.connect(DB_PATH, timeout=30); c2.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('restore_tested_at',?)", (now(),)); c2.commit(); c2.close()
    except sqlite3.Error: pass
    return {'ok': True, 'before': before_name, 'plants': plants, 'photos_added': added, 'version': meta.get('version'), 'restore_tested_at': now()}

@app.route('/api/backups/restore', methods=['POST'])
def backup_restore():
    b = request.get_json(silent=True) or {}
    name = str(b.get('file') or '')
    if not BACKUP_RE.match(name) or not os.path.exists(os.path.join(BACKUP_DIR, name)): abort(404, 'No such backup')
    if BK_JOB.get('running'): abort(409, 'A backup is being made. Try again in a moment.')
    jid = job_start('restore', name)
    try: r = restore_backup(name, editor()); job_end(jid, True, f'{r["plants"]} plants')
    except (ValueError, zipfile.BadZipFile) as e: job_end(jid, False, str(e)); abort(400, str(e))
    except Exception as e:
        job_end(jid, False, f'{type(e).__name__}: {e}')
        problem_exc('backup', e, f'Restoring {name} failed')
        abort(500, f'The restore failed part way: {type(e).__name__}: {e}. The database from before was backed up first; see the Problems list on Settings.')
    return jsonify(r)
