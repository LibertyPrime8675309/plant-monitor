"""Checks 1.52.0 (PLAN.md step 5c): the loop. On an Identify result every species name has "This is right" beside "Not this"
(editors and the owner; not viewers); both send the picture, which becomes an example the checker learns from (id_examples, a
file in data/photos); a plant's own page confirms with the plant's photo; the status line says what it has learned.
Start the mock server with a fresh data folder, then:  python3 dev/test/idloop_check.py [base]      Screenshots: dev/tmp/shots/idloop-*.png"""
import json, os, sys, urllib.request
from PIL import Image
from playwright.sync_api import sync_playwright
LOCAL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = LOCAL.rsplit(':', 1)[0] + ':' + str(int(LOCAL.rsplit(':', 1)[1]) + 1)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp')
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(LOCAL + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Loop Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
green = os.path.join(TMP, 'loop-green.png'); Image.new('RGB', (160, 160), (20, 160, 40)).save(green, 'PNG')
FIXED = "localStorage.setItem('plantdb.idmode',JSON.stringify({identify:'new',add:'new',plant:'mine'}))"
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '404' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Loop Test');" + FIXED)
    pg.goto(LOCAL + '/#/identify'); pg.wait_for_timeout(2500)
    check('learned from 2 confirmed pictures and 1 said' in pg.inner_text('#id-st'), 'the status line says what the checker has learned (the fake checker: 2 confirmed, 1 rejected)')
    pg.set_input_files('input[data-act=idfile]', green); pg.wait_for_selector('dialog[open] .id-pop, #id-res .id-sp', timeout=10000); pg.wait_for_timeout(500)
    if pg.locator('dialog[open]').count(): pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    cards = pg.locator('#id-res .id-sp')
    right = pg.locator('#id-res [data-act=idright]')
    check(cards.count() >= 3 and right.count() == cards.count(), f'every name card ({cards.count()}) has a "This is right" button beside "Not this"')
    check(all('This is right:' in (a or '') for a in [right.nth(i).get_attribute('aria-label') for i in range(right.count())]), 'each says which name it confirms')
    name = right.first.get_attribute('data-name')
    right.first.click(); pg.wait_for_timeout(1500)
    check(name in pg.inner_text('#toasts') and 'example' in pg.inner_text('#toasts'), f'pressing it says the picture was saved as an example of {name}')
    check(right.first.inner_text() == 'Confirmed' and right.first.is_disabled(), 'and the button reads Confirmed')
    ex = call('GET', '/api/identify/examples')
    check(ex['total'] == 1 and ex['examples'][0]['name'] == name and ex['examples'][0]['yes'] == 1, 'the example is kept')
    pg.screenshot(path=os.path.join(OUT, 'idloop-1-right.png'), full_page=False)
    # Not this, with the picture
    other = pg.locator('#id-res [data-act=idnot]:not([data-genus])').nth(1); nname = other.get_attribute('data-name')
    other.click(); pg.wait_for_timeout(2500)
    ex = call('GET', '/api/identify/examples')
    row = next((e for e in ex['examples'] if e['name'] == nname), None)
    check(ex['total'] == 2 and row and row['no'] == 1, f'"Not this" with a picture keeps it as a picture that is not {nname}')
    check(nname not in [c.inner_text().split('\n')[0] for c in pg.locator('#id-res .id-sp .sci').all()], 'and the name leaves the list, as before')
    # the audit log says who
    aud = call('GET', '/api/audit?limit=20')
    check(any('Confirmed: this picture is' in str(x.get('note', '')) and x.get('changed_by', x.get('who', '')) == 'Loop Test' for x in aud), 'the audit log has the confirmation, with who')
    # a plant's own page: This is right with the plant's photo
    pg.goto(LOCAL + '/#/plant/P-001'); pg.wait_for_timeout(2000)
    if pg.locator('[data-act=plantid]').count():
        pg.locator('[data-act=plantid]').first.click(); pg.wait_for_selector('#plant-id .id-sp', timeout=10000); pg.wait_for_timeout(300)
        pr = pg.locator('#plant-id [data-act=idright]')
        check(pr.count() >= 1 and pr.first.get_attribute('data-code') == 'P-001', 'a plant\'s page has "This is right" on each name, for the plant\'s own photo')
        pname = pr.first.get_attribute('data-name'); pr.first.click(); pg.wait_for_timeout(1500)
        ex = call('GET', '/api/identify/examples')
        check(any(e['name'] == pname and e['yes'] >= 1 for e in ex['examples']) and ex['total'] == 3, 'confirming there keeps the plant\'s photo as the example')
    # a viewer sees neither Not this nor This is right (the first person through Tailscale is the owner; the viewer is the second)
    urllib.request.urlopen(urllib.request.Request(TS + '/api/me', headers={'Tailscale-User-Login': 'owner@example.com', 'Tailscale-User-Name': 'Own'})).read()
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers={'Tailscale-User-Login': 'viewer@example.com', 'Tailscale-User-Name': 'Vee'})
    vw.add_init_script(FIXED)
    vw.goto(TS + '/#/identify'); vw.wait_for_timeout(2500)
    vw.set_input_files('input[data-act=idfile]', green); vw.wait_for_selector('dialog[open] .id-pop, #id-res .id-sp', timeout=10000); vw.wait_for_timeout(500)
    if vw.locator('dialog[open]').count(): vw.keyboard.press('Escape'); vw.wait_for_timeout(400)
    check(vw.locator('#id-res .id-sp').count() >= 3 and vw.locator('#id-res [data-act=idright]:visible').count() == 0, 'a viewer gets the names but no "This is right"')
    vw.close()
    for e in errs: check(False, 'browser error: ' + e)
    b.close()
print(f'\n{len(fails)} failed' if fails else '\nall good')
sys.exit(1 if fails else 0)
