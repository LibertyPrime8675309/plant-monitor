"""Checks watering, the care log and the Today page. Start the mock server first (fresh data folder, then Update now so
the weather and rain are filled in), then:  python3 dev/test/care_check.py [base-url]   Screenshots: dev/tmp/shots/care-*.png"""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def confirm(pg):
    pg.wait_for_timeout(300); pg.locator('dialog[open] button[value=ok]').click(); pg.wait_for_timeout(1500)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1366, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Care Test')")
    pg.goto(BASE + '/#/today'); pg.wait_for_timeout(2500)
    check(pg.locator('h1').inner_text() == 'Today', 'Today page opens from the menu link')
    check(pg.locator('[data-nav=today][aria-current=page]').count() == 1, 'Today is highlighted in the menu')
    due = pg.locator('#today-water > ul.jobs > li.job'); nd = due.count()
    check(nd > 0, f'{nd} plants due for water (rain counted for plants in the open)')
    pg.screenshot(path=f'{OUT}/care-today-light.png')
    code = due.first.get_attribute('data-code')
    due.first.locator('button[data-act=care][data-kind=water]').click(); pg.wait_for_timeout(1500)
    check(pg.locator(f'#today-water > ul.jobs > li.job[data-code="{code}"]').count() == 0, f'{code} watered and left the list')
    if nd > 1:
        code2 = pg.locator('#today-water > ul.jobs > li.job').first.get_attribute('data-code')
        pg.locator('#today-water > ul.jobs > li.job').first.locator('button[data-kind=check]').click(); pg.wait_for_timeout(1500)
        check(pg.locator(f'#today-water > ul.jobs > li.job[data-code="{code2}"]').count() == 0, f'{code2} checked (still moist) and left the list')
    unk = pg.locator('#today-water details.grp:has(h3:text-matches("No watering logged")) li.job').count()
    check(unk > 0, f'{unk} plants with no watering logged (porch and indoor plants get no rain)')
    pg.locator('#today-water details.grp:has(h3:text-matches("No watering logged")) summary').click()
    pg.locator('#today-water details.grp:has(h3:text-matches("No watering logged")) button[data-act=careall]').click(); confirm(pg)
    check(pg.locator('#today-water details.grp:has(h3:text-matches("No watering logged"))').count() == 0, 'bulk "I watered all" starts the clock for them')
    check(pg.locator('#today-feed').count() == 1 and pg.locator('#today-needs').count() == 1, 'feed and needed-from-you sections are there')
    # plant page
    pg.goto(BASE + '/#/plant/P-031'); pg.wait_for_timeout(2500)
    st = pg.locator('#quick-status').inner_text()
    check(st.startswith('Water:'), 'quick status line: ' + st[:120])
    wb = pg.locator('.quick button[data-kind=water]')
    if wb.is_enabled(): wb.click(); pg.wait_for_timeout(1500)        # 1.21.0: off already if "I watered all" above included it
    check(pg.locator('.care-log li').count() >= 1 and 'Watered' in pg.locator('.care-log li').first.inner_text() and wb.is_disabled(), 'Watered today shows in the care log, and the button is off for the rest of the day')
    pg.locator('.quick button[data-act=careother]').click(); pg.wait_for_timeout(400)
    pg.select_option('dialog[open] select[name=kind]', 'repot'); pg.fill('dialog[open] input[name=note]', 'moved to a 10 inch pot')
    pg.locator('dialog[open] button[value=ok]').click(); pg.wait_for_timeout(1500)
    check('Repotted' in pg.locator('.care-log').inner_text(), 'other care (Repotted) logged with its note')
    pg.locator('#care-plant').screenshot(path=f'{OUT}/care-plant-log-light.png')
    pg.locator('.care-log li').first.locator('button[data-act=caredel]').click(); confirm(pg)
    check('Repotted' not in pg.locator('.care-log').inner_text(), 'Remove takes an entry out of the care log')
    pg.goto(BASE + '/#/plant/P-031/edit'); pg.wait_for_timeout(1500)
    check(pg.locator('input[name=water_every_days]').count() == 1, 'Edit page has "Check for water every (days)"')
    for name, vp, theme in [('phone-dark', (390, 844), 'dark'), ('wide-dark', (1920, 1080), 'dark')]:
        q = b.new_page(viewport={'width': vp[0], 'height': vp[1]}); q.on('pageerror', lambda e: errs.append(str(e)))
        q.add_init_script("localStorage.setItem('plantdb.editor','Care Test');localStorage.setItem('plantdb.display',JSON.stringify({theme:'%s'}))" % theme)
        for path, tag in (('#/today', 'today'), ('#/plant/P-001', 'plant')):
            q.goto(BASE + '/' + path); q.wait_for_timeout(2000); q.screenshot(path=f'{OUT}/care-{tag}-{name}.png')
            over = q.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 2, f'{name} {tag}: no sideways scrolling ({over}px)')
        q.close()
    b.close()
for e in errs: print('JS error:', e)
sys.exit(1 if fails or errs else 0)
