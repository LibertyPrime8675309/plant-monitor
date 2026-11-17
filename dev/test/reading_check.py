"""Checks the colour themes, colour-vision colours and reading settings of 1.58.0 (Display → Text and colours, and Reading):

- Cream paper on a computer, Soft dark on a phone, and red-green colours on a dark phone: all text on every page in the top bar
  (and a few more) is 7 to 1 or better against what is behind it.
- The reading settings at their strongest (OpenDyslexic, one plain font, Widest spacing, Largest text) on a phone: no page
  scrolls sideways, headings are in the reading font, and Latin names are upright.
- Display: Easier reading sets the reading settings together and "Put back how it was" undoes it; the choices survive a reload.
- A device set to more contrast gets high contrast while Contrast is "Match my device"; health tags carry a symbol.
- From the dyslexia audit: search finds close spellings and says so; messages stay, with Close and Recent messages; short forms are
  explained once a page; Words used in the app; the reading guide follows the pointer; page tints keep 7 to 1.
Start the mock server with a fresh data folder, then:  python3 dev/test/reading_check.py [base-url]"""
import sys, json
from playwright.sync_api import sync_playwright
from waits import until
from contrast_js import CONTRAST
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)

def context(b, vp, mob, prefs, **kw):
    ctx = b.new_context(viewport={'width': vp[0], 'height': vp[1]}, is_mobile=mob, has_touch=mob, service_workers='block', **kw)
    ctx.add_init_script("localStorage.setItem('plantdb.editor','Reading Test');if(!sessionStorage.getItem('rc')){sessionStorage.setItem('rc','1');localStorage.setItem('plantdb.display',%s)}" % json.dumps(json.dumps(prefs)))
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    return ctx, pg

def open_page(pg, h):
    pg.goto(BASE + '/' + h)
    until(pg, lambda: pg.locator('#app h1').count() > 0 and pg.locator('#app[aria-busy=true]').count() == 0)
    pg.wait_for_timeout(1200)                                                # the parts a page fills in after it is drawn

with sync_playwright() as p:
    b = p.chromium.launch()
    pages = None
    for name, vp, mob, prefs in [('computer, Cream paper', (1707, 960), False, {'theme': 'cream'}),
                                 ('phone, Soft dark', (412, 915), True, {'theme': 'softdark'}),
                                 ('phone, Dark with red-green colours', (412, 915), True, {'theme': 'dark', 'cvd': 'rg'})]:
        ctx, pg = context(b, vp, mob, prefs)
        open_page(pg, '#/')
        if pages is None:
            pages = pg.evaluate("[...new Set(SECTIONS.flatMap(s => s[2].map(x => x[2])))]") + ['#/plant/P-031', '#/plant/P-031/edit', '#/health']
        bad = {}
        for h in pages:
            open_page(pg, h)
            c = pg.evaluate(CONTRAST)
            if c: bad[h] = c
        check(not bad, f'{name}: on {len(pages)} pages all text is at 7 to 1 or better' + (': ' + '; '.join(f'{h} {v[0]} ({len(v)})' for h, v in list(bad.items())[:4]) if bad else ''))
        ctx.close()

    # the reading settings at their strongest, on a phone
    ctx, pg = context(b, (412, 915), True, {'font': 'dyslexic', 'plain': '1', 'space': 'widest', 'size': '190', 'theme': 'cream'})
    open_page(pg, '#/')
    check(pg.evaluate("['data-font','data-plain','data-space','data-tone'].map(a => document.documentElement.getAttribute(a)).join()") == 'dyslexic,1,widest,cream',
          'the reading settings are on the page before it is drawn')
    wide = []
    for h in pages:
        open_page(pg, h)
        if pg.evaluate('document.documentElement.scrollWidth > innerWidth + 1'): wide.append(h)
    check(not wide, f'phone, OpenDyslexic, Widest spacing and Largest text: no page scrolls sideways' + (': ' + ', '.join(wide) if wide else ''))
    open_page(pg, '#/plant/P-031')
    check('OpenDyslexic' in pg.evaluate("getComputedStyle(document.querySelector('#app h1')).fontFamily"), 'headings are in the reading font')
    lat = pg.evaluate("(() => { const e = document.querySelector('.latin, i'); return e ? getComputedStyle(e).fontStyle : 'none'; })()")
    check(lat in ('normal', 'none'), f'Latin names are upright ({lat})')
    ctx.close()

    # Easier reading in Display, and putting it back
    ctx, pg = context(b, (1707, 960), False, {'theme': 'light'})
    open_page(pg, '#/plants')
    tag = pg.locator('.tag.h-good').first
    if tag.count(): check(pg.evaluate("e => getComputedStyle(e, '::before').content", tag.element_handle()).startswith('"✓'), 'a Good health tag shows ✓ as well as its colour')
    pg.locator('#display-btn').click(); until(pg, lambda: pg.locator('dialog[open] #dv-easy').count() > 0)
    pg.locator('[data-act=easyread]').click()
    attrs = lambda: pg.evaluate("['data-font','data-plain','data-space','data-tone','data-theme'].map(a => document.documentElement.getAttribute(a)).join()")
    check(until(pg, lambda: attrs() == 'lexend,1,roomy,cream,light'), f'Easier reading: Lexend, one plain font, Roomy, Cream paper ({attrs()})')
    check(pg.evaluate("window.PlantPrefs.get().lines") == 'short', 'and shorter lines')
    check(pg.locator('#dv-easy').inner_text().find('Easier reading is on') >= 0, 'the window says it is on')
    pg.reload(); until(pg, lambda: pg.locator('#app h1').count() > 0)
    check(attrs() == 'lexend,1,roomy,cream,light', 'it is still on after a reload')
    pg.locator('#display-btn').click(); until(pg, lambda: pg.locator('dialog[open] [data-act=easyundo]').count() > 0)
    pg.locator('[data-act=easyundo]').click()
    check(until(pg, lambda: attrs() == 'atkinson,0,normal,,light'), f'"Put back how it was" puts back the settings before ({attrs()})')
    pg.keyboard.press('Escape')
    # the colour-vision setting changes the status colours
    before = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--moss').trim()")
    pg.evaluate("window.PlantPrefs.set('cvd', 'rg')")
    after = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--moss').trim()")
    check(before != after and after == '#1f1f90', f'red-green colours: good is blue ({before} → {after})')
    ctx.close()

    # 1.58.0, the dyslexia audit: search forgives spelling, messages stay, short forms in plain words, the reading guide, a page tint
    ctx, pg = context(b, (1707, 960), False, {'theme': 'light'})
    open_page(pg, '#/plants')
    box = pg.locator('#app input[type=search]').first
    box.fill('filodendron'); pg.wait_for_timeout(600)
    cnt = pg.locator('#count').inner_text()
    check(pg.locator('#grid .sheet').count() > 0 and 'close spellings' in cnt and 'Philodendron' in cnt, f'Plants: "filodendron" finds the philodendrons and says so ({cnt})')
    box.fill('philodendron'); pg.wait_for_timeout(600)
    check('close spellings' not in pg.locator('#count').inner_text(), 'spelt right, it says nothing about spelling')
    box.fill('')
    pg.evaluate("searchDialog()")
    q = pg.locator('#srch-q')
    if until(pg, lambda: q.count() > 0):
        q.fill('monstra')
        check(until(pg, lambda: pg.locator('.srch-close').count() > 0 and 'Monstera' in pg.locator('#srch-res').inner_text()), 'Search: "monstra" finds Monstera, with "Showing close spellings, such as Monstera"')
    pg.evaluate("document.querySelectorAll('dialog[open]').forEach(d => d.close())")
    pg.evaluate("toast('Saved the changes to the test page')")
    t = pg.locator('#toasts .toast').last
    check(t.locator('button.toast-x').count() == 1, 'a message has a Close button')
    pg.wait_for_timeout(4500)
    check(t.count() == 1 and t.is_visible(), 'a message is still there after 4.5 seconds (it used to go after 3.5)')
    t.locator('button.toast-x').click()
    check(until(pg, lambda: pg.locator('#toasts .toast', has_text='Saved the changes to the test page').count() == 0), 'Close takes it away')
    pg.evaluate("recentMsgsDialog()")
    check(until(pg, lambda: 'Saved the changes to the test page' in pg.locator('dialog[open] .msgs-list').inner_text()), 'Settings: Recent messages has it, to read again')
    # a message shown while a window is open sits above that window, and its Close button works
    pg.evaluate("toast('Shown above the open window')")
    t = pg.locator('#toasts .toast', has_text='Shown above the open window')
    check(until(pg, lambda: t.count() == 1) and pg.evaluate("!!document.querySelector('dialog[open] #toasts')"), 'a message shown while a window is open goes into that window, above it')
    hit = pg.evaluate("(() => { const b = [...document.querySelectorAll('#toasts .toast-x')].pop().getBoundingClientRect(); const e = document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2); return !!(e && e.closest('.toast-x')); })()")
    check(hit, 'and nothing covers its Close button')
    r = t.bounding_box(); vw = pg.viewport_size['width']
    check(r and r['x'] > vw / 2 - 40 and r['x'] + r['width'] <= vw, f'on a wide screen messages sit at the right, not over the middle (left edge {int(r["x"]) if r else "?"} of {vw})')
    t.locator('button.toast-x').click()
    check(until(pg, lambda: t.count() == 0), 'Close takes it away inside the window too')
    pg.evaluate("document.querySelectorAll('dialog[open]').forEach(d => d.close())")
    check(until(pg, lambda: pg.evaluate("document.getElementById('toasts').parentElement === document.body")), 'when the window closes, messages go back to the page')
    open_page(pg, '#/lights')
    abx = pg.locator('#app .abx')
    fors = abx.evaluate_all("xs => xs.map(x => x.dataset.for)")
    check(len(fors) > 0 and len(fors) == len(set(fors)), f'Grow lights: short forms explained once each ({", ".join(fors[:6])})')
    pg.evaluate("window.PlantPrefs.set('abbr', '0')")
    check(pg.locator('#app .abx').count() == 0, 'and the brackets go when Short forms is off')
    pg.evaluate("window.PlantPrefs.set('abbr', '1')")
    open_page(pg, '#/words')
    check(pg.locator('.words-row').count() >= 15 and 'PPFD' in pg.locator('main').inner_text(), 'Words used in the app lists the short forms')
    pg.evaluate("window.PlantPrefs.set('guide', '1')"); pg.mouse.move(600, 400); pg.wait_for_timeout(300)
    g = pg.locator('.rguide')
    check(g.count() == 1 and g.is_visible() and abs(g.bounding_box()['y'] + g.bounding_box()['height'] / 2 - 400) < 4, 'the reading guide follows the pointer')
    check(g.evaluate("e => getComputedStyle(e).pointerEvents") == 'none', 'and never takes a click')
    pg.evaluate("window.PlantPrefs.set('guide', '0')")
    check(not g.is_visible(), 'it goes when turned off')
    for tint in ('blue', 'green', 'peach'):
        pg.evaluate(f"window.PlantPrefs.set('tint', '{tint}')")
        check(pg.evaluate("document.documentElement.dataset.tint") == tint and pg.evaluate("getComputedStyle(document.body).backgroundColor") != 'rgb(243, 246, 244)', f'page tint {tint} changes the page colour')
    open_page(pg, '#/plants')
    c = pg.evaluate(CONTRAST)
    check(not c, 'with a page tint all text is still at 7 to 1' + (': ' + c[0] if c else ''))
    pg.evaluate("window.PlantPrefs.set('theme', 'dark')")
    check(pg.evaluate("document.documentElement.dataset.tint") is None, 'a page tint is for light pages only')
    ctx.close()

    # a device that asks for more contrast
    ctx, pg = context(b, (1280, 900), False, {}, contrast='more')
    open_page(pg, '#/')
    check(pg.evaluate("document.documentElement.dataset.contrast") == 'high', 'a device set to more contrast gets high contrast while Contrast is "Match my device"')
    pg.evaluate("window.PlantPrefs.set('contrast', 'normal')")
    check(pg.evaluate("document.documentElement.dataset.contrast") == 'normal', 'choosing Normal overrides the device')
    ctx.close()
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All reading checks passed' if not fails else f'{len(fails)} reading check(s) failed'))
sys.exit(1 if fails else 0)
