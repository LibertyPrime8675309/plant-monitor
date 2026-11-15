"""1.56.1, from Ethan's notes of November 10, 2026: several of a light over one group add up; Spots to sort out shows each
plant's photo; the levels a one-level place offers."""
import server as S
L = S.MODULES[[m.__name__ for m in S.MODULES].index('plantdb.lights')]
H = {'X-Editor': 'Unit'}

def test_several_lights_add_up_over_plants_that_fit_under_fewer():
    assert L.stack_factor(1.0, 1, 0.5) == 1.0
    assert L.stack_factor(1.0, 2, 0.8) == 2.0, 'two bulbs over pots that fit under one: twice the light'
    assert L.stack_factor(1.0, 2, 2.0) == 1.0, 'side by side over pots that need the room: the strength of one'
    assert abs(L.stack_factor(1.0, 2, 1.5) - 2 / 1.5) < 1e-9, 'in between: partly overlapping'
    assert L.stack_factor(1.0, 3, 9.0) == 1.0, 'never less than one light'
    assert L.stack_factor(None, 3, 2.0) == 3.0, 'no area figures: taken to shine on the same plants'

def test_the_preview_changes_with_how_many():
    with S.app.test_client() as t:
        st = t.get('/api/lights').get_json()
        lid = next(x['id'] for x in st['lights'] if x['key'] == 'sansi-10w')
        q = lambda u: t.get(f'/api/lights/preview?light={lid}&units={u}&distance=12&hours=12&dim=100&plants=P-001').get_json()
        one, two = q(1), q(2)
        assert two['ppfd'] == 2 * one['ppfd'] and two['dli'] > one['dli'] and two['stack'] == 2 and two['units'] == 2
        assert two['area_sqft'] == one['area_sqft'], 'aimed at the same plants: the same patch, twice as strong'

def test_spots_to_sort_out_have_photos():
    with S.app.test_client() as t:
        items = t.get('/api/where/sort').get_json()['items']
        ps = [p for it in items for p in it['plants']]
        assert ps and all('photo' in p and 'name' in p for p in ps) and any(p['photo'] for p in ps)
