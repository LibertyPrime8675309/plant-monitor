"""Checks the prototype "Pests that eat plants" (proto/browse-risk): /api/browse, the page #/browse, and the line on a plant's page,
at laptop and phone width, with large text. Start the mock server with a fresh data folder, then: python3 dev/test/browse_check.py
Screenshots: dev/tmp/shots/browse-*.png"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(url):
    with urllib.request.urlopen(BASE + url) as r: return json.loads(r.read())
B = call('/api/browse')
check(B['plants'] and sum(B['counts'].values()) == len(B['plants']), f'every one of {len(B["plants"])} plants has a risk, and the counts add up')
check(all(p['risk'] in ('Low', 'Moderate', 'High', 'Unknown') and p['word'] for p in B['plants']), 'each risk is written out in words')
dief = next((p for p in B['plants'] if p['sci'].startswith('Dieffenbachia')), None)
check(dief and dief['risk'] == 'Low', 'a Dieffenbachia is low risk (oxalates)')
check(any(p['risk'] == 'High' for p in B['plants']), 'some plants are high risk (coleus, begonia, grape)')
one = call('/api/browse?plant=' + B['plants'][0]['code'])
check([p['code'] for p in one['plants']] == [B['plants'][0]['code']], '?plant= gives just that plant')
with sync_playwright() as pw:
    br = pw.chromium.launch()
    for name, w, disp in (('laptop', 1280, {}), ('phone-big', 390, {'theme': 'dark', 'size': '160'})):
        pg = br.new_page(viewport={'width': w, 'height': 900}, device_scale_factor=1)
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script("localStorage.setItem('plantdb.editor','Browse Test');localStorage.setItem('plantdb.display', JSON.stringify(%s))" % json.dumps(disp))
        pg.goto(BASE + '/#/browse'); pg.wait_for_selector('#br-plan', timeout=15000)
        check(pg.locator('h1').inner_text() == 'Pests that eat plants', f'{name}: the page opens')
        check(pg.locator('#app .job').count() == len(B['plants']), f'{name}: every plant is listed once')
        check('High' in pg.inner_text('#app') or 'favourite' in pg.inner_text('#app'), f'{name}: the risk is in words')
        over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: nothing scrolls sideways ({over}px)')
        pg.screenshot(path=os.path.join(OUT, f'browse-{name}.png'))
        pg.close()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Browse Test')")
    pg.goto(BASE + '/#/plant/' + B['plants'][0]['code']); pg.wait_for_selector('#br-plant', timeout=15000)
    check('Eaten by pests' in pg.inner_text('#br-plant'), "a plant's page has the risk line")
    pg.locator('#br-plant a').click(); pg.wait_for_selector('#br-plan')
    check(pg.url.endswith('#/browse'), 'its link opens the page')
    br.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
