"""Checks what is in each pot (PLAN.md step 9, 1.57.0; plantdb/mixes.py, js/mixes.js): the Potting mixes page with the
amendments from batch C5 in three groups and their properties in words; a new recipe in parts by volume through its dialog
(an additive asks "How much" instead of parts) and its estimate; a plant's "What it is in" section (P-032 semi-hydro in LECA,
P-094 with a sphagnum top layer); recording a repot from a recipe with a top layer, which logs Repotted; "How it grows"
changed on the page; a semi-hydro pot's watering button saying "Top up" and its toast "Topped up the reservoir"; Today's list
of flushes; how often, saved; a viewer; phone width, dark and large text.
Start the mock server with a fresh data folder, then: python3 dev/test/mixes_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/mixes-*.png"""
import json, os, sys, urllib.error, urllib.request
from datetime import date
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = BASE.rsplit(':', 1)[0] + ':' + str(int(BASE.rsplit(':', 1)[1]) + 1)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=BASE, login=None):
    h = {'Content-Type': 'application/json', 'X-Editor': 'Mix Test'}
    if login: h.update({'Tailscale-User-Login': login, 'Tailscale-User-Name': login.split('@')[0].title()})
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None, headers=h, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(m, url, body=None, **kw):
    try: call(m, url, body, **kw); return 200
    except urllib.error.HTTPError as e: return e.code
over = lambda pg: pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')

M = call('GET', '/api/mixes')
am = {a['key']: a for a in M['amendments']}
check(len(M['amendments']) >= 20 and {'orchid-bark', 'coco-coir', 'charcoal', 'pumice', 'worm-castings', 'perlite', 'vermiculite', 'leca'} <= set(am),
      'batch C5 brought the amendments Ethan listed and the others suggested')
check(call('GET', '/api/mixes/plant/P-032')['grow_kind'] == 'Semi-hydro', 'P-032 is semi-hydro')

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 1000})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Mix Test')")
    # the page
    pg.goto(BASE + '/#/mixes'); pg.wait_for_selector('#mx-amendments', timeout=20000); pg.wait_for_timeout(400)
    t = pg.inner_text('#mx-amendments')
    check('Parts of a mix' in t and 'Semi-hydro media' in t and 'Additives (a pinch, not a part)' in t, 'amendments in three groups')
    check('Clay pebbles (LECA)' in t and 'lets in a great deal of air' in t and 'does not break down' in t, 'their properties in words, not numbers')
    check(pg.locator('nav a[href="#/mixes"], a[href="#/mixes"]').count() >= 1, 'Potting mixes is in the Care pages')
    pg.screenshot(path=os.path.join(OUT, 'mixes-1-page.png'), full_page=True)
    # a recipe by keyboard and mouse
    pg.locator('[data-act=mxrecipe]').first.focus(); pg.keyboard.press('Enter'); pg.wait_for_selector('form[data-mxrecipe]')
    f = pg.locator('form[data-mxrecipe]')
    f.locator('[name=name]').fill('Aroid chunky')
    rows = f.locator('.mx-part')
    rows.nth(0).locator('select').select_option(str(am['orchid-bark']['id'])); rows.nth(0).locator('[name=grade]').fill('medium'); rows.nth(0).locator('[name=parts]').fill('3')
    rows.nth(1).locator('select').select_option(str(am['perlite']['id'])); rows.nth(1).locator('[name=parts]').fill('2')
    f.locator('[data-act=mxpartadd]').click(); rows.nth(2).locator('select').select_option(str(am['coco-coir']['id'])); rows.nth(2).locator('[name=parts]').fill('1')
    f.locator('[data-act=mxpartadd]').click()
    check(pg.evaluate('document.activeElement.name') == 'am', 'Add a part puts the focus on the new row')
    slow = next(a for a in M['amendments'] if a['role'] == 'additive' and 'fertilizer' in a['name'].lower())
    rows.nth(3).locator('select').select_option(str(slow['id']))
    check(rows.nth(3).locator('.mx-amt').is_visible() and not rows.nth(3).locator('.mx-q').is_visible(), 'an additive asks How much, not parts')
    rows.nth(3).locator('[name=amount]').fill('1 teaspoon a gallon')
    pg.screenshot(path=os.path.join(OUT, 'mixes-2-recipe-dialog.png'))
    f.locator('button[value=ok]').click(); pg.wait_for_timeout(1200)
    t = pg.inner_text('#mx-recipes')
    check('3 orchid bark (medium), 2 horticultural perlite, 1 coco coir, plus slow-release fertilizer (1 teaspoon a gallon)' in t, 'the recipe in words')
    check('50% orchid bark' in t and 'An estimate' in t and 'wants freshening in about 1.5 years' in t, 'its estimate, called an estimate')
    check('Watering gaps: not enough yet' in t, 'how often it is watered waits for enough waterings')
    # P-032 and P-094
    pg.goto(BASE + '/#/plant/P-032'); pg.wait_for_selector('#mx-plant', timeout=15000); pg.wait_for_timeout(500)
    t = pg.inner_text('#mx-plant')
    check('all clay pebbles (LECA)' in t and 'Topping up' in t and 'Flushing' in t, 'P-032: in LECA, with its semi-hydro care')
    check(pg.locator('#mx-plant select[data-k=grow_kind]').input_value() == 'Semi-hydro', 'How it grows says Semi-hydro')
    wb = pg.locator('[data-quickwater]')
    if wb.count(): check('Topped up' in wb.first.inner_text(), f'its watering button says Topped up ({wb.first.inner_text()!r})')
    pg.locator('#mx-plant [data-act=care][data-kind=topup]').click(); pg.wait_for_timeout(1200)
    check('Topped up the reservoir' in pg.inner_text('#toasts'), 'Topped up the reservoir is logged, and the toast says so')
    pg.wait_for_selector('#mx-plant'); pg.wait_for_timeout(500)
    check('Topping up: last today' in pg.inner_text('#mx-plant'), 'the section shows it was topped up today')
    pg.evaluate("document.getElementById('mx-plant').scrollIntoView()"); pg.screenshot(path=os.path.join(OUT, 'mixes-3-P-032.png'))
    pg.goto(BASE + '/#/plant/P-094'); pg.wait_for_selector('#mx-plant', timeout=15000); pg.wait_for_timeout(400)
    check('Top layer: sphagnum moss' in pg.inner_text('#mx-plant'), 'P-094: LECA with a sphagnum top layer')
    # a soil plant repotted into the recipe, with a top layer
    pg.goto(BASE + '/#/plant/P-001'); pg.wait_for_selector('#mx-plant', timeout=15000); pg.wait_for_timeout(400)
    pg.click('#mx-plant [data-act=mxpot][data-repot]'); pg.wait_for_selector('form[data-mxpot]')
    fp = pg.locator('form[data-mxpot]')
    check(fp.locator('[name=repot]').is_checked(), 'Repotted: the box is ticked')
    fp.locator('[name=recipe]').select_option(label='Aroid chunky'); pg.wait_for_timeout(200)
    check(fp.locator('.mx-part').count() == 4, 'choosing the recipe fills in its four parts')
    fp.locator('[name=top_am]').select_option(str(am['sphagnum']['id'])); fp.locator('[name=top_depth]').fill('1')
    pg.screenshot(path=os.path.join(OUT, 'mixes-4-pot-dialog.png'))
    fp.locator('button[value=ok]').click(); pg.wait_for_timeout(1500)
    pg.wait_for_selector('#mx-plant'); t = pg.inner_text('#mx-plant')
    check('Aroid chunky: 3 orchid bark' in t and 'when it was repotted' in t and 'Top layer: sphagnum moss' in t, 'P-001 is in Aroid chunky, repotted today, with a top layer')
    check(any(x['kind'] == 'repot' and x['done_on'] == date.today().isoformat() for x in call('GET', '/api/care?plant=P-001')), 'Repotted is in its care log')
    # How it grows, changed on the page
    pg.locator('#mx-plant select[data-k=grow_kind]').select_option('Water only'); pg.wait_for_timeout(1500)
    pg.wait_for_selector('#mx-plant'); t = pg.inner_text('#mx-plant')
    check('Water only care' in t and 'Fresh water' in t and 'Checking the roots' in t, 'Water only: its care becomes fresh water and root checks')
    pg.locator('#mx-plant select[data-k=grow_kind]').select_option('Soil mix'); pg.wait_for_timeout(1500)
    # Today
    pg.goto(BASE + '/#/today'); pg.wait_for_selector('#mx-hydro', timeout=20000)
    t = pg.inner_text('#mx-hydro')
    check('P-092' in t and 'Flushing' in t and 'P-032' in t, 'Today lists the semi-hydro pots due a flush')
    pg.locator('#mx-hydro').screenshot(path=os.path.join(OUT, 'mixes-5-today.png'))
    # how often
    pg.goto(BASE + '/#/mixes'); pg.wait_for_selector('#mx-every')
    pg.fill('#mx-every [name=flush]', '10'); pg.click('#mx-every button[type=submit]'); pg.wait_for_timeout(1200)
    check(call('GET', '/api/mixes')['every']['flush'] == 10, 'how often to flush is saved')
    call('PUT', '/api/mixes/every', {'flush': 7})
    br.close()

call('GET', '/api/me', base=TS, login='owner@example.com')        # the first person in becomes the owner
call('PUT', '/api/people', {'login': 'viewer@example.com', 'role': 'viewer'}, base=TS, login='owner@example.com')
check(status('POST', '/api/mixes/recipes', {'name': 'Viewer', 'parts': []}, base=TS, login='viewer@example.com') == 403
      and status('POST', '/api/mixes/plant/P-001', {'parts': []}, base=TS, login='viewer@example.com') == 403, 'a viewer cannot add a recipe or a mix')
with sync_playwright() as p:
    br = p.chromium.launch()
    for name, vp, disp, base, login in (('viewer', {'width': 1280, 'height': 900}, {}, TS, 'viewer@example.com'),
                                         ('phone-dark-big', {'width': 390, 'height': 844}, {'theme': 'dark', 'size': '160'}, BASE, None)):
        ctx = br.new_context(viewport=vp, device_scale_factor=2 if 'phone' in name else 1,
                             extra_http_headers={'Tailscale-User-Login': login, 'Tailscale-User-Name': 'Vee'} if login else {})
        ph = ctx.new_page(); ph.on('pageerror', lambda e: errs.append(str(e)))
        ph.add_init_script("localStorage.setItem('plantdb.editor','Phone');localStorage.setItem('plantdb.display', JSON.stringify(%s))" % json.dumps(disp))
        ph.goto(base + '/#/mixes'); ph.wait_for_selector('#mx-amendments', timeout=20000); ph.wait_for_timeout(500)
        if name == 'viewer':
            check(all(ph.locator(f'[data-act={a}]').evaluate_all('els => els.every(e => !e.offsetParent)') for a in ('mxrecipe', 'mxam', 'mxamdel')),
                  'a viewer sees no New recipe, Change or Remove')
            ph.goto(base + '/#/plant/P-032'); ph.wait_for_selector('#mx-plant', timeout=15000); ph.wait_for_timeout(400)
            check(ph.locator('#mx-plant select[data-k=grow_kind]').is_disabled() and ph.locator('#mx-plant [data-act=mxpot]').count() == 0,
                  'nor can a viewer change what a plant is in, but sees it')
        else:
            check(over(ph) <= 0, f'{name}: the Potting mixes page does not scroll sideways ({over(ph)}px)')
            ph.screenshot(path=os.path.join(OUT, 'mixes-6-phone-page.png'))
            ph.goto(BASE + '/#/plant/P-001'); ph.wait_for_selector('#mx-plant', timeout=15000); ph.wait_for_timeout(500)
            check(over(ph) <= 0, f'{name}: a plant page with What it is in does not scroll sideways ({over(ph)}px)')
            ph.evaluate("document.getElementById('mx-plant').scrollIntoView()"); ph.wait_for_timeout(200)
            ph.screenshot(path=os.path.join(OUT, 'mixes-7-phone-plant.png'))
            ph.click('#mx-plant [data-act=mxpot]:not([data-repot])'); ph.wait_for_selector('form[data-mxpot]'); ph.wait_for_timeout(300)
            check(ph.evaluate("(() => { const d = document.querySelector('dialog'); return d.scrollWidth - d.clientWidth; })()") <= 0, f'{name}: the dialog does not scroll sideways')
            ph.screenshot(path=os.path.join(OUT, 'mixes-8-phone-dialog.png'))
        ctx.close()
    br.close()
print(f'\n{len(fails)} FAIL, {len(errs)} page errors' + (': ' + '; '.join(errs[:4]) if errs else ''))
sys.exit(1 if fails or errs else 0)
