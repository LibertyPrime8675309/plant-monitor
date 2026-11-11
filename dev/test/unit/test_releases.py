"""1.55.0 (PLAN.md step 7): the release rhythm. The CHANGELOG entry for the running version, "Got it" per person, the newer
release GitHub reports (owner only), the quarterly restore test (a restore records it), and the every-version page."""
import io, json, os, tempfile
import server as S

ED = {'X-Editor': 'Release Test'}
TS = {'environ_overrides': {'SERVER_PORT': S.TS_PORT}}
VEE = {'Tailscale-User-Login': 'vee@example.com', 'Tailscale-User-Name': 'Vee', 'X-Editor': 'Vee'}

SAMPLE = """# Changelog

## 2.3.4 (2027-01-01)
First line of the newest entry, with **bold** words.
- A bullet.
* Another bullet.
### A heading inside, left out

## 2.3.3 (2026-12-01)
The older one.
"""

def owner_headers(c):
    """The unit tests share one database: whoever signed in first through Tailscale (in another test, maybe) is the owner."""
    c.get('/api/me', headers={'Tailscale-User-Login': 'owner@example.com', 'Tailscale-User-Name': 'Own'}, **TS)
    login = next(p['login'] for p in c.get('/api/people').get_json()['people'] if p['role'] == 'owner')
    return {'Tailscale-User-Login': login, 'Tailscale-User-Name': 'Own', 'X-Editor': 'Own'}

def test_changelog_entry_reads_one_version(monkeypatch):
    d = tempfile.mkdtemp(prefix='plantdb-cl-')
    p = os.path.join(d, 'CHANGELOG.md'); open(p, 'w', encoding='utf-8').write(SAMPLE)
    R = S.MODULES[[m.__name__ for m in S.MODULES].index('plantdb.releases')]
    monkeypatch.setattr(R, 'CHANGELOG_PATHS', [os.path.join(d, 'missing.md'), p])
    e = R.changelog_entry('2.3.4')
    assert e == {'version': '2.3.4', 'date': '2027-01-01', 'lines': ['First line of the newest entry, with **bold** words.', 'A bullet.', 'Another bullet.']}
    assert R.changelog_entry('2.3.3')['lines'] == ['The older one.']
    assert R.changelog_entry('9.9.9') is None, 'a version that is not in the file'
    monkeypatch.setattr(R, 'APP_VERSION', '7.7.7')
    assert R.changelog_entry()['version'] == '2.3.4', 'the running version missing: the top entry stands in'
    monkeypatch.setattr(R, 'CHANGELOG_PATHS', [os.path.join(d, 'missing.md')])
    assert R.changelog_entry() is None
    assert R.newer('1.55.0', '1.54.9') and not R.newer('1.55.0', '1.55.0') and not R.newer('x', '1.0.0')

def test_whatsnew_is_the_running_version_and_got_it_is_per_person():
    with S.app.test_client() as c:
        W = c.get('/api/whatsnew').get_json()
        assert W['version'] == S.APP_VERSION and W['entry']['version'] == S.APP_VERSION and W['entry']['lines']
        assert W['seen'] is False and W['update'] is None
        assert W['restore']['due'] is True and W['restore']['last'] is None, 'owner: a restore has never been tried'
        assert c.post('/api/whatsnew/seen', json={}, headers=ED).status_code == 200
        assert c.get('/api/whatsnew').get_json()['seen'] is True
        # through Tailscale: the first person in is the owner; a viewer has their own "seen", may press Got it, and sees no owner lines
        OWN = owner_headers(c)
        assert c.put('/api/people', json={'login': 'vee@example.com', 'role': 'viewer'}, headers=OWN, **TS).status_code in (200, 201)
        V = c.get('/api/whatsnew', headers=VEE, **TS).get_json()
        assert V['seen'] is False and V['update'] is None and 'restore' not in V
        assert c.post('/api/whatsnew/seen', json={}, headers=VEE, **TS).status_code == 200, 'Got it is the person\'s own setting'
        assert c.get('/api/whatsnew', headers=VEE, **TS).get_json()['seen'] is True
        assert c.put('/api/people', json={'login': 'x@example.com', 'role': 'editor'}, headers=VEE, **TS).status_code == 403, 'other changes stay refused'

def test_a_newer_release_on_github_is_told_to_the_owner_only(monkeypatch):
    R = S.MODULES[[m.__name__ for m in S.MODULES].index('plantdb.releases')]
    class Resp:
        def __init__(self, body): self.body = body
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self): return json.dumps(self.body).encode()
    calls = []
    def fake(req, timeout=0):
        calls.append(req.full_url)
        return Resp({'tag_name': 'v9.9.9', 'html_url': 'https://github.com/example/releases/tag/v9.9.9', 'published_at': '2026-12-01T10:00:00Z', 'assets': [{'name': 'plant-database-v9.9.9-20261201-1000.zip'}]})
    monkeypatch.setattr(R.urllib.request, 'urlopen', fake)
    info = R.check_latest()
    assert calls == [f'https://api.github.com/repos/{R.REPO}/releases/latest'] and info['version'] == '9.9.9' and info['assets'] == ['plant-database-v9.9.9-20261201-1000.zip']
    with S.app.test_client() as c:
        W = c.get('/api/whatsnew').get_json()
        assert W['update'] == {'version': '9.9.9', 'url': 'https://github.com/example/releases/tag/v9.9.9', 'published': '2026-12-01'}
        owner_headers(c)
        assert c.get('/api/whatsnew', headers=VEE, **TS).get_json()['update'] is None, 'a viewer is not told'
    # a tag that is not a version, or GitHub not answering: the setting is left as it was
    def odd(req, timeout=0): return Resp({'tag_name': 'nightly'})
    monkeypatch.setattr(R.urllib.request, 'urlopen', odd)
    assert R.check_latest() is None
    def down(req, timeout=0): raise OSError('no network')
    monkeypatch.setattr(R.urllib.request, 'urlopen', down)
    assert R.check_latest() is None
    with S.app.test_client() as c:
        assert c.get('/api/whatsnew').get_json()['update']['version'] == '9.9.9'
    # the same version as the one running is no update
    def same(req, timeout=0): return Resp({'tag_name': 'v' + S.APP_VERSION, 'html_url': 'u', 'published_at': '2026-12-01T10:00:00Z'})
    monkeypatch.setattr(R.urllib.request, 'urlopen', same)
    R.check_latest()
    with S.app.test_client() as c:
        assert c.get('/api/whatsnew').get_json()['update'] is None

def test_a_restore_counts_as_the_quarterly_test():
    with S.app.test_client() as c:
        r = c.post('/api/backups', json={'wait': 1, 'note': 'unit'}, headers=ED)
        assert r.status_code == 201
        r = c.post('/api/backups/restore', json={'file': r.get_json()['file']}, headers=ED)
        assert r.status_code == 200 and r.get_json()['restore_tested_at']
        W = c.get('/api/whatsnew').get_json()
        assert W['restore']['due'] is False and W['restore']['days'] == 0 and W['restore']['last']
        with S.app.app_context():
            t = S.db().execute("SELECT note FROM audit_log WHERE action='backup' AND field='restore' ORDER BY id DESC LIMIT 1").fetchone()
        assert t and 'True' not in t[0] and ('.zip' in t[0].split('from before is in')[-1] or 'No backup was made' in t[0]), '1.56.5: the Audit log names the backup made before the restore'

def test_every_versions_changes_is_a_plain_page():
    with S.app.test_client() as c:
        r = c.get('/api/whatsnew/all')
        assert r.status_code == 200 and r.mimetype == 'text/html'
        t = r.get_data(as_text=True)
        assert f'<h2>{S.APP_VERSION}' in t and '<ul>' in t and '<script' not in t and '<strong>' in t
