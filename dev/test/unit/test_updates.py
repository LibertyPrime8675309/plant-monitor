"""1.58.0 (November 12 review, item 12): update files from Claude (plantdb/updates.py). A file names its changes; the record
decides what each one is worth now; nothing is changed until the owner accepts, all of it happens together or not at all, and a
file is brought in once. Files are read as data: one that is not an update file, or reaches outside itself, is refused."""
import io, json, os, sqlite3, zipfile
import pytest
import server as S
import plantdb.updates as UM

OWN = {'X-Editor': 'Owner'}
TSO = {'Tailscale-User-Login': 'owner@example.com', 'Tailscale-User-Name': 'Own'}
TSE = {'Tailscale-User-Login': 'ed@example.com', 'Tailscale-User-Name': 'Ed', 'X-Editor': 'Ed'}
TS = {'environ_overrides': {'SERVER_PORT': S.TS_PORT}}

def jpeg(col=(90, 140, 60)):
    from PIL import Image
    b = io.BytesIO(); Image.new('RGB', (60, 45), col).save(b, 'JPEG')
    return b.getvalue()

def pack(changes, photos=None, **top):
    """An update file's bytes: plain JSON, or a zip when photos come with it."""
    d = {'format': 'plant-updates-1', 'made': '2026-11-14', 'about': 'A test file.', 'changes': changes, **top}
    if photos is None: return json.dumps(d).encode()
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z:
        z.writestr('updates.json', json.dumps(d))
        for name, raw in photos.items(): z.writestr(name, raw)
    return b.getvalue()

@pytest.fixture
def folder(tmp_path, monkeypatch):
    """Claude's folder and the page's own, both empty, and nothing remembered from the test before."""
    f = tmp_path / 'plant-updates'; f.mkdir(); box = tmp_path / 'inbox'
    monkeypatch.setattr(UM, 'UPD_FOLDER', str(f)); monkeypatch.setattr(UM, 'UPD_INBOX', str(box)); UM.UPD_CACHE.clear()
    c = sqlite3.connect(S.DB_PATH, timeout=30); c.executescript(UM.UPDATES_SCHEMA); c.execute('DELETE FROM update_files'); c.commit(); c.close()
    return f

def save(folder, raw, name='plant-updates-20261114-0312.json'):
    (folder / name).write_bytes(raw)
    with S.app.test_client() as c:
        return next(w['id'] for w in c.get('/api/updates').get_json()['waiting'] if w['name'] == name)

def plant(c, code): return c.get('/api/plants/' + code).get_json()

def test_a_file_is_weighed_against_the_record_and_brought_in_once(folder):
    with S.app.test_client() as c:
        a, b, d = plant(c, 'P-006'), plant(c, 'P-007'), plant(c, 'P-008')
        fid = save(folder, pack([
            {'kind': 'set', 'code': 'P-006', 'name': a['common_name'], 'field': 'location', 'from': a['location'], 'to': 'By the east fence', 'why': 'It moved.'},
            {'kind': 'set', 'code': 'P-006', 'name': a['common_name'], 'field': 'container', 'from': 'not what the page says', 'to': 'A blue pot', 'why': ''},
            {'kind': 'set', 'code': 'P-007', 'name': b['common_name'], 'field': 'health_rating', 'from': 'x', 'to': b['health_rating'], 'why': ''},
            {'kind': 'set', 'code': 'P-007', 'name': 'Some other name', 'field': 'location', 'from': '', 'to': 'Nowhere', 'why': ''},
            {'kind': 'set', 'code': 'P-007', 'name': b['common_name'], 'field': 'health_rating', 'from': b['health_rating'], 'to': 'Splendid', 'why': ''},
            {'kind': 'set', 'code': 'P-007', 'name': b['common_name'], 'field': 'home_id', 'from': None, 'to': 3, 'why': ''},
            {'kind': 'set', 'code': 'P-007', 'name': b['common_name'], 'field': 'status', 'from': 'active', 'to': 'archived', 'why': ''},
            {'kind': 'archive', 'code': 'P-008', 'name': d['common_name'], 'why': 'A second page for the same plant.'},
            {'kind': 'ask', 'code': 'P-007', 'name': b['common_name'], 'text': 'Is it still on the porch?', 'why': ''},
            {'kind': 'ask', 'code': '', 'name': a['common_name'], 'text': 'Found by its name alone?', 'why': ''}]))
        r = c.get('/api/updates/' + fid).get_json()
        assert [x['state'] for x in r['items']] == ['ready', 'conflict', 'same', 'out', 'out', 'out', 'out', 'ready', 'ready', 'ready']
        assert 'must be one of' in r['items'][4]['note'] and 'not something an update file can change' in r['items'][5]['note'] and r['items'][9]['code'] == 'P-006'
        assert plant(c, 'P-006')['location'] == a['location'], 'looking changes nothing'
        # accept everything it is asked to: only what is ready is made, and a decision is only taken when it is asked for
        res = c.post(f'/api/updates/{fid}/apply', json={'accept': list(range(10)), 'take': []}, headers=OWN).get_json()['before']
        assert [x['did'] for x in res['result']] == ['made', 'left', 'same', 'out', 'out', 'out', 'out', 'made', 'made', 'made'] and res['made_n'] == 4
        p6, p8 = plant(c, 'P-006'), plant(c, 'P-008')
        assert p6['location'] == 'By the east fence' and p6['container'] == a['container'] and p8['status'] == 'archived' and plant(c, 'P-007')['health_rating'] == b['health_rating']
        assert any(q['text'] == 'Is it still on the porch?' for q in plant(c, 'P-007')['requests']) and any(q['text'] == 'Found by its name alone?' for q in p6['requests'])
        h = next(x for x in c.get('/api/plants/P-006/history').get_json()['audit'] if x['field'] == 'location')
        assert h['changed_by'] == 'Claude (plant-updates-20261114-0312.json)' and h['note'].startswith('It moved. (Update from Claude') and 'accepted by Owner' in h['note']
        assert p6['version'] == a['version'] + 1, 'one change, one new version, which Page history can restore'
        # once
        assert c.post(f'/api/updates/{fid}/apply', json={'accept': [1], 'take': [1]}, headers=OWN).status_code == 409
        L = c.get('/api/updates').get_json()
        assert L['waiting'] == [] and L['before'][0]['id'] == fid and L['before'][0]['state'] == 'done' and L['before'][0]['here'] is True
        assert c.get('/api/updates/' + fid).get_json()['before']['made_n'] == 4, 'opening it again shows what it did'
        c.post('/api/plants/P-008/status', json={'archived': False}, headers=OWN)

def test_a_decision_is_taken_only_when_chosen(folder):
    with S.app.test_client() as c:
        a = plant(c, 'P-009')
        fid = save(folder, pack([{'kind': 'set', 'code': 'P-009', 'name': a['common_name'], 'field': 'container', 'from': 'what it said last month', 'to': 'A wide clay bowl', 'why': ''}]))
        assert c.get('/api/updates/' + fid).get_json()['items'][0]['state'] == 'conflict'
        res = c.post(f'/api/updates/{fid}/apply', json={'accept': [], 'take': [0]}, headers=OWN).get_json()['before']
        assert res['made_n'] == 1 and plant(c, 'P-009')['container'] == 'A wide clay bowl'
        c.put('/api/plants/P-009', json={'base_version': plant(c, 'P-009')['version'], 'fields': {'container': a['container']}}, headers=OWN)

def test_a_new_page_comes_with_its_photos_and_a_failure_changes_nothing(folder, monkeypatch):
    with S.app.test_client() as c:
        a = plant(c, 'P-010'); n0 = len(c.get('/api/plants').get_json()); photos0 = set(os.listdir(S.PHOTO_DIR))
        raw = pack([{'kind': 'set', 'code': 'P-010', 'name': a['common_name'], 'field': 'location', 'from': a['location'], 'to': 'On the top shelf', 'why': ''},
                    {'kind': 'new', 'fields': {'common_name': 'Update test aloe', 'scientific_name': 'Aloe testii', 'site': 'Covered porch'}, 'photos': [{'file': 'a.jpg', 'caption': 'First'}, {'file': 'b.jpg', 'caption': ''}], 'why': 'Seen in the photos.'}],
                   photos={'photos/a.jpg': jpeg(), 'photos/b.jpg': jpeg((10, 20, 30))})
        fid = save(folder, raw, 'plant-updates-20261114-0400.zip')
        it = c.get('/api/updates/' + fid).get_json()['items']
        assert it[1]['state'] == 'ready' and it[1]['photos'] == ['a.jpg', 'b.jpg'] and it[1]['site'] == 'Covered porch'
        assert c.get(f'/api/updates/{fid}/photo/a.jpg').mimetype == 'image/jpeg' and c.get(f'/api/updates/{fid}/photo/c.jpg').status_code == 404
        # the second change fails half way: the first is not kept, no photo is left behind, and the file is still waiting
        real = UM.upd_new_plant
        def boom(*a, **k): real(*a, **k); raise RuntimeError('the disk is full')
        monkeypatch.setattr(UM, 'upd_new_plant', boom)
        assert c.post(f'/api/updates/{fid}/apply', json={'accept': [0, 1]}, headers=OWN).status_code == 500
        assert plant(c, 'P-010')['location'] == a['location'] and len(c.get('/api/plants').get_json()) == n0 and set(os.listdir(S.PHOTO_DIR)) == photos0
        assert [w['id'] for w in c.get('/api/updates').get_json()['waiting']] == [fid]
        monkeypatch.setattr(UM, 'upd_new_plant', real)
        res = c.post(f'/api/updates/{fid}/apply', json={'accept': [1]}, headers=OWN).get_json()['before']
        new = next(x for x in res['result'] if x['kind'] == 'new'); p = plant(c, new['code'])
        assert new['did'] == 'made' and p['common_name'] == 'Update test aloe' and p['site'] == 'Covered porch' and p['winter_plan'] == 'Move indoors' and p['created_by'].startswith('Claude (')
        assert [(x['caption'], x['is_primary']) for x in p['photos']] == [('First', 1), ('b.jpg', 0)] and all(os.path.exists(os.path.join(S.PHOTO_DIR, x['file'])) for x in p['photos'])
        assert plant(c, 'P-010')['location'] == a['location'], 'the change that was not accepted this time was not made'
        # the same name again needs a decision
        fid2 = save(folder, pack([{'kind': 'new', 'fields': {'common_name': 'Update test aloe'}, 'why': ''}]), 'plant-updates-20261114-0500.json')
        x = c.get('/api/updates/' + fid2).get_json()['items'][0]
        assert x['state'] == 'conflict' and new['code'] in x['note']
        assert c.post(f'/api/updates/{fid2}/apply', json={'accept': [0]}, headers=OWN).get_json()['before']['made_n'] == 0, 'accepting is not deciding'
        c.post(f'/api/plants/{new["code"]}/status', json={'archived': True}, headers=OWN)

@pytest.mark.parametrize('raw, words', [
    (b'hello', 'not JSON'),
    (json.dumps({'format': 'batch', 'changes': []}).encode(), 'not an update file for this app'),
    (pack([{'kind': 'erase', 'code': 'P-001', 'name': 'x'}]), 'a kind this version does not know'),
    (pack([{'kind': 'archive', 'code': 'P-001'}]), 'does not say which plant'),
    (pack([{'kind': 'set', 'code': 'P-001', 'name': 'x', 'field': 'location'}]), 'does not say what to change'),
    (pack([{'kind': 'set', 'code': 'P-001', 'name': 'x', 'field': 'location', 'to': ['a']}]), 'a list where one value belongs'),
    (pack([{'kind': 'new', 'fields': {'scientific_name': 'No name'}}]), 'no common name'),
    (pack([{'kind': 'new', 'fields': {'common_name': 'x'}, 'photos': [{'file': 'missing.jpg'}]}], photos={}), 'a photo that is not in the file'),
    (pack([{'kind': 'new', 'fields': {'common_name': 'x'}, 'photos': {'file': 'a.jpg'}}], photos={'photos/a.jpg': b'x'}), 'a photo that is not in the file'),
    (pack([{'kind': 'photos', 'code': 'P-001', 'name': 'x', 'photos': [{'file': 'missing.jpg'}]}], photos={'photos/a.jpg': b'x'}), 'adds a photo that is not in the file'),
    (pack([{'kind': 'photos', 'code': 'P-001', 'name': 'x', 'photos': [{'file': 'a.jpg'}]}]), 'adds a photo that is not in the file'),
    (pack([{'kind': 'photos', 'code': 'P-001', 'name': 'x', 'photos': []}], photos={'photos/a.jpg': b'x'}), 'and names none'),
    (pack([{'kind': 'photos', 'name': 'x', 'photos': [{'file': 'a.jpg'}]}], photos={'photos/a.jpg': b'x'}), 'does not say which plant'),
    (pack([], photos={'../evil.txt': b'x'}), 'not a photo of the update'),
    (pack([], photos={'photos/../../evil.jpg': b'x'}), 'not a photo of the update'),
    (pack([], photos={'photos/run.exe': b'x'}), 'not a photo of the update'),
    (b'PK\x03\x04 not really a zip', 'damaged'),
    (pack([], photos={'photos/huge.jpg': b'\0' * (26 * 1024 * 1024)}), 'too large to be part of an update file'),
])
def test_a_file_that_is_not_an_update_file_is_refused_in_plain_words(folder, raw, words):
    with pytest.raises(ValueError) as e: UM.upd_parse(raw, 'plant-updates-x.json')
    assert words in str(e.value)
    with S.app.test_client() as c:
        r = c.post('/api/updates/upload', data={'file': (io.BytesIO(raw), 'plant-updates-x.json')}, headers=OWN)
        assert r.status_code == 400 and words in r.get_json()['error'] and not os.path.isdir(UM.UPD_INBOX)
        (folder / 'plant-updates-bad.json').write_bytes(raw)
        w = c.get('/api/updates').get_json()['waiting']
        assert len(w) == 1 and words in w[0]['bad'] and w[0]['id'] == '', 'in the folder it is named, with the reason, and cannot be opened'

def test_photos_join_a_page_that_exists(folder):
    with S.app.test_client() as c:
        a = plant(c, 'P-013'); had = {p['file'] for p in a['photos']}; main0 = [p['file'] for p in a['photos'] if p['is_primary']]; on_disk = set(os.listdir(S.PHOTO_DIR))
        assert main0, 'the test wants a page that has a main picture'
        fid = save(folder, pack([
            {'kind': 'photos', 'code': 'P-013', 'name': a['common_name'], 'photos': [{'file': 'one.jpg', 'caption': 'November 11: in its jar'}, {'file': 'two.jpg', 'caption': ''}], 'why': 'You sent them on November 11.'},
            {'kind': 'photos', 'code': 'P-013', 'name': 'Not its name', 'photos': [{'file': 'one.jpg', 'caption': ''}], 'why': ''},
            {'kind': 'photos', 'code': 'P-013', 'name': a['common_name'], 'photos': [{'file': 'bad.jpg', 'caption': ''}], 'why': ''}],
            photos={'photos/one.jpg': jpeg(), 'photos/two.jpg': jpeg((10, 20, 30)), 'photos/bad.jpg': b'this is not a picture'}), 'plant-updates-20261114-0900.zip')
        it = c.get('/api/updates/' + fid).get_json()['items']
        assert [x['state'] for x in it] == ['ready', 'out', 'out'] and it[0]['photos'] == ['one.jpg', 'two.jpg'] and it[0]['captions'] == ['November 11: in its jar', '']
        assert 'cannot be read' in it[2]['note'] and c.get(f'/api/updates/{fid}/photo/one.jpg').mimetype == 'image/jpeg'
        assert {p['file'] for p in plant(c, 'P-013')['photos']} == had and set(os.listdir(S.PHOTO_DIR)) == on_disk, 'looking adds nothing'
        res = c.post(f'/api/updates/{fid}/apply', json={'accept': [0, 1, 2]}, headers=OWN).get_json()['before']
        assert [(x['did'], x.get('n')) for x in res['result']] == [('made', 2), ('out', 1), ('out', 1)]
        b = plant(c, 'P-013'); new = [p for p in b['photos'] if p['file'] not in had]
        assert sorted(p['caption'] for p in new) == ['November 11: in its jar', 'two.jpg'] and all(os.path.exists(os.path.join(S.PHOTO_DIR, p['file'])) for p in new)
        assert [p['file'] for p in b['photos'] if p['is_primary']] == main0, "the page's main picture stays as it was"
        assert b['version'] == a['version'] + 1, 'one change, one new version'
        h = [x for x in c.get('/api/plants/P-013/history').get_json()['audit'] if x['action'] == 'photo_add' and x['changed_by'] == 'Claude (plant-updates-20261114-0900.zip)']
        assert len(h) == 2 and h[0]['note'].startswith('Added 2 photo(s). You sent them on November 11. (Update from Claude') and 'accepted by Owner' in h[0]['note']
        for p in new: c.delete(f'/api/photos/{p["id"]}', headers=OWN)

def test_a_new_page_is_made_at_the_home_the_file_names(folder):
    with S.app.test_client() as c:
        homes = c.get('/api/meta').get_json()['homes']; main = next(h for h in homes if h['is_home']); other = next(h for h in homes if not h['is_home'])
        fid = save(folder, pack([
            {'kind': 'new', 'home': other['name'].upper(), 'fields': {'common_name': 'Update test orchid', 'site': 'Indoors'}, 'why': ''},
            {'kind': 'new', 'fields': {'common_name': 'Update test fern', 'site': 'Indoors'}, 'why': ''},
            {'kind': 'new', 'home': 'A home the record does not have', 'fields': {'common_name': 'Update test moss'}, 'why': ''},
            {'kind': 'new', 'fields': {'common_name': 'Update test ivy', 'home_id': other['id']}, 'why': ''}]), 'plant-updates-20261114-1000.json')
        it = c.get('/api/updates/' + fid).get_json()['items']
        assert [x['state'] for x in it] == ['ready', 'ready', 'out', 'out'] and it[0]['home'] == other['name'] and it[1]['home'] == main['name']
        assert 'no home of that name' in it[2]['note'] and 'cannot be given' in it[3]['note'], 'a home is named, never numbered'
        res = c.post(f'/api/updates/{fid}/apply', json={'accept': [0, 1, 2, 3]}, headers=OWN).get_json()['before']
        assert [x['did'] for x in res['result']] == ['made', 'made', 'out', 'out']
        orchid, fern = plant(c, res['result'][0]['code']), plant(c, res['result'][1]['code'])
        d = sqlite3.connect(S.DB_PATH, timeout=30); d.row_factory = sqlite3.Row
        area = lambda p: d.execute('SELECT home_id FROM areas WHERE id=?', (p['area_id'],)).fetchone()
        assert orchid['home_id'] == other['id'] and area(orchid)['home_id'] == other['id'], 'the page, and the room it starts in, are at the home the file named'
        assert not fern['home_id'] and not area(fern)['home_id'], 'a page with no home named is at the main home'
        d.close()
        for x in res['result'][:2]: c.post(f'/api/plants/{x["code"]}/status', json={'archived': True}, headers=OWN)

def test_a_photo_that_is_not_a_picture_leaves_its_page_out(folder):
    with S.app.test_client() as c:
        n0 = len(c.get('/api/plants').get_json())
        fid = save(folder, pack([{'kind': 'new', 'fields': {'common_name': 'Broken photo plant'}, 'photos': [{'file': 'a.jpg', 'caption': ''}, {'file': 'b.jpg', 'caption': ''}], 'why': ''}],
                                photos={'photos/a.jpg': jpeg(), 'photos/b.jpg': b'this is not a picture'}), 'plant-updates-20261114-0800.zip')
        x = c.get('/api/updates/' + fid).get_json()['items'][0]
        assert x['state'] == 'out' and 'cannot be read' in x['note']
        assert c.get(f'/api/updates/{fid}/photo/b.jpg').status_code == 400
        assert c.post(f'/api/updates/{fid}/apply', json={'accept': [0]}, headers=OWN).get_json()['before']['made_n'] == 0 and len(c.get('/api/plants').get_json()) == n0

def test_a_file_chosen_on_the_page_is_kept_until_it_is_used_and_can_be_set_aside(folder):
    with S.app.test_client() as c:
        a = plant(c, 'P-011')
        raw = pack([{'kind': 'ask', 'code': 'P-011', 'name': a['common_name'], 'text': 'A question from a chosen file?', 'why': ''}])
        r = c.post('/api/updates/upload', data={'file': (io.BytesIO(raw), '..\\..\\plant-updates-20261114-0600.json')}, headers=OWN)
        assert r.status_code == 201 and r.get_json()['name'] == 'plant-updates-20261114-0600.json' and r.get_json()['where'] == 'page'
        fid = r.get_json()['id']; kept = os.listdir(UM.UPD_INBOX)
        assert kept == [f'{fid}__plant-updates-20261114-0600.json'], 'kept under its own fingerprint, inside the data folder'
        assert c.post('/api/updates/upload', data={'file': (io.BytesIO(raw), 'another-name.json')}, headers=OWN).get_json()['id'] == fid and len(os.listdir(UM.UPD_INBOX)) == 1, 'the same file is the same update, whatever it is called'
        assert c.post(f'/api/updates/{fid}/aside', json={'on': True}, headers=OWN).status_code == 200
        L = c.get('/api/updates').get_json()
        assert L['waiting'] == [] and L['before'][0]['state'] == 'aside' and L['before'][0]['here'] is False and os.listdir(UM.UPD_INBOX) == []
        assert not any(q['text'].startswith('A question from a chosen') for q in plant(c, 'P-011')['requests']), 'set aside: nothing changed'
        assert c.post('/api/updates/upload', data={'file': (io.BytesIO(raw), 'plant-updates-20261114-0600.json')}, headers=OWN).status_code == 201, 'chosen again, it is looked at again'
        assert c.post(f'/api/updates/{fid}/apply', json={'accept': [0]}, headers=OWN).get_json()['before']['made_n'] == 1 and os.listdir(UM.UPD_INBOX) == []
        r = c.post('/api/updates/upload', data={'file': (io.BytesIO(raw), 'plant-updates-20261114-0600.json')}, headers=OWN)
        assert r.status_code == 409 and 'brought in already' in r.get_json()['error'] and r.get_json()['before']['id'] == fid
        # a file in Claude's folder that was set aside can be looked at again while it is there
        fid2 = save(folder, pack([{'kind': 'ask', 'code': 'P-011', 'name': a['common_name'], 'text': 'From the folder?', 'why': ''}]), 'plant-updates-20261114-0700.json')
        c.post(f'/api/updates/{fid2}/aside', json={'on': True}, headers=OWN)
        assert next(b for b in c.get('/api/updates').get_json()['before'] if b['id'] == fid2)['here'] is True and (folder / 'plant-updates-20261114-0700.json').exists(), "Claude's folder is only read"
        c.post(f'/api/updates/{fid2}/aside', json={'on': False}, headers=OWN)
        assert [w['id'] for w in c.get('/api/updates').get_json()['waiting']] == [fid2]

def test_only_the_owner_sees_or_uses_update_files(folder):
    with S.app.test_client() as c:
        c.get('/api/me', headers=TSO, **TS); c.get('/api/me', headers=TSE, **TS)
        assert c.put('/api/people', json={'login': 'ed@example.com', 'role': 'editor'}, headers=OWN).status_code == 200
        a = plant(c, 'P-012')
        fid = save(folder, pack([{'kind': 'set', 'code': 'P-012', 'name': a['common_name'], 'field': 'location', 'from': a['location'], 'to': 'Changed by an editor', 'why': ''}]))
        for m, u, body in (('get', '/api/updates', None), ('get', '/api/updates/' + fid, None), ('post', f'/api/updates/{fid}/apply', {'accept': [0]}), ('post', f'/api/updates/{fid}/aside', {'on': True})):
            r = getattr(c, m)(u, headers=TSE, **TS) if body is None else getattr(c, m)(u, json=body, headers=TSE, **TS)
            assert r.status_code == 403, (m, u, r.status_code)
        r = c.post('/api/updates/upload', data={'file': (io.BytesIO(pack([])), 'plant-updates-e.json')}, headers=TSE, **TS)
        assert r.status_code == 403 and plant(c, 'P-012')['location'] == a['location']
        d = sqlite3.connect(S.DB_PATH, timeout=30); owner = d.execute("SELECT login FROM people WHERE role='owner' ORDER BY first_seen LIMIT 1").fetchone()[0]; d.close()    # whoever signed in first in this run
        assert c.get('/api/updates', headers={'Tailscale-User-Login': owner}, **TS).status_code == 200, 'the owner can, through Tailscale too'

def test_ids_and_names_cannot_reach_outside_the_folders(folder):
    with S.app.test_client() as c:
        for u in ('/api/updates/..%2F..%2Fplants.db', '/api/updates/' + 'a' * 16, '/api/updates/ABCDEF0123456789', '/api/updates/' + 'a' * 16 + '/photo/x.jpg'):
            assert c.get(u).status_code == 404, u
        (folder / 'notes.txt').write_text('not for the app'); (folder / 'plant-updates-big.json').write_bytes(b' ' * (UM.UPD_MAX + 1))
        w = c.get('/api/updates').get_json()['waiting']
        assert [x['name'] for x in w] == ['plant-updates-big.json'] and 'larger than 30 MB' in w[0]['bad'], 'other files in the folder are ignored; one too large is named and not read'
