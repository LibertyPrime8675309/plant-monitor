"""The release rhythm (1.55.0, PLAN.md step 7): what is new, what is waiting, and the quarterly restore test.

From 1.55.0 a release is made by GitHub, not by hand: a push to main with a new VERSION makes a GitHub Release `v<version>`
with the release zip and any new photo packs attached (.github/workflows/release.yml), and the images are published as
before (images.yml). The updater on a PC asks GitHub for the newest release, downloads what the versions folder lacks, and
installs it. One minor release a month, on the first; patches only for something broken.

This module gives the app three small things, all shown on Today through the feature registry (js/releases.js):
- "What's new": the CHANGELOG entry for the version that is running, until the person says they have seen it (pref
  `seen_version`), so nobody has to go looking after an update.
- "An update is ready": twice a day the app asks GitHub for the newest release (PLANTDB_UPDATES=0 turns it off; the
  mock does) and tells the owner when it is newer than the one running.
- "Test a restore": a restore from the Backups page counts as a test (restore_backup records it); when none has been
  done for a quarter, the owner gets a line on Today."""
import html, json, os, re, sqlite3, time, urllib.request
from .core import *   # noqa: F401,F403

REPO = os.environ.get('PLANTDB_REPO', 'LibertyPrime8675309/plant-monitor')
CHANGELOG_PATHS = [os.path.join(APP_DIR, 'CHANGELOG.md'), os.path.join(os.path.dirname(APP_DIR), 'CHANGELOG.md')]
RESTORE_DAYS = 90

def changelog_entry(version=None):
    """{version, date, lines[]} for one entry of CHANGELOG.md (the running version by default; the top entry when that one is
    not in the file), or None. Lines are the entry's paragraphs and bullets, Markdown kept (the page renders **bold**)."""
    text = None
    for p in CHANGELOG_PATHS:
        try:
            with open(p, encoding='utf-8') as f: text = f.read(); break
        except OSError: continue
    if not text: return None
    entries = re.split(r'^## ', text, flags=re.M)[1:]
    want = version or APP_VERSION
    pick = None
    for e in entries:
        head, _, body = e.partition('\n')
        m = re.match(r'(\d+\.\d+\.\d+)\s*(?:\(([^)]*)\))?', head)
        if not m: continue
        if m.group(1) == want: pick = (m.group(1), m.group(2) or '', body); break
        if pick is None and version is None: pick = (m.group(1), m.group(2) or '', body)   # the top entry, in case the running one is missing
    if not pick: return None
    lines = [l.strip() for l in pick[2].strip().splitlines() if l.strip()]
    lines = [re.sub(r'^[-*]\s+', '', l) for l in lines if not l.startswith('#')]
    return {'version': pick[0], 'date': pick[1], 'lines': lines[:40]}      # 1.56.0: three steps in one release

# ---- the newest release on GitHub, checked twice a day
def check_latest(c=None):
    """Asks GitHub for the newest release and keeps it as the setting latest_release = {version, url, published, checked}."""
    try:
        req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/releases/latest', headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'plant-record/' + APP_VERSION})
        with urllib.request.urlopen(req, timeout=20) as r: d = json.loads(r.read())
        tag = str(d.get('tag_name') or '').lstrip('v')
        if not re.fullmatch(r'\d+\.\d+\.\d+', tag): return None
        info = {'version': tag, 'url': d.get('html_url') or f'https://github.com/{REPO}/releases', 'published': (d.get('published_at') or '')[:10], 'checked': now(),
                'assets': [a.get('name') for a in d.get('assets') or [] if a.get('name')]}
    except Exception as e:
        info = None; print('[releases] GitHub not reachable:', repr(e), flush=True)
    own = c is None
    c = c or sqlite3.connect(DB_PATH, timeout=30)
    try:
        if info: c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('latest_release',?)", (json.dumps(info),))
        else: c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('latest_release_failed',?)", (now(),))
        c.commit()
    finally:
        if own: c.close()
    return info

def updates_loop():
    time.sleep(90)
    while True:
        check_latest()
        time.sleep(12 * 3600)

def newer(a, b):
    """True when version a is newer than b."""
    try: return tuple(int(x) for x in a.split('.')) > tuple(int(x) for x in b.split('.'))
    except ValueError: return False

@app.route('/api/whatsnew')
def whatsnew():
    """What Today needs: the running version's CHANGELOG entry and whether this person has seen it; the newest release on GitHub
    when it is newer than the one running (owner); days since a restore was last tried (owner)."""
    c = db()
    login = prefs_login(c)
    row = c.execute('SELECT value FROM user_prefs WHERE login=? AND key=?', (login, 'seen_version')).fetchone()
    seen = row[0] if row else None
    entry = changelog_entry()
    latest = None
    try: latest = json.loads(setting(c, 'latest_release', '') or 'null')
    except ValueError: latest = None
    u = getattr(g, 'user', None) or {}
    role = u.get('role') or 'owner'
    out = {'version': APP_VERSION, 'entry': entry, 'seen': seen == APP_VERSION,
           'update': {'version': latest['version'], 'url': latest['url'], 'published': latest['published']} if latest and newer(latest['version'], APP_VERSION) and role == 'owner' else None}
    if role == 'owner':
        last = setting(c, 'restore_tested_at', '')
        days = None
        if last:
            try: days = int((time.time() - time.mktime(time.strptime(last[:10], '%Y-%m-%d'))) // 86400)
            except ValueError: days = None
        out['restore'] = {'last': last or None, 'days': days, 'due': days is None or days >= RESTORE_DAYS}
    return jsonify(out)

@app.route('/api/whatsnew/seen', methods=['POST'])
def whatsnew_seen():
    """Got it: this person has read this version's news (a pref, so it follows them)."""
    c = db()
    c.execute('INSERT OR REPLACE INTO user_prefs(login,key,value,updated_at) VALUES(?,?,?,?)', (prefs_login(c), 'seen_version', APP_VERSION, now()))
    c.commit()
    return jsonify(ok=True)

@app.route('/api/whatsnew/all')
def whatsnew_all():
    """The whole CHANGELOG as a plain page (large print follows the browser), for "every version's changes"."""
    text = None
    for p in CHANGELOG_PATHS:
        try:
            with open(p, encoding='utf-8') as f: text = f.read(); break
        except OSError: continue
    if not text: abort(404, 'The list of changes is not in this install.')
    out = []
    for line in text.splitlines():
        if line.startswith('# '): out.append(f'<h1>{html.escape(line[2:])}</h1>')
        elif line.startswith('## '): out.append(f'<h2>{html.escape(line[3:])}</h2>')
        elif re.match(r'^[-*] ', line): out.append('<li>' + re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html.escape(line[2:])) + '</li>')
        elif line.strip(): out.append('<p>' + re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html.escape(line)) + '</p>')
    body = re.sub(r'(<li>.*?</li>)(?=(?:<li>)|$)', r'\1', '\n'.join(out))
    body = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', body)
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Plant record: what changed</title>'
            '<style>body{font:120%/1.5 system-ui,sans-serif;max-width:52rem;margin:1.5rem auto;padding:0 1rem;color:#111;background:#fff}h2{margin-top:2rem}@media (prefers-color-scheme: dark){body{color:#eee;background:#111}}</style></head><body>'
            + body + '</body></html>')
    return Response(page, mimetype='text/html')
