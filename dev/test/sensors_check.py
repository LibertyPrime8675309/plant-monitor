"""Focused check for the sensor dashboard (prototype proto/sensor-dashboard).
Start the app with dev/test/mock_server.py first (a fresh DATA_DIR), then:  python3 dev/test/sensors_check.py [base-url]
It sends made-up readings from three sensors (one drying out, one fine, one gone quiet), links one to P-006, then checks the
Weather page and plant pages at phone and laptop width in light and dark, the dialog (keyboard), saving and the audit log.
Screenshots go to dev/tmp/shots/sns-*.png."""
import json, math, os, sys, time, urllib.request
from playwright.sync_api import sync_playwright
B = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)


def call(m, u, body=None, h=None):
    r = urllib.request.Request(B + u, method=m, data=json.dumps(body).encode() if body is not None else None,
                               headers={'Content-Type': 'application/json', 'X-Editor': 'Sensor check', **(h or {})})
    return json.loads(urllib.request.urlopen(r).read() or 'null')


def seed():
    tok = call('GET', '/api/ingest')['token']
    now, rows = time.time(), []
    iso = lambda t: time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))
    for i in range(96):                 # every 30 minutes for 2 days
        t = now - i * 1800 - 300
        hr = (t / 3600) % 24
        sun = max(0.0, math.sin((hr - 6) / 12 * math.pi)) if 6 <= hr <= 18 else 0.0
        rows.append({'device': 'probe-1', 'ts': iso(t), 'soil_moisture': round(18 + i * 0.25, 1), 'temp_f': round(70 + 4 * math.sin(hr / 24 * 6.28), 1), 'humidity': 46, 'par': round(350 * sun, 1)})
        rows.append({'device': 'probe-2', 'ts': iso(t), 'soil_moisture': 45, 'temp_f': 72, 'humidity': 60})
        if i >= 12: rows.append({'device': 'porch', 'ts': iso(t), 'temp_f': round(58 + 8 * math.sin(hr / 24 * 6.28), 1), 'humidity': 70})
    for k in range(0, len(rows), 400): call('POST', '/api/readings', {'readings': rows[k:k + 400]}, {'X-Ingest-Token': tok})
    call('PUT', '/api/sensors/probe-1', {'name': 'Monstera pot', 'plant': 'P-006', 'quiet_hours': 3})


fails = []
seed()
# the API on its own: the drying probe is judged against P-006's range, the porch sensor is quiet, an unknown one is refused
S = {s['device']: s for s in call('GET', '/api/sensors')['sensors']}
p1 = S['probe-1']; sm = next(m for m in p1['metrics'] if m['key'] == 'soil_moisture')
if sm['judge']['level'] != 'low' or not p1['needs_look']: fails.append(f'probe-1 should be dry: {sm["judge"]}')
if not sm['change'] or sm['change']['by'] >= 0: fails.append(f'probe-1 should be drying: {sm["change"]}')
if not S['porch']['quiet'] or S['probe-2']['quiet']: fails.append('quiet flags are wrong')
if list(S)[0] != 'probe-1': fails.append('the sensor that needs a look should come first')
try: call('PUT', '/api/sensors/nobody', {'name': 'x'}); fails.append('an unknown sensor was accepted')
except urllib.error.HTTPError as e:
    if e.code != 404: fails.append(f'unknown sensor gave {e.code}')
try: call('PUT', '/api/sensors/probe-2', {'quiet_hours': 999}); fails.append('999 quiet hours accepted')
except urllib.error.HTTPError as e:
    if e.code != 400: fails.append(f'bad quiet hours gave {e.code}')

with sync_playwright() as p:
    b = p.chromium.launch()
    for size, (w, h) in {'phone': (390, 844), 'laptop': (1280, 800)}.items():
        for theme in ('light', 'dark'):
            pg = b.new_page(viewport={'width': w, 'height': h}); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.add_init_script("localStorage.setItem('plantdb.editor','Check');localStorage.setItem('plantdb.display',JSON.stringify(%s))" % json.dumps({'theme': theme}))
            pg.goto(B + '/#/weather'); pg.wait_for_selector('#sns-box .sns-card', timeout=15000); pg.wait_for_timeout(1500)
            el = pg.locator('#sns-dash'); el.scroll_into_view_if_needed(); el.screenshot(path=f'{OUT}/sns-{size}-{theme}-weather.png')
            over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            if over > 2: fails.append(f'{size} {theme} weather page scrolls sideways by {over}px')
            txt = el.inner_text()
            for want in ['Your sensors (3)', 'Monstera pot', 'Dry', 'Quiet: last heard', 'Not linked to a plant', 'Change name or plant']:
                if want not in txt: fails.append(f'{size} {theme}: Weather page is missing "{want}"')
            if pg.locator('#sn-list a', has_text='Your sensors').count() == 0: fails.append(f'{size} {theme}: not in the On this page menu')
            pg.goto(B + '/#/plant/P-006'); pg.wait_for_selector('#sns-plant .sns-card', timeout=15000); pg.wait_for_timeout(800)
            el = pg.locator('#soil'); el.scroll_into_view_if_needed(); el.screenshot(path=f'{OUT}/sns-{size}-{theme}-plant.png')
            if 'Sensor: Monstera pot' not in el.inner_text(): fails.append(f'{size} {theme}: plant page has no sensor card')
            over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            if over > 2: fails.append(f'{size} {theme} plant page scrolls sideways by {over}px')
            if errs: fails.append(f'{size} {theme} JavaScript errors: {errs}')
            pg.close()
    pg = b.new_page(viewport={'width': 390, 'height': 844}); pg.add_init_script("localStorage.setItem('plantdb.editor','Check')")
    pg.goto(B + '/#/plant/P-010'); pg.wait_for_selector('#sns-plant', state='attached', timeout=15000); pg.wait_for_timeout(1500)
    if pg.locator('#sns-plant .sns-card').count(): fails.append('P-010 shows a sensor it does not have')
    # link probe-2 to P-010 through the dialog, typing and pressing Enter
    pg.goto(B + '/#/weather'); pg.wait_for_selector('#sns-box .sns-card'); pg.wait_for_timeout(500)
    pg.locator('[data-act=snsedit][data-dev="probe-2"]').click(); pg.wait_for_selector('dialog[open] form[data-form=snssave]')
    if pg.evaluate('document.activeElement.name') != 'name': fails.append('the dialog does not start in the Name box')
    pg.screenshot(path=f'{OUT}/sns-phone-light-dialog.png')
    pg.keyboard.type('Fern pot'); pg.select_option('dialog select[name=plant]', 'P-010')
    pg.locator('dialog [name=quiet_hours]').focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(1500)
    if pg.locator('dialog[open]').count(): fails.append('the dialog stayed open after saving')
    s = next(x for x in call('GET', '/api/sensors')['sensors'] if x['device'] == 'probe-2')
    if s['name'] != 'Fern pot' or not s['plant'] or s['plant']['code'] != 'P-010': fails.append(f'not saved: {s["name"]} {s["plant"]}')
    pg.goto(B + '/#/plant/P-010'); pg.wait_for_selector('#sns-plant .sns-card', timeout=15000)
    a = call('GET', '/api/audit/search?q=probe-2')
    if not any((e.get('field') or '') == 'sensor:probe-2' for e in a['entries']): fails.append('no audit log row for the change')
    call('PUT', '/api/sensors/probe-2', {'name': '', 'plant': '', 'quiet_hours': 3})          # back as it was, so the check can run again
    b.close()
print('\n'.join(fails) or 'sensor dashboard check passed')
sys.exit(1 if fails else 0)
