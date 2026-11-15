"""PLAN.md step 8 (1.56.0): lights that fit the room. fit_check() is pure: a light's mount, a place's measurements, the level,
what a bulb screws into, the distance and the plants' heights in; sentences out. These pin the rules Ethan described on
November 9, 2026, and the "Not checked" answers when something is missing (never a Fits the app cannot back)."""
import server as S
F = S.MODULES[[m.__name__ for m in S.MODULES].index('plantdb.fit')]
U = {'temp': 'f', 'len': 'in', 'rain': 'in'}
T8 = {'kind': 'under', 'points': 'down', 'length_in': 24}
T5 = {'kind': 'under', 'points': 'down', 'length_in': 12}
TRIPOD = {'kind': 'floor', 'points': 'angled', 'height_lo': 33, 'height_hi': 58}
BARRINA = {'kind': 'surface', 'points': 'side', 'footprint_in': 5, 'height_hi': 24}
CLAMP = {'kind': 'clamp', 'points': 'down', 'grip_in': 2, 'reach_in': 15.8}
POTCLIP = {'kind': 'clamp', 'points': 'down', 'grip_in': 0.8, 'reach_in': 12.8, 'pot_rim': True}
BULB = {'kind': 'socket', 'points': 'down', 'socket': 'E26'}
SIDE = {'levels': 1, 'top': 'nothing'}
SHELF = {'levels': 4, 'gap_in': 13, 'width_in': 16, 'depth_in': 11, 'top': 'nothing', 'edge': 'yes', 'edge_in': 0.75, 'socket': 'yes'}
P = lambda code, h=None, name=None: {'code': code, 'name': name or code, 'height_in': h}

def fc(mount, sheet, plants=(), level='', holder='', dist=12, others=None, place='Living Room, Side Table', room=None, name='light'):
    return F.fit_check(mount, name, place, sheet, room or {}, level, holder, dist, list(plants), others, U)
def kinds(r): return [x['kind'] for x in r['lines']]
def text(r): return ' '.join(x['text'] for x in r['lines'])

def test_a_strip_needs_something_above():
    r = fc(T8, SIDE, others=[('SANSI tripod', TRIPOD), ('GooingTop', CLAMP)], name='T8')
    assert r['status'] == 'nofit' and 'The Side Table has nothing above it, so a strip has nowhere to be fixed' in text(r)
    assert 'SANSI tripod' in text(r), 'names a light of yours that would reach it'
    r = fc({'kind': 'hang', 'points': 'down'}, SIDE)
    assert r['status'] == 'nofit' and 'nowhere to be fixed' in text(r)

def test_a_strip_must_be_no_longer_than_the_level_is_wide():
    r = fc(T8, SHELF, level='lower', place='Living Room, Tall Brown Shelf', others=[('Barrina T5', T5)], name='SANSI 2 ft T8')
    assert r['status'] == 'nofit' and 'levels are 16 in wide; the SANSI 2 ft T8 needs 24 in. The Barrina T5 fits.' in text(r)
    r = fc(T5, SHELF, level='lower', place='Living Room, Tall Brown Shelf')
    assert r['status'] == 'fits' and r['clear_in'] == 13 and 'It screws under the shelf above (16 in wide; it needs 12 in).' in text(r)
    r = fc(T5, {**SHELF, 'width_in': None}, level='lower')
    assert r['status'] == 'unchecked' and 'add the width' in text(r)

def test_on_a_shelf_with_levels_the_level_must_be_said():
    r = fc(T5, SHELF, level='')
    assert r['status'] == 'unchecked' and 'has 4 levels. Say which one' in text(r)
    r = fc(T5, SHELF, level='top')                     # the top level of this shelf is open above
    assert r['status'] == 'nofit' and 'nothing above its top level' in text(r)
    r = fc(T5, {**SHELF, 'top': 'ceiling', 'top_in': 50}, level='top')
    assert r['status'] == 'nofit' and 'too far from the leaves' in text(r)

def test_plants_too_tall_for_the_level_and_the_distance_under_a_shelf():
    r = fc(T5, SHELF, [P('P-001', 16), P('P-008', 8)], level='lower', dist=3)
    assert r['status'] == 'nofit' and kinds(r).count('tall') == 1 and 'P-001' in text(r) and '13 in clear' in text(r)
    r = fc(T5, SHELF, [P('P-009', 11)], level='lower', dist=6)
    assert 'only 2 in between its top and the light' in text(r)
    r = fc(T5, SHELF, [P('P-010', 5)], level='lower', dist=2)
    assert r['status'] == 'fits' and 'about 8 in above the tallest plant; the spot says 2 in' in text(r)
    r = fc(T5, SHELF, [P('P-010', 5), P('P-011')], level='lower', dist=8)
    assert '1 plant has no height yet (P-011)' in text(r)

def test_clamps_need_an_edge_and_a_grip_that_fits_it():
    assert fc(CLAMP, SHELF, level='lower')['status'] == 'fits'
    r = fc(CLAMP, {**SIDE, 'edge': 'no'})
    assert r['status'] == 'nofit' and 'has no edge to clamp to' in text(r)
    r = fc(CLAMP, SIDE)
    assert r['status'] == 'unchecked' and 'an edge to clamp to' in text(r)
    r = fc(CLAMP, {**SIDE, 'edge': 'yes', 'edge_in': 3})
    assert r['status'] == 'nofit' and 'is 3 in thick; the clamp opens to 2 in' in text(r)
    r = fc(POTCLIP, {**SIDE, 'edge': 'no'})
    assert r['status'] == 'fits' and 'clips onto the rim of a pot' in text(r), 'the pot clip goes on the pot itself'

def test_stands_need_room_and_the_tripod_cannot_point_straight_down():
    r = fc(TRIPOD, SIDE, name='tripod')
    assert r['status'] == 'unchecked' and 'free floor' in text(r) and 'point' in kinds(r)
    r = fc(TRIPOD, {**SIDE, 'floor_in': 30}, name='tripod')
    assert r['status'] == 'fits' and 'cannot point straight down' in text(r)
    r = fc({**TRIPOD, 'footprint_in': 24}, {**SIDE, 'floor_in': 10}, name='tripod')
    assert r['status'] == 'nofit' and 'needs 24 in' in text(r)
    assert fc(BARRINA, {**SIDE, 'free_in': 7})['status'] == 'fits'
    r = fc(BARRINA, {**SIDE, 'free_in': 3}, name='Barrina')
    assert r['status'] == 'nofit' and 'has 3 in free beside the plants; the base of the Barrina needs 5 in' in text(r)

def test_a_sideways_light_and_the_plants_it_shades():
    r = fc(BARRINA, {**SIDE, 'free_in': 7}, [P('C', 16, 'Tall one'), P('A', 6, 'Short one'), P('B', 10, 'Middle one')])
    assert 'shaded' in kinds(r) and r['status'] == 'fits', 'shade is a warning, not a "does not fit"'
    assert 'Put the shortest nearest the light: Short one (6 in), Middle one (10 in), Tall one (16 in).' in text(r)
    r = fc(BARRINA, {**SIDE, 'free_in': 7}, [P('A', 6), P('B', 8)])
    assert 'shaded' not in kinds(r)
    r = fc(BARRINA, {**SIDE, 'free_in': 7}, [P('A', 30)])
    assert 'taller than the light (24 in)' in text(r)

def test_a_bulb_takes_the_mount_of_what_it_screws_into():
    r = fc(BULB, SIDE, name='80 W bulb')
    assert r['status'] == 'unchecked' and 'Say what the 80 W bulb screws into here' in text(r)
    assert fc(BULB, SIDE, holder='cord')['status'] == 'nofit'                     # hung from what? nothing above the side table
    assert fc(BULB, {**SIDE, 'free_in': 8}, holder='base')['status'] == 'fits'
    r = fc(BULB, {**SIDE, 'free_in': 8}, holder='base')
    assert 'A lamp with a base stands on the Side Table' in text(r)
    assert fc(BULB, SHELF, holder='clamp', level='lower')['status'] == 'fits'

def test_not_checked_rather_than_a_guess():
    assert 'Say how the light holds' in text(fc(None, SIDE))
    assert 'Choose where this spot is' in text(fc(T5, SIDE, place=None))
    r = fc(T5, {'notes': 'Measurements to come'})
    assert r['status'] == 'unchecked' and 'Add the measurements of the Side Table' in text(r)
    r = fc({'kind': 'none', 'points': 'down'}, SIDE)
    assert r['status'] == 'fits'
    r = fc(T5, {**SHELF, 'socket': 'no'}, level='lower')
    assert 'extension cord' in text(r)

def test_mounts_and_measurements_are_checked_on_the_way_in():
    assert F.mount_clean({'kind': 'clamp', 'grip_in': '1.5', 'pot_rim': 'yes'}) == {'kind': 'clamp', 'points': 'down', 'grip_in': 1.5, 'pot_rim': True}
    assert F.mount_clean({'kind': 'surface'})['points'] == 'side'
    assert F.mount_clean({'kind': ''}) is None
    assert F.sheet_clean({'levels': '4', 'gap_in': '13', 'top': 'nothing', 'notes': ' x '}) == {'levels': 4, 'gap_in': 13.0, 'top': 'nothing', 'notes': 'x'}
    w = F.sheet_words({'levels': 4, 'gap_in': 13, 'width_in': 16, 'depth_in': 11, 'top': 'nothing', 'edge': 'no'}, U)
    assert w == '4 levels, 13 in between them; 16 in by 11 in (width by depth); nothing above the top; no edge to clamp to'
    assert 'cm' in F.mount_words(T8, {'temp': 'c', 'len': 'cm', 'rain': 'mm'}) and '61 cm' in F.mount_words(T8, {'temp': 'c', 'len': 'cm', 'rain': 'mm'})

def test_routes_tick_and_untick_and_photos():
    import io
    from PIL import Image
    with S.app.test_client() as c:
        H = {'X-Editor': 'Unit'}
        lights = c.get('/api/lights').get_json()
        t5 = next(L for L in lights['lights'] if L['key'] == 'barrina-t5')
        pl = next(p for p in lights['places'] if p['label'].endswith('Tall Brown Shelf'))
        assert c.put(f'/api/rooms/{pl["id"]}', json={'sheet': SHELF}, headers=H).status_code == 200
        r = c.post('/api/lights/spots', json={'name': 'Unit T5', 'light': t5['id'], 'distance': 4, 'hours': 12, 'place': pl['id'], 'level': 'lower', 'plants': []}, headers=H)
        sid = r.get_json()['id']
        sp = next(s for s in c.get('/api/lights').get_json()['spots'] if s['id'] == sid)
        assert sp['fit']['status'] == 'fits' and sp['checked'] is None and sp['level'] == 'lower'
        assert c.post(f'/api/lights/spots/{sid}/checked', json={'note': 'ok'}, headers=H).get_json()['checked']['stale'] is False
        assert c.put(f'/api/lights/spots/{sid}', json={'name': 'Unit T5', 'light': t5['id'], 'distance': 5, 'hours': 12, 'place': pl['id'], 'level': 'lower'}, headers=H).status_code == 200
        sp = next(s for s in c.get('/api/lights').get_json()['spots'] if s['id'] == sid)
        assert sp['checked']['stale'] is True, 'a new distance clears the tick'
        c.put(f'/api/lights/spots/{sid}', json={'name': 'Unit T5', 'light': t5['id'], 'distance': 5, 'hours': 10, 'place': pl['id'], 'level': 'lower'}, headers=H)
        c.post(f'/api/lights/spots/{sid}/checked', json={}, headers=H)
        c.put(f'/api/lights/spots/{sid}', json={'name': 'Unit T5', 'light': t5['id'], 'distance': 5, 'hours': 14, 'place': pl['id'], 'level': 'lower'}, headers=H)
        sp = next(s for s in c.get('/api/lights').get_json()['spots'] if s['id'] == sid)
        assert sp['checked']['stale'] is False, 'the hours change nothing about how it is put together'
        assert c.delete(f'/api/lights/spots/{sid}/checked', headers=H).status_code == 200
        b = io.BytesIO(); Image.new('RGB', (40, 30), (1, 2, 3)).save(b, 'JPEG'); b.seek(0)
        r = c.post(f'/api/rooms/{pl["id"]}/photos', data={'files': (b, 'shelf.jpg')}, headers=H, content_type='multipart/form-data')
        assert r.status_code == 201 and r.get_json()['photos'][0]['is_primary']
        assert next(p for p in c.get('/api/lights').get_json()['places'] if p['id'] == pl['id'])['photo']
        ph = r.get_json()['photos'][0]['id']
        assert c.delete(f'/api/rooms/photos/{ph}', headers=H).get_json()['photos'] == []
        c.delete(f'/api/lights/spots/{sid}', headers=H)

# 1.56.0: a shelf whose levels differ (Ethan's tall brown shelf, November 10: 23, 13 and 27 in from the bottom, open on top)
BROWN = {'levels': 4, 'gaps_in': [23, 13, 27], 'width_in': 22, 'depth_in': 11, 'top': 'nothing'}

def test_each_level_has_its_own_height():
    tall = [P('P-1', 16, 'Tall one')]
    r = fc(T5, BROWN, tall, level='L2', dist=None, place='Living Room, Tall Brown Shelf')
    assert r['status'] == 'nofit' and r['clear_in'] == 13 and any('13 in clear' in x['text'] for x in r['lines']), 'level 2 has 13 in'
    r = fc(T5, BROWN, tall, level='L1', dist=None, place='Living Room, Tall Brown Shelf')
    assert r['status'] == 'fits' and r['clear_in'] == 23, 'level 1 has 23 in: room for it and a strip'
    r = fc(T5, BROWN, tall, level='L4', dist=None, place='Living Room, Tall Brown Shelf')
    assert r['status'] == 'nofit' and 'nothing above its top level' in r['lines'][0]['text'], 'level 4 of 4 is the top: open air'
    r = fc(T5, BROWN, tall, level='lower', dist=None, place='Living Room, Tall Brown Shelf')
    assert r['status'] == 'unchecked' and 'not all the same height' in r['lines'][0]['text'], '"a lower level" is not enough when they differ'
    assert F.level_word('L3') == 'level 3 from the bottom' and F.level_gap({'gap_in': 11}, 'L2') == 11

def test_heights_for_each_level_in_the_measurements():
    assert F.sheet_clean({'levels': 4, 'gaps_in': '23, 13, 27'})['gaps_in'] == [23, 13, 27]
    import pytest, werkzeug
    with pytest.raises(werkzeug.exceptions.BadRequest): F.sheet_clean({'levels': 4, 'gaps_in': '23, 13'})
    assert F.sheet_words(BROWN, U).startswith('4 levels, 23 in, 13 in and 27 in clear from the bottom up')

def test_batch_c7_measured_the_shelves():
    with S.app.test_client() as t:
        sheets = {sp['name']: sp['sheet'] for h in t.get('/api/where').get_json()['homes'] for a in h['areas'] for sp in a['spots']}
        # (the Tall Brown Shelf's are changed by an earlier test here; its batch values are checked in the batch file)
        import json, os
        b = json.load(open(os.path.join(os.path.dirname(S.__file__), 'seed', 'batches', 'batchC7.json')))
        assert next(u for u in b['place_sheets_update'] if u.get('name') == 'Tall Brown Shelf')['set']['gaps_in'] == [None, [23, 13, 27]]
        assert '44 in by 13 in' in sheets['Large Brown Hutch'] and '5 levels, 11 in between them' in sheets['Tall Black Shelf']
        assert sheets['Side Table'].startswith('one level; 26 in by 9 in')
        assert t.post('/api/lights/spots', json={'name': 'Bad level', 'light': 1, 'distance': 12, 'hours': 12, 'level': 'L99'}, headers={'X-Editor': 'Unit'}).status_code == 400
