"""Prototype (proto/layouts): layouts. What the record suggests for sizes (a plant's from its tray, its pot, its Pot size and its
height; a light's from how it holds; a shelf's levels from its measurements), what a layout of a place starts with, and the
routes: what they refuse, that a plant is on a layout once, that moving a plant on a layout changes nothing on its own page,
that removing a layout removes the things drawn on it and nothing else, and that a viewer changes nothing.
What counts as overlapping or tight, the grid and the moving are the page's (js/layouts.js) and are checked in the browser
(dev/test/layouts_check.py)."""
import json, sqlite3
import pytest
import server as S
LY = S.MODULES[[m.__name__ for m in S.MODULES].index('plantdb.layouts')]
OWN = {'X-Editor': 'Layout unit test'}
TS = {'environ_overrides': {'SERVER_PORT': S.TS_PORT}}
TSO = {'Tailscale-User-Login': 'owner@example.com', 'Tailscale-User-Name': 'Own'}
VIEW = {'Tailscale-User-Login': 'lyviewer@example.com', 'Tailscale-User-Name': 'Vee', 'X-Editor': 'Vee'}

def conn():
    c = sqlite3.connect(S.DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    return c

@pytest.fixture(scope='module')
def room():
    """A room of this file's own (other tests change the measurements of the record's shelves): one shelf with its levels
    measured, as batch C7 gave the Tall Brown Shelf, and a table with no measurements."""
    with S.app.test_client() as c:
        r = c.post('/api/where/areas', json={'name': 'Layout test room', 'side': 'in'}, headers=OWN); assert r.status_code == 201, r.get_data(as_text=True)
        aid = r.get_json()['id']
        ids = []
        for name in ('Layout test shelf', 'Layout test table'):
            r = c.post('/api/where/spots', json={'area_id': aid, 'name': name}, headers=OWN); assert r.status_code == 201, r.get_data(as_text=True)
            ids.append(r.get_json()['id'])
        r = c.put(f'/api/rooms/{ids[0]}', json={'sheet': {'levels': 4, 'gaps_in': [23, 13, 27], 'width_in': 22, 'depth_in': 11}}, headers=OWN); assert r.status_code == 200, r.get_data(as_text=True)
        return {'area': aid, 'shelf': ids[0], 'table': ids[1]}

def pots():
    """A small table of pots and trays, as Pots and trays keeps them."""
    c = sqlite3.connect(':memory:'); c.row_factory = sqlite3.Row
    c.execute('CREATE TABLE containers(id INTEGER PRIMARY KEY, kind TEXT, shape TEXT, dia_in REAL, len_in REAL, wid_in REAL)')
    c.executemany('INSERT INTO containers VALUES(?,?,?,?,?,?)', [(1, 'pot', 'circle', 6, None, None), (2, 'tray', 'circle', 9, None, None), (3, 'pot', 'square', None, 5, None),
                                                               (4, 'pot', 'rectangle', None, 20, 7), (5, 'pot', 'circle', None, None, None)])
    return c

def plant(**kw): return dict({'tray_id': None, 'pot_id': None, 'pot_size': None, 'height_in': None}, **kw)

def test_a_plants_room_is_its_tray_then_its_pot_then_a_guess_that_is_owned_up_to():
    c = pots(); size = lambda **kw: LY.layout_plant_size(c, plant(**kw))
    assert size(tray_id=2, pot_id=1, height_in=14) == (9, 9, 14, 'round', []), 'the tray is wider than the pot, and is what takes the room'
    assert size(pot_id=1, height_in=14) == (6, 6, 14, 'round', [])
    assert size(pot_id=3, height_in=8)[:4] == (5, 5, 8, 'box') and size(pot_id=4, height_in=8)[:4] == (20, 7, 8, 'box'), 'a square pot and a trough are boxes'
    assert size(pot_id=5, pot_size='Large: 12 in and up') == (16, 16, 12, 'round', ['width', 'height']), 'a pot with no size on it is passed over for the Pot size'
    assert size(pot_size='Small: under 6 in')[0] == 6 and size(pot_size='Medium')[0] == 10
    assert size() == (8, 8, 12, 'round', ['width', 'height']), 'nothing known: 8 in across and 12 in tall, both said to be guesses'
    assert size(height_in=30)[4] == ['width'] and size(pot_id=1)[4] == ['height']

def test_a_lights_rough_size_comes_from_how_it_holds():
    size = lambda mount: LY.layout_light_size({'data': json.dumps({'mount': mount} if mount else {})})
    assert size({'kind': 'under', 'length_in': 24}) == (24, 2, 1.5, 'box', True), 'a strip is as long as its mounting says, and hangs'
    assert size({'kind': 'under'})[0] == 12
    assert size({'kind': 'floor', 'footprint_in': 18, 'height_hi': 58}) == (18, 18, 58, 'round', False), 'a floor lamp stands'
    assert size({'kind': 'surface', 'footprint_in': 5, 'height_hi': 24}) == (5, 5, 24, 'box', False)
    assert size({'kind': 'clamp'})[4] is True and size(None) == (5, 5, 6, 'round', True)

def test_a_shelfs_levels_become_boards_from_its_measurements():
    boards, top = LY.layout_boards({'levels': 4, 'gaps_in': [23, 13, 27], 'width_in': 22, 'depth_in': 11})
    assert [b['z'] for b in boards] == [0, 23.75, 37.5, 65.25] and top == 66, 'each level is a board and the clear height below it higher'
    assert [b['name'] for b in boards] == ['Level 1 (bottom)', 'Level 2', 'Level 3', 'Level 4 (top)']
    assert all((b['w'], b['d'], b['h'], b['kind'], b['locked']) == (22, 11, 0.75, 'shelf', True) for b in boards)
    boards, top = LY.layout_boards({'levels': 3, 'gap_in': 12, 'width_in': 30, 'depth_in': 12})
    assert [b['z'] for b in boards] == [0, 12.75, 25.5] and top == 26.25, 'one clear height for every level'
    for sheet in ({'levels': 1, 'width_in': 30, 'depth_in': 12}, {'levels': 3, 'gap_in': 12, 'depth_in': 12}, {'levels': 4, 'gaps_in': [23, 13], 'width_in': 22, 'depth_in': 11}, {}):
        assert LY.layout_boards(sheet) == ([], None), 'not enough measured: no boards are made up'

def test_what_a_layout_of_a_place_starts_with(room):
    with S.app.test_client() as c:
        d = c.get('/api/layouts').get_json()
    assert set(d['kinds']) == {'plant', 'light', 'shelf', 'other', 'zone'} and 1 in d['grids']
    by = {p['pid']: p for p in d['places']}
    shelf, table, whole = by[room['shelf']], by[room['table']], by[-room['area']]
    st = shelf['start']
    assert shelf['kind'] == 'shelf' and shelf['label'] == 'Layout test room, Layout test shelf' and shelf['layout_id'] is None
    assert (st['width_in'], st['depth_in'], st['height_in']) == (22, 11, 90), 'its own width and depth, and 24 in above its top level'
    assert len(st['items']) == 4 and st['items'][1]['z'] == 23.75 and any('4 levels' in n for n in st['notes'])
    st = table['start']
    assert (st['width_in'], st['depth_in'], st['items']) == (36, 12, []) and any('starting guess' in n for n in st['notes']), 'a shelf with no measurements: a size to correct, and it says so'
    st = whole['start']
    assert whole['kind'] == 'room' and (st['width_in'], st['depth_in'], st['height_in']) == (144, 120, 96) and any('starting guess' in n for n in st['notes']), 'a room has no width in its measurements'
    a, b = st['items']
    assert (a['spot_id'], a['w'], a['d'], a['h'], a['z'], a['locked']) == (room['shelf'], 22, 11, 66, 0, False), 'its shelves are blocks on the floor, as wide, deep and tall as their measurements say'
    assert (b['spot_id'], b['w'], b['d'], b['h']) == (room['table'], 30, 12, 36) and b['x'] >= a['x'] + a['w'] and b['y'] == a['y'], 'side by side along the back wall'

def test_the_routes_keep_a_layout_and_refuse_what_makes_no_sense(room):
    with S.app.test_client() as c:
        places = c.get('/api/layouts').get_json()['places']
        shelf = next(p for p in places if p['pid'] == room['shelf'])
        size = {'width_in': 22, 'depth_in': 11, 'height_in': 90}
        bad = lambda body: c.post('/api/layouts', json=body, headers=OWN)
        assert bad(size).status_code == 400 and 'name' in bad(size).get_json()['error']
        assert bad({'name': 'No size'}).status_code == 400 and bad({'name': 'Too high', **size, 'height_in': 700}).status_code == 400
        assert bad({'name': 'Nowhere', **size, 'place': 987654}).status_code == 400 and bad({'name': 'Words', **size, 'width_in': 'wide'}).status_code == 400
        r = c.post('/api/layouts', json={'name': '  Tall   brown shelf ', 'place': shelf['pid'], **size, 'items': shelf['start']['items']}, headers=OWN)
        assert r.status_code == 201, r.get_data(as_text=True)
        L = r.get_json(); lid = L['id']
        assert L['name'] == 'Tall brown shelf' and L['spot_id'] == shelf['pid'] and L['place'].endswith('Layout test shelf') and (L['grid_in'], L['snap'], L['clear_in']) == (1, True, 1)
        assert [i['sort'] for i in L['items']] == [1, 2, 3, 4] and all(i['locked'] and i['shape'] == 'box' for i in L['items'])
        assert L['plants'] and all({'code', 'name', 'w', 'd', 'h', 'shape', 'guessed', 'here', 'on'} <= set(p) for p in L['plants']) and not any(p['on'] for p in L['plants'])
        assert L['lights'] and all(x['w'] > 0 and x['h'] > 0 and isinstance(x['hangs'], bool) for x in L['lights'])
        assert all(s['spot_id'] != shelf['pid'] for s in L['shelves']), 'a shelf is not offered as a thing to put on its own layout'
        # things: one of the record's plants (once), a light, something else; and what is refused
        P = L['plants'][0]; before = c.get(f"/api/plants/{P['code']}").get_json()
        add = lambda body, to=lid: c.post(f'/api/layouts/{to}/items', json=body, headers=OWN)
        r = add({'kind': 'plant', 'plant': P['code'].lower(), 'name': 'ignored', 'x': 2, 'y': 1, 'z': 0.75, 'w': P['w'], 'd': P['d'], 'h': P['h']})
        assert r.status_code == 201, r.get_data(as_text=True)
        it = next(i for i in r.get_json()['items'] if i['plant'] == P['code'])
        assert it['name'] == P['name'] and it['shape'] == 'round' and it['sort'] == 5 and next(p for p in r.get_json()['plants'] if p['code'] == P['code'])['on']
        r = add({'kind': 'plant', 'plant': P['code'], 'w': 6, 'd': 6, 'h': 8})
        assert r.status_code == 409 and 'already on this layout' in r.get_json()['error']
        assert add({'kind': 'plant', 'plant': 'P-99999', 'w': 6, 'd': 6, 'h': 8}).status_code == 404
        assert add({'kind': 'tree', 'name': 'Oak', 'w': 6, 'd': 6, 'h': 8}).status_code == 400 and add({'kind': 'other', 'w': 6, 'd': 6, 'h': 8}).status_code == 400
        assert add({'kind': 'other', 'name': 'Fan', 'w': 6, 'd': 6}).status_code == 400 and add({'kind': 'other', 'name': 'Fan', 'w': 0, 'd': 6, 'h': 8}).status_code == 400
        assert add({'kind': 'other', 'name': 'Fan', 'w': 6, 'd': 6, 'h': 8, 'x': 99999}).status_code == 400 and add({'kind': 'light', 'light_id': 987654, 'w': 6, 'd': 6, 'h': 2}).status_code == 400
        light = L['lights'][0]
        r = add({'items': [{'kind': 'light', 'light_id': light['id'], 'w': light['w'], 'd': light['d'], 'h': light['h'], 'z': 20},
                           {'kind': 'other', 'name': ' Humidifier ', 'shape': 'round', 'w': 8, 'd': 8, 'h': 12}, {'kind': 'zone', 'name': 'Door', 'shape': 'round', 'w': 30, 'd': 30, 'h': 80}]})
        assert r.status_code == 201
        by = {i['name']: i for i in r.get_json()['items']}
        assert by[light['name']]['light_id'] == light['id'] and by[light['name']]['owned'] == light['count'] and 'near_in' in by[light['name']]
        assert by['Humidifier']['shape'] == 'round' and by['Door']['shape'] == 'round' and by['Door']['kind'] == 'zone'
        # moving and resizing one thing; a plant keeps the record's name
        put = lambda iid, body: c.put(f'/api/layouts/items/{iid}', json=body, headers=OWN)
        r = put(it['id'], {'x': 3.456, 'h': 15, 'name': 'Renamed here', 'locked': True})
        assert r.status_code == 200 and (r.get_json()['item']['x'], r.get_json()['item']['h'], r.get_json()['item']['name'], r.get_json()['item']['locked']) == (3.46, 15, P['name'], True)
        assert put(by['Humidifier']['id'], {'name': 'Mist maker'}).get_json()['item']['name'] == 'Mist maker'
        assert put(it['id'], {'w': -1}).status_code == 400 and put(it['id'], {'shape': 'star'}).status_code == 400 and put(987654, {'x': 1}).status_code == 404
        after = c.get(f"/api/plants/{P['code']}").get_json()
        assert (after['version'], after['spot_id'], after['height_in']) == (before['version'], before['spot_id'], before['height_in']), 'a plant moved and resized on a layout is not changed on its own page'
        # the layout itself
        r = c.put(f'/api/layouts/{lid}', json={'height_in': 96, 'grid_in': 2, 'snap': False, 'clear_in': 0}, headers=OWN)
        assert r.status_code == 200 and (r.get_json()['height_in'], r.get_json()['grid_in'], r.get_json()['snap'], r.get_json()['clear_in'], r.get_json()['name']) == (96, 2, False, 0, 'Tall brown shelf')
        assert c.put(f'/api/layouts/{lid}', json={'name': '  '}, headers=OWN).status_code == 400 and c.put(f'/api/layouts/{lid}', json={'grid_in': 0}, headers=OWN).status_code == 400
        # a space of one's own; the same plant may be on two layouts, and its page can ask which
        r = c.post('/api/layouts', json={'name': 'Spare room idea', 'width_in': 120, 'depth_in': 96, 'height_in': 96}, headers=OWN)
        assert r.status_code == 201 and r.get_json()['place'] is None and r.get_json()['items'] == []
        other = r.get_json()['id']
        assert add({'kind': 'plant', 'plant': P['code'], 'w': 6, 'd': 6, 'h': 8}, other).status_code == 201
        on = c.get(f"/api/layouts?plant={P['code']}").get_json()['on']
        assert sorted(x['id'] for x in on) == sorted([lid, other]) and next(x for x in on if x['id'] == lid)['item'] == it['id']
        listed = c.get('/api/layouts').get_json()
        assert {lid, other} <= {x['id'] for x in listed['layouts']} and next(p for p in listed['places'] if p['pid'] == shelf['pid'])['layout_id'] == lid
        # History has the layout and the things put on it, and no line for each move
        d = conn(); notes = [r[0] for r in d.execute("SELECT note FROM audit_log WHERE field IN ('layout', 'layout_item') ORDER BY id")]; d.close()
        assert any(n.startswith('Layout added: Tall brown shelf') for n in notes) and any('3 things put on it' in n for n in notes) and not any(' moved' in n or ' made ' in n for n in notes)
        # taking a thing off, and removing the layout: the things on it go, the plant and the shelf stay
        assert c.delete(f"/api/layouts/items/{by['Door']['id']}", headers=OWN).status_code == 200 and c.delete(f"/api/layouts/items/{by['Door']['id']}", headers=OWN).status_code == 404
        assert c.delete(f'/api/layouts/{lid}', headers=OWN).status_code == 200 and c.get(f'/api/layouts/{lid}').status_code == 404
        d = conn()
        assert d.execute('SELECT COUNT(*) FROM layout_items WHERE layout_id=?', (lid,)).fetchone()[0] == 0 and d.execute('SELECT COUNT(*) FROM spots WHERE id=?', (shelf['pid'],)).fetchone()[0] == 1
        d.close()
        assert c.get(f"/api/plants/{P['code']}").get_json()['version'] == before['version'] and [x['id'] for x in c.get(f"/api/layouts?plant={P['code']}").get_json()['on']] == [other]
        assert c.delete(f'/api/layouts/{other}', headers=OWN).status_code == 200

def test_a_thing_whose_plant_was_archived_says_so_and_keeps_its_name():
    with S.app.test_client() as c:
        r = c.post('/api/plants', json={'fields': {'common_name': 'Layout test fern'}}, headers=OWN); assert r.status_code == 201
        code = r.get_json()['code']
        lid = c.post('/api/layouts', json={'name': 'Fern corner', 'width_in': 40, 'depth_in': 40, 'height_in': 80, 'items': [{'kind': 'plant', 'plant': code, 'w': 6, 'd': 6, 'h': 8}]}, headers=OWN).get_json()['id']
        assert c.post(f'/api/plants/{code}/status', json={'archived': True, 'reason': 'Given away'}, headers=OWN).status_code == 200
        it = c.get(f'/api/layouts/{lid}').get_json()['items'][0]
        assert it['gone'] is True and it['name'] == 'Layout test fern' and it['plant'] == code
        assert not any(p['code'] == code for p in c.get(f'/api/layouts/{lid}').get_json()['plants']), 'an archived plant is not offered'
        r = c.post(f'/api/layouts/{lid}/items', json={'kind': 'plant', 'plant': code, 'w': 6, 'd': 6, 'h': 8}, headers=OWN)
        assert r.status_code in (400, 409)
        assert c.delete(f'/api/layouts/{lid}', headers=OWN).status_code == 200

def test_a_viewer_reads_layouts_and_changes_none():
    with S.app.test_client() as c:
        c.get('/api/me', headers=TSO, **TS); c.get('/api/me', headers=VIEW, **TS)
        assert c.put('/api/people', json={'login': 'lyviewer@example.com', 'role': 'viewer'}, headers=OWN).status_code == 200
        r = c.post('/api/layouts', json={'name': 'Viewer test', 'width_in': 40, 'depth_in': 40, 'height_in': 80, 'items': [{'kind': 'other', 'name': 'Fan', 'w': 8, 'd': 8, 'h': 12}]}, headers=OWN)
        lid, iid = r.get_json()['id'], r.get_json()['items'][0]['id']
        assert c.get('/api/layouts', headers=VIEW, **TS).status_code == 200 and c.get(f'/api/layouts/{lid}', headers=VIEW, **TS).get_json()['items'][0]['name'] == 'Fan'
        for method, path, body in (('POST', '/api/layouts', {'name': 'Mine', 'width_in': 10, 'depth_in': 10, 'height_in': 10}), ('PUT', f'/api/layouts/{lid}', {'width_in': 50}), ('DELETE', f'/api/layouts/{lid}', None),
                                   ('POST', f'/api/layouts/{lid}/items', {'kind': 'other', 'name': 'Heater', 'w': 8, 'd': 8, 'h': 12}), ('PUT', f'/api/layouts/items/{iid}', {'x': 9}), ('DELETE', f'/api/layouts/items/{iid}', None)):
            assert c.open(path, method=method, json=body, headers=VIEW, **TS).status_code == 403, (method, path)
        L = c.get(f'/api/layouts/{lid}').get_json()
        assert (L['width_in'], len(L['items']), L['items'][0]['x']) == (40, 1, 0)
        assert c.delete(f'/api/layouts/{lid}', headers=OWN).status_code == 200

def test_the_tables_are_made_on_first_use_and_making_them_again_harms_nothing():
    c = sqlite3.connect(':memory:')
    LY.layout_tables(c)
    c.execute("INSERT INTO layouts(name, width_in, depth_in, height_in, created_at) VALUES('Kept', 10, 10, 10, 'now')")
    LY.layout_tables(c)                                                        # a record put back from a backup, or the second request
    assert c.execute('SELECT name, grid_in, snap, clear_in FROM layouts').fetchall() == [('Kept', 1, 1, 1)]
    assert {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")} >= {'layouts', 'layout_items'}
