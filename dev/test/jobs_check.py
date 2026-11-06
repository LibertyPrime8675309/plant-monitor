"""Checks 1.32.0: the Jobs list on Settings shows what runs in the background (a backup, the store check, map look-ups), when
each scheduled job is next due, and lets the owner start one now; the split of server.py and app.js changed nothing a page can
see. Start the mock server with a fresh data folder (MOCK_TS=1), then:  python3 dev/test/jobs_check.py"""
import json, os, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Jobs Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)

j = call('GET', '/api/jobs')[1]
check({s['kind'] for s in j['schedule']} >= {'shops', 'backup'} and all(s['word'] for s in j['schedule']), 'the scheduled jobs are listed with when they are next due')
check(call('POST', '/api/jobs/run', {'kind': 'backup'}, V, TS)[0] == 403, 'someone who can only view cannot start one')
check(call('POST', '/api/jobs/run', {'kind': 'shops'}, E, TS)[0] == 400, 'the store check says when there is nothing to look for')
st, _ = call('POST', '/api/jobs/run', {'kind': 'backup'}, E, TS)
check(st == 200, 'the owner can start a backup from the Jobs list')
for _ in range(40):
    time.sleep(0.5)
    j = call('GET', '/api/jobs')[1]
    if any(d['kind'] == 'backup' for d in j['done']): break
d = next((d for d in j['done'] if d['kind'] == 'backup'), None)
check(d and d['ok'] and d['text'].startswith('plantdb-backup-') and d['seconds'] is not None, f'when it finishes it is on the finished list, with its file and how long it took ({d and d["text"]})')
call('PUT', '/api/wishlist', {'name': 'Lupinus texensis', 'common_name': 'Texas bluebonnet'})
for s in call('GET', '/api/shops')[1]['shops']:
    if s['key'] != 'snoopers': call('PUT', '/api/shops', {'key': s['key'], 'enabled': False})
call('PUT', '/api/shops', {'key': 'snoopers', 'url': 'http://127.0.0.1:8090/mock/shop/page'})
check(call('POST', '/api/jobs/run', {'kind': 'shops'}, E, TS)[0] == 200, 'a store check can be started from the Jobs list')
for _ in range(60):
    time.sleep(0.5)
    j = call('GET', '/api/jobs')[1]
    if any(d['kind'] == 'shops' for d in j['done']): break
d = next((d for d in j['done'] if d['kind'] == 'shops'), None)
check(d and d['ok'] and '1 stores read' in d['text'], f'the store check reports how many stores it read ({d and d["text"]})')
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1400, 'height': 900}, extra_http_headers=E); ctx.add_init_script("localStorage.setItem('plantdb.editor','Ethan')")
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(TS + '/#/settings'); pg.wait_for_timeout(2500)
    pg.locator('[data-act=jobs]').click(); pg.wait_for_timeout(1500)
    t = pg.locator('#dlg').inner_text()
    check('On a schedule' in t and 'Finished' in t and 'Backup' in t and 'Store check' in t, 'the Jobs window lists the schedule and what finished')
    check(pg.locator('#dlg [data-act=jobrun]').count() >= 2, 'with Run now buttons for the owner')
    pg.screenshot(path=os.path.join(OUT, 'jobs-1-window.png'))
    pg.keyboard.press('Escape')
    v = b.new_context(viewport={'width': 1400, 'height': 900}, extra_http_headers=V).new_page()
    v.goto(TS + '/#/settings'); v.wait_for_timeout(2500); v.locator('[data-act=jobs]').click(); v.wait_for_timeout(1500)
    check(v.locator('#dlg [data-act=jobrun]').count() == 0 and 'On a schedule' in v.locator('#dlg').inner_text(), 'someone who can only view sees the list, with no Run now')
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All jobs checks passed' if not fails else f'{len(fails)} jobs check(s) failed'))
raise SystemExit(1 if fails else 0)
