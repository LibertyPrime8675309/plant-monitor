"""Checks 1.26.0: pages use the screen. Paragraphs and lists run the full width unless Display > Line length says Shorter lines,
groups and Today's jobs sit side by side on a wide screen, card photos keep their shape, tables too wide for a phone become one box
per row, and on a phone with the largest text the pages fold behind one Pages button while Sections, Debug and Display share one bar along the bottom. Start the mock server with
a fresh data folder, then:
python3 dev/test/layout_check.py      Screenshots: dev/tmp/shots/layout-*.png"""
import json, os
from playwright.sync_api import sync_playwright
LOCAL = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def cols(pg, sel): return pg.locator(sel).first.evaluate("e => getComputedStyle(e).gridTemplateColumns.split(' ').length")
BIG = {'size': '190', 'space': 'roomy', 'contrast': 'high', 'theme': 'dark'}
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1920, 'height': 960})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Layout Test');if(!sessionStorage.getItem('kept'))localStorage.removeItem('plantdb.display');sessionStorage.setItem('kept','1')")
    pg.goto(LOCAL + '/#/groups'); pg.wait_for_timeout(2500)
    check(pg.evaluate("document.documentElement.dataset.lines") == 'full', 'Line length starts at full width')
    check(pg.locator('main p').first.evaluate("e => getComputedStyle(e).maxWidth") == 'none', 'paragraphs run the full width')
    check(cols(pg, '.grp-list') >= 3, f'groups sit at least three across at 1920 ({cols(pg, ".grp-list")})')
    pg.screenshot(path=os.path.join(OUT, 'layout-1-groups.png'))
    pg.click('#display-btn'); pg.wait_for_timeout(500)
    grp = pg.locator('#dlg fieldset:has(legend:text-is("Line length"))')
    check(grp.count() == 1 and grp.locator('label:has-text("Shorter lines")').count() == 1, 'Display has a Line length setting')
    grp.locator('label:has-text("Shorter lines")').click(); pg.wait_for_timeout(300)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    check(pg.evaluate("document.documentElement.dataset.lines") == 'short' and pg.locator('main p').first.evaluate("e => getComputedStyle(e).maxWidth") != 'none',
          'Shorter lines brings back the limit on paragraphs')
    check(cols(pg, '.grp-list') >= 3, 'the group cards stay side by side with shorter lines')
    pg.evaluate("window.PlantPrefs.set('lines','full')")
    pg.goto(LOCAL + '/#/today'); pg.wait_for_timeout(2500)
    if pg.locator('ul.jobs').count(): check(cols(pg, 'ul.jobs') >= 2, 'Today shows its jobs in two columns on a wide screen')
    pg.goto(LOCAL + '/#/'); pg.wait_for_timeout(2500)
    shape = pg.evaluate("""() => [...document.querySelectorAll('.sheet .mat img')].slice(0, 12).map(i => { const r = i.getBoundingClientRect(); return r.width ? r.height / r.width : 0; })""")
    check(shape and max(shape) < 1.6, f'card photos keep their shape (tallest is {max(shape or [0]):.2f} times its width)')
    check(pg.locator('#pages-btn').is_hidden() and pg.locator('#main-nav').is_visible(), 'on a computer the pages are listed in the top bar')
    pg.goto(LOCAL + '/#/frost'); pg.wait_for_timeout(2500)
    check(pg.locator('main table.tbl.stacked').count() == 0, 'on a computer tables stay tables')
    pg.evaluate("window.PlantPrefs.set('size','135')"); pg.wait_for_timeout(600)
    top = pg.evaluate("[document.documentElement.dataset.pagesfold, document.querySelector('header.top').offsetHeight, innerHeight]")
    check(top[0] == '1' and pg.locator('#pages-btn').is_visible() and top[1] < top[2] * .2,
          f'with large text on a computer the pages fold behind the Pages button and the top bar stays short ({top[1]} px)')
    pg.evaluate("window.PlantPrefs.set('size','100')"); pg.wait_for_timeout(600)
    check(pg.evaluate("document.documentElement.dataset.pagesfold") == '0', 'with your usual text size the pages are listed again')
    pg.close()

    # a Galaxy S21 Ultra with the largest text
    ctx = b.new_context(viewport={'width': 384, 'height': 740}, device_scale_factor=2, is_mobile=True, has_touch=True, service_workers='block')
    ctx.add_init_script(f"localStorage.setItem('plantdb.editor','Layout Test');localStorage.setItem('plantdb.display',JSON.stringify({json.dumps(BIG)}))")
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(LOCAL + '/#/groups'); pg.wait_for_timeout(2500)
    btn = pg.locator('#pages-btn')
    check(btn.is_visible() and pg.locator('#main-nav').is_hidden(), 'on a phone the pages fold behind one button')
    check('Groups' in btn.inner_text() and btn.get_attribute('aria-expanded') == 'false', 'the button names the page you are on')
    btn.click(); pg.wait_for_timeout(300)
    check(pg.locator('#main-nav').is_visible() and btn.get_attribute('aria-expanded') == 'true', 'pressing it shows every page')
    check(pg.evaluate("document.activeElement.matches('#main-nav a[aria-current=page]')"), 'and moves to the page you are on')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    check(pg.locator('#main-nav').is_hidden() and pg.evaluate("document.activeElement.id") == 'pages-btn', 'Escape folds the list and goes back to the button')
    btn.click(); pg.wait_for_timeout(300); pg.screenshot(path=os.path.join(OUT, 'layout-2-phone-pages.png'))
    pg.click('#main-nav a[data-nav=today]'); pg.wait_for_timeout(2500)
    check(pg.locator('#main-nav').is_hidden() and 'Today' in btn.inner_text(), 'choosing a page opens it and folds the list')
    bar = pg.evaluate("""() => { const c = document.getElementById('corner'), r = c.getBoundingClientRect(), ks = [...c.children].filter(x => x.getClientRects().length);
        return { inbar: !!c.querySelector('#nav-tab'), bottom: Math.round(r.bottom), h: Math.round(r.height), rows: new Set(ks.map(x => Math.round(x.getBoundingClientRect().top))).size,
                 pad: parseFloat(getComputedStyle(document.querySelector('main')).paddingBottom), tall: Math.min(...ks.map(x => x.getBoundingClientRect().height)) } }""")
    check(bar['inbar'] and bar['bottom'] == 740, 'Sections, Debug and Display share one bar at the bottom of the screen')
    check(bar['rows'] <= 2 and bar['h'] < 740 * .25, f'the bar takes at most two rows with the largest text ({bar["rows"]} rows, {bar["h"]} px)')
    check(bar['tall'] >= 44, 'each button is still at least a fingertip tall')
    check(bar['pad'] >= bar['h'], 'the end of the page can scroll clear of the bar')
    check(not pg.evaluate("document.documentElement.scrollWidth > innerWidth + 1"), 'nothing scrolls sideways')
    pg.screenshot(path=os.path.join(OUT, 'layout-3-phone-bar.png'))
    pg.goto(LOCAL + '/#/frost'); pg.wait_for_timeout(2500)
    st = pg.evaluate("""() => { const t = document.querySelector('main table.tbl'); const td = t && t.querySelector('tbody td[data-label]');
        return { stacked: !!t && t.classList.contains('stacked'), label: td ? getComputedStyle(td, '::before').content : '',
                 side: [...document.querySelectorAll('main .tbl-wrap:not(.wide)')].some(w => w.scrollWidth > w.clientWidth + 2) } }""")
    check(st['stacked'] and 'Low' in st['label'], 'a table too wide for the phone becomes one box per row, each value with its column name')
    check(not st['side'], 'no table on the page scrolls sideways')
    pg.screenshot(path=os.path.join(OUT, 'layout-4-phone-table.png'), full_page=True)
    pg.click('#nav-tab'); pg.wait_for_timeout(400)
    check(pg.locator('#sidenav').is_visible(), 'Sections still opens the menu of sections')
    pg.set_viewport_size({'width': 1920, 'height': 960}); pg.evaluate("window.PlantPrefs.set('size','100')"); pg.wait_for_timeout(800)
    check(not pg.evaluate("!!document.querySelector('#corner #nav-tab')") and pg.locator('#pages-btn').is_hidden(), 'on a wide window everything goes back to its usual place')
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All layout checks passed' if not fails else f'{len(fails)} layout check(s) failed'))
raise SystemExit(1 if fails else 0)
