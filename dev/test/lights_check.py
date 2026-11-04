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
check(all(done[k]['done'] for k in ('lights-disk', 'lights-spots', 'lights-sockets', 'lights-lamps')) and not done['lights-models']['done'], 'answered questions are closed (lamps from batch A6), the model numbers are still open')
check(d7['sansi-80w']['fixture'].startswith('Suggested: the bare socket on the long') and 'clamp-on' in d7['sansi-30w']['fixture'] and 'Five bare sockets are left spare' in d7['sansi-10w']['fixture'],
      'each bulb has a suggested lamp or socket from his answer (batch A6)')
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

# ---- the page
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '404' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Light Test')")
    pg.goto(LOCAL + '/#/lights'); pg.wait_for_timeout(2500)
    check(pg.locator('#lt-rooms .lt-room').count() == 5 and 'Big Brown Hutch' in pg.inner_text('#lt-rooms') and 'Living room window' in pg.inner_text('#lt-rooms'), 'the page lists his rooms with the spot on its shelf')
    check('Manufacturer model' in pg.inner_text('#lt-lights') and pg.locator('#lt-lights [data-k=model]').evaluate_all("els => els.some(e => e.value === 'SANSI-80W-TEST')"), 'each light shows its manufacturer model (1.29.0: in a box you can type in)')
    check(pg.locator('#lt-spots article').count() == 1 and pg.locator('#lt-plan article').count() >= 5 and pg.locator('.lt-light').count() == 11, 'the page shows your spot, the suggestions and your 11 lights')
    check(pg.locator('.lt-light img.lt-photo').count() == 10 and all(pg.locator('.lt-light img.lt-photo').nth(i).get_attribute('alt') for i in range(10)), 'every light photo has a description')
    check(pg.locator('.lv').count() > 10 and pg.locator('.lv span[aria-hidden]').count() == pg.locator('.lv').count(), 'verdicts are words with a symbol, not colour alone')
    pg.screenshot(path=os.path.join(OUT, 'lights-1-page.png'))
    pg.click('#lt-plan [data-act=spotnew]'); pg.wait_for_timeout(1200)
    check(pg.locator('dialog select[name=place] optgroup').count() == 5, 'the spot window offers the rooms and shelves (and the second home\'s room)')
    t1 = pg.inner_text('#sp-prev')
    pg.fill('dialog input[name=distance]', '40'); pg.wait_for_timeout(900)
    t2 = pg.inner_text('#sp-prev')
    check('mol/m² a day' in t1 and t1 != t2, 'the spot window shows the light at the leaves, and it changes with the distance')
    pg.screenshot(path=os.path.join(OUT, 'lights-2-window.png'))
    pg.click('dialog button[value=cancel]'); pg.wait_for_timeout(300)
    inspot = next(c for c, sp in call('GET', '/api/lights')[1]['assigned'].items() if sp == sid)
    pg.goto(LOCAL + '/#/plant/' + inspot); pg.wait_for_timeout(2500)
    check('Living room window' in pg.inner_text('#pl-grow'), "the plant page names the plant's light spot")
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Light Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    ph.goto(LOCAL + '/#/lights'); ph.wait_for_timeout(2500)
    check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'on a phone with the largest text there is no sideways scrolling')
    ph.screenshot(path=os.path.join(OUT, 'lights-3-phone.png'), full_page=False)
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.goto(TS + '/#/lights'); vw.wait_for_timeout(2500)
    check(vw.locator('[data-act=spotnew]:visible, [data-act=lightedit]:visible, [data-act=spotedit]:visible, [data-act=roomnew]:visible, [data-act=roomedit]:visible').count() == 0, 'a viewer sees no buttons that make changes')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails))
sys.exit(1 if fails else 0)
