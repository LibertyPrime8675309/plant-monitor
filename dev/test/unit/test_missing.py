"""Unit tests for Missing details (proto/missing-details): which details a plant lacks, and "Not now"."""
import server as S
OWN = {'X-Editor': 'Unit test'}

def row(**k):
    base = dict(pot_size='Small', leaf_type='Smooth', height_in=10, temp_damage_below=40, water_every_days=7, soil_moisture_low=None, fert_from_month=3, fert_to_month=9,
                fert_every_days=30, fert_strength='', pet_safety='Safe', grow_kind='', light_summary='Bright shade', acquired_on='2024-05-17')
    return dict(base, **k)

def test_a_plant_with_everything_is_missing_nothing():
    assert S.missing_of(row()) == []

def test_light_and_the_potting_mix_are_details_too():
    assert S.missing_of(row(light_summary='')) == ['light']
    assert S.missing_of(row(), has_mix=False) == ['pot_mix']
    assert S.missing_of(row(grow_kind='Water only', leaf_type=''), has_mix=False) == [], 'a plant kept in water has no mix and needs no leaf type'

def test_a_plant_with_no_date_acquired_is_missing_it():
    assert S.missing_of(row(acquired_on='')) == ['acquired_on'] and S.missing_of(row(acquired_on=None)) == ['acquired_on']

def test_every_detail_with_a_box_fills_a_real_plant_field():
    for key, fields, _t, _w, how in S.MISSING_DETAILS:
        if how != 'page': assert fields and all(f in S.FIELD_KIND for f in fields), key

def test_the_list_has_ten_details_each_with_its_reason():
    assert [d[0] for d in S.MISSING_DETAILS] == ['pot_size', 'leaf_type', 'height_in', 'temp_damage_below', 'water', 'feed', 'pet_safety', 'light', 'pot_mix', 'acquired_on']
    assert all(d[2] and d[3] for d in S.MISSING_DETAILS)

def test_not_now_takes_a_plant_off_one_list_and_changes_nothing_on_its_page():
    with S.app.test_client() as c:
        m = c.get('/api/missing').get_json()
        d = next(x for x in m['details'] if x['key'] == 'height_in' and x['plants'])
        code = d['plants'][0]['code']; before = c.get(f'/api/plants/{code}').get_json()
        r = c.post('/api/missing/later', json={'plant': code, 'key': 'height_in'}, headers=OWN); assert r.status_code == 200, r.get_data(as_text=True)
        d2 = next(x for x in r.get_json()['details'] if x['key'] == 'height_in')
        assert code not in [p['code'] for p in d2['plants']] and d2['later'] == d['later'] + 1 and len(d2['plants']) == len(d['plants']) - 1
        after = c.get(f'/api/plants/{code}').get_json()
        assert after['version'] == before['version'] and after['height_in'] == before['height_in'], 'the plant page is untouched'
        other = [x for x in r.get_json()['details'] if x['key'] != 'height_in' and code in [p['code'] for p in x['plants']]]
        was = [x for x in m['details'] if x['key'] != 'height_in' and code in [p['code'] for p in x['plants']]]
        assert len(other) == len(was), 'only that one list'
        assert c.post('/api/missing/later', json={'plant': code, 'key': 'nonsense'}, headers=OWN).status_code == 400
        r = c.delete('/api/missing/later', json={'key': 'height_in'}, headers=OWN)
        d3 = next(x for x in r.get_json()['details'] if x['key'] == 'height_in')
        assert code in [p['code'] for p in d3['plants']] and d3['later'] == 0, 'Show them again brings it back'
