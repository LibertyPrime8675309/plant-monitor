"""Checks 1.11.0: what each plant needs (N-P-K ratio and strength), your fertilizers, the best match and how much to mix,
on the Fertilizer page, plant pages and the feeding dialog; and the Location button: choosing, searching, adding and
making a place home, and every weather screen following it.
Start the mock server with a fresh data folder first, then:  python3 dev/test/fertloc_check.py [base-url]
Screenshots: dev/tmp/shots/fertloc-*.png"""
import json, os, sys, time, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, place=None, who='Fert Test'):
    h = {'X-Editor': who, 'Content-Type': 'application/json'}
    if place: h['X-Place'] = str(place)
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None, headers=h, method=m)
    return json.load(urllib.request.urlopen(req))
def status(m, url, body=None):
    try: call(m, url, body); return 200
    except urllib.error.HTTPError as e: return e.code
need = lambda code: call('GET', '/api/fertilizer/needs?plant=' + code)['needs'][0]

# ---- the server: plant needs, your fertilizers, matching and amounts
n = need('P-013')
check(n['ratio_text'] == '2-7-7' and n['strength'] == 'Half strength' and n['match'] is None and 'No fertilizers yet' in n['note'], 'cactus P-013 needs 2-7-7 at half strength; no fertilizers yet')
check(need('P-023')['strength'] == 'None needed' and need('P-017')['ratio_text'] == '4-1-6', 'cosmos needs none; the majesty palm needs 4-1-6')
allneeds = call('GET', '/api/fertilizer/needs')['needs']
check(len(allneeds) >= 78 and all(x['ratio'] or x['strength'] == 'None needed' for x in allneeds), f'all {len(allneeds)} plants have a ratio or "None needed" (batch A2)')
check(status('POST', '/api/fertilizer/products', {'product': 'Bad', 'form': 'liquid', 'n': 0, 'p': 0, 'k': 0}) == 400, 'a fertilizer with 0-0-0 is refused')
call('POST', '/api/fertilizer/products', {'product': 'Dyna-Gro Foliage-Pro', 'form': 'liquid', 'n': 9, 'p': 3, 'k': 6})
call('POST', '/api/fertilizer/products', {'product': 'Schultz Cactus Plus', 'form': 'liquid', 'n': 2, 'p': 7, 'k': 7})
call('POST', '/api/fertilizer/products', {'product': 'Osmocote Smart-Release', 'form': 'slow-release', 'n': 14, 'p': 14, 'k': 14})
check(status('POST', '/api/fertilizer/products', {'product': 'schultz cactus plus', 'form': 'liquid', 'n': 2, 'p': 7, 'k': 7}) == 409, 'the same name twice is refused')
m = need('P-013')['match']
check(m['product'] == 'Schultz Cactus Plus' and m['quality'] == 'Matches' and m['dose']['kind'] == 'water' and 'tsp' in m['dose']['words'] and 'gallon' in m['dose']['words'], f"cactus: Schultz Cactus Plus matches, {m['dose']['words']}")
m = need('P-001')['match']
check(m['product'] == 'Dyna-Gro Foliage-Pro' and m['quality'] == 'Matches' and m['dose']['amount_text'] == '⅝ tsp' and 70 <= m['dose']['ppm_n'] <= 80, f"aroid: Foliage-Pro, {m['dose']['amount_text']} a gallon, about {m['dose']['ppm_n']} ppm N")
m = need('P-025')['match']
check(m['product'] == 'Osmocote Smart-Release' and m['dose']['kind'] == 'soil' and 'not into water' in m['dose']['words'], 'balanced: slow-release goes on the mix, not into water')
m = need('P-017')['match']
check(m['quality'] in ('Usable', 'Not a good match', 'Close') and 'potash' in m['why'], f"palm: closest is {m['product']} ({m['quality']}): {m['why']}")
check(need('P-023')['match'] is None, 'cosmos (none needed): nothing suggested')
# a fertilizer that was only logged counts too, with the dose used last time
call('POST', '/api/fertilizer', {'plants': ['P-022'], 'product': 'Rose Food 18-24-16', 'form': 'powder', 'n': 18, 'p': 24, 'k': 16, 'applied_on': '2026-10-20',
                                 'amount': 0.5, 'amount_unit': 'tsp', 'water_amount': 1, 'water_unit': 'gal'})
m = need('P-022')['match']
check(m['product'] == 'Rose Food 18-24-16' and m['last'] and m['last']['amount'] == 0.5, 'rose: a fertilizer you only logged is matched, with your last dose')
prods = call('GET', '/api/fertilizer/products')
check(len(prods) == 4 and sum(1 for x in prods if x['saved']) == 3, '4 fertilizers: 3 saved and 1 from the log')
check(status('PUT', '/api/plants/P-013', {'base_version': call('GET', '/api/plants/P-013')['version'], 'fields': {'npk_ratio': 'lots'}}) == 400, 'a ratio that is not three numbers is refused')
v = call('GET', '/api/plants/P-013')['version']
call('PUT', '/api/plants/P-013', {'base_version': v, 'fields': {'npk_ratio': '1:2:2'}})
check(call('GET', '/api/plants/P-013')['npk_ratio'] == '1-2-2', '"1:2:2" is saved as 1-2-2')
call('PUT', '/api/plants/P-013', {'base_version': v + 1, 'fields': {'npk_ratio': '2-7-7'}})

# ---- the server: the place in use
home = call('GET', '/api/meta')['place']
check(home['is_home'] and home['name'], f"the home place to start with: {home['name']}")
r = call('POST', '/api/places', {'name': 'Baraboo, WI', 'lat': 43.4711, 'lon': -89.7443, 'tz': 'America/Chicago'})
pid = r['place']['id']
for _ in range(40):
    time.sleep(1.5)
    if not call('GET', '/api/weather/job').get('running'): break
meta2 = call('GET', '/api/meta', place=pid)
check(meta2['place']['id'] == pid and meta2['home_tz'] == 'America/Chicago', 'X-Place picks the place for a request')
f1, f2 = call('GET', '/api/frost'), call('GET', '/api/frost', place=pid)
check(f2.get('first') and (not f1.get('first') or f2['first']['low'] < f1['first']['low']), 'frost warnings follow the place (Baraboo is colder)')
check(call('GET', '/api/weather', place=pid)['location']['id'] == pid, 'the Weather page data follows it too')
ref = call('GET', '/api/reference', place=pid)
check(ref['applies'] is False and call('GET', '/api/reference')['applies'] is True, 'the written Round Rock notes apply only near Round Rock')
check(call('GET', '/api/meta', place=9999)['place']['id'] == home['id'], 'a place that does not exist falls back to home')

with sync_playwright() as pw:
    b = pw.chromium.launch()
    def page(vw=(1280, 900), disp=None, place=None):
        pg = b.new_page(viewport={'width': vw[0], 'height': vw[1]})
        pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        init = "localStorage.setItem('plantdb.editor','Fert Test');localStorage.setItem('plantdb.display',JSON.stringify(%s));" % json.dumps(disp or {'navopen': '0'})
        init += "localStorage.setItem('plantdb.place','%s');" % place if place else "localStorage.removeItem('plantdb.place');"
        pg.add_init_script("if(!sessionStorage.getItem('fl-init')){sessionStorage.setItem('fl-init','1');" + init + "}")
        return pg
    # Fertilizer page
    pg = page((1280, 1000))
    pg.goto(f'{BASE}/#/fertilizer'); pg.wait_for_timeout(2600)
    pg.evaluate("document.querySelectorAll('details.grp').forEach(d => { d.open = true; })")
    row = pg.locator('ul.todo li.fn-li:has(a[href="#/plant/P-013"])')
    t = row.inner_text()
    check(row.count() == 1 and 'Needs N-P-K ratio 2-7-7' in t and 'Schultz Cactus Plus' in t and 'tsp into 1 gallon' in t, 'Fertilizer page row: needs, best match and amount')
    lines = t.split('\n')
    check(lines.index(next(x for x in lines if x.startswith('P-013'))) < lines.index(next(x for x in lines if x.startswith('Needs'))), 'the needs line sits under the ID and last-logged line')
    check('Matches' in row.locator('.fn-q').inner_text() and row.locator('.fn-q').inner_text().startswith('✔'), 'the match badge has a symbol and a word, not only colour')
    check(pg.locator('#fn-products tbody tr').count() == 4, '"Your fertilizers" lists all 4')
    pg.evaluate("document.querySelector('ul.todo li.fn-li').scrollIntoView({block:'center'})"); pg.wait_for_timeout(300)
    pg.screenshot(path=f'{OUT}/fertloc-fert-rows.png')
    # add one from the page
    pg.locator('[data-act=fzadd]').click(); pg.wait_for_timeout(400)
    pg.fill('dialog[open] input[name=product]', 'Palm Gain 8-2-12'); pg.select_option('dialog[open] select[name=form]', 'granular')
    pg.fill('dialog[open] input[name=n]', '8'); pg.fill('dialog[open] input[name=p]', '2'); pg.fill('dialog[open] input[name=k]', '12')
    pg.locator('dialog[open] button[value=ok]').click(); pg.wait_for_timeout(2200)
    pg.evaluate("document.querySelectorAll('details.grp').forEach(d => { d.open = true; })")
    check(pg.locator('#fn-products tbody tr').count() == 5, 'Add a fertilizer you have saves it')
    t = pg.locator('ul.todo li.fn-li:has(a[href="#/plant/P-017"])').inner_text()
    check('Palm Gain 8-2-12' in t and 'not into water' in t, 'the palm now matches Palm Gain, a granular feed for the mix')
    pg.evaluate("document.getElementById('fn-products').scrollIntoView()"); pg.wait_for_timeout(300)
    pg.screenshot(path=f'{OUT}/fertloc-products.png')
    # logging for one plant starts from its match
    pg.locator('ul.todo li.fn-li:has(a[href="#/plant/P-001"]) [data-act=fertlog]').click(); pg.wait_for_timeout(600)
    check(pg.locator('dialog[open] input[name=product]').input_value() == 'Dyna-Gro Foliage-Pro' and pg.locator('dialog[open] input[name=amount]').input_value() == '0.625',
          'Log for P-001 starts with Foliage-Pro, ⅝ tsp')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    # plant page
    pg.goto(f'{BASE}/#/plant/P-013'); pg.wait_for_timeout(2600)
    t = pg.locator('#fert-need').inner_text()
    check('What to feed it' in t and '2-7-7' in t and 'Schultz Cactus Plus' in t, 'plant page: What to feed it, under Nutrients')
    pg.goto(f'{BASE}/#/plant/P-013/edit'); pg.wait_for_timeout(1800)
    check(pg.locator('input[name=npk_ratio]').input_value() == '2-7-7' and pg.locator('select[name=fert_strength]').input_value() == 'Half strength', 'Edit page: ratio and strength')
    pg.close()

    # Location
    q = page((1280, 900))
    q.goto(f'{BASE}/#/winter'); q.wait_for_timeout(2600)
    check(q.locator('#place-name').inner_text() == home['name'], 'the Location button shows the home place to start with')
    q.locator('#place-btn').click(); q.wait_for_timeout(400)
    check(q.locator('dialog[open] h2').inner_text() == 'Location' and q.locator('dialog[open] input[data-plc]').count() >= 2, 'it opens the Location window with the places')
    q.locator(f'dialog[open] input[data-plc="{pid}"]').check(); q.wait_for_timeout(2600)
    check('Baraboo' in q.locator('#plc-msg').inner_text(), 'choosing a place says so in the window')
    check(q.locator('dialog[open] [data-act=plchome]').count() == 1, 'and offers to make it the home place')
    q.screenshot(path=f'{OUT}/fertloc-location-window.png')
    q.keyboard.press('Escape'); q.wait_for_timeout(400)
    check(q.locator('#place-name').inner_text() == 'Baraboo, WI', 'the button now says Baraboo, WI')
    check('Baraboo' in q.locator('h1 ~ p.muted').first.inner_text() and 'Round Rock' not in q.locator('#app').inner_text().split('Expected and tracked')[0], 'the Winter plan talks about Baraboo, not Round Rock')
    fz = q.locator('.fz-title')
    check(fz.count() == 0 or 'Baraboo' in fz.first.inner_text(), 'the frost banner names the place')
    check(json.loads(q.evaluate("JSON.stringify(localStorage.getItem('plantdb.place'))")) == str(pid), 'this browser remembers the choice')
    q.reload(); q.wait_for_timeout(2600)
    check(q.locator('#place-name').inner_text() == 'Baraboo, WI', 'still Baraboo after reloading')
    q.goto(f'{BASE}/#/weather'); q.wait_for_timeout(2600)
    check(q.locator('select[data-f=wxplace]').input_value() == str(pid), 'the Weather page shows the same place')
    q.select_option('select[data-f=wxplace]', str(home['id'])); q.wait_for_timeout(2600)
    check(q.locator('#place-name').inner_text() == home['name'], 'choosing on the Weather page changes the Location button too')
    check(q.evaluate("localStorage.getItem('plantdb.place')") is None, 'choosing home stores nothing (follows home if it changes)')
    q.goto(f'{BASE}/#/plant/P-024'); q.wait_for_timeout(2400)
    check(f"Winter in {home['name'].split(',')[0]}" in q.locator('#winter h2').inner_text(), 'plant page: Winter in <place>')
    # search and add from the window, with the keyboard
    q.keyboard.press('l'); q.wait_for_timeout(400)
    check(q.locator('dialog[open] h2').inner_text() == 'Location', 'the L key opens the Location window')
    q.fill('dialog[open] input[name=plcq]', 'Baraboo'); q.keyboard.press('Enter'); q.wait_for_timeout(1500)
    check(q.locator('dialog[open]').count() == 1 and q.locator('#plc-results li').count() == 2, 'Enter searches (the window stays open): 2 results')
    q.locator('#plc-results [data-act=plcadd]').nth(1).click(); q.wait_for_timeout(3000)
    check('Australia' in q.locator('#place-name').inner_text(), 'Add and use: the new place is in use')
    q.locator('#place-btn').click(); q.wait_for_timeout(400)
    q.locator('dialog[open] [data-act=plchome]').click(); q.wait_for_timeout(2600)
    newhome = [p for p in call('GET', '/api/meta')['places'] if p['is_home']][0]
    check('Australia' in newhome['name'] and 'home place for everyone' in q.locator('#plc-msg').inner_text(), 'Make home: it becomes the home place for everyone')
    call('PUT', f"/api/places/{home['id']}", {'is_home': True})                  # put things back
    q.keyboard.press('Escape'); q.close()
    # phones, largest text: the Location button fits and nothing scrolls sideways
    for w, size in ((390, '190'), (360, '160'), (390, '115')):
        p2 = page((w, 800), {'size': size, 'theme': 'dark'})
        for u in ('#/plants', '#/fertilizer', '#/weather'):
            p2.goto(f'{BASE}/{u}'); p2.wait_for_timeout(2200)
            over = p2.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            bw = p2.evaluate("(() => { const b = document.getElementById('place-btn').getBoundingClientRect(); return b.right <= innerWidth + 1 && b.left >= -1; })()")
            check(over <= 2 and bw, f'phone {w}px, text {size}%, {u}: no sideways scrolling ({over}px), Location button fits')
        if size == '190':
            p2.locator('#place-btn').click(); p2.wait_for_timeout(500)
            p2.screenshot(path=f'{OUT}/fertloc-phone-location.png')
        p2.close()
    b.close()
for e in errs: print('JS error:', e)
sys.exit(1 if fails or errs else 0)
