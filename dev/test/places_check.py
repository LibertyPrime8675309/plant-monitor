"""Checks 1.28.0: nothing tied to Texas. The library's lists, filters and tags follow the place in use (Texas for Round Rock,
California for Nevada City); the Texas invasive list only shows in Texas; Identify offers the place's own state; Claude's
question names the place; and the Library's offline photos are downloaded by area, in a table with counts, percent,
"Check for updates" and the date. Start the mock server with a fresh data folder (MOCK_TS=1), then:
python3 dev/test/places_check.py      Screenshots: dev/tmp/shots/places-*.png"""
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
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Places Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)
NC = {'X-Place': str([h for h in call('GET', '/api/meta')[1]['homes'] if h['name'].startswith('Nevada')][0]['id'])}

check(call('GET', '/api/meta')[1]['region']['name'] == 'Texas', 'Round Rock is in Texas')
call('GET', '/api/library/local', h=NC)                     # the first look starts the region lookup
for _ in range(20):
    d = call('GET', '/api/library/local', h=NC)[1]
    if d.get('region'): break
    time.sleep(1)
check((d.get('region') or {}).get('name') == 'California', 'Nevada City is looked up and found to be in California')
check(d['filters'].get('native') == 'Native to California' and 'invasive' not in d['filters'], 'its filters say California, and there is no Texas invasive list')
check(any(l['name'] == 'near-2' or l['name'].startswith('near-') for l in d['lists']) and any('Nevada City' in l['label'] for l in d['lists']), 'its "near here" lists are about Nevada City')
dt = call('GET', '/api/library/local')[1]
check(dt['filters'].get('native') == 'Native to Texas' and 'invasive' in dt['filters'], 'Round Rock keeps Texas and its invasive list')
st = call('GET', '/api/identify/status', h=NC)[1]
check(st['scopes'].get('state', {}).get('count') == 6105 and 'texas' not in st['scopes'], "Identify's state list is California's for Nevada City")

# download areas
call('PUT', '/api/library/settings', {'online': True}, h=E, base=TS)
check(call('GET', '/api/library/areas/search?q=cali')[1][0]['name'] == 'California, US', 'the area search finds California')
check(call('POST', '/api/library/areas', {'place_id': 14, 'name': 'California, US'}, h=V, base=TS)[0] == 403, 'someone who can only view cannot add an area')
st, r = call('POST', '/api/library/areas', {'place_id': 14, 'name': 'California, US'}, h=E, base=TS)
check(st == 200 and r['areas'][0]['name'] == 'California, US', 'the owner adds California and its download starts')
check(call('POST', '/api/library/areas', {'place_id': 14, 'name': 'California, US'}, h=E, base=TS)[0] == 409, 'the same area cannot be added twice')
for _ in range(60):
    a = call('GET', '/api/library/areas')[1]['areas'][0]
    if a['state'] == 'idle' and a['checked_at']: break
    time.sleep(1)
check(a['total'] > 0 and a['kept'] == a['total'] - a['no_photo'] and a['percent'] > 0 and a['checked_at'],
      f"when it finishes the table shows photos downloaded out of how many ({a['kept']} of {a['total']}, {a['percent']}%) and the date")
st, r = call('POST', f"/api/library/areas/{a['id']}", h=E, base=TS)
check(st == 200, 'Check for updates starts again')
idx = call('GET', '/api/library/offline-index')[1]
check(idx['scope'] == 'areas' and len(idx['species']) >= 1 and idx['areas'] == ['California, US'], 'the offline copy for phones is the download areas')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1920, 'height': 1080}, extra_http_headers=E)
    ctx.add_init_script("localStorage.setItem('plantdb.editor','Ethan')")
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(TS + '/#/library'); pg.wait_for_timeout(4000)
    sec = pg.locator('#h-libpre').locator('xpath=..')
    sec.locator('table.lib-areas').wait_for(timeout=10000)
    t = sec.inner_text()
    check('California, US' in t and 'Check for updates' in t and '%' in t, 'the Library page has the table of areas with Check for updates')
    check(pg.locator('select[data-f=libknow] option').filter(has_text='Native to Texas').count() == 1, 'with Round Rock in use the area filter says Texas')
    sec.locator('[name=q]').fill('mex'); sec.locator('[data-form=libareafind] button').click()
    pg.locator('[data-act=libareaadd]').first.wait_for(timeout=8000)
    check('Mexico' in pg.locator('#libarea-res').inner_text(), 'searching shows places to choose from')
    sec.scroll_into_view_if_needed(); sec.screenshot(path=os.path.join(OUT, 'places-1-areas.png'))
    pg.evaluate("localStorage.setItem('plantdb.place', '2')")
    pg.reload(); pg.wait_for_timeout(4500)
    opts = pg.locator('select[data-f=libknow] option').all_inner_texts()
    check(any('California' in o for o in opts) and not any('Texas' in o for o in opts), 'with Nevada City in use the filters say California, never Texas')
    lk = pg.locator('select[data-f=libscope] option').all_inner_texts()
    check(any(o.startswith('California plants') for o in lk) and not any('Texas' in o for o in lk), 'Look in offers California plants')
    pg.screenshot(path=os.path.join(OUT, 'places-2-library-nevada.png'))
    v = b.new_context(viewport={'width': 1280, 'height': 900}, extra_http_headers=V).new_page()
    v.goto(TS + '/#/library'); v.wait_for_timeout(4000)
    check(v.locator('table.lib-areas').count() == 1 and v.locator('[data-act=libareaupd]').count() == 0, 'someone who can only view sees the table but no buttons')
    ph = b.new_context(viewport={'width': 384, 'height': 740}, is_mobile=True, has_touch=True, service_workers='block', extra_http_headers=E)
    ph.add_init_script("localStorage.setItem('plantdb.editor','Ethan');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    q = ph.new_page(); q.on('pageerror', lambda e: errs.append(str(e)))
    q.goto(TS + '/#/library'); q.wait_for_timeout(4000)
    check(not q.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'on a phone with the largest text nothing scrolls sideways')
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All places checks passed' if not fails else f'{len(fails)} places check(s) failed'))
raise SystemExit(1 if fails else 0)
