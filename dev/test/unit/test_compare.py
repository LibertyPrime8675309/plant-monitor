"""PLAN.md step 10 (1.56.0): compare lights. compare_row() works each light out at one distance and never stretches a chart past
its ends; the routes add a light being considered, buy it, retire it, and try it in a spot."""
import json
import server as S
M = S.MODULES[[m.__name__ for m in S.MODULES].index('plantdb.compare')]
H = {'X-Editor': 'Unit'}

class Row(dict):
    def keys(self): return super().keys()
def light(data, **kw):
    return Row({'id': 1, 'lkey': 'x', 'name': 'Test light', 'count': 1, 'notes': '', 'status': 'owned', 'data': json.dumps(data), **kw})

CHART = {'ppfd': [[12, 720, 3.0], [24, 331, 8.7], [36, 163, 17.0]], 'watts': 80, 'price': 50, 'kelvin': 4000, 'cri': '97+',
         'spectrum': {'red': 40, 'blue': 18}, 'dimming': [25, 50, 100], 'timer_repeats': True, 'timer_keeps': False}

def test_one_distance_from_the_chart_and_never_beyond_it():
    r = M.compare_row(light(CHART), 0, 24, 12)
    assert r['ppfd'] == 331 and r['area_sqft'] == 8.7 and r['dli'] == round(331 * 12 * 3600 / 1e6, 1) and r['beyond'] is None
    r = M.compare_row(light(CHART), 0, 18, 12)
    assert 331 < r['ppfd'] < 720, 'in between: from the line through the figures'
    for d in (6, 48):
        r = M.compare_row(light(CHART), 0, d, 12)
        assert r['ppfd'] is None and r['dli'] is None and r['beyond'] == "Beyond the maker's chart (12 to 36 in)"
    one = M.compare_row(light({'ppfd': [[6, 35.78, 1.0]]}), 0, 12, 12)
    assert one['ppfd'] is None and 'one figure, at 6 in' in one['beyond']
    assert M.compare_row(light({'ppfd': [[7.87, 129, 1.0], [15.75, 39, 2.0]]}), 0, 8, 12)['ppfd'], '20 cm is 7.87 in: on the chart'

def test_worked_out_columns():
    r = M.compare_row(light(CHART), 2, 12, 12)
    ppf = 720 * 3.0 * M.SQFT_M2
    assert r['per_watt'] == round(ppf / 80, 2) and r['per_light'] == round(50 / ppf * 100, 2)
    assert r['cri_num'] == 97 and r['red'] == 40 and r['dimmable'] and r['dimming'] == [25, 50, 100]
    assert r['timer_repeats'] is True and r['timer_keeps'] is False and r['in_use'] == 2
    assert M.compare_row(light({'ppfd': [[12, 90]], 'watts': 20}), 0, 12, 12)['per_watt'] is None, 'no area, no per-watt figure'

def test_where_the_numbers_come_from():
    assert M.light_source({}) == ('maker', "Maker's figures")
    assert M.light_source({'area_estimated': True})[1] == "Maker's figures, area estimated"
    assert M.light_source({'estimated': True}) == ('estimate', "Claude's estimate")
    assert M.light_source({'estimated': True, 'doubtful': 'it says two things'}) == ('doubtful', 'Doubtful: it says two things')
    assert M.first_num('about 98') == 98 and M.first_num('over 80') == 80 and M.first_num('') is None

def test_batch_c6_marks_the_doubtful_listings():
    with S.app.test_client() as t:
        rows = {r['key']: r for r in t.get('/api/lights/compare?at=12&hours=12').get_json()['rows']}
        assert rows['sansi-gooseneck']['source'] == 'doubtful' and rows['sansi-30w']['source'] == 'doubtful'
        assert rows['sansi-80w']['timer_keeps'] is False and rows['sansi-80w']['source'] == 'maker'
        assert rows['gooingtop-clip']['source'] == 'estimate'
        assert all(r['status'] == 'owned' for r in rows.values()), 'every light from before is owned'

def test_consider_buy_and_retire_a_light():
    with S.app.test_client() as t:
        r = t.post('/api/lights', json={'name': 'Unit candidate', 'status': 'considering', 'count': 3, 'brand': 'Acme', 'url': 'https://example.com/x',
                                        'price': '99.5', 'watts': 100, 'points': '12 in 900 (4 sq ft), 24 in 330 (9 sq ft)', 'direction': 'down',
                                        'kelvin': 3500, 'cri': '90', 'dimming': '10, 50, 100', 'timer_repeats': '1', 'timer_keeps': ''}, headers=H)
        assert r.status_code == 201, r.get_json()
        lid = r.get_json()['id']
        row = next(x for x in t.get('/api/lights/compare?at=12').get_json()['rows'] if x['id'] == lid)
        assert row['status'] == 'considering' and row['count'] == 0, 'a light being considered has none yet'
        assert row['brand'] == 'Acme' and row['price'] == 99.5 and row['price_on'] and row['timer_repeats'] and row['timer_keeps'] is None
        assert row['ppfd'] == 900 and row['area_sqft'] == 4
        assert all(L['id'] != lid for L in t.get('/api/lights').get_json()['lights']), 'not on Grow lights until bought'
        assert t.post('/api/lights', json={'name': 'Bad link', 'status': 'considering', 'url': 'ftp://x'}, headers=H).status_code == 400
        assert t.put(f'/api/lights/{lid}', json={'count': 2}, headers=H).status_code == 400, 'Bought it, not a count, makes it owned'
        assert t.post(f'/api/lights/{lid}/status', json={'status': 'owned', 'count': 2, 'on': '2999-01-01'}, headers=H).status_code == 400
        assert t.post(f'/api/lights/{lid}/status', json={'status': 'owned', 'count': 2}, headers=H).status_code == 200
        L = next(L for L in t.get('/api/lights').get_json()['lights'] if L['id'] == lid)
        assert L['count'] == 2 and L['status'] == 'owned' and L['specs']['bought_on'] and L['specs']['brand'] == 'Acme', 'nothing to type again'
        st = t.get('/api/lights').get_json()
        busy = next(s for s in st['spots']) if st['spots'] else None
        if busy:
            assert t.post(f"/api/lights/{busy['light_id']}/status", json={'status': 'retired'}, headers=H).status_code == 409, 'a light in a spot stays'
        assert t.post(f'/api/lights/{lid}/status', json={'status': 'retired'}, headers=H).status_code == 200
        row = next(x for x in t.get('/api/lights/compare').get_json()['rows'] if x['id'] == lid)
        assert row['status'] == 'retired' and row['count'] == 0
        assert t.post(f'/api/lights/{lid}/status', json={'status': 'gone'}, headers=H).status_code == 400

def test_try_a_light_in_a_spot():
    with S.app.test_client() as t:
        st = t.get('/api/lights').get_json()
        lights = {L['key']: L['id'] for L in st['lights']}
        codes = [c['code'] for c in st['candidates'] if c['need']][:2]
        r = t.post('/api/lights/spots', json={'name': 'Unit try spot', 'light': lights['sansi-10w'], 'units': 1, 'distance': 12, 'hours': 12, 'dim': 100, 'plants': codes}, headers=H)
        assert r.status_code == 201, r.get_json()
        sid = r.get_json()['id']
        cand = t.post('/api/lights', json={'name': 'Unit try light', 'status': 'considering', 'points': '6 in 1500, 12 in 700', 'dimming': '100'}, headers=H).get_json()['id']
        t2 = t.get(f'/api/lights/{cand}/try?spot={sid}').get_json()
        assert t2['spot']['name'] == 'Unit try spot' and t2['now']['dli'] == 4.2 and t2['new']['dli'] == round(700 * 12 * 3600 / 1e6, 1)
        assert [p['code'] for p in t2['plants']] == sorted(codes) and all(p['new_word'] and p['now_word'] for p in t2['plants'])
        assert any('not known for a light you are considering' in n for n in t2['notes'])
        assert t2['fit'] is not None
        far = t.post('/api/lights/spots', json={'name': 'Unit far spot', 'light': lights['sansi-10w'], 'units': 1, 'distance': 30, 'hours': 12, 'dim': 50}, headers=H).get_json()['id']
        t3 = t.get(f'/api/lights/{cand}/try?spot={far}').get_json()
        assert any('outside the maker' in n for n in t3['notes']) and any('no 50% setting' in n for n in t3['notes'])
        assert t.get(f'/api/lights/{cand}/try?spot=99999').status_code == 404

def test_figures_over_a_thousand_keep_their_commas_apart():
    """1.56.2: Ethan's gooseneck, "6 in 2,496, 12 in 804, 18 in 480", was refused: "496" was read as a distance of its own."""
    with S.app.test_client() as t:
        lid = next(L['id'] for L in t.get('/api/lights').get_json()['lights'] if L['key'] == 'sansi-gooseneck')
        before = next(L for L in t.get('/api/lights').get_json()['lights'] if L['id'] == lid)
        r = t.put(f'/api/lights/{lid}', json={'name': before['name'], 'count': before['count'], 'points': '6 in 2,496, 12 in 804, 18 in 480'}, headers=H)
        assert r.status_code == 200, r.get_json()
        after = next(L for L in t.get('/api/lights').get_json()['lights'] if L['id'] == lid)
        assert [(p['distance_in'], p['ppfd']) for p in after['points']] == [(6, 2496), (12, 804), (18, 480)]
        r = t.put(f'/api/lights/{lid}', json={'name': before['name'], 'count': before['count'], 'points': '6 in 2,496,12 in 804 (1.5 sq ft); 18: 480'}, headers=H)
        assert r.status_code == 200 and [p['ppfd'] for p in next(L for L in t.get('/api/lights').get_json()['lights'] if L['id'] == lid)['points']] == [2496, 804, 480]
        orig = ', '.join(f"{p['distance_in']:g} in {p['ppfd']:g}" + (f" ({p['area_sqft']:g} sq ft)" if p.get('area_sqft') else '') for p in before['points'])
        assert t.put(f'/api/lights/{lid}', json={'name': before['name'], 'count': before['count'], 'points': orig}, headers=H).status_code == 200   # as it was, for the tests after
