"""Batch C9 (1.57.0): Ethan's repotted moth orchid from Baraboo, Wisconsin. A batch can give a new page its own care log, potting
mix and questions: the page is made, the repot is logged on its date with the mix it was done with, and nothing repeats."""
import json, os
import server as S
H = {'X-Editor': 'Unit'}
NAME = 'Moth orchid (grey pot, from Baraboo)'

def the_page(t):
    rows = [p for p in t.get('/api/plants').get_json() if p['common_name'] == NAME]
    assert len(rows) == 1, 'one page, made once'
    return rows[0]['code']

def test_the_page_is_made_with_its_photos_and_notes():
    t = S.app.test_client(); code = the_page(t)
    p = t.get('/api/plants/' + code).get_json()
    assert p['site'] == 'Covered porch' and p['grow_kind'] == 'Soil mix' and p['reservoir'] == 'Drains freely'
    assert 'Baraboo' in p['notes'] and 'Baraboo' in p['aliases'] and 'Baraboo' in p['location']
    assert p['home_id'], 'it lives at the Baraboo home, not the main one'
    homes = [h['name'] for h in t.get('/api/places').get_json() if h['id'] == p['home_id']]
    assert homes == ['Baraboo, WI'] or any('Baraboo' in n for n in homes), homes
    with S.app.app_context():                # 1.58.0: the batch carried `area_id: 7`, copied from the white orchid's row: a room of the main home, and another room in every record
        a = S.db().execute('SELECT * FROM areas WHERE id=?', (p['area_id'],)).fetchone()
    assert a['home_id'] == p['home_id'] and (a['side'], a['sheltered'], a['name']) == ('out', 1, 'Covered porch'), 'it is on the covered porch of the Baraboo home'
    photos = [x for x in p['photos']]
    assert len(photos) == 5 and sum(1 for x in photos if x['is_primary']) == 1
    assert all(os.path.exists(os.path.join(S.DATA_DIR, 'photos', x['file'])) for x in photos)

def test_the_repot_is_logged_with_the_mix_it_was_done_with():
    t = S.app.test_client(); code = the_page(t)
    m = t.get('/api/mixes/plant/' + code).get_json()['mix']
    assert m['mixed_on'] == '2026-07-31' and m['care_id'], 'the mix points at the Repotted entry'
    assert [x['name'] for x in m['parts']] == ['Orchid bark']
    care = t.get('/api/care?plant=' + code).get_json()
    entries = care if isinstance(care, list) else care.get('entries', care.get('log', []))
    assert any(e['kind'] == 'repot' and e['done_on'] == '2026-07-31' for e in entries)

def test_its_questions_are_on_its_page():
    t = S.app.test_client(); code = the_page(t)
    q = json.dumps(t.get('/api/requests').get_json())
    assert 'c9-orchid-update' in q or 'old flower spike' in q
    assert code in q

def test_the_page_is_dated_when_its_photos_were_taken():
    import plantdb.core as core
    t = S.app.test_client(); code = the_page(t)
    with S.app.app_context():
        c = core.db()
        r = c.execute('SELECT created_at, updated_at FROM plants WHERE code=?', (code,)).fetchone()
        assert r['created_at'].startswith('2026-07-31') and r['updated_at'].startswith('2026-07-31')
        assert {x[0][:10] for x in c.execute('SELECT added_at FROM photos WHERE plant_id=(SELECT id FROM plants WHERE code=?)', (code,))} == {'2026-07-31'}
        assert c.execute('SELECT created_at FROM care_log WHERE plant_code=?', (code,)).fetchone()[0].startswith('2026-07-31')
