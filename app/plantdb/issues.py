"""The Issue tracker (1.58.0; asked for by Ethan on November 15, 2026): anyone who can open the app can report a problem or an
idea from any page, and the owner reads the reports on one page.

Two things led to it. High contrast in the Light theme looked as if it did nothing, and an iPad showed version 1.55.0 for days
while the PC ran 1.57.0. Both were noticed on a device, away from the PC, and by the time they were written down the details that
explain them (which version the page was, which device, which settings, which page) had to be remembered. A report carries them.

- **Report a problem** is a button at the foot of Navigation on every page (and a card on Settings). The page sends
  `POST /api/report`: the person's notes, up to four pictures, and what the page knows about itself: the version the page is,
  the page and section it is on, this device's name (the one the Offline page keeps, typed once), what a browser can tell about
  the device, the Display settings and the other settings kept on the device. The server adds who sent it (the account, its role,
  how it is connected), the version the server is running and when it arrived.
  Everyone may send one, people who can only view included (VIEWER_POSTS in core.py): a report changes nothing of the plants. Sent
  without a connection it waits on the device like any other change (js/offline.js) and is made once (X-Offline-Op).
- **The Issue tracker** page (`#/issues`, Settings row) is the owner's alone: every route under `/api/issues` is in
  OWNER_ONLY_PATHS. A report is Open, Being looked at, Fixed (with the version) or Closed (not a fault, or not to be changed), has
  the owner's own notes, and can be copied for Claude with everything it carries.
- Pictures are kept in the photos folder as `issue_<random>.jpg`, so every backup with photos has them, and are sent only through
  `/api/issues/<id>/photo/<n>`. The photo routes everyone can use refuse those names to anyone but the owner.
- Reports stay in the app's own record. They name accounts and devices, and the repository is public, so nothing here sends them
  anywhere else."""
from .core import *   # noqa: F401,F403

ISSUES_SCHEMA = """
CREATE TABLE IF NOT EXISTS issues(
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, made_at TEXT, login TEXT, name TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT '',
  via TEXT NOT NULL DEFAULT '', addr TEXT NOT NULL DEFAULT '', page TEXT NOT NULL DEFAULT '', page_title TEXT NOT NULL DEFAULT '', section TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '', page_version TEXT NOT NULL DEFAULT '', server_version TEXT NOT NULL DEFAULT '', device TEXT NOT NULL DEFAULT '',
  info TEXT NOT NULL DEFAULT '{}', settings TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'open', fixed_in TEXT NOT NULL DEFAULT '',
  owner_notes TEXT NOT NULL DEFAULT '', seen_at TEXT, updated_at TEXT, updated_by TEXT);
CREATE TABLE IF NOT EXISTS issue_photos(id INTEGER PRIMARY KEY AUTOINCREMENT, issue_id INTEGER NOT NULL, file TEXT NOT NULL, name TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS issue_photos_issue ON issue_photos(issue_id);
"""
ISSUE_STATUS = {'open': 'Open', 'looking': 'Being looked at', 'fixed': 'Fixed', 'closed': 'Closed'}
ISSUE_MAX_NOTES, ISSUE_MAX_PHOTOS, ISSUE_MAX_JSON, ISSUE_PER_HOUR = 4000, 4, 12000, 30
ISSUE_FILE = re.compile(r'^issue_[0-9a-f]{32}\.jpg$')

def issues_tables(c): c.executescript(ISSUES_SCHEMA)          # init_db() runs this too; here for a database opened by an older mock

def issue_clip(v, n): return str(v if v is not None else '').strip()[:n]

def issue_json(v):
    """What the page sent as a list of details: kept only if it is a JSON object of plain values, and never longer than ISSUE_MAX_JSON.
    The page writes it, so it is treated as words to show, never as anything to act on."""
    try: d = json.loads(v) if isinstance(v, str) else v
    except ValueError: return '{}'
    if not isinstance(d, dict): return '{}'
    out = {}
    for k, x in list(d.items())[:80]:
        if isinstance(x, (dict, list)): x = json.dumps(x)[:600]
        elif x is None or isinstance(x, (bool, int, float)): pass
        else: x = str(x)[:600]
        out[str(k)[:60]] = x
    s = json.dumps(out)
    while len(s) > ISSUE_MAX_JSON and out:
        out.popitem(); s = json.dumps(out)
    return s

def issue_addr():
    """The address a report came from, for telling two devices of one account apart: through Tailscale, the device's own address
    in the tailnet (Serve passes it on); on this computer, the address the request came from."""
    if via_tailscale(): return issue_clip((request.headers.get('X-Forwarded-For') or '').split(',')[0], 60)
    return issue_clip(request.remote_addr, 60)

def issue_save_image(file_storage):
    try:
        im = ImageOps.exif_transpose(Image.open(file_storage.stream)).convert('RGB')        # written again, so nothing of the file's own details is kept
    except Exception:
        abort(400, f'{file_storage.filename or "That file"} is not a picture this can read (use JPG or PNG).')
    im.thumbnail((2000, 2000))                    # a screenshot's small text must stay readable
    name = f'issue_{uuid.uuid4().hex}.jpg'
    im.save(os.path.join(PHOTO_DIR, name), 'JPEG', quality=86, optimize=True)
    return name

def issue_dict(c, r):
    d = dict(r)
    for k in ('info', 'settings'):
        try: d[k] = json.loads(d[k] or '{}')
        except ValueError: d[k] = {}
    d['status_word'] = ISSUE_STATUS.get(d['status'], d['status'])
    d['role_word'] = ROLE_WORD.get(d['role'], d['role'])
    d['photos'] = [{'id': p['id'], 'name': p['name']} for p in c.execute('SELECT id, name FROM issue_photos WHERE issue_id=? ORDER BY id', (r['id'],))]
    return d

@app.before_request
def issue_photo_guard():
    """A report's pictures are in the photos folder so that backups carry them; the routes that show any photo by its name do not
    show these to anyone but the owner (the Issue tracker asks for them through /api/issues, which is the owner's)."""
    p = request.path
    if (p.startswith('/photos/') or p.startswith('/thumbs/')) and os.path.basename(p).startswith('issue_'):
        if ((getattr(g, 'user', None) or {}).get('role')) != 'owner': abort(404)

@app.route('/api/report', methods=['POST'])
def issue_report():
    """A report from any page. Form fields (or JSON): notes, page, page_title, section, page_version, device, made_at, info and
    settings (each a JSON object as text), and files (pictures). Everyone signed in may send one."""
    b = request.form if request.form or request.files else (request.get_json(silent=True) or {})
    notes = issue_clip(b.get('notes'), ISSUE_MAX_NOTES)
    files = [f for f in request.files.getlist('files') if f and f.filename]
    if not notes and not files: abort(400, 'Write what happened, or add a picture, before sending.')
    if len(files) > ISSUE_MAX_PHOTOS: abort(400, f'A report takes up to {ISSUE_MAX_PHOTOS} pictures. Send the rest in a second report.')
    u = getattr(g, 'user', None) or {'via': 'local', 'login': None, 'name': editor(), 'role': 'owner'}
    c = db()
    hour = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    if c.execute('SELECT COUNT(*) FROM issues WHERE at>=? AND COALESCE(login,\'\')=?', (hour, u.get('login') or '')).fetchone()[0] >= ISSUE_PER_HOUR:
        return jsonify(error='That is a lot of reports in one hour. Wait a little, then send the next one.'), 429
    made = issue_clip(request.headers.get('X-Offline-Made') or b.get('made_at'), 40)
    saved = [(issue_save_image(f), issue_clip(os.path.basename((f.filename or '').replace('\\', '/')), 80)) for f in files]
    cur = c.execute('INSERT INTO issues(at,made_at,login,name,role,via,addr,page,page_title,section,notes,page_version,server_version,device,info,settings) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (now(), made or None, u.get('login'), editor(), u.get('role') or '', u.get('via') or '', issue_addr(), issue_clip(b.get('page'), 300), issue_clip(b.get('page_title'), 120),
                     issue_clip(b.get('section'), 120), notes, issue_clip(b.get('page_version'), 20), APP_VERSION, issue_clip(b.get('device'), 60), issue_json(b.get('info')), issue_json(b.get('settings'))))
    iid = cur.lastrowid
    for name, orig in saved: c.execute('INSERT INTO issue_photos(issue_id,file,name) VALUES(?,?,?)', (iid, name, orig))
    audit_only(c, 'setting', 'issue', None, f'Report {iid}', editor(), f'Problem report {iid} sent from {issue_clip(b.get("page_title"), 60) or "a page"}')
    c.commit()
    return jsonify(ok=True, id=iid), 201

@app.route('/api/issues')
def issues_list():
    """Every report, newest first, with what it carries. ?brief=1: only the counts (for Today and the Settings card).
    `fresh` counts reports from other people that the owner has not seen on the Issue tracker yet."""
    c = db()
    counts = {k: 0 for k in ISSUE_STATUS}
    for r in c.execute('SELECT status, COUNT(*) FROM issues GROUP BY status'): counts[r[0] if r[0] in counts else 'open'] += r[1]
    fresh = c.execute("SELECT COUNT(*) FROM issues WHERE seen_at IS NULL AND role<>'owner'").fetchone()[0]
    if request.args.get('brief') == '1': return jsonify(counts=counts, fresh=fresh)
    rows = [issue_dict(c, r) for r in c.execute('SELECT * FROM issues ORDER BY id DESC LIMIT 500')]
    return jsonify(issues=rows, counts=counts, fresh=fresh, status_words=ISSUE_STATUS, version=APP_VERSION)

@app.route('/api/issues/seen', methods=['POST'])
def issues_seen():
    """The owner has opened the Issue tracker: Today stops announcing the reports that were new."""
    c = db(); c.execute('UPDATE issues SET seen_at=? WHERE seen_at IS NULL', (now(),)); c.commit()
    return jsonify(ok=True)

@app.route('/api/issues/<int:iid>', methods=['PUT', 'DELETE'])
def issue_one(iid):
    """PUT {status, fixed_in, owner_notes}: any of them. DELETE: the report and its pictures go."""
    c = db(); r = c.execute('SELECT * FROM issues WHERE id=?', (iid,)).fetchone()
    if not r: abort(404, 'That report is not here any more.')
    if request.method == 'DELETE':
        for p in c.execute('SELECT file FROM issue_photos WHERE issue_id=?', (iid,)).fetchall():
            if ISSUE_FILE.match(p['file']):
                for d in (PHOTO_DIR, THUMB_DIR):
                    try: os.remove(os.path.join(d, p['file']))
                    except OSError: pass
        c.execute('DELETE FROM issue_photos WHERE issue_id=?', (iid,)); c.execute('DELETE FROM issues WHERE id=?', (iid,))
        audit_only(c, 'setting', 'issue', f'Report {iid}', None, editor(), f'Problem report {iid} removed')
        c.commit()
        return jsonify(ok=True)
    b = request.get_json(silent=True) or {}
    sets, vals, said = [], [], []
    if 'status' in b:
        if b['status'] not in ISSUE_STATUS: abort(400, 'A report is Open, Being looked at, Fixed or Closed.')
        if b['status'] != r['status']: sets.append('status=?'); vals.append(b['status']); said.append(f"{ISSUE_STATUS.get(r['status'], r['status'])} to {ISSUE_STATUS[b['status']]}")
    if 'fixed_in' in b:
        v = issue_clip(b['fixed_in'], 20)
        if v and not re.fullmatch(r'\d+\.\d+\.\d+', v): abort(400, 'Write the version as three numbers, like 1.58.0.')
        if v != r['fixed_in']: sets.append('fixed_in=?'); vals.append(v); said.append(f'fixed in {v}' if v else 'fixed-in version cleared')
    if 'owner_notes' in b:
        v = issue_clip(b['owner_notes'], ISSUE_MAX_NOTES)
        if v != r['owner_notes']: sets.append('owner_notes=?'); vals.append(v); said.append('notes changed')
    if sets:
        c.execute(f"UPDATE issues SET {', '.join(sets)}, updated_at=?, updated_by=?, seen_at=COALESCE(seen_at,?) WHERE id=?", (*vals, now(), editor(), now(), iid))
        audit_only(c, 'setting', 'issue', None, f'Report {iid}', editor(), f"Problem report {iid}: {', '.join(said)}")
        c.commit()
    return jsonify(issue_dict(c, c.execute('SELECT * FROM issues WHERE id=?', (iid,)).fetchone()))

@app.route('/api/issues/<int:iid>/photo/<int:pid>')
def issue_photo(iid, pid):
    r = db().execute('SELECT file FROM issue_photos WHERE id=? AND issue_id=?', (pid, iid)).fetchone()
    if not r or not ISSUE_FILE.match(r['file']) or not os.path.exists(os.path.join(PHOTO_DIR, r['file'])): abort(404, 'That picture is not here any more.')
    return send_from_directory(PHOTO_DIR, r['file'], max_age=3600)
