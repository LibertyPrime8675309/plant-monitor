"""Checks the Undo message after a care button (prototype proto/undo-care). Start the mock server first (fresh data folder,
then Update now so the forecast and rain are filled in), then:  python3 dev/test/undo_check.py [base-url]
Screenshots: dev/tmp/shots/undo-*.png"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def get(path): return json.load(urllib.request.urlopen(BASE + path))
def log_for(code): return get('/api/care?plant=' + code)
JOBS = '#today-water > ul.jobs > li.job'
TOAST = '#toasts .undo-toast'
with sync_playwright() as p:
    b = p.chromium.launch()
    for size, (w, h) in {'laptop': (1366, 900), 'phone': (390, 844)}.items():
        for theme in ('light', 'dark'):
            pg = b.new_page(viewport={'width': w, 'height': h})
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.add_init_script("localStorage.setItem('plantdb.editor','Undo Test');localStorage.setItem('plantdb.display',JSON.stringify({theme:'%s'}))" % theme)
            pg.goto(BASE + '/#/today'); pg.wait_for_timeout(2500)
            tag = f'{size}-{theme}'
            n0 = pg.locator(JOBS).count()
            check(n0 > 1, f'{tag}: {n0} plants due for water')
            code = pg.locator(JOBS).first.get_attribute('data-code'); before = len(log_for(code))
            pg.locator(JOBS).first.locator('button[data-act=care][data-kind=water]').click(); pg.wait_for_timeout(1500)
            check(pg.locator(f'{JOBS}[data-code="{code}"]').count() == 0, f'{tag}: {code} watered and left the list')
            check(len(log_for(code)) == before + 1, f'{tag}: one care log entry added')
            t = pg.locator(TOAST)
            check(t.count() == 1 and t.locator('[data-undo=undo]').is_visible(), f'{tag}: message with an Undo button is showing')
            check('Watered' in t.inner_text() and 'Closes in' in t.inner_text(), f'{tag}: message says what was saved and when it closes')
            over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 2, f'{tag}: no sideways scrolling with the message showing')
            box = t.bounding_box(); check(box and box['x'] >= 0 and box['x'] + box['width'] <= w + 1, f'{tag}: message fits the screen width')
            pg.screenshot(path=f'{OUT}/undo-{tag}-today.png')
            t.locator('[data-undo=undo]').click(); pg.wait_for_timeout(1800)
            check(len(log_for(code)) == before, f'{tag}: Undo removed the entry')
            check(pg.locator(f'{JOBS}[data-code="{code}"]').count() == 1, f'{tag}: {code} is back on the list')
            check(pg.locator(TOAST).count() == 0, f'{tag}: the Undo message closed')
            check(pg.locator('#toasts .toast', has_text='Undone').count() == 1, f'{tag}: "Undone" message shown')
            if size == 'laptop' and theme == 'light':
                # the U key, after Still moist (focus is on the next job's button, not in a box)
                code2 = pg.locator(JOBS).first.get_attribute('data-code'); b2 = len(log_for(code2))
                pg.locator(JOBS).first.locator('button[data-kind=check]').click(); pg.wait_for_timeout(1500)
                check(len(log_for(code2)) == b2 + 1, 'Still moist logged')
                pg.keyboard.press('u'); pg.wait_for_timeout(1800)
                check(len(log_for(code2)) == b2, 'U key undid Still moist')
                # the countdown runs, and stops while the keyboard is on the message
                pg.locator(JOBS).first.locator('button[data-kind=water]').click(); pg.wait_for_timeout(1200)
                t1 = pg.locator(TOAST + ' .undo-left').inner_text(); pg.wait_for_timeout(2100)
                t2 = pg.locator(TOAST + ' .undo-left').inner_text()
                check(t1 != t2, f'countdown runs ({t1} -> {t2})')
                pg.locator(TOAST + ' [data-undo=undo]').focus(); pg.wait_for_timeout(2100)
                t3 = pg.locator(TOAST + ' .undo-left').inner_text(); pg.wait_for_timeout(2100)
                check(t3 == pg.locator(TOAST + ' .undo-left').inner_text(), 'countdown stops while focus is on the message')
                pg.keyboard.press('Tab'); pg.wait_for_timeout(200)
                check(pg.evaluate("document.activeElement.dataset.undo") == 'close', 'Tab reaches the Close button')
                pg.keyboard.press('Enter'); pg.wait_for_timeout(500)
                check(pg.locator(TOAST).count() == 0, 'Close removes the message (the watering stays)')
                check(pg.evaluate("document.activeElement && document.activeElement.tagName") == 'H1', 'focus goes to the page heading after Close')
                # someone else removed the entry first
                code3 = pg.locator(JOBS).first.get_attribute('data-code')
                pg.locator(JOBS).first.locator('button[data-kind=water]').click(); pg.wait_for_timeout(1500)
                eid = log_for(code3)[0]['id']
                urllib.request.urlopen(urllib.request.Request(BASE + f'/api/care/{eid}', method='DELETE', headers={'X-Editor': 'Someone'}))
                pg.locator(TOAST + ' [data-undo=undo]').click(); pg.wait_for_timeout(1500)
                check(pg.locator('#toasts .toast', has_text='Nothing to undo').count() == 1, 'says "Nothing to undo" when the entry was already removed')
                # change log wording
                a = get('/api/audit?n=20')
                rows = a if isinstance(a, list) else a.get('entries', [])
                check(any('Undone right after it was logged' in (r.get('note') or '') for r in rows), 'change log says "Undone right after it was logged"')
                # plant page: Watered today, then Undo (1.21.0: on a plant not watered today, since the button is off once it is)
                W = get('/api/water'); code = next(w['code'] for w in W['plants'] if w['last_water'] != W['today'])
                pg.goto(BASE + '/#/plant/' + code); pg.wait_for_timeout(2500)
                b4 = len(log_for(code))
                pg.locator('.quick-btns [data-act=care][data-kind=water]').click(); pg.wait_for_timeout(1500)
                check(len(log_for(code)) == b4 + 1 and pg.locator(TOAST).count() == 1, 'plant page: Watered today shows the Undo message')
                pg.screenshot(path=f'{OUT}/undo-{tag}-plant.png')
                pg.locator(TOAST + ' [data-undo=undo]').click(); pg.wait_for_timeout(1800)
                check(len(log_for(code)) == b4, 'plant page: Undo removed it')
                # Log other care dialog
                pg.locator('[data-act=careother]').first.click(); pg.wait_for_timeout(400)
                pg.locator('dialog[open] select[name=kind]').select_option('repot'); pg.locator('dialog[open] button[value=ok]').click(); pg.wait_for_timeout(1500)
                check(len(log_for(code)) == b4 + 1 and 'for ' in pg.locator(TOAST).inner_text(), 'Log other care shows the Undo message')
                pg.locator(TOAST + ' [data-undo=undo]').click(); pg.wait_for_timeout(1800)
                check(len(log_for(code)) == b4, 'Log other care undone')
            if size == 'phone' and theme == 'dark':
                btn = pg.locator('[data-act=careall]')
                if btn.count():
                    total = len(get('/api/care?n=2000'))
                    btn.first.click(); pg.wait_for_timeout(300); pg.locator('dialog[open] button[value=ok]').click(); pg.wait_for_timeout(2000)
                    added = len(get('/api/care?n=2000')) - total
                    check(added > 1 and f'all {added} entries' in pg.locator(TOAST).inner_text(), f'Mark all as watered: message says Undo removes all {added}')
                    pg.screenshot(path=f'{OUT}/undo-{tag}-all.png')
                    pg.locator(TOAST + ' [data-undo=undo]').click(); pg.wait_for_timeout(4000)
                    check(len(get('/api/care?n=2000')) == total, 'Undo removed every one of them')
                else: print('skip Mark all as watered (no button on this data)')
            pg.close()
    b.close()
for e in errs: print('JS error:', e)
print('\n' + ('All undo checks passed' if not fails and not errs else f'{len(fails)} failed, {len(errs)} JS errors'))
sys.exit(1 if fails or errs else 0)
