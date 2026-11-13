"""Checks the weather history's own backup (1.58.0; plantdb/wxbackup.py, the "Weather history" part of the Backups page): the first
piece from the button, the page saying where things stand, the other backups leaving the weather out once it is covered, the
schedule saved from the page, putting back when nothing is missing, a viewer kept out, and the page at phone width.
Start the mock server with a fresh data folder, then: python3 dev/test/wxbackup_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/wxbackup-*.png"""
import json, os, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waits import until
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = BASE.rsplit(':', 1)[0] + ':' + str(int(BASE.rsplit(':', 1)[1]) + 1)       # the Tailscale port
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=BASE, login=None):
    h = {'Content-Type': 'application/json', 'X-Editor': 'Weather Backup Test'}
    if login: h.update({'Tailscale-User-Login': login, 'Tailscale-User-Name': login.split('@')[0].title()})
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None, headers=h, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(m, url, body=None, **kw):
    try: call(m, url, body, **kw); return 200
    except urllib.error.HTTPError as e: return e.code

import time
call('POST', '/api/weather/refresh')                     # a fresh record has no weather until its first update
for _ in range(120):
    W = call('GET', '/api/backups/weather')
    if W['live']['rows'] > 0 and not call('GET', '/api/jobs').get('running'): break
    time.sleep(0.5)
check(W['live']['rows'] > 0 and W['settings'] == {'enabled': True, 'freq': 'weekly', 'hour': 4}, f"the record has weather ({W['live']['rows']} hourly readings) and the weather backup is on, weekly")
had = len(W['pieces'])
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 1000})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Weather Backup Test')")
    pg.goto(BASE + '/#/backups'); pg.wait_for_selector('#bk-wx', timeout=20000)
    sec = pg.locator('#bk-wx')
    check('Weather history' in sec.locator('h2').inner_text() and 'in pieces' in sec.inner_text(), 'the Backups page has a Weather history part that says what the pieces are')
    if not had:
        check('No weather backup yet' in sec.inner_text() and 'still carry the weather' in sec.inner_text(), 'before the first piece: it says so, and that the other backups still carry the weather')
        check(sec.locator('button[data-what=combine]').is_disabled() and sec.locator('button[data-what=fill]').is_disabled(), 'nothing to combine or to put back from yet')
        sec.locator('button[data-what=make]').click()
    check(until(pg, lambda: 'Newest piece' in pg.locator('#bk-wx').inner_text(), 60000), 'Back up the weather now makes the first piece, and the page says when')
    sec = pg.locator('#bk-wx')
    W = call('GET', '/api/backups/weather')
    check(len(W['pieces']) >= 1 and W['pieces'][-1]['kind'] == 'full' and W['pieces'][-1]['rows'] == W['live']['rows'] and W['covered'], 'the first piece holds every hourly reading, and the weather counts as covered')
    check('leave the weather out' in sec.inner_text(), 'the page says the other backups now leave the weather out')
    sec.locator('details.grp > summary').click()
    check(until(pg, lambda: sec.locator('tbody tr').count() == len(W['pieces'])) and 'Everything up to then' in sec.locator('tbody tr').last.inner_text(), 'the pieces are listed, the first as everything up to then')
    check(sec.locator('tbody a[download]').first.get_attribute('href').startswith('/api/backups/weather/plantdb-weather-'), 'each piece can be downloaded')
    pg.screenshot(path=os.path.join(OUT, 'wxbackup-page.png'), full_page=True)
    # the other backups
    b = call('POST', '/api/backups', {'wait': True, 'note': 'after the weather piece'})
    mine = [x for x in call('GET', '/api/backups')['backups'] if x['file'] == b['file']][0]
    check(mine['weather'] is False and mine['bytes'] < 5 * 1048576, f"a backup made now leaves the weather out ({mine['bytes'] // 1024} KB)")
    pg.goto(BASE + '/#/'); pg.goto(BASE + '/#/backups'); pg.wait_for_selector('#bk-wx', timeout=20000)
    check(until(pg, lambda: 'without the weather history' in pg.locator('main').inner_text()), 'the list of backups says which ones are without the weather history')
    check('a backup of its own' in pg.locator('main > p.muted').first.inner_text(), 'the top of the page points to the weather backup')
    # nothing new: no second file
    n = len(call('GET', '/api/backups/weather')['pieces'])
    pg.locator('#bk-wx button[data-what=make]').click()
    check(until(pg, lambda: 'Nothing new since the last piece' in pg.locator('#bk-wx').inner_text(), 60000) and len(call('GET', '/api/backups/weather')['pieces']) == n, 'a second run with nothing new makes no file, and says so')
    # putting back when nothing is missing
    pg.locator('#bk-wx button[data-what=fill]').click()
    check(until(pg, lambda: (call('GET', '/api/backups/weather/job').get('text') or '').startswith('0 hourly readings and 0 day summaries put back'), 60000), 'putting back with nothing missing adds nothing')
    check(call('GET', '/api/backups/weather')['live']['rows'] == W['live']['rows'], 'and the record has the readings it had')
    # the schedule
    pg.wait_for_selector('#bk-wx form[data-form=wbset]', timeout=20000)
    f = pg.locator('#bk-wx form[data-form=wbset]')
    f.locator('select[name=freq]').select_option('daily'); f.locator('select[name=hour]').select_option('6'); f.locator('button[type=submit]').click()
    check(until(pg, lambda: call('GET', '/api/backups/weather')['settings'] == {'enabled': True, 'freq': 'daily', 'hour': 6}), 'how often and when are saved from the page')
    check(status('PUT', '/api/backups/weather/settings', {'freq': 'hourly'}) == 400, 'an unknown choice is refused')
    # a viewer (the first person to sign in through Tailscale is the owner, so the owner signs in first)
    call('GET', '/api/me', base=TS, login='owner@example.com')
    call('PUT', '/api/people', {'login': 'viewer@example.com', 'role': 'viewer'}, base=TS, login='owner@example.com')
    check(status('GET', '/api/backups/weather', base=TS, login='viewer@example.com') == 403 and status('POST', '/api/backups/weather', {'what': 'make'}, base=TS, login='viewer@example.com') == 403,
          'someone who is not the owner cannot read or start the weather backup')
    # phone width
    ph = br.new_page(viewport={'width': 384, 'height': 740})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Weather Backup Test')")
    ph.goto(BASE + '/#/backups'); ph.wait_for_selector('#bk-wx', timeout=20000)
    check(not ph.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'the Backups page fits a phone with no sideways scrolling')
    ph.locator('#bk-wx').scroll_into_view_if_needed(); ph.screenshot(path=os.path.join(OUT, 'wxbackup-phone.png'))
    br.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print(f"\n{'FAILED' if fails else 'passed'}: {len(fails)} of the checks failed" if fails else '\nAll weather backup checks passed')
sys.exit(1 if fails else 0)
