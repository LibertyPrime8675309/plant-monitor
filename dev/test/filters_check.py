"""Checks 1.16.2: the Plants page filters. Show (active, active and archived, archived only) and Location are in the filter
row, archived plants say so on their card, the counts follow, Previous / Next follow the same choices, and the choices are
remembered. Start the mock server with a fresh data folder first, then:  python3 dev/test/filters_check.py [base]
Screenshots: dev/tmp/shots/filters-*.png"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
get = lambda u: json.loads(urllib.request.urlopen(BASE + u).read())
act, allp = get('/api/plants'), get('/api/plants?status=all')
arch = [p for p in allp if p['status'] == 'archived']
check(len(arch) >= 2 and len(allp) == len(act) + len(arch) and all('status' in p for p in allp), f'the list can include archived plants ({len(act)} active, {len(arch)} archived)')
porch = [p for p in act if p['site'] == 'Covered porch']
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Filter Test')")
    pg.goto(BASE + '/'); pg.wait_for_timeout(2500)
    check(pg.locator('.filters select[data-f=status]').count() == 1 and pg.locator('.filters select[data-f=site]').count() == 1 and pg.locator('[data-f=archived]').count() == 0,
          'Show and Location are in the filter row, and the old checkbox at the bottom is gone')
    n = lambda: pg.locator('#grid .sheet').count()
    check(n() == len(act) and 'archived plants are hidden' in pg.inner_text('main'), f'by default only active plants show ({n()}), with a note about the archived ones')
    pg.select_option('select[data-f=status]', 'all'); pg.wait_for_timeout(600)
    check(n() == len(allp) and pg.locator('#grid .tag-arch').count() == len(arch), f'"Active and archived" shows both, and archived cards say Archived ({n()})')
    pg.select_option('select[data-f=status]', 'archived'); pg.wait_for_timeout(600)
    check(n() == len(arch) and pg.locator('h1').first.inner_text() == 'Archived plants', 'Archived only shows just the archived plants')
    pg.screenshot(path=os.path.join(OUT, 'filters-1-archived.png'))
    pg.select_option('select[data-f=status]', 'active'); pg.select_option('select[data-f=site]', 'Covered porch'); pg.wait_for_timeout(600)
    check(n() == len(porch) and f'{len(porch)} of {len(act)} active plants shown' in pg.inner_text('#count'), f'Location narrows to the covered porch ({n()})')
    pg.reload(); pg.wait_for_timeout(2500)
    check(pg.locator('select[data-f=site]').input_value() == 'Covered porch' and n() == len(porch), 'the choices are remembered')
    pg.select_option('select[data-f=site]', ''); pg.select_option('select[data-f=status]', 'all'); pg.wait_for_timeout(500)
    pg.goto(BASE + '/#/plant/' + arch[0]['code']); pg.wait_for_timeout(2500)
    check('archived included' in pg.inner_text('#pn-sum') and pg.locator('#pn-pos').inner_text().startswith('plant '), 'Previous and Next include archived plants when the filter does')
    check(pg.locator('#pn-filters select[data-f=status]').count() == 1 and pg.locator('#pn-filters select[data-f=site]').count() == 1, 'the Previous / Next panel has the same filters')
    pg.goto(BASE + '/'); pg.wait_for_timeout(1500); pg.click('[data-act=clearfilters]') if pg.locator('[data-act=clearfilters]').count() else None
    # ---- 1.17.0: more filters
    pg.goto(BASE + '/'); pg.wait_for_timeout(2000)
    pg.select_option('select[data-f=status]', 'active'); pg.wait_for_timeout(300)
    check(pg.locator('#more-f select[data-f=more]').count() == 9, 'More filters has 9 choices (Summer here added by proto/summer-heat)')
    if not pg.locator('#more-f').evaluate('d => d.open'): pg.click('#more-f > summary')
    def more(key, val):
        pg.select_option(f'#more-f select[data-key={key}]', val); pg.wait_for_timeout(700); return n()
    full = [p for p in act if (p.get('dli_low') or 0) >= 25]
    check(more('light', 'full') == len(full) and len(full) > 5, f'Light needs: full sun ({len(full)})')
    check('(1 on)' in pg.inner_text('#more-f > summary'), 'the fold-out says how many are on')
    more('light', '')
    safe = [p for p in act if p.get('pet_safety') == 'Safe for pets (ASPCA)']
    check(more('pets', 'safe') == len(safe) and len(safe) > 5, f'Pets: safe for pets ({len(safe)})')
    more('pets', '')
    tender, hardy = more('hardy', 'tender'), more('hardy', 'hardy')
    check(tender > 20 and hardy > 5, f'Winter here: {hardy} hardy, {tender} not hardy')
    more('hardy', '')
    w = get('/api/water'); due = {x['code'] for x in w['plants'] if x['state'] == 'due'}
    got = more('care', 'water')
    check(got == len(due & {p['code'] for p in act}) and got > 0, f'Care today: water due ({got})')
    more('care', '')
    check(more('grow', 'yes') == 0 and 'No plants match' in pg.inner_text('#grid'), 'Grow light: none are under a spot yet, and the page says so')
    more('grow', '')
    check(more('leaf', 'Succulent or cactus') == len([p for p in act if p.get('leaf_type') == 'Succulent or cactus']), 'Leaf type works')
    more('leaf', '')
    check(more('photo', 'none') == len([p for p in act if not p.get('photo_count')]), 'Photos: no photo yet')
    more('photo', '')
    pg.goto(BASE + '/#/plant/P-020'); pg.wait_for_timeout(2000)
    check(pg.locator('#pn-filters select[data-f=more]').count() == 9, 'the Previous / Next panel has the same 9 filters')
    pg.goto(BASE + '/#/plant/P-020'); pg.wait_for_timeout(1500)
    check('Toxic to pets' in pg.inner_text('#about'), 'the fiddle-leaf fig page says it is toxic to pets')
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.add_init_script("localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    ph.goto(BASE + '/'); ph.wait_for_timeout(2500)
    check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'on a phone with the largest text there is no sideways scrolling')
    ph.screenshot(path=os.path.join(OUT, 'filters-2-phone.png'))
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails))
sys.exit(1 if fails else 0)
