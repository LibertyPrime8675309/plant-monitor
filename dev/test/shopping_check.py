"""Checks 1.30.0: Shopping and quicker page changes. Garden supplies can be watched beside wishlist plants, with the price per
quart, pound or square foot read from each listing; the stores near each home have their address, phone, hours and what they
carry (batch B5), with notes and an OpenStreetMap look-up; buttons on Pots and trays, Fertilizer and the cold-night checklist
start watching; pages opened before show at once and are checked again; the Debug window lists page timings; answers are sent
squeezed. Start the mock server with a fresh data folder (MOCK_TS=1), then:
python3 dev/test/shopping_check.py      Screenshots: dev/tmp/shots/shopping-*.png"""
import gzip, json, os, sqlite3, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL, TS, MOCK = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081', 'http://127.0.0.1:8090'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
DB = os.path.join(HERE, '..', 'tmp', 'data', 'plants.db')
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Shopping Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)
def run_check():
    call('POST', '/api/wishlist/check', {})
    for _ in range(80):
        time.sleep(0.5)
        if not call('GET', '/api/wishlist/check')[1]['busy']: return

# batch B5: store details near both homes, and two photos ticked off
sh = {s['key']: s for s in call('GET', '/api/shops')[1]['shops']}
check(sh['roundrockgc']['address'].startswith('901 Sam Bass') and sh['roundrockgc']['phone'] == '512-255-3353' and 'fert' in sh['roundrockgc']['carries'],
      'Round Rock Garden Center has its address, phone and what it carries')
nc = [s for s in sh.values() if s['home_name'] == 'Nevada City, CA']
check(len(nc) == 6 and sh['peacefulvalley']['online'] == 1 and sh['peacefulvalley']['hours'].startswith('Mon to Sat 9'), f'6 stores near Nevada City, Peaceful Valley with its hours ({len(nc)})')
c = sqlite3.connect(DB)
check(c.execute("SELECT COUNT(*) FROM to_photograph WHERE done=1 AND (label LIKE 'Third extra palm%' OR label LIKE 'Any plants not yet%')").fetchone()[0] == 2, 'the third palm and "any plants not yet photographed" are ticked off')
c.close()

# supplies
check(call('PUT', '/api/wishlist', {'name': 'Pumice, 1/4 in', 'kind': 'soil'})[0] == 400, 'a kind that is not on the list is refused')
check(call('PUT', '/api/wishlist', {'name': 'Perlite', 'kind': 'amend'}, V, TS)[0] == 403, 'someone who can only view cannot add one')
call('PUT', '/api/wishlist', {'name': 'Pumice, 1/4 in', 'kind': 'amend', 'search_words': 'pumice', 'max_price': 1.2, 'price_per': 'unit', 'alert_stock': True})
call('PUT', '/api/wishlist', {'name': 'Frost cloth', 'kind': 'frost', 'search_words': 'frost blanket', 'source': 'frost'})
call('PUT', '/api/wishlist', {'name': 'Lupinus texensis', 'common_name': 'Texas bluebonnet'})
check(call('PUT', '/api/wishlist', {'name': 'Lupinus texensis', 'rename': 'Bluebonnet'})[0] == 400, 'a wishlist plant keeps its species name')
check(call('PUT', '/api/wishlist', {'name': 'Frost cloth', 'rename': 'Frost cloth, 10 x 12 ft'})[0] == 200, 'a supply can be renamed')
for s in sh.values():
    if s['key'] != 'snoopers': call('PUT', '/api/shops', {'key': s['key'], 'enabled': False})
call('PUT', '/api/shops', {'key': 'snoopers', 'url': MOCK + '/mock/shop/page'})
call('POST', '/api/shops', {'name': 'Test Shopify', 'url': 'http://127.0.0.1:8090/'})
run_check()
d = call('GET', '/api/shopping?near=all')[1]
it = {w['name']: w for w in d['items']}
pb = it['Pumice, 1/4 in']['offers']['best']
check(pb and pb['unit'] and pb['unit']['unit'] == 'quart' and abs(pb['unit']['per'] - 13.99 / (0.5 * 25.71)) < 0.01, f'pumice: $13.99 for 0.5 cu ft is about $1.09 a quart ({pb and pb["unit"]})')
fb = it['Frost cloth, 10 x 12 ft']['offers']['best']
check(fb and fb['unit']['unit'] == 'square foot' and abs(fb['unit']['per'] - 18.99 / 120) < 0.01, 'frost cloth: $18.99 for 10 x 12 ft is about 16 cents a square foot')
pa = [a for a in d['alerts'] if a['wish'] == 'Pumice, 1/4 in']
check(len(pa) == 1 and 'a quart' in pa[0]['text'] and '$1.20 a quart' in pa[0]['text'], 'the price alert is per quart, as asked: ' + (pa[0]['text'] if pa else 'none'))
check([k['key'] for k in d['kinds']][:3] == ['plant', 'pots', 'mix'] and len(d['kinds']) == 9, 'nine kinds, wishlist plants first')
ncid = [h['id'] for h in d['homes'] if h['name'].startswith('Nevada')][0]
bb_all = it['Lupinus texensis']['offers']
bb_nc = {w['name']: w for w in call('GET', f'/api/shopping?near={ncid}')[1]['items']}['Lupinus texensis']['offers']
check(bb_all['best']['shop'] == 'snoopers' and bb_nc['best']['shop'] != 'snoopers' and bb_nc['shops'] == bb_all['shops'] - 1,
      'choosing Nevada City leaves out the Round Rock nursery, and keeps the online stores')
# stores
st = call('GET', '/api/shops/custom-test-shopify')[1]
check(any(o['wish'] == 'Pumice, 1/4 in' and o['unit'] for o in st['listings']), 'a store page lists what you watch that it has, with the price per unit')
check(call('POST', '/api/stores/weiss/notes', {'text': 'They had perlite in bags.'}, V, TS)[0] == 403, 'someone who can only view cannot add a note')
call('POST', '/api/stores/weiss/notes', {'text': 'They had perlite in bags.'}, E, TS)
w = call('GET', '/api/shops/weiss')[1]
check(w['notes'] and w['notes'][0]['created_by'] == 'Ethan', 'a note about a store is kept, with who wrote it')
r = call('POST', '/api/stores/weiss/lookup', {})[1]
check('hours' in r.get('filled', []) and r['hours'].startswith('Mo-Sa') and r['miles'] is not None and r['miles'] < 10,
      f'looking it up on OpenStreetMap fills in its hours and map position, and the distance shows ({r.get("filled")}, {r.get("miles")} miles)')
check(r['phone'] == '(530) 273-5814', 'and leaves the phone it already had')
check(call('PUT', '/api/stores/weiss/details', {'home_id': 9999})[0] == 400, 'a store must be near one of your homes')
r = call('PUT', '/api/stores/weiss/details', {'carries': ['plant', 'pots', 'nonsense'], 'hours': 'Every day 8 to 5'})[1]
check(r['carries'] == ['plant', 'pots'] and r['hours'] == 'Every day 8 to 5' and 'Typed in' in r['details_src'], 'details can be typed in, and what it carries chosen')
r = call('PUT', '/api/stores/weiss/details', {'address': '1 New Street, Grass Valley, CA'})[1]
check(r['lat'] is None, 'a new address clears the old map position (it is found again)')
check(call('PUT', '/api/stores/weiss/details', {'hours': 'x'}, V, TS)[0] == 403, 'someone who can only view cannot change them')
# squeezed answers and timings
req = urllib.request.Request(LOCAL + '/api/plants?status=all', headers={'Accept-Encoding': 'gzip'})
with urllib.request.urlopen(req) as x:
    raw = x.read(); enc_ = x.headers.get('Content-Encoding'); took = x.headers.get('X-Took-Ms')
check(enc_ == 'gzip' and len(json.loads(gzip.decompress(raw))) > 50 and took is not None, f'answers are sent squeezed ({len(raw):,} bytes), with how long they took')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1600, 'height': 1000}, extra_http_headers=E)
    ctx.add_init_script("localStorage.setItem('plantdb.editor','Ethan')")
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(TS + '/#/shopping'); pg.wait_for_timeout(3000)
    check(pg.locator('#sub-nav a[data-nav=shopping][aria-current=page]').count() == 1, 'Shopping is a page under Discover')
    check(pg.locator('fieldset.buy-kinds-r').is_visible() and not pg.locator('label.buy-kinds-s').is_visible(), 'on a wide screen the kinds are buttons')
    n_all = pg.locator('.buy-item').count()
    pg.locator('fieldset.buy-kinds-r label', has_text='Amendments').click(); pg.wait_for_timeout(1500)
    check(pg.locator('.buy-item').count() == 1 and 'Pumice' in pg.locator('.buy-item').inner_text(), f'choosing Amendments shows only the pumice (of {n_all})')
    check('$1.09 a quart' in pg.locator('.buy-item').inner_text(), 'with its price per quart')
    pg.screenshot(path=os.path.join(OUT, 'shopping-1-page.png'), full_page=True)
    pg.locator('[data-act=buynew]').click(); pg.wait_for_timeout(500)
    pg.fill('#dlg [name=name]', 'Worm castings'); pg.select_option('#dlg [name=kind]', 'amend'); pg.fill('#dlg [name=max_price]', '1.5')
    pg.locator('#dlg [name=price_per][value=unit]').check(); pg.locator('#dlg button[value=ok]').click(); pg.wait_for_timeout(2000)
    wc = {w['name']: w for w in call('GET', '/api/shopping')[1]['items']}.get('Worm castings')
    check(wc and wc['kind'] == 'amend' and wc['price_per'] == 'unit' and wc['max_price'] == 1.5, 'Add something to watch adds it, with a price per unit to watch for')
    pg.goto(TS + '/#/store/peacefulvalley'); pg.wait_for_timeout(2500)
    check(pg.locator('a[href="tel:5302724769"]').count() == 1 and pg.locator('a[href="tel:8887841722"]').count() == 1, 'the store page has its phone numbers as links you can tap to call')
    pg.locator('[data-act=storeedit]').click(); pg.wait_for_timeout(500)
    pg.fill('#dlg [name=hours]', 'Mon to Sat 9 am to 5 pm'); pg.locator('#dlg button[value=ok]').click(); pg.wait_for_timeout(2000)
    check(call('GET', '/api/shops/peacefulvalley')[1]['hours'] == 'Mon to Sat 9 am to 5 pm', 'Edit details saves the hours')
    pg.fill('form[data-form=storenote] textarea', 'Pumice in 2 cu ft bags.'); pg.locator('form[data-form=storenote] button[type=submit]').click(); pg.wait_for_timeout(2000)
    check('Pumice in 2 cu ft bags.' in pg.locator('main').inner_text(), 'a note added on the page shows there')
    pg.screenshot(path=os.path.join(OUT, 'shopping-2-store.png'), full_page=True)
    pg.goto(TS + '/#/shopping/stores'); pg.wait_for_timeout(2500)
    check(pg.locator('h2', has_text='Near Nevada City').count() == 1 and pg.locator('h2', has_text='Online').count() == 1, 'the Stores page groups them by home, then online')
    pg.select_option('[data-act=storecarries]', 'frost'); pg.wait_for_timeout(1500)
    check(pg.locator('main tbody tr', has_text='Peaceful Valley').count() == 1 and pg.locator('main tbody tr', has_text='Weiss').count() == 0, 'and can show only the stores that carry frost cloth')
    pg.screenshot(path=os.path.join(OUT, 'shopping-3-stores.png'), full_page=True)
    # the watch buttons on other pages
    cid = call('POST', '/api/containers', {'kind': 'pot', 'name': '8 in terracotta', 'shape': 'circle', 'dia_in': 8, 'material': 'Terracotta', 'qty': 2})[1]['id']
    pg.goto(TS + '/#/pots'); pg.wait_for_timeout(2500)
    pg.locator(f'#ct-{cid} [data-act=buywatch]').click(); pg.wait_for_timeout(2500)
    pt = {w['name']: w for w in call('GET', '/api/shopping')[1]['items']}.get('8 in terracotta')
    check(pt and pt['kind'] == 'pots' and pt['source'] == f'pots:{cid}' and 'Terracotta pot' in pt['search_words'] and pg.evaluate('location.hash') == '#/shopping',
          '"Watch for more" on a pot starts watching it on Shopping')
    pg.goto(TS + '/#/frost'); pg.wait_for_timeout(2500)
    check(pg.locator('[data-act=buywatch][data-kind=frost]').count() == 1, 'the cold-night checklist has a button to watch for frost cloth')
    # quicker pages: a page opened before shows from what was saved, then is checked again
    pg.goto(TS + '/#/lights'); pg.wait_for_timeout(2500); pg.goto(TS + '/#/shopping'); pg.wait_for_timeout(1500)
    pg.evaluate("location.hash = '#/lights'"); pg.wait_for_timeout(1500)
    pg.evaluate("location.hash = '#/shopping'"); pg.wait_for_timeout(1500)
    T = pg.evaluate("JSON.parse(localStorage.getItem('plantdb.timings') || '[]')")
    check(T and T[0]['page'] == '#/shopping' and T[0]['saved'] > 0, f'a page opened before shows from the saved copy ({T[0]["saved"] if T else 0} answers), then is checked again')
    check(pg.evaluate("Object.keys(JSON.parse(localStorage.getItem('plantdb.prefetch') || '{}')).length") >= 3, 'the answers each page needs are learned, to fetch ahead')
    pg.goto(TS + '/#/settings'); pg.wait_for_timeout(2000); pg.locator('#debug-btn').click(); pg.wait_for_timeout(800)
    check(pg.locator('#dlg .dbg-times tbody tr').count() >= 3, 'the Debug window lists the page timings')
    pg.screenshot(path=os.path.join(OUT, 'shopping-4-debug.png'), full_page=True)
    pg.keyboard.press('Escape')
    # viewer
    v = b.new_context(viewport={'width': 1280, 'height': 900}, extra_http_headers=V).new_page()
    v.goto(TS + '/#/store/peacefulvalley'); v.wait_for_timeout(3000)
    check(v.locator('[data-act=storeedit]').count() == 0 and v.locator('form[data-form=storenote]').count() == 0 and 'Pumice in 2 cu ft bags.' in v.locator('main').inner_text(),
          'someone who can only view sees the store and its notes, but cannot change them')
    # phone
    ph = b.new_context(viewport={'width': 384, 'height': 740}, is_mobile=True, has_touch=True, service_workers='block', extra_http_headers=E)
    ph.add_init_script("localStorage.setItem('plantdb.editor','Ethan');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    q = ph.new_page(); q.on('pageerror', lambda e: errs.append(str(e)))
    for h in ('#/shopping', '#/store/peacefulvalley', '#/shopping/stores'):
        q.goto(TS + '/' + h); q.wait_for_timeout(3000)
        check(not q.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), f'{h} on a phone with the largest text does not scroll sideways')
        if h == '#/shopping':
            check(q.locator('label.buy-kinds-s').is_visible() and not q.locator('fieldset.buy-kinds-r').is_visible(), 'on a phone the kinds are one dropdown')
            q.screenshot(path=os.path.join(OUT, 'shopping-5-phone.png'), full_page=False)
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All shopping checks passed' if not fails else f'{len(fails)} shopping check(s) failed'))
raise SystemExit(1 if fails else 0)
