"""Checks "Copy my answers for Claude". Start the mock server first (a fresh data folder is fine), then:
  python3 dev/test/copy_check.py [base-url]        Screenshots: dev/tmp/shots/copy-*.png
It answers a request, edits a plant, moves one indoors and ticks off a photo, then checks the message, copying,
the "since I last copied" memory, the choices in the dialog, saving a text file and phone width."""
import json, os, re, sys, urllib.request
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'X-Editor': 'Copy Test', 'Content-Type': 'application/json'}, method=m)
    return json.load(urllib.request.urlopen(req))

# what a person might have done since the last message
reqs = [r for r in call('GET', '/api/requests?open=1') if r['plant_code']]
target = reqs[0]['plant_code'] if reqs else 'P-001'
p = call('GET', '/api/plants/P-024'); h_old = p['health_rating']; h_new = 'Good' if h_old == 'Fair' else 'Fair'
call('PUT', '/api/plants/P-024', {'base_version': p['version'], 'fields': {'health_rating': h_new}, 'note': 'New fronds coming in green'})
s_old = call('GET', '/api/plants/P-028')['site'] or 'Outdoors'; s_new = 'Outdoors' if s_old == 'Indoors' else 'Indoors'
call('POST', '/api/plants/P-028/site', {'site': s_new})
todo = [t for t in call('GET', '/api/to-photograph') if not t['done']]
if todo: call('PATCH', f"/api/to-photograph/{todo[0]['id']}", {'done': True})

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, accept_downloads=True)
    ctx.grant_permissions(['clipboard-read', 'clipboard-write'], origin=BASE)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Copy Test');localStorage.setItem('plantdb.display',JSON.stringify({layout:'single',navopen:'0'}))")
    # answer a request on a plant page, the way Ethan would
    pg.goto(f'{BASE}/#/plant/{target}'); pg.wait_for_timeout(2000)
    pg.locator('#needs button[data-act=reqanswer]').first.click(); pg.wait_for_timeout(300)
    pg.fill('dialog[open] textarea[name=answer]', 'It tastes very sweet, like sugar.'); pg.locator('dialog[open] button[value=ok]').click(); pg.wait_for_timeout(1500)
    check(pg.locator('#needs button[data-act=forclaude]').count() == 1, 'plant page: "Copy my answers for Claude" button in Needed from you')
    # Plants page shows how many answers are new
    pg.goto(BASE + '/#/plants'); pg.wait_for_timeout(2000)
    btn = pg.locator('.needs-bar button[data-act=forclaude]')
    label = btn.inner_text() if btn.count() else ''
    check(re.search(r'\(\d+ new\)', label) is not None, 'Plants page button says how many are new: ' + label)
    btn.click(); pg.wait_for_timeout(800)
    text = pg.locator('#fc-text').input_value()
    check('It tastes very sweet, like sugar.' in text, 'the message has the answer')
    check(f'Health rating: from {h_old} to {h_new}' in text and f'Location: from {s_old} to {s_new}' in text, 'the message has the page changes')
    check(not todo or ('Ticked off: ' + todo[0]['label']) in text, 'the message says which photo was ticked off')
    check(pg.evaluate('document.activeElement && document.activeElement.dataset.act') == 'fccopy', 'focus starts on Copy message')
    pg.screenshot(path=f'{OUT}/copy-dialog.png')
    pg.locator('button[data-act=fccopy]').click(); pg.wait_for_timeout(800)
    clip = pg.evaluate('navigator.clipboard.readText()')
    check(clip == text, 'Copy message puts the whole message on the clipboard')
    check('Copied' in pg.locator('#fc-status').inner_text(), 'it says it was copied (inside the dialog, where it can be seen)')
    pg.locator('dialog[open] button[value=close]').click(); pg.wait_for_timeout(300)
    check(pg.locator('.needs-bar .fc-n').count() == 0, 'the "(new)" count goes once copied')
    # next time starts from the copy
    pg.goto(BASE + '/#/history'); pg.goto(BASE + '/#/plants'); pg.wait_for_timeout(1800)
    pg.locator('.needs-bar button[data-act=forclaude]').click(); pg.wait_for_timeout(800)
    check('Nothing new from me' in pg.locator('#fc-text').input_value(), 'opening it again: nothing new since the copy')
    pg.select_option('select[data-act=fcrange]', 'all'); pg.wait_for_timeout(800)
    check('It tastes very sweet' in pg.locator('#fc-text').input_value(), 'Everything brings the answer back')
    check(pg.evaluate('document.activeElement && document.activeElement.dataset.act') == 'fcrange', 'focus stays on the menu')
    pg.locator('input[data-act=fcopen]').check(); pg.wait_for_timeout(800)
    check('Still open (' in pg.locator('#fc-text').input_value(), '"Also list what is still open" lists them')
    with pg.expect_download() as dl:
        pg.locator('button[data-act=fcsave]').click()
    d = dl.value; path = os.path.join(OUT, 'copy-download.txt'); d.save_as(path)
    check(re.match(r'plant-record-for-claude-\d{8}-\d{4}\.txt$', d.suggested_filename) is not None, 'Save as a text file: ' + d.suggested_filename)
    check('It tastes very sweet' in open(path, encoding='utf-8').read(), 'the file has the same message')
    pg.screenshot(path=f'{OUT}/copy-dialog-everything.png')
    pg.close()
    # phone, dark, biggest text
    q = ctx.new_page(); q.set_viewport_size({'width': 390, 'height': 844}); q.on('pageerror', lambda e: errs.append(str(e)))
    q.add_init_script("localStorage.setItem('plantdb.display',JSON.stringify({theme:'dark',size:'190'}))")
    q.goto(BASE + '/#/plants'); q.wait_for_timeout(2000)
    q.evaluate("document.querySelector('.needs-bar button[data-act=forclaude]').click()"); q.wait_for_timeout(800)   # the phone top bar can cover it
    q.screenshot(path=f'{OUT}/copy-phone-dark.png')
    over = q.evaluate('document.getElementById("dlg").scrollWidth - document.getElementById("dlg").clientWidth')
    check(over <= 2, f'phone, largest text: nothing in the dialog scrolls sideways ({over}px)')
    q.close(); b.close()
    # opened by a network address (like a phone on the home Wi-Fi): no clipboard API there, so it selects and copies
    port = BASE.rsplit(':', 1)[-1].strip('/')
    b2 = pw.chromium.launch(args=['--host-resolver-rules=MAP plants.test 127.0.0.1'])
    r = b2.new_page(); r.on('pageerror', lambda e: errs.append(str(e)))
    r.add_init_script("localStorage.setItem('plantdb.editor','Copy Test')")
    r.goto(f'http://plants.test:{port}/#/plants'); r.wait_for_timeout(2000)
    r.locator('.needs-bar button[data-act=forclaude]').click(); r.wait_for_timeout(800)
    r.locator('button[data-act=fccopy]').click(); r.wait_for_timeout(800)
    check(not r.evaluate('window.isSecureContext') and 'Copied' in r.locator('#fc-status').inner_text(), 'copying works on a page opened by a network address too')
    b2.close()
log = call('GET', '/api/audit?limit=50')
check(any(a['note'] == 'Copied my answers for Claude' for a in log), 'the change log notes when it was copied')
for e in errs: print('JS error:', e)
sys.exit(1 if fails or errs else 0)
