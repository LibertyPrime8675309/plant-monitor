"""Checks 1.33.0: notifications (each person's own devices and choices, cold nights, Shopping alerts, what is due, requests), the
second copy of backups (a folder, and the receiver on another computer), and search everywhere. The mock server stands in for
the push service (/mock/pushed) and this check starts a receiver of its own. Start the mock server with a fresh data folder
(MOCK_TS=1), then:  python3 dev/test/reach_check.py      Screenshots: dev/tmp/shots/reach-*.png"""
import json, os, secrets, shutil, subprocess, sys, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
RECV = os.path.join(HERE, '..', 'tmp', 'received'); shutil.rmtree(RECV, ignore_errors=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Reach Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'gf@example.net', 'Tailscale-User-Name': 'Partner'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)
pushed = lambda: call('GET', '/mock/pushed')[1]['pushed']
sub = lambda who, dev, ep: call('POST', '/api/push/subscribe', {'endpoint': 'https://push.example/' + ep, 'keys': {'p256dh': 'BPk', 'auth': 'aa'}, 'device': dev}, who, TS)

# devices and choices
k = call('GET', '/api/push', h=E, base=TS)[1]
check(len(k['key']) > 60 and len(k['kinds']) == 6 and all(x['on'] for x in k['kinds']), 'everyone starts with the six kinds on, and the page gets the key it needs')
check(sub(E, 'Windows PC, Chrome', 'ethan-pc')[0] == 200 and sub(E, 'Android phone, Chrome', 'ethan-phone')[0] == 200, 'a device can be added for Ethan')
check(sub(V, 'iPhone, Safari', 'gf-phone')[0] == 200, 'and one for someone who can only view (their own devices)')
check(call('POST', '/api/push/subscribe', {'endpoint': 'ftp://x', 'keys': {'p256dh': 'a', 'auth': 'b'}}, E, TS)[0] == 400, 'a bad address is refused')
check(call('GET', '/api/push', h=E, base=TS)[1]['devices'].__len__() == 2 and len(call('GET', '/api/push', h=V, base=TS)[1]['devices']) == 1, 'each person sees only their own devices')
call('DELETE', '/mock/pushed')
r = call('POST', '/api/push/test', {}, E, TS)[1]
P = pushed()
check(r['sent'] == 2 and len(P) == 2 and {p['device'] for p in P} == {'Windows PC, Chrome', 'Android phone, Chrome'} and P[0]['title'] == 'Plant record', 'a test goes to that person\'s devices only')
# choices
call('PUT', '/api/me/prefs', {'push.shopping': '0'}, V, TS)
check(not next(x for x in call('GET', '/api/push', h=V, base=TS)[1]['kinds'] if x['key'] == 'shopping')['on'], 'a kind can be turned off for your own sign-in')
# a device the push service says is gone is dropped
sub(E, 'Old tablet', 'gone-tablet'); call('DELETE', '/mock/pushed'); call('POST', '/api/push/test', {}, E, TS)
check(len(call('GET', '/api/push', h=E, base=TS)[1]['devices']) == 2, 'a device the push service says is gone is dropped')
# shopping alerts: a store check with an alert sends one (to Ethan, not to her: she turned them off)
call('PUT', '/api/wishlist', {'name': 'Lupinus texensis', 'common_name': 'Texas bluebonnet', 'max_price': 5})
for s in call('GET', '/api/shops')[1]['shops']:
    if s['key'] != 'snoopers': call('PUT', '/api/shops', {'key': s['key'], 'enabled': False})
call('PUT', '/api/shops', {'key': 'snoopers', 'url': 'http://127.0.0.1:8090/mock/shop/page'})
call('DELETE', '/mock/pushed'); call('POST', '/api/wishlist/check', {})
for _ in range(60):
    time.sleep(0.5)
    if not call('GET', '/api/wishlist/check')[1]['busy']: break
P = pushed()
check(len(P) == 2 and all(p['kind'] == 'shopping' and p['login'] == 'ethan@example.com' and 'bluebonnet' in p['body'].lower() for p in P), f'a Shopping alert is sent to the devices of the people who want them ({len(P)} sent)')
# cold nights and what is due, for the home each person starts on
nc = [h for h in call('GET', '/api/people', h=E, base=TS)[1]['homes'] if h['name'].startswith('Nevada')][0]['id']
call('PUT', '/api/people', {'login': 'gf@example.net', 'home_id': nc}, E, TS)
call('DELETE', '/mock/pushed'); call('POST', '/mock/push/run', {'what': 'cold'})
P = pushed()
check(all(p['kind'] == 'cold' for p in P) and (not P or {p['login'] for p in P} <= {'ethan@example.com'}), f'cold-night messages go by home: {len(P)} for Round Rock (its forecast), none for Nevada City (no forecast yet)')
n1 = len(P); call('POST', '/mock/push/run', {'what': 'cold'})
check(len(pushed()) == n1, 'and the same cold night is not sent twice')
call('DELETE', '/mock/pushed'); call('POST', '/mock/push/run', {'what': 'due'})
P = pushed()
check(all(p['kind'] == 'due' and p['login'] == 'ethan@example.com' and 'Today at Round Rock' in p['title'] for p in P), f'the morning message says what is due at that home ({len(P)} sent, {P[0]["title"] if P else ""})')
# requests from Claude: added by a batch
import sqlite3
# (requests_add runs inside apply_batches; a direct call to push_requests stands in for it here)
call('DELETE', '/mock/pushed')
# search
r = call('GET', '/api/search?q=aloe')[1]
kinds = {g['kind']: g for g in r['groups']}
check('plants' in kinds and any('P-014' in i['title'] for i in kinds['plants']['items']), 'search finds plants by name')
r = call('GET', '/api/search?q=peaceful')[1]; kinds = {g['kind']: g for g in r['groups']}
check('stores' in kinds and kinds['stores']['items'][0]['href'] == '#/store/peacefulvalley', 'and stores')
r = call('GET', '/api/search?q=garage')[1]; kinds = {g['kind']: g for g in r['groups']}
check('where' in kinds and any(i['title'] == 'Garage' for i in kinds['where']['items']), 'and rooms')
check(call('GET', '/api/search?q=a')[1]['groups'] == [], 'one letter is too little')
# backup copies: a receiver on another port, and the folder
tok = secrets.token_hex(8)
recv = subprocess.Popen([sys.executable, os.path.join(ROOT, 'receiver', 'receiver.py')], env=dict(os.environ, BACKUP_TOKEN=tok, RECEIVE_DIR=RECV, PORT='8099'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(1.5)
    check(call('PUT', '/api/backups/copies', {'url': 'nonsense', 'token': tok}, E, TS)[0] == 400, 'the receiver address must look like an address')
    check(call('PUT', '/api/backups/copies', {'url': 'http://127.0.0.1:8099', 'token': tok}, V, TS)[0] == 403, 'only the owner sets it')
    st, C = call('PUT', '/api/backups/copies', {'url': 'http://127.0.0.1:8099', 'token': tok}, E, TS)
    check(st == 200 and C['have_token'] and C['url'] == 'http://127.0.0.1:8099', 'the owner can set the other computer')
    call('POST', '/api/backups', {'photos': False, 'note': 'copy test'}, E, TS)
    for _ in range(40):
        time.sleep(0.5)
        if not call('GET', '/api/backups/job')[1].get('running'): break
    time.sleep(2)
    C = call('GET', '/api/backups/copies')[1]; st = C['status']
    check(st.get('receiver', '').startswith('received by') and len([f for f in os.listdir(RECV) if f.endswith('.zip')]) == 1, f'a new backup is sent to the other computer by itself ({st.get("receiver")})')
    call('PUT', '/api/backups/copies', {'token': 'wrong'}, E, TS)
    st, r = call('POST', '/api/backups/copies', {}, E, TS)
    check(st == 200 and 'failed' in r['status'].get('receiver', '') and call('GET', '/api/problems')[1]['open'] >= 1, 'a wrong token fails, and lands on the Problems list')
    j = call('GET', '/api/jobs')[1]
    check(any(d['kind'] == 'copy' for d in j['done']), 'copies show on the Jobs list')
finally: recv.terminate()
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1400, 'height': 900}, extra_http_headers=E); ctx.add_init_script("localStorage.setItem('plantdb.editor','Ethan')")
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(TS + '/#/settings'); pg.wait_for_timeout(2500)
    pg.locator('[data-act=notify]').click(); pg.wait_for_timeout(1500)
    t = pg.locator('#dlg').inner_text()
    check('Cold nights' in t and 'Your devices (2)' in t and pg.locator('#dlg [data-f=pushkind]').count() == 6, 'the Notifications window lists the choices and your devices')
    pg.screenshot(path=os.path.join(OUT, 'reach-1-notify.png'))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.keyboard.press('/'); pg.wait_for_timeout(500)
    check(pg.locator('#srch-q').count() == 1 and pg.evaluate("document.activeElement.id") == 'srch-q', 'away from the Plants page, the / key opens Search with the box focused')
    pg.keyboard.type('bluebon'); pg.wait_for_timeout(1200)
    check('Shopping and wishlist' in pg.locator('#srch-res').inner_text(), 'results are grouped')
    pg.keyboard.press('ArrowDown'); pg.wait_for_timeout(200)
    check(pg.evaluate("document.activeElement.closest('.srch-list') !== null"), 'the arrow keys move into the results')
    pg.keyboard.press('Enter'); pg.wait_for_timeout(1500)
    check(pg.evaluate('location.hash') == '#/shopping', 'Enter opens one')
    pg.locator('#search-btn').click(); pg.wait_for_timeout(300); pg.keyboard.type('back'); pg.wait_for_timeout(1200)
    check('Pages' in pg.locator('#srch-res').inner_text() and 'Backups' in pg.locator('#srch-res').inner_text(), 'pages are found too')
    pg.screenshot(path=os.path.join(OUT, 'reach-2-search.png'))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(500)
    if pg.locator('dialog[open]').count(): pg.locator('dialog[open] button[value=cancel]').first.click(); pg.wait_for_timeout(500)
    pg.locator('#search-btn').click(); pg.wait_for_timeout(300); pg.keyboard.type('sitter'); pg.wait_for_timeout(1200)   # 1.52.1: the sitter sheet is a page of its own
    check('Plant-sitter sheet' in pg.locator('#srch-res').inner_text(), 'the plant-sitter sheet is found as a page')
    pg.locator('#srch-res a', has_text='Plant-sitter sheet').click(); pg.wait_for_timeout(2500)
    check(pg.url.endswith('/sitter.html') and pg.locator('.ps-doc').count() == 1, 'and opening it goes to the sheet')
    pg.goto(TS + '/#/backups'); pg.wait_for_timeout(2500)
    check('Second copy' in pg.locator('main').inner_text() and pg.locator('form[data-form=bkcopies]').count() == 1, 'the Backups page has the Second copy section')
    pg.screenshot(path=os.path.join(OUT, 'reach-3-copies.png'), full_page=True)
    # ---- 1.58.0: the owner is told when the backups would not save the record
    check(pg.locator('.bk-note').count() == 0, 'with another computer set and photos in, the Backups page has no warning')
    call('PUT', '/api/backups/copies', {'url': ''}, E, TS); call('PUT', '/api/backups/settings', {'photos': False}, E, TS)
    pg.goto(TS + '/#/settings'); pg.wait_for_timeout(300); pg.goto(TS + '/#/backups'); pg.wait_for_timeout(2500)
    notes = pg.locator('.bk-note')
    check(notes.count() == 2 and 'leave out your photos' in notes.nth(0).inner_text() and 'same drive' in notes.nth(1).inner_text(), 'photos left out and every copy on one drive: the Backups page says both, at the top')
    check(notes.nth(1).locator('a[href="#/backups?sec=bk-copies"]').count() == 1 and 'protects nothing if the drive fails' in pg.locator('#bk-copies').inner_text(), 'the one-drive warning leads to Second copy, which says the folder beside the data is the same drive')
    pg.screenshot(path=os.path.join(OUT, 'reach-4-backup-notes.png'), full_page=True)
    notes.nth(0).get_by_role('button', name='Include the photos from now on').click(); pg.wait_for_timeout(2500)
    check(pg.locator('.bk-note').count() == 1 and call('GET', '/api/backups', h=E, base=TS)[1]['settings']['photos'] is True and pg.locator('form[data-form=bkset] input[name=photos]').is_checked(), 'one press puts the photos in automatic backups, and that warning goes')
    time.sleep(61)                                    # the Health card is worked out at most once a minute
    pg.goto(TS + '/#/settings'); pg.wait_for_timeout(3000)
    bad = pg.locator('#health-box li.hl-bad')
    check(any('same drive' in bad.nth(i).inner_text() for i in range(bad.count())), 'the Health card marks a copy beside the data as a problem, not as a second copy')
    pg.goto(TS + '/#/'); pg.wait_for_timeout(3500)
    q = pg.locator('#today-quiet')
    check(q.count() == 1 and 'Backups need a look' in q.inner_text() and q.locator('a[href="#/backups"]').count() == 1, 'Today tells the owner, with a link')
    vctx = b.new_context(viewport={'width': 1400, 'height': 900}, extra_http_headers=V); vctx.add_init_script("localStorage.setItem('plantdb.editor','Partner')")
    vp = vctx.new_page(); vp.goto(TS + '/#/'); vp.wait_for_timeout(3500)
    check('Backups need a look' not in vp.locator('main').inner_text(), 'someone who is not the owner is not told (they cannot change it)')
    vctx.close()
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All reach checks passed' if not fails else f'{len(fails)} reach check(s) failed'))
raise SystemExit(1 if fails else 0)
