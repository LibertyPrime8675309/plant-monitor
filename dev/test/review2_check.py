"""Checks the second November review's changes (1.57.0): Today folds "No watering logged yet" and keeps Water's count honest;
the Display button sits in the top bar on a page with no Navigation menu; a greyed-out button says why; the page title takes the
focus after moving to a page; Settings links to Offline use, Backups and the Audit log instead of repeating them; Weather says
"No readings" once instead of drawing empty charts; the plant page links its Page history and folds its reference sections the
first time; headings do not skip a level; the phone's bottom bar slips away while scrolling down; "Notes under buttons and boxes:
Show them when I ask" turns each note into a Note button that opens by mouse, keyboard or a long press; the page loads one script.
Start the mock server with a fresh data folder, then: python3 dev/test/review2_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/review2-*.png"""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def shot(pg, name, sel=None):
    (pg.locator(sel).first if sel else pg).screenshot(path=os.path.join(OUT, f'review2-{name}.png'))
def open_page(pg, h, wait='h1', reload=False):
    pg.goto(BASE + '/' + h)
    if reload: pg.reload()           # a new address that differs only after # does not load the page again, and prefs.js runs on load
    pg.wait_for_selector(wait, timeout=20000); pg.wait_for_timeout(900)
def heading_skips(pg):
    return pg.evaluate("""() => { const hs = [...document.querySelectorAll('#app h1, #app h2, #app h3, #app h4, #app h5, #app h6')].filter(h => h.getClientRects().length || h.classList.contains('sr'));
      const out = []; let last = 0; for (const h of hs) { const n = +h.tagName[1]; if (last && n > last + 1) out.push(h.tagName + ' ' + h.textContent.trim().slice(0, 40)); last = n; } return out; }""")

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Review Test')")

    # one script for the app (item 21)
    open_page(pg, '#/')
    srcs = pg.evaluate("[...document.scripts].map(s => s.getAttribute('src'))")
    check(len(srcs) == 2 and srcs[0].startswith('/prefs.js?v=') and srcs[1].startswith('/app.js?v='), f'the page loads prefs.js and one app.js ({srcs})')
    check(pg.evaluate("typeof viewToday === 'function' && typeof viewLibrary === 'function' && typeof viewShopping === 'function' && typeof viewFungi === 'function'"),
          'every part of the bundle ran (Today, the library, Shopping and mushroom finds are there)')

    # Today (item 6)
    pg.wait_for_selector('#today-needs', timeout=20000); pg.wait_for_timeout(800)
    zero = pg.evaluate("[...document.querySelectorAll('#app h2')].filter(h => /\\(0\\)\\s*$/.test(h.textContent)).map(h => h.textContent.trim())")
    check(not zero, f'no Today heading counts nothing ({zero})')
    unl = pg.locator('#today-unlogged')
    if unl.count():
        check(pg.locator('#today-unlogged details.grp:not([open])').count() == 1 and 'No watering logged yet' in unl.inner_text(), 'plants with no watering logged are in their own folded block')
        shot(pg, 'today-unlogged', '#today-unlogged')
    else: print('note: no plants without a watering in this data')

    # the page title takes the focus after moving to a page (item 17)
    pg.locator('a[href="#/plants"]:visible').first.click(); pg.wait_for_selector('h1:has-text("All plants")', timeout=20000); pg.wait_for_timeout(600)
    check(pg.evaluate("document.activeElement && document.activeElement.tagName") == 'H1', 'after following a link, the page title has the focus')
    check(not heading_skips(pg), f'All plants: no heading skips a level {heading_skips(pg)}')

    # headings (item 18)
    for h in ('#/library', '#/review', '#/compare'):
        open_page(pg, h)
        sk = heading_skips(pg)
        check(not sk, f'{h}: no heading skips a level {sk}')

    # Display in the top bar on a page with no Navigation menu (item 7)
    open_page(pg, '#/history')
    if pg.evaluate("document.documentElement.dataset.navempty") == '1':
        check(pg.locator('header.top .top-acts > #display-btn').count() == 1, 'the Audit log has no Navigation menu, so Display is in the top bar')
        box = pg.locator('#display-btn').bounding_box()
        check(box and box['y'] < 120, 'at the top of the page, where it covers nothing')
        shot(pg, 'display-top', 'header.top')
    else: print('note: the Audit log has a Navigation menu here')
    open_page(pg, '#/plant/P-001')
    check(pg.locator('#sn-foot #display-btn').count() == 1, 'on a page with a Navigation menu, Display is at its foot as before')

    # the plant page: Page history link (item 16)
    link = pg.locator('.l-top a[data-act=jumpsec][data-sec=history]')
    check(link.count() == 1 and link.inner_text().strip() == 'Page history', 'the label card links to Page history')
    check('Version ' in pg.inner_text('#history') if pg.locator('#history').count() else False, 'and the history starts with the version and who updated it')

    # disabled buttons say why (item 10)
    open_page(pg, '#/identify')
    why = pg.locator('#id-snap-why')
    check(pg.locator('#id-snap[disabled]').count() == 1 and why.is_visible() and why.inner_text() == 'Start the camera first.', '"Check this picture" is greyed out and says why')
    check(pg.get_attribute('#id-snap', 'aria-describedby') == 'id-snap-why', 'and a screen reader hears the reason with the button')
    check(pg.evaluate("getComputedStyle(document.getElementById('id-snap')).borderStyle") == 'dashed', 'a greyed-out button has a dashed edge, not only a paler colour')
    open_page(pg, '#/new')
    check(pg.locator('#newfill-why').is_visible(), '"Fill in the names" says "Add a photo below first."')

    # Settings links instead of repeated cards (item 15)
    open_page(pg, '#/settings')
    st = pg.inner_text('#app')
    check(all(pg.locator(f'#app a[href="{h}"]').count() >= 1 for h in ('#/offline', '#/backups', '#/history')), 'Settings links to Offline use, Backups and the Audit log')
    check(pg.locator('#app .set-card h2:text-is("Backups")').count() == 0, 'and no longer repeats the Backups card')

    # Weather with no readings (item 12)
    open_page(pg, '#/weather'); pg.wait_for_timeout(1500)
    if pg.locator('.wx-grid .chart-card').count() == 0:
        check('No readings in this period yet' in pg.inner_text('#app'), 'Weather with no readings says so once instead of drawing empty charts')
    else: print('note: this data has weather readings')

    # Notes on request (Display: Notes under buttons and boxes)
    pg.evaluate("localStorage.setItem('plantdb.display', JSON.stringify({notes: 'ask'}))")
    open_page(pg, '#/new', reload=True)
    check(pg.evaluate("document.documentElement.dataset.notes") == 'ask', 'the setting is on the page (data-notes=ask)')
    n = pg.locator('#app .hint[data-note]').first
    check(pg.locator('#app label.f > small[data-note][role=button]').count() >= 3, 'the notes under field names are Note buttons too')
    check(n.count() == 1 and n.get_attribute('role') == 'button' and n.get_attribute('tabindex') == '0' and n.get_attribute('aria-expanded') == 'false',
          'each note becomes a Note button that the keyboard can reach')
    pg.mouse.move(5, 5)
    h0 = n.bounding_box()['height']
    shot(pg, 'notes-closed', 'form')
    n.focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(150)
    check(n.get_attribute('aria-expanded') == 'true' and 'note-open' in (n.get_attribute('class') or ''), 'Enter opens it')
    pg.locator('h1').focus(); pg.mouse.move(5, 5); pg.wait_for_timeout(100)
    check(n.evaluate("e => parseFloat(getComputedStyle(e).fontSize)") >= 12, 'an open note shows its words at full size')
    shot(pg, 'notes-open', 'form')
    n.focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(100)
    check(n.get_attribute('aria-expanded') == 'false', 'Enter closes it again')
    pg.locator('h1').focus(); pg.mouse.move(5, 5); pg.wait_for_timeout(100)
    check(n.evaluate("e => parseFloat(getComputedStyle(e).fontSize)") == 0 and h0 < 70, 'closed, only the Note chip shows')
    pg.evaluate("localStorage.removeItem('plantdb.display')")

    # first visit to a plant page: the reference sections start folded (item 8)
    pg.evaluate("localStorage.removeItem('plantdb.folds'); localStorage.removeItem('plantdb.foldseed'); localStorage.setItem('plantdb.foldseedtest', '1')")
    open_page(pg, '#/plant/P-001'); pg.reload(); pg.wait_for_selector('h1', timeout=20000); pg.wait_for_timeout(1500)
    folded = pg.evaluate("[...document.querySelectorAll('[data-folded=\"1\"]')].map(s => (s.querySelector('h2') || s).textContent.trim().split('\\n')[0])")
    check(any('Temperature' in f for f in folded) and any('Pests' in f for f in folded), f'reference sections start folded on a first visit ({len(folded)} folded)')
    check(not any(f.startswith('Photos') or f.startswith('Care') for f in folded), 'photos and care stay open')
    shot(pg, 'plant-folded')
    pg.evaluate("localStorage.removeItem('plantdb.foldseedtest')")

    # a tall top bar: the Navigation menu starts under it (item 13)
    pg.set_viewport_size({'width': 1100, 'height': 900})
    pg.evaluate("localStorage.setItem('plantdb.display', JSON.stringify({size: '130'}))")
    open_page(pg, '#/checkup', reload=True); pg.wait_for_timeout(600)
    if pg.evaluate("document.documentElement.dataset.toptall === '1' && document.documentElement.dataset.narrow !== '1'"):
        gap = pg.evaluate("Math.abs(document.getElementById('sidenav').getBoundingClientRect().top - document.querySelector('.top').getBoundingClientRect().bottom)")
        check(gap <= 2, f'with a tall top bar the Navigation menu starts right under it ({gap}px)')
        shot(pg, 'nav-top')
    else: print('note: the top bar is not tall at this size')
    pg.evaluate("localStorage.removeItem('plantdb.display')")

    # the phone's bottom bar slips away while scrolling down (item 14)
    ctx = br.new_context(viewport={'width': 390, 'height': 800}, has_touch=True, is_mobile=True)
    ph = ctx.new_page(); ph.on('pageerror', lambda e: errs.append(str(e)))
    ph.add_init_script("localStorage.setItem('plantdb.editor','Review Test')")
    ph.goto(BASE + '/#/plants'); ph.wait_for_selector('h1', timeout=20000); ph.wait_for_timeout(1200)
    check(ph.evaluate("document.documentElement.dataset.narrow") == '1', 'phone width is narrow mode')
    ph.evaluate("window.scrollTo(0, 600)"); ph.wait_for_timeout(150); ph.evaluate("window.scrollTo(0, 1400)"); ph.wait_for_timeout(400)
    check(ph.evaluate("document.documentElement.dataset.barhide") == '1', 'scrolling down hides the bottom bar')
    shot(ph, 'phone-barhidden')
    ph.evaluate("window.scrollTo(0, 1200)"); ph.wait_for_timeout(400)
    check(ph.evaluate("document.documentElement.dataset.barhide") is None, 'scrolling up brings it back')
    ph.evaluate("window.scrollTo(0, 0)"); ph.wait_for_timeout(300)
    check(ph.evaluate("document.documentElement.scrollWidth <= innerWidth"), 'no sideways scrolling at phone width')
    # long press on a field opens its note
    ph.evaluate("localStorage.setItem('plantdb.display', JSON.stringify({notes: 'ask'}))")
    ph.goto(BASE + '/#/new'); ph.reload(); ph.wait_for_selector('h1', timeout=20000); ph.wait_for_timeout(1200)
    target = ph.evaluate("""() => { const n = document.querySelector('#app label.f > small[data-note]'); if (!n) return null;
      const box = n.closest('label, .f'); const c = box.querySelector('input, select, textarea') || box; c.scrollIntoView({block: 'center'}); c.id = c.id || 'lp-target'; n.id = n.id || 'lp-note'; return [c.id, n.id]; }""")
    if target:
        ph.wait_for_timeout(200)
        b = ph.locator('#' + target[0]).bounding_box()
        cdp = ctx.new_cdp_session(ph)
        x, y = b['x'] + 5, b['y'] + b['height'] / 2
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
        ph.wait_for_timeout(750)
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        ph.wait_for_timeout(200)
        check(ph.get_attribute('#' + target[1], 'aria-expanded') == 'true', 'a long press on a field opens its note')
        shot(ph, 'notes-longpress')
    else: check(False, 'the Add a plant form has a note to open')
    ctx.close()
    br.close()

check(not errs, f'no script errors ({errs[:3]})')
print('\n' + ('ALL OK' if not fails else f'{len(fails)} FAILED'))
sys.exit(1 if fails else 0)
