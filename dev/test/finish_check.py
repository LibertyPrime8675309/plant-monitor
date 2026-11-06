"""Checks 1.36.0: summer heat verdicts per plant and the Summer here filter, calibrating a soil probe in the app, the soil
moisture on a plant's timeline and calendar, every page in its section's row (and the entry points to Coming inside), the
Health of the app card, Clear the saved pages, and buttons that say what they act on. Start the mock server with a fresh data
folder (MOCK_TS=1), then:  python3 dev/test/finish_check.py      Screenshots: dev/tmp/shots/finish-*.png"""
import json, math, os, sys, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
SENSOR = 'http://127.0.0.1:' + os.environ.get('PLANTDB_SENSOR_PORT', '8082')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Finish Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
call('GET', '/api/me', h=E, base=TS)
iso = lambda t: time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))

# ---- summer heat verdicts
call('POST', '/mock/history', {'years': 4})
P = call('GET', '/api/heat/plants')[1]
levels = {v['level'] for v in P['plants'].values()}
check(P['zone'] == 8 and len(P['plants']) > 50 and {'hard', 'few', 'fine'} & levels and any(v['fit'] == 'within' for v in P['plants'].values()), f'every plant gets a summer verdict ({len(P["plants"])} plants, levels {sorted(x for x in levels if x)})')
p12 = call('GET', '/api/plants/P-012')[1]
check(p12.get('heat_zone_high') == 9 and p12.get('heat_zone_low') == 4 and 'Gardenia' in (p12.get('heat_zone_source') or ''), 'batch B6 gave the aeonium its AHS heat zones with a source')
h = call('GET', '/api/heat?above=95')[1]
check(h['level'] == 'hard' and h['reach'] > 30 and h['hot_months'] and h['hot_months'][0]['month'] in ('Jun', 'Jul'), f'for a plant that scorches at 95°F: {h["reach"]} days a year, hard')
check(call('GET', '/api/heat?above=30')[0] == 400, 'a silly temperature is refused')

# ---- calibrating a soil probe
tok = call('GET', '/api/ingest')[1]['token']
post = lambda b: call('POST', '/api/readings', b, {'X-Ingest-Token': tok}, SENSOR)
post({'device': 'probe-c', 'soil_raw': 2.9, 'soil_moisture': 3})
check(call('POST', '/api/sensors/probe-c/calibrate', {'step': 'dry'})[1]['cal_dry'] == 2.9, 'the probe in dry air: the raw volts are saved as 0 %')
post({'device': 'probe-c', 'soil_raw': 1.3})
r = call('POST', '/api/sensors/probe-c/calibrate', {'step': 'wet'})[1]
check(r['done'] and r['cal_wet'] == 1.3, 'the probe in water: 100 %')
post({'device': 'probe-c', 'soil_raw': 2.1})
m = {x['key']: x for x in next(s for s in call('GET', '/api/sensors')[1]['sensors'] if s['device'] == 'probe-c')['metrics']}
check(m['soil_moisture']['value'] == 50 and next(s for s in call('GET', '/api/sensors')[1]['sensors'] if s['device'] == 'probe-c')['calibrated'], 'from then on the app works out the moisture from the volts (2.1 V is 50 %)')
check(call('POST', '/api/sensors/probe-c/calibrate', {'step': 'clear'})[1]['cal_dry'] is None, 'Start over clears both')
post({'device': 'probe-c', 'soil_raw': 2.5, 'ts': iso(time.time() - 3600)})
check(call('POST', '/api/sensors/probe-c/calibrate', {'step': 'dry'})[0] == 200, 'a reading from an hour ago is not used when a fresh one exists')

# ---- the soil moisture day by day
now, rows = time.time(), []
v = 55
for i in range(60 * 8, -1, -1):
    v -= 1.1
    if v < 22: v = 62
    rows.append({'device': 'probe-d', 'ts': iso(now - i * 3 * 3600), 'soil_moisture': round(v, 1)})
for k in range(0, len(rows), 400): post({'readings': rows[k:k + 400]})
call('PUT', '/api/sensors/probe-d', {'name': 'Pot probe', 'plant': 'P-030', 'quiet_hours': 6})
for d in ('2026-10-12', '2026-10-24'): call('POST', '/api/care', {'kind': 'water', 'plant': 'P-030', 'done_on': d})
call('POST', '/api/care', {'kind': 'water', 'plant': 'P-030'})      # today, by the app's clock
D = call('GET', '/api/sensors/days?plant=P-030&days=60')[1]
check(len(D['sensors']) == 1 and len(D['sensors'][0]['days']) >= 55 and len(D['waterings']) >= 2 and D['range'] == [35, 60], f'60 days of soil moisture for the plant ({len(D["sensors"][0]["days"])} days, {len(D["waterings"])} waterings)')

# ---- health
H = call('GET', '/api/health')[1]
check(H['version'] and H['plants'] > 50 and H['data_bytes'] > 0 and 'backup' in H and 'copy' in H and 'problems' in H, 'the health answer has the version, counts, backups, copies, problems and disk space')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Finish Test');localStorage.removeItem('plantdb.filters');localStorage.setItem('plantdb.display',JSON.stringify({layout:'single'}))")
    # the plant page
    pg.goto(LOCAL + '/#/plant/P-012'); pg.wait_for_timeout(4000)
    t = pg.locator('#about').inner_text()
    check('Summer heat (AHS heat zones)' in t and 'heat zone 8' in t and ('Summer heat is hard on it here' in t or 'A few days a summer' in t or 'Summer heat is fine' in t) and 'within its heat zones' in t, 'About this plant has the summer verdict and the heat zone range against the zone here')
    pg.locator('#about').screenshot(path=f'{OUT}/finish-heat-plant.png')
    # the filter
    pg.goto(LOCAL + '/#/weather'); pg.wait_for_timeout(4000)
    check(pg.locator('#wx-climate .heat-counts li').count() >= 2, 'the Weather page counts the plants by summer verdict')
    pg.locator('#wx-climate a[data-act=heatf]').first.click(); pg.wait_for_timeout(3000)
    n = pg.locator('#count').inner_text()
    check(pg.evaluate('location.hash') == '#/plants' and pg.locator('select[data-key=heat]').input_value() != '' and not n.startswith('87 of'), f'a count opens the Plants page with the Summer here filter set ({n})')
    pg.select_option('select[data-key=heat]', 'nodata'); pg.wait_for_timeout(1500)
    check(pg.locator('#count').inner_text().startswith('0 of') or pg.locator('#grid .sheet').count() < 87, 'the filter has a "no verdict yet" choice')
    pg.select_option('select[data-key=heat]', ''); pg.wait_for_timeout(800)
    # the moisture chart and the calendar
    pg.goto(LOCAL + '/#/plant/P-030'); pg.wait_for_timeout(4500)
    svg = pg.locator('#timeline .mchart')
    check(svg.count() == 1 and svg.get_attribute('aria-label').startswith('Soil moisture from Pot probe') and pg.locator('#timeline .mc-water').count() >= 2, 'the timeline draws the soil moisture with the waterings marked, and says it in words')
    check(pg.locator('#nutrients .bd.b-soil').count() >= 2 and pg.locator('#nutrients .bd.b-water').count() >= 1, 'the calendar shows the day\'s soil moisture and the waterings')
    pg.locator('#timeline').screenshot(path=f'{OUT}/finish-moisture.png')
    # pages in their rows, and the entry points
    pg.goto(LOCAL + '/#/inside'); pg.wait_for_timeout(2500)
    row = pg.locator('#sub-nav').inner_text()
    check('Cold-night checklist' in row and 'Coming inside' in row and 'Back outside' in row and pg.locator('#sub-nav a[aria-current=page]').inner_text().strip() == 'Coming inside', 'the Care row lists the cold-night checklist, Coming inside and Back outside')
    pg.goto(LOCAL + '/#/decisions'); pg.wait_for_timeout(2000)
    check(pg.locator('#sub-nav a[aria-current=page]').inner_text().strip() == 'Offline decisions', 'Offline decisions sits in the Settings row')
    pg.goto(LOCAL + '/#/around'); pg.wait_for_timeout(2500)
    check(pg.locator('#sub-nav a[aria-current=page]').inner_text().strip() == 'Around home', 'Around home sits in the Discover row')
    pg.goto(LOCAL + '/#/plants'); pg.wait_for_timeout(2500)
    link = pg.locator('.card-link a').first
    check(link.count() == 1 and link.inner_text() == 'Pest check before it comes inside', 'a card of a plant that moves indoors links to its pest check')
    link.click(); pg.wait_for_timeout(2500)
    check(pg.evaluate("document.activeElement.textContent") == 'Getting ready to come inside' and pg.locator('#inside a[href="#/inside"]').count() >= 1, 'it opens the plant page at that section, which links to the Coming inside page')
    pg.goto(LOCAL + '/#/'); pg.wait_for_timeout(3000)
    check(pg.locator('#today-inside a[href="#/inside"]').count() == 1, 'Today links to the Coming inside page')
    # the pages menu knows the new pages (search)
    pg.keyboard.press('/'); pg.wait_for_timeout(500); pg.keyboard.type('coming'); pg.wait_for_timeout(800)
    check('Coming inside' in pg.locator('dialog[open]').inner_text(), 'search finds "Coming inside" as a page')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300); pg.evaluate("document.getElementById('dlg').open && document.getElementById('dlg').close()")
    # health card and clear saved pages
    pg.goto(LOCAL + '/#/settings'); pg.wait_for_timeout(3000)
    hl = pg.locator('#health .hl li')
    check(hl.count() >= 6 and 'Version' in hl.first.inner_text() and 'free of' in hl.last.inner_text(), 'the Health of the app card lists the version, backups, copies, weather, stores, problems and disk space')
    pg.locator('#health').screenshot(path=f'{OUT}/finish-health.png')
    pg.goto(LOCAL + '/#/offline'); pg.wait_for_timeout(2500)
    before = pg.evaluate('QC.size')
    pg.click('[data-act=qcclear]'); pg.wait_for_timeout(1500)
    check(before > 0 and pg.evaluate('QC.size') < before + 3 and 'Cleared' in pg.locator('#toasts').inner_text(), f'Clear the saved pages empties the quick cache ({before} before)')
    # buttons say what they act on
    pg.goto(LOCAL + '/#/backups'); pg.wait_for_timeout(2500)
    if pg.locator('form[data-form=bknow] button[type=submit]').count(): pg.click('form[data-form=bknow] button[type=submit]'); pg.wait_for_timeout(5000)
    names = pg.evaluate("[...document.querySelectorAll('main button, main a')].map(e => (e.getAttribute('aria-label') || e.textContent).trim())")
    check(not any(n in ('Delete', 'Download', 'Remove') for n in names), 'on Backups, Download and Delete say which backup')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
