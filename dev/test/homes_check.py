"""Checks 1.28.0: homes. Batch B3 adds Nevada City as a second home; a plant can be moved there; the Plants page has a Home
filter and each card says its home; frost, watering and Back outside for a home list only its plants; a home with plants
cannot be removed or turned back into a weather-only place. Start the mock server with a fresh data folder, then:
python3 dev/test/homes_check.py      Screenshots: dev/tmp/shots/homes-*.png"""
import json, os, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None):
    req = urllib.request.Request(LOCAL + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Homes Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}

homes = call('GET', '/api/meta')[1]['homes']
check([h['name'] for h in homes] == ['Round Rock, TX', 'Nevada City, CA'], 'batch B3 adds Nevada City as a second home')
nc = [h for h in homes if h['name'].startswith('Nevada')][0]['id']
rr = [h for h in homes if h['is_home']][0]['id']
moved = []
for code in ('P-003', 'P-008', 'P-042'):
    p = call('GET', f'/api/plants/{code}')[1]
    st, _ = call('PUT', f'/api/plants/{code}', {'base_version': p['version'], 'fields': {'home_id': nc}})
    moved.append(st)
check(moved == [200, 200, 200], 'plants can be moved to the second home')
p = call('GET', '/api/plants/P-003')[1]
check(p['home_id'] == nc, 'the plant keeps its new home')
st, _ = call('PUT', '/api/plants/P-014', {'base_version': call('GET', '/api/plants/P-014')[1]['version'], 'fields': {'home_id': 999}})
check(st == 400, 'a home that does not exist is refused')
st, _ = call('PUT', '/api/plants/P-022', {'base_version': call('GET', '/api/plants/P-022')[1]['version'], 'fields': {'home_id': rr}})
check(st == 200 and call('GET', '/api/plants/P-022')[1]['home_id'] is None, 'choosing the main home stores it as the main home (empty)')
lst = call('GET', '/api/plants')[1]
check(sum(1 for x in lst if x.get('home_id') == nc) == 3, 'the plant list carries each home')

w_rr = {x['code'] for x in call('GET', '/api/water')[1]['plants']}
w_nc = {x['code'] for x in call('GET', '/api/water', h={'X-Place': str(nc)})[1]['plants']}
check(w_nc == {'P-003', 'P-008', 'P-042'} and not (w_rr & w_nc), 'watering for each home lists only its own plants')
f_nc = call('GET', '/api/frost', h={'X-Place': str(nc)})[1]
check(f_nc['place'] == 'Nevada City, CA' and f_nc['outdoor'] <= 3, 'frost warnings for the second home look only at its plants')
check(call('DELETE', f'/api/places/{nc}')[0] == 409, 'a home with plants in it cannot be removed')
check(call('PUT', f'/api/places/{nc}', {'plants_here': False})[0] == 409, 'or turned into a weather-only place while plants live there')
pl = {x['id']: x for x in call('GET', '/api/places')[1]}
check(pl[nc]['plant_count'] == 3 and pl[nc]['plants_here'], 'the places table counts the plants at each home')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1920, 'height': 1080})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Homes Test');localStorage.removeItem('plantdb.filters')")
    pg.goto(LOCAL + '/#/plants'); pg.wait_for_timeout(3000)
    sel = pg.locator('select[data-f=home]')
    check(sel.count() == 1, 'the Plants page has a Home filter')
    sel.select_option(str(nc)); pg.wait_for_timeout(800)
    n = pg.locator('#grid .sheet').count()
    check(n == 3, f'choosing Nevada City shows its 3 plants (showed {n})')
    check(pg.locator('#grid .sheet .tag-homeat').first.inner_text().strip().endswith('Nevada City, CA'), 'each card says which home it is at')
    pg.screenshot(path=os.path.join(OUT, 'homes-1-plants.png'))
    sel.select_option(''); pg.wait_for_timeout(500)
    pg.goto(LOCAL + '/#/plant/P-003/edit'); pg.wait_for_timeout(2500)
    hs = pg.locator('select[name=home_id]')
    check(hs.count() == 1 and hs.input_value() == str(nc), 'the edit form has Home, set to its home')
    pg.goto(LOCAL + '/#/plant/P-003'); pg.wait_for_timeout(2500)
    check('Nevada City, CA' in pg.locator('#app').inner_text(), 'the plant page says its home')
    pg.goto(LOCAL + '/#/weather'); pg.wait_for_timeout(3000)
    t = pg.locator('#app').inner_text()
    check('Plants live here: 3' in t and 'Main home' in t, 'the places table shows each home and its plant count')
    pg.screenshot(path=os.path.join(OUT, 'homes-2-places.png'), full_page=True)
    ph = b.new_context(viewport={'width': 384, 'height': 740}, is_mobile=True, has_touch=True, service_workers='block')
    ph.add_init_script("localStorage.setItem('plantdb.editor','Homes Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    q = ph.new_page(); q.on('pageerror', lambda e: errs.append(str(e)))
    q.goto(LOCAL + '/#/plants'); q.wait_for_timeout(3000)
    check(not q.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'on a phone with the largest text nothing scrolls sideways')
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All homes checks passed' if not fails else f'{len(fails)} homes check(s) failed'))
raise SystemExit(1 if fails else 0)
