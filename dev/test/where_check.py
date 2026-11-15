"""Checks 1.29.0: where a plant is. Each home has areas outside and rooms inside (the main home's rooms come from the Grow lights
page's Rooms and shelves, whose shelves become spots), every plant gets the area matching its old Location, an area's "roof
overhead" or "heated" sets the Location frost warnings use, spots can be made from the words written on plants, and the lists can
be renamed on the page. Start the mock server with a fresh data folder (MOCK_TS=1), then:
python3 dev/test/where_check.py      Screenshots: dev/tmp/shots/where-*.png"""
import json, os, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Where Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)
plant = lambda c: call('GET', '/api/plants/' + c)[1]

W = call('GET', '/api/where')[1]['homes']
main = W[0]; areas = {(a['side'], a['name']): a for a in main['areas']}
check(('out', 'Yard') in areas and ('out', 'Covered porch') in areas and areas[('out', 'Covered porch')]['sheltered'], 'the main home has a yard and a covered porch outside')
check(('in', 'Downstairs Living Room') in areas and ('in', 'Garage') in areas and not areas[('in', 'Garage')]['sheltered'],
      'its rooms come from Rooms and shelves, and the garage counts as not heated')
dl = areas[('in', 'Downstairs Living Room')]
check({'Tall Black Shelf', 'Large Brown Hutch'} <= {s['name'] for s in dl['spots']}, 'the shelves became spots in their room')
nc = [h for h in W[1:] if 'Nevada City' in h['home']['name']]       # batch C9 adds Baraboo as a third home
check(len(W) == 3 and nc and any(a['name'] == 'Yard' for a in nc[0]['areas']), 'Nevada City has its own areas')
allp = call('GET', '/api/plants?status=all')[1]
check(all(p.get('code') for p in allp), 'plants still load')
pp = [plant(p['code']) for p in allp[:40]]
check(all(x['area_id'] for x in pp), 'every plant has an area')
check(all((x['site'] == 'Covered porch') == (x['area_id'] == areas[('out', 'Covered porch')]['id']) for x in pp if x['home_id'] is None),
      'plants on the covered porch are in the Covered porch area, and only they are')
lights = call('GET', '/api/lights')[1]
check(any(p['label'] == 'Downstairs Living Room, Tall Black Shelf' for p in lights['places']), 'grow light spots choose from the same rooms and spots')

# moving a plant
p14 = plant('P-014'); pid = areas[('in', 'Downstairs Living Room')]['id']; shelf = [s for s in dl['spots'] if s['name'] == 'Tall Black Shelf'][0]['id']
st, r = call('PUT', '/api/plants/P-014', {'base_version': p14['version'], 'fields': {'spot_id': shelf}})
check(st == 200 and r['area_id'] == pid and r['site'] == 'Indoors', 'choosing a spot puts the plant in its room, and its Location follows (Indoors)')
st, r = call('POST', '/api/plants/P-014/site', {'site': 'Covered porch'})
check(st == 200 and r['area_id'] == areas[('out', 'Covered porch')]['id'] and r['spot_id'] is None, 'the old Location buttons still work, and move the area too')
# an area changes from open to sheltered
st, r = call('POST', '/api/where/areas', {'home_id': None, 'side': 'out', 'name': 'Patio', 'sheltered': False})
patio = r['id']
p22 = plant('P-022'); call('PUT', '/api/plants/P-022', {'base_version': p22['version'], 'fields': {'area_id': patio}})
check(plant('P-022')['site'] == 'Outdoors', 'a plant on the open patio counts as Outdoors')
call('PUT', f'/api/where/areas/{patio}', {'sheltered': True})
check(plant('P-022')['site'] == 'Covered porch', 'when the patio gets a roof, its plants count as on a covered porch')
check(call('DELETE', f'/api/where/areas/{patio}')[0] == 409, 'an area with plants in it cannot be removed')
check(call('POST', '/api/where/areas', {'side': 'in', 'name': 'Dining room'}, h=V, base=TS)[0] == 403, 'someone who can only view cannot change the lists')
# spots from the words on the plants
S = call('GET', '/api/where/sort')[1]['items']
check(len(S) > 5 and all(x['name'] for x in S[:5]), f'spots to sort out: {len(S)} written places, each with a suggested spot name')
first = S[0]
st, r = call('POST', '/api/where/sort', {'items': [{'text': first['text'], 'area_id': first['area_id'], 'name': first['name']}]})
check(st == 200 and r['moved'] == len(first['plants']), f'making a spot puts those plants in it ({r.get("moved")})')
check(plant(first['plants'][0]['code'])['location'] == first['text'], 'and the words on the plant stay')
# 1.56.3 (Ethan, November 10): putting plants in a spot that is already there, in another area, used to move nothing
S = call('GET', '/api/where/sort')[1]['items']
grp = next(x for x in S if x['area_id'] != dl['id'])
hutch = next(sp for sp in dl['spots'] if sp['name'] == 'Large Brown Hutch')
keep = grp['plants'][1:] if len(grp['plants']) > 1 else []
st, r = call('POST', '/api/where/sort', {'items': [{'text': grp['text'], 'from_area_id': grp['area_id'], 'area_id': dl['id'], 'spot_id': hutch['id'], 'codes': [grp['plants'][0]['code']]}]})
P0 = plant(grp['plants'][0]['code'])
check(st == 200 and r['moved'] == 1 and P0['spot_id'] == hutch['id'] and P0['area_id'] == dl['id'] and r['made'] == [],
      f'a plant goes to a spot already there in another room, with no new spot made ({r.get("moved")}, {r.get("made")})')
check(all(plant(x['code'])['spot_id'] is None for x in keep), 'an unticked plant of the same group stays for later')
st, r = call('POST', '/api/where/sort', {'items': [{'text': grp['text'], 'from_area_id': grp['area_id'], 'area_id': dl['id'], 'name': 'large brown hutch', 'codes': [x['code'] for x in keep]}]})
check(st == 200 and r['made'] == [] and all(plant(x['code'])['spot_id'] == hutch['id'] for x in keep), 'typing the name of a spot already there, in any case, uses it')
S2 = call('GET', '/api/where/sort')[1]['items']
check(not any(x['text'] == grp['text'] and x['area_id'] == grp['area_id'] for x in S2), 'and the group is gone from the list')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1920, 'height': 1080}, extra_http_headers=E)
    ctx.add_init_script("localStorage.setItem('plantdb.editor','Ethan')")
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(TS + '/#/where'); pg.wait_for_timeout(3000)
    check(pg.locator('#sub-nav a[data-nav=where][aria-current=page]').count() == 1, 'Rooms and spots is a page under Plants')
    nm = pg.locator(f'[data-ed=area][data-id="{pid}"][data-k=name]')
    nm.fill('Living room downstairs'); nm.press('Tab'); pg.wait_for_timeout(1200)
    W2 = call('GET', '/api/where')[1]['homes'][0]
    check(any(a['name'] == 'Living room downstairs' for a in W2['areas']), 'renaming a room by typing over it saves when you leave the box')
    check(pg.locator('.undo-toast').count() == 1, 'and the message has Undo')
    pg.locator('.undo-toast [data-undo=undo]').click(); pg.wait_for_timeout(1500)
    check(any(a['name'] == 'Downstairs Living Room' for a in call('GET', '/api/where')[1]['homes'][0]['areas']), 'Undo puts the old name back')
    pg.screenshot(path=os.path.join(OUT, 'where-1-page.png'), full_page=True)
    # 1.56.3: Plants without a spot, from the page
    check(pg.locator('#wh-sort h2').inner_text().startswith('Plants without a spot ('), 'the section is "Plants without a spot"')
    card = pg.locator('#whs-0')
    codes0 = card.locator('[data-k=code]').evaluate_all('els => els.map(e => e.value)')
    card.locator('[data-k=area]').select_option(str(dl['id'])); pg.wait_for_timeout(300)
    names = card.locator('[data-k=spot] option').all_inner_texts()
    check('Tall Black Shelf' in names and names[-1] == 'A new spot…', f'choosing a room offers its spots and a new one ({len(names)})')
    card.locator('[data-k=spot]').select_option(label='Tall Black Shelf'); pg.wait_for_timeout(200)
    check(card.locator('[data-whsnew]').is_hidden(), 'the new spot name box only shows for a new spot')
    # 1.58.0 (Ethan, November 12): choices made in other groups survive Put in this spot
    others = pg.evaluate("WHSORT.slice(1, 3).map(it => whsKey(it))")
    for j in (1, 2):
        if pg.locator(f'#whs-{j}').count():
            o = pg.locator(f'#whs-{j}')
            o.locator('[data-k=area]').select_option(str(dl['id'])); pg.wait_for_timeout(200)
            o.locator('[data-k=spot]').select_option('new'); pg.wait_for_timeout(100)
            o.locator('[data-k=name]').fill(f'Kept choice {j}')
            if o.locator('[data-k=code]').count() > 1: o.locator('[data-k=code]').first.uncheck()
    card.locator('[data-act=whsone]').click(); pg.wait_for_timeout(2000)
    after = pg.evaluate("""keys => keys.map(k => { const i = WHSORT.findIndex(it => whsKey(it) === k); if (i < 0) return null;
      const q = n => document.querySelector(`[data-whs="${i}"][data-k=${n}]`);
      return { area: q('area').value, spot: q('spot').value, name: q('name').value, shown: !document.querySelector(`[data-whsnew="${i}"]`).hidden,
               off: document.querySelectorAll(`[data-whs="${i}"][data-k=code]:not(:checked)`).length, many: document.querySelectorAll(`[data-whs="${i}"][data-k=code]`).length }; })""", others)
    kept = [a for a in after if a]
    check(len(kept) >= 1 and all(a['area'] == str(dl['id']) and a['spot'] == 'new' and a['name'].startswith('Kept choice') and a['shown'] and (a['off'] == 1 or a['many'] == 1) for a in kept),
          f'after Put in this spot, the area, new spot name and ticks chosen in the other groups are still there ({len(kept)} groups: {kept})')
    pg.screenshot(path=os.path.join(OUT, 'where-3-kept.png'), full_page=False)
    tbs = next(sp for sp in dl['spots'] if sp['name'] == 'Tall Black Shelf')
    check(all(plant(c)['spot_id'] == tbs['id'] for c in codes0), f'Put in this spot puts its plants on the Tall Black Shelf ({len(codes0)})')
    check('put in Tall Black Shelf' in pg.inner_text('#toasts'), 'and says so')
    pg.screenshot(path=os.path.join(OUT, 'where-2-without-spot.png'), full_page=False)
    pg.goto(TS + '/#/plant/P-030/edit'); pg.wait_for_timeout(2500)
    f = pg.locator('form[data-form=edit]')
    f.locator('[name=__side][value=in]').check(); pg.wait_for_timeout(300)
    opts = f.locator('select[name=area_id] option').all_inner_texts()
    check(any('Garage' in o for o in opts) and not any('Yard' in o for o in opts), 'on a plant, choosing Inside lists only the rooms')
    f.locator('select[name=area_id]').select_option(str(pid)); pg.wait_for_timeout(300)
    check(any('Tall Black Shelf' in o for o in f.locator('select[name=spot_id] option').all_inner_texts()), 'and choosing a room lists its spots')
    f.locator('select[name=spot_id]').select_option(str(shelf))
    f.locator('button[type=submit]').click(); pg.wait_for_timeout(2500)
    r = plant('P-030')
    check(r['area_id'] == pid and r['spot_id'] == shelf and r['site'] == 'Indoors', 'saving the plant keeps its room and spot, and it counts as Indoors')
    check('Inside, Downstairs Living Room, Tall Black Shelf' in pg.locator('#app').inner_text() or pg.locator('[data-ed=plant][data-k=spot_id]').count() == 1, 'the plant page shows where it is')
    ph = b.new_context(viewport={'width': 384, 'height': 740}, is_mobile=True, has_touch=True, service_workers='block', extra_http_headers=E)
    ph.add_init_script("localStorage.setItem('plantdb.editor','Ethan');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    q = ph.new_page(); q.on('pageerror', lambda e: errs.append(str(e)))
    q.goto(TS + '/#/where'); q.wait_for_timeout(3000)
    check(not q.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'on a phone with the largest text nothing scrolls sideways')
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All where checks passed' if not fails else f'{len(fails)} where check(s) failed'))
raise SystemExit(1 if fails else 0)
