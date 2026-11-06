"""Checks 1.35.0: your sensors. Made-up readings from three sensors (one drying out in a plant's pot, one on the porch, one gone
quiet), the Sensors page with its cards and little charts, naming and placing a sensor, the plant page block, the Today section,
the watering logged from a jump in soil moisture, the sensor notifications, and people who can only view. Start the mock server
with a fresh data folder (MOCK_TS=1), then:  python3 dev/test/sensors_check.py      Screenshots: dev/tmp/shots/sns-*.png"""
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
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Sensor Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'gf@example.net', 'Tailscale-User-Name': 'Partner'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)
iso = lambda t: time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))

# ---- readings: the sensor port with the token
tok = call('GET', '/api/ingest')[1]['token']
check(call('POST', '/api/readings', {'device': 'probe-1', 'soil_moisture': 30}, {'X-Ingest-Token': 'wrong'}, SENSOR)[0] == 403, 'a wrong token is refused on the sensor port')
check(call('POST', '/api/readings', {'device': 'probe-1', 'weight_g': 999999}, {'X-Ingest-Token': tok}, SENSOR)[0] == 400, 'a weight beyond the limits is refused')
now, rows = time.time(), []
for i in range(0, 26 * 6):                      # 26 hours, every 10 minutes
    t = now - i * 600 - 60
    hr = (t / 3600) % 24
    sun = max(0.0, math.sin((hr - 6) / 12 * math.pi)) if 6 <= hr <= 18 else 0.0
    rows.append({'device': 'probe-1', 'ts': iso(t), 'soil_moisture': round(22 + i * 0.1, 1), 'temp_c': round(21 + 2 * math.sin(i / 40), 1), 'humidity': 48, 'lux': round(9000 * sun), 'weight_g': round(1850 - i * 0.8)})
    if i % 7 == 0: rows.append({'device': 'porch-air', 'ts': iso(t), 'temp_f': round(38 + 6 * math.sin(i / 40), 1), 'humidity': 60})
rows.append({'device': 'old-probe', 'ts': iso(now - 30 * 3600), 'soil_moisture': 40})
for k in range(0, len(rows), 400):
    st, r = call('POST', '/api/readings', {'readings': rows[k:k + 400]}, {'X-Ingest-Token': tok}, SENSOR)
    check(st == 201, f'{r.get("stored")} readings stored')
# the plant the probe is in: ranges to compare with
v = call('GET', '/api/plants/P-006')[1]['version']
st, r = call('PUT', '/api/plants/P-006', {'base_version': v, 'fields': {'soil_moisture_low': 35, 'soil_moisture_high': 60, 'humidity_low': 50, 'humidity_high': 70, 'temp_damage_below': 50}, 'note': 'ranges for the sensor check'})
check(st == 200 and r['temp_damage_below'] == 50, 'the plant gets ranges to compare with')
st, r = call('PUT', '/api/sensors/probe-1', {'name': 'Monstera pot', 'plant': 'P-006', 'spot': 1, 'quiet_hours': 3})
check(st == 200, 'a sensor can be named, placed at a spot and put in a plant')
check(call('PUT', '/api/sensors/nobody', {'name': 'x'})[0] == 404 and call('PUT', '/api/sensors/probe-1', {'quiet_hours': 500})[0] == 400, 'unknown sensors and silly quiet hours are refused')
d = call('GET', '/api/sensors')[1]
S = {s['device']: s for s in d['sensors']}
m = {x['key']: x for x in S['probe-1']['metrics']}
check([s['device'] for s in d['sensors']][0] == 'probe-1' and S['probe-1']['needs_look'] and m['soil_moisture']['judge']['level'] == 'low' and 'Dry' == m['soil_moisture']['judge']['word'],
      'the probe in the dry pot comes first: soil moisture below the plant\'s range')
check(m['soil_moisture']['change'] and m['soil_moisture']['change']['by'] < -10 and len([x for x in m['soil_moisture']['spark'] if x is not None]) >= 40, 'it says how much the pot dried in a day and has the little chart')
check('weight_g' in m and m['weight_g']['change'] and m['weight_g']['change']['by'] > 100 and m['weight_g']['unit'] == ' g', 'the pot weight is a metric with its change over the day')
check(S['probe-1']['place'] and S['probe-1']['place']['spot'] == 'Tall Black Shelf' and S['probe-1']['plant']['code'] == 'P-006', 'it knows its spot and its plant')
check(S['old-probe']['quiet'] and 'Quiet' in S['old-probe']['words'] and not S['porch-air']['quiet'] and S['porch-air']['plant'] is None, 'a sensor silent for 30 hours is quiet; the porch one is just not in a plant')
check(S['probe-1']['dli'] and S['probe-1']['dli']['value'] > 0, 'daily light is worked out from a day of light readings')
sm = call('GET', '/api/sensors/summary')[1]
check(sm['n'] == 3 and sm['look'] == 1 and sm['quiet'] == 1 and len(sm['cards']) == 2, 'the summary for Today: 3 sensors, 1 needs a look, 1 quiet')

# ---- the watering tie-in
before = len([x for x in call('GET', '/api/care?plant=P-006')[1] if x['kind'] == 'water'])
call('POST', '/api/readings', {'device': 'probe-1', 'soil_moisture': 58}, {'X-Ingest-Token': tok}, SENSOR)
log = [x for x in call('GET', '/api/care?plant=P-006')[1] if x['kind'] == 'water']
check(len(log) == before + 1 and log[0]['created_by'] == 'Sensor' and 'up 36 points' in log[0]['note'], 'a jump in soil moisture logs a watering for the plant, signed by the sensor')
call('POST', '/api/readings', {'device': 'probe-1', 'soil_moisture': 60}, {'X-Ingest-Token': tok}, SENSOR)
check(len([x for x in call('GET', '/api/care?plant=P-006')[1] if x['kind'] == 'water']) == before + 1, 'and only once a day')
call('PUT', '/api/sensors/probe-1', {'name': 'Monstera pot', 'plant': 'P-006', 'spot': 1, 'quiet_hours': 3, 'auto_water': False})
check(not next(s for s in call('GET', '/api/sensors')[1]['sensors'] if s['device'] == 'probe-1')['auto_water'], 'the tie-in can be turned off per sensor')
m2 = {x['key']: x for x in next(s for s in call('GET', '/api/sensors')[1]['sensors'] if s['device'] == 'probe-1')['metrics']}
check(m2['soil_moisture']['judge']['level'] == 'ok', 'after the watering the pot is in range')

# ---- notifications
call('POST', '/api/push/subscribe', {'endpoint': 'https://push.example/ethan', 'keys': {'p256dh': 'BPk', 'auth': 'aa'}, 'device': 'Windows PC'}, E, TS)
call('DELETE', '/mock/pushed')
call('POST', '/api/readings', {'device': 'probe-1', 'soil_moisture': 20, 'temp_f': 40}, {'X-Ingest-Token': tok}, SENSOR)      # dry again, and dangerously cold
call('POST', '/mock/push/run', {'what': 'sensors'})
P = call('GET', '/mock/pushed')[1]['pushed']
titles = sorted(p['title'] for p in P)
check(len(P) == 3 and any('is dry' in t for t in titles) and any('Too cold' in t for t in titles) and any('gone quiet' in t for t in titles), f'sensor alerts go out: dry, too cold, quiet ({titles})')
call('POST', '/mock/push/run', {'what': 'sensors'})
check(len(call('GET', '/mock/pushed')[1]['pushed']) == 3, 'and only once a day each')
k = call('GET', '/api/push', h=E, base=TS)[1]
check(any(x['key'] == 'sensors' for x in k['kinds']), '"Sensor alerts" is a kind of notification each person can turn off')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Sensor Test')")
    pg.goto(LOCAL + '/#/sensors'); pg.wait_for_timeout(3000)
    check(pg.locator('h1').inner_text().startswith('Your sensors (3)') and pg.locator('#sub-nav a[aria-current=page]').inner_text().strip() == 'Sensors', 'the Sensors page is in the Weather section')
    cards = pg.locator('.sns-card')
    check(cards.count() == 3 and cards.first.locator('h3').inner_text().startswith('Monstera pot') and 'sns-alert' in cards.first.get_attribute('class'), 'three cards, the one that needs a look first')
    first = cards.first
    check(first.locator('.sns-judge .tag').first.inner_text().strip().startswith('↓ Dry') and first.locator('.sns-spark').count() >= 3 and first.locator('.sns-spark').first.get_attribute('aria-label').startswith('Last 24 hours'), 'a verdict in words with its mark, and charts with a text alternative')
    check('Tall Black Shelf' in first.inner_text() and 'P-006' in first.inner_text(), 'the card says where it sits and which plant it is in')
    check('sns-off' in cards.nth(2).get_attribute('class') and 'Quiet' in cards.nth(2).inner_text(), 'the quiet one is dashed and says so')
    pg.screenshot(path=f'{OUT}/sns-page.png', full_page=True)
    # the dialog, by keyboard
    pg.locator('[data-act=snsedit][data-dev="porch-air"]').focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(800)
    check(pg.locator('dialog[open] h2').inner_text() == 'Sensor "porch-air"' and pg.evaluate("document.activeElement.name") == 'name', 'the window opens with the focus in Name')
    pg.keyboard.type('Porch air'); pg.select_option('dialog select[name=place]', 'area:2'); pg.wait_for_timeout(200)
    pg.locator('dialog button[value=ok]').click(); pg.wait_for_timeout(2500)
    card = pg.locator('#sns-porch-air')
    check(card.locator('h3').inner_text().startswith('Porch air') and 'At Covered porch' in card.inner_text(), 'saving renames it and places it in the area')
    # the plant page
    pg.goto(LOCAL + '/#/plant/P-006'); pg.wait_for_timeout(3500)
    check(pg.locator('#sns-plant .sns-card').count() == 1 and pg.locator('#sns-plant h3').inner_text().startswith('Sensor: Monstera pot'), 'the plant page shows the sensor in its pot under Water and soil')
    pg.locator('#sns-plant').scroll_into_view_if_needed(); pg.screenshot(path=f'{OUT}/sns-plant.png')
    # Today
    pg.goto(LOCAL + '/#/'); pg.wait_for_timeout(3000)
    t = pg.locator('#today-sensors')
    check(t.count() == 1 and t.locator('li').count() == 2 and 'sensors to look at' in pg.locator('.verdict-box strong').first.inner_text() and pg.locator('.td-jumps a[data-sec=today-sensors]').count() == 1, 'Today lists the sensors that need a look or have gone quiet, with a jump button')
    # a phone, dark, large text
    ph = b.new_page(viewport={'width': 390, 'height': 800}, is_mobile=True, has_touch=True)
    ph.add_init_script("localStorage.setItem('plantdb.editor','Sensor Test');localStorage.setItem('plantdb.display', JSON.stringify({theme:'dark', size:'160', space:'roomy'}))")
    ph.goto(LOCAL + '/#/sensors'); ph.wait_for_timeout(3000)
    over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
    check(over <= 2, f'phone, large text: no sideways scrolling ({over}px)')
    ph.screenshot(path=f'{OUT}/sns-phone.png', full_page=True); ph.close()
    # people who can only view
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.goto(TS + '/#/sensors'); vw.wait_for_timeout(3000)
    check(vw.locator('.sns-card').count() == 3 and not vw.locator('[data-act=snsedit]').first.is_visible() and vw.locator('[data-act=snsrm]').count() == 0, 'someone who can only view sees the cards but no buttons')
    check(call('PUT', '/api/sensors/probe-1', {'name': 'x'}, V, TS)[0] == 403 and call('DELETE', '/api/sensors/probe-1', h=V, base=TS)[0] == 403, 'and cannot change or forget a sensor')
    vw.close()
    # forget
    check(call('DELETE', '/api/sensors/old-probe', h=E, base=TS)[1]['removed'] == 1 and call('GET', '/api/sensors/summary')[1]['n'] == 2, 'the owner can forget a sensor and its readings')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
