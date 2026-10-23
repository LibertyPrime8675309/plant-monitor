"""Checks that a plant page in two halves drops its row of section buttons while the On this page menu is open, and
brings it back when the menu is hidden. Start the mock server first, then:  python3 dev/test/jumprow_check.py
Screenshots: dev/tmp/shots/jumprow-*.png"""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
JH = "getComputedStyle(document.getElementById('pane-r')).getPropertyValue('--jump-h').trim()"
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={'width': 1366, 'height': 900}); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Jump Test')")
    pg.goto(BASE + '/#/plant/P-031'); pg.wait_for_timeout(2500)
    check(pg.locator('#sidenav').is_visible() and not pg.locator('.pane .jump').is_visible(), 'menu open: the row of section buttons is not shown')
    check(pg.evaluate(JH) == '0px', 'and the section titles do not leave room for it')
    pg.screenshot(path=f'{OUT}/jumprow-menu-open.png')
    # a button near the bottom of the right half can be pressed
    last = pg.locator('#pane-r #history button').last
    last.scroll_into_view_if_needed(); box = last.bounding_box(); hit = pg.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); return e && e.closest('#history') !== null; }", [box['x'] + box['width'] / 2, box['y'] + box['height'] / 2])
    check(hit, 'a button at the bottom of the right half is not covered')
    pg.locator('#sidenav button[data-act=navtoggle]').click(); pg.wait_for_timeout(600)
    jh = pg.evaluate(JH); h = pg.evaluate("document.querySelector('.pane .jump').offsetHeight")
    check(pg.locator('.pane .jump').is_visible() and jh == f'{h}px', f'menu hidden: the row comes back and titles leave room for it ({jh})')
    pg.locator('.pane .jump button[data-id=soil]').click(); pg.wait_for_timeout(900)
    t = pg.evaluate("document.querySelector('#soil h2').getBoundingClientRect().top"); jb = pg.evaluate("document.querySelector('.pane .jump').getBoundingClientRect().bottom")
    check(t >= jb - 2, f'a section button scrolls its title into view below the row ({t:.0f} >= {jb:.0f})')
    pg.screenshot(path=f'{OUT}/jumprow-menu-hidden.png')
    pg.locator('#nav-tab').click(); pg.wait_for_timeout(600)
    check(not pg.locator('.pane .jump').is_visible() and pg.evaluate(JH) == '0px', 'menu opened again: the row steps aside again')
    pg.locator('#sidenav').get_by_role('link', name='Water and soil').click(); pg.wait_for_timeout(900)
    t = pg.evaluate("document.querySelector('#soil h2').getBoundingClientRect().top"); pt = pg.evaluate("document.getElementById('pane-r').getBoundingClientRect().top")
    check(t >= pt - 2, 'the menu link scrolls Water and soil to the top of the right half')
    pg.close()
    q = b.new_page(viewport={'width': 1366, 'height': 900}); q.on('pageerror', lambda e: errs.append(str(e)))
    q.add_init_script("localStorage.setItem('plantdb.display',JSON.stringify({layout:'single'}))")
    q.goto(BASE + '/#/plant/P-031'); q.wait_for_timeout(2200)
    check(q.locator('.jump').is_visible(), 'one-column layout: the row stays, as before')
    q.close(); b.close()
for e in errs: print('JS error:', e)
sys.exit(1 if fails or errs else 0)
