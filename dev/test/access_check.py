"""Checks 1.12.0: people signed in through Tailscale, their roles (owner, can edit, can view only), and what each may do.
The mock server stands in for the Tailscale container on port 8081 (MOCK_TS=1); this test sends the Tailscale-User-* headers
there itself, as Tailscale Serve would. Port 8080 is "this computer".
Start the mock server with a fresh data folder first (MOCK_TS=1), then:  python3 dev/test/access_check.py
Screenshots: dev/tmp/shots/access-*.png"""
import json, os, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan Schmidtke'}
G = {'Tailscale-User-Login': 'sam@example.net', 'Tailscale-User-Name': 'Sam Rivera'}
errs, fails = [], []
def more(pg):                      # 1.56.5: on a narrow screen Editing is behind More in the top bar
    if pg.locator('#more-btn').is_visible() and pg.locator('#more-btn').get_attribute('aria-expanded') != 'true': pg.locator('#more-btn').click(); pg.wait_for_timeout(200)
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, base, url, body=None, h=None, editor='Test'):
    hd = {'Content-Type': 'application/json', **({'X-Editor': editor} if editor else {}), **(h or {})}
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None, headers=hd, method=m)
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'null'), r.headers
    except urllib.error.HTTPError as e:
        t = e.read().decode()
        try: t = json.loads(t).get('error', t)
        except ValueError: pass
        return e.code, t, e.headers

# ---- the server
st, body, _ = call('GET', TS, '/api/me')
check(st == 403 and 'signed in to Tailscale' in body, 'through Tailscale without a person (a tagged device): refused')
st, me, h = call('GET', TS, '/api/me', h=E)
check(st == 200 and me['role'] == 'owner' and me['via'] == 'tailscale' and me['name'] == 'Ethan Schmidtke', 'the first person in is the owner, named by Tailscale')
check(h.get('Strict-Transport-Security', '').startswith('max-age='), 'HTTPS is enforced for Tailscale visitors (HSTS)')
check(not call('GET', LOCAL, '/api/version')[2].get('Strict-Transport-Security'), 'but not on http://localhost:8080')
st, me, _ = call('GET', TS, '/api/me', h=G)
check(me['role'] == 'viewer' and me['owner_name'] == 'Ethan Schmidtke', 'the next person starts as "Can view only"')
v = call('GET', TS, '/api/plants/P-013', h=G)[1]['version']
st, msg, _ = call('PUT', TS, '/api/plants/P-013', {'base_version': v, 'fields': {'notes': 'x'}}, h=G)
check(st == 403 and 'changes are turned off' in msg and 'Ethan Schmidtke' in msg, f'a viewer cannot change anything: "{msg[:60]}..."')
check(call('GET', TS, '/api/plants', h=G)[0] == 200 and call('GET', TS, '/api/audit/search', h=G)[0] == 200 and call('GET', TS, '/api/fertilizer/needs', h=G)[0] == 200, 'but can see plants, the audit log and the Fertilizer page')
for path in ('/api/backups', '/api/ingest', '/api/people'):
    check(call('GET', TS, path, h=G)[0] == 403, f'{path}: owner only')
st, me, _ = call('GET', LOCAL, '/api/me', h=G)
check(me['via'] == 'local' and me['role'] == 'owner' and me['login'] is None, 'Tailscale headers sent to http://localhost:8080 are ignored (cannot pretend to be someone)')
st, P, _ = call('PUT', LOCAL, '/api/people', {'login': 'sam@example.net', 'role': 'editor'}, editor='Ethan')
check(st == 200 and dict((p['login'], p['role']) for p in P['people'])['sam@example.net'] == 'editor', 'the owner (on this computer) lets Sam edit')
st, p, _ = call('PUT', TS, '/api/plants/P-013', {'base_version': v, 'fields': {'notes': 'Watered it on my visit'}}, h=G, editor='Someone Else')
check(st == 200 and p['updated_by'] == 'Sam Rivera', 'an editor can change things, and is named by Tailscale, not by what they type')
check(call('GET', TS, '/api/backups', h=G)[0] == 403 and call('PUT', TS, '/api/settings', {'base_url': ''}, h=G)[0] == 403, 'an editor still cannot reach backups or settings')
check(call('PUT', TS, '/api/people', {'login': 'ethan@example.com', 'role': 'viewer'}, h=E)[0] == 409, 'the last owner cannot be made a viewer')
st, me, _ = call('PUT', TS, '/api/me', {'name': 'Sam'}, h=G)
check(st == 200 and me['name'] == 'Sam', 'people can change the name shown for them')
st, msg, _ = call('POST', TS, '/api/care', {'plant': 'P-013', 'kind': 'water'}, h=G, editor=None)
check(st == 403 and 'X-Editor' in msg, 'changes without the app\'s own header are refused (other websites cannot send them)')
st, msg, _ = call('POST', TS, '/api/care', {'plant': 'P-013', 'kind': 'water'}, h={**G, 'Origin': 'https://evil.example'})
check(st == 403 and 'cross-origin' in msg, 'changes from another website\'s page are refused')
st, P, _ = call('DELETE', LOCAL, '/api/people?login=sam%40example.net')
check(st == 200 and all(p['login'] != 'sam@example.net' for p in P['people']), 'the owner can remove someone from the list')
check(call('GET', TS, '/api/me', h=G)[1]['role'] == 'viewer', 'if they come back, they start as "Can view only" again')
SENSOR = 'http://127.0.0.1:8082'
tok = call('GET', LOCAL, '/api/ingest')[1]['token']
check(call('GET', SENSOR, '/')[0] == 404 and call('GET', SENSOR, '/api/plants')[0] == 404, 'the sensor port shows nothing of the app')
check(call('POST', SENSOR, '/api/readings', {'device': 'porch', 'temp_f': 70})[0] == 403, 'the sensor port refuses readings without the token')
check(call('POST', SENSOR, '/api/readings', {'device': 'porch', 'temp_f': 70}, h={'X-Ingest-Token': tok})[0] in (200, 201), 'and takes readings with it')
names = [r['changed_by'] for r in call('GET', LOCAL, '/api/audit/search?q=Watered%20it%20on%20my%20visit')[1]['entries']]
check(names == ['Sam Rivera'], 'the audit log shows who really made the change')

with sync_playwright() as pw:
    b = pw.chromium.launch()
    def page(h, vw=(1280, 900), disp=None):
        c = b.new_context(viewport={'width': vw[0], 'height': vw[1]}, extra_http_headers=h or {})
        c.add_init_script("localStorage.setItem('plantdb.display',JSON.stringify(%s))" % json.dumps(disp or {'navopen': '0'}))
        pg = c.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        return pg
    g = page(G)
    g.goto(f'{TS}/#/plant/P-013'); g.wait_for_timeout(2600)
    check(g.locator('#who-name').inner_text() == 'Signed in as Sam Rivera', 'top right: Signed in as Sam Rivera')
    check(g.locator('.vw-note').count() == 1 and 'View only' in g.locator('.vw-note').inner_text(), 'a "View only" note at the top of the page')
    check(not g.locator('a[href$="/edit"]').first.is_visible() and g.locator('.quick-btns').count() and not g.locator('.quick-btns').first.is_visible(), 'Edit this page and the quick care buttons are hidden')
    check(g.locator('select[data-act=site]').first.is_disabled(), 'menus that save straight away are switched off')
    g.screenshot(path=f'{OUT}/access-viewer-plant.png')
    g.evaluate("document.querySelector('[data-act=care]') && document.querySelector('[data-act=care]').click()"); g.wait_for_timeout(600)
    t = g.locator('#toasts').inner_text()
    check('changes are turned off' in t or t == '', 'a change slipped through the page is answered with the view-only message')
    g.goto(f'{TS}/#/backups'); g.wait_for_timeout(1500)
    check('looked after by Ethan Schmidtke' in g.locator('#app').inner_text(), 'Backups page: looked after by the owner')
    g.goto(f'{TS}/#/weather'); g.wait_for_timeout(2600)
    check('Only Ethan Schmidtke can see the sensor' in g.locator('#sensor').inner_text(), 'Weather page: the sensor token is hidden')
    more(g); g.locator('#who-name').click(); g.wait_for_timeout(500)
    t = g.locator('dialog[open]').inner_text()
    check('sam@example.net' in t and 'not make changes' in t and g.locator('dialog[open] #people-box').count() == 0, 'Sam\'s window: who she is, view only, no people list')
    g.keyboard.press('Escape')
    e = page(E)
    e.goto(f'{TS}/#/plants'); e.wait_for_timeout(2500)
    more(e); e.locator('#who-name').click(); e.wait_for_timeout(800)
    check(e.locator('ul.people li').count() == 2, "Ethan's window lists the 2 people")
    e.select_option('select[data-f=prole][data-login="sam@example.net"]', 'editor'); e.wait_for_timeout(900)
    check('Saved: Can edit' in e.locator('#who-msg').inner_text(), 'choosing "Can edit" saves straight away')
    e.screenshot(path=f'{OUT}/access-owner-people.png')
    e.select_option('select[data-f=prole][data-login="ethan@example.com"]', 'viewer'); e.wait_for_timeout(900)
    check('at least one owner' in e.locator('#who-msg').inner_text() and e.locator('select[data-f=prole][data-login="ethan@example.com"]').input_value() == 'owner',
          'making himself a viewer is refused, and the menu goes back to Owner')
    e.fill('dialog[open] input[name=n]', 'Ethan'); e.locator('dialog[open] [data-act=whosave]').click(); e.wait_for_timeout(700)
    check(e.locator('#who-name').inner_text() == 'Signed in as Ethan', 'renaming himself updates the top right')
    e.keyboard.press('Escape')
    g.goto(f'{TS}/#/plants'); g.reload(); g.wait_for_timeout(2600)
    check(g.locator('.vw-note').count() == 0 and g.locator('a[href="#/new"]').first.is_visible(), 'after the change, Sam sees the editing buttons')
    # this computer: as before
    l = page(None)
    l.add_init_script("localStorage.setItem('plantdb.editor','Ethan')")
    l.goto(f'{LOCAL}/#/plants'); l.wait_for_timeout(2400)
    check(l.locator('#who-name').inner_text() == 'Editing as Ethan', 'on this computer: Editing as Ethan, as before')
    more(l); l.locator('#who-name').click(); l.wait_for_timeout(700)
    check(l.locator('ul.people li').count() == 2, 'and the people list is there too')
    l.keyboard.press('Escape')
    # phone, largest text
    p = page(G, (390, 844), {'size': '190', 'theme': 'dark'})
    p.goto(f'{TS}/#/plants'); p.wait_for_timeout(2400)
    more(p); p.locator('#who-name').click(); p.wait_for_timeout(500)
    over = p.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
    check(over <= 2, f'phone, largest text: no sideways scrolling ({over}px)')
    p.screenshot(path=f'{OUT}/access-phone-you.png')
    b.close()
errs = [x for x in errs if '403' not in x and '409' not in x]          # refused changes are expected in this test
for x in errs: print('JS error:', x)
sys.exit(1 if fails or errs else 0)
