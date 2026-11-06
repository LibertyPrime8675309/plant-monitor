"""Checks 1.21.0: the library lists every species in the chosen list without a search, searches as you type, filters (kind,
family, state, common name, yours), sorts, shows cards or a table, loads more, fills in photos from iNaturalist (a stand-in in
dev/test/mock_vision.py) in the background, and opens a page for each species with photos, description, names,
classification, US states, lookalikes and links. Start the mock server with a fresh data folder (MOCK_TS=1), then:
python3 dev/test/library_check.py      Screenshots: dev/tmp/shots/library-*.png"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
LOCAL, TS, VIS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081', 'http://127.0.0.1:8090'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def get(u, h=None, base=LOCAL): return json.loads(urllib.request.urlopen(urllib.request.Request(base + u, headers=h or {})).read())
def put(u, body, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'X-Editor': 'Lib Test', **(h or {})}, method='PUT')
    try:
        with urllib.request.urlopen(req) as r: return r.status
    except urllib.error.HTTPError as e: return e.code
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
get('/api/me', E, TS); get('/api/me', V, TS)
r = get('/api/library/browse?scope=common')
check(r['total'] == 64 and len(r['results']) == 48, f'with no search the library lists the whole list, a page at a time ({len(r["results"])} of {r["total"]})')
r = get('/api/library/browse?scope=common&mine=species')
check([x['scientific_name'] for x in r['results']] == ['Monstera deliciosa'] and r['results'][0]['own_photo'], 'the "Only ones I have" filter, with your own photo for it')
ph = get('/api/library/photos?names=' + urllib.parse.quote('Lupinus texensis|Testia species01'))
check(ph['photos']['Lupinus texensis'] in ('pending', None) or isinstance(ph['photos']['Lupinus texensis'], dict), 'photos are asked for by name')
check(put('/api/library/settings', {'online': False}, V, TS) == 403, 'only the owner can turn the online photos off')
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '404' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Lib Test');localStorage.setItem('plantdb.morefilters','1')")
    pg.goto(LOCAL + '/#/today'); pg.wait_for_timeout(1000); pg.evaluate("localStorage.removeItem('plantdb.library')")
    pg.goto(LOCAL + '/#/library'); pg.wait_for_timeout(3000)
    cards = lambda: pg.locator('#lib-res .lib-card').count()
    check(cards() == 48 and 'Showing 48 of 64' in pg.inner_text('#lib-count'), 'the page lists the plants straight away, without a search')
    for lab in ('Search', 'Look in', 'Kind of plant', 'Family', 'Grows wild in', 'Show', 'Sort by', 'Show as', 'Your area', 'Only plants with a common name'):
        if pg.locator('.lib-filters label, #more-f label', has_text=lab).count() < 1: check(False, f'filter "{lab}" has a label')
    check(pg.locator('.lib-filters label, #more-f label').count() == 10, 'ten filters, each with a real label')
    pg.click('#lib-more'); pg.wait_for_timeout(1500)
    check(cards() == 64 and pg.locator('#lib-more').is_hidden() and pg.evaluate("document.activeElement.closest('.lib-card') !== null"), '"Show more" adds the rest, and moves the keyboard to the first new one')
    pg.wait_for_timeout(9000)
    n_img = pg.locator('#lib-res .lib-card .mat img').count()
    check(n_img >= 4, f'photos fill in from iNaturalist as they arrive, about one a second ({n_img} so far)')
    check(pg.locator('#lib-res .nophoto', has_text='No photo found').count() >= 1, 'a species with no photo says so')
    pg.screenshot(path=os.path.join(OUT, 'library-1-cards.png'))
    pg.fill('input[data-f=libq]', 'blue'); pg.wait_for_timeout(1200)
    check(cards() == 1 and 'Texas bluebonnet' in pg.inner_text('#lib-res') and 'matching "blue"' in pg.inner_text('#lib-count'), 'typing in the search box narrows the list as you type')
    pg.fill('input[data-f=libq]', ''); pg.wait_for_timeout(1000)
    pg.select_option('select[data-f=libkind]', 'fern'); pg.wait_for_timeout(1000)
    check(cards() == 12, f'Kind of plant: ferns ({cards()})')
    pg.select_option('select[data-f=libkind]', ''); pg.fill('input[data-f=libfamily]', 'Araceae'); pg.locator('input[data-f=libfamily]').dispatch_event('change'); pg.wait_for_timeout(1000)
    check(cards() == 1 and 'Monstera' in pg.inner_text('#lib-res'), 'Family: Araceae')
    pg.fill('input[data-f=libfamily]', ''); pg.locator('input[data-f=libfamily]').dispatch_event('change')
    pg.select_option('select[data-f=libstate]', 'Texas'); pg.wait_for_timeout(1000)
    check(cards() == 33, f'Grows wild in Texas ({cards()})')
    pg.check('input[data-f=libcommon]'); pg.wait_for_timeout(1000)
    n = cards(); check(0 < n < 33 and all(x.strip() for x in pg.locator('#lib-res .lib-card .sci').all_inner_texts()), f'Only plants with a common name ({n})')
    pg.reload(); pg.wait_for_timeout(3000)
    check(cards() == n and pg.locator('select[data-f=libstate]').input_value() == 'Texas', 'the filters are remembered')
    pg.click('#lib-clear'); pg.wait_for_timeout(2500)
    check(cards() == 48 and pg.locator('select[data-f=libstate]').input_value() == '', '"Clear search and filters" starts over')
    pg.select_option('select[data-f=libview]', 'table'); pg.wait_for_timeout(1000)
    rows = pg.locator('#lib-res table.lib-tbl tbody tr').count()
    check(rows == 48 and pg.locator('#lib-res table th[scope=col]').count() == 7, f'"Show as: a table" gives a table with column headings ({rows} rows)')
    pg.screenshot(path=os.path.join(OUT, 'library-2-table.png'))
    pg.select_option('select[data-f=libview]', 'cards'); pg.wait_for_timeout(800)
    # a species page
    pg.fill('input[data-f=libq]', 'monstera'); pg.wait_for_timeout(1200)
    pg.locator('#lib-res .sheet-link').first.click(); pg.wait_for_timeout(5000)
    check(pg.evaluate('location.hash') == '#/species/Monstera%20deliciosa' and pg.locator('#sub-nav a[href="#/library"][aria-current=page]').count() == 1, 'a card opens the species page')
    t = pg.inner_text('main')
    check('Swiss cheese plant' in pg.locator('h1').inner_text() or 'Swiss cheese plant' in t, 'it shows the common name from iNaturalist')
    check('A test plant & its relatives' in t and 'From Wikipedia' in t, 'the short description, credited to Wikipedia')
    import re as _re
    gm = _re.search(r'1 of (\d+)', pg.inner_text('#sp-gallery')); gn = int(gm.group(1)) if gm else 0
    check(pg.locator('#sp-gallery figure img').count() == 1 and 'Your plant P-049' in pg.inner_text('#sp-gallery') and gn >= 6,
          f'a photo gallery: your own photos first (P-049, P-084, P-088 and the Thai Constellations), then iNaturalist photos ({gn})')
    seen = ''
    for _ in range(gn - 1):
        pg.click('[data-act=spph][data-d="1"]'); pg.wait_for_timeout(200); seen += pg.inner_text('#sp-gallery')
        if 'Test Person 0' in seen: break
    check('Test Person 0' in seen and 'CC BY-NC' in seen and 'CC-BY-NC' not in seen, 'each iNaturalist photo names its photographer and licence')
    for h in ('Names', 'Classification', 'Where it grows wild in the US', 'Looks like', 'More about it elsewhere'):
        check(pg.locator('h2', has_text=h).count() == 1, f'section "{h}"')
    check('P-049' in pg.inner_text('.sp-yours'), 'your plants of this species are listed')
    pg.screenshot(path=os.path.join(OUT, 'library-3-species.png'), full_page=True)
    pg.click('.sp-cls a:has-text("Araceae")'); pg.wait_for_timeout(2500)
    check(pg.evaluate('location.hash').startswith('#/library') and pg.locator('input[data-f=libfamily]').input_value() == 'Araceae', 'the family in the classification links to the library filtered to that family')
    # a phone, largest text
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Lib Test');localStorage.setItem('plantdb.morefilters','1');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    for u in ('/#/library', '/#/species/Monstera%20deliciosa'):
        ph.goto(LOCAL + u); ph.wait_for_timeout(3500)
        check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'{u}: no sideways scrolling on a phone with the largest text')
    ph.screenshot(path=os.path.join(OUT, 'library-4-phone.png'))
    # turning the online photos off
    put('/api/library/settings', {'online': False})
    pg.goto(LOCAL + '/#/library'); pg.wait_for_timeout(1500)
    calls = len(get('/mock/inat/calls', base=VIS))
    pg.fill('input[data-f=libq]', 'Testia species5'); pg.wait_for_timeout(4000)
    check(len(get('/mock/inat/calls', base=VIS)) == calls, 'with online photos off, nothing is looked up')
    put('/api/library/settings', {'online': True})
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.goto(TS + '/#/species/Monstera%20deliciosa'); vw.wait_for_timeout(3000)
    check(vw.locator('h2', has_text='Classification').count() == 1 and not vw.locator('[data-act=spnew]').is_visible(), 'a viewer can read species pages, without "Add to my plants"')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
