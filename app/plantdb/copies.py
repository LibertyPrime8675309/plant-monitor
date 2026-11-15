"""1.33.0: a second copy of each backup, somewhere other than the PC's main drive: a folder mapped into the container (another
drive, through PLANTDB_COPY_DIR in .env) and, or, a receiver running on another computer over Tailscale (receiver/ in the
release: a small container that takes a backup with a shared token and keeps the newest twenty). Runs right after a backup is
made; the owner can set it up and try it on the Backups page."""
from .core import *   # noqa: F401,F403

COPY_DIR = os.environ.get('PLANTDB_COPY_MOUNT', '/backups-copy')     # docker-compose maps the chosen folder here
COPY_KEEP = 10

def copy_settings(c):
    return {'url': setting(c, 'backup_copy_url', ''), 'token': setting(c, 'backup_copy_token', ''), 'keep': COPY_KEEP,
            'dir': COPY_DIR if os.path.isdir(COPY_DIR) else '', 'dir_env': os.environ.get('PLANTDB_COPY_DIR', ''),
            'status': json.loads(setting(c, 'backup_copy_status', '{}') or '{}')}

def copy_away(c):
    """1.58.0: is there a copy somewhere other than the record's own drive? A folder the owner named (PLANTDB_COPY_DIR in .env;
    docker-compose passes it in from 1.58.0, the app could not see it before) or another computer. The default backups-copy
    folder sits beside the data, on the same drive, and does not count."""
    return bool(os.environ.get('PLANTDB_COPY_DIR', '').strip() and copy_dir_ok()) or bool(setting(c, 'backup_copy_url', '') and setting(c, 'backup_copy_token', ''))

def copy_dir_ok():
    """The second folder, if Docker mapped one and it is not the backups folder itself."""
    if not os.path.isdir(COPY_DIR): return False
    try: return not os.path.samefile(COPY_DIR, BACKUP_DIR)
    except OSError: return False

def copy_to_dir(name):
    src = os.path.join(BACKUP_DIR, name); dst = os.path.join(COPY_DIR, name)
    if not copy_dir_ok(): return 'no folder'
    tmp = dst + '.part'
    shutil.copyfile(src, tmp); os.replace(tmp, dst)
    old = sorted((f for f in os.listdir(COPY_DIR) if BACKUP_RE.match(f)), reverse=True)[COPY_KEEP:]
    for f in old:
        try: os.remove(os.path.join(COPY_DIR, f))
        except OSError: pass
    return 'copied'

def copy_to_receiver(c, name):
    S = copy_settings(c)
    if not (S['url'] and S['token']): return 'not set up'
    url = S['url'].rstrip('/') + '/backup/' + urllib.parse.quote(name)
    with open(os.path.join(BACKUP_DIR, name), 'rb') as f: data = f.read()
    req = urllib.request.Request(url, data=data, method='PUT', headers={'X-Backup-Token': S['token'], 'Content-Type': 'application/zip', 'Content-Length': str(len(data))})
    with urllib.request.urlopen(req, timeout=600) as r:
        j = json.loads(r.read() or b'{}')
    return f"received by {j.get('host') or 'the receiver'}" + (f", {j['kept']} kept there" if j.get('kept') else '')

def copy_backup(name):
    """Called after each backup: tries each destination and keeps the result for the Backups page. Never raises."""
    c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    try:
        st = {'file': name, 'at': now(), 'dir': '', 'receiver': ''}
        if copy_dir_ok():
            try: st['dir'] = copy_to_dir(name)
            except Exception as e: st['dir'] = f'failed: {type(e).__name__}: {e}'[:200]; problem('backup', 'The second copy to the folder failed', str(e), c)
        S = copy_settings(c)
        if S['url'] and S['token']:
            jid = job_start('copy', name)
            try: st['receiver'] = copy_to_receiver(c, name); job_end(jid, True, st['receiver'])
            except Exception as e:
                st['receiver'] = f'failed: {type(e).__name__}: {str(e)[:120]}'; job_end(jid, False, st['receiver'])
                problem('backup', "The copy to the other computer failed", f'{type(e).__name__}: {e}', c)
        set_setting(c, 'backup_copy_status', json.dumps(st)); c.commit()
    finally: c.close()

@app.route('/api/backups/copies', methods=['GET', 'PUT', 'POST'])
def backup_copies_api():
    """GET: the set-up and the last result. PUT {url, token}: the receiver on another computer (owner). POST {file?}: copy the newest
    (or named) backup now (owner)."""
    c = db()
    if request.method == 'PUT':
        b = request.get_json(silent=True) or {}
        url = str(b.get('url') or '').strip()[:300] if 'url' in b else setting(c, 'backup_copy_url', '')
        if url and not re.match(r'^https?://[^\s/]+(:\d+)?(/\S*)?$', url): abort(400, 'The address must look like http://100.1.2.3:8089')
        if 'url' in b: set_setting(c, 'backup_copy_url', url)
        if b.get('token'): set_setting(c, 'backup_copy_token', str(b['token']).strip()[:200])
        audit_only(c, 'backup', 'copies', None, url or '(off)', editor(), 'Backup copies: the other computer ' + ('set' if url else 'turned off')); c.commit()
    if request.method == 'POST':
        b = request.get_json(silent=True) or {}
        name = str(b.get('file') or '')
        if not name:
            names = sorted((f for f in os.listdir(BACKUP_DIR) if BACKUP_RE.match(f)), reverse=True)
            if not names: abort(400, 'There is no backup to copy yet.')
            name = names[0]
        if not BACKUP_RE.match(name) or not os.path.exists(os.path.join(BACKUP_DIR, name)): abort(404, 'No such backup')
        if not copy_dir_ok() and not (setting(c, 'backup_copy_url', '') and setting(c, 'backup_copy_token', '')): abort(400, 'Nowhere to copy to yet: map a folder (PLANTDB_COPY_DIR in .env) or set the other computer below.')
        copy_backup(name)
    S = copy_settings(c); S.pop('token', None); S['have_token'] = bool(setting(c, 'backup_copy_token', ''))
    S['dir_ok'] = copy_dir_ok()
    S['dir_files'] = sorted((f for f in os.listdir(COPY_DIR) if BACKUP_RE.match(f)), reverse=True)[:COPY_KEEP] if S['dir_ok'] else []
    return jsonify(S)
