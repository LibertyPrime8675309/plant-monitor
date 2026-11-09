"""Checks 1.25.0: pop-up windows. Display settings in parts (a menu of parts beside the settings, which become buttons on a phone),
Done and Reset to defaults always in view, every window closes with a click outside it (not with a drag that ends outside), the
buttons at the bottom of long windows stay in view while scrolling, and windows use more of the screen. Start the mock server with
a fresh data folder (MOCK_TS=1), then:
python3 dev/test/dialog_check.py      Screenshots: dev/tmp/shots/dialog-*.png"""
import os, sys
from playwright.sync_api import sync_playwright
LOCAL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def inside(pg, sel):
    return pg.evaluate("""s => { const b = document.querySelector(s).getBoundingClientRect(), d = document.getElementById('dlg').getBoundingClientRect();
      return b.top >= d.top - 1 && b.bottom <= d.bottom + 1 && b.top >= 0 && b.bottom <= innerHeight + 1; }""", sel)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1920, 'height': 1080})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Dlg Test');localStorage.removeItem('plantdb.display')")
    pg.goto(LOCAL + '/#/plants'); pg.wait_for_timeout(2500)
    pg.click('#display-btn'); pg.wait_for_timeout(500)
    d = pg.locator('#dlg')
    bb = d.bounding_box()
    check(d.get_attribute('class') == 'dv' and bb['width'] > 1700 and bb['height'] > 900, f'Display settings fills most of the screen ({round(bb["width"])} x {round(bb["height"])})')
    check(d.get_attribute('aria-labelledby') == 'dv-title', 'the window is named by its heading')
    tabs = pg.locator('.dv-tab')
    check(tabs.count() == 7 and tabs.first.get_attribute('aria-current') == 'true', 'a menu of seven parts (Units joined in 1.47.0, Identify in 1.51.0), the first marked as showing')
    check(pg.locator('.dv-cols').first.evaluate("e => getComputedStyle(e).gridTemplateColumns.split(' ').length") >= 2, 'settings sit side by side')
    pg.screenshot(path=os.path.join(OUT, 'dialog-1-display.png'))
    pg.click('.dv-tab:has-text("Keyboard")')
    try: pg.wait_for_function("document.querySelector('.dv-tab[aria-current=true]') && document.querySelector('.dv-tab[aria-current=true]').textContent.includes('Keyboard')", timeout=5000)
    except Exception: pass
    pg.wait_for_timeout(1500)                       # the smooth scroll settles (it is longer with seven parts, 1.51.0)
    check(pg.locator('.dv-tab:has-text("Keyboard")').get_attribute('aria-current') == 'true' and inside(pg, '#dv-s6 h3'), 'a part in the menu jumps to it and is marked as showing')
    check(inside(pg, '.dv-acts button[value=ok]') and inside(pg, '[data-act=prefreset]'), 'Done and Reset to defaults are still in view')
    pg.click('#dv-s0 .opts label:has-text("Larger")'); pg.wait_for_timeout(300)
    check(pg.evaluate("document.documentElement.dataset.size") == '160', 'a setting still applies right away')
    pg.click('[data-act=prefreset]'); pg.wait_for_timeout(500)
    check(pg.locator('#dlg[open]').count() == 1 and pg.evaluate("document.documentElement.dataset.size") == '115', 'Reset to defaults resets, and the window stays open')
    # a drag that ends outside does not close it; a click outside does
    pg.mouse.move(bb['x'] + 300, bb['y'] + 300); pg.mouse.down(); pg.mouse.move(4, 4); pg.mouse.up(); pg.wait_for_timeout(300)
    check(pg.locator('#dlg[open]').count() == 1, 'a drag that ends outside the window leaves it open')
    pg.mouse.click(5, 5); pg.wait_for_timeout(400)
    check(pg.locator('#dlg[open]').count() == 0, 'a click outside the window closes it')
    # another window: Location
    pg.click('#place-btn'); pg.wait_for_timeout(800)
    bb2 = d.bounding_box()
    check(bb2['width'] > 1000, f'other windows are wider too ({round(bb2["width"])} px)')
    foot = '#dlg > form > .row:last-child'
    pg.evaluate("document.getElementById('dlg').scrollTop = 0"); pg.wait_for_timeout(200)
    check(inside(pg, foot), 'the buttons at the bottom of a window are in view from the top of it')
    pg.screenshot(path=os.path.join(OUT, 'dialog-2-location.png'))
    pg.mouse.click(bb2['x'] - 10 if bb2['x'] > 20 else 5, 5); pg.wait_for_timeout(400)
    check(pg.locator('#dlg[open]').count() == 0, 'it closes with a click outside too')
    pg.keyboard.press('Escape')
    # a confirmation box stays small, and Cancel is what a click outside does
    pg.goto(LOCAL + '/#/offline'); pg.wait_for_timeout(2000)
    pg.check('input[data-f=offkeep]'); pg.wait_for_timeout(2500)
    pg.click('[data-act=offforget]'); pg.wait_for_timeout(500)
    bb3 = d.bounding_box()
    check(d.get_attribute('class') == 'small' and bb3['width'] < 700, f'a confirmation stays small ({round(bb3["width"])} px)')
    pg.mouse.click(5, 5); pg.wait_for_timeout(600)
    check(pg.locator('#dlg[open]').count() == 0 and 'Last saved' in pg.inner_text('main') or 'Saving' in pg.inner_text('main') or 'Delete the saved copy' in pg.inner_text('main'), 'a click outside a confirmation is Cancel: nothing is deleted')
    # phones
    for name, w, h in (('galaxy-s21-ultra', 384, 854), ('iphone-11', 414, 896)):
        ph = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True)
        ph.add_init_script("localStorage.setItem('plantdb.editor','Dlg Test')")
        ph.goto(LOCAL + '/#/plants'); ph.wait_for_timeout(2500)
        ph.evaluate("document.getElementById('display-btn').click()"); ph.wait_for_timeout(500)
        bx = ph.locator('#dlg').bounding_box()
        check(bx['width'] >= w - 1 and bx['height'] >= h - 2, f'{name}: Display settings covers the screen')
        check(ph.locator('.dv-tabs').evaluate("e => getComputedStyle(e).flexDirection") == 'row' and inside(ph, '.dv-acts button[value=ok]'), f'{name}: the parts are a row of buttons, with Done in view')
        ph.evaluate("document.getElementById('dv-body').scrollTop = 99999"); ph.wait_for_timeout(300)
        check(inside(ph, '.dv-acts button[value=ok]') and ph.evaluate("document.getElementById('dv-body').scrollWidth <= document.getElementById('dv-body').clientWidth + 1"), f'{name}: Done stays in view at the bottom, with no sideways scrolling')
        ph.screenshot(path=os.path.join(OUT, f'dialog-3-{name}.png'))
        ph.close()
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
