"""1.37.0: the mirror. A second copy of the app on another machine (the spare hardware, or the girlfriend's PC) that keeps
itself up to date from the backups the receiver gets, and is read-only: everyone is a viewer, every change is refused with a
note saying where the main app is. It runs the same image with PLANTDB_MIRROR=1 and the receiver's folder mounted at
/mirror-in; every few minutes it restores the newest backup there (database, and any photos the backup carries)."""
from .core import *   # noqa: F401,F403

MIRROR = os.environ.get('PLANTDB_MIRROR', '') == '1'
MIRROR_IN = os.environ.get('PLANTDB_MIRROR_IN', '/mirror-in')
MIRROR_MAIN = os.environ.get('PLANTDB_MIRROR_MAIN', '')          # the main app's address, for the note on every page
MIRROR_EVERY = int(os.environ.get('PLANTDB_MIRROR_MINUTES', '5') or 5)
MIRROR_STATE = {'last': '', 'at': '', 'error': '', 'checked': ''}

def mirror_newest():
    try: names = [f for f in os.listdir(MIRROR_IN) if BACKUP_RE.match(f)]
    except OSError: return None
    if not names: return None
    return max(names, key=lambda f: os.path.getmtime(os.path.join(MIRROR_IN, f)))

def mirror_once():
    """Restore the newest backup in the receiver's folder, if it is not the one already shown."""
    name = mirror_newest()
    MIRROR_STATE['checked'] = now()
    if not name: MIRROR_STATE['error'] = 'No backup in the receiver folder yet.'; return
    c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    try:
        last = setting(c, 'mirror_last', '')
        if name == last: MIRROR_STATE.update(last=last, at=setting(c, 'mirror_at', ''), error=''); return
        dst = os.path.join(BACKUP_DIR, name)
        if not os.path.exists(dst): shutil.copyfile(os.path.join(MIRROR_IN, name), dst)
    finally: c.close()
    jid = job_start('mirror', name)
    try:
        r = restore_backup(name, 'Mirror', before=False)
        c = sqlite3.connect(DB_PATH, timeout=30)
        try: set_setting(c, 'mirror_last', name); set_setting(c, 'mirror_at', now()); c.commit()
        finally: c.close()
        MIRROR_STATE.update(last=name, at=now(), error='')
        job_end(jid, True, f"{r.get('plants', '?')} plants")
        for f in sorted(os.listdir(BACKUP_DIR)):           # the mirror keeps only the backup it shows
            if BACKUP_RE.match(f) and f != name:
                try: os.remove(os.path.join(BACKUP_DIR, f))
                except OSError: pass
    except Exception as e:
        MIRROR_STATE['error'] = f'{type(e).__name__}: {e}'[:200]; job_end(jid, False, MIRROR_STATE['error'])
        problem_exc('mirror', e, 'The mirror could not take the newest backup')

def mirror_loop():
    time.sleep(20)
    while True:
        try: mirror_once()
        except Exception as e: problem_exc('mirror', e, 'The mirror check failed')
        time.sleep(MIRROR_EVERY * 60)

def mirror_info(c=None):
    """For /api/meta and the note on every page."""
    if not MIRROR: return None
    last = MIRROR_STATE['last'] or (setting(c, 'mirror_last', '') if c else '')
    m = re.match(r'^plantdb-backup-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})', last or '')
    made = f'{m[1]}-{m[2]}-{m[3]}T{m[4]}:{m[5]}:{m[6]}Z' if m else ''
    return {'on': True, 'last': last, 'made': made, 'at': MIRROR_STATE['at'] or (setting(c, 'mirror_at', '') if c else ''),
            'main': MIRROR_MAIN, 'error': MIRROR_STATE['error'], 'checked': MIRROR_STATE['checked'], 'every': MIRROR_EVERY}

@app.route('/api/mirror')
def mirror_api():
    return jsonify(mirror_info(db()) or {'on': False})
