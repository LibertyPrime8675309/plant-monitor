"""Checks sites (1.48.0, PLAN.md step 4b): a home has a country, a units default and seasons; Today, the health walk-through and
Needed from you follow the home in use; a tropical home has no cold-season pages or blocks; an editor can be limited to some homes
and may change plants only there; a person with no units of their own reads in the home's units. Nevada City comes from batch B3.
Start the mock server with a fresh data folder (MOCK_TS=1), then:  python3 dev/test/sites_check.py    Screenshots: dev/tmp/shots/sites-*.png"""
import json, os, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL, editor='Sites Test'):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', **({'X-Editor': editor} if editor else {}), **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan Schmidtke'}
S = {'Tailscale-User-Login': 'sam@example.net', 'Tailscale-User-Name': 'Sam Rivera'}

homes = call('GET', '/api/meta')[1]['homes']
rr = next(h for h in homes if h['is_home']); nc = next(h for h in homes if h['name'].startswith('Nevada'))
check(rr.get('country') == 'US' and rr.get('units') in ('', None) and rr.get('season') == 'temperate', 'the main home starts as US, Fahrenheit, a winter with frost (a first guess from where it is)')
# site settings: owner only
st, _ = call('PUT', f'/api/places/{nc["id"]}', {'country': 'US', 'units': 'metric', 'season': 'tropical'})
check(st == 200 and call('GET', '/api/places')[1] and next(p for p in call('GET', '/api/places')[1] if p['id'] == nc['id'])['season'] == 'tropical', 'the owner sets a home\'s country, units and seasons')
check(call('PUT', f'/api/places/{nc["id"]}', {'season': 'arctic'})[0] == 400 and call('PUT', f'/api/places/{nc["id"]}', {'country': 'USA'})[0] == 400, 'a wrong season or a three-letter country is refused in plain words')
# plants at Nevada City
codes = ['P-003', 'P-008', 'P-042']
for code in codes:
    p = call('GET', f'/api/plants/{code}')[1]
    call('PUT', f'/api/plants/{code}', {'base_version': p['version'], 'fields': {'home_id': nc['id']}})
# the health walk follows the home in use
ck_nc = {x['code'] for x in call('GET', '/api/checkup', h={'X-Place': str(nc['id'])})[1]['plants']}
ck_rr = {x['code'] for x in call('GET', '/api/checkup')[1]['plants']}
check(ck_nc == set(codes) and not (ck_rr & set(codes)) and len(ck_rr) > 20, 'the health walk-through lists only the plants at the home in use')
# units follow the home when a person has none of their own
call('PUT', '/api/me/prefs', {'units': None})
pr = call('GET', '/api/prep', h={'X-Place': str(nc['id'])})[1]
check(any('°C' in st for m in pr['methods'] for st in m['steps']), 'server sentences read in °C at the metric home for someone with no units of their own')
pr = call('GET', '/api/prep')[1]
check(any('°F' in st for m in pr['methods'] for st in m['steps']), 'and in °F at the main home')
# an editor limited to Nevada City
st, me = call('GET', '/api/me', h=E, base=TS, editor=None); check(me.get('role') == 'owner', 'Ethan is the owner through Tailscale')
call('GET', '/api/me', h=S, base=TS, editor='Sam')
st, P = call('PUT', '/api/people', {'login': 'sam@example.net', 'role': 'editor', 'edit_homes': [nc['id']]})
sam = next(p for p in P['people'] if p['login'] == 'sam@example.net')
check(st == 200 and sam['role'] == 'editor' and sam['edit_homes'] == [nc['id']], 'the owner makes Sam an editor at Nevada City only')
st, r = call('POST', '/api/care', {'plant': 'P-003', 'kind': 'water'}, h=S, base=TS, editor='Sam')
check(st == 201, 'Sam waters a plant at Nevada City')
st, r = call('POST', '/api/care', {'plant': 'P-001', 'kind': 'water'}, h=S, base=TS, editor='Sam')
check(st == 403 and 'Nevada City' in json.dumps(r) and 'P-001' in json.dumps(r), 'but not one at Round Rock: refused, saying which homes Sam may change')
p1 = call('GET', '/api/plants/P-001')[1]
st, r = call('PUT', '/api/plants/P-001', {'base_version': p1['version'], 'fields': {'notes': 'Sam was here'}}, h=S, base=TS, editor='Sam')
check(st == 403, 'nor may Sam edit a Round Rock plant\'s page')
st, r = call('POST', '/api/care', {'plants': ['P-003', 'P-001'], 'kind': 'water'}, h=S, base=TS, editor='Sam')
check(st == 403, 'a batch that touches both homes is refused whole')
st, me = call('GET', '/api/me', h=S, base=TS, editor='Sam'); check(me.get('edit_homes') == [nc['id']], '/api/me tells Sam which homes they may change')
st, P = call('PUT', '/api/people', {'login': 'sam@example.net', 'edit_homes': [nc['id'], rr['id']]})
check(next(p for p in P['people'] if p['login'] == 'sam@example.net')['edit_homes'] == [], 'ticking every home means no limit (stored as none)')
st, _ = call('POST', '/api/care', {'plant': 'P-001', 'kind': 'water'}, h=S, base=TS, editor='Sam'); check(st == 201, 'and Sam may water at Round Rock again')
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Sites Test')")
    # Round Rock: cold-season pages present
    pg.goto(LOCAL + '/#/'); pg.wait_for_selector('#today-needs', timeout=15000); pg.wait_for_timeout(1000)
    pg.goto(LOCAL + '/#/fertilizer'); pg.wait_for_selector('#sub-nav a[data-nav=fertilizer]', timeout=15000); pg.wait_for_timeout(400)
    check(pg.locator('#sub-nav a[data-nav=frost]').count() == 1 and pg.locator('#sub-nav a[data-nav=inside]').count() == 1, 'at the main home, Care lists the Cold-night checklist and Coming inside')
    check(pg.locator('#main-nav a[data-sec=care]').get_attribute('href') == '#/winter', 'the Care link opens the Winter plan')
    # Nevada City (tropical, metric): no cold pages, °C, only its plants on Today
    pg.evaluate(f"localStorage.setItem('plantdb.place', '{nc['id']}')"); pg.goto(LOCAL + '/#/'); pg.reload(); pg.wait_for_selector('#today-needs', timeout=15000); pg.wait_for_timeout(1500)
    check('Nevada City' in pg.inner_text('#place-name'), 'the Location button shows Nevada City')
    pg.goto(LOCAL + '/#/fertilizer'); pg.wait_for_selector('#sub-nav a[data-nav=fertilizer]', timeout=15000); pg.wait_for_timeout(400)
    check(pg.locator('#main-nav a[data-sec=care]').get_attribute('href') == '#/turning', 'the Care link opens Turn the pots there, its first page that applies')
    pg.goto(LOCAL + '/#/'); pg.wait_for_selector('#today-needs', timeout=15000); pg.wait_for_timeout(1200)
    pg.goto(LOCAL + '/#/fertilizer'); pg.wait_for_selector('#sub-nav a[data-nav=fertilizer]', timeout=15000); pg.wait_for_timeout(400)
    check(pg.locator('#sub-nav a[data-nav=frost]').count() == 0 and pg.locator('#sub-nav a[data-nav=inside]').count() == 0 and pg.locator('#sub-nav a[data-nav=fertilizer]').count() == 1,
          'at a tropical home, Care has no Winter plan, Cold-night checklist, Coming inside or Back outside, but keeps Fertilizer')
    pg.goto(LOCAL + '/#/'); pg.wait_for_selector('#today-needs', timeout=15000); pg.wait_for_timeout(1500)
    check(pg.locator('#today-cold, #today-inside, #fd-today, #bo-today, .fz-banner').count() == 0, 'Today has no cold blocks or frost banner there')
    water_codes = pg.evaluate("[...document.querySelectorAll('#today-water .job, #today-unlogged .job')].map(e => e.dataset.code)")   # 1.57.0: and the plants with no watering logged
    check(all(c in codes for c in water_codes), 'Today\'s water list has only Nevada City plants')
    needs = pg.inner_text('#today-needs')
    check('P-001' not in needs, 'Needed from you shows no Round Rock plant')
    pg.goto(LOCAL + '/#/plant/P-003'); pg.wait_for_selector('.verdicts', timeout=15000); pg.wait_for_timeout(800)
    t = pg.inner_text('main'); check('°C' in t and '°F' not in t.replace('(F)', ''), 'a plant page reads in °C at the metric home with no units of your own')
    pg.screenshot(path=os.path.join(OUT, 'sites-1-nevada-today.png'))
    # Display says it is following the home
    pg.click('#display-btn'); pg.wait_for_selector('#pref-u-region')
    check('Following the home you are looking at' in pg.inner_text('dialog.dv'), 'Display, Units says it follows the home until you choose')
    pg.select_option('#pref-u-region', 'us'); pg.wait_for_timeout(1200); pg.locator('dialog.dv .dv-acts button[value=ok]').click(); pg.wait_for_timeout(800)
    t = pg.inner_text('main'); check('°F' in t, 'choosing United States yourself wins over the home\'s metric default')
    pg.evaluate("localStorage.removeItem('plantdb.units')"); call('PUT', '/api/me/prefs', {'units': None})
    # Homes and places: the site settings
    pg.evaluate("localStorage.removeItem('plantdb.place')"); pg.goto(LOCAL + '/#/weather?sec=places'); pg.reload(); pg.wait_for_selector('.site-set', timeout=15000)
    check(pg.locator('.site-set').count() == 2, 'Homes and places has site settings for each home')
    sel = pg.locator(f'select[data-act=placesite][data-id="{nc["id"]}"][data-k=season]')
    check(sel.input_value() == 'tropical', 'Nevada City shows its seasons')
    sel.select_option('temperate'); pg.wait_for_timeout(1500)
    check(next(p for p in call('GET', '/api/places')[1] if p['id'] == nc['id'])['season'] == 'temperate', 'changing the seasons saves')
    pg.screenshot(path=os.path.join(OUT, 'sites-2-places.png'))
    # the people list, as the owner through Tailscale
    pg2 = br.new_context(extra_http_headers=E).new_page(); pg2.on('pageerror', lambda e: errs.append(str(e)))
    pg2.goto(TS + '/#/'); pg2.wait_for_selector('button.who', timeout=15000); pg2.wait_for_timeout(800)
    pg2.locator('button.who').click(); pg2.wait_for_selector('.people', timeout=15000)
    sam_box = pg2.locator('.people li', has_text='Sam Rivera')
    check(sam_box.locator('.p-homes input').count() == 2 and sam_box.locator('.p-homes input:checked').count() == 2, 'an editor\'s row lists the homes, all ticked when there is no limit')
    sam_box.locator(f'.p-homes input[value="{rr["id"]}"]').uncheck(); pg2.wait_for_timeout(1500)
    st, P = call('GET', '/api/people')
    check(next(p for p in P['people'] if p['login'] == 'sam@example.net')['edit_homes'] == [nc['id']], 'unticking a home limits the editor to the others')
    pg2.screenshot(path=os.path.join(OUT, 'sites-3-people.png'))
    br.close()
check(not errs, 'no page errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print(f'\n{len(fails)} FAIL' + (': ' + '; '.join(fails) if fails else ''))
sys.exit(1 if fails else 0)
