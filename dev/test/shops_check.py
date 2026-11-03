"""Checks 1.27.0: prices and stock for the wishlist. Shops are read in the background: a Shopify store and a WooCommerce store
(found out on the first check), a nursery page with no online store, and eBay and Etsy's search services (stand-ins in
dev/test/mock_vision.py). Listings are kept with their past prices, and alerts come when something is in stock or at or under the
price set (again only if it drops further). Only the owner changes the shops and keys. Start the mock server with a fresh data
folder (MOCK_TS=1), then:
python3 dev/test/shops_check.py      Screenshots: dev/tmp/shots/shops-*.png"""
import json, os, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL, TS, MOCK = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081', 'http://127.0.0.1:8090'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Shops Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)
def run_check():
    st, _ = call('POST', '/api/wishlist/check', {})
    for _ in range(60):
        time.sleep(0.5)
        if not call('GET', '/api/wishlist/check')[1]['busy']: return st
    return 0
BB = 'Lupinus texensis'

call('PUT', '/api/wishlist', {'name': BB, 'common_name': 'Texas bluebonnet', 'max_price': 5, 'alert_stock': True})
call('PUT', '/api/wishlist', {'name': 'Monstera deliciosa', 'common_name': 'Swiss cheese plant', 'alert_stock': True})
check(call('PUT', '/api/wishlist', {'name': BB, 'max_price': 'cheap'})[0] == 400, 'a price to watch for must be a number')
sh = call('GET', '/api/shops')[1]
names = [s['name'] for s in sh['shops']]
check(len(names) == 16 and {"Snooper's Nursery", 'Barry Hill Garden Center', 'Cantu Imports', "Mind's Eye Plants", 'Round Rock Garden Center', 'eBay', 'Etsy'} <= set(names),
      f'16 shops to start with, including the local nurseries ({len(names)})')
check(sh['hours'] == '12', 'they are checked every 12 hours unless changed')
check(call('PUT', '/api/shops', {'key': 'burpee', 'enabled': False}, V, TS)[0] == 403 and call('PUT', '/api/shops/keys', {'shop': 'etsy', 'etsy_key': 'x'}, V, TS)[0] == 403,
      'someone who can only view cannot change the shops or the keys')
check(call('POST', '/api/wishlist/check', {}, V, TS)[0] == 403, 'or start a check')
for s in sh['shops']:
    if s['key'] not in ('ebay', 'etsy', 'snoopers'): call('PUT', '/api/shops', {'key': s['key'], 'enabled': False})
call('PUT', '/api/shops', {'key': 'snoopers', 'url': MOCK + '/mock/shop/page'})
check(call('POST', '/api/shops', {'name': 'Test Shopify', 'url': 'http://127.0.0.1:8090/'})[0] == 200, 'the owner can add a shop by its address')
call('POST', '/api/shops', {'name': 'Test Woo', 'url': 'http://localhost:8090/', 'local': True})
check(call('POST', '/api/shops', {'name': 'Bad', 'url': 'not a link'})[0] == 400, 'a shop needs a real web address')

# eBay and Etsy without keys, then with them
run_check()
sh = {s['key']: s for s in call('GET', '/api/shops')[1]['shops']}
check('Needs' in (sh['ebay']['status'] or '') and 'Needs' in (sh['etsy']['status'] or ''), 'without keys eBay and Etsy say they need them')
check(sh['custom-test-shopify']['platform'] == 'shopify' and sh['custom-test-woo']['platform'] == 'woo', 'a new shop is found to be a Shopify or WooCommerce store on its first check')
check('page' in (sh['snoopers']['status'] or '') and not sh['snoopers']['error'], 'a nursery with no online store has its page read for the names')
call('PUT', '/api/shops/keys', {'shop': 'ebay', 'ebay_app_id': 'app-1', 'ebay_cert_id': 'cert-1'})
call('PUT', '/api/shops/keys', {'shop': 'etsy', 'etsy_key': 'etsy-1'})
check(call('GET', '/api/shops')[1]['have_ebay'] is True and 'cert-1' not in json.dumps(call('GET', '/api/shops')[1]), 'keys are saved and never sent back')
run_check()
sh = {s['key']: s for s in call('GET', '/api/shops')[1]['shops']}
check(not sh['ebay']['error'] and not sh['etsy']['error'], 'with keys eBay and Etsy are searched')
offers = call('GET', '/api/wishlist/offers?name=Lupinus%20texensis')[1]['offers']
by = {o['shop']: o for o in offers}
check(by.get('custom-test-shopify', {}).get('price') == 4.95 and by['custom-test-shopify']['available'] == 1, 'the Shopify store: $4.95, in stock (cheapest size)')
check(by.get('custom-test-woo', {}).get('price') == 7.99, 'the WooCommerce store: $7.99')
check(by.get('snoopers', {}).get('price') == 2.5, "the nursery page: the line naming it, with its price ($2.50); script text is ignored")
check(by.get('ebay', {}).get('price') == 9.5 and not any('poster' in o['title'] for o in offers), 'eBay: the plant, not the poster that only says "bluebonnet"')
check(by.get('etsy', {}).get('price') == 6.5, 'Etsy: $6.50')
wl = call('GET', '/api/wishlist')[1]
bb = next(w for w in wl['wishlist'] if w['name'] == BB)
check(bb['offers']['best']['price'] == 2.5 and bb['offers']['shops'] == 5, 'the wishlist shows the cheapest and how many shops have it')
al = wl['alerts']
bba = [a for a in al if a['wish'] == BB]
check(len(bba) == 2 and bba[1]['kind'] == 'price' and '$2.50 at Snooper' in bba[1]['text'] and '(and 1 more)' in bba[1]['text'] and 'In stock at 3 shops' in bba[1]['text'],
      'one alert per check: the cheapest at or under $5, and the 3 stores that had it on the first check')
check(len(bba) == 2 and bba[0]['kind'] == 'stock' and 'In stock at 2 shops: Etsy $6.50, eBay $9.50' in bba[0]['text'], 'then one for eBay and Etsy, once their keys were saved')
check(not [a for a in al if a['wish'] == 'Monstera deliciosa'], 'no alert for something out of stock')
run_check()
check(len(call('GET', '/api/wishlist/alerts')[1]['alerts']) == len(al), 'checking again does not repeat them')
urllib.request.urlopen(urllib.request.Request(MOCK + '/mock/shop/set', data=json.dumps({'bluebonnet_price': '3.99'}).encode(), headers={'Content-Type': 'application/json'}, method='POST'))
run_check()
al2 = call('GET', '/api/wishlist/alerts')[1]['alerts']
check(len(al2) == len(al) + 1 and '$3.99' in al2[0]['text'] and 'In stock' not in al2[0]['text'], 'a lower price gives a new alert, about that price only')
hist = next(o for o in call('GET', '/api/wishlist/offers?name=Lupinus%20texensis')[1]['offers'] if o['shop'] == 'custom-test-shopify')['history']
check([h['price'] for h in hist] == [4.95, 3.99], 'and the old price is kept in its history')
urllib.request.urlopen(urllib.request.Request(MOCK + '/mock/shop/set', data=json.dumps({'bluebonnet_stock': False}).encode(), headers={'Content-Type': 'application/json'}, method='POST'))
run_check()
urllib.request.urlopen(urllib.request.Request(MOCK + '/mock/shop/set', data=json.dumps({'bluebonnet_stock': True}).encode(), headers={'Content-Type': 'application/json'}, method='POST'))
run_check()
al3 = call('GET', '/api/wishlist/alerts')[1]['alerts']
check(len(al3) == len(al2) + 1 and al3[0]['kind'] == 'stock', 'back in stock after selling out gives a new alert')
check(call('POST', '/api/wishlist/alerts', {'id': al3[0]['id']}, V, TS)[0] == 403, 'someone who can only view cannot dismiss alerts')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Shops Test');localStorage.setItem('plantdb.display',JSON.stringify({navopen:'0'}))")
    pg.goto(LOCAL + '/#/today'); pg.wait_for_timeout(2500)
    check(pg.locator('#today-wish').count() == 1 and 'Texas bluebonnet' in pg.locator('#today-wish').inner_text(), 'Today shows the wishlist alerts')
    nb = pg.locator('#main-nav a[data-nav=library] .nav-badge')
    check(nb.count() == 1 and f'{len(al3)} wishlist alert' in nb.inner_text(), 'and the top bar says how many, beside Library')
    pg.goto(LOCAL + '/#/wishlist'); pg.wait_for_timeout(2500)
    t = pg.locator('main').inner_text()
    check('Cheapest now: $2.50' in t and 'Alerts (' in t, 'the wishlist shows the cheapest listing and the alerts')
    check(pg.locator('.wl-shops input[data-act=shopon]').count() >= 16, 'the owner sees every shop with an On box')
    pg.locator('details.wl-offers').first.locator('summary').click(); pg.wait_for_timeout(1200)
    check('$3.99' in pg.locator('.wl-offers-box').first.inner_text(), 'opening "Every listing found" shows them with past prices')
    pg.screenshot(path=os.path.join(OUT, 'shops-1-wishlist.png'), full_page=True)
    pg.locator('[data-act=wldismiss][data-id=all]').first.click(); pg.wait_for_timeout(1500)
    check(not call('GET', '/api/wishlist/alerts')[1]['alerts'], 'Dismiss them all clears them')
    pg.locator('[data-act=wledit]').first.click(); pg.wait_for_timeout(400)
    check(pg.locator('#dlg [name=max_price]').count() == 1 and pg.locator('#dlg [name=search]').count() == 1, 'Edit has the search words and the alerts')
    pg.keyboard.press('Escape')
    b.close()
    ph = p.chromium.launch().new_context(viewport={'width': 384, 'height': 740}, is_mobile=True, has_touch=True, service_workers='block')
    ph.add_init_script("localStorage.setItem('plantdb.editor','Shops Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    q = ph.new_page(); q.on('pageerror', lambda e: errs.append(str(e)))
    q.goto(LOCAL + '/#/wishlist'); q.wait_for_timeout(3000)
    check(not q.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'on a phone with the largest text nothing scrolls sideways')
    q.screenshot(path=os.path.join(OUT, 'shops-2-phone.png'), full_page=True)
    v = p.chromium.launch().new_context(viewport={'width': 1280, 'height': 900}, extra_http_headers=V).new_page()
    v.goto(TS + '/#/wishlist'); v.wait_for_timeout(3000)
    check(not v.locator('[data-act=wlcheck]').is_visible() and v.locator('.wl-shops input[data-act=shopon]').count() == 0, 'someone who can only view sees the prices, but no buttons')

# search words start the listings again
call('PUT', '/api/wishlist', {'name': 'Monstera deliciosa', 'search_words': 'Pothos Golden'})
run_check()
mo = call('GET', '/api/wishlist/offers?name=Monstera%20deliciosa')[1]['offers']
check([o['title'] for o in mo if not o['gone']] == ['Pothos Golden'], 'own search words replace the names, and the old listings are dropped')
check(call('DELETE', '/api/shops?key=burpee')[0] == 404 and call('DELETE', '/api/shops?key=custom-test-woo')[0] == 200, 'only a shop you added can be removed')
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All shops checks passed' if not fails else f'{len(fails)} shops check(s) failed'))
raise SystemExit(1 if fails else 0)
