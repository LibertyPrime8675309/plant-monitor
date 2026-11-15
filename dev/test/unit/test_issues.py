"""1.58.0: the Issue tracker (plantdb/issues.py) and Check for updates (plantdb/releases.py). Anyone signed in can send a report,
people who can only view included; only the owner reads, changes or removes one, or sees its pictures; what the page sends about
the device is kept as words and nothing more; and the owner can ask GitHub for the newest release now."""
import io, json, os, sqlite3
import pytest
import server as S
import plantdb.issues as IM
import plantdb.releases as RM

OWN = {'X-Editor': 'Owner'}
TSO = {'Tailscale-User-Login': 'owner@example.com', 'Tailscale-User-Name': 'Own', 'X-Editor': 'Own'}
TSV = {'Tailscale-User-Login': 'viewer-issues@example.com', 'Tailscale-User-Name': 'Vee', 'X-Editor': 'Vee', 'X-Forwarded-For': '100.64.0.7, 10.0.0.1'}
TS = {'environ_overrides': {'SERVER_PORT': S.TS_PORT}}

def png(size=(120, 80)):
    from PIL import Image
    b = io.BytesIO(); Image.new('RGB', size, (40, 90, 130)).save(b, 'PNG')
    return b.getvalue()

@pytest.fixture
def clean():
    c = sqlite3.connect(S.DB_PATH, timeout=30); c.executescript(IM.ISSUES_SCHEMA)
    c.execute('DELETE FROM issues'); c.execute('DELETE FROM issue_photos'); c.commit(); c.close()
    with S.app.test_client() as t:
        # the unit tests share one record: whoever signed in first through Tailscale (in another test, maybe) owns it; the next can only view
        t.get('/api/me', headers=TSO, **TS)
        TSO['Tailscale-User-Login'] = next(p['login'] for p in t.get('/api/people').get_json()['people'] if p['role'] == 'owner')
        assert t.get('/api/me', headers=TSV, **TS).get_json()['role'] == 'viewer'
    yield

def report(t, notes='The page showed an old version.', files=(), headers=OWN, **kw):
    d = {'notes': notes, 'page': '#/plant/P-006', 'page_title': 'Hardy aloe', 'section': 'Care', 'page_version': '1.55.0', 'device': 'iPad mini',
         'made_at': '2026-11-15T12:00:00.000Z', 'info': json.dumps({'Window': '744 by 1133', 'Opened as': 'An app on the Home Screen'}),
         'settings': json.dumps({'Display: contrast': 'high (changed)', 'units': '{"region":"us"}'})}
    d.update(kw)
    if files: d['files'] = [(io.BytesIO(raw), name) for name, raw in files]
    return t.post('/api/report', data=d, headers=headers, content_type='multipart/form-data', **(TS if 'Tailscale-User-Login' in headers else {}))

def test_a_report_keeps_what_the_page_and_the_server_know(clean):
    with S.app.test_client() as t:
        r = report(t, files=[('screen one.png', png()), ('two.png', png((3000, 1000)))])
        assert r.status_code == 201 and r.get_json()['id']
        L = t.get('/api/issues').get_json()
        x = L['issues'][0]
        assert L['counts'] == {'open': 1, 'looking': 0, 'fixed': 0, 'closed': 0} and L['fresh'] == 0          # the owner's own report is not news to the owner
        assert (x['notes'], x['page'], x['page_title'], x['section'], x['device']) == ('The page showed an old version.', '#/plant/P-006', 'Hardy aloe', 'Care', 'iPad mini')
        assert x['page_version'] == '1.55.0' and x['server_version'] == S.APP_VERSION and x['role'] == 'owner' and x['name'] == 'Owner' and x['status'] == 'open'
        assert x['info']['Opened as'] == 'An app on the Home Screen' and x['settings']['Display: contrast'] == 'high (changed)'
        assert [p['name'] for p in x['photos']] == ['screen one.png', 'two.png']
        pic = t.get(f"/api/issues/{x['id']}/photo/{x['photos'][1]['id']}")
        from PIL import Image
        assert pic.status_code == 200 and max(Image.open(io.BytesIO(pic.data)).size) == 2000                  # made smaller, still readable
        assert t.get(f"/api/issues/{x['id']}/photo/999999").status_code == 404

def test_a_report_needs_words_or_a_picture_and_takes_four_pictures(clean):
    with S.app.test_client() as t:
        assert report(t, notes='   ').status_code == 400
        assert report(t, notes='', files=[('a.png', png())]).status_code == 201                               # a picture alone is a report
        assert report(t, files=[(f'{i}.png', png()) for i in range(5)]).status_code == 400
        assert report(t, files=[('notes.txt', b'not a picture')]).status_code == 400
        assert len(t.get('/api/issues').get_json()['issues']) == 1                                            # the refused ones left nothing behind
        assert t.post('/api/report', json={'notes': 'Sent as JSON, with no picture.'}, headers=OWN).status_code == 201

def test_what_the_page_sends_is_kept_as_words_and_cut_to_size(clean):
    with S.app.test_client() as t:
        big = {f'k{i}': 'x' * 900 for i in range(200)}
        r = report(t, notes='n' * 9000, info=json.dumps(big), settings='["not", "a", "list of details"]', device='d' * 200, page_version='1.57.0 and a lot more words')
        assert r.status_code == 201
        x = t.get('/api/issues').get_json()['issues'][0]
        assert len(x['notes']) == IM.ISSUE_MAX_NOTES and len(x['device']) == 60 and len(x['page_version']) == 20
        assert x['settings'] == {} and 0 < len(x['info']) <= 80 and all(len(v) <= 600 for v in x['info'].values())
        assert len(json.dumps(x['info'])) <= IM.ISSUE_MAX_JSON
        report(t, info=json.dumps({'nested': {'a': [1, 2]}, 'n': 3, 'none': None}))
        y = t.get('/api/issues').get_json()['issues'][0]
        assert y['info'] == {'nested': '{"a": [1, 2]}', 'n': 3, 'none': None}

def test_anyone_can_send_one_and_only_the_owner_reads_them(clean):
    with S.app.test_client() as t:
        r = report(t, notes='I cannot see the buttons in the dark theme.', headers=TSV, files=[('dark.png', png())])
        assert r.status_code == 201                                                                           # a person who can only view may send a report
        iid = r.get_json()['id']
        for m, url in (('get', '/api/issues'), ('get', '/api/issues?brief=1'), ('get', f'/api/issues/{iid}/photo/1'), ('post', '/api/issues/seen')):
            assert getattr(t, m)(url, headers=TSV, **TS).status_code == 403, url
        assert t.put(f'/api/issues/{iid}', json={'status': 'closed'}, headers=TSV, **TS).status_code == 403
        assert t.delete(f'/api/issues/{iid}', headers=TSV, **TS).status_code == 403
        L = t.get('/api/issues', headers=TSO, **TS).get_json()
        x = L['issues'][0]
        assert L['fresh'] == 1 and x['login'] == 'viewer-issues@example.com' and x['name'] == 'Vee' and x['role'] == 'viewer' and x['via'] == 'tailscale' and x['addr'] == '100.64.0.7'
        # its picture is in the photos folder, so backups carry it; the routes that show any photo by name show it to the owner alone
        c = sqlite3.connect(S.DB_PATH); f = c.execute('SELECT file FROM issue_photos WHERE issue_id=?', (iid,)).fetchone()[0]; c.close()
        assert IM.ISSUE_FILE.match(f) and os.path.exists(os.path.join(S.PHOTO_DIR, f))
        for url in ('/photos/' + f, '/thumbs/' + f):
            assert t.get(url, headers=TSV, **TS).status_code == 404 and t.get(url, headers=TSO, **TS).status_code == 200, url
        # Today's line goes once the owner has opened the page
        assert t.post('/api/issues/seen', json={}, headers=TSO, **TS).status_code == 200
        assert t.get('/api/issues?brief=1', headers=TSO, **TS).get_json() == {'counts': {'open': 1, 'looking': 0, 'fixed': 0, 'closed': 0}, 'fresh': 0}

def test_the_owner_sorts_notes_and_removes_a_report(clean):
    with S.app.test_client() as t:
        iid = report(t, files=[('a.png', png())]).get_json()['id']
        assert t.put(f'/api/issues/{iid}', json={'status': 'mended'}, headers=OWN).status_code == 400
        assert t.put(f'/api/issues/{iid}', json={'fixed_in': 'soon'}, headers=OWN).status_code == 400
        x = t.put(f'/api/issues/{iid}', json={'status': 'fixed', 'fixed_in': '1.58.0', 'owner_notes': 'The page had been open since 1.55.0.'}, headers=OWN).get_json()
        assert (x['status'], x['status_word'], x['fixed_in'], x['owner_notes'], x['updated_by']) == ('fixed', 'Fixed', '1.58.0', 'The page had been open since 1.55.0.', 'Owner')
        assert t.get('/api/issues?brief=1').get_json()['counts'] == {'open': 0, 'looking': 0, 'fixed': 1, 'closed': 0}
        c = sqlite3.connect(S.DB_PATH); f = c.execute('SELECT file FROM issue_photos WHERE issue_id=?', (iid,)).fetchone()[0]
        said = [r[0] for r in c.execute("SELECT note FROM audit_log WHERE field='issue' ORDER BY id DESC LIMIT 2")]; c.close()
        assert 'Open to Fixed' in said[0] and 'fixed in 1.58.0' in said[0] and 'sent from Hardy aloe' in said[1]
        assert t.delete(f'/api/issues/{iid}', headers=OWN).status_code == 200
        assert not os.path.exists(os.path.join(S.PHOTO_DIR, f)) and t.get('/api/issues').get_json()['issues'] == []
        assert t.put(f'/api/issues/{iid}', json={'status': 'open'}, headers=OWN).status_code == 404

def test_a_report_sent_twice_from_a_device_is_made_once(clean):
    with S.app.test_client() as t:
        h = dict(OWN, **{'X-Offline-Op': 'issue-op-0001', 'X-Offline-Made': '2026-11-14T08:00:00.000Z', 'X-Offline-Device': 'iPad mini'})
        a, b = report(t, headers=h), report(t, headers=h)
        assert a.status_code == 201 and b.status_code == 201 and b.headers.get('X-Offline-Replayed') == '1' and a.get_json()['id'] == b.get_json()['id']
        L = t.get('/api/issues').get_json()['issues']
        assert len(L) == 1 and L[0]['made_at'] == '2026-11-14T08:00:00.000Z'                                  # when it was written, not when it arrived

def test_too_many_reports_in_an_hour_are_refused(clean, monkeypatch):
    monkeypatch.setattr(IM, 'ISSUE_PER_HOUR', 2)
    with S.app.test_client() as t:
        assert [report(t).status_code for _ in range(3)] == [201, 201, 429]
        assert report(t, headers=TSV).status_code == 201                                                      # counted for each account by itself

def test_check_for_updates_asks_github_for_the_owner_alone(clean, monkeypatch):
    asked = []
    def fake(c=None):
        asked.append(1); info = {'version': '9.1.0', 'url': 'https://example.com/r', 'published': '2026-12-01', 'checked': S.now(), 'assets': []}
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('latest_release',?)", (json.dumps(info),)); c.commit()
        return info
    monkeypatch.setattr(RM, 'check_latest', fake)
    with S.app.test_client() as t:
        monkeypatch.setenv('PLANTDB_UPDATES', '1')
        d = t.post('/api/whatsnew/check', json={}, headers=OWN).get_json()
        assert asked == [1] and d == {'version': S.APP_VERSION, 'asked': True, 'off': False, 'newer': True, 'latest': {'version': '9.1.0', 'published': '2026-12-01', 'url': 'https://example.com/r'}}
        monkeypatch.setenv('PLANTDB_UPDATES', '0')                       # turned off: GitHub is not asked, and the answer kept from before is given
        d = t.post('/api/whatsnew/check', json={}, headers=OWN).get_json()
        assert asked == [1] and d['asked'] is False and d['off'] is True and d['latest']['version'] == '9.1.0'
        assert t.post('/api/whatsnew/check', json={}, headers=TSV, **TS).status_code == 403
        c = sqlite3.connect(S.DB_PATH); c.execute("DELETE FROM settings WHERE key='latest_release'"); c.commit(); c.close()
        assert t.get('/api/version').get_json() == {'version': S.APP_VERSION}
