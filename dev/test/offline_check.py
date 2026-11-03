"""Checks 1.24.0: offline use. A device keeps a copy (every plant, find and photo), opens and shows it without a connection, keeps
changes made offline (watering, an edit, a move, a new mushroom find with a GPS photo, the wishlist, a picture for Identify), and
sends them when it is back online, each only once. Someone else's edits to other fields are kept; a clash on the same field
waits on "Needs your decision". Start the mock server with a fresh data folder (MOCK_TS=1), then:
python3 dev/test/offline_check.py      Screenshots: dev/tmp/shots/offline-*.png"""
import json, os, signal, subprocess, sys, time, urllib.request, urllib.error
from PIL import Image
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
HERE = os.path.dirname(os.path.abspath(__file__)); TMP = os.path.join(HERE, '..', 'tmp')
OUT = os.path.join(TMP, 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Sam at home', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'{}')
def server(up):
    """Pauses the mock server (no answer at all, like a phone with no signal) or lets it go on. Playwright's own offline switch
    does not reach the service worker's requests, so this is how the test cuts the device off."""
    for pid in subprocess.run(['pgrep', '-f', 'dev/test/mock_' + 'server'], capture_output=True, text=True).stdout.split():
        os.kill(int(pid), signal.SIGCONT if up else signal.SIGSTOP)
P = 'P-012'
plant = call('GET', f'/api/plants/{P}')[1]
im = Image.new('RGB', (1000, 750), (170, 140, 100)); ex = Image.Exif(); ex[0x8825] = {1: 'N', 2: (30.0, 31.0, 0.0), 3: 'W', 4: (97.0, 41.0, 0.0)}
GPS = os.path.join(TMP, 'offline-find.jpg'); im.save(GPS, 'JPEG', exif=ex)
BLUE = os.path.join(TMP, 'offline-id.jpg'); Image.new('RGB', (600, 600), (40, 50, 210)).save(BLUE, 'JPEG')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1280, 'height': 900})
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Ethan on the phone')")
    pg.goto(LOCAL + '/#/'); pg.wait_for_timeout(3000)
    check(pg.evaluate("navigator.serviceWorker.controller !== null || navigator.serviceWorker.ready.then(() => true)") is not None, 'the service worker is registered')
    pg.reload(); pg.wait_for_timeout(2500)
    check(pg.evaluate('!!navigator.serviceWorker.controller'), 'and controls the page after a reload')
    check(pg.locator('#net').inner_text().startswith('Online'), 'the header says "Online", in words')
    pg.click('#net'); pg.wait_for_timeout(1500)
    check(pg.evaluate('location.hash') == '#/offline' and pg.locator('h1').inner_text() == 'Offline use', 'it opens the Offline use page')
    pg.check('input[data-f=offkeep]'); pg.wait_for_timeout(2000)
    pg.fill('input[data-f=offdev]', 'Ethan\'s phone'); pg.locator('input[data-f=offdev]').dispatch_event('change')
    for _ in range(90):
        pg.wait_for_timeout(1000)
        if 'Done.' in pg.inner_text('main') or 'Last saved' in pg.inner_text('main'): break
    t = pg.inner_text('main')
    check('Last saved' in t or 'Done.' in t, '"Keep a copy on this device" saves everything (' + (pg.locator('#off-dl').inner_text() or 'no progress shown') + ')')
    n_api = pg.evaluate("caches.open('plantdb-api').then(c => c.keys()).then(k => k.length)")
    n_pic = pg.evaluate("caches.open('plantdb-photos').then(c => c.keys()).then(k => k.length)")
    check(n_api > 600 and n_pic > 300, f'answers for every page and every photo, full size and small ({n_api} answers, {n_pic} photos)')
    pg.screenshot(path=os.path.join(OUT, 'offline-1-page.png'), full_page=True)
    # no connection
    ctx.set_offline(True); server(False)
    pg.goto(LOCAL + '/#/'); pg.wait_for_timeout(14000)
    check(pg.locator('#grid .sheet').count() > 50 and pg.locator('#net').inner_text().startswith('Offline'), 'offline, the app still opens and lists the plants, and the header says "Offline"')
    check('This is what this device saved' in pg.inner_text('main'), 'with a note that this is the saved copy')
    pg.goto(LOCAL + f'/#/plant/{P}'); pg.wait_for_timeout(9000)
    check(plant['common_name'] in pg.locator('h1').inner_text(), 'a plant page opens offline')
    ok_img = pg.evaluate("Array.from(document.querySelectorAll('main img')).filter(i => (i.src.includes('/photos/') || i.src.includes('/thumbs/')) && i.loading !== 'lazy').every(i => i.complete && i.naturalWidth > 0)")
    check(ok_img, 'with its photos')
    # changes while offline
    wb = pg.locator('[data-act=care][data-kind=water]').first
    if wb.count() and wb.is_enabled(): wb.click(); pg.wait_for_timeout(1200)
    else: pg.evaluate(f"api('POST', '/api/care', {{ plant: '{P}', kind: 'water' }})"); pg.wait_for_timeout(800)
    pg.goto(LOCAL + f'/#/plant/{P}/edit'); pg.wait_for_timeout(8000)
    pg.fill('form [name=notes]', 'Edited on the phone, offline.'); pg.fill('form [name=container]', 'Blue glazed pot (phone)')
    pg.click('form[data-form=edit] button[type=submit]') if pg.locator('form[data-form=edit]').count() else pg.click('form button[type=submit]')
    pg.wait_for_timeout(9000)
    t = pg.inner_text('main')
    check('Not sent yet' in t and 'Edited on the phone, offline.' in t, 'an edit made offline shows on the page at once, marked "Not sent yet"')
    # a new mushroom find with a photo that carries its location
    pg.goto(LOCAL + '/#/fungi/new'); pg.wait_for_timeout(8000)
    pg.fill('#mu-name', 'Offline puffball'); pg.set_input_files('form[data-form=musave] input[name=photos]', [GPS])
    pg.click('form[data-form=musave] button[type=submit]'); pg.wait_for_timeout(3000)
    check(pg.evaluate('location.hash').startswith('#/fungi/NEW-') and 'Offline puffball' in pg.inner_text('main'), 'a find added offline opens with a temporary code')
    check(pg.locator('#mu-gallery img').count() == 1 and pg.evaluate("document.querySelector('#mu-gallery img').naturalWidth > 0"), 'with its photo, from this device')
    pg.click('[data-act=muident]'); pg.wait_for_timeout(1500)
    check('will be checked when you are back online' in pg.inner_text('#mu-ident'), 'Identify offline keeps the picture to check later')
    pg.goto(LOCAL + '/#/fungi'); pg.wait_for_timeout(8000)
    check(pg.locator('.mu-card', has_text='Offline puffball').count() == 1 and 'Not sent yet' in pg.inner_text('#mu-grid'), 'the Mushrooms page lists it, marked "Not sent yet"')
    pg.goto(LOCAL + '/#/species/Monstera%20deliciosa'); pg.wait_for_timeout(9000)
    pg.click('[data-act=spwish]'); pg.wait_for_timeout(1000)
    pg.goto(LOCAL + '/#/offline'); pg.wait_for_timeout(3000)
    t = pg.inner_text('main')
    check('Waiting to be sent (5)' in t and 'New mushroom find' in t and 'Watered' in t, f'the Offline page lists the 5 changes waiting')
    check('Pictures to identify' in t and 'Waiting for a connection' in t, 'and the picture waiting for Identify')
    check(pg.locator('#net').inner_text() == 'Offline · 5 to send', 'the header says how many are waiting: ' + pg.locator('#net').inner_text())
    pg.screenshot(path=os.path.join(OUT, 'offline-2-waiting.png'), full_page=True)
    # meanwhile, someone at home changes the same plant: one field the phone changed too, one it didn't
    server(True); time.sleep(2)
    cur = call('GET', f'/api/plants/{P}')[1]
    st, _ = call('PUT', f'/api/plants/{P}', {'base_version': cur['version'], 'fields': {'container': 'Terracotta (home)', 'location': 'Back porch shelf'}})
    check(st == 200, 'meanwhile, someone at home edits the same plant')
    # back online
    ctx.set_offline(False)
    pg.evaluate("window.dispatchEvent(new Event('online'))")
    for _ in range(40):
        pg.wait_for_timeout(1000)
        if pg.locator('#net').inner_text().startswith('Online') and 'to send' not in pg.locator('#net').inner_text(): break
    check('to send' not in pg.locator('#net').inner_text(), 'back online, the waiting changes are sent by themselves: ' + pg.locator('#net').inner_text())
    after = call('GET', f'/api/plants/{P}')[1]
    check(after['notes'] == 'Edited on the phone, offline.' and after['location'] == 'Back porch shelf', 'the phone\'s note and the home edit to another field are both kept')
    check(after['container'] == 'Terracotta (home)', 'the field both changed keeps the home value for now')
    care = call('GET', f'/api/care?plant={P}&n=5')[1]
    check(sum(1 for x in care if x['kind'] == 'water') == 1 and care[0]['created_by'] == 'Ethan on the phone', 'the watering made offline is logged once, by the person on the phone')
    finds = call('GET', '/api/fungi')[1]['finds']
    f = next((x for x in finds if x['name'] == 'Offline puffball'), None)
    check(f is not None and f['code'].startswith('F-') and f['photo_count'] == 1, 'the find was sent, got its F- code, with its photo')
    fd = call('GET', '/api/fungi/' + f['code'])[1] if f else {}
    check(abs((fd.get('lat') or 0) - 30.516667) < 0.001, 'and took the photo\'s location')
    check(any(w['name'] == 'Monstera deliciosa' for w in call('GET', '/api/wishlist')[1]['wishlist']), 'the wishlist change was sent')
    conf = call('GET', '/api/conflicts')[1]
    c1 = next((x for x in conf['conflicts'] if x['code'] == P and x['field'] == 'container'), None)
    check(conf['open'] == 1 and c1 and c1['phone_value'] == 'Blue glazed pot (phone)' and c1['server_value'] == 'Terracotta (home)' and c1['device'] == "Ethan's phone", 'the clash waits for a decision, with both values and the device')
    # sending the same change twice makes it once
    st1, r1 = call('POST', '/api/care', {'plant': 'P-013', 'kind': 'water'}, {'X-Offline-Op': 'test-op-0001-abcd'})
    st2, r2 = call('POST', '/api/care', {'plant': 'P-013', 'kind': 'water'}, {'X-Offline-Op': 'test-op-0001-abcd'})
    n13 = sum(1 for x in call('GET', '/api/care?plant=P-013&n=20')[1] if x['kind'] == 'water')
    check(st1 == 201 and st2 == 201 and r1 == r2 and n13 == 1, 'a change sent twice (a dropped connection) is made only once')
    # decide
    pg.goto(LOCAL + '/#/decisions'); pg.wait_for_timeout(2000)
    t = pg.inner_text('main')
    check('Blue glazed pot (phone)' in t and 'Terracotta (home)' in t and "Changed on Ethan's phone" in t, '"Needs your decision" shows both values side by side')
    pg.screenshot(path=os.path.join(OUT, 'offline-3-decide.png'), full_page=True)
    pg.locator('[data-act=decide][data-choice=phone]').first.click(); pg.wait_for_timeout(2000)
    check(call('GET', f'/api/plants/{P}')[1]['container'] == 'Blue glazed pot (phone)' and call('GET', '/api/conflicts')[1]['open'] == 0, '"Keep this" writes the chosen value and closes it')
    pg.goto(LOCAL + '/#/offline'); pg.wait_for_timeout(3000)
    t = pg.inner_text('main')
    check('It looks most like' in t, 'the picture kept for Identify was checked once back online')
    # viewers cannot keep changes
    vw = b.new_context(viewport={'width': 390, 'height': 844}, extra_http_headers={'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'})
    call('GET', '/api/me', h={'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}, base=TS)
    v = vw.new_page(); v.goto(TS + '/#/offline'); v.wait_for_timeout(2500)
    check(v.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'the Offline page fits a phone')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
