"""Checks units (1.47.0, PLAN.md step 4a): the record keeps °F and inches; a person's choice in Display (a region, then each unit by
hand) changes what every page shows and what the edit forms take, and follows them to the server. Start the mock server with a fresh
data folder, then:  python3 dev/test/units_check.py      Screenshots: dev/tmp/shots/units-*.png"""
import json, os, re, sys, urllib.request
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Units Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
plants = call('GET', '/api/plants')
P = next(p for p in plants if p.get('temp_ideal_low') is not None and p.get('temp_damage_below') is not None)
code, lo, dmg = P['code'], P['temp_ideal_low'], P['temp_damage_below']
c_of = lambda f: round((f - 32) * 5 / 9)
def temps_on(pg, sel='main'):
    # the change log (article.slip) quotes old values as they were typed, so it is left out of the count
    t = pg.evaluate("sel => { const m = document.querySelector(sel).cloneNode(true); m.querySelectorAll('article.slip').forEach(e => e.remove()); return m.innerText; }", sel)
    f = re.findall(r'.{0,60}-?\d+(?:\.\d+)?°F.{0,20}', t)
    if f: print('   °F still here: ' + ' | '.join(x.replace('\n', ' ') for x in f[:4]))
    return len(f), len(re.findall(r'-?\d+(?:\.\d+)?°C', t))
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Units Test')")
    # 1. the default is Fahrenheit and inches
    pg.goto(BASE + f'/#/plant/{code}'); pg.wait_for_selector('.gauge-title, .verdicts', timeout=15000); pg.wait_for_timeout(800)
    f_n, c_n = temps_on(pg)
    check(f_n > 3 and c_n == 0 and f'{lo}°F' in pg.inner_text('main'), f'a plant page starts in °F ({f_n} figures), with its comfortable minimum {lo}°F')
    # 2. Display, Units: the region "Everywhere else" turns everything metric at once
    pg.click('#nav-tab') if pg.locator('#nav-tab').is_visible() else None
    pg.click('#display-btn'); pg.wait_for_selector('#pref-u-region')
    pg.select_option('#pref-u-region', 'metric'); pg.wait_for_timeout(1200)
    check(pg.input_value('#pref-u-temp') == 'c' and pg.input_value('#pref-u-len') == 'cm' and pg.input_value('#pref-u-rain') == 'mm', 'choosing a region sets temperature, lengths and rain together')
    pg.locator('dialog.dv .dv-acts button[value=ok]').click(); pg.wait_for_timeout(1000)
    f_n, c_n = temps_on(pg)
    check(f_n == 0 and c_n > 3 and f'{c_of(lo)}°C' in pg.inner_text('main'), f'the plant page now reads in °C ({c_n} figures, none in °F): comfortable minimum {c_of(lo)}°C')
    pg.screenshot(path=os.path.join(OUT, 'units-1-plant-celsius.png'), full_page=False)
    check(json.loads(pg.evaluate("localStorage.getItem('plantdb.units')"))['region'] == 'metric', 'the choice is kept in plantdb.units')
    pg.wait_for_timeout(1500)
    check(json.loads((call('GET', '/api/me/prefs')['prefs'].get('units') or '{}')).get('region') == 'metric', 'and sent to the server with the settings that follow you')
    # 3. the edit form shows and takes °C, and keeps °F underneath
    pg.goto(BASE + f'/#/plant/{code}/edit'); pg.wait_for_selector('input[name=temp_ideal_low]', timeout=15000)
    check(pg.input_value('input[name=temp_ideal_low]') == str(c_of(lo)), f'the edit form shows the comfortable minimum as {c_of(lo)} (°C)')
    lab = pg.inner_text('label:has(input[name=temp_ideal_low])')
    check('(°C)' in lab and '(F)' not in lab, 'its label says °C')
    pg.fill('input[name=temp_ideal_low]', str(c_of(lo) + 2)); pg.click('form button[type=submit]'); pg.wait_for_timeout(2000)
    saved = call('GET', f'/api/plants/{code}')
    check(saved['temp_ideal_low'] == round((c_of(lo) + 2) * 9 / 5 + 32), f'saving 2°C more stores whole °F again ({saved["temp_ideal_low"]}°F)')
    call('PUT', f'/api/plants/{code}', {'base_version': saved['version'], 'base_values': {'temp_ideal_low': saved['temp_ideal_low']}, 'fields': {'temp_ideal_low': lo}})
    # 4. Today and Weather read in °C and mm; the frost line too
    pg.goto(BASE + '/#/weather'); pg.wait_for_selector('h1', timeout=15000); pg.wait_for_timeout(2500)
    f_n, c_n = temps_on(pg)
    check(f_n == 0 and c_n > 0, f'the Weather page reads in °C ({c_n} figures, no °F)')
    check(pg.locator('.chart-card h3', has_text='°C').count() >= 1 and pg.locator('.chart-card h3', has_text='°F').count() == 0, 'temperature charts are titled in °C')
    pg.screenshot(path=os.path.join(OUT, 'units-2-weather-celsius.png'), full_page=False)
    pg.goto(BASE + '/#/frost'); pg.wait_for_selector('h1', timeout=15000); pg.wait_for_timeout(1500)
    f_n, c_n = temps_on(pg); check(f_n == 0, 'the cold-night checklist has no °F left')
    # 5. one unit changed by hand stands: Celsius, but inches for lengths
    pg.click('#display-btn'); pg.wait_for_selector('#pref-u-len'); pg.select_option('#pref-u-len', 'in'); pg.wait_for_timeout(800)
    pg.locator('dialog.dv .dv-acts button[value=ok]').click(); pg.wait_for_timeout(800)
    u = json.loads(pg.evaluate("localStorage.getItem('plantdb.units')"))
    check(u.get('region') == 'metric' and u.get('len') == 'in', 'a unit changed by hand is kept beside the region')
    pot = call('POST', '/api/containers', {'kind': 'pot', 'name': 'Units test pot', 'shape': 'circle', 'dia_in': 6, 'height_in': 5, 'qty': 2})
    pg.goto(BASE + '/#/pots'); pg.wait_for_selector('.ct-card', timeout=15000)
    card = pg.locator(f'#ct-{pot["id"]}')
    check('(in)' in card.inner_text() and card.locator('input[data-k=dia_in]').input_value() == '6' and 'inches' in pg.inner_text('main'), 'Pots and trays go back to inches (a 6 in pot reads 6) while temperatures stay in °C')
    pg.click('#display-btn'); pg.wait_for_selector('#pref-u-len'); pg.select_option('#pref-u-len', 'cm'); pg.wait_for_timeout(800)
    pg.locator('dialog.dv .dv-acts button[value=ok]').click(); pg.wait_for_timeout(1200)
    card = pg.locator(f'#ct-{pot["id"]}')
    check('(cm)' in card.inner_text() and card.locator('input[data-k=dia_in]').input_value() == '15', 'in centimetres the same pot reads 15 across')
    card.locator('input[data-k=dia_in]').fill('20'); card.locator('input[data-k=dia_in]').press('Enter'); pg.wait_for_timeout(1500)
    got = next(x for x in call('GET', '/api/containers')['items'] if x['id'] == pot['id'])
    check(abs(got['dia_in'] - 7.9) < 0.11, f'typing 20 cm stores {got["dia_in"]} inches')
    # 6. phone width, large text: the Units part of Display fits
    pg.set_viewport_size({'width': 390, 'height': 844}); pg.goto(BASE + '/#/'); pg.wait_for_selector('h1', timeout=15000)
    pg.evaluate("PlantPrefs.set('size', '160')")
    if pg.locator('#nav-tab').is_visible(): pg.click('#nav-tab')
    pg.click('#display-btn'); pg.wait_for_selector('#pref-u-region'); pg.locator('#pref-u-region').scroll_into_view_if_needed(); pg.wait_for_timeout(500)
    check(pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), 'no sideways scrolling at phone width with the Units settings open')
    pg.screenshot(path=os.path.join(OUT, 'units-3-display-phone.png'))
    # 7. back to the United States: everything in °F again
    pg.select_option('#pref-u-region', 'us'); pg.wait_for_timeout(800); pg.locator('dialog.dv .dv-acts button[value=ok]').click(); pg.wait_for_timeout(800)
    pg.set_viewport_size({'width': 1280, 'height': 900}); pg.goto(BASE + f'/#/plant/{code}'); pg.wait_for_selector('.verdicts', timeout=15000); pg.wait_for_timeout(800)
    f_n, c_n = temps_on(pg); check(c_n == 0 and f_n > 3, 'back on United States, the plant page reads in °F again')
    br.close()
check(not errs, 'no page errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print(f'\n{len(fails)} FAIL' + (': ' + '; '.join(fails) if fails else ''))
sys.exit(1 if fails else 0)
