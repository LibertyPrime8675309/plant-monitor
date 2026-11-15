"""Unit tests for propagation (proto/propagation): the ways match the guide's sections and the dates behave."""
import os, re
import server as S

def test_every_way_points_at_a_guide_section():
    js = open(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app', 'static', 'js', 'guide.js'), encoding='utf-8').read()
    ids = set(re.findall(r"id: '(gd-[a-z-]+)'", js))
    assert {m['guide'] for m in S.METHODS.values()} <= ids

def test_every_mark_has_words_and_seed_counts_sprouts():
    for k, m in S.METHODS.items():
        assert all(x in S.EVENT_WORD for x in m['marks']), k
    assert S.METHODS['seed']['marks'] == ('sprouted',) and 'sprouted' in S.COUNTED

def test_stage_presets_cover_every_kind_and_are_sane():
    assert set(S.STAGE_PRESET) == set(S.STAGE_KINDS)
    for k, (days, lo, hi) in S.STAGE_PRESET.items():
        assert days >= 0 and (lo is None) == (hi is None) and (lo is None or lo < hi)

def test_check_days_prefers_the_persons_number_then_water_then_the_way():
    row = lambda **k: {'check_every': None, 'medium': '', 'method': 'layer', **k}
    assert S.check_days(row()) == 14 and S.check_days(row(medium='Water')) == 7 and S.check_days(row(check_every=3, medium='Water')) == 3

def test_dates_and_numbers_are_checked():
    from datetime import date
    import pytest, werkzeug.exceptions as E
    with pytest.raises(E.BadRequest): S.prop_iso('nope', 'Date')
    with pytest.raises(E.BadRequest): S.prop_iso('2999-01-01', 'Date', date(2026, 11, 12))
    assert S.prop_iso('2026-11-01', 'Date', date(2026, 11, 12)) == '2026-11-01'
    assert S.to_int('', 'x', 1, 5, none_ok=True) is None
    with pytest.raises(E.BadRequest): S.to_int('9', 'x', 1, 5)

# ---------------------------------------------------------------- a seed lot: tests, sowing, sprouting, photos (the seed-lot idea, step 1)
OWN = {'X-Editor': 'Unit test'}

def _lot(c, **k):
    r = c.post('/api/propagations', json={'method': 'seed', 'species': 'Quercus shumardii', 'title': 'Red oak acorns', 'count': 40, **k}, headers=OWN)
    assert r.status_code == 201, r.get_data(as_text=True)
    return r.get_json()

def test_a_seed_test_keeps_both_numbers_and_can_take_the_bad_ones_off_the_lot():
    with S.app.test_client() as c:
        lot = _lot(c); ev = f"/api/propagations/{lot['id']}/events"
        r = c.post(ev, json={'kind': 'test', 'how': 'float', 'tested': 40, 'sound': 31, 'discard': True}, headers=OWN)
        assert r.status_code == 201, r.get_data(as_text=True)
        card = r.get_json()['card']
        t = card['last_test']
        assert (t['word'], t['result'], t['sound_pct']) == ('Float test', '31 of 40 sound', 78)
        assert card['lost'] == 9 and card['left'] == 31, 'the floaters came off the lot'
        r = c.post(ev, json={'kind': 'test', 'how': 'cut', 'tested': 5, 'sound': 4}, headers=OWN)
        assert r.get_json()['card']['lost'] == 9, 'a test without "discard" changes no count'
        for bad in ({'kind': 'test', 'how': 'float', 'tested': 5, 'sound': 6}, {'kind': 'test', 'how': 'x-ray', 'tested': 5, 'sound': 1}, {'kind': 'test', 'how': 'cut', 'sound': 1}):
            assert c.post(ev, json=bad, headers=OWN).status_code == 400, bad

def test_sprouting_is_counted_from_the_seeds_sown():
    with S.app.test_client() as c:
        lot = _lot(c); ev = f"/api/propagations/{lot['id']}/events"
        card = c.post(ev, json={'kind': 'sprouted', 'n': 4}, headers=OWN).get_json()['card']
        assert (card['sprout_of'], card['sprout_pct']) == (40, 10), 'nothing sown is written down: counted from the whole lot'
        card = c.post(ev, json={'kind': 'sown', 'n': 20}, headers=OWN).get_json()['card']
        assert (card['sown'], card['sprout_of'], card['sprout_pct']) == (20, 20, 20)
        r = c.post(ev, json={'kind': 'sown', 'n': 21}, headers=OWN)
        assert r.status_code == 400 and 'more than the 40' in r.get_data(as_text=True), 'no more can be sown than the lot holds'

def test_only_a_seed_lot_has_a_seed_test_or_sowing():
    with S.app.test_client() as c:
        code = c.get('/api/plants').get_json()[0]['code']
        r = c.post('/api/propagations', json={'method': 'stem', 'parent_code': code, 'count': 2}, headers=OWN); assert r.status_code == 201
        ev = f"/api/propagations/{r.get_json()['id']}/events"
        assert c.post(ev, json={'kind': 'sown', 'n': 1}, headers=OWN).status_code == 400
        assert c.post(ev, json={'kind': 'test', 'how': 'float', 'tested': 2, 'sound': 2}, headers=OWN).status_code == 400

def test_photos_of_an_attempt_are_kept_and_a_removed_one_goes_to_the_bin_folder():
    import io
    from PIL import Image
    def jpg(colour):
        b = io.BytesIO(); Image.new('RGB', (80, 60), colour).save(b, 'JPEG'); b.seek(0); return b
    with S.app.test_client() as c:
        lot = _lot(c); url = f"/api/propagations/{lot['id']}/photos"
        assert c.post(url, data={}, headers=OWN).status_code == 400
        r = c.post(url, data={'files': [(jpg('brown'), 'a.jpg'), (jpg('green'), 'b.jpg')], 'caption': 'Before the cold step'}, headers=OWN, content_type='multipart/form-data')
        assert r.status_code == 201, r.get_data(as_text=True)
        ph = r.get_json()['photos']
        assert len(ph) == 2 and ph[0]['caption'] == 'Before the cold step' and all(os.path.exists(os.path.join(S.PHOTO_DIR, p['file'])) for p in ph)
        assert c.post(url, data={'files': [(io.BytesIO(b'not a picture'), 'x.jpg')]}, headers=OWN, content_type='multipart/form-data').status_code == 400
        card = c.delete(f"/api/propagations/photos/{ph[0]['id']}", headers=OWN).get_json()
        assert [p['id'] for p in card['photos']] == [ph[1]['id']]
        assert not os.path.exists(os.path.join(S.PHOTO_DIR, ph[0]['file'])) and os.path.exists(os.path.join(S.TRASH_DIR, ph[0]['file'])), 'the file is kept in photos_deleted'
        assert c.delete(f"/api/propagations/{lot['id']}", headers=OWN).get_json() == {'removed': True}
        assert os.path.exists(os.path.join(S.TRASH_DIR, ph[1]['file'])), 'removing the record keeps its photos in photos_deleted too'

# ---------------------------------------------------------------- the morning notification
def test_the_morning_message_counts_what_is_due_and_names_the_first():
    items = [{'title': 'Shumard oak acorns', 'due': [{'words': 'Cold, moist (stratify) ends today'}]}, {'title': 'Pothos, stem cuttings', 'due': [{'words': 'Look at it: last looked 8 days ago'}]}]
    assert S.prop_push_words(items) == ('Propagation: 2 to look at today', 'Shumard oak acorns: cold, moist (stratify) ends today; Pothos, stem cuttings: look at it: last looked 8 days ago')

def test_propagation_is_a_kind_of_notification_and_goes_once_a_day(monkeypatch):
    import sqlite3
    from datetime import datetime
    import plantdb.propagation as P
    assert any(k[0] == 'prop' for k in S.PUSH_EXTRA_KINDS) and S.prop_push in S.PUSH_CLOCK
    with S.app.test_client() as c:
        code = c.get('/api/plants').get_json()[0]['code']
        r = c.post('/api/propagations', json={'method': 'stem', 'parent_code': code, 'count': 2, 'started_on': (S.date.today() - S.timedelta(days=20)).isoformat()}, headers=OWN); assert r.status_code == 201
        assert 'prop' in [k['key'] for k in c.get('/api/push').get_json()['kinds']]
    sent = []
    monkeypatch.setattr(P, 'push_send', lambda c, kind, title, body, url='#/', home_id=None, logins=None, tag=None: sent.append((kind, title, url)))
    d = sqlite3.connect(S.DB_PATH); d.row_factory = sqlite3.Row
    try:
        d.execute("DELETE FROM settings WHERE key LIKE 'push_sent:prop:%'"); d.commit()
        assert S.prop_push(d, datetime(2026, 11, 15, 7, 0)) is None and not sent, 'not before 8 in the morning'
        got = S.prop_push(d, datetime(2026, 11, 15, 9, 0))
        assert got and got[0].startswith('Propagation: ') and sent and sent[0][0] == 'prop' and sent[0][2] == '#/propagating'
        assert S.prop_push(d, datetime(2026, 11, 15, 10, 0)) is None and len(sent) == 1, 'once a day'
        d.commit()
    finally: d.close()


# ---------------------------------------------------------------- the Library's seed facts (batch D2)
def test_every_seed_fact_has_a_source_with_an_address_and_steps_a_seed_lot_can_have():
    import json, os
    b = json.load(open(os.path.join(os.path.dirname(S.__file__), 'seed', 'batches', 'batchD2.json'), encoding='utf-8'))
    rows = b['facts_add']
    assert len(rows) == 11 and len({r['name'] for r in rows}) == 11
    for r in rows:
        assert r['field'] == 'about_seed' and r['source_kind'] == 'reference' and r['confidence'] in ('certain', 'likely') and 'https://' in r['source'], r['name']
        assert (r['confidence'] == 'certain') == ('note' not in r), r['name'] + ': a fact marked likely says why'
        v = r['value']
        assert v['text'].endswith('.') and len(v['text']) < 700 and isinstance(v['steps'], list)
        for s in v['steps']:
            assert s['kind'] in S.STAGE_KINDS and 1 <= s['days'] <= 365, r['name']
            if 'days_low' in s: assert s['days_low'] <= s['days'] <= s['days_high']
            if 'temp_low' in s: assert 32 <= s['temp_low'] < s['temp_high'] <= 45

def test_a_seed_lot_finds_its_species_seed_fact_by_name_or_by_its_parent():
    with S.app.test_client() as c:
        f = c.get('/api/propagations/seedfacts?name=Quercus shumardii').get_json()
        assert f['found'] and f['steps'][0]['kind'] == 'cold' and f['steps'][0]['label'] and (f['steps'][0]['days_low'], f['steps'][0]['days_high']) == (30, 90)
        assert c.get('/api/propagations/seedfacts?name=asclepias tuberosa').get_json()['found'], 'a name typed in small letters is found too'
        assert c.get('/api/propagations/seedfacts?name=Nothing known').get_json() == {'found': False}
        assert c.get('/api/propagations/seedfacts').get_json() == {'found': False}
        code = c.get('/api/plants').get_json()[0]['code']
        assert 'found' in c.get(f'/api/propagations/seedfacts?parent={code}').get_json()
