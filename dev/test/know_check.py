"""Checks 1.23.0: the library part 2. Lists about the area fetched in the background from iNaturalist (native and introduced to Texas,
recorded wild near home, flowering and fungi this month) and the ASPCA's pet lists (stand-ins in dev/test/mock_vision.py); the Texas
invasive list; the "Texas and home" filter and card tags; species pages with Here at home, Pets and a care sheet from Claude; and the
Around home page. Start the mock server with a fresh data folder (MOCK_TS=1), then:
python3 dev/test/know_check.py      Screenshots: dev/tmp/shots/know-*.png"""
import json, os, sys, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Know Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)

st, d = call('GET', '/api/library/local')
check(st == 200 and len(d['lists']) == 6, 'six lists about the area, fetched in the background when first asked for')
for _ in range(40):
    time.sleep(1); d = call('GET', '/api/library/local')[1]
    if not d['now'] and not d['queued']: break
by = {l['name']: l for l in d['lists']}
check(by['native-18']['count'] == 17 and by['introduced-18']['count'] == 3 and by['near-1']['count'] == 5 and by['aspca']['count'] == 6, f'they are all fetched ({", ".join(f"{k} {v["count"]}" for k, v in by.items())})')
check(not any(l['error'] for l in d['lists']), 'without errors')
calls = json.loads(urllib.request.urlopen('http://127.0.0.1:8090/mock/inat/calls').read())
sc = [c for c in calls if c.startswith('species_counts')]
check(any('lat=30.5083' in c and 'radius=50' in c and 'captive=false' in c for c in sc), 'near home means recorded wild (not captive) within 50 km of the home place')
check(call('POST', '/api/library/local', {}, V, TS)[0] == 403, 'someone who can only view cannot fetch them again')
r = call('GET', '/api/library/browse?scope=world&know=invasive')[1]
check([x['scientific_name'] for x in r['results']] == ['Melia azedarach'] and r['results'][0]['know']['invasive'] == 'chinaberry', 'the Texas invasive list is built in')
r = call('GET', '/api/library/browse?scope=world&know=petsafe')[1]
check({x['scientific_name'] for x in r['results']} == {'Lupinus texensis', 'Testia species01'}, 'Safe for dogs and cats, from the ASPCA lists')
st, r = call('POST', '/api/library/care', {'name': 'Lupinus texensis'})
check(st == 400, 'without a Claude key a care sheet says what is needed')
call('PUT', '/api/identify/settings', {'claude_key': 'test-key-123'})

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '404' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Know Test')")
    pg.goto(LOCAL + '/#/today'); pg.wait_for_timeout(1000); pg.evaluate("localStorage.removeItem('plantdb.library')")
    pg.goto(LOCAL + '/#/library'); pg.wait_for_timeout(3000)
    t = pg.inner_text('#lib-lists')
    check('Plants native to Texas: 17 species' in t and 'ASPCA' in t and 'zone' in t.lower(), 'the Library page lists the lists, how many species and when they were fetched')
    pg.select_option('select[data-f=libknow]', 'native'); pg.wait_for_timeout(1500)
    check(pg.locator('#lib-res .lib-card').count() == 17 and 'Native to Texas' in pg.inner_text('#lib-res'), '"Your area: Native to Texas" filters the library, and the cards say so')
    pg.select_option('select[data-f=libknow]', 'bloom'); pg.wait_for_timeout(1500)
    check(pg.locator('#lib-res .lib-card').count() == 2 and 'Flowering near home now' in pg.inner_text('#lib-res'), 'Flowering near home this month')
    pg.select_option('select[data-f=libknow]', 'pettoxic'); pg.wait_for_timeout(1500)
    check(pg.locator('#lib-res .lib-card').count() == 3 and '⚠ Toxic to dogs and cats' in pg.inner_text('#lib-res'), 'Toxic to dogs or cats, with a warning tag in words')
    pg.click('#lib-clear'); pg.wait_for_timeout(2000)
    # a species page
    pg.goto(LOCAL + '/#/species/Melia%20azedarach'); pg.wait_for_timeout(3000)
    t = pg.inner_text('main')
    check('On the Texas noxious and invasive plant list' in t and 'introduced (not native)' in t and 'recorded growing wild 40 times within 31 miles' in t, 'Here at home: invasive, introduced, recorded nearby')
    check('Likely.' in t and 'grows wild within 31 miles' in t, 'Will it survive outside here: likely, because it grows wild nearby')
    check(pg.locator('.sp-pets tbody tr').count() == 3 and '⚠ Toxic' in pg.inner_text('.sp-pets'), 'Pets: the ASPCA answer for dogs, cats and horses, in words')
    pg.goto(LOCAL + '/#/species/Testia%20species05'); pg.wait_for_timeout(2500)
    t = pg.inner_text('main')
    check('Not known yet.' in t and 'Not on the ASPCA' in t and 'does not mean it is safe' in t, 'when nothing is known it says so, and never calls it safe')
    pg.click('[data-act=spcare]'); pg.wait_for_selector('#sp-care dl', timeout=15000)
    t = pg.inner_text('#sp-care')
    check('Written by Claude, not checked by a person' in t and 'Full sun' in t and 'zones 7a to 10b' in t, 'Write a care sheet with Claude: kept, marked as not checked, with its zones')
    t = pg.inner_text('main')
    pg.reload(); pg.wait_for_timeout(2500)
    check('Likely.' in pg.inner_text('main') and 'yours is' in pg.inner_text('main'), 'and the zones answer "Will it survive outside here?"')
    pg.screenshot(path=os.path.join(OUT, 'know-1-species.png'), full_page=True)
    # around home
    pg.goto(LOCAL + '/#/library'); pg.wait_for_timeout(2000)
    pg.click('a[href="#/around"]'); pg.wait_for_timeout(2500)
    t = pg.inner_text('main')
    check(pg.evaluate('location.hash') == '#/around' and 'Flowering near' in t and 'Mushrooms and other fungi found near' in t and 'Recorded wild most often' in t, 'Around home has its three sections')
    check(pg.locator('#ar-bloom').count() == 1 and pg.locator('section:has(#ar-near) .lib-card').count() == 5 and '120 records near home' in t, 'with cards for each species and how often it was recorded')
    check('Never eat a wild mushroom' in t, 'and the mushroom safety note')
    pg.screenshot(path=os.path.join(OUT, 'know-2-around.png'), full_page=True)
    pg.locator('section:has(#ar-bloom) a:has-text("See them all in the library")').click(); pg.wait_for_timeout(2500)
    check(pg.locator('select[data-f=libknow]').input_value() == 'bloom' and pg.locator('#lib-res .lib-card').count() == 2, '"See them all in the library" opens the library with that filter')
    # viewer and phone
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.on('pageerror', lambda e: errs.append(str(e)))
    vw.goto(TS + '/#/species/Testia%20species05'); vw.wait_for_timeout(2500)
    check('Full sun' in vw.inner_text('main') and vw.locator('[data-act=spcare]').count() == 0, 'a viewer reads the care sheet but cannot ask for one')
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Know Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    for u in ('/#/around', '/#/species/Melia%20azedarach', '/#/library'):
        ph.goto(LOCAL + u); ph.wait_for_timeout(2500)
        check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'{u}: no sideways scrolling on a phone with the largest text')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
