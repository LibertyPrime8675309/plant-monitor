"""1.58.0, from the November 12 review (items 2 and 3).
Backups: automatic ones include the photos (a saved "no" is switched once), backups made before an update no longer pile up, and
the owner is told when the photos are left out or when every copy is on the record's own drive.
This computer's port: it answers only to names a stranger cannot point at it."""
import json, os, sqlite3, tempfile, zipfile
import pytest
import server as S

ED = {'X-Editor': 'Safety Test'}

def conn():
    c = sqlite3.connect(S.DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    return c

def put(key, value):
    c = conn()
    if value is None: c.execute('DELETE FROM settings WHERE key=?', (key,))
    else: c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)', (key, value))
    c.commit(); c.close()

def get(key):
    c = conn(); r = c.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone(); c.close()
    return r[0] if r else None

@pytest.fixture
def settings_back():
    keys = ('backup_settings', 'backup_photos_once', 'backup_copy_url', 'backup_copy_token', 'base_url', 'ics_options')
    was = {k: get(k) for k in keys}
    yield
    for k, v in was.items(): put(k, v)

# ---------------------------------------------------------------- backups
def test_automatic_backups_include_the_photos_on_a_new_record(settings_back):
    put('backup_settings', None)
    c = conn()
    assert S.bk_settings(c)['photos'] is True
    assert get('backup_photos_once'), 'init_db() ran the one-time switch'
    c.close()

def test_a_saved_no_is_switched_to_photos_once_and_a_later_no_is_kept(settings_back):
    put('backup_settings', json.dumps({'enabled': True, 'freq': 'daily', 'hour': 3, 'keep': 14, 'photos': False})); put('backup_photos_once', None)
    c = conn(); S.backup_photos_once(c)
    assert S.bk_settings(c)['photos'] is True and S.bk_settings(c)['keep'] == 14
    note = c.execute("SELECT note, changed_by FROM audit_log WHERE field='backup_settings' ORDER BY id DESC LIMIT 1").fetchone()
    assert 'now include the photos' in note['note'] and note['changed_by'] == 'Plant record'
    # the owner unticks the box afterwards: that stays
    put('backup_settings', json.dumps({'photos': False}))
    S.backup_photos_once(c)
    assert S.bk_settings(c)['photos'] is False
    c.close()

def test_a_record_with_a_great_many_photos_is_not_switched_but_told(settings_back):
    put('backup_settings', json.dumps({'photos': False})); put('backup_photos_once', None)
    was = S.PHOTOS_ONCE_MAX; S.patch('PHOTOS_ONCE_MAX', -1)
    try:
        c = conn(); S.backup_photos_once(c)
        assert S.bk_settings(c)['photos'] is False and get('backup_photos_once')
        n = [x for x in S.backup_notes(c) if x['key'] == 'photos']
        assert n and n[0]['photos'] == c.execute('SELECT COUNT(*) FROM photos').fetchone()[0] and n[0]['bytes'] == S.photo_bytes()
        c.close()
    finally: S.patch('PHOTOS_ONCE_MAX', was)

def test_backups_made_before_an_update_no_longer_pile_up():
    made = []
    def fake(stamp, kind):
        name = f'plantdb-backup-2020010{stamp[0]}-0000{stamp[1:]}-{kind}.zip'
        with zipfile.ZipFile(os.path.join(S.BACKUP_DIR, name), 'w') as z: z.writestr('backup.json', json.dumps({'kind': kind, 'version': '1.0.0'}))
        made.append(name); return name
    try:
        ups = [fake(f'1{i:02d}', 'update') for i in range(8)]
        autos = [fake(f'2{i:02d}', 'auto') for i in range(4)]
        mine = [fake(f'3{i:02d}', 'manual') for i in range(3)]
        removed = S.prune_backups(2)
        left = {b['file'] for b in S.bk_list()}
        assert set(ups[-S.KEEP_UPDATES:]) <= left and not (set(ups[:-S.KEEP_UPDATES]) & left), 'the newest five before-update backups stay'
        assert set(autos[-2:]) <= left and not (set(autos[:2]) & left), 'automatic ones as before'
        assert set(mine) <= left, 'a backup a person made is never removed'
        assert set(removed) == set(ups[:-S.KEEP_UPDATES]) | set(autos[:2])
    finally:
        for n in made:
            try: os.remove(os.path.join(S.BACKUP_DIR, n))
            except OSError: pass

def test_the_owner_is_told_when_every_copy_is_on_one_drive(settings_back, monkeypatch):
    put('backup_copy_url', None); put('backup_copy_token', None)
    monkeypatch.delenv('PLANTDB_COPY_DIR', raising=False)
    c = conn()
    assert 'one-drive' in [n['key'] for n in S.backup_notes(c)] and not S.copy_away(c)
    # a folder named in .env (docker-compose passes it in), and mapped
    d = tempfile.mkdtemp(prefix='plantdb-copy-'); was = S.COPY_DIR; S.patch('COPY_DIR', d)
    try:
        assert not S.copy_away(c), 'the default folder beside the data does not count'
        monkeypatch.setenv('PLANTDB_COPY_DIR', 'D:\\PlantBackups')
        assert S.copy_away(c) and 'one-drive' not in [n['key'] for n in S.backup_notes(c)]
    finally: S.patch('COPY_DIR', was)
    monkeypatch.delenv('PLANTDB_COPY_DIR')
    # or another computer
    put('backup_copy_url', 'http://100.1.2.3:8089'); put('backup_copy_token', 'secret')
    assert S.copy_away(c) and 'one-drive' not in [n['key'] for n in S.backup_notes(c)]
    c.close()

def test_the_pages_get_the_backup_notes(settings_back, monkeypatch):
    put('backup_copy_url', None); put('backup_copy_token', None); put('backup_settings', json.dumps({'photos': False}))
    monkeypatch.delenv('PLANTDB_COPY_DIR', raising=False)
    S.HEALTH_CACHE.clear()
    with S.app.test_client() as c:
        B = c.get('/api/backups').get_json()
        assert [n['key'] for n in B['notes']] == ['photos', 'one-drive'] and B['keep_updates'] == S.KEEP_UPDATES
        assert c.get('/api/jobs').get_json()['backup_notes'] == ['photos', 'one-drive']
        H = c.get('/api/health').get_json()
        assert H['copy']['away'] is False and [n['key'] for n in H['backup_notes']] == ['photos', 'one-drive']
        assert c.put('/api/backups/settings', json={'photos': True}, headers=ED).status_code == 200
        assert [n['key'] for n in c.get('/api/backups').get_json()['notes']] == ['one-drive']
        assert c.put('/api/backups/settings', json={'enabled': False}, headers=ED).status_code == 200
        assert [n['key'] for n in c.get('/api/backups').get_json()['notes']] == ['off', 'one-drive']
    S.HEALTH_CACHE.clear()

# ---------------------------------------------------------------- the names this computer's port answers to
GOOD = ('localhost:8080', 'LOCALHOST', '127.0.0.1:8080', '[::1]:8080', '192.168.1.20:8080', 'ethans-pc:8080', 'ethans-pc.local', 'host.docker.internal:8080', 'plants.lan:8080', 'plants.test:8080')
BAD = ('evil.example:8080', 'attacker.com', 'localhost.evil.example:8080', 'plants.example.ts.net:8443', '127.0.0.1.evil.example')

def test_this_computers_port_answers_to_its_own_names():
    with S.app.test_client() as c:
        for host in GOOD:
            assert c.get('/api/meta', headers={'Host': host}).status_code == 200, host

def test_a_name_a_stranger_could_point_here_is_refused():
    with S.app.test_client() as c:
        n = conn().execute('SELECT COUNT(*) FROM to_photograph').fetchone()[0]
        for host in BAD:
            r = c.get('/api/people', headers={'Host': host})
            assert r.status_code == 403 and 'does not answer to the name' in r.get_data(as_text=True) and 'PLANTDB_HOSTS' in r.get_data(as_text=True), host
            assert c.get('/', headers={'Host': host}).status_code == 403, host
            # the page such a name would serve is "the same site" to the browser: its writes carry a matching Origin and X-Editor
            r = c.post('/api/to-photograph', json={'label': 'rebound'}, headers={'Host': host, 'Origin': 'http://' + host, 'X-Editor': 'Rebound'})
            assert r.status_code == 403, host
        assert conn().execute('SELECT COUNT(*) FROM to_photograph').fetchone()[0] == n
        assert c.get('/healthz', headers={'Host': BAD[0]}).status_code == 200, 'the health probe is not a page'

def test_a_name_you_list_or_saved_is_let_in(settings_back):
    with S.app.test_client() as c:
        was = S.EXTRA_HOSTS; S.patch('EXTRA_HOSTS', {'plants.myhouse.example'})
        try:
            assert c.get('/api/meta', headers={'Host': 'plants.myhouse.example:8080'}).status_code == 200
            assert c.get('/api/meta', headers={'Host': 'other.myhouse.example:8080'}).status_code == 403
        finally: S.patch('EXTRA_HOSTS', was)
        put('base_url', 'http://plants.myhouse.example:8080')
        assert c.get('/api/meta', headers={'Host': 'plants.myhouse.example:8080'}).status_code == 200, 'the address saved for labels'
        put('base_url', None); put('ics_options', json.dumps({'public_base': 'https://my-pc.tail1234.ts.net:8443'}))
        assert c.get('/api/meta', headers={'Host': 'my-pc.tail1234.ts.net:8443'}).status_code == 200, 'the public address saved for the calendar'
        assert c.get('/api/meta', headers={'Host': 'your-pc.tail1234.ts.net:8443'}).status_code == 403

def test_people_through_tailscale_and_links_with_their_own_key_are_not_checked_by_name():
    with S.app.test_client() as c:
        TS = {'environ_overrides': {'SERVER_PORT': S.TS_PORT}}
        r = c.get('/api/me', headers={'Host': 'plants.tail1234.ts.net', 'Tailscale-User-Login': 'owner@example.com', 'Tailscale-User-Name': 'Own'}, **TS)
        assert r.status_code == 200, 'Tailscale lets people in by who they are'
        cal = c.get('/api/calendar/settings').get_json()['links']['local']
        r = c.get('/cal/' + cal.rsplit('/', 1)[-1], headers={'Host': 'my-pc.tail1234.ts.net:8443', 'Tailscale-Funnel-Request': '?1'})
        assert r.status_code == 200, 'the calendar link works under the public name, as before'
