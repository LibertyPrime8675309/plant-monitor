"""1.58.0 (November 12 review, item 4): an editor limited to some homes (people.edit_homes, 1.48.0) cannot change plants at another
home, however the request names the plant. Until now the limit was read out of the request before the route ran (the plant's code
in the path or in a few body keys), so a request that named the plant another way (a photo's id, a mix, a light spot) went through.
It is now also checked where a plant is fetched for a change and where it is changed (home_check in core.py).

The last test walks every route that changes data: each must be tried here against a plant at another home, or be listed as not
being about one home's plants. A new route fails it until someone decides which it is."""
import io, json, sqlite3
import pytest
import server as S

OWN = {'X-Editor': 'Owner'}                                                    # this computer's port: the owner
TSO = {'Tailscale-User-Login': 'owner@example.com', 'Tailscale-User-Name': 'Own'}
LIM = {'Tailscale-User-Login': 'limited@example.com', 'Tailscale-User-Name': 'Lim', 'X-Editor': 'Lim'}
TS = {'environ_overrides': {'SERVER_PORT': S.TS_PORT}}
F = 'P-006'                                                                    # a plant at the main home
TRIED = set()                                                                  # endpoints a case below was refused on

def conn():
    c = sqlite3.connect(S.DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    return c

def jpeg():
    from PIL import Image
    b = io.BytesIO(); Image.new('RGB', (40, 30), (90, 140, 60)).save(b, 'JPEG')
    return b.getvalue()

@pytest.fixture(scope='module')
def world():
    """The owner sets up: a second home with one plant of its own, an editor limited to that home, and one of everything that
    hangs off the plant at the main home."""
    with S.app.test_client() as c:
        c.get('/api/me', headers=TSO, **TS)                                    # someone is the owner before the editor arrives
        c.get('/api/me', headers=LIM, **TS)
        d = conn()
        main = S.home_place(d)['id']
        other = next(h['id'] for h in S.homes(d) if h['id'] != main)
        d.close()
        r = c.put('/api/people', json={'login': 'limited@example.com', 'role': 'editor', 'edit_homes': [other]}, headers=OWN); assert r.status_code == 200, r.get_data(as_text=True)
        r = c.post('/api/plants', json={'fields': {'common_name': 'Home limit test plant', 'home_id': other}}, headers=OWN); assert r.status_code == 201, r.get_data(as_text=True)
        mine = r.get_json()['code']
        W = {'main': main, 'other': other, 'mine': mine}
        P = c.get(f'/api/plants/{F}').get_json()
        assert (P.get('home_id') or main) == main
        W['photo'] = P['photos'][0]['id']
        r = c.post('/api/care', json={'plant': F, 'kind': 'check'}, headers=OWN); assert r.status_code in (200, 201), r.get_data(as_text=True)
        d = conn()
        W['care'] = d.execute('SELECT id FROM care_log WHERE plant_code=? ORDER BY id DESC LIMIT 1', (F,)).fetchone()[0]
        r = c.post('/api/fertilizer', json={'plant': F, 'product': 'Test feed', 'applied_on': S.local_today(d).isoformat()}, headers=OWN); assert r.status_code in (200, 201), r.get_data(as_text=True)
        W['fert'] = d.execute('SELECT id FROM fertilizer_log WHERE plant_code=? ORDER BY id DESC LIMIT 1', (F,)).fetchone()[0]
        r = c.post('/api/requests', json={'plant_code': F, 'text': 'What colour are the flowers?'}, headers=OWN); assert r.status_code in (200, 201), r.get_data(as_text=True)
        W['request'] = d.execute('SELECT id FROM requests WHERE plant_code=? ORDER BY id DESC LIMIT 1', (F,)).fetchone()[0]
        am = d.execute('SELECT id FROM amendments ORDER BY id LIMIT 1').fetchone()[0]
        W['parts'] = [{'amendment_id': am, 'parts': 1}]
        r = c.post(f'/api/mixes/plant/{F}', json={'parts': W['parts']}, headers=OWN); assert r.status_code in (200, 201), r.get_data(as_text=True)
        W['mix'] = d.execute('SELECT id FROM pot_mixes WHERE plant_code=? ORDER BY id DESC LIMIT 1', (F,)).fetchone()[0]
        r = c.post('/api/groups', json={'name': 'Home limit group', 'kind': 'picked', 'codes': [F, mine]}, headers=OWN); assert r.status_code in (200, 201), r.get_data(as_text=True)
        W['group'] = d.execute("SELECT id FROM plant_groups WHERE name='Home limit group'").fetchone()[0]
        r = c.post(f"/api/groups/{W['group']}/apply", json={'set': {'water_notes': 'Set for the home limit test'}, 'codes': [F]}, headers=OWN); assert r.status_code == 200, r.get_data(as_text=True)
        W['bulk'] = r.get_json()['bulk_id']
        light = d.execute('SELECT id FROM lights ORDER BY id LIMIT 1').fetchone()[0]
        W['light'] = light
        r = c.post('/api/lights/spots', json={'name': 'Home limit spot', 'light': light, 'units': 1, 'distance': 12, 'hours': 12, 'plants': [F]}, headers=OWN); assert r.status_code in (200, 201), r.get_data(as_text=True)
        W['lspot'] = d.execute("SELECT id FROM light_spots WHERE name='Home limit spot'").fetchone()[0]
        r = c.post('/api/lights/spots', json={'name': 'Home limit spot 2', 'light': light, 'units': 1, 'distance': 12, 'hours': 12, 'plants': []}, headers=OWN); assert r.status_code in (200, 201), r.get_data(as_text=True)
        W['lspot2'] = d.execute("SELECT id FROM light_spots WHERE name='Home limit spot 2'").fetchone()[0]
        r = c.post('/api/browse/sightings', json={'plant': F, 'pest': 'Not sure'}, headers=OWN); assert r.status_code in (200, 201), r.get_data(as_text=True)
        W['sighting'] = d.execute('SELECT id FROM pest_sightings WHERE plant_code=? ORDER BY id DESC LIMIT 1', (F,)).fetchone()[0]
        a = d.execute('SELECT area_id FROM plants WHERE code=?', (F,)).fetchone()[0]
        W['area'] = a
        r = c.post('/api/where/spots', json={'area_id': a, 'name': 'Home limit shelf'}, headers=OWN); assert r.status_code in (200, 201), r.get_data(as_text=True)
        W['spot'] = d.execute("SELECT id FROM spots WHERE name='Home limit shelf'").fetchone()[0]
        r = c.put(f'/api/plants/{F}', json={'base_version': c.get(f'/api/plants/{F}').get_json()['version'], 'fields': {'spot_id': W['spot']}}, headers=OWN); assert r.status_code == 200, r.get_data(as_text=True)
        x = d.execute("SELECT code, location, area_id FROM plants WHERE status='active' AND spot_id IS NULL AND COALESCE(home_id, ?)=? AND code<>? ORDER BY code LIMIT 1", (main, main, F)).fetchone()
        W['loose'] = {'code': x['code'], 'text': (x['location'] or '').strip(), 'area': x['area_id']}      # a plant at the main home with no spot yet
        d.execute("INSERT INTO readings(ts, source, device, temp_f) VALUES(?, 'sensor', 'limit-probe', 70)", (S.now(),)); d.commit()
        W['version'] = c.get(f'/api/plants/{F}').get_json()['version']
        W['counts'] = counts(d)
        d.close()
        yield c, W

def counts(d):
    q = lambda sql: d.execute(sql, (F,)).fetchone()[0]
    return {'care': q('SELECT COUNT(*) FROM care_log WHERE plant_code=?'), 'fert': q('SELECT COUNT(*) FROM fertilizer_log WHERE plant_code=?'),
            'requests': q('SELECT COUNT(*) FROM requests WHERE plant_code=?'), 'mixes': q('SELECT COUNT(*) FROM pot_mixes WHERE plant_code=?'),
            'photos': q('SELECT COUNT(*) FROM photos p JOIN plants x ON x.id=p.plant_id WHERE x.code=?'), 'lights': q('SELECT COUNT(*) FROM light_assign WHERE plant_code=?'),
            'sightings': q('SELECT COUNT(*) FROM pest_sightings WHERE plant_code=?'), 'spot': q('SELECT spot_id FROM plants WHERE code=?'),
            'members': q('SELECT COUNT(*) FROM group_members m JOIN plants x ON x.id=m.plant_id WHERE x.code=?')}

def refused(c, endpoint, method, path, **kw):
    """The limited editor tries it; it must be refused for the plant's home, by name."""
    headers = dict(LIM, **kw.pop('headers', {}))
    r = c.open(path, method=method, headers=headers, **TS, **kw)
    text = r.get_data(as_text=True)
    assert r.status_code == 403 and ('You can change plants at' in text or 'You can add or move plants at' in text), (endpoint, method, path, r.status_code, text[:300])
    TRIED.add(endpoint)

def test_a_limited_editor_cannot_change_a_plant_at_another_home_by_any_route(world):
    c, W = world
    today = S.local_today(conn()).isoformat()
    photo = lambda name='x.jpg': {'files': (io.BytesIO(jpeg()), name)}
    # --- the plant's own page and what hangs off it
    refused(c, 'update_plant', 'PUT', f'/api/plants/{F}', json={'base_version': W['version'], 'fields': {'notes': 'changed'}})
    refused(c, 'plant_identify', 'POST', f'/api/plants/{F}/identify', json={})
    refused(c, 'add_photos', 'POST', f'/api/plants/{F}/photos', data=photo(), content_type='multipart/form-data')
    refused(c, 'restore', 'POST', f'/api/plants/{F}/restore/1')
    refused(c, 'plant_site', 'POST', f'/api/plants/{F}/site', json={'site': 'Indoors'})
    refused(c, 'plant_status', 'POST', f'/api/plants/{F}/status', json={'archived': True})
    refused(c, 'prep_traits', 'POST', f'/api/plants/{F}/prep-traits', json={'leaf_type': 'Smooth'})
    refused(c, 'plant_groups_route', 'POST', f'/api/plants/{F}/groups', json={'picked': []})
    # --- records that follow the plant, named by their own id (these went through before 1.58.0)
    refused(c, 'delete_photo', 'DELETE', f"/api/photos/{W['photo']}")
    refused(c, 'patch_photo', 'PATCH', f"/api/photos/{W['photo']}", json={'caption': 'changed'})
    refused(c, 'care_one', 'DELETE', f"/api/care/{W['care']}")
    refused(c, 'fertilizer_one', 'DELETE', f"/api/fertilizer/{W['fert']}")
    refused(c, 'fertilizer_one', 'PUT', f"/api/fertilizer/{W['fert']}", json={'product': 'Other feed'})
    refused(c, 'request_one', 'PUT', f"/api/requests/{W['request']}", json={'answer': 'Blue'})
    refused(c, 'mixes_plant', 'POST', f'/api/mixes/plant/{F}', json={'parts': W['parts']})
    refused(c, 'mixes_pot_del', 'DELETE', f"/api/mixes/pot/{W['mix']}")
    refused(c, 'browse_sighting_delete', 'DELETE', f"/api/browse/sightings/{W['sighting']}")
    # --- care and the like, with the plant in the body
    refused(c, 'care', 'POST', '/api/care', json={'plant': F, 'kind': 'water'})
    refused(c, 'care', 'POST', '/api/care', json={'plants': [W['mine'], F], 'kind': 'water'})
    refused(c, 'fertilizer', 'POST', '/api/fertilizer', json={'plants': [F], 'product': 'Feed', 'applied_on': today})
    refused(c, 'requests_list', 'POST', '/api/requests', json={'plant_code': F, 'text': 'A question'})
    refused(c, 'frost_mark', 'POST', '/api/frost/done', json={'date': today, 'code': F, 'what': 'covered'})
    refused(c, 'outside_porch', 'POST', '/api/outside/porch', json={'code': F, 'action': 'start'})
    refused(c, 'turning', 'PUT', '/api/turning', json={'plant': F, 'on': False})
    refused(c, 'repotting', 'PUT', '/api/repotting', json={'plant': F, 'every': 'off'})
    refused(c, 'identify_confirm', 'POST', f'/api/identify/confirm?plant={F}&name=Ipomoea%20batatas')
    refused(c, 'identify_reject', 'POST', '/api/identify/reject', json={'plant': F, 'name': 'Ipomoea batatas'})
    refused(c, 'browse_sightings', 'POST', '/api/browse/sightings', json={'plant': F, 'pest': 'Not sure'})
    refused(c, 'sensor_save', 'PUT', '/api/sensors/limit-probe', json={'name': 'Probe', 'plant': F})
    # --- several plants at once
    refused(c, 'group_apply', 'POST', f"/api/groups/{W['group']}/apply", json={'set': {'water_notes': 'Changed by the limited editor'}, 'codes': [F]})
    refused(c, 'group_spot', 'POST', f"/api/groups/{W['group']}/spot", json={'spot': None, 'codes': [F]})
    refused(c, 'bulk_undo', 'POST', f"/api/bulk/{W['bulk']}/undo")
    # --- grow light spots: which light a plant is under
    refused(c, 'light_spot_add', 'POST', '/api/lights/spots', json={'name': 'Another spot', 'light': W['light'], 'units': 1, 'distance': 12, 'hours': 12, 'plants': [F]})
    refused(c, 'light_spot_one', 'PUT', f"/api/lights/spots/{W['lspot']}", json={'name': 'Home limit spot', 'light': W['light'], 'units': 1, 'distance': 12, 'hours': 12, 'plants': []})
    refused(c, 'light_spot_one', 'DELETE', f"/api/lights/spots/{W['lspot']}")
    refused(c, 'light_spot_add_plants', 'POST', f"/api/lights/spots/{W['lspot2']}/plants", json={'add': [F]})
    # --- rooms and spots: where a plant stands
    L = W['loose']
    refused(c, 'where_sort', 'POST', '/api/where/sort', json={'items': [{'text': L['text'], 'from_area_id': L['area'], 'area_id': L['area'], 'name': 'A new shelf'}]})
    assert conn().execute('SELECT spot_id FROM plants WHERE code=?', (L['code'],)).fetchone()[0] is None
    refused(c, 'where_spot_one', 'DELETE', f"/api/where/spots/{W['spot']}")
    # --- a new plant, or a move, lands only at the editor's homes
    refused(c, 'create_plant', 'POST', '/api/plants', json={'fields': {'common_name': 'Stray', 'home_id': W['main']}})
    refused(c, 'create_plant', 'POST', '/api/plants', json={'fields': {'common_name': 'Stray with no home named'}})
    refused(c, 'several_create', 'POST', '/api/plants/several', json={'plants': [{'fields': {'common_name': 'Stray', 'home_id': W['main']}}]})
    mine_v = c.get(f"/api/plants/{W['mine']}").get_json()['version']
    refused(c, 'update_plant', 'PUT', f"/api/plants/{W['mine']}", json={'base_version': mine_v, 'fields': {'home_id': W['main']}})
    # --- and nothing about the plant changed
    d = conn()
    assert c.get(f'/api/plants/{F}').get_json()['version'] == W['version']
    assert counts(d) == W['counts']
    d.close()

def test_the_same_editor_can_still_work_at_their_own_home(world):
    c, W = world
    M = W['mine']
    ok = lambda r: r.status_code in (200, 201) or pytest.fail(r.get_data(as_text=True)[:300])
    v = c.get(f'/api/plants/{M}').get_json()['version']
    ok(c.put(f'/api/plants/{M}', json={'base_version': v, 'fields': {'notes': 'Looked after from here'}}, headers=LIM, **TS))
    ok(c.post('/api/care', json={'plant': M, 'kind': 'water'}, headers=LIM, **TS))
    ok(c.post(f'/api/plants/{M}/photos', data={'files': (io.BytesIO(jpeg()), 'mine.jpg')}, content_type='multipart/form-data', headers=LIM, **TS))
    pid = c.get(f'/api/plants/{M}').get_json()['photos'][0]['id']
    ok(c.open(f'/api/photos/{pid}', method='PATCH', json={'caption': 'My own'}, headers=LIM, **TS))
    ok(c.post(f'/api/mixes/plant/{M}', json={'parts': W['parts']}, headers=LIM, **TS))
    ok(c.post('/api/plants', json={'fields': {'common_name': 'A new one here', 'home_id': W['other']}}, headers=LIM, **TS))
    ok(c.post('/api/lights/spots', json={'name': 'My own spot', 'light': W['light'], 'units': 1, 'distance': 12, 'hours': 12, 'plants': [M]}, headers=LIM, **TS))
    # things that are not one home's plants stay open to any editor
    ok(c.post('/api/groups', json={'name': 'My own group', 'kind': 'picked', 'codes': [M]}, headers=LIM, **TS))
    ok(c.post('/api/to-photograph', json={'label': 'The new shelf'}, headers=LIM, **TS))

def test_an_editor_without_a_limit_and_the_owner_are_not_held_back(world):
    c, W = world
    c.get('/api/me', headers={'Tailscale-User-Login': 'free@example.com', 'Tailscale-User-Name': 'Free'}, **TS)
    assert c.put('/api/people', json={'login': 'free@example.com', 'role': 'editor', 'edit_homes': []}, headers=OWN).status_code == 200
    H = {'Tailscale-User-Login': 'free@example.com', 'Tailscale-User-Name': 'Free', 'X-Editor': 'Free'}
    assert c.post('/api/care', json={'plant': F, 'kind': 'check'}, headers=H, **TS).status_code in (200, 201)
    assert c.post('/api/care', json={'plant': F, 'kind': 'check'}, headers=OWN).status_code in (200, 201)
    # reading is never limited
    assert c.get(f'/api/plants/{F}', headers=LIM, **TS).status_code == 200

# Routes that change something which is not one home's plants (or change nothing of the record at all): open to any editor, or
# closed by the owner-only and viewer rules, which test_access and the access check cover.
FREE = {
    # the owner's: backups, people, settings, jobs, problems, keys
    'backups', 'backup_file', 'backup_restore', 'backup_settings_put', 'backup_copies_api', 'wx_backup_api', 'wx_backup_settings_put', 'people', 'settings', 'jobs_run_now', 'problems_api',
    'identify_settings', 'library_settings', 'weather_settings', 'shops_api', 'shops_keys', 'ingest_regen', 'calendar_new_link',
    # a person's own: name, settings, devices, "Got it"
    'me', 'me_prefs', 'push_device_rm', 'push_subscribe', 'push_test', 'whatsnew_seen', 'for_claude_copied',
    # knowledge about species, not about one plant
    'facts_import', 'facts_propose', 'facts_accept', 'facts_reject', 'species_facts', 'library_notes', 'library_care', 'library_local',
    'library_areas', 'library_area_one', 'library_areas_stop',
    # asking what a picture or a recording shows (nothing is changed), and pictures waiting to be used
    'identify', 'identify_claude', 'identify_plantnet', 'voice', 'several_identify', 'several_photo', 'browse_photo', 'group_preview', 'group_match',
    # lists that belong to the whole record: groups, lights, pots, mixes and recipes, fertilizers, stores, the wishlist
    'groups_list', 'group_one', 'group_members_change', 'checkup_group', 'checkup_settings', 'light_add', 'light_one', 'light_status',
    'containers', 'container_one', 'container_photos', 'container_photo_del', 'mixes_am_add', 'mixes_am_one', 'mixes_every',
    'mixes_recipe_add', 'mixes_recipe_one', 'fertilizer_products', 'fertilizer_product_one', 'shop_details', 'shop_lookup_api',
    'shop_note_add', 'shop_note_rm', 'wishlist_api', 'wishlist_alerts', 'shops_check',
    # rooms, shelves and places themselves (the plants in them are checked when they would move: where_sort, where_spot_one above)
    'where_area_add', 'where_spot_add', 'light_place_add', 'light_place_one', 'light_spot_checked',
    'fit_place_one', 'fit_place_photos_add', 'fit_place_photo_one', 'places', 'place_one',
    # photos not on a plant, the list of things to photograph, mushroom finds, sensors, the weather
    'add_unassigned', 'share_target', 'to_photograph', 'to_photograph_item', 'fungi_list', 'fungi_one', 'fungi_add_photos', 'fungi_status',
    'fungi_photo', 'sensor_forget', 'sensor_calibrate', 'current', 'post_readings', 'weather_refresh', 'calendar_settings',
    # plant-sitter links (the sitter's ticks are their own record)
    'sitter_shares', 'sitter_share_stop', 'share_tick',
}
# Reached through plant_row() and apply_changes(), which hold the limit, but needing more set-up than this file makes
LOOKUP = {'conflict_decide': ('plant_row(', 'apply_changes('),            # an offline clash decided for the phone's value
          'where_area_one': ('apply_changes(', 'where_area_delete('),      # a room made sheltered or removed: the plants in it change
          'light_spot_plan_all': ('make_spot(',)}                          # every suggested spot at once: set_spot_plants() checks each plant

def test_every_route_that_changes_a_plant_keeps_the_home_limit(world):
    import inspect
    every = {r.endpoint for r in S.app.url_map.iter_rules() if r.methods - {'GET', 'HEAD', 'OPTIONS'}}
    for ep, needs in LOOKUP.items():
        src = inspect.getsource(S.app.view_functions[ep])
        assert all(n in src for n in needs), f'{ep} no longer goes through {needs}: try it in the first test instead'
    unknown = every - TRIED - FREE - set(LOOKUP)
    assert not unknown, ('These routes change something and are not in this file. If one changes a plant (or a record that follows a plant), '
                         'make it call plant_row() or home_check() and add a case to the first test; if not, add it to FREE: ' + ', '.join(sorted(unknown)))
    gone = (FREE | set(LOOKUP)) - every
    assert not gone, 'No longer routes (take them out of this file): ' + ', '.join(sorted(gone))
    assert not (TRIED & FREE), 'Listed as free but tried as a plant route: ' + ', '.join(sorted(TRIED & FREE))
