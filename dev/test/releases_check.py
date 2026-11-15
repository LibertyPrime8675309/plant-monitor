"""Checks the release rhythm (1.55.0, PLAN.md step 7; plantdb/releases.py, js/releases.js): "What's new" on Today from the
CHANGELOG, with "Got it" that is the person's own; "An update is ready" for the owner when GitHub has a newer release (the
answer is changed on the way to the page, since the mock never asks GitHub); the quarterly "Test a restore" reminder, which a
restore from Backups clears; the "every version's changes" page; a viewer may press Got it but sees neither owner line.
Start the mock server with a fresh data folder, then: python3 dev/test/releases_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/releases-*.png"""
import json, os, sys, time, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = BASE.rsplit(':', 1)[0] + ':' + str(int(BASE.rsplit(':', 1)[1]) + 1)       # the Tailscale port
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=BASE, login=None):
    h = {'Content-Type': 'application/json', 'X-Editor': 'Release Test'}
    if login: h.update({'Tailscale-User-Login': login, 'Tailscale-User-Name': login.split('@')[0].title()})
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None, headers=h, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(m, url, body=None, **kw):
    try: call(m, url, body, **kw); return 200
    except urllib.error.HTTPError as e: return e.code

W = call('GET', '/api/whatsnew')
version = call('GET', '/api/meta').get('version') or W['version']
check(W['version'] == version and W['entry'] and W['entry']['version'] == version, f'/api/whatsnew has the CHANGELOG entry for the running version ({version})')
check(W['entry']['lines'] and all('**' not in l or l.count('**') % 2 == 0 for l in W['entry']['lines']), 'with its lines (bullets without the dash)')
check(W['seen'] is False and W['update'] is None, 'not seen yet on a fresh install; no update known')
check(W['restore'] == {'last': None, 'days': None, 'due': True}, 'a restore has never been tried, so the test is due')
page = urllib.request.urlopen(BASE + '/api/whatsnew/all').read().decode()
check(f'<h2>{version}' in page and '<ul>' in page and '<script' not in page, "the every-version page lists this version, with bullets and no script")

# the owner's Today
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Release Test')")
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#rl-new', timeout=20000); pg.wait_for_selector('#today-needs', timeout=20000)
    txt = pg.inner_text('#rl-new')
    check(f'New in {version}' in txt and W['entry']['lines'][0].replace('**', '')[:40] in txt, 'Today opens with "New in <version>" and the first line of the entry')
    check(pg.locator('#rl-new details summary').count() == (1 if len(W['entry']['lines']) > 1 else 0), 'the rest of the entry folds under a summary')
    check(pg.locator('#rl-new strong').count() >= 1 and pg.locator('#rl-new [data-act=rlseen]').inner_text().strip() == 'Got it', 'bold from the CHANGELOG is real bold; the button says Got it')
    check(pg.locator('#rl-new a[href="/api/whatsnew/all"]').count() == 1, 'and a link to every version\'s changes')
    check(pg.locator('#rl-restore').count() == 1 and 'never been restored' in pg.inner_text('#rl-restore'), 'the owner has "Test a restore", saying none has been tried')
    check(pg.locator('#rl-update').count() == 0, 'no "update is ready" line when none is known')
    pg.locator('#rl-new').screenshot(path=os.path.join(OUT, 'releases-1-new.png'))
    pg.locator('#rl-restore').screenshot(path=os.path.join(OUT, 'releases-1-restore.png'))
    pg.locator('#rl-new details summary').click() if len(W['entry']['lines']) > 1 else None
    pg.wait_for_timeout(200); pg.locator('#rl-new').screenshot(path=os.path.join(OUT, 'releases-1-new-open.png'))
    # 1.56.5: on a later visit (another tab) it is folded to one line until Got it
    pg.evaluate("sessionStorage.removeItem('plantdb.rlshown')"); pg.reload(); pg.wait_for_selector('#rl-new', timeout=20000); pg.wait_for_timeout(800)   # as a new visit
    check(pg.locator('details#rl-new.rl-fold:not([open])').count() == 1 and f"What's new in {version}" in pg.inner_text('#rl-new summary'), 'a later visit shows it folded to one line')
    pg.locator('#rl-new > summary').click(); pg.wait_for_timeout(200)
    # Got it
    pg.locator('#rl-new [data-act=rlseen]').focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(1200)
    check(pg.locator('#rl-new').count() == 0 and 'Noted' in pg.inner_text('#toasts'), 'Got it (by keyboard) removes the box and says so')
    check(call('GET', '/api/whatsnew')['seen'] is True, 'the server remembers it for this person')
    pg.reload(); pg.wait_for_selector('#today-needs', timeout=20000); pg.wait_for_timeout(1000)
    check(pg.locator('#rl-new').count() == 0, 'and it stays away after a reload')
    # an update is ready: GitHub's answer, changed on the way to the page
    def newer(route):
        r = route.fetch(); d = r.json()
        d['update'] = {'version': '9.9.9', 'url': 'https://github.com/example/releases/tag/v9.9.9', 'published': '2026-12-01'}
        route.fulfill(response=r, body=json.dumps(d), headers=dict(r.headers, **{'content-type': 'application/json'}))
    cx = br.new_context(viewport={'width': 1280, 'height': 900}, service_workers='block')
    up = cx.new_page(); up.on('pageerror', lambda e: errs.append(str(e)))
    up.add_init_script("localStorage.setItem('plantdb.editor','Release Test')")
    up.route('**/api/whatsnew', newer)
    up.goto(BASE + '/#/'); up.wait_for_selector('#rl-update', timeout=20000)
    t = up.inner_text('#rl-update')
    check('An update is ready: 9.9.9' in t and 'Update Plant Database.cmd' in t and 'released 2026-12-01' in t, 'with a newer release on GitHub, Today says an update is ready and how to install it')
    check(up.locator('#rl-update a[href^="https://github.com/"]').inner_text().strip() == 'What changed', 'with a link to what changed')
    up.locator('#rl-update').screenshot(path=os.path.join(OUT, 'releases-2-update.png'))
    cx.close()
    # a restore clears the reminder
    bk = call('POST', '/api/backups', {'wait': 1, 'note': 'release check'})
    r = call('POST', '/api/backups/restore', {'file': bk['file']})
    check(r.get('restore_tested_at'), 'restoring a backup records when a restore was last tried')
    W2 = call('GET', '/api/whatsnew')
    check(W2['restore']['due'] is False and W2['restore']['days'] == 0, 'so the restore test is not due for another quarter')
    pg.reload(); pg.wait_for_selector('#today-needs', timeout=20000); pg.wait_for_timeout(1000)
    check(pg.locator('#rl-restore').count() == 0, 'and Today no longer asks for one')
    # a viewer, through Tailscale: Got it works, the owner's lines do not show
    call('GET', '/api/me', base=TS, login='owner@example.com')
    call('PUT', '/api/people', {'login': 'viewer@example.com', 'role': 'viewer'}, base=TS, login='owner@example.com')
    V = call('GET', '/api/whatsnew', base=TS, login='viewer@example.com')
    check(V['seen'] is False and V['update'] is None and 'restore' not in V, 'a viewer has not seen it (it is per person) and gets neither owner line')
    check(status('POST', '/api/whatsnew/seen', {}, base=TS, login='viewer@example.com') == 200, 'a viewer may press Got it')
    check(call('GET', '/api/whatsnew', base=TS, login='viewer@example.com')['seen'] is True, 'and it is remembered for them')
    check(status('PUT', '/api/people', {'login': 'x@example.com', 'role': 'editor'}, base=TS, login='viewer@example.com') == 403, 'while other changes are still refused for a viewer')
    # phone, dark, large text: the new box fits
    for name, disp in (('phone-light', {}), ('phone-dark-big', {'theme': 'dark', 'size': '160'})):
        ph = br.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        ph.on('pageerror', lambda e: errs.append(str(e)))
        ph.add_init_script("localStorage.setItem('plantdb.editor','Phone %s');localStorage.setItem('plantdb.display', JSON.stringify(%s))" % (name, json.dumps(disp)))
        ph.route('**/api/whatsnew', newer)
        ph.goto(BASE + '/#/'); ph.wait_for_selector('#rl-update', timeout=20000); ph.wait_for_timeout(800)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: nothing scrolls sideways ({over}px)')
        ph.evaluate("window.scrollTo(0, document.getElementById('rl-update').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'releases-3-{name}.png'))
        ph.close()
    br.close()
print(f'\n{len(fails)} FAIL, {len(errs)} page errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
sys.exit(1 if fails or errs else 0)
