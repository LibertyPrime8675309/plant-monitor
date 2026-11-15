"""Prototype (proto/layouts): layouts. What the record suggests for sizes (a plant's from its tray, its pot, its Pot size and its
height; a light's from how it holds; a shelf's levels from its measurements), what a layout of a place starts with, and the
routes: what they refuse, that a plant is on a layout once, that moving a plant on a layout changes nothing on its own page
while a height given there is saved on it, that a layout moves plants in the record only when told to, what a drawn light
carries for the page to work out the light from, that removing a layout removes the things drawn on it and nothing else, and
that a viewer changes nothing.
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
        # a plant's height given on a layout goes on its page too, with a line in its History; moving it changes nothing there
        after = c.get(f"/api/plants/{P['code']}").get_json()
        assert (after['version'], after['spot_id'], after['height_in']) == (before['version'] + 1, before['spot_id'], 15), 'the height typed on the layout is the height on its page'
        assert r.get_json()['item']['page_h'] == 15
        hist = c.get(f"/api/plants/{P['code']}/history").get_json()['audit'][0]
        assert (hist['field'], hist['old_value'], hist['new_value'], hist['note']) == ('height_in', None, '15.0', 'Height set on the layout "Tall brown shelf"')
        assert put(it['id'], {'x': 4, 'y': 2, 'w': 7}).status_code == 200 and put(it['id'], {'h': 15}).status_code == 200
        assert c.get(f"/api/plants/{P['code']}").get_json()['version'] == before['version'] + 1, 'moving it, widening it, or giving the same height again changes nothing on its page'
        assert put(it['id'], {'h': 700}).status_code == 400 and put(it['id'], {'h': 0.2}).status_code == 400, 'a height the page would refuse is refused here'
        assert c.get(f'/api/layouts/{lid}').get_json()['items'][4]['h'] == 15 and c.get(f"/api/plants/{P['code']}").get_json()['height_in'] == 15
        # the layout itself
        r = c.put(f'/api/layouts/{lid}', json={'height_in': 96, 'grid_in': 2, 'snap': False, 'clear_in': 0}, headers=OWN)
        assert r.status_code == 200 and (r.get_json()['height_in'], r.get_json()['grid_in'], r.get_json()['snap'], r.get_json()['clear_in'], r.get_json()['name']) == (96, 2, False, 0, 'Tall brown shelf')
        assert c.put(f'/api/layouts/{lid}', json={'name': '  '}, headers=OWN).status_code == 400 and c.put(f'/api/layouts/{lid}', json={'grid_in': 0}, headers=OWN).status_code == 400
        # a space of one's own; the same plant may be on two layouts, and its page can ask which
        r = c.post('/api/layouts', json={'name': 'Spare room idea', 'width_in': 120, 'depth_in': 96, 'height_in': 96}, headers=OWN)
        assert r.status_code == 201 and r.get_json()['place'] is None and r.get_json()['items'] == []
        other = r.get_json()['id']
        r = add({'kind': 'plant', 'plant': P['code'], 'w': 6, 'd': 6, 'h': 8}, other)
        assert r.status_code == 201 and r.get_json()['items'][0]['h'] == 15, 'a plant is as tall on every layout as its page says'
        assert c.get(f"/api/plants/{P['code']}").get_json()['height_in'] == 15, 'putting it on a layout does not change its page'
        twin = r.get_json()['items'][0]['id']
        assert put(twin, {'h': 18}).status_code == 200 and c.get(f'/api/layouts/{lid}').get_json()['items'][4]['h'] == 18, 'and a new height on one layout is its height on the other'
        # Undo sends what the page said before: a number, or none for a page that had no height
        r = put(twin, {'h': 8, 'page_h': before['height_in']})
        assert r.status_code == 200 and (r.get_json()['item']['h'], r.get_json()['item']['page_h']) == (8, before['height_in'])
        assert c.get(f"/api/plants/{P['code']}").get_json()['height_in'] == before['height_in']
        assert c.get(f'/api/layouts/{lid}').get_json()['items'][4]['h'] == 15, 'with no height on its page, each layout keeps the height it was drawn with'
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
        assert c.get(f"/api/plants/{P['code']}").get_json()['height_in'] == before['height_in'] and [x['id'] for x in c.get(f"/api/layouts?plant={P['code']}").get_json()['on']] == [other]
        assert c.delete(f'/api/layouts/{other}', headers=OWN).status_code == 200

def test_a_shelf_drawn_as_a_block_in_a_room_carries_its_levels(room):
    assert LY.layout_levels({'levels': 4, 'gaps_in': [23, 13, 27], 'width_in': 22, 'depth_in': 11}) == [
        {'n': 1, 'name': 'Level 1 (bottom)', 'z': 0.75, 'room': 23}, {'n': 2, 'name': 'Level 2', 'z': 24.5, 'room': 13},
        {'n': 3, 'name': 'Level 3', 'z': 38.25, 'room': 27}, {'n': 4, 'name': 'Level 4 (top)', 'z': 66.0, 'room': None}]
    assert LY.layout_levels({'width_in': 30, 'depth_in': 20}) == [] and LY.layout_levels({'levels': 3, 'width_in': 30, 'depth_in': 20}) == [], 'a table, or a shelf whose level heights are not measured, has only its top'
    with S.app.test_client() as c:
        start = next(p for p in c.get('/api/layouts').get_json()['places'] if p['pid'] == -room['area'])['start']
        lid = c.post('/api/layouts', json={'name': 'Levels test room', 'place': -room['area'], **{k: start[k] for k in ('width_in', 'depth_in', 'height_in', 'items')}}, headers=OWN).get_json()['id']
        L = c.get(f'/api/layouts/{lid}').get_json()
        by = {i['name']: i for i in L['items']}
        shelf, table = by['Layout test shelf'], by['Layout test table']
        assert [v['z'] for v in shelf['levels']] == [0.75, 24.5, 38.25, 66.0] and shelf['h'] == 66 and shelf['board_in'] == 0.75, 'the block is as tall as its top level, and says where each level is'
        assert table['levels'] == [], 'a table has only its top'
        r = c.post(f'/api/layouts/{lid}/items', json={'kind': 'other', 'name': 'Sofa', 'w': 60, 'd': 30, 'h': 30}, headers=OWN)
        assert 'levels' not in r.get_json()['items'][-1], 'a thing that is not one of the record\'s shelves has none'
        assert c.delete(f'/api/layouts/{lid}', headers=OWN).status_code == 200

def test_a_layout_moves_plants_in_the_record_only_when_told_to(room):
    with S.app.test_client() as c:
        made = [c.post('/api/plants', json={'fields': {'common_name': name}}, headers=OWN).get_json()['code'] for name in ('Layout move fern', 'Layout move fig')]
        fern, fig = made
        was = {x: c.get(f'/api/plants/{x}').get_json() for x in made}
        lid = c.post('/api/layouts', json={'name': 'Move test shelf', 'place': room['shelf'], 'width_in': 22, 'depth_in': 11, 'height_in': 90,
                                           'items': [{'kind': 'plant', 'plant': x, 'w': 6, 'd': 6, 'h': 8, 'x': 7 * i} for i, x in enumerate(made)]}, headers=OWN).get_json()['id']
        L = c.get(f'/api/layouts/{lid}').get_json()
        by = {i['plant']: i for i in L['items']}
        home = -was[fern]['area_id']
        assert by[fern]['rec'] == home and by[fern]['rec_label'] and L['pid'] == room['shelf'], 'each drawn plant says where the record has it'
        assert not next(p for p in L['plants'] if p['code'] == fern)['here']
        assert c.put(f"/api/layouts/items/{by[fern]['id']}", json={'x': 3, 'y': 2}, headers=OWN).status_code == 200
        assert c.get(f'/api/plants/{fern}').get_json()['version'] == was[fern]['version'], 'drawing and moving a plant on a layout moves nothing in the record'
        move = lambda moves, where=lid: c.post(f'/api/layouts/{where}/record', json={'moves': moves}, headers=OWN)
        # what is refused, and that nothing moves when any one of them is refused
        assert move([]).status_code == 400 and move([{'plant': 'P-99999', 'place': room['shelf']}]).status_code == 400 and move([{'plant': fern}]).status_code == 400
        assert move([{'plant': fern, 'place': room['shelf']}, {'plant': fig, 'place': 987654}]).status_code == 400
        other = c.get('/api/layouts').get_json()['places']; stray = next(p['pid'] for p in other if p['pid'] not in (room['shelf'], home))
        loose = c.post('/api/plants', json={'fields': {'common_name': 'Layout move stray'}}, headers=OWN).get_json()['code']
        r = move([{'plant': loose, 'place': room['shelf']}]); assert r.status_code == 400 and 'not on this layout' in r.get_json()['error']
        assert all(c.get(f'/api/plants/{x}').get_json()['version'] == was[x]['version'] for x in made)
        # the move: both plants are on the shelf in the record, each with a new version and a line that says where from
        r = move([{'plant': fern.lower(), 'place': room['shelf']}, {'plant': fig, 'place': room['shelf']}])
        assert r.status_code == 200, r.get_data(as_text=True)
        out = r.get_json()
        assert [(m['plant'], m['from'], m['to'], m['changed']) for m in out['moved']] == [(fern, home, room['shelf'], True), (fig, home, room['shelf'], True)]
        assert out['moved'][0]['to_label'].endswith('Layout test shelf') and all(i['rec'] == room['shelf'] for i in out['layout']['items'])
        assert all(p['here'] for p in out['layout']['plants'] if p['code'] in made)
        now = c.get(f'/api/plants/{fern}').get_json()
        assert (now['spot_id'], now['area_id'], now['version']) == (room['shelf'], room['area'], was[fern]['version'] + 1) and now['site'] != was[fern]['site'], 'its old Location follows the room, as on its own page'
        note = c.get(f'/api/plants/{fern}/history').get_json()['audit'][0]['note']
        assert note.startswith('Moved to Layout test room, Layout test shelf') and 'Move test shelf' in note
        assert move([{'plant': fern, 'place': room['shelf']}]).get_json()['moved'][0]['changed'] is False, 'already there: nothing to change'
        # to the room itself (no shelf), and back where it came from, as Undo sends it
        assert move([{'plant': fig, 'place': -room['area']}]).status_code == 200 and c.get(f'/api/plants/{fig}').get_json()['spot_id'] is None
        assert move([{'plant': fern, 'place': home}, {'plant': fig, 'place': home}]).status_code == 200
        back = c.get(f'/api/plants/{fern}').get_json()
        assert (back['spot_id'], back['area_id'], back['site']) == (was[fern]['spot_id'], was[fern]['area_id'], was[fern]['site'])
        # an archived plant is not moved; a viewer moves nothing
        assert c.post(f'/api/plants/{fig}/status', json={'archived': True}, headers=OWN).status_code == 200
        assert move([{'plant': fig, 'place': room['shelf']}]).status_code == 400
        c.get('/api/me', headers=TSO, **TS); c.get('/api/me', headers=VIEW, **TS)
        assert c.post(f'/api/layouts/{lid}/record', json={'moves': [{'plant': fern, 'place': room['shelf']}]}, headers=VIEW, **TS).status_code == 403
        assert c.get(f'/api/plants/{fern}').get_json()['spot_id'] is None and stray
        for x in (fern, loose): assert c.post(f'/api/plants/{x}/status', json={'archived': True}, headers=OWN).status_code == 200
        assert c.delete(f'/api/layouts/{lid}', headers=OWN).status_code == 200

def test_a_drawn_light_carries_what_the_page_works_the_light_out_from(room):
    with S.app.test_client() as c:
        code = c.post('/api/plants', json={'fields': {'common_name': 'Layout light fern', 'dli_low': 6, 'dli_high': 12}}, headers=OWN).get_json()['code']
        L = c.post('/api/layouts', json={'name': 'Light test shelf', 'place': room['shelf'], 'width_in': 22, 'depth_in': 11, 'height_in': 90}, headers=OWN).get_json()
        lid = L['id']
        light = next(x for x in L['lights'] if x['figures']); bare = {'kind': 'light', 'name': 'A lamp of my own', 'w': 5, 'd': 5, 'h': 6, 'z': 30}
        assert (light['hours'], light['dim_pct']) == (12, 100) or light['hours'] > 0, 'what one of your lights would start with is said before it is added'
        r = c.post(f'/api/layouts/{lid}/items', json={'items': [{'kind': 'light', 'light_id': light['id'], 'w': light['w'], 'd': light['d'], 'h': light['h'], 'z': 20}, bare,
                                                                 {'kind': 'plant', 'plant': code, 'w': 6, 'd': 6, 'h': 8}, {'kind': 'other', 'name': 'Fan', 'w': 6, 'd': 6, 'h': 8}]}, headers=OWN)
        assert r.status_code == 201, r.get_data(as_text=True)
        mine, lamp, fern, fan = r.get_json()['items']
        # one of your lights: its maker's figures, nearest first, its brightness steps, and the hours and brightness it is drawn with
        d = conn(); spec = json.loads(d.execute('SELECT data FROM lights WHERE id=?', (light['id'],)).fetchone()[0]); d.close()
        assert mine['pts'] and mine['pts'] == sorted(mine['pts']) and all(len(p) == 3 and p[0] > 0 and p[1] > 0 for p in mine['pts']) and len(mine['pts']) <= len(spec['ppfd'])
        assert (mine['hours'], mine['dim_pct']) == (light['hours'], light['dim_pct']) and mine['dims'][0] == 100 and mine['dims'] == sorted(mine['dims'], reverse=True)
        assert (lamp['pts'], lamp['hours'], lamp['dim_pct'], lamp['dims']) == ([], 12, 100, [100]), 'a light of your own naming has no figures to count'
        assert fern['need'] == {'lo': 6, 'hi': 12, 'target': 8.4} and 'hours' not in fern and 'hours' not in fan
        assert r.get_json()['verdicts']['too_dim'] == 'Too dim', 'the words are the ones Grow lights uses'
        put = lambda iid, body: c.put(f'/api/layouts/items/{iid}', json=body, headers=OWN)
        r = put(mine['id'], {'hours': 14.5, 'dim_pct': 50})
        assert r.status_code == 200 and (r.get_json()['item']['hours'], r.get_json()['item']['dim_pct']) == (14.5, 50)
        assert put(mine['id'], {'x': 2}).get_json()['item']['hours'] == 14.5, 'moving it keeps its setting'
        assert put(mine['id'], {'hours': 25}).status_code == 400 and put(mine['id'], {'dim_pct': 0}).status_code == 400 and put(mine['id'], {'hours': 'all day'}).status_code == 400
        assert put(mine['id'], {'hours': 0}).status_code == 200, 'a light may be drawn switched off'
        assert 'hours' not in put(fan['id'], {'hours': 9}).get_json()['item'], 'only a light has hours'
        # a light starts with the setting of a Grow lights spot that has it at this place
        r = c.post('/api/lights/spots', json={'name': 'Layout test spot', 'light': light['id'], 'units': 1, 'distance': 12, 'hours': 9, 'dim': 100, 'place': room['shelf']}, headers=OWN)
        assert r.status_code in (200, 201), r.get_data(as_text=True)
        again = c.get(f'/api/layouts/{lid}').get_json()
        assert next(x for x in again['lights'] if x['id'] == light['id'])['hours'] == 9
        r = c.post(f'/api/layouts/{lid}/items', json={'kind': 'light', 'light_id': light['id'], 'w': 5, 'd': 5, 'h': 2, 'z': 40}, headers=OWN)
        assert r.get_json()['items'][-1]['hours'] == 9 and r.get_json()['items'][0]['hours'] == 0, 'and one already drawn keeps its own'
        d = conn(); sid = d.execute("SELECT id FROM light_spots WHERE name='Layout test spot'").fetchone()[0]; d.close()
        assert c.delete(f'/api/lights/spots/{sid}', headers=OWN).status_code == 200
        assert c.post(f'/api/plants/{code}/status', json={'archived': True}, headers=OWN).status_code == 200
        assert c.delete(f'/api/layouts/{lid}', headers=OWN).status_code == 200

def test_a_table_made_before_lights_had_hours_gains_them():
    c = sqlite3.connect(':memory:'); c.row_factory = sqlite3.Row
    c.executescript(LY.LAYOUT_SCHEMA.replace('  hours REAL, dim_pct INTEGER,\n', ''))
    assert 'hours' not in {r[1] for r in c.execute('PRAGMA table_info(layout_items)')}
    LY.layout_tables(c); LY.layout_tables(c)
    assert {'hours', 'dim_pct'} <= {r[1] for r in c.execute('PRAGMA table_info(layout_items)')}

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
