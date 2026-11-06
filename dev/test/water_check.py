"""Checks 1.21.0: "Watered today" on a plant page is switched off for the rest of the day once pressed (Undo or Remove switch it
back on), the server never logs a second watering for the same day, and "Water all" on the Plants page waters every plant
the filters show, skipping those already watered today. Start the mock server with a fresh data folder, then:
python3 dev/test/water_check.py      Screenshots: dev/tmp/shots/water-*.png"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Water Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
W = call('GET', '/api/water'); today = W['today']
watered = lambda: {w['code'] for w in call('GET', '/api/water')['plants'] if w['last_water'] == today}
todays = lambda code: [e for e in call('GET', f'/api/care?plant={code}') if e['kind'] == 'water' and e['done_on'] == today]
r = call('POST', '/api/care', {'plant': 'P-002', 'kind': 'water'})
r2 = call('POST', '/api/care', {'plant': 'P-002', 'kind': 'water'})
check(len(r['ids']) == 1 and r2['ids'] == [] and r2['skipped'] == ['P-002'] and len(todays('P-002')) == 1, 'the server logs one watering a day: a second one is skipped, not added')
call('POST', '/api/care', {'plant': 'P-002', 'kind': 'check'}); call('POST', '/api/care', {'plant': 'P-002', 'kind': 'check'})
check(len([e for e in call('GET', '/api/care?plant=P-002') if e['kind'] == 'check']) == 2, 'other kinds of care can still be logged more than once a day')
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Water Test');localStorage.removeItem('plantdb.filters')")
    pg.goto(BASE + '/#/plant/P-006'); pg.wait_for_timeout(2500)
    btn = pg.locator('.quick-btns [data-act=care][data-kind=water]')
    check(btn.is_enabled() and btn.inner_text() == 'Watered today' and pg.locator('#water-done-note').is_hidden(), 'before watering, "Watered today" can be pressed')
    btn.click(); pg.wait_for_timeout(1500)
    check(btn.is_disabled() and btn.inner_text() == '✓ Watered today' and pg.locator('#water-done-note').is_visible(), 'after pressing it, it says "✓ Watered today" and is switched off, with a note saying why')
    check(pg.evaluate("getComputedStyle(document.querySelector('.quick-btns [data-kind=water]')).opacity") == '1', 'the switched-off button is not faded (full contrast)')
    pg.screenshot(path=os.path.join(OUT, 'water-1-done.png'), clip=pg.locator('.quick').bounding_box())
    pg.reload(); pg.wait_for_timeout(2500)
    check(btn.is_disabled(), 'it stays off when the page is opened again the same day')
    call('POST', '/api/care', {'plant': 'P-007', 'kind': 'water'})
    pg.goto(BASE + '/#/plant/P-007'); pg.wait_for_timeout(2500)
    check(btn.is_disabled(), 'it is also off when the plant was watered from somewhere else today')
    pg.goto(BASE + '/#/plant/P-008'); pg.wait_for_timeout(2500)
    btn.click(); pg.wait_for_timeout(1500)
    pg.locator('.undo-toast [data-undo=undo]').click(); pg.wait_for_timeout(1800)
    check(btn.is_enabled() and btn.inner_text() == 'Watered today' and not todays('P-008'), 'Undo takes the watering back and switches the button on again')
    # Water all on the Plants page
    pg.goto(BASE + '/#/plants'); pg.wait_for_timeout(2500)
    pg.select_option('select[data-f=site]', 'Covered porch'); pg.wait_for_timeout(600)
    shown = [x for x in pg.locator('#grid .sheet').evaluate_all('els => els.map(e => e.dataset.code)')]
    wa = pg.locator('#wa-btn')
    check(wa.inner_text() == f'Water all {len(shown)} shown' and len(shown) > 3, f'the Plants page has "Water all {len(shown)} shown", following the filters')
    before = watered() & set(shown)
    check(len(before) >= 1, f'some plants shown were already watered today ({sorted(before)})')
    wa.click(); pg.wait_for_selector('dialog[open]')
    t = pg.inner_text('dialog[open]')
    check(f'Mark {len(shown) - len(before)} plant' in t and 'already watered today and' in t, 'it asks first, and says how many are skipped as already watered')
    pg.screenshot(path=os.path.join(OUT, 'water-2-all.png'))
    pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(1800)
    check(set(shown) <= watered(), 'every plant shown is now watered today')
    check(all(len(todays(c)) == 1 for c in shown), 'and none of them has two waterings for today')
    other = [w['code'] for w in call('GET', '/api/water')['plants'] if w['site'] != 'Covered porch']
    check(not (set(other) & watered() - {'P-002', 'P-006', 'P-007'}), 'plants the filters hid were not touched')
    check('marked as watered' in pg.inner_text('#toasts') and pg.locator('.undo-toast [data-undo=undo]').count() == 1, 'the message has Undo, as for the other care buttons')
    pg.locator('.undo-toast [data-undo=undo]').click(); pg.wait_for_timeout(2000)
    check(watered() & set(shown) == before, 'Undo takes back only the ones it watered')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
