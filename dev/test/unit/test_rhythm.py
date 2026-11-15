"""How often you water (prototype proto/water-rhythm): the pure parts."""
import server as S

def test_state_needs_a_clear_difference():
    st = S.rhythm_state
    assert st(3, 10) == 'often' and st(20, 10) == 'seldom' and st(10, 10) == 'matches'
    assert st(5, 6) == 'matches'          # a day apart is not worth a change
    assert st(2, 3) == 'matches'          # nor is a short reminder a day early
    assert st(9, 6) == 'seldom' and st(4, 6) == 'often'

def test_the_setting_lands_the_reminder_nearest_the_gap():
    f = S.rhythm_setting_for
    for n in range(1, 40):
        for k in (0.6, 0.8, 1.0, 1.3, 1.5, 1.6):
            base, gives = f(n, k)
            assert 1 <= base <= 60 and gives == max(1, round(base * k))
            assert all(abs(gives - n) <= abs(max(1, round(b * k)) - n) for b in range(1, 61))   # no other setting comes closer
    assert f(3, 1.5) == (2, 3) and f(10, 1.0) == (10, 10)

def test_a_gap_chosen_on_the_page_has_no_indoor_stretch():
    assert S.water_factor_for({'P-001'}, 'P-001', 80, True)[0] == 1.0, 'indoors, taken as chosen'
    assert S.water_factor_for(set(), 'P-001', 80, True)[0] == 1.5, 'indoors, the app\'s own estimate is still stretched'
    assert S.water_factor_for({'P-001'}, 'P-001', 96, False) == S.water_factor(96, False), 'outdoors the weather still counts'

def test_choosing_a_gap_for_an_indoor_plant_gives_that_gap_and_undo_gives_the_stretch_back():
    OWN = {'X-Editor': 'Unit test'}
    with S.app.test_client() as c:
        code = next(p['code'] for p in c.get('/api/plants').get_json() if p['site'] == 'Indoors')
        was = c.get(f'/api/rhythm?plant={code}').get_json()['plants'][0]
        r = c.put('/api/rhythm', json={'plant': code, 'every': 5}, headers=OWN); assert r.status_code == 200, r.get_data(as_text=True)
        p = r.get_json()['plants'][0]
        assert (p['every'], p['own_setting'], p['exact']) == (5, 5, True)
        p = c.put('/api/rhythm', json={'plant': code, 'setting': was['own_setting'], 'exact': False}, headers=OWN).get_json()['plants'][0]
        assert (p['every'], p['own_setting'], p['exact']) == (was['every'], was['own_setting'], False)
        c.put('/api/rhythm', json={'plant': code, 'every': 5}, headers=OWN)
        p = c.put('/api/rhythm', json={'plant': code, 'every': None}, headers=OWN).get_json()['plants'][0]
        assert p['own_setting'] is None and not p['exact'], 'letting the app work it out drops the mark too'
