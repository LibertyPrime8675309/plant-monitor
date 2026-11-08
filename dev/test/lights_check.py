"""Checks 1.13.0: grow lights. Your lights (from upgrade batch batchA3), light spots, the suggested layout, the light maths,
the step-down plan, the plant page note, the audit log, and that people who can only view cannot change anything.
Start the mock server with a fresh data folder first (MOCK_TS=1), then:  python3 dev/test/lights_check.py
Screenshots: dev/tmp/shots/lights-*.png"""
import json, os, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'app'))
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=LOCAL, h=None):
    hd = {'Content-Type': 'application/json', 'X-Editor': 'Light Test', **(h or {})}
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None, headers=hd, method=m)
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'null')
    except urllib.error.HTTPError as e:
        t = e.read().decode()
        try: t = json.loads(t).get('error', t)
        except ValueError: pass
        return e.code, t

# ---- the maths, straight from the server module (no database needed)
os.environ.setdefault('DATA_DIR', os.path.join(OUT, '..', 'lights-check-data'))
import server as S
pts = [(12, 719.41, 0.54), (24, 233.57, 1.51), (36, 106.4, 2.26), (48, 52.39, 5.06)]
check(abs(S.ppfd_at(pts, 24) - 233.57) < 0.01 and abs(S.ppfd_at(pts, 36) - 106.4) < 0.01, "light at the maker's own distances is the maker's figure")
check(233.57 > S.ppfd_at(pts, 30) > 106.4, 'between two distances it falls smoothly')
check(S.dli_of(100, 12) == 4.3, '100 PAR for 12 hours is 4.3 mol/m2 a day')
check(S.light_verdict(2.0, 3, 8) == 'too_dim' and S.light_verdict(2.8, 3, 8) == 'dim' and S.light_verdict(5, 3, 8) == 'good' and S.light_verdict(9, 3, 8) == 'bright' and S.light_verdict(12, 3, 8) == 'too_bright', 'verdicts: too dim, a bit dim, good, a bit bright, too bright')
st = S.light_setting({'ppfd': [list(p) for p in pts], 'dimming': [25, 50, 75, 100]}, 10, 6, 15)
check(st and st['reach'] == 'ok' and 6 <= st['dli'] <= 15 and st['hours'] == 12, f"a setting for 10 mol/day under the tripod: {st and (st['distance_in'], st['hours'], st['dli'])}")
weak = S.light_setting({'ppfd': [[6, 35.78, 1.0]]}, 20)
check(weak['reach'] == 'weak', 'a pot clip cannot give 20 mol/day, and says so')

# ---- the lights from the batch
st, j = call('GET', '/api/lights')
check(st == 200 and len(j['lights']) == 11, f"the 11 grow lights arrived with the update ({len(j['lights'])})")
by = {L['key']: L for L in j['lights']}
check(by['barrina-t5']['count'] == 2 and by['sansi-10w']['count'] == 6 and by['sansi-pot-clip']['count'] == 3 and by['sansi-30w']['count'] == 2, 'with the right counts')
check(all(L['photo'] for k, L in by.items() if k != 'disk-light') and not by['disk-light']['photo'], 'every light but the disk light has a photo')
check(by['gooingtop-clip']['specs'].get('estimated') and not by['sansi-tripod']['specs'].get('estimated'), "estimates are marked as Claude's, makers' figures are not")
for L in j['lights']:
    if L['photo']:
        with urllib.request.urlopen(LOCAL + '/' + L['photo']) as r: ok = r.status == 200 and r.headers['Content-Type'].startswith('image/jpeg')
        if not ok: check(False, 'photo loads: ' + L['photo'])
check(True, 'the light photos load')
check(len(j['candidates']) >= 30 and j['plan'] and all(s['units'] >= 1 for s in j['plan']), f"a suggested layout for the {len(j['candidates'])} plants inside or coming in")
used = {}
for s in j['plan']: used[s['light_id']] = used.get(s['light_id'], 0) + s['units']
check(all(used.get(L['id'], 0) <= L['count'] for L in j['lights']), 'the layout never uses more of a light than you have')
check(all(sum(1 for s in j['plan'] if s['light_id'] == L['id']) <= L['count'] for L in j['lights']), 'and each light is in at most as many spots as you have of it')
placed = [c for s in j['plan'] for c in s['codes']]
check(len(placed) == len(set(placed)), 'no plant is in two suggested spots')
good = sum(1 for s in j['plan'] for p in s['plants'] if p['verdict'] == 'good')
check(good >= len(placed) * 0.8, f'most suggested plants get a good amount of light ({good} of {len(placed)})')
st, rq = call('GET', '/api/requests')
keys = {r.get('rkey') for r in (rq if isinstance(rq, list) else rq.get('requests', []))}
check({'lights-sockets', 'lights-t8-set', 'lights-disk', 'lights-spots'} <= keys, 'questions for Ethan about the lights are in the open requests')

# ---- set up a spot from the suggestion, change it, move a plant, remove it
p0 = next((s for s in j['plan'] if len(s['codes']) >= 2), j['plan'][0])
st, prev = call('GET', '/api/lights/preview?light=%d&distance=%g&hours=%g&dim=%d&units=%d&plants=%s' % (p0['light_id'], p0['distance_in'], p0['hours'], p0['dim_pct'], p0['units'], ','.join(p0['codes'])))
check(st == 200 and prev['dli'] == p0['dli'] and len(prev['plants']) == len(p0['codes']), 'the preview matches the suggestion')
st, r = call('POST', '/api/lights/spots', {'name': 'Living room window', 'light': p0['light_id'], 'units': p0['units'], 'distance': p0['distance_in'], 'hours': p0['hours'], 'dim': p0['dim_pct'], 'plants': p0['codes']})
check(st == 201, 'a spot is set up from the suggestion')
sid = r['id']
st, j2 = call('GET', '/api/lights')
check(any(s['id'] == sid and s['name'] == 'Living room window' for s in j2['spots']) and all(j2['assigned'].get(c) == sid for c in p0['codes']), 'its plants are in it')
check(not any(c in s['codes'] for s in j2['plan'] for c in p0['codes']), 'and are no longer in the suggested layout')
L0 = next(L for L in j2['lights'] if L['id'] == p0['light_id'])
check(L0['in_use'] == p0['units'], 'the light shows how many are in use')
st, g = call('GET', '/api/lights?plant=' + p0['codes'][0])
check(st == 200 and g['spot'] and g['spot']['id'] == sid, "the plant's own page knows its spot")
other = next(c['code'] for c in j2['candidates'] if c['code'] not in p0['codes'])
st, r = call('POST', '/api/lights/spots', {'name': 'Hall shelf', 'light': by['sansi-tripod']['id'], 'units': 1, 'distance': 20, 'hours': 12, 'plants': [p0['codes'][0], other]})
check(st == 201, 'a second spot')
sid2 = r['id']
st, j3 = call('GET', '/api/lights')
check(j3['assigned'].get(p0['codes'][0]) == sid2, 'ticking a plant in another spot moves it there')
st, _ = call('PUT', '/api/lights/spots/%d' % sid2, {'name': 'Hall shelf', 'light': by['sansi-tripod']['id'], 'units': 1, 'distance': 30, 'hours': 14, 'dim': 75, 'plants': [other]})
st, j4 = call('GET', '/api/lights')
s2 = next(s for s in j4['spots'] if s['id'] == sid2)
check(st == 200 and s2['distance_in'] == 30 and s2['dim_pct'] == 75 and [p['code'] for p in s2['plants']] == [other], 'a spot can be changed')
check(call('POST', '/api/lights/spots', {'name': '', 'light': by['sansi-tripod']['id'], 'distance': 20, 'hours': 12})[0] == 400, 'a spot needs a name')
check(call('POST', '/api/lights/spots', {'name': 'X', 'light': 99999, 'distance': 20, 'hours': 12})[0] == 400, 'and one of your lights')
st, msg = call('DELETE', '/api/lights/%d' % by['sansi-tripod']['id'])
check(st == 409 and 'spot' in msg, 'a light in use cannot be removed')
st, _ = call('DELETE', '/api/lights/spots/%d' % sid2)
check(st == 200 and other not in call('GET', '/api/lights')[1]['assigned'], 'removing a spot frees its plants')

# ---- 1.41.0: what a light can give, the best setting, a better spot, adding plants from a plant's page
j8 = call('GET', '/api/lights')[1]
d8 = {L['key']: L for L in j8['lights']}
R = d8['sansi-80w']['reach']
check(R and R['near_in'] == 12 and R['far_in'] == 48 and R['dim_min'] == 25 and R['dli_any'][0] < R['dli12'][0] < R['dli12'][1] < R['dli_any'][1]
      and abs(R['dli12'][1] - S.dli_of(R['ppfd_max'], 12)) <= 0.1, f"the 80 W bulb's reach: {R and (R['ppfd_max'], R['ppfd_min'], R['dli12'], R['dli_any'])}")
check(d8['sansi-pot-clip']['reach']['one_point'] and d8['disk-light']['room_light'] and not any(L['room_light'] for k, L in d8.items() if k != 'disk-light'), 'one-distance lights and the room light are marked')
check(all('foot' in c and 'photo' in c and 'inside' in c for c in j8['candidates']) and sum(1 for c in j8['candidates'] if c['photo']) > len(j8['candidates']) / 2, 'each plant in the list has its photo and the room its pot takes')
needy = sorted([c for c in j8['candidates'] if c['need'] and c['code'] not in j8['assigned']], key=lambda c: c['need']['target'])
lowp, mids = needy[0], needy[len(needy) // 2: len(needy) // 2 + 4]
st, best = call('GET', '/api/lights/best?light=%d&units=1&plants=%s' % (d8['sansi-tripod']['id'], ','.join(c['code'] for c in mids)))
st2, pv = call('GET', '/api/lights/preview?light=%d&distance=%g&hours=%g&dim=%d&units=1&plants=%s' % (d8['sansi-tripod']['id'], best['distance_in'], best['hours'], best['dim_pct'], ','.join(c['code'] for c in mids)))
check(st == 200 and best['of'] == 4 and best['good'] >= 3 and sum(p['verdict'] == 'good' for p in pv['plants']) == best['good'] and pv['dli'] == best['dli'],
      f"best setting for 4 plants under the tripod: {best.get('distance_in')} in, {best.get('hours')} h, {best.get('good')} of 4 in range, as the preview says")
check(call('GET', '/api/lights/best?light=%d&units=1&plants=' % d8['sansi-tripod']['id'])[0] == 400, 'the best setting needs ticked plants')
st, a = call('POST', '/api/lights/spots', {'name': 'Too bright test', 'light': d8['sansi-80w']['id'], 'units': 1, 'distance': 14, 'hours': 14, 'plants': [lowp['code']]})
st, bb = call('POST', '/api/lights/spots', {'name': 'Dim test', 'light': d8['barrina-t5']['id'], 'units': 1, 'distance': 12, 'hours': 12, 'plants': []})
j9 = call('GET', '/api/lights')[1]
sa, sb = next(s for s in j9['spots'] if s['id'] == a['id']), next(s for s in j9['spots'] if s['id'] == bb['id'])
pl = sa['plants'][0]
want_b = lowp['need']['lo'] <= sb['dli'] <= lowp['need']['hi']
check(pl['verdict'] == 'too_bright' and (pl['better'] or {}).get('id') == (bb['id'] if want_b else None), f"a plant too bright in its spot is pointed at one that suits it ({pl['verdict']}, {pl['better']}, other spot {sb['dli']})")
pv = call('GET', '/api/lights/preview?light=%d&distance=14&hours=14&dim=100&units=1&plants=%s&spot=%d' % (d8['sansi-80w']['id'], lowp['code'], a['id']))[1]
check((pv['plants'][0]['better'] or {}).get('id') == (bb['id'] if want_b else None), 'the spot window says so too')
st, g = call('GET', '/api/lights?plant=' + lowp['code'])
check(st == 200 and g['need'] and {x['id'] for x in g['spots']} >= {a['id'], bb['id']} and next(x for x in g['spots'] if x['id'] == a['id'])['verdict'] == 'too_bright', "the plant's page lists your spots with how each suits it")
st, r = call('POST', '/api/lights/spots/%d/plants' % bb['id'], {'add': [lowp['code']]})
check(st == 200 and call('GET', '/api/lights')[1]['assigned'].get(lowp['code']) == bb['id'], 'adding it to another spot from its page moves it there')
check(call('POST', '/api/lights/spots/%d/plants' % bb['id'], {'add': []})[0] == 400 and call('POST', '/api/lights/spots/99999/plants', {'add': ['P-001']})[0] == 404, 'adding needs a plant and a spot that exists')
call('DELETE', '/api/lights/spots/%d' % a['id']); call('DELETE', '/api/lights/spots/%d' % bb['id'])

# ---- 1.13.1: rooms and shelves, the model field, Ethan's answers (batchA4)
st, j7 = call('GET', '/api/lights')
labels = [pl['label'] for pl in j7['places']]
want = ['Downstairs Living Room, Tall Black Shelf', 'Downstairs Living Room, Tall Brown Shelf', 'Downstairs Living Room, Short Brown Shelf', 'Downstairs Living Room, Large Brown Hutch',
        'Downstairs Living Room, Side Table', 'My Bedroom, Shelves', 'Garage', 'Upstairs Living Room']      # 1.29.0: each room can also be chosen itself
check(all(w in labels for w in want), f'his 8 rooms and shelves arrived ({len(labels)} places, with each room itself)')
d7 = {L['key']: L for L in j7['lights']}
check(d7['disk-light']['fixture'].startswith('New, still in its box') and 'E26' in d7['sansi-gooseneck']['notes'], "the disk light and gooseneck carry his answers")
st, rq2 = call('GET', '/api/requests')
done = {r['rkey']: r for r in rq2 if r.get('rkey')}
check(all(done[k]['done'] for k in ('lights-disk', 'lights-spots', 'lights-sockets', 'lights-lamps', 'lights-models', 'lights-model-disk', 'lights-t8-set')), 'answered questions are closed (lamps from batch A6, model numbers from batch B7, the disk light and the T8 strip from batches C2 and C1)')
check(d7['disk-light']['specs']['model'] == 'A01062304A' and d7['disk-light']['specs']['kelvin'] == 5000, "the disk light's card has its model and 5000 K (batch C2)")
check(d7['sansi-80w']['fixture'].startswith('Suggested: the bare socket on the long') and 'clamp-on' in d7['sansi-30w']['fixture'] and 'Five bare sockets are left spare' in d7['sansi-10w']['fixture'],
      'each bulb has a suggested lamp or socket from his answer (batch A6)')
# 1.41.1: a room itself has a negative id; renaming and removing it said "Request failed (405)"
st, rm = call('POST', '/api/lights/places', {'room': 'Test sunroom'})
check(st == 201 and rm['id'] < 0 and call('PUT', '/api/lights/places/%d' % rm['id'], {'room': 'Test sunroom 2'})[0] == 200
      and any(pl['label'] == 'Test sunroom 2' for pl in call('GET', '/api/lights')[1]['places']), 'a room itself can be renamed (negative id)')
check(call('DELETE', '/api/lights/places/%d' % rm['id'])[0] == 200 and not any(pl['id'] == rm['id'] for pl in call('GET', '/api/lights')[1]['places']), 'and removed')
busy = next(pl['id'] for pl in j7['places'] if pl['label'] == 'Downstairs Living Room')
st, e = call('DELETE', '/api/lights/places/%d' % busy)
check(st == 409 and 'Move them' in str(e), f'a room with plants in it says why it cannot go, instead of 405 ({st} {e})')
pid = next(pl['id'] for pl in j7['places'] if pl['label'] == 'Downstairs Living Room, Large Brown Hutch')
st, _ = call('PUT', '/api/lights/spots/%d' % sid, {'name': 'Living room window', 'place': pid, 'light': p0['light_id'], 'units': p0['units'], 'distance': p0['distance_in'], 'hours': p0['hours'], 'dim': p0['dim_pct']})
sp = next(s for s in call('GET', '/api/lights')[1]['spots'] if s['id'] == sid)
check(st == 200 and sp['place'] == 'Downstairs Living Room, Large Brown Hutch', 'a spot can say which room and shelf it is on')
check(call('PUT', '/api/lights/spots/%d' % sid, {'name': 'X', 'place': 99999, 'light': p0['light_id'], 'distance': 12, 'hours': 12})[0] == 400, 'but only one from the list')
st, r = call('POST', '/api/lights/places', {'room': 'My Bedroom', 'name': 'Window shelf'})
check(st == 201 and call('POST', '/api/lights/places', {'room': 'My Bedroom', 'name': 'Window shelf'})[0] == 409, 'a shelf can be added to a room, once')
check(call('POST', '/api/lights/places', {'room': '', 'name': 'x'})[0] == 400, 'a place needs a room')
st, _ = call('PUT', '/api/lights/places/%d' % pid, {'room': 'Downstairs Living Room', 'name': 'Big Brown Hutch'})
check(st == 200 and next(s for s in call('GET', '/api/lights')[1]['spots'] if s['id'] == sid)['place'] == 'Downstairs Living Room, Big Brown Hutch', 'renaming a shelf renames it on its spots')
st, _ = call('DELETE', '/api/lights/places/%d' % r['id'])
check(st == 200, 'an empty shelf can be removed')
st, _ = call('PUT', '/api/lights/%d' % d7['sansi-80w']['id'], {'name': d7['sansi-80w']['name'], 'count': 1, 'model': 'SANSI-80W-TEST', 'fixture': '', 'notes': ''})
check(st == 200 and next(L for L in call('GET', '/api/lights')[1]['lights'] if L['key'] == 'sansi-80w')['specs'].get('model') == 'SANSI-80W-TEST', 'a light keeps its manufacturer model')

# ---- change and add lights
L = by['sansi-10w']
st, _ = call('PUT', '/api/lights/%d' % L['id'], {'name': L['name'], 'count': 6, 'fixture': 'Two 3-socket clamp lamps on the bookshelf', 'notes': ''})
st2, j5 = call('GET', '/api/lights')
L2 = next(x for x in j5['lights'] if x['id'] == L['id'])
check(st == 200 and L2['fixture'].startswith('Two 3-socket') and L2['points'] == L['points'], 'where a light is can be noted, keeping its figures')
st, r = call('POST', '/api/lights', {'name': 'Desk lamp LED', 'count': 1, 'watts': 8, 'points': '12 in 40, 24 in 12 (6 sq ft)', 'dimming': '100'})
check(st == 201, 'a new light can be added')
st, j6 = call('GET', '/api/lights')
nl = next(x for x in j6['lights'] if x['name'] == 'Desk lamp LED')
check([p['distance_in'] for p in nl['points']] == [12, 24] and nl['points'][1]['area_sqft'] == 6, 'with its distances, PAR and area read from plain text')
check(call('POST', '/api/lights', {'name': 'Bad', 'count': 1, 'points': '12 in'})[0] == 400, 'unreadable figures are refused with a message')
check(call('DELETE', '/api/lights/%d' % nl['id'])[0] == 200, 'an unused light can be removed')
st, aud = call('GET', '/api/audit/search?kind=lights')
notes = ' | '.join(e['note'] for e in aud['entries'])
check('Room or shelf renamed' in notes and 'Grow light updated (batchA4)' in notes, 'rooms, shelves and batch updates are in the audit log too')
check('Grow light spot set up: Living room window' in notes and 'Grow light: now in the spot' in notes and 'Grow light changed' in notes and 'Grow light added (batchA3)' in notes, 'everything shows in the audit log under "Grow lights"')

# ---- people who can only view (through Tailscale)
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', base=TS, h=E); call('GET', '/api/me', base=TS, h=V)
check(call('GET', '/api/lights', base=TS, h=V)[0] == 200, 'a viewer can see the Grow lights page')
check(call('POST', '/api/lights/spots', {'name': 'X', 'light': by['sansi-tripod']['id'], 'distance': 20, 'hours': 12}, base=TS, h=V)[0] == 403 and
      call('PUT', '/api/lights/%d' % L['id'], {'name': 'X', 'count': 1}, base=TS, h=V)[0] == 403, 'but cannot set up spots or change lights')
check(call('POST', '/api/lights/spots/plan', {}, base=TS, h=V)[0] == 403 and call('POST', '/api/lights/spots/%d/plants' % sid, {'add': ['P-001']}, base=TS, h=V)[0] == 403
      and call('GET', '/api/lights/best?light=%d&units=1&plants=P-001' % by['sansi-tripod']['id'], base=TS, h=V)[0] == 200, '1.41.0: nor set up the whole layout or add plants (the best setting only reads)')

# ---- the page
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '404' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Light Test')")
    pg.goto(LOCAL + '/#/lights'); pg.wait_for_timeout(2500)
    check(pg.locator('#lt-rooms .lt-room').count() == 5 and 'Big Brown Hutch' in pg.inner_text('#lt-rooms') and 'Living room window' in pg.inner_text('#lt-rooms'), 'the page lists his rooms with the spot on its shelf')
    check('SANSI-80W-TEST' in pg.inner_text('#lt-lights') and pg.locator('#lt-lights .lt-ed:visible').count() == 0, '1.39.1: each light shows its model as text; the edit fields wait behind a button')
    pg.locator('[data-act=ltedit]').first.click(); pg.wait_for_timeout(300)
    check('Manufacturer model' in pg.inner_text('#lt-lights') and pg.locator('#lt-lights [data-k=model]').evaluate_all("els => els.some(e => e.value === 'SANSI-80W-TEST')"), 'each light shows its manufacturer model (1.29.0: in a box you can type in)')
    check(pg.locator('#lt-spots details.lt-spot-fold').count() == 1 and pg.locator('#lt-plan article').count() >= 5 and pg.locator('.lt-light').count() == 11, 'the page shows your spot, the suggestions and your 11 lights')
    check(pg.locator('.lt-light img.lt-photo').count() == 10 and all(pg.locator('.lt-light img.lt-photo').nth(i).get_attribute('alt') for i in range(10)), 'every light photo has a description')
    check(pg.locator('.lv').count() > 10 and pg.locator('.lv span[aria-hidden]').count() == pg.locator('.lv').count(), 'verdicts are words with a symbol, not colour alone')
    pg.screenshot(path=os.path.join(OUT, 'lights-1-page.png'))
    np_ = pg.locator('article.lt-light.no-photo')
    check(np_.count() >= 1 and all(w[1] > 0.8 * w[0] for w in np_.evaluate_all('els => els.map(e => [e.getBoundingClientRect().width, e.querySelector(".lt-body").getBoundingClientRect().width])')),
          '1.41.1: a light with no photo (the disk light) uses the whole card, not the narrow photo column')
    # 1.42.0: the summary table at the top, sticky and folding as one; buttons by their section titles; spots fold; plants two to a row
    jl = call('GET', '/api/lights')[1]; nc = len(jl['candidates']); ni = sum(1 for c in jl['candidates'] if c['inside']); na = len(jl['assigned'])
    cells = [x.strip() for x in pg.locator('table.lt-sum-tbl tbody td').all_inner_texts()]
    heads = [x.strip() for x in pg.locator('table.lt-sum-tbl thead th').all_inner_texts()]
    check(heads == ['Inside', 'Coming in', 'Assigned light spot', 'No assigned light spot', '7-day mol/m² average'] and cells[:4] == [str(ni), str(nc - ni), str(na), str(nc - na)],
          f'the summary table: {dict(zip(heads, cells))}')
    check(pg.locator('text=This winter').count() == 0 and pg.locator('#lt-lights > header [data-act=lightnew]').count() == 1 and pg.locator('#lt-spots > header [data-act=spotnew]').count() == 1,
          '"This winter" is gone; Add a light and Set up a spot sit by their section titles')
    pg.evaluate('window.scrollTo(0, 2500)'); pg.wait_for_timeout(300)
    tp = pg.evaluate("document.getElementById('lt-top').getBoundingClientRect().top")
    check(abs(tp - pg.evaluate("parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--top-h'))")) < 3 and pg.locator('table.lt-sum-tbl').is_visible(), f'the title and table stay at the top as you scroll ({tp:.0f}px)')
    pg.click('[data-act=lttop]'); pg.wait_for_timeout(300)
    check(not pg.locator('table.lt-sum-tbl').is_visible() and pg.locator('#lt-top h1').is_visible() and pg.get_attribute('[data-act=lttop]', 'aria-expanded') == 'false', 'Hide the summary folds it as one, the title stays')
    pg.click('[data-act=lttop]'); pg.wait_for_timeout(300); pg.evaluate('window.scrollTo(0, 0)')
    sf = pg.locator('#lt-spots details.lt-spot-fold').first
    st_ = sf.locator(':scope > summary').inner_text()
    check(not sf.evaluate('d => d.open') and 'Living room window' in st_ and 'Where:' in st_ and 'mol/m² per day' in st_ and 'Plants: ' in st_, f'a spot folds shut showing its name, where, light and plants ({st_!r})')
    sf.locator(':scope > summary').click(); pg.wait_for_timeout(300)
    li = sf.locator('ul.lt-plants li').first
    check(sf.evaluate('d => d.open') and li.locator('.lt-pt > span').nth(0).inner_text().startswith('P-') and 'mol/m² per day' in li.locator('.lt-pt > span').nth(1).inner_text(), 'each plant: its code, then its range per day, on lines of their own')
    cols = pg.evaluate("getComputedStyle(document.querySelector('#lt-spots ul.lt-plants')).gridTemplateColumns.split(' ').length")
    check(cols == 2, f'plants two to a row on a wide screen ({cols})')
    for t_ in ('Your lights', 'Your light spots', 'Rooms and shelves', 'Suggested layout', 'How the numbers work'):
        it = pg.evaluate(f"(() => {{ const it = NAVITEMS.find(x => x.text.startsWith({t_!r})); return it ? !!document.querySelector(`[data-act=secfold][data-for='${{it.id}}']`) : null; }})()")
        check(it is True, f'"{t_}" is in Navigation and has Show or hide')
    # 1.42.0: rooms: New Room and New Shelf open Build-A-Room; removing a shelf keeps the room and your place on the page
    check(pg.locator('#lt-rooms [data-act=roomnew]').inner_text().strip() == 'New Room' and pg.locator('#lt-rooms .lt-room-head [data-act=shelfnew]').count() == pg.locator('#lt-rooms .lt-room').count(), 'New Room, and New Shelf by each room')
    rm = pg.locator('#lt-rooms .lt-room').first; rname = rm.locator('h3').inner_text().strip()
    rm.locator('[data-act=shelfnew]').click(); pg.wait_for_timeout(500)
    check(pg.locator('dialog h2').inner_text().strip() == 'Build-A-Room' and pg.input_value('dialog input[name=room]') == rname and pg.evaluate('document.activeElement.name') == 'name', 'New Shelf opens Build-A-Room for that room, at the shelf box')
    pg.fill('dialog input[name=name]', 'Test shelf only'); pg.click('dialog button[value=ok]'); pg.wait_for_timeout(2000)
    pg.click('[data-act=roomnew]'); pg.wait_for_timeout(500)
    check(pg.locator('dialog h2').inner_text().strip() == 'Build-A-Room', 'New Room opens Build-A-Room')
    pg.fill('dialog input[name=room]', 'Test single-shelf room'); pg.fill('dialog input[name=name]', 'Lone shelf'); pg.click('dialog button[value=ok]'); pg.wait_for_timeout(2000)
    room = pg.locator('#lt-rooms .lt-room', has_text='Test single-shelf room')
    room.scroll_into_view_if_needed(); y0 = pg.evaluate('scrollY')
    room.locator('li [data-act=roomdel]').click(); pg.wait_for_timeout(400)
    check('The room Test single-shelf room stays' in pg.inner_text('dialog'), 'removing a shelf says the room stays')
    pg.locator('dialog .btn').first.click(); pg.wait_for_timeout(2500)
    check(any(p_['room'] == 'Test single-shelf room' for p_ in call('GET', '/api/lights')[1]['places']) and room.count() == 1 and room.locator('li').count() == 0,
          'removing the only shelf keeps the room (it took the room with it)')
    check(abs(pg.evaluate('scrollY') - y0) < 300, f'and the page stays where it was, not back at the top ({y0} then {pg.evaluate("scrollY")})')
    room.locator('[data-act=roomdel]').click(); pg.wait_for_timeout(400)
    check('Remove this room?' in pg.inner_text('dialog'), 'Remove room asks about the room')
    pg.locator('dialog .btn').first.click(); pg.wait_for_timeout(2000)
    check(not any(p_['room'] == 'Test single-shelf room' for p_ in call('GET', '/api/lights')[1]['places']), 'and removes it')
    pg.evaluate('window.scrollTo(0, 0)')
    pg.click('#lt-plan [data-act=spotnew]'); pg.wait_for_timeout(1200)
    check(pg.locator('dialog select[name=place] optgroup').count() == 5, 'the spot window offers the rooms and shelves (and the second home\'s room)')
    t1 = pg.inner_text('#sp-prev')
    pg.fill('dialog input[name=distance]', '40'); pg.wait_for_timeout(900)
    t2 = pg.inner_text('#sp-prev')
    check('mol/m² a day' in t1 and t1 != t2, 'the spot window shows the light at the leaves, and it changes with the distance')
    # 1.41.0: the Light menu, the light's card, and the plant list's search, Show, Sort, links, tags and Best setting
    grow = pg.locator('dialog select[name=light] optgroup[label="Grow lights"] option').all_inner_texts()
    room = pg.locator('dialog select[name=light] optgroup[label="Room lights"] option').all_inner_texts()
    names = [t.split(':')[0] for t in grow]
    nat = lambda t: [int(x) if x.isdigit() else x.lower() for x in __import__('re').split(r'(\d+)', t)]       # A to Z, 2 ft before 10 W
    check(names == sorted(names, key=nat) and len(grow) == 10 and len(room) == 1 and room[0].startswith('Commercial Electric disk light'), 'the Light menu is A to Z, the room light in its own group')
    check(all('free' in t and ('PAR' in t or 'no light figures' in t) for t in grow + room), 'each light in the menu says its most light and how many are free')
    check('Daily light' in pg.inner_text('#sp-light') and 'Light at the leaves' in pg.inner_text('#sp-light'), "the window shows the chosen light's reach")
    pg.select_option('dialog select[name=light]', str(by['sansi-80w']['id'])); pg.wait_for_timeout(900)
    check('SANSI 80 W' in pg.inner_text('#sp-light .sp-light-h') and '25%' in pg.inner_text('#sp-light'), 'choosing another light shows its card')
    rows = pg.locator('ul.sp-plants li.sp-row')
    check(rows.count() == len(j7['candidates']) and pg.locator('ul.sp-plants a[target=_blank][href^="#/plant/"]').count() == rows.count() and pg.locator('ul.sp-plants img').count() > rows.count() / 2,
          'one plant a row, with a photo and a link that opens its page in a new tab')
    pg.fill('dialog [data-sp=q]', 'fern'); pg.press('dialog [data-sp=q]', 'Enter'); pg.wait_for_timeout(400)
    vis = pg.locator('ul.sp-plants li.sp-row:visible')
    check(pg.evaluate('document.querySelector("dialog").open') and vis.count() >= 1 and all('fern' in vis.nth(i).inner_text().lower() for i in range(vis.count())), 'search finds the ferns, and Enter does not save the spot')
    pg.fill('dialog [data-sp=q]', ''); pg.select_option('dialog [data-sp=show]', 'fit'); pg.wait_for_timeout(400)
    vis = pg.locator('ul.sp-plants li.sp-row:visible')
    check(vis.count() >= 1 and vis.count() == pg.locator('ul.sp-plants li.sp-row:visible .lv-good').count(), f'"Fits this setting" shows only plants this light suits ({vis.count()})')
    pg.select_option('dialog [data-sp=show]', ''); pg.select_option('dialog [data-sp=sort]', 'need'); pg.wait_for_timeout(400)
    tg = [float(x) for x in pg.locator('ul.sp-plants li.sp-row').evaluate_all('els => els.map(e => e.dataset.target).filter(Boolean)')]
    check(tg == sorted(tg, reverse=True), 'Sort: most light needed first')
    check('Showing %d of %d' % (rows.count(), rows.count()) in pg.inner_text('#sp-count'), 'it says how many are showing and ticked')
    pg.locator('ul.sp-plants li.sp-row input[name=plant]').nth(0).check(); pg.locator('ul.sp-plants li.sp-row input[name=plant]').nth(1).check(); pg.wait_for_timeout(300)
    pg.click('dialog [data-act=spotbest]'); pg.wait_for_timeout(1500)
    check(pg.inner_text('#sp-best').startswith('Set to') and pg.input_value('dialog input[name=distance]') == pg.inner_text('#sp-best').split(' in ')[0].split()[-1], 'Best setting fills in the distance, hours and brightness and says how many fit')
    pg.screenshot(path=os.path.join(OUT, 'lights-2-window.png'))
    pg.click('dialog button[value=cancel]'); pg.wait_for_timeout(300)
    pg.locator('#lt-spots details.lt-spot-fold').first.evaluate('d => { d.open = true; }'); pg.wait_for_timeout(300)
    pg.click('#lt-spots [data-act=spotadd]'); pg.wait_for_timeout(1200)
    check(pg.locator('dialog [data-sp=show]').input_value() == 'free' and pg.evaluate('document.activeElement.dataset.sp') == 'q', 'Add plants opens the spot with the plants not in a spot yet, at the search box')
    pg.click('dialog button[value=cancel]'); pg.wait_for_timeout(300)
    inspot = next(c for c, sp in call('GET', '/api/lights')[1]['assigned'].items() if sp == sid)
    pg.goto(LOCAL + '/#/plant/' + inspot); pg.wait_for_timeout(2500)
    check('Living room window' in pg.inner_text('#pl-grow'), "the plant page names the plant's light spot")
    free = next(c['code'] for c in call('GET', '/api/lights')[1]['candidates'] if c['code'] not in call('GET', '/api/lights')[1]['assigned'] and c['need'])
    pg.goto(LOCAL + '/#/plant/' + free); pg.wait_for_timeout(2500)
    check(pg.locator('#pl-grow [data-act=grownew]').count() == 1 and pg.locator('#pl-grow [data-act=growadd]').count() == 1, 'a plant not in a spot can be put in one from its page')
    pg.click('#pl-grow [data-act=grownew]'); pg.wait_for_timeout(1500)
    check(pg.evaluate('[...document.querySelectorAll("dialog input[name=plant]:checked")].map(i => i.value)') == [free], '"Set up a new spot for it" starts with that plant ticked')
    pg.click('dialog button[value=cancel]'); pg.wait_for_timeout(300)
    pg.click('#pl-grow [data-act=growadd]'); pg.wait_for_timeout(900)
    check(pg.locator('dialog input[name=spot]').count() >= 1 and pg.locator('dialog .lv').count() == pg.locator('dialog input[name=spot]').count(), '"Add it to one of your spots" lists them with how each suits it')
    pg.click('dialog input[name=spot] >> nth=0'); pg.click('dialog button[value=ok]'); pg.wait_for_timeout(2000)
    check('In the spot' in pg.inner_text('#pl-grow'), 'and adds it')
    dk = b.new_context(viewport={'width': 1280, 'height': 900}, color_scheme='dark').new_page()
    dk.add_init_script("localStorage.setItem('plantdb.display',JSON.stringify({theme:'light'}))"); dk.goto(LOCAL + '/#/lights'); dk.wait_for_timeout(1500)
    check(dk.evaluate('getComputedStyle(document.documentElement).colorScheme') == 'light', 'tick boxes and menus follow the chosen light theme on a computer set to dark (they were dark squares)')
    dk.close()
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Light Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    ph.goto(LOCAL + '/#/lights'); ph.wait_for_timeout(2500)
    check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'on a phone with the largest text there is no sideways scrolling')
    ph.click('[data-act=spotnew] >> nth=0'); ph.wait_for_timeout(1500)
    check(ph.evaluate('(() => { const d = document.querySelector("dialog"); return d.scrollWidth <= d.clientWidth + 1; })()'), 'and none in the spot window')
    ph.screenshot(path=os.path.join(OUT, 'lights-4-phone-window.png'))
    ph.click('dialog button[value=cancel]'); ph.wait_for_timeout(300)
    ph.screenshot(path=os.path.join(OUT, 'lights-3-phone.png'), full_page=False)
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.goto(TS + '/#/lights'); vw.wait_for_timeout(2500)
    check(vw.locator('[data-act=spotnew]:visible, [data-act=lightedit]:visible, [data-act=spotedit]:visible, [data-act=roomnew]:visible, [data-act=roomedit]:visible, [data-act=spotadd]:visible, [data-act=spotplanall]:visible').count() == 0, 'a viewer sees no buttons that make changes')
    # 1.41.0: set up every suggested spot in one go
    pg.goto(LOCAL + '/#/lights'); pg.wait_for_timeout(2500)
    before = call('GET', '/api/lights')[1]; np = len(before['plan'])
    pg.click('[data-act=spotplanall]'); pg.wait_for_timeout(600); pg.locator('dialog .btn').first.click(); pg.wait_for_timeout(3000)
    after = call('GET', '/api/lights')[1]
    check(np >= 2 and len(after['spots']) == len(before['spots']) + np and len(after['plan']) == 0 and all(c in after['assigned'] for s in before['plan'] for c in s['codes']),
          f'"Set up all {np} suggested spots" sets them all up, with their plants')
    check(call('POST', '/api/lights/spots/plan', {})[0] == 400, 'and there is nothing left to set up after')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails))
sys.exit(1 if fails else 0)
