"""Checks the prototype "Pests that eat plants" (proto/browse-risk): /api/browse, the page #/browse, and the line on a plant's page,
at laptop and phone width, with large text. Start the mock server with a fresh data folder, then: python3 dev/test/browse_check.py
Screenshots: dev/tmp/shots/browse-*.png"""
import json, os, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
from PIL import Image
BASE = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(url, m='GET', body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Browse Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(url, m, body=None):
    try: call(url, m, body); return 200
    except urllib.error.HTTPError as e: return e.code
B = call('/api/browse')
check(B['plants'] and sum(B['counts'].values()) == len(B['plants']), f'every one of {len(B["plants"])} plants has a risk, and the counts add up')
check(all(p['risk'] in ('Low', 'Moderate', 'High', 'Unknown') and p['word'] for p in B['plants']), 'each risk is written out in words')
dief = next((p for p in B['plants'] if p['sci'].startswith('Dieffenbachia')), None)
check(dief and dief['risk'] == 'Low', 'a Dieffenbachia is low risk (oxalates)')
check(any(p['risk'] == 'High' for p in B['plants']), 'some plants are high risk (coleus, begonia, grape)')
one = call('/api/browse?plant=' + B['plants'][0]['code'])
check([p['code'] for p in one['plants']] == [B['plants'][0]['code']], '?plant= gives just that plant')
# ---- the log: who ate it, with pictures as evidence; the risk set by hand
code = B['plants'][0]['code']
check(status('/api/browse/sightings', 'POST', {'plant': code, 'pest': 'Dragon'}) == 400, 'an unknown pest is refused')
check(status('/api/browse/sightings', 'POST', {'plant': code, 'pest': 'Rat', 'photos': ['../etc/passwd']}) == 400, 'a picture that is not in the record is refused')
check(status('/api/browse/sightings', 'POST', {'plant': code, 'seen_on': '2999-01-01'}) == 400, 'a date in the future is refused')
x = call('/api/browse/sightings', 'POST', {'plant': code, 'pest': 'Rat', 'damage': 'Stem chewed or gnawed', 'note': 'Gnawed at the base'})
check(x['pest'] == 'Rat' and x['photos'] == [], 'a sighting is saved')
one = call('/api/browse?plant=' + code)['plants'][0]
check(one['seen']['count'] == 1 and one['seen']['pests'] == ['Rat'], "the plant's line counts it and says who")
check(any('Seen eating: Rat' in (a.get('note') or '') for a in call('/api/audit?n=50')), 'a sighting is in the audit log')
check(call('/api/browse')['by_pest'].get('Rat') == 1, 'the page counts sightings by pest')
v = call('/api/plants/' + code)
call('/api/plants/' + code, 'PUT', {'base_version': v['version'], 'base_values': {'browse_risk': ''}, 'fields': {'browse_risk': 'High'}})
one = call('/api/browse?plant=' + code)['plants'][0]
check(one['risk'] == 'High' and one['source'] == 'you' and one['usual'] != 'High' or one['source'] == 'you', 'a risk set by hand beats the usual for its kind')
tn = call('/api/browse?tonight=1')
check(any(p['code'] == code for p in tn['tonight']), 'a plant set to High (outside) is on tonight\'s list')
call('/api/browse/sightings/%d' % x['id'], 'DELETE')
check(call('/api/browse?plant=' + code)['plants'][0]['seen']['count'] == 0, 'a sighting can be removed')
pic = os.path.join(OUT, 'browse-evidence.jpg'); Image.new('RGB', (320, 240), (90, 140, 70)).save(pic)
with sync_playwright() as pw:
    br = pw.chromium.launch()
    # the windows: log a sighting with a picture, change a risk
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Browse Test')")
    pg.goto(BASE + '/#/browse'); pg.wait_for_selector('#br-plan', timeout=15000)
    pg.locator('#app .job [data-act=brseen]').first.click(); pg.wait_for_selector('dialog[open] [name=pest]')
    pg.select_option('dialog[open] [name=pest]', 'Rabbit'); pg.select_option('dialog[open] [name=damage]', 'Leaves eaten')
    pg.set_input_files('dialog[open] [name=files]', pic)
    pg.screenshot(path=os.path.join(OUT, 'browse-dialog-seen.png'))
    pg.locator('dialog[open] button[value=ok]').click(); pg.wait_for_selector('#br-seen .br-sight', timeout=10000)
    check('rabbit' in pg.inner_text('#br-seen .br-sight').lower(), 'a sighting logged in the window shows on the page')
    check(pg.locator('#br-seen .br-sight img').count() == 1, 'and its picture is shown as evidence')
    check(pg.locator('#br-seen .br-sight img').first.get_attribute('alt'), 'the picture has a description')
    pg.screenshot(path=os.path.join(OUT, 'browse-sightings.png'))
    pg.locator('#app .job [data-act=brrisk]').first.click(); pg.wait_for_selector('dialog[open] [name=risk]')
    pg.select_option('dialog[open] [name=risk]', 'Low'); pg.locator('dialog[open] button[value=ok]').click(); pg.wait_for_timeout(1200)
    check(any(p['own'] == 'Low' for p in call('/api/browse')['plants']), 'Change risk saves a risk for that plant')
    pg.evaluate("document.documentElement.dataset.role = 'viewer'")
    check(pg.locator('[data-act=brseen]:visible, [data-act=brrisk]:visible, [data-act=brdel]:visible').count() == 0, 'people who can only view do not see the buttons')
    pg.close()
    # Today, in the evening (the server's clock is changed on the way to the page)
    def evening(route):
        r = route.fetch(); d = r.json(); d['evening'] = True
        route.fulfill(response=r, body=json.dumps(d), headers=dict(r.headers, **{'content-type': 'application/json'}))
    cx = br.new_context(viewport={'width': 1280, 'height': 900}, service_workers='block')
    tp = cx.new_page(); tp.on('pageerror', lambda e: errs.append(str(e)))
    tp.add_init_script("localStorage.setItem('plantdb.editor','Browse Test')")
    tp.route('**/api/browse?tonight=1', evening)
    tp.goto(BASE + '/#/'); tp.wait_for_selector('#today-browse', timeout=15000)
    check(tp.inner_text('#today-browse h2').startswith('Cover tonight ('), 'in the evening Today lists the plants to cover')
    check(tp.locator('.td-jumps a[data-sec=today-browse]').count() == 1, 'with a jump button')
    tp.locator('#today-browse').screenshot(path=os.path.join(OUT, 'browse-today.png'))
    tp.locator('[data-act=brdone]').click(); tp.wait_for_timeout(500)
    check(tp.locator('#today-browse').count() == 0, 'Done for tonight hides it')
    tp.goto(BASE + '/#/plants'); tp.goto(BASE + '/#/'); tp.wait_for_selector('#today-needs'); tp.wait_for_timeout(1500)
    check(tp.locator('#today-browse').count() == 0, 'and it stays hidden for the rest of the day')
    cx.close()
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
    pg.locator('#br-plant a[href="#/browse"]').click(); pg.wait_for_selector('#br-plan')
    check(pg.url.endswith('#/browse'), 'its link opens the page')
    br.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
