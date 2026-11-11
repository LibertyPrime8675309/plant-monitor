"""Checks 1.14.1: the section menu and the row of section buttons list every part of a plant page (including the photos
and the name and details card at the top, and any section added later), and swiping sideways on a phone opens the next
or previous plant without getting in the way of scrolling, form fields or the screen edges.
Start the mock server first, then:  python3 dev/test/swipe_check.py
Screenshots: dev/tmp/shots/swipe-*.png"""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)

def swipe(pg, cdp, x0, y0, x1, y1, steps=8, pause=12, shot=None):
    """A real finger: touch down, move in steps, lift."""
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x0, 'y': y0}]})
    for i in range(1, steps + 1):
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x0 + (x1 - x0) * i / steps, 'y': y0 + (y1 - y0) * i / steps}]})
        pg.wait_for_timeout(pause)
    hint = pg.evaluate("(() => { const h = document.getElementById('swipe-hint'); return h && h.classList.contains('show') ? h.textContent + (h.classList.contains('ready') ? ' [ready]' : '') : ''; })()")
    if shot: pg.screenshot(path=os.path.join(OUT, shot))
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
    pg.wait_for_timeout(1500)
    return hint

with sync_playwright() as pw:
    b = pw.chromium.launch()
    # ---- the menu and the row of section buttons, on a laptop
    pg = b.new_page(viewport={'width': 1366, 'height': 900}); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Swipe Test')")
    pg.goto(BASE + '/#/plant/P-020'); pg.wait_for_timeout(2500)
    links = [a.strip() for a in pg.locator('#sn-list a').all_inner_texts()]
    check(links[:3] == ['Top of the page', 'Photos', 'Name and details'], f'the menu starts with the top, the photos and the name and details card ({links[:3]})')
    heads = pg.evaluate("[...document.querySelectorAll('#app h2')].filter(h => h.offsetParent && !h.closest('dialog,.chart-card')).map(h => h.textContent.trim())")
    check(all(h in links for h in heads), f'every section title on the page is in the menu ({len(heads)} sections, {len(links)} links)')
    pg.locator('#sidenav').get_by_role('link', name='Name and details').click(); pg.wait_for_timeout(900)
    t = pg.evaluate("document.getElementById('details').getBoundingClientRect().top"); pt = pg.evaluate("document.getElementById('pane-r').getBoundingClientRect().top")
    check(abs(t - pt) < 120 and pg.evaluate("document.activeElement && document.activeElement.matches('#details h2')"), 'Name and details scrolls the card into view and moves focus to its title (1.56.5: the plant\'s name is above the photos)')
    pg.screenshot(path=os.path.join(OUT, 'swipe-1-menu.png'))
    pg.locator('#sidenav button[data-act=navtoggle]').click(); pg.wait_for_timeout(600)
    row = [x.strip() for x in pg.locator('#jumprow button').all_inner_texts()]
    check(row[:1] == ['Details'] and all(x in row for x in ['Now', 'Identification', 'About', 'Light', 'Coming inside', 'Timeline', 'History']), f'the button row has every section, with short names ({len(row)}: {", ".join(row)})')
    # both lists come from the page itself, so a section added later joins them with no other change
    ids = pg.evaluate("[...document.querySelectorAll('#pane-r section h2')].filter(h => h.offsetParent).map(h => h.closest('section').id)")
    got = pg.evaluate("[...document.querySelectorAll('#jumprow button')].map(b => b.dataset.id)")
    check(set(ids) <= set(got), f'every section in the details half has a button ({len(ids)} sections)')
    pg.close()

    # ---- swiping on a phone
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True, device_scale_factor=2)
    ctx.add_init_script("localStorage.setItem('plantdb.editor','Swipe Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'160'}))")
    ph = ctx.new_page(); ph.on('pageerror', lambda e: errs.append(str(e)))
    cdp = ctx.new_cdp_session(ph)
    ph.goto(BASE + '/#/plant/P-020'); ph.wait_for_timeout(2500)
    ph.evaluate("document.getElementById('ident').scrollIntoView()"); ph.wait_for_timeout(300)
    hint = swipe(ph, cdp, 320, 500, 90, 510, shot='swipe-2-hint.png')
    check('Next plant' in hint and '[ready]' in hint, f'while swiping left a label names the next plant and says it is ready ({hint})')
    check(ph.evaluate('location.hash') == '#/plant/P-021', f'swiping left opens the next plant ({ph.evaluate("location.hash")})')
    ph.evaluate("document.getElementById('ident').scrollIntoView()"); ph.wait_for_timeout(300)   # swipes that start on the photo are left alone
    hint = swipe(ph, cdp, 80, 500, 320, 505)
    check(ph.evaluate('location.hash') == '#/plant/P-020' and 'Previous plant' in hint, 'swiping right opens the previous plant')
    ph.evaluate("document.getElementById('ident').scrollIntoView()"); ph.wait_for_timeout(300)
    swipe(ph, cdp, 200, 650, 230, 250)
    check(ph.evaluate('location.hash') == '#/plant/P-020', 'scrolling up and down does not change the plant')
    swipe(ph, cdp, 300, 500, 250, 505)
    check(ph.evaluate('location.hash') == '#/plant/P-020', 'a short sideways nudge does not change the plant')
    swipe(ph, cdp, 383, 500, 120, 505)
    check(ph.evaluate('location.hash') == '#/plant/P-020', 'a swipe from the screen edge (Back on the phone) is left alone')
    sel = ph.locator('select.site-pick'); sel.scroll_into_view_if_needed(); bx = sel.bounding_box()
    swipe(ph, cdp, bx['x'] + bx['width'] - 20, bx['y'] + bx['height'] / 2, bx['x'] + 10, bx['y'] + bx['height'] / 2 + 4)
    check(ph.evaluate('location.hash') == '#/plant/P-020', 'a swipe that starts on a form field is left alone')
    ph.goto(BASE + '/#/plant/P-001'); ph.wait_for_timeout(2000)
    ph.evaluate("document.getElementById('ident').scrollIntoView()"); ph.wait_for_timeout(300)
    hint = swipe(ph, cdp, 80, 500, 320, 505)
    check(ph.evaluate('location.hash') == '#/plant/P-001' and 'first plant' in hint, 'on the first plant, swiping right says so and stays')
    check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'no sideways scrolling on the phone')
    ph.evaluate("PlantPrefs.set('swipe', '0')")
    swipe(ph, cdp, 320, 500, 90, 510)
    check(ph.evaluate('location.hash') == '#/plant/P-001', 'with swiping turned off in Display, a swipe does nothing')
    ph.evaluate("PlantPrefs.set('swipe', '1')")
    ph.evaluate("window.scrollBy(0, -80)"); ph.wait_for_timeout(400)  # 1.57.0: the bottom bar slips away while scrolling down; a little up brings it back
    ph.locator('#nav-tab').click(); ph.wait_for_timeout(400)          # 1.42.0: Display is at the bottom of the Navigation menu
    ph.locator('#display-btn').click(); ph.wait_for_timeout(500)
    check(ph.locator('dialog fieldset', has=ph.locator('legend', has_text='Swipe between plants')).count() == 1, 'Display has a Swipe between plants setting')
    ctx.close(); b.close()
for e in errs: print('JS error:', e)
check(not errs, 'no JavaScript errors')
print('%d failed' % len(fails))
sys.exit(1 if fails else 0)
