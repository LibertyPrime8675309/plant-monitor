"""Checks Compare lights (PLAN.md step 10, 1.56.0; plantdb/compare.py, js/compare.js): reached from Grow lights; every light at one
distance, with "beyond the maker's chart" instead of a stretched figure; sorting by a header button from the keyboard (aria-sort
and the sentence above the table follow); a filter, its chip, and removing it with Enter; search; Columns; two to four lights
picked side by side; adding a light being considered from a listing; trying it in a spot; Bought it, which puts it on Grow lights;
a viewer; phone width with dark theme and large text (cards, no sideways scrolling).
Start the mock server with a fresh data folder, then: python3 dev/test/compare_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/compare-*.png"""
import json, os, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = BASE.rsplit(':', 1)[0] + ':' + str(int(BASE.rsplit(':', 1)[1]) + 1)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=BASE, login=None):
    h = {'Content-Type': 'application/json', 'X-Editor': 'Compare Test'}
    if login: h.update({'Tailscale-User-Login': login, 'Tailscale-User-Name': login.split('@')[0].title()})
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None, headers=h, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(m, url, body=None, **kw):
    try: call(m, url, body, **kw); return 200
    except urllib.error.HTTPError as e: return e.code
over = lambda pg: pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
say = lambda pg: pg.inner_text('#cmp-say')

st = call('GET', '/api/lights')
L = {x['key']: x['id'] for x in st['lights']}
codes = [x['code'] for x in st['candidates'] if x['need']][:3]
call('POST', '/api/lights/spots', {'name': 'Living room shelf', 'light': L['sansi-10w'], 'units': 2, 'distance': 12, 'hours': 12, 'dim': 100, 'plants': codes})

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 1000})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Compare Test')")
    pg.goto(BASE + '/#/lights'); pg.wait_for_selector('#cmp-ltlink', timeout=20000)
    pg.click('#cmp-ltlink'); pg.wait_for_selector('#cmp-list table', timeout=20000); pg.wait_for_timeout(400)
    check('#/compare' in pg.url and pg.locator('[data-nav=lights][aria-current=page]').count() >= 1, 'Grow lights links here, and stays marked in the top bar')
    check(over(pg) <= 0 and pg.locator('#cmp-list table').count() == 1, 'at 1280 wide the usual columns fit as a table')
    t = pg.inner_text('#cmp-list')
    check(say(pg).startswith('11 of 11 lights, sorted by PAR at 12 in, highest first'), f'the sort is said in words ({say(pg)!r})')
    check('Beyond its chart' in t, 'the pot clip light, measured only at 6 in, is beyond its chart at 12 in')
    check('Doubtful' in t and 'Estimate' in t and 'Maker' in t, 'where the numbers come from is a column')
    first = lambda: pg.locator('#cmp-list tbody th').first.inner_text()
    check(first() == 'SANSI 4-head gooseneck clamp light', f'highest PAR first ({first()!r})')
    pg.screenshot(path=os.path.join(OUT, 'compare-1-table.png'), full_page=True)
    # sort from the keyboard
    pg.locator('.cmp-th[data-k=perwatt]').focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    check(pg.locator('th:has(.cmp-th[data-k=perwatt])').get_attribute('aria-sort') == 'descending' and 'light per watt (rough), highest first' in say(pg), 'Enter on a header sorts by it, highest first')
    check(first() == 'SANSI 80 W folding bulb', f'the 80 W bulb gives the most light per watt ({first()!r})')
    check(pg.evaluate('document.activeElement.dataset.k') == 'perwatt', 'the focus stays on the header (%s)' % pg.evaluate('document.activeElement.outerHTML.slice(0, 90)'))
    pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    check('lowest first' in say(pg) and pg.locator('#cmp-list tbody tr').last.locator('td').nth(4).inner_text() == '—', 'again: lowest first, and not known still last')
    # search
    pg.fill('#cmp-q', 'barrina'); pg.wait_for_timeout(500)
    check(say(pg).startswith('2 of 11 lights matching "barrina"'), f'search by name ({say(pg)!r})')
    pg.fill('#cmp-q', ''); pg.wait_for_timeout(500)
    # a filter and its chip
    pg.locator('#cmp-filters summary').click()
    pg.locator('[data-act=cmpf][data-k=points]').select_option('side'); pg.wait_for_timeout(300)
    check(say(pg).startswith('1 of 11') and 'Barrina 2 ft standing light' in pg.inner_text('#cmp-list'), 'Points: sideways leaves the standing light')
    chip = pg.locator('#cmp-chips .chip')
    check(chip.count() == 1 and 'Points sideways' in chip.inner_text(), 'the filter shows as a chip that says what it filters')
    chip.focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    check(say(pg).startswith('11 of 11') and pg.locator('[data-act=cmpf][data-k=points]').input_value() == '', 'Enter on the chip removes the filter')
    pg.check('[data-act=cmpf][data-k=dimmable]'); pg.fill('[data-act=cmpf][data-k=ppfd]', '100'); pg.locator('[data-act=cmpf][data-k=ppfd]').dispatch_event('change'); pg.wait_for_timeout(300)
    check(all(n in pg.inner_text('#cmp-list') for n in ('SANSI 80 W folding bulb', 'SANSI tripod')) and 'SANSI 30 W' not in pg.inner_text('#cmp-list'), 'dimmable with at least 100 PAR')
    pg.click('#cmp-chips [data-k="*"]'); pg.wait_for_timeout(300)
    check(say(pg).startswith('11 of 11'), f'Clear all filters ({say(pg)!r} {pg.inner_text("#cmp-chips")!r})')
    # Columns
    pg.click('[data-act=cmpcols]'); pg.wait_for_selector('.cmp-colset')
    pg.check('.cmp-colset input[value=price]'); pg.uncheck('.cmp-colset input[value=points]'); pg.click('button[value=ok]'); pg.wait_for_timeout(500)
    heads = pg.inner_text('#cmp-list thead')
    check('Price' in heads and 'Points' not in heads, 'Columns: Price added, Points taken away')
    check('price' in json.loads(pg.evaluate("localStorage.getItem('plantdb.compare')"))['cols'], 'the choice is kept as the person\'s own setting')
    # pick to compare
    for i in range(3): pg.locator('[data-act=cmppick]').nth(i).check()
    pg.wait_for_timeout(300)
    check('The 3 picked, side by side' in pg.inner_text('#cmp-picked') and pg.locator('[data-act=cmppick]:disabled').count() == 0, 'three picked side by side')
    pg.locator('[data-act=cmppick]').nth(3).check(); pg.wait_for_timeout(300)
    check(pg.locator('[data-act=cmppick]:disabled').count() == 7, 'four is the most: the others cannot be picked')
    pg.screenshot(path=os.path.join(OUT, 'compare-2-picked.png'), full_page=True)
    pg.click('#cmp-picked [data-act=cmpunpick]'); pg.wait_for_timeout(300)
    # a light being considered
    pg.click('[data-act=cmpnew]'); pg.wait_for_selector('form.cmp-form')
    f = pg.locator('form.cmp-form')
    f.locator('[name=name]').fill('Spider Farmer SF1000'); f.locator('[name=brand]').fill('Spider Farmer'); f.locator('[name=price]').fill('139.99')
    f.locator('[name=url]').fill('https://example.com/sf1000'); f.locator('[name=watts]').fill('100')
    f.locator('[name=points]').fill('12 in 905 (4 sq ft), 18 in 516 (6.25 sq ft), 24 in 329 (9 sq ft)')
    f.locator('[name=direction]').select_option('down'); f.locator('[name=kelvin]').fill('3500'); f.locator('[name=dimming]').fill('10, 25, 50, 75, 100')
    pg.screenshot(path=os.path.join(OUT, 'compare-3-add.png'))
    f.locator('button[value=ok]').click(); pg.wait_for_timeout(1500)
    check('as a light you are considering' in pg.inner_text('#toasts'), 'Added, as a light you are considering')
    row = pg.locator('#cmp-list :is(tbody tr, li.cmp-card)', has_text='Spider Farmer SF1000')
    check(row.count() == 1 and 'Considering' in row.inner_text() and '$139.99' in row.inner_text(), f'it is in the table as Considering, with its price ({row.all_inner_texts()!r})')
    check(all(x['name'] != 'Spider Farmer SF1000' for x in call('GET', '/api/lights')['lights']), 'and not on Grow lights yet')
    # try it in a spot
    pg.locator('.cmp-name', has_text='Spider Farmer SF1000').click(); pg.wait_for_selector('form.cmp-dlg')
    pg.locator('form.cmp-dlg button[value=try]').click(); pg.wait_for_selector('#cmp-try-out table', timeout=15000); pg.wait_for_timeout(300)
    t = pg.inner_text('#cmp-try-out')
    check('Now, with SANSI 10 W bulb (PAR20)' in t and 'With Spider Farmer SF1000 (2 of them)' in t and 'Does it fit there?' in t, 'Try it in a spot: now, with it, and whether it fits')
    check(pg.locator('#cmp-try-out tbody tr').count() == len(codes), 'each plant in the spot')
    pg.screenshot(path=os.path.join(OUT, 'compare-4-try.png'))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    # bought it
    pg.locator('.cmp-name', has_text='Spider Farmer SF1000').click(); pg.wait_for_selector('form.cmp-dlg'); pg.locator('form.cmp-dlg button[value=bought]').click()
    pg.wait_for_selector('input[name=count]'); pg.fill('input[name=count]', '2'); pg.click('button[value=ok]'); pg.wait_for_timeout(1500)
    check('Bought: Spider Farmer SF1000' in pg.inner_text('#toasts'), 'Bought it')
    got = next((x for x in call('GET', '/api/lights')['lights'] if x['name'] == 'Spider Farmer SF1000'), None)
    check(got and got['count'] == 2 and got['specs'].get('brand') == 'Spider Farmer' and got['specs'].get('price') == 139.99, 'on Grow lights with 2, and nothing typed again')
    br.close()

# a viewer, and a phone
call('GET', '/api/me', base=TS, login='owner@example.com')
call('PUT', '/api/people', {'login': 'viewer@example.com', 'role': 'viewer'}, base=TS, login='owner@example.com')
check(status('POST', '/api/lights', {'name': 'V', 'status': 'considering'}, base=TS, login='viewer@example.com') == 403
      and status('POST', f"/api/lights/{L['sansi-10w']}/status", {'status': 'retired'}, base=TS, login='viewer@example.com') == 403, 'a viewer cannot add, buy or retire a light')
with sync_playwright() as p:
    br = p.chromium.launch()
    v = br.new_context(viewport={'width': 1280, 'height': 900}, extra_http_headers={'Tailscale-User-Login': 'viewer@example.com', 'Tailscale-User-Name': 'Vee'}).new_page()
    v.on('pageerror', lambda e: errs.append(str(e)))
    v.goto(TS + '/#/compare'); v.wait_for_selector('#cmp-list table, #cmp-list ul', timeout=20000); v.wait_for_timeout(400)
    check(v.locator('[data-act=cmpnew]').count() == 0 or not v.locator('[data-act=cmpnew]').is_visible(), 'a viewer sees no Add a light')
    v.locator('.cmp-name').first.click(); v.wait_for_selector('form.cmp-dlg')
    check(v.locator('form.cmp-dlg button[value=try]').count() == 1 and v.locator('form.cmp-dlg button[value=edit]').count() == 0, 'but can open a light and try it in a spot')
    ph = br.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2).new_page()
    ph.on('pageerror', lambda e: errs.append(str(e)))
    ph.add_init_script("localStorage.setItem('plantdb.editor','Phone');localStorage.setItem('plantdb.display', JSON.stringify({theme:'dark', size:'160'}))")
    ph.goto(BASE + '/#/compare'); ph.wait_for_selector('#cmp-list', timeout=20000); ph.wait_for_timeout(600)
    check(ph.locator('.cmp-cards').count() == 1 and over(ph) <= 0, f'phone, large text: cards, and no sideways scrolling ({over(ph)}px)')
    ph.screenshot(path=os.path.join(OUT, 'compare-5-phone.png'))
    ph.locator('[data-act=cmppick]').nth(0).check(); ph.locator('[data-act=cmppick]').nth(1).check(); ph.wait_for_timeout(300)
    check(over(ph) <= 0 and ph.locator('#cmp-picked .cmp-stack, #cmp-picked table').count() == 1, 'two picked fit the phone')
    ph.locator('#cmp-picked').screenshot(path=os.path.join(OUT, 'compare-6-phone-picked.png'))
    ph.locator('.cmp-name').first.click(); ph.wait_for_selector('form.cmp-dlg'); ph.wait_for_timeout(300)
    check(ph.evaluate("(() => { const d = document.querySelector('dialog'); return d.scrollWidth - d.clientWidth; })()") <= 0, 'its window fits the phone')
    br.close()
print(f'\n{len(fails)} FAIL, {len(errs)} page errors' + (': ' + '; '.join(errs[:4]) if errs else ''))
sys.exit(1 if fails or errs else 0)
