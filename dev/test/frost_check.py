"""Checks the frost alert and the cold-night checklist. Start the mock server with cold weather first:
  MOCK_BASE_F=40 DATA_DIR=dev/tmp/data python3 dev/test/mock_server.py   then press Update now (or POST /api/weather/refresh)
  python3 dev/test/frost_check.py [base-url]       screenshots go to dev/tmp/shots/frost-*.png"""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1366, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Frost Test')")
    pg.goto(BASE + '/#/'); pg.wait_for_timeout(2000)
    ban = pg.locator('.fz-banner')
    check(ban.count() == 1, 'banner shows on the Plants page')
    print('     ' + ban.inner_text().replace('\n', ' | ')[:300])
    pg.screenshot(path=f'{OUT}/frost-banner-light.png')
    pg.goto(BASE + '/#/plant/P-031'); pg.wait_for_timeout(1500)
    check(pg.locator('.fz-note').count() == 1, 'plant page shows its own frost risk')
    check(pg.locator('.fz-banner').count() == 0, 'no banner on a plant page (its own note is enough)')
    pg.click('.fz-note a[href="#/frost"]'); pg.wait_for_timeout(1500)
    check('Cold-night checklist' in pg.locator('h1').inner_text(), 'checklist page opens')
    check(pg.locator('.fz-banner').count() == 0, 'no banner on the checklist page itself')
    groups = pg.locator('section.blk[id^=fz-]'); check(groups.count() >= 1, f'{groups.count()} groups of plants listed')
    pg.screenshot(path=f'{OUT}/frost-checklist-light.png', full_page=False)
    # cover the first plant that has a Covered button
    row = pg.locator('.fz-row:has(button[data-act=frostcover])').first; code = row.get_attribute('data-code')
    row.locator('button[data-act=frostcover]').click(); pg.wait_for_timeout(1500)
    check(pg.locator(f'.fz-row[data-code="{code}"].is-done').count() == 1, f'{code} ticked as covered')
    focused = pg.evaluate('document.activeElement && document.activeElement.textContent')
    check('Undo' in (focused or ''), f'focus stays on that plant (on "{focused}")')
    # move a plant indoors: it leaves the list
    row = pg.locator('.fz-row:has(button[data-act=frostin])').first; code2 = row.get_attribute('data-code')
    row.locator('button[data-act=frostin]').click(); pg.wait_for_timeout(1800)
    check(pg.locator(f'.fz-row[data-code="{code2}"]').count() == 0, f'{code2} moved indoors and left the list')
    pg.locator('#fz-in').screenshot(path=f'{OUT}/frost-group-light.png')
    pg.locator('.fz-row').first.screenshot(path=f'{OUT}/frost-row-light.png')
    # undo the cover
    pg.locator(f'.fz-row[data-code="{code}"] button[data-act=frostundo]').first.click(); pg.wait_for_timeout(1500)
    check(pg.locator(f'.fz-row[data-code="{code}"].is-done').count() == 0, 'undo works')
    # the table counts covered plants
    check(pg.locator('.fz-tbl tbody tr').count() == 7, 'seven nights in the table')
    # hide the banner
    pg.goto(BASE + '/#/winter'); pg.wait_for_timeout(1500)
    pg.click('button[data-act=frosthide]'); pg.wait_for_timeout(500)
    pg.goto(BASE + '/#/'); pg.wait_for_timeout(1500)
    check(pg.locator('.fz-banner').count() == 0, 'hidden banner stays hidden')
    pg.evaluate("localStorage.removeItem('plantdb.frosthide')")
    for name, vp, theme in [('phone-dark', (390, 844), 'dark'), ('wide-dark', (1920, 1080), 'dark')]:
        q = b.new_page(viewport={'width': vp[0], 'height': vp[1]}); q.on('pageerror', lambda e: errs.append(str(e)))
        q.add_init_script("localStorage.setItem('plantdb.editor','Frost Test');localStorage.setItem('plantdb.display',JSON.stringify({theme:'%s'}))" % theme)
        q.goto(BASE + '/#/'); q.wait_for_timeout(1800); q.screenshot(path=f'{OUT}/frost-banner-{name}.png')
        q.goto(BASE + '/#/frost'); q.wait_for_timeout(1800); q.screenshot(path=f'{OUT}/frost-checklist-{name}.png')
        over = q.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 2, f'{name}: no sideways scrolling ({over}px)')
        q.close()
    b.close()
for e in errs: print('JS error:', e)
sys.exit(1 if fails or errs else 0)
