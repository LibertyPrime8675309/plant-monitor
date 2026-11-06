"""Checks 1.27.3: the On this page menu marks the section you chose, even when the page is too short to scroll it to the top,
and outlines the section for a moment. Start the mock server first (see dev/test), then:
python3 dev/test/sectionmenu_check.py      Screenshots: dev/tmp/shots/sectionmenu-*.png"""
import os
from playwright.sync_api import sync_playwright
LOCAL = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
cur = lambda pg: pg.evaluate("(document.querySelector('#sn-list a[aria-current=true]')||{}).textContent||''").strip()
def open_menu(pg):
    if not pg.locator('#sn-list a').first.is_visible():
        t = pg.locator('#nav-tab')
        if t.count() and t.first.is_visible(): t.first.click(); pg.wait_for_timeout(400)
with sync_playwright() as p:
    b = p.chromium.launch()
    for vw, vh, label in ((1920, 1080, 'monitor'), (1280, 900, 'laptop')):
        pg = b.new_page(viewport={'width': vw, 'height': vh})
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script("localStorage.setItem('plantdb.editor','Menu Test')")
        for route in ('#/groups', '#/frost', '#/lights', '#/plant/P-014'):
            pg.goto(LOCAL + '/' + route); pg.wait_for_timeout(2500)
            open_menu(pg)
            links = pg.locator('#sn-list a'); n = links.count()
            ok_all, name = True, ''
            for i in [n - 1, 0, n // 2, n - 1, 1 if n > 1 else 0]:
                name = links.nth(i).inner_text().strip()
                links.nth(i).click(); pg.wait_for_timeout(900)
                if cur(pg) != name: ok_all = False; print('   ', label, route, 'chose', repr(name), 'marked', repr(cur(pg)))
            check(ok_all, f'{label} {route}: the section you choose is the one marked ({n} sections)')
            pg.wait_for_timeout(1500)
            check(cur(pg) == name, f'{label} {route}: still marked after the menu is rebuilt')
        pg.goto(LOCAL + '/#/groups'); pg.wait_for_timeout(2500); open_menu(pg)
        links = pg.locator('#sn-list a'); last = links.nth(links.count() - 1); name = last.inner_text().strip()
        last.click(); pg.wait_for_timeout(1200)
        check(pg.locator('.sn-flash').count() == 1, f'{label}: the section you jumped to is outlined')
        pg.screenshot(path=os.path.join(OUT, f'sectionmenu-{label}.png'))
        pg.mouse.move(vw // 2, vh // 2); pg.mouse.wheel(0, -20000); pg.wait_for_timeout(1200)
        check(cur(pg) == 'Top of the page', f'{label}: scrolling back up yourself lets the menu follow the page again')
        pg.close()
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All section menu checks passed' if not fails else f'{len(fails)} section menu check(s) failed'))
raise SystemExit(1 if fails else 0)
